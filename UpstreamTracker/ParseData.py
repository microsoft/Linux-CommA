import sys
import os
import inspect
currentdir = os.path.dirname(os.path.abspath(
    inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0, parentdir)
import Util.Constants as cst  # noqa E402
from DatabaseDriver.UpstreamPatchTable import UpstreamPatchTable  # noqa E402
from datetime import datetime  # noqa E402
from Objects.UpstreamPatch import UpstreamPatch  # noqa E402
from Objects.UbuntuPatch import UbuntuPatch  # noqa E402
from Objects.DiffCode import DiffCode  # noqa E402
from Objects.ConfidenceWeight import ConfidenceWeight  # noqa E402
from datetime import datetime  # noqa E402
import git  # noqa E402


def get_patch_object(indicator):
    if indicator == "Upstream":
        return UpstreamPatch("", "", "", "", "", datetime.now(),
                             "", "", "", datetime.now(), "")
    else:
        return UbuntuPatch("", "", "", "", datetime.now(),
                           "", "", "", "", datetime.now())


def insert_patch(db, match, distro, patch, indicator):
    if indicator == "Upstream":
        db.insert_upstream(patch.commit_id, patch.author_name, patch.author_email, patch.subject,
                           patch.description, patch.diff, patch.commit_time, patch.filenames,
                           patch.author_time, patch.fixed_patches)
    elif indicator.startswith("Ub") or indicator.startswith("De"):
        conf = ConfidenceWeight(0.2, 0.49, 0.1, 0.2, 0.01)
        distro_patch_match = match.get_matching_patch(patch, conf)
        if (distro_patch_match and distro_patch_match.upstream_patch_id != -1):
            db.insert_into(distro_patch_match, distro.distro_id, patch.commit_id, patch.commit_time, patch.buglink,
                           distro.kernel_version, patch.author_time)
    elif indicator.startswith("SUSE"):
        conf = ConfidenceWeight(0, 1, 0, 0, 0)
        distro_patch_match = match.get_matching_patch(patch, conf)
        if (distro_patch_match and distro_patch_match.upstream_patch_id != -1):
            db.insert_into(distro_patch_match, distro.distro_id, patch.commit_id, patch.commit_time, patch.buglink,
                           distro.kernel_version, patch.author_time)


def process_commits(repo, file_paths, db, match, distro):
    """
    look at all commits in the given repo and handle based on distro

    repo: The git.repo object of the repository we want to parse commits of
    revision: The git revision we want to see the commits of, or None
    file_paths: list of filenames to check commits for
    db: Database object to add commits to
    match: A downstream matcher object, or None if we don't need to match
    distro: A Distro object, or None
    indicator: A unique indicator repo (e.g. 'Ub' for Ubuntu, 'Upstream')
    """
    count_added = 0
    count_present = 0

    indicator = distro.distro_id
    commits = repo.iter_commits(rev=distro.get_revision(), paths=file_paths, no_merges=True)
    for curr_commit in commits:
        patch = get_patch_object(indicator)
        patch.commit_id = curr_commit.hexsha
        patch.author_name = curr_commit.author.name
        patch.author_email = curr_commit.author.email
        patch.commit_time = datetime.utcfromtimestamp(curr_commit.committed_date)  # noqa E501
        patch.author_time = datetime.utcfromtimestamp(curr_commit.authored_date)  # noqa E501

        # TODO abstract parsing description to another function to simplify and optimize

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
        if indicator == "Upstream" and patch.description != "":
            fixed_patches_lines = filter(
                            lambda x: x.strip().lower().startswith('fixes:'),
                            list(description_lines))
            fixed_patches = []
            for line in fixed_patches_lines:
                words = line.split(" ")
                if len(words) > 1:
                    fixed_patches.append(words[1])
            patch.fixed_patches = " ".join(fixed_patches)

        if indicator.startswith("Ub"):
            buglink_lines = list(filter(
                            lambda x: x.startswith('BugLink:'),
                            list(description_lines)))
            if len(buglink_lines) > 0:
                # There will only be one buglink
                words = buglink_lines[0].split(" ")
                patch.buglink = words[1]

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
        patch.filenames = " ".join(filenames_list)

        # Parse diff to only keep lines with changes (+ or - at start)
        # diff is passed in as bytes
        def parse_diff(diff):
            diff_lines = diff.decode("utf-8").splitlines()
            return "\n".join(filter(
                lambda line: line.startswith(("+", "-")), diff_lines))

        patch.diff = "\n".join(["%s\n%s" % (diff.a_path, parse_diff(diff.diff))
                                for diff in commit_diffs if diff.a_path is not None])

        if db.check_commit_present(patch.commit_id, distro):
            print("Commit id %s is skipped as it is present already" % patch.commit_id)
            count_present += 1
        else:
            insert_patch(db, match, distro, patch, indicator)
            count_added += 1

    print("[Info] Added new commits: %d\t skipped patches: %d" % (count_added, count_present))
