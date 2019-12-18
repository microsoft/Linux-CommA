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
from Objects.UbuntuPatch import Ubuntu_Patch
import git
from datetime import datetime

def get_patch_object(indicator):
    if indicator == "Upstream":
        return UpstreamPatch("","","","","",datetime.now(),"","","",datetime.now())
    elif indicator.startswith("Ub"):
        return Ubuntu_Patch("","","","",datetime.now(),"","","","",datetime.now())
    else:
        print("Exception")

def insert_patch(db, match, distro, patch, indicator):
    if indicator == "Upstream":
        db.insert_Upstream(patch.commit_id,patch.author_name,patch.author_email,patch.subject,patch.description,patch.diff,patch.commit_time,patch.filenames,patch.author_time)
    elif indicator.startswith("Ub"):
        dict1 = match.get_matching_patch(patch)
        if (dict1):
            db.insertInto(dict1,distro.distro_id,patch.commit_id,patch.commit_time, patch.buglink, distro.kernel_version, patch.author_time) # get dirstroId from db table


def parse_log(git_path, file_paths, db, match, distro, indicator):
    """
    parse_log looks at all commits in the given repo, and handles depending on the distro/indicator
    git_path: the path to the git repo we are parsing
    file_paths: list of filenames to check commits for
    db: Database object to add commits to
    match: A downstream matcher object
    distro: A Distro object, or None
    indicator: A unique indicator based on upstream or downstream distro (e.g. 'Ub' for Ubuntu, 'Upstream')
    """
    repo = git.Repo(git_path)
    count_added = 0
    count_present = 0
    
    commits = repo.iter_commits(rev=None, paths=file_paths, no_merges=True)
    for curr_commit in commits:
        patch = get_patch_object(indicator)
        patch.commit_id = curr_commit.hexsha
        patch.author_name = curr_commit.author.name
        patch.author_email = curr_commit.author.email
        patch.commit_time = datetime.utcfromtimestamp(curr_commit.committed_date)
        patch.author_time = datetime.utcfromtimestamp(curr_commit.authored_date)

        # Remove extra whitespace while splitting commit message
        split_message = [line.strip() for line in curr_commit.message.split('\n')]
        patch.subject = split_message[0]
        
        # Filter description by removing blank and unwanted lines
        ignore_phrases = ('reported-by:', 'signed-off-by:', 'reviewed-by:', 'acked-by:', 'cc:')
        def should_keep_line(line):
            simplified_line = line.lower()
            if not simplified_line:
                return False
            if simplified_line.startswith(ignore_phrases):
                return False
            return True
        
        # Check for blank description
        if len(split_message) > 1:
            description_lines = filter(should_keep_line, split_message[1:])
            patch.description = "\n".join(description_lines)
        else:
            patch.description = ""
            

        # Check if this patch fixes other patches. This will fill fixed_patches_concat with a string of space-separated fixed patches, e.g. "SHA1 SHA2 SHA3"
        # if indicator == "UpstreamDependencies":
        #     fixed_patches_lines = filter(lambda x : x.startsWith('Fixes:'), description_lines)
        #     fixed_patches = []
        #     for line in fixed_patches_lines:
        #         words = line.split(" ")
        #         if len(words) > 1:
        #             fixed_patches.append(words[1])
        #     patch.fixed_patches = " ".join(fixed_patches)
            
        if indicator.startswith("Ub"):
            buglink_lines = filter(lambda x : x.startsWith('BugLink:'), buglink_lines)
            if len(buglink_lines) > 0:
                # There will only be one buglink
                words = buglink_lines[0].split(" ")
                patch.buglink = words[1]

        if (len(curr_commit.parents) == 0):
            # First ever commit, we don't need to store this as obviously it'll be present in any distro as it's needed
            continue
        else:
            # We are ignoring merges so all commits should have a single parent
            commit_diffs = curr_commit.tree.diff(curr_commit.parents[0], paths=file_paths, create_patch=True)
        print('-')
        for diff in commit_diffs:
            print(diff.a_path)
            if not diff.a_path:
                print('uh oh')
        patch.filenames = " ".join([diff.a_path for diff in commit_diffs])
        patch.diff = "\n\n".join(["Path: %s\n%s"%(diff.a_path, diff.diff) for diff in commit_diffs])

        if db.check_commit_present(patch.commit_id, distro):
            print("Commit id "+patch.commit_id+" is skipped as either present already")
            count_present += 1
        else:
            insert_patch(db, match, distro, patch, indicator)
            count_added += 1
            
    print("[Info] Added new commits: "+str(count_added)+"\t skipped patches:"+str(count_present))



