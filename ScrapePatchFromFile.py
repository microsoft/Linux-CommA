import re
import json
from DatabaseDriver import DatabaseDriver

print("Welcome to Patch tracker!!")
db = DatabaseDriver()
# 1. Go through whole bunch of Hyper-v files to get patches

# 2. Separate out each commit / patch and check database
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
    with open (filename, 'r') as f:
        for line in f:
            words = line.strip().split()
            if words == None or len(words)==0:
                continue
            if len(words) == 2 and words[0] == "commit":
                print("Commit id: "+commit_id)
                if commit_id is not None:
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
                commit_id=words[1]
            elif len(words) > 3 and words[0] == "Author:":
                for word in range(1,len(words)-1):
                    author_name += " "+words[word]
                author_id = words[len(words)-1]
            elif len(words) == 7 and words[0] == "Date:":
                for i in range(1,len(words)):
                    date += words[i]
                prev_line_date = True
            elif prev_line_date and ":" in line:
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
                print("Poor you.... Left this case!")

    f.closed

    if (commit_id is not None or len(commit_id) != 0) and not db.checkCommitPresent(commit_id):
        db.insertIntoUpstream(commit_id,author_name,author_id,commit_sub,commit_msg,diff_files)
    
getEachPatch('./sample.txt')

# 3. Update Database

#db.executeSelect()
# should do sanitization before inserting data into db
#db.insertDataTest()
