#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
import sys
from collections.abc import Callable, Container, Iterator, Mapping, Sequence
from contextlib import suppress
from pathlib import Path
from typing import Literal, NamedTuple

import cmk.ccc.version as cmk_version
import cmk.livestatus_client as livestatus
import cmk.utils.paths
from cmk import trace
from cmk.agent_based.v1.value_store import set_value_store_manager
from cmk.base import config
from cmk.base.base_app import CheckmkBaseApp
from cmk.base.checkers import (
    CheckerConfig,
    CheckerPluginMapper,
    CMKFetcher,
    CMKParser,
    CMKSummarizer,
    SectionPluginMapper,
)
from cmk.base.config import ConfigCache
from cmk.base.configlib.agent import make_only_from_config
from cmk.base.configlib.exit_code import make_exit_code_spec
from cmk.base.configlib.fetchers import make_parsed_snmp_fetch_intervals_config
from cmk.base.configlib.inventory import make_inventory_config
from cmk.base.configlib.loaded_config import BaseConfig
from cmk.base.configlib.logwatch import set_global_logwatch_config
from cmk.base.configlib.servicelevel import make_service_level_config
from cmk.base.configlib.servicename import (
    make_passive_service_name_config,
)
from cmk.base.errorhandling import (
    CheckResultErrorHandler,
    create_section_crash_dump,
    RecordingFetcher,
    serialize_fetched,
)
from cmk.ccc.cpu_tracking import CPUTracker
from cmk.ccc.exceptions import OnError
from cmk.ccc.hostaddress import HostAddress, HostName, Hosts
from cmk.checkengine import inventory
from cmk.checkengine.auto_queue import AutoQueue
from cmk.checkengine.checking import (
    execute_checkmk_checks,
    make_timing_results,
)
from cmk.checkengine.discovery import DiscoverySettings, is_inventorized
from cmk.checkengine.fetcher_abc import FetcherFunction
from cmk.checkengine.fetcher_abc import Mode as FetchMode
from cmk.checkengine.fetcher_utils.secrets import AdHocSecrets, StoredSecrets
from cmk.checkengine.fetchers.snmp import NoSelectedSNMPSections, SNMPFetcherConfig
from cmk.checkengine.filecache import FileCacheOptions
from cmk.checkengine.inventory import HWSWInventoryParameters
from cmk.checkengine.parser import (
    NO_SELECTION,
    ParserFunction,
    SectionNameCollection,
)
from cmk.checkengine.plugins import (
    AgentBasedPlugins,
    CheckPluginName,
    InventoryPlugin,
    InventoryPluginName,
    SectionName,
)
from cmk.checkengine.sectionparser import SectionPlugin
from cmk.checkengine.snmplib import (
    SNMPBackendEnum,
    SNMPSectionName,
)
from cmk.checkengine.specs.checkresults import ActiveCheckResult, ServiceState
from cmk.checkengine.submitters import get_submitter
from cmk.checkengine.summarize import SummarizerFunction
from cmk.checkengine.value_store import AllValueStoresStore, ValueStoreManager
from cmk.inventory.label_picker import InventorizedHostLabelsStore, LabelPickerConfig, pick_labels
from cmk.inventory.paths import InventoryPaths
from cmk.inventory.store import InventoryStore, make_meta
from cmk.inventory.trees import (
    ImmutableTree,
    MutableTree,
    RawIntervalFromConfig,
    SDPath,
)
from cmk.ruleset_matcher.labels import DiscoveredHostLabelsStore, LabelManager
from cmk.ruleset_matcher.matcher import (
    BundledHostRulesetMatcher,
    RulesetMatcher,
)
from cmk.ruleset_matcher.tags import HostTags
from cmk.utils import ip_lookup, timeperiod
from cmk.utils.everythingtype import EVERYTHING
from cmk.utils.log import console
from cmk.utils.servicename import ServiceName

tracer = trace.get_tracer()


