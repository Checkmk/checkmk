#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import contextlib
import itertools
import sys
from collections.abc import Callable, Iterable, Sequence
from contextlib import suppress
from pathlib import Path

import cmk.utils.password_store
import cmk.utils.paths
from cmk.base import config
from cmk.base.app import make_app
from cmk.base.checkers import (
    CMKFetcher,
    CMKParser,
    CMKSummarizer,
    DiscoveryPluginMapper,
    HostLabelPluginMapper,
    SectionPluginMapper,
)
from cmk.base.config import ConfigCache
from cmk.base.configlib.checkengine import DiscoveryConfig
from cmk.base.configlib.fetchers import make_parsed_snmp_fetch_intervals_config
from cmk.base.configlib.logwatch import set_global_logwatch_config
from cmk.base.configlib.servicename import make_final_service_name_config
from cmk.base.core.active_config_layout import (
    RELATIVE_PATH_SECRETS,
    RELATIVE_PATH_TRUSTED_CAS,
)
from cmk.base.errorhandling import (
    CheckResultErrorHandler,
    create_section_crash_dump,
    RecordingFetcher,
    serialize_fetched,
)
from cmk.ccc.config_path import VersionedConfigPath
from cmk.ccc.cpu_tracking import CPUTracker
from cmk.ccc.exceptions import MKBailOut, MKGeneralException, OnError
from cmk.ccc.hostaddress import HostName, Hosts
from cmk.checkengine.checking import make_timing_results
from cmk.checkengine.discovery import (
    AutochecksStore,
    commandline_discovery,
    execute_check_discovery,
)
from cmk.checkengine.fetcher_abc import Mode as FetchMode
from cmk.checkengine.fetcher_utils.secrets import AdHocSecrets, StoredSecrets
from cmk.checkengine.fetchers.snmp import NoSelectedSNMPSections, SNMPFetcherConfig
from cmk.checkengine.filecache import FileCacheOptions, MaxAge
from cmk.checkengine.parser import NO_SELECTION
from cmk.checkengine.plugins import CheckPluginName, SectionName
from cmk.checkengine.snmplib import SNMPSectionName
from cmk.checkengine.specs.checkresults import ActiveCheckResult, ServiceState
from cmk.cli.internal import Args as CLIArgs
from cmk.cli.internal import Context as CLIContext
from cmk.cli.internal import ExitCode as CLIExitCode
from cmk.cli.internal import GlobalOptions as CLIGlobalOptions
from cmk.cli.internal import Handler as CLIHandler
from cmk.plugins.checkmk.cli.agent_based import extract_plugin_selection, load_checks
from cmk.plugins.checkmk.cli.discovery import (
    CheckDiscoveryRequest,
    cli_command_check_discovery,
    cli_command_discover,
    DiscoverRequest,
)
from cmk.plugins.checkmk.cli.exit_code import state_exit_code
from cmk.plugins.checkmk.cli.options import host_address, make_file_cache_options
from cmk.ruleset_matcher.matcher import BundledHostRulesetMatcher
from cmk.server_side_calls_backend import load_secrets_file
from cmk.utils import ip_lookup
from cmk.utils.log import console


def _write_active_check_result(check_result: ActiveCheckResult) -> ServiceState:
    with suppress(IOError):
        sys.stdout.write(check_result.as_text() + "\n")
        sys.stdout.flush()
    return check_result.state


