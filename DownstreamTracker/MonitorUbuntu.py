import git
import os,sys,inspect
currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0,parentdir) 
import Constants.constants as cst
from UpstreamTracker.MonitorChanges import parseMaintainers,sanitizeFileNames
from Objects.Patch import Patch
from Objects.DistroPatchMatch import DistroPatchMatch
from datetime import datetime
from DatabaseDriver.DistroMatch import DistroMatch


def getDownStreamPatch( filename, db ):
    '''
    getEachPatch will scrape each patch from git log
    '''
    patch = Patch.blank()
    prev_line_date=False
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
                    if len(words) == 2 and words[0] == "commit":
                        # print("Commit id: "+commit_id)
                        if patch.commit_id is not None and len(patch.commit_id) > 0:
                            if db.checkIfPresent(patch.commit_id) or skip_commit:
                                print("Commit id "+patch.commit_id+" already present")
                                count_present += 1
                            else:
                                print(patch)
                                # call distropatchmatch
                                # get best match
                                match = DistroPatchMatch("","","","","","")
                                dict1 = match.matcher(patch)
                                db.insertInto(match, dict1["patchId"],"UB18.04",patch.commit_id,patch.upstream_date)
                                count_added += 1
                            patch = Patch.blank()
                            prev_line_date=False
                            diff_started=False
                            commit_msg_started=False
                            skip_commit = False
                            diff_fileNames = []
                        patch.commit_id=words[1]
                    elif line.startswith("Merge: "):
                        skip_commit = True
                    elif len(words) >= 3 and words[0] == "Author:":
                        for word in range(1,len(words)-1):
                            patch.author_name += " "+words[word]
                        patch._author_email = words[len(words)-1]
                        patch.author_name = patch.author_name.strip()
                    elif len(words) == 7 and words[0] == "Date:":
                        date = ""
                        for i in range(1,len(words)-1):
                            date += " "+words[i]
                        date = date.strip()
                        patch.upstream_date = datetime.strptime(date, '%a %b %d %H:%M:%S %Y')
                        prev_line_date = True
                    elif prev_line_date:
                        patch.subject=line
                        prev_line_date=False
                        commit_msg_started=True
                    elif commit_msg_started and line.startswith('diff --git'):
                        fileN = words[2][1:]
                        diff_fileNames.append(fileN)
                        commit_msg_started = False
                        diff_started=True
                        patch.diff += line
                    elif commit_msg_started:
                        if 'Reported-by:' in line and 'Signed-off-by:' in line and 'Reviewed-by:' in line and 'Cc:' in line and 'fixes' in line:
                            continue
                        else:
                            patch.description += line
                    elif diff_started and line.startswith('diff --git'):
                        fileN = words[2][1:]
                        diff_fileNames.append(fileN)
                    elif diff_started:
                        patch.diff += line
                    else:
                        print("[Warning] No parsing done for the following line..")
                        print(line)
            except Exception as e:
                print("[Error] "+str(e))
                print(line)

        if (patch.commit_id is not None or len(patch.commit_id) != 0) and not db.checkCommitPresent(patch.commit_id):
            print(patch)
            db.insertIntoUpstream(patch.commit_id,patch.author_name,patch.author_id,patch.subject,patch.description,patch.diff,patch.upstream_date," ".join(diff_fileNames))
            count_added += 1
    except IOError:
        print("[Error] Failed to read "+ filename)
    finally:
        print("[Info] Added new commits: "+str(count_added)+"\t Already present:"+str(count_present))
        f.closed


if __name__ == '__main__':
    print("Welcome to Patch tracker!!")
    os.makedirs(os.path.dirname(cst.PathToCommitLog), exist_ok=True)
    print("..Ubuntu Monitoring Script..")
    if os.path.exists(cst.PathToBionic):
        print("[Info] Path to Ubuntu Bionic Repo exists")
        repo = git.Repo(cst.PathToLinux)
        print("[Info] Pulling recent changes")
        repo.remotes.origin.pull()
        print("[Info] Git pull complete")
    else:
        print("[Info] Path to Ubuntu Bionic does not exists")
        print("[Info] Cloning Ubuntu Bionic repo")
        git.Git(cst.PathToClone).clone("git://git.launchpad.net/~ubuntu-kernel/ubuntu/+source/linux/+git/bionic")
        print("[Info] Cloning Complete")

    print("[Info] parsing maintainers files")
    fileList = parseMaintainers(cst.PathToBionic)
    print("[Info] Received HyperV file paths")
    fileNames = sanitizeFileNames(fileList)
    print("[Info] Preprocessed HyperV file paths")
    print(fileNames)
    currDir = os.getcwd()
    os.chdir(cst.PathToBionic)
    # print(' '.join(fileNames))
    command = "git log -p -- "+' '.join(fileNames)+" >> "+cst.PathToCommitLog+"/bionicLog"
    os.system(command)
    print("[Info] Created HyperV files git logs at "+cst.PathToCommitLog)
    getDownStreamPatch(cst.PathToCommitLog+"/bionicLog", DistroMatch())
