#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""This module serves the path structure of the Check_MK environment
to all components of Check_MK."""

import os
from pathlib import Path
from typing import Union


# One bright day, when every path is really a Path, this can die... :-)
def _path(*args: Union[str, Path]) -> str:
    return str(Path(*args))


def _omd_path(path: str) -> Path:
    return omd_root / path


def _omd_path_str(path: str) -> str:
    return str(_omd_path(path))


def _local_path(global_path: Union[str, Path]) -> Path:
    return Path(_path(omd_root, "local", Path(global_path).relative_to(omd_root)))


# TODO: Add active_checks_dir and use it in code

omd_root = Path(os.environ.get("OMD_ROOT", ""))

_opt_root = "/opt" / omd_root.relative_to(omd_root.root)
rrd_multiple_dir = _opt_root / "var/pnp4nagios/perfdata"
rrd_single_dir = _opt_root / "var/check_mk/rrd"

mkbackup_lock_dir = Path("/run/lock/mkbackup")
trusted_ca_file = _omd_path("var/ssl/ca-certificates.crt")
root_cert_file = _omd_path("etc/ssl/ca.pem")
site_cert_file = _omd_path(f"etc/ssl/sites/{os.environ.get('OMD_SITE')}.pem")
default_config_dir = _omd_path_str("etc/check_mk")
main_config_file = _omd_path_str("etc/check_mk/main.mk")
final_config_file = _omd_path_str("etc/check_mk/final.mk")
local_config_file = _omd_path_str("etc/check_mk/local.mk")
check_mk_config_dir = _omd_path_str("etc/check_mk/conf.d")
modules_dir = _omd_path_str("share/check_mk/modules")
var_dir = _omd_path_str("var/check_mk")
log_dir = _omd_path_str("var/log")
precompiled_checks_dir = _omd_path_str("var/check_mk/precompiled_checks")
base_autochecks_dir = _omd_path_str("var/check_mk/autochecks")
core_helper_config_dir = _omd_path("var/check_mk/core/helper_config")
autochecks_dir = base_autochecks_dir
precompiled_hostchecks_dir = _omd_path_str("var/check_mk/precompiled")
snmpwalks_dir = _omd_path_str("var/check_mk/snmpwalks")
counters_dir = _omd_path_str("tmp/check_mk/counters")
tcp_cache_dir = _omd_path_str("tmp/check_mk/cache")
data_source_cache_dir = _omd_path_str("tmp/check_mk/data_source_cache")
snmp_scan_cache_dir = _omd_path_str("tmp/check_mk/snmp_scan_cache")
include_cache_dir = _omd_path_str("tmp/check_mk/check_includes")
tmp_dir = _omd_path_str("tmp/check_mk")
logwatch_dir = _omd_path_str("var/check_mk/logwatch")
nagios_objects_file = _omd_path_str("etc/nagios/conf.d/check_mk_objects.cfg")
nagios_command_pipe_path = _omd_path_str("tmp/run/nagios.cmd")
check_result_path = _omd_path_str("tmp/nagios/checkresults")
nagios_status_file = _omd_path_str("tmp/nagios/status.dat")
nagios_conf_dir = _omd_path_str("etc/nagios/conf.d")
nagios_config_file = _omd_path_str("tmp/nagios/nagios.cfg")
nagios_startscript = _omd_path_str("etc/init.d/core")
nagios_binary = _omd_path_str("bin/nagios")
apache_config_dir = _omd_path_str("etc/apache")
htpasswd_file = _omd_path_str("etc/htpasswd")
livestatus_unix_socket = _omd_path_str("tmp/run/live")
livebackendsdir = _omd_path_str("share/check_mk/livestatus")
inventory_output_dir = _omd_path_str("var/check_mk/inventory")
inventory_archive_dir = _omd_path_str("var/check_mk/inventory_archive")
inventory_delta_cache_dir = _omd_path_str("var/check_mk/inventory_delta_cache")
status_data_dir = _omd_path_str("tmp/check_mk/status_data")
robotmk_var_dir = _omd_path_str("var/robotmk")
base_discovered_host_labels_dir = _omd_path("var/check_mk/discovered_host_labels")
discovered_host_labels_dir = base_discovered_host_labels_dir
piggyback_dir = Path(tmp_dir, "piggyback")
piggyback_source_dir = Path(tmp_dir, "piggyback_sources")
profile_dir = Path(var_dir, "web")
crash_dir = Path(var_dir, "crashes")
diagnostics_dir = Path(var_dir, "diagnostics")
site_config_dir = Path(var_dir, "site_configs")

share_dir = _omd_path_str("share/check_mk")
checks_dir = _omd_path_str("share/check_mk/checks")
notifications_dir = _omd_path("share/check_mk/notifications")
inventory_dir = _omd_path_str("share/check_mk/inventory")
check_manpages_dir = _omd_path_str("share/check_mk/checkman")
agents_dir = _omd_path_str("share/check_mk/agents")
web_dir = _omd_path_str("share/check_mk/web")
pnp_templates_dir = _omd_path("share/check_mk/pnp-templates")
doc_dir = _omd_path("share/doc/check_mk")
locale_dir = _omd_path("share/check_mk/locale")
bin_dir = _omd_path_str("bin")
lib_dir = _omd_path_str("lib")
mib_dir = _omd_path("share/snmp/mibs")
optional_packages_dir = _omd_path("share/check_mk/optional_packages")
disabled_packages_dir = _omd_path("var/check_mk/disabled_packages")
protocols_dir = _omd_path("share/protocols")
alert_handlers_dir = _omd_path("share/check_mk/alert_handlers")

_base_plugins_dir = Path(lib_dir, "check_mk", "base", "plugins")
agent_based_plugins_dir = _base_plugins_dir / "agent_based"

gui_plugins_dir = Path(lib_dir, "check_mk", "gui", "plugins")

local_share_dir = _local_path(share_dir)
local_checks_dir = _local_path(checks_dir)
local_agent_based_plugins_dir = _local_path(agent_based_plugins_dir)
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
local_alert_handlers_dir = _local_path(alert_handlers_dir)

local_agent_based_plugins_dir = _local_path(agent_based_plugins_dir)
local_gui_plugins_dir = _local_path(gui_plugins_dir)

license_usage_dir = Path(var_dir, "license_usage")

# Agent registration paths
received_outputs_dir = Path(omd_root, "var/agent-receiver/received-outputs")
data_source_push_agent_dir = Path(data_source_cache_dir, "push-agent")
_r4r_base_dir = Path(var_dir, "wato/requests-for-registration")
r4r_new_dir = _r4r_base_dir.joinpath("NEW")
r4r_pending_dir = _r4r_base_dir.joinpath("PENDING")
r4r_declined_dir = _r4r_base_dir.joinpath("DECLINED")
r4r_declined_bundles_dir = _r4r_base_dir.joinpath("DECLINED-BUNDLES")
r4r_ready_dir = _r4r_base_dir.joinpath("READY")
r4r_discoverable_dir = _r4r_base_dir.joinpath("DISCOVERABLE")


def make_experimental_config_file() -> Path:
    """Returns file with experimental settings to be used.
    Used to enable features which is "in development" and not good enough to be enabled by default.
    Example of experimental.mk:
    config_storage_format = "raw"
    """
    return Path(default_config_dir) / "experimental.mk"