def mandatory_ip_lookup(
    *, usewalk: bool, ip_lookup_config: ip_lookup.IPLookupConfig
) -> ip_lookup.IPLookup | None:
    if usewalk:
        return None
    return ip_lookup.make_lookup_ip_address(ip_lookup_config)


# also used in precompiled host checks!
def run_checking(
    app: CheckmkBaseApp,
    loaded_config: BaseConfig,
    ruleset_matcher: RulesetMatcher,
    label_manager: LabelManager,
    plugins: AgentBasedPlugins,
    config_cache: ConfigCache,
    hosts_config: Hosts,
    host_tags: HostTags,
    monitoring_core: Literal["cmc", "nagios"],
    service_depends_on: Callable[[HostAddress, ServiceName], Sequence[ServiceName]],
    args: Sequence[str],
    *,
    file_cache_options: FileCacheOptions,
    snmp_backend: SNMPBackendEnum | None,
    usewalk: bool,
    selected_sections: SectionNameCollection,
    run_plugin_names: Container[CheckPluginName],
    dry_run: bool,
    show_perfdata: bool,
    secrets_config_relay: AdHocSecrets | StoredSecrets,
    secrets_config_site: StoredSecrets,
    trusted_ca_file: Path,
    fake_dns: HostAddress | None,
    debug: bool,
) -> ServiceState:
    set_global_logwatch_config(
        loaded_config,
        ruleset_matcher,
        label_manager,
        omd_root=cmk.utils.paths.omd_root,
        var_dir=cmk.utils.paths.var_dir,
        debug=debug,
    )

    # handle adhoc-check
    hostname = HostName(args[0])
    ipaddress: HostAddress | None = None
    if len(args) == 2:
        ipaddress = HostAddress(args[1])

    ip_lookup_config = config_cache.ip_lookup_config(fake_dns=fake_dns)
    ip_address_of = ip_lookup.ConfiguredIPLookup(
        ip_lookup.make_lookup_ip_address(ip_lookup_config),
        allow_empty=hosts_config.clusters,
        error_handler=config.handle_ip_lookup_failure,
    )
    with ruleset_matcher.ruleset_optimizer.processed_hosts({hostname}):
        service_name_config = make_passive_service_name_config(
            loaded_config, ruleset_matcher, label_manager
        )
        service_configurer = config_cache.make_service_configurer(
            plugins.check_plugins, service_name_config
        )
        clustering = config.make_clustering_config(
            loaded_config, hosts_config, ruleset_matcher, label_manager
        )
        service_level_config = make_service_level_config(
            loaded_config, ruleset_matcher, label_manager
        )
        exit_code_spec = make_exit_code_spec(loaded_config, ruleset_matcher, label_manager)
        only_from = make_only_from_config(loaded_config, ruleset_matcher, label_manager)
        inventory_config = make_inventory_config(
            loaded_config, ruleset_matcher, label_manager, hosts_config
        )
        enforced_service_table = config.EnforcedServicesTable(
            BundledHostRulesetMatcher(
                loaded_config.static_checks,
                ruleset_matcher,
                label_manager.labels_of_host,
            ),
            service_name_config,
            plugins.check_plugins,
            label_manager.labels_of_service,
        )
        logger = logging.getLogger("cmk.base.checking")
        fetcher = CMKFetcher(
            config_cache,
            host_tags,
            get_relay_id=lambda hn: config.get_relay_id(label_manager.labels_of_host(hn)),
            make_trigger=lambda relay_id: app.make_fetcher_trigger(relay_id, trusted_ca_file),
            source_config=config_cache.make_source_config(
                service_configurer,
                ip_address_of,
                service_name_config,
                enforced_service_table,
                SNMPFetcherConfig(
                    on_error=OnError.RAISE,
                    missing_sys_description=config_cache.missing_sys_description,
                    selected_sections=(
                        NoSelectedSNMPSections()
                        if selected_sections is NO_SELECTION
                        else frozenset(
                            SNMPSectionName(n)
                            for n in selected_sections
                            if n in plugins.snmp_sections
                        )
                    ),
                    backend_override=snmp_backend,
                    base_path=cmk.utils.paths.omd_root,
                    relative_stored_walk_path=cmk.utils.paths.relative_snmpwalks_dir,
                    relative_walk_cache_path=cmk.utils.paths.relative_walk_cache_dir,
                    relative_section_cache_path=cmk.utils.paths.relative_snmp_section_cache_dir,
                    caching_config=make_parsed_snmp_fetch_intervals_config(
                        loaded_config, ruleset_matcher, label_manager.labels_of_host
                    ),
                    force_stored_walks=usewalk,
                    debug=debug,
                ),
            ),
            plugins=plugins,
            clusters=hosts_config.clusters,
            default_address_family=ip_lookup_config.default_address_family,
            file_cache_options=file_cache_options,
            force_snmp_cache_refresh=False,
            get_ip_stack_config=ip_lookup_config.ip_stack_config,
            ip_address_of=ip_address_of,
            ip_address_of_mandatory=mandatory_ip_lookup(
                usewalk=usewalk, ip_lookup_config=ip_lookup_config
            ),
            ip_address_of_mgmt=ip_lookup.make_lookup_mgmt_board_ip_address(ip_lookup_config),
            mode=(
                FetchMode.CHECKING
                if selected_sections is NO_SELECTION
                else FetchMode.FORCE_SECTIONS
            ),
            simulation_mode=loaded_config.simulation_mode,
            secrets_config_relay=secrets_config_relay,
            secrets_config_site=secrets_config_site,
            debug=debug,
        )
        parser = CMKParser(
            config.make_parser_config(
                loaded_config,
                ruleset_matcher,
                label_manager,
                ip_address_of=config_cache.primary_ip_address_of,
            ),
            selected_sections=selected_sections,
            keep_outdated=file_cache_options.keep_outdated,
            debug=debug,
        )
        checker_config = CheckerConfig(
            only_from=only_from,
            effective_service_level=service_level_config.effective,
            get_clustered_service_configuration=clustering.get_clustered_service_configuration,
            nodes=lambda hn: hosts_config.clusters.get(hn, ()),
            effective_host=clustering.effective_host,
            get_snmp_backend=config_cache.get_snmp_backend,
            timeperiods_active=timeperiod.TimeperiodActiveCoreLookup(
                livestatus.get_optional_timeperiods_active_map, logger.warning
            ),
        )
        summarizer = CMKSummarizer(
            hostname,
            config_cache.summary_config,
            override_non_ok_state=None,
        )
        recording_fetcher = RecordingFetcher(fetcher)
        error_handler = CheckResultErrorHandler(
            exit_code_spec(hostname),
            host_name=hostname,
            service_name="Check_MK",
            plugin_name="mk",
            is_cluster=hostname in hosts_config.clusters,
            snmp_backend=config_cache.get_snmp_backend(hostname),
            keepalive=False,
            get_agent_output=lambda: recording_fetcher.serialized(hostname),
            debug=debug,
        )

        checks_result: Sequence[ActiveCheckResult] = []
        with (
            error_handler,
            set_value_store_manager(
                ValueStoreManager(
                    hostname, AllValueStoresStore(cmk.utils.paths.counters_dir / hostname)
                ),
                store_changes=not dry_run,
            ) as value_store_manager,
        ):
            console.debug(f"Checkmk version {cmk_version.__version__}")
            fetched = recording_fetcher(hostname, ip_address=ipaddress)
            check_plugins = CheckerPluginMapper(
                checker_config,
                plugins.check_plugins,
                value_store_manager,
                clusters=hosts_config.clusters,
                get_agent_output=lambda: serialize_fetched((f[0], f[1]) for f in fetched),
                omd_root=cmk.utils.paths.omd_root,
                debug=debug,
            )
            with CPUTracker(console.debug) as tracker:
                checks_result = execute_checkmk_checks(
                    hostname=hostname,
                    omd_root=cmk.utils.paths.omd_root,
                    fetched=((f[0], f[1]) for f in fetched),
                    parser=parser,
                    summarizer=summarizer,
                    section_plugins=SectionPluginMapper(
                        {**plugins.agent_sections, **plugins.snmp_sections}
                    ),
                    section_error_handling=lambda section_name, raw_data: create_section_crash_dump(
                        operation="parsing",
                        section_name=section_name,
                        section_content=raw_data,
                        host_name=hostname,
                        get_agent_output=lambda: serialize_fetched((f[0], f[1]) for f in fetched),
                    ),
                    check_plugins=check_plugins,
                    inventory_plugins=plugins.inventory_plugins,
                    inventory_parameters=inventory_config.plugin_parameters,
                    params=inventory_config.hwsw_parameters(hostname),
                    services=config_cache.configured_services(
                        hostname,
                        plugins.check_plugins,
                        service_configurer,
                        service_name_config,
                        enforced_service_table,
                        service_depends_on,
                    ),
                    run_plugin_names=run_plugin_names,
                    get_check_period=lambda service_name, service_labels: timeperiod.TimeperiodName(
                        config_cache.check_period_of_passive_service(
                            hostname, service_name, service_labels
                        )
                    ),
                    submitter=get_submitter(
                        check_submission=loaded_config.check_submission,
                        monitoring_core=monitoring_core,
                        dry_run=dry_run,
                        host_name=hostname,
                        perfdata_format=loaded_config.perfdata_format,
                        show_perfdata=show_perfdata,
                    ),
                    exit_spec=exit_code_spec(hostname),
                    timeperiods_active=checker_config.timeperiods_active,
                    debug=debug,
                )

            checks_result = [
                *checks_result,
                make_timing_results(
                    tracker.duration,
                    tuple((f[0], f[2]) for f in fetched),
                    perfdata_with_times=loaded_config.check_mk_perfdata_with_times,
                ),
            ]

        if error_handler.result is not None:
            checks_result = (error_handler.result,)

        check_result = ActiveCheckResult.from_subresults(*checks_result)
        with suppress(IOError):
            sys.stdout.write(check_result.as_text() + "\n")
            sys.stdout.flush()
        return check_result.state


