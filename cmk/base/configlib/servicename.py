#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-any-return"

import contextlib
from collections.abc import Callable, Container, Mapping, Sequence
from typing import Final

from cmk.ccc.hostaddress import HostName
from cmk.checkengine.plugins import CheckPluginName, ServiceID
from cmk.utils.caching import cache_manager
from cmk.utils.labels import LabelManager, Labels
from cmk.utils.rulesets.ruleset_matcher import RulesetMatcher, RuleSpec
from cmk.utils.servicename import Item, ServiceName
from cmk.utils.translations import (
    parse_translation_options,
    translate_service_description,
    TranslationOptions,
)

from .loaded_config import LoadedConfigFragment


class FinalServiceNameConfig:
    def __init__(
        self,
        matcher: RulesetMatcher,
        illegal_chars: str,
        translations: Sequence[RuleSpec[Mapping[str, object]]],
    ) -> None:
        self._matcher: Final = matcher
        self._illegal_chars: Final = illegal_chars
        self._translations: Final = translations

    def __call__(
        self,
        host_name: HostName,
        description: ServiceName,
        labels_of_host: Callable[[HostName], Labels],
    ) -> ServiceName:
        translations = self._get_service_translations(labels_of_host, host_name)
        # Note: at least strip the service name.
        # Some plugins introduce trailing whitespaces, but Nagios silently drops leading
        # and trailing spaces in the configuration file.
        description = (
            translate_service_description(translations, description).strip()
            if translations
            else description.strip()
        )

        # Sanitize: remove illegal characters from a service name
        cache = cache_manager.obtain_cache("final_service_description")
        with contextlib.suppress(KeyError):
            return cache[description]

        return cache.setdefault(
            description,
            "".join(c for c in description if c not in self._illegal_chars).rstrip("\\"),
        )

    def _get_service_translations(
        self,
        labels_of_host: Callable[[HostName], Labels],
        hostname: HostName,
    ) -> TranslationOptions:
        translations_cache = cache_manager.obtain_cache("service_description_translations")
        with contextlib.suppress(KeyError):
            return translations_cache[hostname]

        rules = self._matcher.get_host_values_all(hostname, self._translations, labels_of_host)
        merged = TranslationOptions(case=None, drop_domain=False, regex=[], mapping=[])
        for rule in rules[::-1]:
            parsed_rule = parse_translation_options(rule)
            if "case" in rule:  # inheritence! Don't check for "case" in parsed_rule!
                merged["case"] = parsed_rule["case"]
            merged["regex"] = list(set(merged["regex"]) | set(parsed_rule["regex"]))
            merged["mapping"] = list(set(merged["mapping"]) | set(parsed_rule["mapping"]))

        return translations_cache.setdefault(hostname, parse_translation_options(merged))


def make_final_service_name_config(
    loaded_config: LoadedConfigFragment,
    matcher: RulesetMatcher,
) -> FinalServiceNameConfig:
    return FinalServiceNameConfig(
        matcher=matcher,
        illegal_chars=(
            loaded_config.cmc_illegal_chars
            if loaded_config.monitoring_core == "cmc"
            else loaded_config.nagios_illegal_chars
        ),
        translations=loaded_config.service_description_translation,
    )


class PassiveServiceNameConfig:
    def __init__(
        self,
        final_service_name_config: Callable[
            [HostName, ServiceName, Callable[[HostName], Labels]], ServiceName
        ],
        user_defined_service_names: Mapping[str, str],
        use_new_names_for: Container[str],
        labels_of_host: Callable[[HostName], Labels],
    ):
        self._final_service_name_config: Final = final_service_name_config
        self._user_defined_service_names: Final = user_defined_service_names
        self._use_new_names_for: Final = use_new_names_for
        self._labels_of_host: Final = labels_of_host

    def __call__(
        self,
        host_name: HostName,
        service_id: ServiceID,
        service_name_template: str | None,
    ) -> ServiceName:
        if service_name_template is None:
            return (
                f"Unimplemented check {service_id.name} / {service_id.item}"
                if service_id.item
                else f"Unimplemented check {service_id.name}"
            )

        return self._final_service_name_config(
            host_name,
            _format_item_with_template(
                *self._get_service_description_template_and_item(
                    service_id.name, service_name_template, service_id.item
                )
            ),
            self._labels_of_host,
        )

    def _get_service_description_template_and_item(
        self, plugin_name: CheckPluginName, service_name_template: str, item: Item
    ) -> tuple[ServiceName, Item]:
        plugin_name_str = str(plugin_name)

        # use user-supplied service name, if available
        if descr_format := self._user_defined_service_names.get(plugin_name_str):
            return descr_format, item

        old_descr = _OLD_SERVICE_DESCRIPTIONS.get(plugin_name_str)
        if old_descr is None or plugin_name_str in self._use_new_names_for:
            return service_name_template, item
        return old_descr(item)