# def parse_log( filename, db, match, distro, indicator):
#     '''
#     parse_log will scrape each patch from git log
#     '''
#     patch = get_patch_object(indicator)
#     prev_line_date=False
#     diff_started=False
#     commit_msg_started=False
#     diff_fileNames = []
#     count_added = 0
#     count_present = 0
#     skip_commit = False
#     try:
#         with open (filename, 'r', encoding="utf8") as f:
#             try:    
#                 for line in f:
#                     words = line.strip().split()
#                     if words == None or len(words)==0:
#                         continue
#                     if len(words) == 2 and words[0] == "commit":
#                         # print("Commit id: "+commit_id)
#                         if patch.commit_id is not None and len(patch.commit_id) > 0:
#                             # TODO this check can be removed once we go over upstream once then add patches
#                             if db.check_commit_present(patch.commit_id, distro):
#                                 print("Commit id "+patch.commit_id+" is skipped as either present already")
#                                 count_present += 1
#                             elif skip_commit:
#                                 print("Commit id "+patch.commit_id+" is skipped as it is a merge commit")
#                                 count_present += 1
#                             else:
#                                 patch.filenames = " ".join(diff_fileNames)
#                                 print(patch)
#                                 insert_patch(db,match,distro,patch,indicator)
#                                 count_added += 1
#                             patch = get_patch_object(indicator)
#                             prev_line_date=False
#                             diff_started=False
#                             commit_msg_started=False
#                             skip_commit = False
#                             diff_fileNames = []
#                         patch.commit_id=words[1]
#                     elif line.startswith("Merge: ") or skip_commit:
#                         skip_commit = True
#                     elif len(words) >= 3 and words[0] == "Author:":
#                         for word in range(1,len(words)-1):
#                             patch.author_name += " "+words[word]
#                         patch.author_email = words[len(words)-1]
#                         patch.author_name = patch.author_name.strip()
#                     elif len(words) == 7 and words[0] == "AuthorDate:":
#                         date=""
#                         for i in range(1,len(words)-1):
#                             date += " "+words[i]
#                         date = date.strip()
#                         patch.author_time = datetime.strptime(date, '%a %b %d %H:%M:%S %Y')
#                     elif len(words) >= 3 and words[0] == "Commit:":
#                         continue
#                     elif len(words) == 7 and words[0] == "CommitDate:":
#                         date=""
#                         for i in range(1,len(words)-1):
#                             date += " "+words[i]
#                         date = date.strip()
#                         patch.commit_time = datetime.strptime(date, '%a %b %d %H:%M:%S %Y')
#                         prev_line_date = True
#                     elif prev_line_date:
#                         patch.subject=line.strip()
#                         prev_line_date=False
#                         commit_msg_started=True
#                     elif (commit_msg_started and indicator.startswith("Ub")) and words[0] == 'BugLink:':
#                         patch.buglink = words[1]
#                     elif commit_msg_started and line.startswith('diff --git'):
#                         fileN = words[2][1:]
#                         diff_fileNames.append(fileN)
#                         commit_msg_started = False
#                         diff_started=True
#                         patch.diff += line.strip()
#                     elif commit_msg_started:
#                         ignore_phrases = ('reported-by:', 'signed-off-by:', 'reviewed-by:', 'acked-by:', 'cc:')
#                         lowercase_line = line.strip().lower()
#                         if lowercase_line.startswith(ignore_phrases):
#                             continue
#                         else:
#                             patch.description += line.strip()
#                     elif diff_started and line.startswith('diff --git'):
#                         fileN = words[2][1:]
#                         diff_fileNames.append(fileN)
#                     elif diff_started:
#                         patch.diff += line.strip()
#                     else:
#                         print("[Warning] No parsing done for the following line..")
#                         print(line)
#             except Exception as e:
#                 print("[Error] "+str(e))
#                 print(line)

#         if (patch.commit_id is not None or len(patch.commit_id) != 0) and not db.check_commit_present(patch.commit_id, distro):
#             patch.filenames = " ".join(diff_fileNames)
#             print(patch)
#             insert_patch(db,match,distro,patch,indicator)
#             count_added += 1
            
#     except IOError:
#         print("[Error] Failed to read "+ filename)
#     finally:
#         print("[Info] Added new commits: "+str(count_added)+"\t skipped patches:"+str(count_present))
#         f.closed