class _SaveTreeActions(NamedTuple):
    do_archive: bool
    do_save: bool


def _render_update_results(
    update_results: Mapping[SDPath, Sequence[str]],
) -> str:
    lines = ["Updated inventory tree:"]
    for path, messages in update_results.items():
        lines.append(f"  Path '{' > '.join(path)}':")
        lines.extend(f"    {r}" for r in sorted(messages))
    return "\n".join(lines) + "\n"


def _get_save_tree_actions(
    *,
    previous_tree: ImmutableTree,
    inventory_tree: MutableTree,
) -> _SaveTreeActions:
    if not inventory_tree:
        # Archive current inventory tree file if it exists. Important for host inventory icon
        console.verbose("No inventory tree.")
        return _SaveTreeActions(do_archive=True, do_save=False)

    if not previous_tree:
        console.verbose("New inventory tree.")
        return _SaveTreeActions(do_archive=False, do_save=True)

    if has_changed := previous_tree != inventory_tree:
        console.verbose("Inventory tree has changed.")

    if update_results := inventory_tree.get_update_results():
        console.verbose_no_lf(_render_update_results(update_results))

    return _SaveTreeActions(
        do_archive=has_changed,
        do_save=(has_changed or len(update_results) > 0),
    )


def _schedule_host_labels_rediscovery(
    host_name: HostName,
    *,
    labels_differ: bool,
    rediscovery: DiscoverySettings,
    autodiscovery_dir: Path,
) -> Iterator[ActiveCheckResult]:
    if labels_differ and rediscovery.update_host_labels:
        AutoQueue(autodiscovery_dir).add(host_name)
        yield ActiveCheckResult(state=0, summary="Rediscovery scheduled")


