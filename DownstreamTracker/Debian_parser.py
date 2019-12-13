from datetime import datetime
import os,sys,inspect
currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0,parentdir) 
import Constants.constants as cst
from UpstreamTracker.ParseData import get_patch_object
from DatabaseDriver.DistroMatch import DistroMatch
from UpstreamTracker.MonitorChanges import parseMaintainers,sanitizeFileNames
from Objects.Distro import Distro
from Util.util import contains_filepath

filenames = []


def check_hyperV_patch(patch_filenames):
    global filenames
    if len(filenames) == 0:
        print("[Info] parsing maintainers files")
        fileList = parseMaintainers(cst.PathToClone+'linux')
        print("[Info] Received HyperV file paths")
        filenames = sanitizeFileNames(fileList)

    for file in patch_filenames:
        for hV_file in filenames:
            if contains_filepath(file, hV_file):
                return True
    
    return False



def parse_log( filename, db, match, distro, indicator):
    '''
    parse_log will scrape each patch from git log
    '''
    patch = get_patch_object("Debian")
    diff_started=False
    commit_msg_started=False
    diff_fileNames = []
    count_added = 0
    count_present = 0
    skip_commit = False
    try:
        with open (filename, 'r', encoding="utf8") as f:
            try:    
                for line in f:
                    words = line.strip().split()
                    if words == None or len(words)==0:
                        continue
                    if len(words) >= 3 and words[0] == "From:":
                        
                        if len(patch.subject) > 0 and not db.check_commit_present(patch.subject, distro):
                            #check if commit already present
                            patch.filenames = " ".join(diff_fileNames)
                            if check_hyperV_patch(diff_fileNames):
                                print(" ************hyperV related patch*********************"+patch.subject)
                                #if true then match upstream
                                #then insert
                            print("New commit "+patch.subject)

                            patch = get_patch_object("debian")
                            diff_started=False
                            commit_msg_started=False
                            skip_commit = False
                            diff_fileNames = []

                        for word in range(1,len(words)-1):
                            patch.author_name += " "+words[word]
                        patch.author_email = words[len(words)-1]
                        patch.author_name = patch.author_name.strip()
                        
                    elif words[0] == "Subject:":
                        patch.subject=' '.join(words[1:])
                        commit_msg_started=True
                    elif len(words) == 7 and words[0] == "Date:":
                        date=""
                        for i in range(1,len(words)-1):
                            date += " "+words[i]
                        date = date.strip()
                        try:
                            patch.author_time = datetime.strptime(date, '%a, %d %b %Y %H:%M:%S')
                        except ValueError:
                            patch.author_time = datetime.strptime(date, '%a %b %d %H:%M:%S %Y')
                        commit_msg_started=True
                    elif words[0] == 'Bug-Debian:':
                        patch.buglink = words[1]
                    elif words[0] == "Forwarded:":
                        continue
                    elif commit_msg_started and line.startswith('--- a/'):
                        fileN = words[1][1:]
                        diff_fileNames.append(fileN)
                        commit_msg_started = False
                        diff_started=True
                        patch.diff += fileN
                    elif commit_msg_started:
                        ignore_phrases = ('reported-by:', 'signed-off-by:', 'reviewed-by:', 'acked-by:', 'cc:')
                        lowercase_line = line.strip().lower()
                        if lowercase_line.startswith(ignore_phrases):
                            continue
                        else:
                            patch.description += line.strip()
                    elif diff_started and line.startswith('--- a/'):
                        fileN = words[1][1:]
                        diff_fileNames.append(fileN)
                    elif diff_started:
                        if line.startswith('+') or line.startswith('-'):
                            patch.diff += "\n"+line.strip()
                    else:
                        print("[Warning] No parsing done for the following line..")
                        print(line)
                        
            except Exception as e:
                print("[Error] "+str(e))
                print(line)

        if (patch.commit_id is not None or len(patch.commit_id) != 0) and not db.check_commit_present(patch.commit_id, distro):
            patch.filenames = " ".join(diff_fileNames)
            print(patch)
            count_added += 1
            
    except IOError:
        print("[Error] Failed to read "+ filename)
    finally:
        print("[Info] Added new commits: "+str(count_added)+"\t skipped patches:"+str(count_present))
        f.closed

if __name__ == '__main__':
    print("Starting patch scraping from files..")
    distro = Distro("Debian","","","","")
    parse_log(cst.PathToCommitLog+"/debian.log",DistroMatch(),"",distro,"Debain")