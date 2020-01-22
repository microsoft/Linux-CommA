import re
import json
import os,sys,inspect
currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0,parentdir) 
import Constants.constants as cst
from DatabaseDriver.UpstreamPatchTable import UpstreamPatchTable
from datetime import datetime
from Objects.UpstreamPatch import UpstreamPatch
from Objects.UbuntuPatch import Ubuntu_Patch
from Objects.Diff_code import Diff_code
from Objects.confidence_weight import confidence_weight


def get_patch_object(indicator):
    if indicator == "Upstream":
        return UpstreamPatch("","","","","",datetime.now(),"","","",datetime.now())
    # elif indicator.startswith("Ub"):
    else:
        return Ubuntu_Patch("","","","",datetime.now(),"","","","",datetime.now())
    # else:
    #     print("Exception")


def insert_patch(db, match, distro, patch, indicator):
    if indicator == "Upstream":
        db.insert_Upstream(patch.commit_id, patch.author_name, patch.author_email, patch.subject, patch.description, patch.diff, patch.commit_time, patch.filenames, patch.author_time)
    elif indicator.startswith("Ub") or indicator.startswith("De"):
        conf = confidence_weight(0.2, 0.49, 0.1, 0.2, 0.01)
        dict1 = match.get_matching_patch(patch, conf)
        if (dict1):
            db.insertInto(dict1, distro.distro_id, patch.commit_id, patch.commit_time, patch.buglink, distro.kernel_version, patch.author_time)   # get dirstroId from db table
    elif indicator.startswith("SUSE"):
        conf = confidence_weight(0, 1, 0, 0, 0)
        dict1 = match.get_matching_patch(patch, conf)
        if (dict1):  # and dict1.upstream_patch_id != -1
            db.insertInto(dict1, distro.distro_id, patch.commit_id, patch.commit_time, patch.buglink, distro.kernel_version, patch.author_time)


def parse_log(filename, db, match, distro, indicator):
    '''
    parse_log will scrape each patch from git log
    '''
    patch = get_patch_object(distro.distro_id)
    prev_line_date = False
    diff_started = False
    commit_msg_started = False
    diff_fileNames = []
    count_added = 0
    count_present = 0
    skip_commit = False
    try:
        with open (filename, 'r', encoding="utf8") as f:
            try:    
                for line in f:
                    words = line.strip().split()
                    if words is None or len(words) == 0:
                        continue
                    if len(words) == 2 and words[0] == "commit":
                        # print("Commit id: "+commit_id)
                        if patch.commit_id is not None and len(patch.commit_id) > 0:
                            if db.check_commit_present(patch.commit_id, distro):
                                print("Commit id "+patch.commit_id+" is already present")
                                count_present += 1
                            elif skip_commit:
                                print("Commit id "+patch.commit_id+" is skipped as it is a merge commit")
                                count_present += 1
                            else:
                                patch.filenames = " ".join(diff_fileNames)
                                print(patch)
                                insert_patch(db, match, distro, patch, distro.distro_id)
                                count_added += 1
                            patch = get_patch_object(distro.distro_id)
                            prev_line_date = False
                            diff_started = False
                            commit_msg_started = False
                            skip_commit = False
                            diff_fileNames = []
                        patch.commit_id = words[1]
                    elif line.startswith("Merge: "):
                        skip_commit = True
                    elif len(words) >= 3 and words[0] == "Author:":
                        for word in range(1,len(words)-1):
                            patch.author_name += " "+words[word]
                        patch.author_email = words[len(words)-1]
                        patch.author_name = patch.author_name.strip()
                    elif len(words) == 7 and words[0] == "AuthorDate:":
                        date = ""
                        for i in range(1,len(words)-1):
                            date += " "+words[i]
                        date = date.strip()
                        patch.author_time = datetime.strptime(date, '%a %b %d %H:%M:%S %Y')
                    elif len(words) >= 3 and words[0] == "Commit:":
                        continue
                    elif len(words) == 7 and words[0] == "CommitDate:":
                        date = ""
                        for i in range(1, len(words)-1):
                            date += " "+words[i]
                        date = date.strip()
                        patch.commit_time = datetime.strptime(date, '%a %b %d %H:%M:%S %Y')
                        prev_line_date = True
                    elif prev_line_date:
                        patch.subject = line.strip()
                        prev_line_date = False
                        commit_msg_started = True
                    elif (commit_msg_started and distro.distro_id.startswith("Ub")) and words[0] == 'BugLink:':
                        patch.buglink = words[1]
                    elif commit_msg_started and line.startswith('diff --git'):
                        fileN = words[2][1:]
                        diff_fileNames.append(fileN)
                        commit_msg_started = False
                        diff_started = True
                        patch.diff += fileN
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
                        if words[0] == '+' or words[0] == '-':
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
            insert_patch(db, match, distro, patch, distro.distro_id)
            count_added += 1

    except IOError:
        print("[Error] Failed to read " + filename)
    finally:
        print("[Info] Added new commits: "+str(count_added)+"\t skipped patches:"+str(count_present))
        f.closed


if __name__ == '__main__':
    print("Starting patch scraping from files..")
    db = UpstreamPatchTable()
    parse_log(cst.PathToCommitLog+"/log", db, "", "", "Upstream")
