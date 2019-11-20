import os,sys,inspect
import git
currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0,parentdir) 
from UpstreamTracker.MonitorChanges import parseMaintainers,sanitizeFileNames
import Constants.constants as cst

#git.Git("C:/Users/ABMARATH/Documents/Work/").clone("git://git.launchpad.net/~ubuntu-kernel/ubuntu/+source/linux/+git/bionic",branch = "master")
patch_diff="/drivers/hv/vmbus_drv.c + /* +  * When we reach here, all the non-boot CPUs have been offlined, and +  * the stimers on them have been unbound in hv_synic_cleanup() -> +  * hv_stimer_cleanup() -> clockevents_unbind_device(). +  * +  * hv_synic_suspend() only runs on CPU0 with interrupts disabled. Here +  * we do not unbind the stimer on CPU0 because: 1) it's unnecessary +  * because the interrupts remain disabled between syscore_suspend() +  * and syscore_resume(): see create_image() and resume_target_kernel(); +  * 2) the stimer on CPU0 is automatically disabled later by +  * syscore_suspend() -> timekeeping_suspend() -> tick_suspend() -> ... +  * -> clockevents_shutdown() -> ... -> hv_ce_shutdown(); 3) a warning +  * would be triggered if we call clockevents_unbind_device(), which +  * may sleep, in an interrupts-disabled context. So, we intentionally +  * don't call hv_stimer_cleanup(0) here. +  */ + + hv_synic_disable_regs(0); + + return 0; + + hv_synic_enable_regs(0); + + /* +  * Note: we don't need to call hv_stimer_init(0), because the timer +  * on CPU0 is not unbound in hv_synic_suspend(), and the timer is +  * automatically re-enabled in timekeeping_resume(). +  */ + + .suspend = hv_synic_suspend, + .resume = hv_synic_resume, + + register_syscore_ops(&hv_synic_syscore_ops); + + unregister_syscore_ops(&hv_synic_syscore_ops); +"

tockens = patch_diff.split('+ ')

function_name=[]
return_types = ["int","char","void","float","double","short"]

for t in tockens:
    print(t)
    if '(' in t and ')' in t:
        tok = t.split(" ")
        # need try
        i=0
        if tok[i] == 'static':
            i+=1
        if tok[i] in return_types:
            if tok[i+1] == '*':
                i+=2
            else:
                i+=1
        elif tok[i]  == 'struct':
            i+=2
        function = tok[i]


EMPTY_TREE_SHA   = "4b825dc642cb6eb9a060e54bf8d69288fbee4904"

#parse maintainers file to get hyperV files
print("[Info] parsing maintainers files")
fileList = parseMaintainers(cst.PathToBionic)
print("[Info] Received HyperV file paths")
fileNames = sanitizeFileNames(fileList)

fifty_first_commits = list(repo.iter_commits('master',paths=fileNames))
print(len(fifty_first_commits))
#print(fifty_first_commits)

diff_list = []
last_commit = None
for commit in fifty_first_commits:
    if last_commit is not None:
        diff_list.append(commit.diff(last_commit))
    last_commit = commit

for diff_item in diff_list:
    print("A blob:\n{}".format(diff_item.a_blob.data_stream.read().decode('utf-8')))
    print("B blob:\n{}".format(diff_item.b_blob.data_stream.read().decode('utf-8'))) 