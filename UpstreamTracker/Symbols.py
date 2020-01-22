import os,sys,inspect
import git
currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0, parentdir) 
import Constants.constants as cst
from DatabaseDriver.UpstreamPatchTable import UpstreamPatchTable
from UpstreamTracker.MonitorChanges import parseMaintainers, sanitizeFileNames
from Util.util import list_diff


def get_symbols(files):
    command = "ctags -x −−c−kinds=f -R "+files+" | awk '{ if ($2 == \"function\") print $1 }' "+cst.RedirectOp+"../tmp.txt"
    #print("[Info] Running command: "+command)
    os.system(command)
    symb_list = [line.rstrip('\n') for line in open('../tmp.txt')]
    return symb_list


def map_symbols_to_patch(prev_commit, commits, fileNames):
    up = UpstreamPatchTable()
    os.chdir(cst.PathToLinux)
    command = "git reset --hard "+prev_commit
    print("[Info] "+command)
    os.system(command)
    before_patch_apply = None
    # iterate
    for commit in commits:
        # get symbols
        if before_patch_apply == None:
            before_patch_apply = get_symbols(' '.join(fileNames))

        command = "git reset --hard "+commit
        os.system(command)
        # get symbols
        after_patch_apply = get_symbols(' '.join(fileNames))

        # compare
        diff_symbols = list_diff(after_patch_apply,before_patch_apply)
        print("Commit:"+commit+" -> "+''.join(diff_symbols))

        # save symbols into database
        up.save_patch_symbols(commit, ' '.join(diff_symbols))
        before_patch_apply = after_patch_apply

    print("[Info] Finished symbol tracker")


def mapping_to_patches():
    up = UpstreamPatchTable()
    commits = up.get_commits()

    print("[Info] parsing maintainers files")
    fileList = parseMaintainers(cst.PathToLinux)
    print("[Info] Received HyperV file paths")
    fileNames = sanitizeFileNames(fileList)
    print("[Info] Preprocessed HyperV file paths")
    map_symbols_to_patch("097c1bd5673edaf2a162724636858b71f658fdd2", commits, fileNames)


def symbol_checker(list_of_symbols):
    print("[Info] Starting Symbol Checker")
    up = UpstreamPatchTable()
    symbol_map = up.get_patch_symbols()
    missing_symbol_patch = []
    for patchId, symbols in symbol_map.items():
        # list_diff gives set differences so may not be useful for same symbols
        # but same symbols could only be differ with the help of header files
        if len(list_diff(symbols, list_of_symbols)) > 0:
            missing_symbol_patch.append(patchId)
    return sorted(missing_symbol_patch)


if __name__ == '__main__':
    print("Starting Symbol matcher")
    # mapping_to_patches()
    list_of_symbols = [line.strip() for line in open("../syms.txt")]
    missing_symbols = symbol_checker(list_of_symbols)
    print("Missing symbols")
    print(*missing_symbols)