def _mode_check_discovery(
    omd_root: Path, global_options: CLIGlobalOptions, request: CheckDiscoveryRequest, args: CLIArgs
) -> CLIExitCode:
    app = make_app(omd_root)
    raw_host_name = args[0]
    hostname = host_address(raw_host_name)
    file_cache_options = make_file_cache_options(request.file_cache)

    # We do not resolve the `latest` link here, as any given serial might be removed by the core.
    latest_config_path = VersionedConfigPath.make_latest_path(cmk.utils.paths.omd_root)

    plugins = load_checks(debug=global_options.debug)
    loading_result = config.load(validate_hosts=True, debug=global_options.debug)
    loaded_config = loading_result.loaded_config
    config_cache = loading_result.config_cache
    ruleset_matcher = config_cache.ruleset_matcher
    label_manager = config_cache.label_manager
    hosts_config = loading_result.hosts_config
    if hostname not in hosts_config.all_configured_hosts:
        # There is no configuration to discover from, hence no data source to contact.
        # Such a host must not be reported as "all up to date".
        return state_exit_code(
            _write_active_check_result(
                ActiveCheckResult(state=3, summary=f"Unknown host: {hostname}")
            )
        )

    host_tags = loading_result.host_tags
    set_global_logwatch_config(
        loaded_config,
        ruleset_matcher,
        label_manager,
        omd_root=cmk.utils.paths.omd_root,
        var_dir=cmk.utils.paths.var_dir,
        debug=global_options.debug,
    )

    with ruleset_matcher.ruleset_optimizer.processed_hosts({hostname}):
        service_name_config = config_cache.make_passive_service_name_config(
            make_final_service_name_config(loaded_config, ruleset_matcher)
        )
        autochecks_config = config.AutochecksConfigurer(
            config_cache, plugins.check_plugins, service_name_config
        )
        enforced_services_table = config.EnforcedServicesTable(
            BundledHostRulesetMatcher(
                loaded_config.static_checks,
                ruleset_matcher,
                label_manager.labels_of_host,
            ),
            service_name_config,
            plugins.check_plugins,
            label_manager.labels_of_service,
        )

        discovery_config = DiscoveryConfig(
            ruleset_matcher,
            label_manager.labels_of_host,
            loaded_config.discovery_parameters,
        )
        ip_lookup_config = config_cache.ip_lookup_config(fake_dns=request.fake_dns)
        ip_address_of = ip_lookup.ConfiguredIPLookup(
            ip_lookup.make_lookup_ip_address(ip_lookup_config),
            allow_empty=hosts_config.clusters,
            error_handler=config.handle_ip_lookup_failure,
        )
        check_interval = config_cache.check_mk_check_interval(hostname)
        discovery_file_cache_max_age = (
            1.5 * check_interval if file_cache_options.use_outdated else 0
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
                enforced_services_table,
                SNMPFetcherConfig(
                    on_error=OnError.RAISE,
                    missing_sys_description=config_cache.missing_sys_description,
                    selected_sections=NoSelectedSNMPSections(),
                    backend_override=request.snmp_backend,
                    base_path=cmk.utils.paths.omd_root,
                    relative_stored_walk_path=cmk.utils.paths.relative_snmpwalks_dir,
                    relative_walk_cache_path=cmk.utils.paths.relative_walk_cache_dir,
                    relative_section_cache_path=cmk.utils.paths.relative_snmp_section_cache_dir,
                    caching_config=make_parsed_snmp_fetch_intervals_config(
                        loaded_config, ruleset_matcher, label_manager.labels_of_host
                    ),
                    force_stored_walks=request.usewalk,
                    debug=global_options.debug,
                ),
            ),
            plugins=plugins,
            clusters=hosts_config.clusters,
            default_address_family=ip_lookup_config.default_address_family,
            file_cache_options=file_cache_options,
            force_snmp_cache_refresh=False,
            get_ip_stack_config=ip_lookup_config.ip_stack_config,
            ip_address_of=ip_address_of,
            ip_address_of_mgmt=ip_lookup.make_lookup_mgmt_board_ip_address(ip_lookup_config),
            mode=FetchMode.DISCOVERY,
            simulation_mode=loaded_config.simulation_mode,
            max_cachefile_age=MaxAge(
                checking=loaded_config.check_max_cachefile_age,
                discovery=discovery_file_cache_max_age,
                inventory=1.5 * check_interval,
            ),
            secrets_config_relay=AdHocSecrets(
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
            debug=global_options.debug,
        )
        parser = CMKParser(
            config.make_parser_config(
                loading_result.loaded_config,
                ruleset_matcher,
                config_cache.label_manager,
                ip_address_of=config_cache.primary_ip_address_of,
            ),
            selected_sections=NO_SELECTION,
            keep_outdated=file_cache_options.keep_outdated,
            debug=global_options.debug,
        )
        summarizer = CMKSummarizer(
            hostname,
            config_cache.summary_config,
            override_non_ok_state=None,
        )
        recording_fetcher = RecordingFetcher(fetcher)
        error_handler = CheckResultErrorHandler(
            exit_spec=config_cache.exit_code_spec(hostname),
            host_name=hostname,
            service_name="Check_MK Discovery",
            plugin_name="discover",
            is_cluster=hostname in hosts_config.clusters,
            snmp_backend=config_cache.get_snmp_backend(hostname),
            keepalive=False,
            get_agent_output=lambda: recording_fetcher.serialized(hostname),
            debug=global_options.debug,
        )

        check_results: Sequence[ActiveCheckResult] = []
        with error_handler:
            fetched = recording_fetcher(hostname, ip_address=None)
            with CPUTracker(console.debug) as tracker:
                check_results = execute_check_discovery(
                    hostname,
                    omd_root=cmk.utils.paths.omd_root,
                    autodiscovery_dir=cmk.utils.paths.autodiscovery_dir,
                    is_cluster=hostname in hosts_config.clusters,
                    cluster_nodes=hosts_config.clusters.get(hostname, ()),
                    params=config_cache.discovery_check_parameters(hostname),
                    fetched=fetched,
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
                        get_agent_output=lambda: serialize_fetched(
                            (f.source, f.raw_data) for f in fetched
                        ),
                    ),
                    host_label_plugins=HostLabelPluginMapper(
                        discovery_config=discovery_config,
                        sections={**plugins.agent_sections, **plugins.snmp_sections},
                    ),
                    plugins=DiscoveryPluginMapper(
                        discovery_config=discovery_config,
                        check_plugins=plugins.check_plugins,
                    ),
                    autochecks_config=autochecks_config,
                    enforced_services=enforced_services_table(hostname),
                    read_autochecks=lambda hn: AutochecksStore(
                        hn, cmk.utils.paths.autochecks_dir
                    ).read(debug=global_options.debug),
                    read_discovered_host_labels=label_manager.discovered_labels_of_host,
                    debug=global_options.debug,
                )
            check_results = [
                *check_results,
                make_timing_results(
                    tracker.duration,
                    tuple((f.source, f.duration) for f in fetched),
                    perfdata_with_times=loaded_config.check_mk_perfdata_with_times,
                ),
            ]

        if error_handler.result is not None:
            check_results = (error_handler.result,)

        return state_exit_code(
            _write_active_check_result(ActiveCheckResult.from_subresults(*check_results))
        )


