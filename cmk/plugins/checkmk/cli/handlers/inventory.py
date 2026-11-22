#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import contextlib
import itertools
import sys
import time
from collections.abc import Container, Sequence
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Protocol

import cmk.ccc.cleanup
import cmk.livestatus_client as livestatus
import cmk.utils.password_store
import cmk.utils.paths
from cmk.base import config
from cmk.base.app import make_app
from cmk.base.checkers import CMKFetcher, CMKParser, CMKSummarizer, SectionPluginMapper
from cmk.base.checking import mandatory_ip_lookup
from cmk.base.configlib.servicename import make_final_service_name_config
from cmk.base.core.active_config_layout import (
    RELATIVE_PATH_SECRETS,
    RELATIVE_PATH_TRUSTED_CAS,
)
from cmk.base.errorhandling import create_section_crash_dump, RecordingFetcher
from cmk.base.inventory import execute_active_check_inventory
from cmk.ccc.config_path import VersionedConfigPath
from cmk.ccc.exceptions import MKGeneralException, MKTimeout, OnError
from cmk.ccc.hostaddress import HostName
from cmk.ccc.timeout import Timeout
from cmk.checkengine import inventory
from cmk.checkengine.auto_queue import AutoQueue
from cmk.checkengine.discovery import DiscoverySettings
from cmk.checkengine.fetcher_abc import Mode as FetchMode
from cmk.checkengine.fetcher_utils.secrets import AdHocSecrets, StoredSecrets
from cmk.checkengine.fetchers.snmp import NoSelectedSNMPSections
from cmk.checkengine.parser import NO_SELECTION
from cmk.checkengine.plugins import InventoryPluginName, SectionName
from cmk.checkengine.specs.checkresults import ActiveCheckResult
from cmk.cli.internal import Context as CLIContext
from cmk.cli.internal import ExitCode as CLIExitCode
from cmk.cli.internal import Handler as CLIHandler
from cmk.inventory.paths import InventoryPaths
from cmk.inventory.store import InventoryStore
from cmk.plugins.checkmk.cli.inventory import (
    cli_command_inventorize_marked_hosts,
    cli_command_inventory,
    InventoryRequest,
)
from cmk.plugins.checkmk.cli.options import FetchRequest
from cmk.ruleset_matcher.matcher import BundledHostRulesetMatcher
from cmk.ruleset_matcher.tags import expand_host_specs, HostSelectionError
from cmk.server_side_calls_backend import load_secrets_file
from cmk.utils import ip_lookup
from cmk.utils.everythingtype import EVERYTHING
from cmk.utils.log import console, section

from ._file_cache import make_file_cache_options
from ._snmp_fetcher import snmp_fetcher_config, snmp_section_selection
from .agent_based import extract_plugin_selection, load_checks, PluginSelectionError
from .host_selection import monitored_hosts


class _Inventorize(Protocol):
    def __call__(self, request: InventoryRequest, *, omd_root: Path, debug: bool) -> None: ...


