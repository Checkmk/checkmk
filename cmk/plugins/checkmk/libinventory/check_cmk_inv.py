#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import argparse
import logging
import sys
from collections.abc import Sequence
from contextlib import suppress
from pathlib import Path

import cmk.ccc.version as cmk_version
import cmk.utils.password_store
import cmk.utils.paths
from cmk.base import config
from cmk.base.app import make_app
from cmk.base.base_app import CheckmkBaseApp
from cmk.base.checkers import (
    CMKFetcher,
    CMKParser,
    CMKSummarizer,
    SectionPluginMapper,
)
from cmk.base.configlib.fetchers import make_parsed_snmp_fetch_intervals_config
from cmk.base.configlib.servicename import make_final_service_name_config
from cmk.base.core.active_config_layout import RELATIVE_PATH_SECRETS, RELATIVE_PATH_TRUSTED_CAS
from cmk.base.errorhandling import CheckResultErrorHandler
from cmk.base.modes.check_mk import execute_active_check_inventory
from cmk.ccc.config_path import VersionedConfigPath
from cmk.ccc.cpu_tracking import CPUTracker
from cmk.ccc.exceptions import OnError
from cmk.ccc.hostaddress import HostName
from cmk.checkengine.checking import make_timing_results
from cmk.checkengine.checkresults import ActiveCheckResult
from cmk.checkengine.inventory import HWSWInventoryParameters
from cmk.checkengine.parser import NO_SELECTION
from cmk.checkengine.plugin_backend import (
    extract_known_discovery_rulesets,
    load_selected_plugins,
    plugin_index,
)
from cmk.checkengine.plugins import AgentBasedPlugins
from cmk.checkengine.submitters import ServiceState
from cmk.fetchers import Mode as FetchMode
from cmk.fetchers import NoSelectedSNMPSections, SNMPFetcherConfig, StoredSecrets
from cmk.fetchers.filecache import FileCacheOptions
from cmk.server_side_calls_backend import load_secrets_file
from cmk.utils.ip_lookup import (
    ConfiguredIPLookup,
    make_lookup_ip_address,
    make_lookup_mgmt_board_ip_address,
)
from cmk.utils.log import console
from cmk.utils.rulesets.ruleset_matcher import BundledHostRulesetMatcher


def parse_arguments(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="check_cmk_inv",
        description="""Check Checkmk HW/SW Inventory""",
    )

    parser.add_argument(
        "hostname",
        type=str,
        metavar="HOSTNAME",
        help="Host for which the HW/SW Inventory is executed",
    )

    parser.add_argument(
        "--use-indexed-plugins",
        action="store_true",
        help="Precompiled plugin index file",
    )

    parser.add_argument(
        "--inv-fail-status",
        type=int,
        default=1,
        help="State when HW/SW Inventory fails",
    )

    parser.add_argument(
        "--hw-changes",
        type=int,
        default=0,
        help="State when hardware changes are detected",
    )

    parser.add_argument(
        "--sw-changes",
        type=int,
        default=0,
        help="State when software packages info is missing",
    )

    parser.add_argument(
        "--sw-missing",
        type=int,
        default=0,
        help="State when software packages info is missing",
    )

    parser.add_argument(
        "--nw-changes",
        type=int,
        default=0,
        help="State when networking changes are detected",
    )

    return parser.parse_args(argv)


def main(argv: Sequence[str]) -> int:
    args = parse_arguments(argv or sys.argv[1:])
    parameters = HWSWInventoryParameters(
        hw_changes=args.hw_changes,
        sw_changes=args.sw_changes,
        sw_missing=args.sw_missing,
        nw_changes=args.nw_changes,
        fail_status=args.inv_fail_status,
        status_data_inventory=False,
    )

    # This is not race condition free, but we can not resolve the latest link:
    # The core may choose to remove the currently latest one at any time.
    active_config_path = VersionedConfigPath.make_latest_path(cmk.utils.paths.omd_root)

    return _inventory_as_check(
        make_app(cmk_version.edition(cmk.utils.paths.omd_root)),
        parameters,
        active_config_path,
        args.hostname,
        load_plugins_from_index(active_config_path) if args.use_indexed_plugins else load_checks(),
    )