def _run_check_discovery(
    context: CLIContext, request: CheckDiscoveryRequest, args: CLIArgs
) -> CLIExitCode:
    try:
        return _mode_check_discovery(context.omd_root, context.global_options, request, args)
    except (MKBailOut, MKGeneralException) as e:
        context.logger.error("%(error)s", {"error": e})  # noqa: TRY400
        if context.global_options.debug:
            raise
        return CLIExitCode.UNKNOWN


def _preprocess_hostnames(
    arg_host_names: frozenset[HostName],
    is_cluster: Callable[[HostName], bool],
    resolve_nodes: Callable[[HostName], Iterable[HostName]],
    hosts_config: Hosts,
    config_cache: ConfigCache,
    only_host_labels: bool,
) -> set[HostName]:
    """Default to all hosts and expand cluster names to their nodes"""
    svc = "" if only_host_labels else "services and "
    if not arg_host_names:
        console.verbose(f"Discovering {svc}host labels on all hosts")
        return {
            hn
            for hn in hosts_config.hosts
            if config_cache.is_active(hn) and config_cache.is_online(hn)
        }
    node_names = {
        node_name
        for host_name in arg_host_names
        for node_name in (resolve_nodes(host_name) if is_cluster(host_name) else (host_name,))
    }
    console.verbose(f"Discovering {svc}host labels on: {', '.join(sorted(node_names))}")
    return node_names


