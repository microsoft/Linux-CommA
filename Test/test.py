import os,sys,inspect
currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0,parentdir) 
from DatabaseDriver.UpstreamPatchTable import UpstreamPatchTable

def test_get_code_matching():
    UpstreamPatchTable = UpstreamPatchTable()
    up_list = UpstreamPatchTable.get_upstream_patch()
    dw_list = 