def _inventorize(request: InventoryRequest, *, omd_root: Path, debug: bool) -> None:
    app = make_app(omd_root)
    file_cache_options = make_file_cache_options(request.fetch.file_cache)

    plugins = load_checks(debug=debug)
    loading_result = config.load(validate_hosts=True, debug=debug)
    loaded_config = loading_result.loaded_config
    host_tags = loading_result.host_tags
    ruleset_matcher = loading_result.config_cache.ruleset_matcher
    label_manager = loading_result.config_cache.label_manager
    config_cache = loading_result.config_cache

    hosts_config = loading_result.hosts_config
    service_name_config = config_cache.make_passive_service_name_config(
        make_final_service_name_config(loaded_config, ruleset_matcher)
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
    ip_lookup_config = config_cache.ip_lookup_config(fake_dns=request.fetch.fake_dns)
    ip_address_of = ip_lookup.ConfiguredIPLookup(
        ip_lookup.make_lookup_ip_address(ip_lookup_config),
        allow_empty=hosts_config.clusters,
        error_handler=config.handle_ip_lookup_failure,
    )

    valid_hosts = monitored_hosts(hosts_config, config_cache)
    hostnames: Sequence[HostName]
    if request.hosts:
        hostnames = expand_host_specs(request.hosts, choose_from=valid_hosts, host_tags=host_tags)
        console.verbose(f"Doing HW/SW Inventory on: {', '.join(hostnames)}")
    else:
        # No hosts specified: do all hosts
        hostnames = sorted(valid_hosts)
        console.verbose("Doing HW/SW Inventory on all hosts")

    with (
        config_cache.ruleset_matcher.ruleset_optimizer.processed_hosts(hostnames)
        if request.hosts
        else contextlib.nullcontext()
    ):
        if request.force:
            file_cache_options = replace(file_cache_options, keep_outdated=True)

        selected_sections, run_plugin_names = extract_plugin_selection(
            detect_plugins=request.plugin_selection.detect_plugins,
            detect_sections=request.plugin_selection.detect_sections,
            selected_plugins=request.plugin_selection.plugins,
            plugins=plugins.inventory_plugins,
            sections=itertools.chain(
                plugins.agent_sections.values(), plugins.snmp_sections.values()
            ),
            type_=InventoryPluginName,
        )
        fetcher = CMKFetcher(
            config_cache,
            host_tags,
            get_relay_id=lambda hn: config.get_relay_id(label_manager.labels_of_host(hn)),
            make_trigger=lambda relay_id: app.make_fetcher_trigger(
                relay_id, cmk.utils.paths.trusted_ca_file
            ),
            source_config=config_cache.make_source_config(
                config_cache.make_service_configurer(plugins.check_plugins, service_name_config),
                ip_address_of,
                service_name_config,
                enforced_service_table,
                snmp_fetcher_config(
                    loading_result,
                    snmp_section_selection(selected_sections, plugins.snmp_sections),
                    on_error=OnError.RAISE,
                    backend_override=request.fetch.snmp_backend,
                    force_stored_walks=request.fetch.usewalk,
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
                usewalk=request.fetch.usewalk, ip_lookup_config=ip_lookup_config
            ),
            ip_address_of_mgmt=ip_lookup.make_lookup_mgmt_board_ip_address(ip_lookup_config),
            mode=(
                FetchMode.INVENTORY
                if selected_sections is NO_SELECTION
                else FetchMode.FORCE_SECTIONS
            ),
            simulation_mode=loaded_config.simulation_mode,
            secrets_config_relay=AdHocSecrets(
                path=cmk.utils.password_store.generate_ad_hoc_secrets_path(
                    cmk.utils.paths.relative_tmp_dir
                ),
                secrets=(
                    secrets := load_secrets_file(
                        cmk.utils.password_store.pending_secrets_path_site()
                    )
                ),
            ),
            secrets_config_site=StoredSecrets(
                path=cmk.utils.password_store.pending_secrets_path_site(), secrets=secrets
            ),
            debug=debug,
        )
        recording_fetcher = RecordingFetcher(fetcher)
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

        section_plugins = SectionPluginMapper({**plugins.agent_sections, **plugins.snmp_sections})
        inventory_plugins = plugins.inventory_plugins

        inv_store = InventoryStore(cmk.utils.paths.omd_root)

        for hostname in hostnames:

            def section_error_handling(
                section_name: SectionName,
                raw_data: Sequence[object],
                host_name: HostName = hostname,
            ) -> str:
                return create_section_crash_dump(
                    operation="parsing",
                    section_name=section_name,
                    section_content=raw_data,
                    host_name=host_name,
                    get_agent_output=lambda: recording_fetcher.serialized(host_name),
                )

            parameters = config_cache.inventory_config.hwsw_parameters(hostname)
            raw_intervals_from_config = config_cache.inventory_config.retention_intervals(hostname)
            summarizer = CMKSummarizer(
                hostname,
                config_cache.summary_config,
                override_non_ok_state=parameters.fail_status,
            )

            section.section_begin(hostname)
            section.section_step("Inventorizing")
            try:
                previous_tree = inv_store.load_previous_inventory_tree(host_name=hostname)
                if hostname in hosts_config.clusters:
                    check_results = inventory.inventorize_cluster(
                        hosts_config.clusters[hostname],
                        parameters=parameters,
                        previous_tree=previous_tree,
                    ).check_results
                else:
                    check_results = inventory.inventorize_host(
                        hostname,
                        omd_root=cmk.utils.paths.omd_root,
                        fetcher=recording_fetcher,
                        parser=parser,
                        summarizer=summarizer,
                        inventory_parameters=config_cache.inventory_config.plugin_parameters,
                        section_plugins=section_plugins,
                        section_error_handling=section_error_handling,
                        inventory_plugins=inventory_plugins,
                        run_plugin_names=run_plugin_names,
                        parameters=parameters,
                        raw_intervals_from_config=raw_intervals_from_config,
                        previous_tree=previous_tree,
                        debug=debug,
                    ).check_results

                check_result = ActiveCheckResult.from_subresults(*check_results)
                if check_result.state:
                    section.section_error(check_result.summary)
                else:
                    section.section_success(check_result.summary)

            except Exception as e:
                if debug:
                    raise
                section.section_error("%s" % e)
            finally:
                cmk.ccc.cleanup.cleanup_globals()


@dataclass(frozen=True, kw_only=True)
class _InventoryCommand:
    inventorize: _Inventorize

    def run(self, context: CLIContext, request: InventoryRequest) -> CLIExitCode:
        try:
            self.inventorize(request, omd_root=context.omd_root, debug=context.global_options.debug)
        except (HostSelectionError, MKGeneralException, PluginSelectionError) as e:
            context.logger.error("%(error)s", {"error": e})  # noqa: TRY400
            if context.global_options.debug:
                raise
            return CLIExitCode.UNKNOWN
        return CLIExitCode.SUCCESS


class _InventorizeMarkedHosts(Protocol):
    def __call__(self, request: FetchRequest, *, omd_root: Path, debug: bool) -> None: ...


def _inventorize_marked_hosts(request: FetchRequest, *, omd_root: Path, debug: bool) -> None:
    app = make_app(omd_root)
    file_cache_options = make_file_cache_options(request.file_cache)

    if not (queue := AutoQueue(InventoryPaths(cmk.utils.paths.omd_root).auto_dir)):
        console.verbose("Autoinventory: No hosts marked by inventory check")
        return

    # We do not resolve the `latest` link here, as any given serial might be removed by the core.
    latest_config_path = VersionedConfigPath.make_latest_path(cmk.utils.paths.omd_root)

    plugins = load_checks(debug=debug)
    loading_result = config.load(validate_hosts=True, debug=debug)
    loaded_config = loading_result.loaded_config
    hosts_config = loading_result.hosts_config
    host_tags = loading_result.host_tags
    ruleset_matcher = loading_result.config_cache.ruleset_matcher
    label_manager = loading_result.config_cache.label_manager
    config_cache = loading_result.config_cache

    service_name_config = config_cache.make_passive_service_name_config(
        make_final_service_name_config(loaded_config, ruleset_matcher)
    )  # not obvious to me why/if we *really* need this
    enforced_service_table = config.EnforcedServicesTable(
        BundledHostRulesetMatcher(
            loaded_config.static_checks,
            ruleset_matcher,
            label_manager.labels_of_host,
        ),
        service_name_config,
        plugins.check_plugins,
        label_manager.labels_of_service,
    )  # not obvious to me why/if we *really* need this
    ip_lookup_config = config_cache.ip_lookup_config(fake_dns=request.fake_dns)
    ip_address_of = ip_lookup.ConfiguredIPLookup(
        ip_lookup.make_lookup_ip_address(ip_lookup_config),
        allow_empty=hosts_config.clusters,
        error_handler=config.handle_ip_lookup_failure,
    )

    parser = CMKParser(
        config.make_parser_config(
            loaded_config,
            ruleset_matcher,
            label_manager,
            ip_address_of=config_cache.primary_ip_address_of,
        ),
        selected_sections=NO_SELECTION,
        keep_outdated=file_cache_options.keep_outdated,
        debug=debug,
    )
    fetcher = CMKFetcher(
        config_cache,
        host_tags,
        get_relay_id=lambda hn: config.get_relay_id(label_manager.labels_of_host(hn)),
        make_trigger=lambda relay_id: app.make_fetcher_trigger(
            relay_id, latest_config_path / RELATIVE_PATH_TRUSTED_CAS
        ),
        source_config=config_cache.make_source_config(
            config_cache.make_service_configurer(plugins.check_plugins, service_name_config),
            ip_address_of,
            service_name_config,
            enforced_service_table,
            snmp_fetcher_config(
                loading_result,
                NoSelectedSNMPSections(),
                on_error=OnError.RAISE,
                backend_override=request.snmp_backend,
                force_stored_walks=request.usewalk,
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
            usewalk=request.usewalk, ip_lookup_config=ip_lookup_config
        ),
        ip_address_of_mgmt=ip_lookup.make_lookup_mgmt_board_ip_address(ip_lookup_config),
        mode=FetchMode.INVENTORY,
        simulation_mode=loaded_config.simulation_mode,
        secrets_config_relay=StoredSecrets(
            path=cmk.utils.password_store.active_secrets_path_relay(),
            secrets=(
                secrets := load_secrets_file(
                    cmk.utils.password_store.active_secrets_path_site(RELATIVE_PATH_SECRETS)
                )
            ),
        ),
        secrets_config_site=StoredSecrets(
            path=cmk.utils.password_store.active_secrets_path_site(RELATIVE_PATH_SECRETS),
            secrets=secrets,
        ),
        debug=debug,
    )

    def summarizer(host_name: HostName) -> CMKSummarizer:
        return CMKSummarizer(
            host_name,
            config_cache.summary_config,
            override_non_ok_state=config_cache.inventory_config.hwsw_parameters(
                host_name
            ).fail_status,
        )

    all_hosts = frozenset(
        itertools.chain(hosts_config.hosts, hosts_config.clusters, hosts_config.shadow_hosts)
    )
    for host_name in queue:
        if host_name not in all_hosts:
            console.verbose(f"  Removing mark '{host_name}' (host not configured")
            queue.remove(host_name)

    if queue.oldest() is None:
        console.verbose("Autoinventory: No hosts marked by inventory check")
        return

    console.verbose("Autoinventory: Inventorize all hosts marked by inventory check:")
    try:
        response = livestatus.LocalConnection().query("GET hosts\nColumns: name state")
        process_hosts: Container[HostName] = {
            HostName(name) for name, state in response if state == 0
        }
    except livestatus.MKLivestatusNotFoundError, livestatus.MKLivestatusSocketError:
        process_hosts = EVERYTHING

    section_plugins = SectionPluginMapper({**plugins.agent_sections, **plugins.snmp_sections})

    start = time.monotonic()
    limit = 120
    message = f"  Timeout of {limit} seconds reached. Let's do the remaining hosts next time."

    try:
        with Timeout(limit + 10, message=message):
            for host_name in queue:
                if time.monotonic() > start + limit:
                    raise TimeoutError(message)

                if host_name not in process_hosts:
                    continue

                execute_active_check_inventory(
                    host_name,
                    hosts_config=hosts_config,
                    parser=parser,
                    fetcher=fetcher,
                    summarizer=summarizer(host_name),
                    section_plugins=section_plugins,
                    inventory_plugins=plugins.inventory_plugins,
                    inventory_parameters=config_cache.inventory_config.plugin_parameters,
                    parameters=config_cache.inventory_config.hwsw_parameters(host_name),
                    raw_intervals_from_config=config_cache.inventory_config.retention_intervals(
                        host_name
                    ),
                    label_picker_configs=config_cache.inventory_config.label_picker_configs(
                        host_name
                    ),
                    rediscovery=DiscoverySettings.from_vs(
                        config_cache.discovery_check_parameters(host_name).rediscovery.get("mode")
                    ),
                    inventorized_host_labels_dir=cmk.utils.paths.inventorized_host_labels_dir,
                    discovered_host_labels_dir=cmk.utils.paths.discovered_host_labels_dir,
                    autodiscovery_dir=cmk.utils.paths.autodiscovery_dir,
                    debug=debug,
                )
    except (MKTimeout, TimeoutError) as exc:
        console.verbose_no_lf(str(exc), file=sys.stderr)


@dataclass(frozen=True, kw_only=True)
class _InventorizeMarkedHostsCommand:
    inventorize_marked_hosts: _InventorizeMarkedHosts

    def run(self, context: CLIContext, request: FetchRequest) -> CLIExitCode:
        try:
            self.inventorize_marked_hosts(
                request, omd_root=context.omd_root, debug=context.global_options.debug
            )
        except MKGeneralException as e:
            context.logger.error("%(error)s", {"error": e})  # noqa: TRY400
            if context.global_options.debug:
                raise
            return CLIExitCode.UNKNOWN
        return CLIExitCode.SUCCESS


cli_handler_inventory = CLIHandler(
    command=cli_command_inventory, run=_InventoryCommand(inventorize=_inventorize).run
)

cli_handler_inventorize_marked_hosts = CLIHandler(
    command=cli_command_inventorize_marked_hosts,
    run=_InventorizeMarkedHostsCommand(inventorize_marked_hosts=_inventorize_marked_hosts).run,
)
