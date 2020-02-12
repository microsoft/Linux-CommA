import sys
import os
import inspect
currentdir = os.path.dirname(os.path.abspath(
    inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0, parentdir)
from datetime import datetime
from Objects.Patch import Patch


def process_commits(repo, revision, file_paths, db):
    """
    look at all commits in the given repo and handle based on distro

    repo: The git.repo object of the repository we want to parse commits of
    revision: The git revision we want to see the commits of, or None
    file_paths: list of filenames to check commits for
    db: Database object to add commits to
    """
    count_added = 0
    count_skipped = 0

    commits = repo.iter_commits(rev=revision, paths=file_paths, no_merges=True)
    for curr_commit in commits:
        patch = Patch.blank()
        patch.commit_id = curr_commit.hexsha
        patch.author_name = curr_commit.author.name
        patch.author_email = curr_commit.author.email
        patch.commit_time = datetime.utcfromtimestamp(curr_commit.committed_date)
        patch.author_time = datetime.utcfromtimestamp(curr_commit.authored_date)

        # TODO abstract parsing description to another function to simplify and optimize
        # Especially with the checking of phrases starting in lines, we don't have to do separately.

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
        description_lines = []
        # Check for blank description
        if len(split_message) > 1:
            description_lines = list(filter(should_keep_line, split_message[1:]))
            patch.description = "\n".join(description_lines)
        else:
            patch.description = ""

        # Check if this patch fixes other patches. This will fill
        # fixed_patches with a string of space-separated fixed patches
        # e.g. "SHA1 SHA2 SHA3"
        if patch.description != "":
            fixed_patches_lines = filter(lambda x: x.strip().lower().startswith('fixes:'), list(description_lines))
            fixed_patches = []
            for line in fixed_patches_lines:
                words = line.split(" ")
                if len(words) > 1:
                    fixed_patches.append(words[1])
            patch.fixed_patches = " ".join(fixed_patches)

        if (len(curr_commit.parents) == 0):
            # First ever commit, we don't need to store this as
            # it'll be present in any distro as it's needed
            # TODO revisit, maybe check against set hash of first commit?
            # Get code some other way? Unsure if first commit matters or not.
            continue
        else:
            # We are ignoring merges so all commits should have a single parent
            commit_diffs = curr_commit.tree.diff(curr_commit.parents[0], paths=file_paths, create_patch=True)

        filenames_list = [diff.a_path for diff in commit_diffs if diff.a_path is not None]
        patch.affected_filenames = " ".join(filenames_list)

        # Parse diff to only keep lines with changes (+ or - at start)
        # diff is passed in as bytes
        def parse_diff(diff):
            diff_lines = diff.decode("utf-8").splitlines()
            return "\n".join(filter(lambda line: line.startswith(("+", "-")), diff_lines))

        # The patch commit diffs are stored as "(filename1)\n(diff1)\n(filename2)\n(diff2)..."
        patch.commit_diffs = "\n".join(["%s\n%s" % (diff.a_path, parse_diff(diff.diff))
                                for diff in commit_diffs if diff.a_path is not None])

        # TODO is this check needed if we start on only patches we haven't processed before?
        # If we DO want to keep this check, let's move before parsing everything
        if db.check_commit_present(patch.commit_id):
            count_skipped += 1
        else:
            db.insert_patch(patch)
            count_added += 1

        # Log progress
        total_commits_processed = count_skipped + count_added
        if (total_commits_processed % 250 == 0):
            print("[Info] %d commits processed... %d added, %d skipped"
                % (total_commits_processed, count_added, count_skipped))

    print("[Info] Added new commits: %d\t skipped patches: %d" % (count_added, count_skipped))
