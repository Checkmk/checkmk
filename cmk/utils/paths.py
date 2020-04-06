#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""This module serves the path structure of the Check_MK environment
to all components of Check_MK."""

import sys
import os

from typing import Union  # pylint: disable=unused-import

# Explicitly check for Python 3 (which is understood by mypy)
if sys.version_info[0] >= 3:
    from pathlib import Path  # pylint: disable=import-error
else:
    from pathlib2 import Path


# One bright day, when every path is really a Path, this can die... :-)
def _path(*args):
    # type: (*Union[str, Path]) -> str
    return str(Path(*args))


def _omd_path(path):
    # type: (str) -> str
    return _path(omd_root, path)


def _local_path(global_path):
    # type: (Union[str, Path]) -> Path
    return Path(_path(omd_root, "local", Path(global_path).relative_to(omd_root)))


# TODO: Add active_checks_dir and use it in code

omd_root = _path(os.environ.get("OMD_ROOT", ""))
opt_root = _path("/opt" + omd_root)

default_config_dir = _omd_path("etc/check_mk")
main_config_file = _omd_path("etc/check_mk/main.mk")
final_config_file = _omd_path("etc/check_mk/final.mk")
local_config_file = _omd_path("etc/check_mk/local.mk")
check_mk_config_dir = _omd_path("etc/check_mk/conf.d")
modules_dir = _omd_path("share/check_mk/modules")
var_dir = _omd_path("var/check_mk")
log_dir = _omd_path("var/log")
precompiled_checks_dir = _omd_path("var/check_mk/precompiled_checks")
core_autochecks_dir = _omd_path("var/check_mk/core/autochecks")
base_autochecks_dir = _omd_path("var/check_mk/autochecks")
autochecks_dir = base_autochecks_dir
precompiled_hostchecks_dir = _omd_path("var/check_mk/precompiled")
snmpwalks_dir = _omd_path("var/check_mk/snmpwalks")
counters_dir = _omd_path("tmp/check_mk/counters")
tcp_cache_dir = _omd_path("tmp/check_mk/cache")
data_source_cache_dir = _omd_path("tmp/check_mk/data_source_cache")
snmp_scan_cache_dir = _omd_path("tmp/check_mk/snmp_scan_cache")
include_cache_dir = _omd_path("tmp/check_mk/check_includes")
tmp_dir = _omd_path("tmp/check_mk")
logwatch_dir = _omd_path("var/check_mk/logwatch")
nagios_objects_file = _omd_path("etc/nagios/conf.d/check_mk_objects.cfg")
nagios_command_pipe_path = _omd_path("tmp/run/nagios.cmd")
check_result_path = _omd_path("tmp/nagios/checkresults")
nagios_status_file = _omd_path("tmp/nagios/status.dat")
nagios_conf_dir = _omd_path("etc/nagios/conf.d")
nagios_config_file = _omd_path("tmp/nagios/nagios.cfg")
nagios_startscript = _omd_path("etc/init.d/core")
nagios_binary = _omd_path("bin/nagios")
apache_config_dir = _omd_path("etc/apache")
htpasswd_file = _omd_path("etc/htpasswd")
livestatus_unix_socket = _omd_path("tmp/run/live")
pnp_rraconf_dir = _omd_path("share/check_mk/pnp-rraconf")
livebackendsdir = _omd_path("share/check_mk/livestatus")
inventory_output_dir = _omd_path("var/check_mk/inventory")
inventory_archive_dir = _omd_path("var/check_mk/inventory_archive")
status_data_dir = _omd_path("tmp/check_mk/status_data")
core_discovered_host_labels_dir = Path(_omd_path("var/check_mk/core/discovered_host_labels"))
base_discovered_host_labels_dir = Path(_omd_path("var/check_mk/discovered_host_labels"))
discovered_host_labels_dir = base_discovered_host_labels_dir
piggyback_dir = Path(tmp_dir, "piggyback")
piggyback_source_dir = Path(tmp_dir, "piggyback_sources")
crash_dir = Path(var_dir, "crashes")
diagnostics_dir = Path(var_dir, "diagnostics")

share_dir = _omd_path("share/check_mk")
checks_dir = _omd_path("share/check_mk/checks")
notifications_dir = Path(_omd_path("share/check_mk/notifications"))
inventory_dir = _omd_path("share/check_mk/inventory")
check_manpages_dir = _omd_path("share/check_mk/checkman")
agents_dir = _omd_path("share/check_mk/agents")
web_dir = _omd_path("share/check_mk/web")
pnp_templates_dir = Path(_omd_path("share/check_mk/pnp-templates"))
doc_dir = Path(_omd_path("share/doc/check_mk"))
locale_dir = Path(_omd_path("share/check_mk/locale"))
bin_dir = _omd_path("bin")
lib_dir = _omd_path("lib")
mib_dir = Path(_omd_path("share/snmp/mibs"))
optional_packages_dir = Path(_omd_path("share/check_mk/optional_packages"))

_base_plugins_dir = Path(lib_dir, "check_mk", "base", "plugins")
agent_based_plugins_dir = _base_plugins_dir / "agent_based"

local_share_dir = _local_path(share_dir)
local_checks_dir = _local_path(checks_dir)
local_notifications_dir = _local_path(notifications_dir)
local_inventory_dir = _local_path(inventory_dir)
local_check_manpages_dir = _local_path(check_manpages_dir)
local_agents_dir = _local_path(agents_dir)
local_web_dir = _local_path(web_dir)
local_pnp_templates_dir = _local_path(pnp_templates_dir)
local_doc_dir = _local_path(doc_dir)
local_locale_dir = _local_path(locale_dir)
local_bin_dir = _local_path(bin_dir)
local_lib_dir = _local_path(lib_dir)
local_mib_dir = _local_path(mib_dir)

_local_base_plugins_dir = Path(local_lib_dir, "check_mk", "base", "plugins")
local_agent_based_plugins_dir = _local_base_plugins_dir / "agent_based"
