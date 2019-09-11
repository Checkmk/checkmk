#!/usr/bin/python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2016             mk@mathias-kettner.de |
# +------------------------------------------------------------------+
#
# This file is part of Check_MK.
# The official homepage is at http://mathias-kettner.de/check_mk.
#
# check_mk is free software;  you can redistribute it and/or modify it
# under the  terms of the  GNU General Public License  as published by
# the Free Software Foundation in version 2.  check_mk is  distributed
# in the hope that it will be useful, but WITHOUT ANY WARRANTY;  with-
# out even the implied warranty of  MERCHANTABILITY  or  FITNESS FOR A
# PARTICULAR PURPOSE. See the  GNU General Public License for more de-
# tails. You should have  received  a copy of the  GNU  General Public
# License along with GNU Make; see the file  COPYING.  If  not,  write
# to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
# Boston, MA 02110-1301 USA.
"""This module serves the path structure of the Check_MK environment
to all components of Check_MK."""

import os

try:
    from pathlib import Path  # type: ignore
except ImportError:
    from pathlib2 import Path


# One bright day, when every path is really a Path, this can die... :-)
def _path(*args):
    return str(Path(*args))


def _omd_path(path):
    return _path(omd_root, path)


def _local_path(global_path):
    return _path(omd_root, "local", Path(global_path).relative_to(omd_root))


# TODO: Add active_checks_dir and use it in code

omd_root = _path(os.environ.get("OMD_ROOT", ""))

default_config_dir = _omd_path("etc/check_mk")
main_config_file = _omd_path("etc/check_mk/main.mk")
final_config_file = _omd_path("etc/check_mk/final.mk")
local_config_file = _omd_path("etc/check_mk/local.mk")
check_mk_config_dir = _omd_path("etc/check_mk/conf.d")
modules_dir = _omd_path("share/check_mk/modules")
var_dir = _omd_path("var/check_mk")
log_dir = _omd_path("var/log")
precompiled_checks_dir = _omd_path("var/check_mk/precompiled_checks")
autochecks_dir = _omd_path("var/check_mk/autochecks")
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
discovered_host_labels_dir = Path(_omd_path("var/check_mk/discovered_host_labels"))
piggyback_dir = Path(tmp_dir, "piggyback")
piggyback_source_dir = Path(tmp_dir, "piggyback_sources")

share_dir = _omd_path("share/check_mk")
checks_dir = _omd_path("share/check_mk/checks")
notifications_dir = _omd_path("share/check_mk/notifications")
inventory_dir = _omd_path("share/check_mk/inventory")
check_manpages_dir = _omd_path("share/check_mk/checkman")
agents_dir = _omd_path("share/check_mk/agents")
web_dir = _omd_path("share/check_mk/web")
pnp_templates_dir = _omd_path("share/check_mk/pnp-templates")
doc_dir = _omd_path("share/doc/check_mk")
locale_dir = _omd_path("share/check_mk/locale")
bin_dir = _omd_path("bin")
lib_dir = _omd_path("lib")
mib_dir = Path(_omd_path("share/snmp/mibs"))

local_share_dir = Path(_local_path(share_dir))
local_checks_dir = Path(_local_path(checks_dir))
local_notifications_dir = Path(_local_path(notifications_dir))
local_inventory_dir = Path(_local_path(inventory_dir))
local_check_manpages_dir = Path(_local_path(check_manpages_dir))
local_agents_dir = Path(_local_path(agents_dir))
local_web_dir = Path(_local_path(web_dir))
local_pnp_templates_dir = Path(_local_path(pnp_templates_dir))
local_doc_dir = Path(_local_path(doc_dir))
local_locale_dir = Path(_local_path(locale_dir))
local_bin_dir = Path(_local_path(bin_dir))
local_lib_dir = Path(_local_path(lib_dir))
local_mib_dir = Path(_local_path(mib_dir))
