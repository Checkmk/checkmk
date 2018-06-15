"""(Almost) all files in this directory are being imported.

All files whose names up to the first dot are not in EXCLUDES below are being
imported as a submodule (referred to as 'dataset'). In particular, files
starting with a '.' are ignored.
The required variables for a dataset are described in the generictests module.
"""
import os as _os
from importlib import import_module as _import


EXCLUDES = ('', '__init__', 'conftest')


DATASET_NAMES = {_os.path.splitext(_f)[0] for _f
                 in _os.listdir(_os.path.dirname(__file__))
                 if _f.split('.')[0] not in EXCLUDES}


for _m in sorted(DATASET_NAMES):
    _import("%s.%s" % (__name__, _m))


