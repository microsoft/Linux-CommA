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
    first_commit_done=False
    prev_line_date=False
    diff_started=False
    commit_msg_started=False
    data = {}
    data_array = []
    with open (filename, 'r') as f:
        for line in f:
            words = line.strip().split()
            if words == None or len(words)==0:
                continue
            if len(words) == 2 and words[0] == "commit":
                commit_id=words[1]
                '''
                check here if this commid id is present in the database or not
                if it is present then we don't need to go further we can close this file as next commits would be theree
                '''
                if db.checkCommitPresent(commit_id):
                    break
                if first_commit_done:
                    data = {}
                    data["commit_id"] = commit_id
                    data["author_name"] = author_name
                    data["author_id"] = author_id
                    data["date"] = date
                    data["commit_sub"] = commit_sub
                    data["commit_msg"] = commit_msg
                    data["diff_files"] = diff_files
                    data_array.append(data)
                    author_name=""
                    author_id=""
                    date=""
                    commit_sub=""
                    commit_msg=""
                    diff_files=""
                first_commit_done=True
            elif len(words) > 3 and words[0] == "Author:":
                for word in range(1,len(words)-1):
                    author_name += words[word]
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
                first_commit_done=True
                print("Poor you.... Left this case!")

    f.closed
    data = {}
    data['commit_id'] = commit_id
    data["author_name"] = author_name
    data["author_id"] = author_id
    data["date"] = date
    data["commit_sub"] = commit_sub
    data["commit_msg"] = commit_msg
    data["diff_files"] = diff_files
    data_array.append(data)
    json_data=json.dumps(data_array)
    
    # print(json.dumps(json_data, indent=8, sort_keys=True))
    return json.dumps(json_data, indent=8, sort_keys=True)

#jsonArray = getEachPatch('./sample.txt')

# 3. Update Database

db.executeSelect()
db.insertData()
