#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os
from collections.abc import Mapping
from pathlib import Path

from pytest import MonkeyPatch

from tests.testlib.unit.utils import import_module_hack

import cmk.utils.paths

_NON_STD_PREFIX: Mapping[str, str] = {
    "mkbackup_lock_dir": "/%.0s",
    "rrd_multiple_dir": "/opt%s",
    "rrd_single_dir": "/opt%s",
}


_IGNORED_VARS = {"Path", "os", "cse_config_dir", "sys", "Union", "LOCAL_SEGMENT"}


def _ignore(varname: str) -> bool:
    return varname.startswith(("_", "make_")) or varname in _IGNORED_VARS


def _check_paths(root: str, namespace_dict: Mapping[str, object]) -> None:
    for var, value in namespace_dict.items():
        if _ignore(var):
            continue

        assert isinstance(value, Path)
        required_prefix = _NON_STD_PREFIX.get(var, "%s") % root
        assert str(value).startswith(required_prefix), repr((var, value, required_prefix))


def test_paths_in_omd_and_opt_root(monkeypatch: MonkeyPatch) -> None:
    omd_root = "/omd/sites/dingeling"
    with monkeypatch.context() as m:
        m.setitem(os.environ, "OMD_ROOT", omd_root)
        test_paths = import_module_hack(cmk.utils.paths.__file__)
        _check_paths(omd_root, test_paths.__dict__)
