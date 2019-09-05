import re
import json
import os
from DatabaseDriver import DatabaseDriver

print("Welcome to Patch tracker!!")
db = DatabaseDriver()

'''
getEachPatch will scrape each patch from git log
'''
def getEachPatch( filename ):
    print("Starting patch scraping from files..")
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
    try:
        with open (filename, 'r', encoding="utf8") as f:
            try:    
                for line in f:
                    words = line.strip().split()
                    if words == None or len(words)==0:
                        continue
                    if len(words) == 2 and words[0] == "commit":
                        print("Commit id: "+commit_id)
                        if commit_id is not None and len(commit_id) > 0:
                            if db.checkCommitPresent(commit_id):
                                print("Commit id "+commit_id+" already present")
                            else:
                                db.insertIntoUpstream(commit_id,author_name,author_id,commit_sub,commit_msg,diff_files)
                            author_name=""
                            author_id=""
                            date=""
                            commit_sub=""
                            commit_msg=""
                            diff_files=""
                            prev_line_date=False
                            diff_started=False
                            commit_msg_started=False
                        commit_id=words[1]
                    elif len(words) > 3 and words[0] == "Author:":
                        for word in range(1,len(words)-1):
                            author_name += " "+words[word]
                        author_id = words[len(words)-1]
                    elif len(words) == 7 and words[0] == "Date:":
                        for i in range(1,len(words)):
                            date += words[i]
                        prev_line_date = True
                    elif prev_line_date:    #and ':' in line removed as not all subject lines have :
                        commit_sub=line
                        prev_line_date=False
                        commit_msg_started=True
                    elif commit_msg_started and line.startswith('diff --git'):
                        commit_msg_started = False
                        diff_started=True
                        diff_files += line
                    elif commit_msg_started:
                        commit_msg += line
                    elif diff_started:
                        diff_files += line
                    else:
                        print("[Warning] No parsing done for the following line..")
                        print(line)
                        print("\n")
            except:
                print("[Error] Something gone wrong at line")
                print(line)

        if (commit_id is not None or len(commit_id) != 0) and not db.checkCommitPresent(commit_id):
            db.insertIntoUpstream(commit_id,author_name,author_id,commit_sub,commit_msg,diff_files)
    except IOError:
        print("[Error] Failed to read "+ filename)
    finally:
        f.closed
commitLogPath = "../commit-log"
for root, dirs, files in os.walk(commitLogPath):
    for filename in files:
        print("----------------------"+filename+"-----------------------------")
        getEachPatch(commitLogPath+"/"+filename)