def _inventory_as_check(
    app: CheckmkBaseApp,
    parameters: HWSWInventoryParameters,
    latest_config_path: Path,
    hostname: HostName,
    plugins: AgentBasedPlugins,
) -> ServiceState:
    loading_result = config.load(
        discovery_rulesets=extract_known_discovery_rulesets(plugins),
        get_builtin_host_labels=app.get_builtin_host_labels,
    )
    loaded_config = loading_result.loaded_config
    ruleset_matcher = loading_result.config_cache.ruleset_matcher
    label_manager = loading_result.config_cache.label_manager

    config_cache = loading_result.config_cache
    ruleset_matcher.ruleset_optimizer.set_all_processed_hosts({hostname})
    hosts_config = config.make_hosts_config(loaded_config)
    service_name_config = config_cache.make_passive_service_name_config(
        make_final_service_name_config(loaded_config, ruleset_matcher)
    )
    enforced_service_table = config.EnforcedServicesTable(
        BundledHostRulesetMatcher(
            loaded_config.static_checks, ruleset_matcher, label_manager.labels_of_host
        ),
        service_name_config,
        plugins.check_plugins,
    )

    ip_lookup_config = config_cache.ip_lookup_config()
    ip_address_of_bare = make_lookup_ip_address(ip_lookup_config)
    ip_address_of = ConfiguredIPLookup(
        ip_address_of_bare,
        allow_empty=config_cache.hosts_config.clusters,
        error_handler=config.handle_ip_lookup_failure,
    )
    file_cache_options = FileCacheOptions()

    fetcher = CMKFetcher(
        config_cache,
        get_relay_id=lambda hn: config.get_relay_id(label_manager.labels_of_host(hn)),
        make_trigger=lambda relay_id: app.make_fetcher_trigger(
            relay_id, latest_config_path / RELATIVE_PATH_TRUSTED_CAS
        ),
        factory=config_cache.fetcher_factory(
            config_cache.make_service_configurer(plugins.check_plugins, service_name_config),
            ip_address_of,
            service_name_config,
            enforced_service_table,
            SNMPFetcherConfig(
                on_error=OnError.RAISE,
                missing_sys_description=config_cache.missing_sys_description,
                selected_sections=NoSelectedSNMPSections(),
                backend_override=None,
                base_path=cmk.utils.paths.omd_root,
                relative_stored_walk_path=cmk.utils.paths.relative_snmpwalks_dir,
                relative_walk_cache_path=cmk.utils.paths.relative_walk_cache_dir,
                relative_section_cache_path=cmk.utils.paths.relative_snmp_section_cache_dir,
                caching_config=make_parsed_snmp_fetch_intervals_config(
                    loaded_config, ruleset_matcher, label_manager.labels_of_host
                ),
            ),
        ),
        plugins=plugins,
        default_address_family=ip_lookup_config.default_address_family,
        file_cache_options=file_cache_options,
        force_snmp_cache_refresh=False,
        get_ip_stack_config=ip_lookup_config.ip_stack_config,
        ip_address_of=ip_address_of,
        ip_address_of_mandatory=ip_address_of_bare,
        ip_address_of_mgmt=make_lookup_mgmt_board_ip_address(ip_lookup_config),
        mode=FetchMode.INVENTORY,
        simulation_mode=config.simulation_mode,
        secrets_config_relay=StoredSecrets(
            path=cmk.utils.password_store.active_secrets_path_relay(),
            secrets=(
                secrets := load_secrets_file(
                    cmk.utils.password_store.active_secrets_path_site(
                        RELATIVE_PATH_SECRETS, config_path=latest_config_path
                    )
                )
            ),
        ),
        secrets_config_site=StoredSecrets(
            path=cmk.utils.password_store.active_secrets_path_site(
                RELATIVE_PATH_SECRETS, config_path=latest_config_path
            ),
            secrets=secrets,
        ),
        metric_backend_fetcher_factory=lambda hn: app.make_metric_backend_fetcher(
            hn,
            config_cache.explicit_host_attributes,
            config_cache.check_mk_check_interval,
            loaded_config.monitoring_core == "cmc",
        ),
    )
    parser = CMKParser(
        config.make_parser_config(loaded_config, ruleset_matcher, label_manager),
        selected_sections=NO_SELECTION,
        keep_outdated=file_cache_options.keep_outdated,
        logger=logging.getLogger("cmk.base.inventory"),
    )
    summarizer = CMKSummarizer(
        hostname,
        config_cache.summary_config,
        override_non_ok_state=parameters.fail_status,
    )
    error_handler = CheckResultErrorHandler(
        exit_spec=config_cache.exit_code_spec(hostname),
        host_name=hostname,
        service_name="Check_MK HW/SW Inventory",
        plugin_name="check_mk_active-cmk_inv",
        is_cluster=hostname in hosts_config.clusters,
        snmp_backend=config_cache.get_snmp_backend(hostname),
        keepalive=False,
    )
    check_results: Sequence[ActiveCheckResult] = []
    with error_handler:
        with CPUTracker(console.debug) as tracker:
            check_results = execute_active_check_inventory(
                hostname,
                config_cache=config_cache,
                hosts_config=hosts_config,
                fetcher=fetcher,
                parser=parser,
                summarizer=summarizer,
                section_plugins=SectionPluginMapper(
                    {**plugins.agent_sections, **plugins.snmp_sections}
                ),
                inventory_plugins=plugins.inventory_plugins,
                inventory_parameters=config_cache.inventory_parameters,
                parameters=parameters,
                raw_intervals_from_config=config_cache.inv_retention_intervals(hostname),
            )
        check_results = [
            *check_results,
            make_timing_results(
                tracker.duration,
                # FIXME: This is inconsistent with the other two calls.
                (),  # nothing to add here, b/c fetching is triggered further down the call stack.
                perfdata_with_times=config.check_mk_perfdata_with_times,
            ),
        ]

    if error_handler.result is not None:
        check_results = (error_handler.result,)

    check_result = ActiveCheckResult.from_subresults(*check_results)
    with suppress(IOError):
        sys.stdout.write(check_result.as_text() + "\n")
        sys.stdout.flush()
    return check_result.state


def load_checks() -> AgentBasedPlugins:
    plugins = config.load_all_pluginX(cmk.utils.paths.checks_dir)
    if sys.stderr.isatty():
        for error_msg in plugins.errors:
            console.error(error_msg, file=sys.stderr)
    return plugins


def load_plugins_from_index(config_path: Path) -> AgentBasedPlugins:
    plugin_idx = plugin_index.load_plugin_index(config_path)
    _errors, sections, checks = config.load_and_convert_legacy_checks(plugin_idx.legacy)
    return load_selected_plugins(plugin_idx.locations, sections, checks, validate=False)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