def make_passive_service_name_config(
    loaded_config: LoadedConfigFragment,
    matcher: RulesetMatcher,
    label_manager: LabelManager,
) -> PassiveServiceNameConfig:
    return PassiveServiceNameConfig(
        final_service_name_config=FinalServiceNameConfig(
            matcher=matcher,
            illegal_chars=(
                loaded_config.cmc_illegal_chars
                if loaded_config.monitoring_core == "cmc"
                else loaded_config.nagios_illegal_chars
            ),
            translations=loaded_config.service_description_translation,
        ),
        user_defined_service_names=loaded_config.service_descriptions,
        use_new_names_for=loaded_config.use_new_descriptions_for,
        labels_of_host=label_manager.labels_of_host,
    )


def _format_item_with_template(template: str, item: Item) -> str:
    """
    >>> _format_item_with_template("Foo", None)
    'Foo'
    >>> _format_item_with_template("Foo %s", None)
    'Foo <missing an item>'
    >>> _format_item_with_template("Foo", "bar")
    'Foo bar'
    >>> _format_item_with_template("Foo %s", "bar")
    'Foo bar'
    """
    try:
        return template % ("<missing an item>" if item is None else item)
    except TypeError:
        return f"{template} {item or ''}".strip()


# Renaming of service names while keeping backward compatibility with
# existing installations.
# Synchronize with htdocs/wato.py and plugins/wato/check_mk_configuration.py!


# Cleanup! .. some day
def _get_old_cmciii_temp_description(item: Item) -> tuple[ServiceName, None]:
    if item is None:
        raise TypeError()

    if "Temperature" in item:
        return item, None  # old item format, no conversion

    parts = item.split(" ")
    if parts[0] == "Ambient":
        return f"{parts[1]} Temperature", None

    if len(parts) == 2:
        return f"{parts[1]} {parts[0]}.Temperature", None

    if parts[1] == "LCP":
        parts[1] = "Liquid_Cooling_Package"
    return f"{parts[1]} {parts[0]}.{parts[2]}-Temperature", None


