#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import copy
from collections.abc import Callable, Mapping
from logging import Logger
from pathlib import Path
from typing import Any

from cmk.utils import debug
from cmk.utils.exceptions import MKGeneralException
from cmk.utils.hostaddress import HostName
from cmk.utils.paths import autochecks_dir
from cmk.utils.rulesets.definition import RuleGroup

from cmk.checkengine.checking import CheckPluginName
from cmk.checkengine.discovery import AutocheckEntry, AutochecksStore
from cmk.checkengine.legacy import LegacyCheckParameters

from cmk.base.api.agent_based import register

from cmk.gui.watolib.rulesets import AllRulesets, Ruleset, RulesetCollection

from cmk.update_config.plugins.actions.replaced_check_plugins import REPLACED_CHECK_PLUGINS
from cmk.update_config.registry import update_action_registry, UpdateAction
from cmk.update_config.update_state import UpdateActionState

# some autocheck parameters need transformation even though there is no ruleset.
_EXPLICIT_DISCOVERED_PARAMETERS_TRANSFORMS: Mapping[
    CheckPluginName,
    Callable[
        [Any],  # should be LegacyCheckParameters, but this makes writing transforms cumbersome ...
        LegacyCheckParameters,
    ],
] = {
    CheckPluginName("aironet_clients"): (lambda p: {}),
    CheckPluginName("aironet_errors"): (lambda p: {}),
    CheckPluginName("alcatel_cpu_aos7"): (lambda p: {}),
    CheckPluginName("alcatel_cpu"): (lambda p: {}),
    CheckPluginName("allnet_ip_sensoric_humidity"): (lambda p: {}),
    CheckPluginName("apc_ats_status"): (
        lambda p: p if isinstance(p, dict) else {"power_source": p}
    ),
    CheckPluginName("apc_inrow_airflow"): (lambda p: {}),
    CheckPluginName("apc_netbotz_sensors_humidity"): (lambda p: {}),
    CheckPluginName("arc_raid_status"): (lambda p: p if isinstance(p, dict) else {"n_disks": p}),
    CheckPluginName("arris_cmts_cpu"): (lambda p: {}),
    CheckPluginName("aws_ec2_security_groups"): (
        lambda p: p if isinstance(p, dict) else {"groups": p}
    ),
    CheckPluginName("blade_powerfan"): (lambda p: {}),
    CheckPluginName("brocade_fan"): (lambda p: {}),
    CheckPluginName("brocade_mlx_module_cpu"): (lambda p: {}),
    CheckPluginName("brocade_mlx_module_mem"): (lambda p: {}),
    CheckPluginName("bvip_util"): (lambda p: {}),
    CheckPluginName("cisco_hsrp"): (
        lambda p: p if not isinstance(p, tuple) else {"group": p[0], "state": p[1]}
    ),
    CheckPluginName("cpsecure_sessions"): (lambda p: {}),
    CheckPluginName("decru_fans"): (lambda p: {}),
    CheckPluginName("decru_perf"): (lambda p: {}),
    CheckPluginName("dell_powerconnect_cpu"): (lambda p: {}),
    CheckPluginName("drbd_disk"): (lambda p: {}),
    # this is unreadable, but since we remove it soon I don't bother to rewrite it
    CheckPluginName("drbd"): (
        lambda p: p
        if isinstance(p, dict)
        else {
            "roles_inventory": p[0] and p[0] or None,
            "diskstates_inventory": (p[0] and p[1]) and p[1] or None,
        }
    ),
    CheckPluginName("drbd_net"): (lambda p: {}),
    CheckPluginName("drbd_stats"): (lambda p: {}),
    CheckPluginName("emc_vplex_cpu"): (lambda p: {}),
    CheckPluginName("emerson_stat"): (lambda p: {}),
    CheckPluginName("f5_bigip_chassis_temp"): (lambda p: {}),
    CheckPluginName("f5_bigip_cpu_temp"): (lambda p: {}),
    CheckPluginName("f5_bigip_fans"): (lambda p: {}),
    CheckPluginName("fortigate_memory"): (lambda p: {}),
    CheckPluginName("fortigate_node_cpu"): (lambda p: {}),
    CheckPluginName("fsc_subsystems"): (lambda p: {}),
    CheckPluginName("genua_pfstate"): (lambda p: {}),
    CheckPluginName("gude_humidity"): (lambda p: {}),
    CheckPluginName("hitachi_hnas_cpu"): (lambda p: {}),
    CheckPluginName("hitachi_hnas_fpga"): (lambda p: {}),
    CheckPluginName("hp_blade_manager"): (lambda p: p if isinstance(p, dict) else {"role": p[0]}),
    CheckPluginName("hp_procurve_cpu"): (lambda p: {}),
    CheckPluginName("ibm_svc_nodestats_cpu_util"): (lambda p: {}),
    CheckPluginName("innovaphone_channels"): (lambda p: {}),
    CheckPluginName("innovaphone_licenses"): (lambda p: {}),
    CheckPluginName("isc_dhcpd"): (lambda p: {}),
    CheckPluginName("jolokia_metrics_app_sess"): (lambda p: {}),
    CheckPluginName("jolokia_metrics_bea_sess"): (lambda p: {}),
    CheckPluginName("kentix_amp_sensors_smoke"): (lambda p: {}),
    CheckPluginName("liebert_bat_temp"): (lambda p: {}),
    CheckPluginName("mbg_lantime_ng_refclock_gps"): (lambda p: {}),
    CheckPluginName("mbg_lantime_refclock"): (lambda p: {}),
    CheckPluginName("mem_vmalloc"): (lambda p: {}),
    CheckPluginName("msexch_dag_dbcopy"): (
        lambda p: p if isinstance(p, dict) else {"inv_key": p[0], "inv_val": p[1]}
    ),
    CheckPluginName("netctr_combined"): (lambda p: {}),
    CheckPluginName("papouch_th2e_sensors_humidity"): (lambda p: {}),
    CheckPluginName("siemens_plc_flag"): (lambda p: {}),
    CheckPluginName("strem1_sensors"): (lambda p: {}),
    CheckPluginName("stulz_humidity"): (lambda p: {}),
    CheckPluginName("sylo"): (lambda p: {}),
    CheckPluginName("tsm_scratch"): (lambda p: {}),
    CheckPluginName("tsm_sessions"): (lambda p: {}),
    CheckPluginName("vxvm_objstatus"): (lambda p: {}),
    CheckPluginName("wut_webtherm_humidity"): (lambda p: {}),
}


