#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""This module serves the path structure of the Check_MK environment
to all components of Check_MK."""

import os
from pathlib import Path

LOCAL_SEGMENT = "local"


def _omd_path(path: str) -> Path:
    return omd_root / path


def _local_path(global_path: str | Path) -> Path:
    return omd_root / LOCAL_SEGMENT / Path(global_path).relative_to(omd_root)


omd_root = Path(os.environ.get("OMD_ROOT", ""))

_opt_root = "/opt" / omd_root.relative_to(omd_root.root)
rrd_multiple_dir = _opt_root / "var/pnp4nagios/perfdata"
rrd_single_dir = _opt_root / "var/check_mk/rrd"

mkbackup_lock_dir = Path("/run/lock/mkbackup")
trusted_ca_file = _omd_path("var/ssl/ca-certificates.crt")
remote_sites_cas_dir = _omd_path("var/ssl/remote_sites_cas")
root_cert_file = _omd_path("etc/ssl/ca.pem")
agent_cas_dir = _omd_path("etc/ssl/agents")
relay_cas_dir = _omd_path("etc/ssl/relays")
agent_cert_store = _omd_path("etc/ssl/agent_cert_store.pem")
site_cert_file = _omd_path(f"etc/ssl/sites/{os.environ.get('OMD_SITE')}.pem")
default_config_dir = _omd_path("etc/check_mk")
main_config_file = _omd_path("etc/check_mk/main.mk")
final_config_file = _omd_path("etc/check_mk/final.mk")
local_config_file = _omd_path("etc/check_mk/local.mk")
check_mk_config_dir = _omd_path("etc/check_mk/conf.d")
modules_dir = _omd_path("share/check_mk/modules")

relative_var_dir = Path("var/check_mk")
var_dir = omd_root / relative_var_dir

log_dir = _omd_path("var/log")
precompiled_checks_dir = _omd_path("var/check_mk/precompiled_checks")
autochecks_dir = _omd_path("var/check_mk/autochecks")
precompiled_hostchecks_dir = _omd_path("var/check_mk/precompiled")

relative_snmpwalks_dir = Path("var/check_mk/snmpwalks")
snmpwalks_dir = omd_root / relative_snmpwalks_dir

relative_walk_cache_dir = Path("var/check_mk/snmp_cache")

relative_snmp_section_cache_dir = Path("var/check_mk/snmp_cached_sections")

counters_dir = _omd_path("tmp/check_mk/counters")

relative_tcp_cache_dir = Path("tmp/check_mk/cache")
tcp_cache_dir = omd_root / relative_tcp_cache_dir

relative_data_source_cache_dir = Path("tmp/check_mk/data_source_cache")
data_source_cache_dir = omd_root / relative_data_source_cache_dir

include_cache_dir = _omd_path("tmp/check_mk/check_includes")
relative_tmp_dir = Path("tmp/check_mk")
tmp_dir = omd_root / relative_tmp_dir
tmp_run_dir = _omd_path("tmp/run")
logwatch_dir = _omd_path("var/check_mk/logwatch")
nagios_objects_file = _omd_path("etc/nagios/conf.d/check_mk_objects.cfg")
nagios_command_pipe_path = _omd_path("tmp/run/nagios.cmd")
check_result_path = _omd_path("tmp/nagios/checkresults")
nagios_conf_dir = _omd_path("etc/nagios/conf.d")
nagios_config_file = _omd_path("tmp/nagios/nagios.cfg")
nagios_startscript = _omd_path("etc/init.d/core")
nagios_binary = _omd_path("bin/nagios")
nagios_resource_cfg = _omd_path("etc/nagios/resource.cfg")
htpasswd_file = _omd_path("etc/htpasswd")
livestatus_unix_socket = _omd_path("tmp/run/live")
raw_data_socket = _omd_path("tmp/run/raw-data")
base_discovered_host_labels_dir = _omd_path("var/check_mk/discovered_host_labels")
discovered_host_labels_dir = base_discovered_host_labels_dir
autodiscovery_dir = _omd_path("var/check_mk/autodiscovery")
profile_dir = var_dir / "web"
diagnostics_dir = var_dir / "diagnostics"
site_config_dir = var_dir / "site_configs"
visuals_cache_dir = tmp_dir / "visuals_cache"
predictions_dir = var_dir / "prediction"
user_messages_spool_dir = var_dir / "user_messages/spool"
diskspace_config_dir = default_config_dir / "diskspace.d/wato/"

cmc_objects_file = var_dir / "core/config"

configuration_lockfile = default_config_dir / "multisite.mk"

# persisted secret files
# avoid using these paths directly; use wrappers in cmk.util.crypto.secrets instead
# note that many of these paths are duplicated in code relating to snapshots and Activate Changes
#
auth_secret_file = omd_root / "etc/auth.secret"
# the path for password_store.secret is also duplicated in omd cmk_password_store.h!
password_store_secret_file = omd_root / "etc/password_store.secret"
site_internal_secret_file = omd_root / "etc/site_internal.secret"

share_dir = _omd_path("share/check_mk")
checks_dir = _omd_path("share/check_mk/checks")
cmk_addons_plugins_dir = _omd_path("lib/python3/cmk_addons/plugins")
cmk_plugins_dir = _omd_path("lib/python3/cmk/plugins")
notifications_dir = _omd_path("share/check_mk/notifications")
inventory_dir = _omd_path("share/check_mk/inventory")
legacy_check_manpages_dir = _omd_path("share/check_mk/checkman")
agents_dir = _omd_path("share/check_mk/agents")
relays_dir = _omd_path("share/check_mk/relays")
special_agents_dir = _omd_path("share/check_mk/agents/special")
web_dir = _omd_path("share/check_mk/web")
pnp_templates_dir = _omd_path("share/check_mk/pnp-templates")
doc_dir = _omd_path("share/doc/check_mk")
locale_dir = _omd_path("share/check_mk/locale")
bin_dir = _omd_path("bin")
lib_dir = _omd_path("lib")
optional_packages_dir = _omd_path("share/check_mk/optional_packages")
disabled_packages_dir = _omd_path("var/check_mk/disabled_packages")
installed_packages_dir = _omd_path("var/check_mk/packages")
protocols_dir = _omd_path("share/protocols")
alert_handlers_dir = _omd_path("share/check_mk/alert_handlers")

_base_plugins_dir = lib_dir / "python3/cmk/base/plugins"
agent_based_plugins_dir = _base_plugins_dir / "agent_based"

gui_plugins_dir = lib_dir / "python3/cmk/gui/plugins"
nagios_plugins_dir = lib_dir / "nagios/plugins"

local_root = _local_path(omd_root)
local_share_dir = _local_path(share_dir)
local_checks_dir = _local_path(checks_dir)
local_cmk_addons_plugins_dir = _local_path(cmk_addons_plugins_dir)
local_cmk_plugins_dir = _local_path(cmk_plugins_dir)
local_agent_based_plugins_dir = _local_path(agent_based_plugins_dir)
local_notifications_dir = _local_path(notifications_dir)
local_inventory_dir = _local_path(inventory_dir)
local_legacy_check_manpages_dir = _local_path(legacy_check_manpages_dir)
local_agents_dir = _local_path(agents_dir)
local_special_agents_dir = _local_path(special_agents_dir)
local_web_dir = _local_path(web_dir)
local_pnp_templates_dir = _local_path(pnp_templates_dir)
local_doc_dir = _local_path(doc_dir)
local_locale_dir = _local_path(locale_dir)
local_bin_dir = _local_path(bin_dir)
local_lib_dir = _local_path(lib_dir)
local_nagios_plugins_dir = _local_path(nagios_plugins_dir)
local_alert_handlers_dir = _local_path(alert_handlers_dir)
local_optional_packages_dir = _omd_path("var/check_mk/packages_local")
local_enabled_packages_dir = local_share_dir / "enabled_packages"

local_gui_plugins_dir = _local_path(gui_plugins_dir)
local_dashboards_dir = local_gui_plugins_dir / "dashboard"
local_views_dir = local_gui_plugins_dir / "views"
local_reports_dir = local_gui_plugins_dir / "reports"

licensing_dir = var_dir / "licensing"

# Agent registration paths
received_outputs_dir = omd_root / "var/agent-receiver/received-outputs"
uuid_lookup_dir = omd_root / "var/agent-receiver/uuid-lookup"
data_source_push_agent_dir = data_source_cache_dir / "push-agent"
_r4r_base_dir = var_dir / "wato/requests-for-registration"
r4r_new_dir = _r4r_base_dir.joinpath("NEW")
r4r_pending_dir = _r4r_base_dir.joinpath("PENDING")
r4r_declined_dir = _r4r_base_dir.joinpath("DECLINED")
r4r_declined_bundles_dir = _r4r_base_dir.joinpath("DECLINED-BUNDLES")
r4r_discoverable_dir = _r4r_base_dir.joinpath("DISCOVERABLE")


cse_config_dir = Path("/etc/cse")
