# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.
"""
Utility functions and classes
"""

from datetime import datetime, timezone

import approxidate


class DateString(str):
    """
    Wrapper for build-in string type with an additional attribute, epoch
    """

    def __init__(self, object_, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.epoch: float = approxidate.approx(str(object_))
        self.datetime = datetime.fromtimestamp(self.epoch, tz=timezone.utc)


def format_diffs(commit, paths):
    """
    Format diffs from commit object into string
    """

    diffs = []
    # We are ignoring merges so all commits should have a single parent
    for diff in commit.tree.diff(commit.parents[0], paths=paths, create_patch=True):
        if diff.a_path is not None:
            # The patch commit diffs are stored as "(filename1)\n(diff1)\n(filename2)\n(diff2)..."
            lines = "\n".join(
                line
                for line in diff.diff.decode("utf-8").splitlines()
                if line.startswith(("+", "-"))
            )
            diffs.append(f"{diff.a_path}\n{lines}")

    return "\n".join(diffs)


class PatchDiff:
    """
    Representation of code changes in a patch
    """

    def __init__(self, git_diff):
        """
        git_diff: Text of the diffs, of the form "(filename1)\n(diff1)\n(filename2)\n(diff2)",
        where each diff line begins with a + or -
        """
        # Parse the git_diff format to store in a way we can compare
        # We store diffs as a dict of filename:(add_lines set, remove_lines set)
        self.diffs = {}
        self.total_lines = 0

        filename = None
        for line in git_diff.splitlines():
            if line.startswith("+"):
                self.diffs[filename][0].add(line)
                self.total_lines += 1
            elif line.startswith("-"):
                self.diffs[filename][1].add(line)
                self.total_lines += 1
            else:
                filename = line
                self.diffs[filename] = (set(), set())

    def percent_present_in(self, other: "PatchDiff"):
        """
        Give the percent of diff lines present in other_patch_diffs.
        """
        if not self.total_lines:
            return 0.0

        missing_lines = 0
        for filename, (added, removed) in self.diffs.items():
            if filename in other.diffs:
                other_added, other_removed = other.diffs[filename]
                missing_lines += len(added - other_added) + len(removed - other_removed)
            else:
                missing_lines += len(added) + len(removed)

        return 1.0 - (missing_lines / self.total_lines)
