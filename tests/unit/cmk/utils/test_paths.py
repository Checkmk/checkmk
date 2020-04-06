#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os
import sys

if sys.version_info[0] >= 3:
    from pathlib import Path  # pylint: disable=import-error,unused-import
else:
    from pathlib2 import Path  # pylint: disable=import-error,unused-import

from testlib import repo_path, import_module

pathlib_paths = [
    "core_discovered_host_labels_dir",
    "base_discovered_host_labels_dir",
    "discovered_host_labels_dir",
    "piggyback_dir",
    "piggyback_source_dir",
    "notifications_dir",
    "pnp_templates_dir",
    "doc_dir",
    "locale_dir",
    "mib_dir",
    "crash_dir",
    "optional_packages_dir",
    "local_share_dir",
    "local_checks_dir",
    "local_notifications_dir",
    "local_inventory_dir",
    "local_check_manpages_dir",
    "local_agents_dir",
    "local_web_dir",
    "local_pnp_templates_dir",
    "local_doc_dir",
    "local_locale_dir",
    "local_bin_dir",
    "local_lib_dir",
    "local_mib_dir",
    "agent_based_plugins_dir",
    "local_agent_based_plugins_dir",
    "diagnostics_dir",
]


def _check_paths(root, module):
    for var, value in module.__dict__.items():
        if not var.startswith("_") and var not in ('Path', 'os', 'sys', 'Union'):
            if var in pathlib_paths:
                assert isinstance(value, Path)
                assert str(value).startswith(root)
            else:
                assert isinstance(value, str)
                # TODO: Differentiate in a more clever way between /omd and /opt paths
                assert value.startswith(root) or value.startswith("/opt")


def test_paths_in_omd_and_opt_root(monkeypatch):

    omd_root = '/omd/sites/dingeling'
    with monkeypatch.context() as m:
        m.setitem(os.environ, 'OMD_ROOT', omd_root)
        test_paths = import_module("%s/cmk/utils/paths.py" % repo_path())
        _check_paths(omd_root, test_paths)