def _mode_discover(
    omd_root: Path, global_options: CLIGlobalOptions, request: DiscoverRequest, args: CLIArgs
) -> CLIExitCode:
    app = make_app(omd_root)
    plugins = load_checks(debug=global_options.debug)
    loading_result = config.load(validate_hosts=True, debug=global_options.debug)
    loaded_config = loading_result.loaded_config
    hosts_config = loading_result.hosts_config
    host_tags = loading_result.host_tags
    ruleset_matcher = loading_result.config_cache.ruleset_matcher
    label_manager = loading_result.config_cache.label_manager
    config_cache = loading_result.config_cache
    set_global_logwatch_config(
        loaded_config,
        ruleset_matcher,
        label_manager,
        omd_root=cmk.utils.paths.omd_root,
        var_dir=cmk.utils.paths.var_dir,
        debug=global_options.debug,
    )

    discovery_config = DiscoveryConfig(
        ruleset_matcher,
        label_manager.labels_of_host,
        loaded_config.discovery_parameters,
    )
    service_name_config = config_cache.make_passive_service_name_config(
        make_final_service_name_config(loaded_config, ruleset_matcher)
    )
    enforced_services_table = config.EnforcedServicesTable(
        BundledHostRulesetMatcher(
            loaded_config.static_checks,
            ruleset_matcher,
            label_manager.labels_of_host,
        ),
        service_name_config,
        plugins.check_plugins,
        label_manager.labels_of_service,
    )
    ip_lookup_config = config_cache.ip_lookup_config(fake_dns=request.fake_dns)
    ip_address_of = ip_lookup.ConfiguredIPLookup(
        ip_lookup.make_lookup_ip_address(ip_lookup_config),
        allow_empty=hosts_config.clusters,
        error_handler=config.handle_ip_lookup_failure,
    )

    hostnames = config.parse_hostname_list(config_cache, hosts_config, host_tags, args)
    if hostnames:
        # In case of discovery with host restriction, do not use the cache
        # file by default as -I and -II are used for debugging.
        file_cache_options = FileCacheOptions(disabled=True, use_outdated=False)
    else:
        # In case of discovery without host restriction, use the cache file
        # by default. Otherwise Checkmk would have to connect to ALL hosts.
        file_cache_options = FileCacheOptions(disabled=False, use_outdated=True)

    with (
        ruleset_matcher.ruleset_optimizer.processed_hosts(hostnames)
        if hostnames
        else contextlib.nullcontext()
    ):
        file_cache_options = make_file_cache_options(
            request.file_cache, defaults=file_cache_options
        )

        on_error = OnError.RAISE if global_options.debug else OnError.WARN
        selected_sections, run_plugin_names = extract_plugin_selection(
            detect_plugins=request.plugin_selection.detect_plugins,
            detect_sections=request.plugin_selection.detect_sections,
            selected_plugins=request.plugin_selection.plugins,
            plugins=plugins.check_plugins,
            sections=itertools.chain(
                plugins.agent_sections.values(), plugins.snmp_sections.values()
            ),
            type_=CheckPluginName,
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
            debug=global_options.debug,
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
                enforced_services_table,
                SNMPFetcherConfig(
                    on_error=on_error,
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
                    backend_override=request.snmp_backend,
                    base_path=cmk.utils.paths.omd_root,
                    relative_stored_walk_path=cmk.utils.paths.relative_snmpwalks_dir,
                    relative_walk_cache_path=cmk.utils.paths.relative_walk_cache_dir,
                    relative_section_cache_path=cmk.utils.paths.relative_snmp_section_cache_dir,
                    caching_config=make_parsed_snmp_fetch_intervals_config(
                        loaded_config, ruleset_matcher, label_manager.labels_of_host
                    ),
                    force_stored_walks=request.usewalk,
                    debug=global_options.debug,
                ),
            ),
            plugins=plugins,
            clusters=hosts_config.clusters,
            default_address_family=ip_lookup_config.default_address_family,
            file_cache_options=file_cache_options,
            force_snmp_cache_refresh=False,
            get_ip_stack_config=ip_lookup_config.ip_stack_config,
            ip_address_of=ip_address_of,
            ip_address_of_mgmt=ip_lookup.make_lookup_mgmt_board_ip_address(ip_lookup_config),
            mode=(
                FetchMode.DISCOVERY
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
                path=cmk.utils.password_store.pending_secrets_path_site(),
                secrets=secrets,
            ),
            debug=global_options.debug,
        )
        recording_fetcher = RecordingFetcher(fetcher)
        any_failed = False
        known_hosts = frozenset(hosts_config.all_configured_hosts)
        for hostname in sorted(
            _preprocess_hostnames(
                frozenset(hostnames),
                is_cluster=lambda hn: hn in hosts_config.clusters,
                resolve_nodes=lambda hn: hosts_config.clusters.get(hn, ()),
                hosts_config=hosts_config,
                config_cache=config_cache,
                only_host_labels=request.only_host_labels,
            )
        ):
            if hostname not in known_hosts:
                sys.stderr.write(f"unknown host: {hostname}\n")
                any_failed = True
                continue

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

            succeeded = commandline_discovery(
                hostname,
                clear_ruleset_matcher_caches=ruleset_matcher.clear_caches,
                parser=parser,
                fetcher=recording_fetcher,
                section_plugins=SectionPluginMapper(
                    {**plugins.agent_sections, **plugins.snmp_sections}
                ),
                section_error_handling=section_error_handling,
                host_label_plugins=HostLabelPluginMapper(
                    discovery_config=discovery_config,
                    sections={**plugins.agent_sections, **plugins.snmp_sections},
                ),
                plugins=DiscoveryPluginMapper(
                    discovery_config=discovery_config,
                    check_plugins=plugins.check_plugins,
                ),
                run_plugin_names=run_plugin_names,
                autochecks_config=config.AutochecksConfigurer(
                    config_cache, plugins.check_plugins, service_name_config
                ),
                enforced_services=enforced_services_table(hostname),
                arg_only_new=request.discover == 1,
                only_host_labels=request.only_host_labels,
                on_error=on_error,
                autochecks_dir=cmk.utils.paths.autochecks_dir,
                discovered_host_labels_dir=cmk.utils.paths.discovered_host_labels_dir,
                inventorized_host_labels_dir=cmk.utils.paths.inventorized_host_labels_dir,
                debug=global_options.debug,
            )
            any_failed |= not succeeded

        return CLIExitCode.FAILURE if any_failed else CLIExitCode.SUCCESS


def _run_discover(context: CLIContext, request: DiscoverRequest, args: CLIArgs) -> CLIExitCode:
    try:
        return _mode_discover(context.omd_root, context.global_options, request, args)
    except (MKBailOut, MKGeneralException) as e:
        context.logger.error("%(error)s", {"error": e})  # noqa: TRY400
        if context.global_options.debug:
            raise
        return CLIExitCode.UNKNOWN


cli_handler_check_discovery = CLIHandler(
    command=cli_command_check_discovery, run=_run_check_discovery
)

cli_handler_discover = CLIHandler(command=cli_command_discover, run=_run_discover)