def execute_active_check_inventory(
    host_name: HostName,
    *,
    hosts_config: Hosts,
    fetcher: FetcherFunction,
    parser: ParserFunction,
    summarizer: SummarizerFunction,
    section_plugins: Mapping[SectionName, SectionPlugin],
    inventory_plugins: Mapping[InventoryPluginName, InventoryPlugin],
    inventory_parameters: Callable[[HostName, InventoryPlugin], Mapping[str, object]],
    parameters: HWSWInventoryParameters,
    raw_intervals_from_config: Sequence[RawIntervalFromConfig],
    label_picker_configs: Sequence[LabelPickerConfig],
    rediscovery: DiscoverySettings,
    inventorized_host_labels_dir: Path,
    discovered_host_labels_dir: Path,
    autodiscovery_dir: Path,
    debug: bool,
) -> Sequence[ActiveCheckResult]:
    inv_store = InventoryStore(cmk.utils.paths.omd_root)
    previous_tree = inv_store.load_previous_inventory_tree(host_name=host_name)

    if host_name in hosts_config.clusters:
        result = inventory.inventorize_cluster(
            hosts_config.clusters[host_name],
            parameters=parameters,
            previous_tree=previous_tree,
        )
    else:
        recording_fetcher = RecordingFetcher(fetcher)
        result = inventory.inventorize_host(
            host_name,
            omd_root=cmk.utils.paths.omd_root,
            fetcher=recording_fetcher,
            parser=parser,
            summarizer=summarizer,
            inventory_parameters=inventory_parameters,
            section_plugins=section_plugins,
            section_error_handling=lambda section_name, raw_data: create_section_crash_dump(
                operation="parsing",
                section_name=section_name,
                section_content=raw_data,
                host_name=host_name,
                get_agent_output=lambda: recording_fetcher.serialized(host_name),
            ),
            inventory_plugins=inventory_plugins,
            run_plugin_names=EVERYTHING,
            parameters=parameters,
            raw_intervals_from_config=raw_intervals_from_config,
            previous_tree=previous_tree,
            debug=debug,
        )

    inv_paths = InventoryPaths(cmk.utils.paths.omd_root)
    if result.no_data_or_files:
        AutoQueue(inv_paths.auto_dir).add(host_name)
    else:
        AutoQueue(inv_paths.auto_dir).remove(host_name)

    if not (result.processing_failed or result.no_data_or_files):
        save_tree_actions = _get_save_tree_actions(
            previous_tree=previous_tree,
            inventory_tree=result.inventory_tree,
        )
        # The order of archive or save is important:
        if save_tree_actions.do_archive:
            console.verbose("Archive current inventory tree.")
            inv_store.archive_inventory_tree(host_name=host_name)
        if save_tree_actions.do_save:
            console.verbose("Save new inventory tree.")
            inv_store.save_inventory_tree(
                host_name=host_name,
                tree=result.inventory_tree,
                meta=make_meta(do_archive=save_tree_actions.do_archive),
            )

    if host_name in hosts_config.clusters:
        return result.check_results

    labels_store = InventorizedHostLabelsStore(host_name, inventorized_host_labels_dir)
    if not (result.processing_failed or result.no_data_or_files):
        labels_store.save(pick_labels(result.inventory_tree, label_picker_configs))
    label_results = inventory.check_inventorized_host_labels(
        parameters=parameters,
        picked=labels_store.load(),
        accepted={
            label.name: label.value
            for label in DiscoveredHostLabelsStore(host_name, discovered_host_labels_dir).load()
            if is_inventorized(label)
        },
    )
    return [
        *result.check_results,
        *label_results,
        *_schedule_host_labels_rediscovery(
            host_name,
            labels_differ=bool(label_results),
            rediscovery=rediscovery,
            autodiscovery_dir=autodiscovery_dir,
        ),
    ]