class UpdateAutochecks(UpdateAction):
    def __call__(self, logger: Logger, update_action_state: UpdateActionState) -> None:
        failed_hosts = []

        all_rulesets = AllRulesets.load_all_rulesets()

        for autocheck_file in Path(autochecks_dir).glob("*.mk"):
            hostname = HostName(autocheck_file.stem)
            store = AutochecksStore(hostname)

            try:
                autochecks = store.read()
            except MKGeneralException as exc:
                if debug.enabled():
                    raise
                logger.error(str(exc))
                failed_hosts.append(hostname)
                continue

            store.write([_fix_entry(logger, s, all_rulesets, hostname) for s in autochecks])

        if failed_hosts:
            msg = f"Failed to rewrite autochecks file for hosts: {', '.join(failed_hosts)}"
            logger.error(msg)
            raise MKGeneralException(msg)


update_action_registry.register(
    UpdateAutochecks(
        name="autochecks",
        title="Autochecks",
        sort_index=40,
    )
)


def _fix_entry(
    logger: Logger,
    entry: AutocheckEntry,
    all_rulesets: RulesetCollection,
    hostname: str,
) -> AutocheckEntry:
    """Change names of removed plugins to the new ones and transform parameters"""
    new_plugin_name = REPLACED_CHECK_PLUGINS.get(entry.check_plugin_name, entry.check_plugin_name)

    explicit_transform = _EXPLICIT_DISCOVERED_PARAMETERS_TRANSFORMS.get(
        new_plugin_name, lambda x: x
    )

    return AutocheckEntry(
        check_plugin_name=new_plugin_name,
        item=entry.item,
        parameters=_transformed_params(
            logger,
            new_plugin_name or entry.check_plugin_name,
            explicit_transform(entry.parameters),
            all_rulesets,
            hostname,
        ),
        service_labels=entry.service_labels,
    )


def _transformed_params(
    logger: Logger,
    plugin_name: CheckPluginName,
    params: LegacyCheckParameters,
    all_rulesets: RulesetCollection,
    hostname: str,
) -> LegacyCheckParameters:
    check_plugin = register.get_check_plugin(plugin_name)
    if check_plugin is None:
        return params

    ruleset_name = RuleGroup.CheckgroupParameters(f"{check_plugin.check_ruleset_name}")
    if ruleset_name not in all_rulesets.get_rulesets():
        return params

    debug_info = "host={!r}, plugin={!r}, ruleset={!r}, params={!r}".format(
        hostname,
        str(plugin_name),
        str(check_plugin.check_ruleset_name),
        params,
    )

    try:
        ruleset = all_rulesets.get_rulesets()[ruleset_name]
        new_params = _transform_params_safely(params, ruleset, ruleset_name, logger)

        assert new_params or not params, "non-empty params vanished"
        assert not isinstance(params, dict) or isinstance(new_params, dict), (
            "transformed params down-graded from dict: %r" % new_params
        )

        return new_params  # type: ignore[no-any-return]

    except Exception as exc:
        msg = f"Transform failed: {debug_info}, error={exc!r}"
        if debug.enabled():
            raise RuntimeError(msg) from exc
        logger.error(msg)

    return params


# TODO(sk): remove this safe-convert'n'check'n'warning after fixing all of transform_value
def _transform_params_safely(
    params: LegacyCheckParameters, ruleset: Ruleset, ruleset_name: str, logger: Logger
) -> Any:
    """Safely converts <params> using <transform_value> function
    Write warning in the log if <transform_value> alters input. Such behavior is not allowed and
    the warning helps us to detect bad legacy/old transform functions.
    Returns `Any` because valuespecs are currently Any
    """
    param_copy = copy.deepcopy(params)
    new_params = ruleset.valuespec().transform_value(param_copy) if params else {}
    if param_copy != params:
        logger.warning(f"transform_value() for ruleset '{ruleset_name}' altered input")
    return new_params
