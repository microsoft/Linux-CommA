import os,sys,inspect
currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0,parentdir) 
from DatabaseDriver.UpstreamPatchTable import UpstreamPatchTable

db = UpstreamPatchTable()
Ulist = db.get_upstream_patch()
print(len(Ulist))