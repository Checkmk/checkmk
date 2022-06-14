#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os
from pathlib import Path
from typing import Final, Mapping

from tests.testlib import import_module, repo_path

_NON_STD_PREFIX: Mapping[str, str] = {
    "mkbackup_lock_dir": "/%.0s",
    "rrd_multiple_dir": "/opt%s",
    "rrd_single_dir": "/opt%s",
}

_STR_PATHS: Final = {
    "default_config_dir",
    "main_config_file",
    "final_config_file",
    "local_config_file",
    "check_mk_config_dir",
    "modules_dir",
    "var_dir",
    "log_dir",
    "precompiled_checks_dir",
    "base_autochecks_dir",
    "autochecks_dir",
    "precompiled_hostchecks_dir",
    "snmpwalks_dir",
    "counters_dir",
    "tcp_cache_dir",
    "data_source_cache_dir",
    "snmp_scan_cache_dir",
    "include_cache_dir",
    "tmp_dir",
    "logwatch_dir",
    "nagios_objects_file",
    "nagios_command_pipe_path",
    "check_result_path",
    "nagios_status_file",
    "nagios_conf_dir",
    "nagios_config_file",
    "nagios_startscript",
    "nagios_binary",
    "apache_config_dir",
    "htpasswd_file",
    "livestatus_unix_socket",
    "livebackendsdir",
    "inventory_output_dir",
    "inventory_archive_dir",
    "inventory_delta_cache_dir",
    "status_data_dir",
    "robotmk_html_log_dir",
    "share_dir",
    "checks_dir",
    "inventory_dir",
    "check_manpages_dir",
    "agents_dir",
    "web_dir",
    "lib_dir",
}


_IGNORED_VARS = {"Path", "os", "sys", "Union"}


def _ignore(varname: str) -> bool:
    return varname.startswith(("_", "make_")) or varname in _IGNORED_VARS


def _check_paths(root: str, namespace_dict: Mapping[str, object]) -> None:
    for var, value in namespace_dict.items():

        if _ignore(var):
            continue

        if var in _STR_PATHS:
            assert isinstance(value, str)
            assert value.startswith(root)
            continue

        assert isinstance(value, Path)
        required_prefix = _NON_STD_PREFIX.get(var, "%s") % root
        assert str(value).startswith(required_prefix), repr((var, value, required_prefix))


def test_paths_in_omd_and_opt_root(monkeypatch) -> None:

    omd_root = "/omd/sites/dingeling"
    with monkeypatch.context() as m:
        m.setitem(os.environ, "OMD_ROOT", omd_root)
        test_paths = import_module("%s/cmk/utils/paths.py" % repo_path())
        _check_paths(omd_root, test_paths.__dict__)
