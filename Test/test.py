import os,sys,inspect
currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0,parentdir) 
from DatabaseDriver.PatchDataTable import PatchDataTable

def test_get_code_matching():
    PatchDataTable = PatchDataTable()
    up_list = PatchDataTable.get_upstream_patch()
    # dw_list = 