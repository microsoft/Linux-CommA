
class PatchDiffs:

    def __init__(self, git_diff):
        """
        PatchDiffs represents all code changes a patch introduces

        git_diff: Text of the diffs, of the form "(filename1)\n(diff1)\n(filename2)\n(diff2)",
        where each diff line begins with a + or -
        """
        # Parse the git_diff format to store in a way we can compare
        # We store diffs as a dict of filename:(add_lines set, remove_lines set)
        self.diffs = {}
        self.num_total_lines = 0
        filename = ""
        add_lines = set()
        remove_lines = set()
        for line in git_diff.split("\n"):
            self.num_total_lines += 1
            if (line.startswith("-")):
                remove_lines.add(line)
            elif (line.startswith("+")):
                add_lines.add(line)
            else:
                if (filename != ""):
                    self.diffs[filename] = (add_lines, remove_lines)
                    add_lines = set()
                    remove_lines = set()
                filename = line

        if (filename != ""):
            self.diffs[filename] = (add_lines, remove_lines)
            add_lines = set()
            remove_lines = set()

    def percent_present_in(self, other_patch_diffs):
        """
        This will give the percent of diff lines present in other_patch_diffs.
        """
        if (self.num_total_lines == 0):
            return 0.0

        num_missing_lines = 0
        for filename, diffs in self.diffs.items():
            add_lines, remove_lines = diffs
            if filename in other_patch_diffs.diffs:
                other_add_lines, other_remove_lines = other_patch_diffs.diffs[filename]
                num_missing_lines += len(add_lines - other_add_lines)
                num_missing_lines += len(remove_lines - other_remove_lines)
            else:
                num_missing_lines += (len(add_lines) + len(remove_lines))

        return 1.0 - (num_missing_lines / self.num_total_lines)
