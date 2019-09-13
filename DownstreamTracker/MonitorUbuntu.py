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
from DatabaseDriver.UpstreamPatchTable import UpstreamPatchTable
from DownstreamTracker.DownstreamMatcher import DownstreamMatcher

def get_downstream_patch( filename, db, match ):
    '''
    Get each patch and match it with upstream. Store matching commits
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
                                dict1 = match.get_matching_patch(patch)
                                db.insertInto(dict1,"UB18.04",patch.commit_id,patch.upstream_date)   # get dirstroId from db table
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
                        if 'Reported-by:' in line or 'Signed-off-by:' in line or 'Reviewed-by:' in line or 'Cc:' in line or 'fixes' in line:    # match case insensitive
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

        if (patch.commit_id is not None or len(patch.commit_id) != 0) and not db.checkIfPresent(patch.commit_id):
            db.insertInto(dict1,"UB18.04",patch.commit_id,patch.upstream_date)   # get dirstroId from db table
            count_added += 1


    except IOError:
        print("[Error] Failed to read "+ filename)
    finally:
        print("[Info] Added new commits: "+str(count_added)+"\t Already present:"+str(count_present))
        f.closed


if __name__ == '__main__':
    print("Welcome to Patch tracker!!")

    # make sure that Kernel is present
    os.makedirs(os.path.dirname(cst.PathToCommitLog), exist_ok=True)
    print("..Ubuntu Monitoring Script..")
    if os.path.exists(cst.PathToBionic):
        print("[Info] Path to Ubuntu Bionic Repo exists")
        repo = git.Repo(cst.PathToBionic)
        print("[Info] Pulling recent changes")
        repo.remotes.origin.pull()
        print("[Info] Git pull complete")
    else:
        print("[Info] Path to Ubuntu Bionic does not exists")
        print("[Info] Cloning Ubuntu Bionic repo")
        git.Git(cst.PathToClone).clone("git://git.launchpad.net/~ubuntu-kernel/ubuntu/+source/linux/+git/bionic")
        print("[Info] Cloning Complete")


    #parse maintainers file to get hyperV files
    print("[Info] parsing maintainers files")
    fileList = parseMaintainers(cst.PathToBionic)
    print("[Info] Received HyperV file paths")
    fileNames = sanitizeFileNames(fileList)


    # Collecting git logs for HyperV files
    print("[Info] Preprocessed HyperV file paths")
    currDir = os.getcwd()
    os.chdir(cst.PathToBionic)
    command = "git log -p -- "+' '.join(fileNames)+" >> "+cst.PathToCommitLog+"/bionicLog"
    os.system(command)
    print("[Info] Created HyperV files git logs at "+cst.PathToCommitLog+"/bionicLog")

    # Parse git log and dump data into database
    match = DownstreamMatcher(UpstreamPatchTable())
    get_downstream_patch(cst.PathToCommitLog+"/bionicLog", DistroMatch(), match)