_OLD_SERVICE_DESCRIPTIONS: Mapping[str, Callable[[Item], tuple[ServiceName, Item]]] = {
    "aix_memory": lambda item: ("Memory used", item),
    # While using the old description, don't append the item, even when discovered
    # with the new check which creates an item.
    "barracuda_mailqueues": lambda item: ("Mail Queue", None),
    "brocade_sys_mem": lambda item: ("Memory used", item),
    "casa_cpu_temp": lambda item: ("Temperature %s", item),
    "cisco_asa_failover": lambda item: ("Cluster Status", item),
    "cisco_mem": lambda item: ("Mem used %s", item),
    "cisco_mem_asa": lambda item: ("Mem used %s", item),
    "cisco_mem_asa64": lambda item: ("Mem used %s", item),
    "cmciii_temp": _get_old_cmciii_temp_description,
    "cmciii_psm_current": lambda item: ("%s", item),
    "cmciii_lcp_airin": lambda item: ("LCP Fanunit Air IN", item),
    "cmciii_lcp_airout": lambda item: ("LCP Fanunit Air OUT", item),
    "cmciii_lcp_water": lambda item: ("LCP Fanunit Water %s", item),
    "db2_mem": lambda item: ("Mem of %s", item),
    "df": lambda item: ("fs_%s", item),
    "df_netapp": lambda item: ("fs_%s", item),
    "df_netapp32": lambda item: ("fs_%s", item),
    "docker_container_mem": lambda item: ("Memory used", item),
    "enterasys_temp": lambda item: ("Temperature", None),
    "esx_vsphere_datastores": lambda item: ("fs_%s", item),
    "esx_vsphere_hostsystem_mem_usage": lambda item: ("Memory used", item),
    "esx_vsphere_hostsystem_mem_usage_cluster": lambda item: ("Memory usage", item),
    "etherbox_temp": lambda item: ("Sensor %s", item),
    "fortigate_memory": lambda item: ("Memory usage", item),
    "fortigate_memory_base": lambda item: ("Memory usage", item),
    "fortigate_node_memory": lambda item: ("Memory usage %s", item),
    "hr_fs": lambda item: ("fs_%s", item),
    "hr_mem": lambda item: ("Memory used", item),
    "huawei_switch_mem": lambda item: ("Memory used %s", item),
    "hyperv_vm": lambda item: ("hyperv_vms", item),
    "ibm_svc_mdiskgrp": lambda item: ("MDiskGrp %s", item),
    "ibm_svc_system": lambda item: ("IBM SVC Info", item),
    "ibm_svc_systemstats_cache": lambda item: ("IBM SVC Cache Total", item),
    "ibm_svc_systemstats_diskio": lambda item: ("IBM SVC Throughput %s Total", item),
    "ibm_svc_systemstats_disk_latency": lambda item: ("IBM SVC Latency %s Total", item),
    "ibm_svc_systemstats_iops": lambda item: ("IBM SVC IOPS %s Total", item),
    "innovaphone_mem": lambda item: ("Memory used", item),
    "innovaphone_temp": lambda item: ("Temperature", None),
    "juniper_mem": lambda item: ("Memory Utilization %s", item),
    "juniper_screenos_mem": lambda item: ("Memory used", item),
    "juniper_trpz_mem": lambda item: ("Memory used", item),
    "liebert_bat_temp": lambda item: ("Battery Temp", None),
    "logwatch": lambda item: ("LOG %s", item),
    "logwatch_groups": lambda item: ("LOG %s", item),
    "megaraid_bbu": lambda item: ("RAID Adapter/BBU %s", item),
    "megaraid_pdisks": lambda item: ("RAID PDisk Adapt/Enc/Sl %s", item),
    "megaraid_ldisks": lambda item: ("RAID Adapter/LDisk %s", item),
    "mem_used": lambda item: ("Memory used", item),
    "mem_win": lambda item: ("Memory and pagefile", item),
    "mknotifyd": lambda item: ("Notification Spooler %s", item),
    "mknotifyd_connection": lambda item: ("Notification Connection %s", item),
    "mssql_backup": lambda item: ("%s Backup", item),
    "mssql_blocked_sessions": lambda item: ("MSSQL Blocked Sessions", None),
    "mssql_counters_cache_hits": lambda item: ("%s", item),
    "mssql_counters_file_sizes": lambda item: ("%s File Sizes", item),
    "mssql_counters_locks": lambda item: ("%s Locks", item),
    "mssql_counters_locks_per_batch": lambda item: ("%s Locks per Batch", item),
    "mssql_counters_pageactivity": lambda item: ("%s Page Activity", item),
    "mssql_counters_sqlstats": lambda item: ("%s", item),
    "mssql_counters_transactions": lambda item: ("%s Transactions", item),
    "mssql_databases": lambda item: ("%s Database", item),
    "mssql_datafiles": lambda item: ("Datafile %s", item),
    "mssql_tablespaces": lambda item: ("%s Sizes", item),
    "mssql_transactionlogs": lambda item: ("Transactionlog %s", item),
    "mssql_versions": lambda item: ("%s Version", item),
    "netscaler_mem": lambda item: ("Memory used", item),
    "nullmailer_mailq": lambda item: ("Nullmailer Queue", None),
    "nvidia_temp": lambda item: ("Temperature NVIDIA %s", item),
    "postfix_mailq": lambda item: (
        ("Postfix Queue", None) if item == "default" else ("Postfix Queue %s", item)
    ),
    "ps": lambda item: ("proc_%s", item),
    "qmail_stats": lambda item: ("Qmail Queue", None),
    "raritan_emx": lambda item: ("Rack %s", item),
    "raritan_pdu_inlet": lambda item: ("Input Phase %s", item),
    "services": lambda item: ("service_%s", item),
    "solaris_mem": lambda item: ("Memory used", item),
    "sophos_memory": lambda item: ("Memory usage", item),
    "statgrab_mem": lambda item: ("Memory used", item),
    "tplink_mem": lambda item: ("Memory used", item),
    "ups_bat_temp": lambda item: ("Temperature Battery %s", item),
    "vms_diskstat_df": lambda item: ("fs_%s", item),
    "wmic_process": lambda item: ("proc_%s", item),
    "zfsget": lambda item: ("fs_%s", item),
    "prism_alerts": lambda item: ("Prism Alerts", None),
    "prism_containers": lambda item: ("Containers %s", item),
    "prism_info": lambda item: ("Prism Cluster", None),
    "prism_storage_pools": lambda item: ("Storage Pool %s", item),
}
