import re
import json
import os
import datetime
from DatabaseDriver import DatabaseDriver
from constants import *
from datetime import datetime

print("Welcome to Patch tracker!!")



def getEachPatch( filename ):
    '''
    getEachPatch will scrape each patch from git log
    '''
    print("Starting patch scraping from files..")
    db = DatabaseDriver()
    commit_id = ""
    author_name=""
    author_id=""
    date=""
    commit_sub=""
    commit_msg=""
    diff_files=""
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
                        if commit_id is not None and len(commit_id) > 0:
                            if db.checkCommitPresent(commit_id) or skip_commit:
                                # print("Commit id "+commit_id+" already present")
                                count_present += 1
                            else:
                                db.insertIntoUpstream(commit_id,author_name,author_id,commit_sub,commit_msg,diff_files,datetime_obj," ".join(diff_fileNames))
                                count_added += 1
                            author_name=""
                            author_id=""
                            date=""
                            commit_sub=""
                            commit_msg=""
                            diff_files=""
                            prev_line_date=False
                            diff_started=False
                            commit_msg_started=False
                            skip_commit = False
                            diff_fileNames = []
                        commit_id=words[1]
                    elif line.startswith("Merge: "):
                        skip_commit = True
                    elif len(words) >= 3 and words[0] == "Author:":
                        for word in range(1,len(words)-1):
                            author_name += " "+words[word]
                        author_id = words[len(words)-1]
                        author_name = author_name.strip()
                    elif len(words) == 7 and words[0] == "Date:":
                        for i in range(1,len(words)-1):
                            date += " "+words[i]
                        date = date.strip()
                        datetime_obj = datetime.strptime(date, '%a %b %d %H:%M:%S %Y')
                        prev_line_date = True
                    elif prev_line_date:
                        commit_sub=line
                        prev_line_date=False
                        commit_msg_started=True
                    elif line.startswith('Merge:'):
                        continue
                    elif commit_msg_started and line.startswith('diff --git'):
                        fileN = words[2][1:]
                        diff_fileNames.append(fileN)
                        commit_msg_started = False
                        diff_started=True
                        diff_files += line
                    elif commit_msg_started:
                        if 'Reported-by:' in line and 'Signed-off-by:' in line and 'Reviewed-by:' in line and 'Cc:' in line and 'fixes' in line:
                            continue
                        else:
                            commit_msg += line
                    elif diff_started and line.startswith('diff --git'):
                        fileN = words[2][1:]
                        diff_fileNames.append(fileN)
                    elif diff_started:
                        diff_files += line
                    else:
                        print("[Warning] No parsing done for the following line..")
                        print(line)
            except:
                print("[Error] Something gone wrong at line")
                print(line)

        if (commit_id is not None or len(commit_id) != 0) and not db.checkCommitPresent(commit_id):
            db.insertIntoUpstream(commit_id,author_name,author_id,commit_sub,commit_msg,diff_files,datetime_obj," ".join(diff_fileNames))
            count_added += 1
    except IOError:
        print("[Error] Failed to read "+ filename)
    finally:
        print("[Info] Added new commits: "+str(count_added)+"\t Already present:"+str(count_present))
        f.closed
