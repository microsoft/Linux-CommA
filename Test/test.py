import inspect
import os
import sys

from DatabaseDriver.PatchDataDriver import PatchDataDriver

currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0, parentdir)


def test_get_code_matching():
    PatchDataDriver = PatchDataDriver()
    up_list = PatchDataDriver.get_upstream_patch()
    # dw_list =
