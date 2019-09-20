import re
import json
import os,sys,inspect
import datetime
currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0,parentdir) 
import Constants.constants as cst
from DatabaseDriver.UpstreamPatchTable import UpstreamPatchTable
from datetime import datetime
from Objects.UpstreamPatch import UpstreamPatch

def getEachPatch( filename, db):
    '''
    getEachPatch will scrape each patch from git log
    '''
    patch = UpstreamPatch("","","","","",datetime.now(),"","","")
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
                            if db.check_commit_present(patch.commit_id) or skip_commit:
                                # print("Commit id "+commit_id+" already present")
                                count_present += 1
                            else:
                                patch.filenames = " ".join(diff_fileNames)
                                db.insert_Upstream(patch.commit_id,patch.author_name,patch.author_email,patch.subject,patch.description,patch.diff,patch.upstream_date,patch.filenames)
                                count_added += 1
                            patch = UpstreamPatch("","","","","",datetime.now(),"","","")
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
                        patch.author_email = words[len(words)-1]
                        patch.author_name = patch.author_name.strip()
                    elif len(words) == 7 and words[0] == "Date:":
                        date=""
                        for i in range(1,len(words)-1):
                            date += " "+words[i]
                        date = date.strip()
                        patch.upstream_date = datetime.strptime(date, '%a %b %d %H:%M:%S %Y')
                        prev_line_date = True
                    elif prev_line_date:
                        patch.subject=line.strip()
                        prev_line_date=False
                        commit_msg_started=True
                    elif commit_msg_started and line.startswith('diff --git'):
                        fileN = words[2][1:]
                        diff_fileNames.append(fileN)
                        commit_msg_started = False
                        diff_started=True
                        patch.diff += line.strip()
                    elif commit_msg_started:
                        ignore_phrases = ('reported-by:', 'signed-off-by:', 'reviewed-by:', 'acked-by:', 'cc:')
                        lowercase_line = line.strip().lower()
                        if lowercase_line.startswith(ignore_phrases):
                            continue
                        else:
                            patch.description += line.strip()
                    elif diff_started and line.startswith('diff --git'):
                        fileN = words[2][1:]
                        diff_fileNames.append(fileN)
                    elif diff_started:
                        patch.diff += line.strip()
                    else:
                        print("[Warning] No parsing done for the following line..")
                        print(line)
            except Exception as e:
                print("[Error] "+str(e))
                print(line)

        if (patch.commit_id is not None or len(patch.commit_id) != 0) and not db.check_commit_present(patch.commit_id):
            patch.filenames = " ".join(diff_fileNames)
            db.insert_Upstream(patch.commit_id,patch.author_name,patch.author_email,patch.subject,patch.description,patch.diff,patch.upstream_date,patch.filenames)
            count_added += 1
    except IOError:
        print("[Error] Failed to read "+ filename)
    finally:
        print("[Info] Added new commits: "+str(count_added)+"\t skipped patches:"+str(count_present))
        f.closed

if __name__ == '__main__':
    print("Starting patch scraping from files..")
    db = UpstreamPatchTable()
    getEachPatch(cst.PathToCommitLog+"/log",db)