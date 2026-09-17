#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""The service discovery commands: --check-discovery and --discover."""

import itertools
import sys
from collections.abc import Callable, Iterable, Mapping, Sequence
from contextlib import suppress

import cmk.ccc.debug
import cmk.utils.password_store
import cmk.utils.paths
from cmk.base import config
from cmk.base.base_app import CheckmkBaseApp
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
from cmk.base.errorhandling import CheckResultErrorHandler, create_section_crash_dump
from cmk.base.modes.check_mk import (
    DiscoveryOptions,
    extract_plugin_selection,
    FETCHER_OPTIONS,
    forced_ip_lookup,
    get_plugins_option,
    handle_fetcher_options,
    host_address,
    load_checks,
    option_detect_plugins,
    option_sections,
    parse_snmp_backend,
    set_fake_dns,
    SNMP_BACKEND_OPTION,
)
from cmk.ccc.config_path import VersionedConfigPath
from cmk.ccc.cpu_tracking import CPUTracker
from cmk.ccc.exceptions import MKBailOut, OnError
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
from cmk.cli.engine.modes import option_count, option_names, option_string
from cmk.cli.internal import Args, CLICommand, CLIOption, GlobalOptions, Options
from cmk.ruleset_matcher.matcher import BundledHostRulesetMatcher
from cmk.server_side_calls_backend import load_secrets_file
from cmk.utils import ip_lookup
from cmk.utils.log import console

# .
#   .--check-discovery-----------------------------------------------------.
#   |       _     _               _ _                                      |
#   |   ___| |__ | | __        __| (_)___  ___ _____   _____ _ __ _   _    |
#   |  / __| '_ \| |/ / _____ / _` | / __|/ __/ _ \ \ / / _ \ '__| | | |   |
#   | | (__| | | |   < |_____| (_| | \__ \ (_| (_) \ V /  __/ |  | |_| |   |
#   |  \___|_| |_|_|\_(_)     \__,_|_|___/\___\___/ \_/ \___|_|   \__, |   |
#   |                                                             |___/    |
#   '----------------------------------------------------------------------'


def _write_active_check_result(check_result: ActiveCheckResult) -> ServiceState:
    with suppress(IOError):
        sys.stdout.write(check_result.as_text() + "\n")
        sys.stdout.flush()
    return check_result.state


def _mode_check_discovery(
    app: CheckmkBaseApp, global_options: GlobalOptions, options: Options, args: Args
) -> int:
    set_fake_dns(global_options.fake_dns)
    raw_host_name = args[0]
    hostname = host_address(raw_host_name)
    file_cache_options = handle_fetcher_options(options)
    try:
        snmp_backend_override = parse_snmp_backend(options.get("snmp-backend"))
    except ValueError as exc:
        raise MKBailOut("Unknown SNMP backend") from exc

    # We do not resolve the `latest` link here, as any given serial might be removed by the core.
    latest_config_path = VersionedConfigPath.make_latest_path(cmk.utils.paths.omd_root)

    plugins = load_checks()
    loading_result = config.load()
    loaded_config = loading_result.loaded_config
    config_cache = loading_result.config_cache
    ruleset_matcher = config_cache.ruleset_matcher
    label_manager = config_cache.label_manager
    hosts_config = loading_result.hosts_config
    if hostname not in hosts_config.all_configured_hosts:
        # There is no configuration to discover from, hence no data source to contact.
        # Such a host must not be reported as "all up to date".
        return _write_active_check_result(
            ActiveCheckResult(state=3, summary=f"Unknown host: {hostname}")
        )

    host_tags = loading_result.host_tags
    set_global_logwatch_config(
        loaded_config,
        ruleset_matcher,
        label_manager,
        omd_root=cmk.utils.paths.omd_root,
        var_dir=cmk.utils.paths.var_dir,
        debug=cmk.ccc.debug.enabled(),
    )

    ruleset_matcher.ruleset_optimizer.set_all_processed_hosts({hostname})
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
    ip_lookup_config = config_cache.ip_lookup_config()
    ip_address_of = ip_lookup.ConfiguredIPLookup(
        forced_ip_lookup() or ip_lookup.make_lookup_ip_address(ip_lookup_config),
        allow_empty=hosts_config.clusters,
        error_handler=config.handle_ip_lookup_failure,
    )
    check_interval = config_cache.check_mk_check_interval(hostname)
    discovery_file_cache_max_age = 1.5 * check_interval if file_cache_options.use_outdated else 0
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
                backend_override=snmp_backend_override,
                base_path=cmk.utils.paths.omd_root,
                relative_stored_walk_path=cmk.utils.paths.relative_snmpwalks_dir,
                relative_walk_cache_path=cmk.utils.paths.relative_walk_cache_dir,
                relative_section_cache_path=cmk.utils.paths.relative_snmp_section_cache_dir,
                caching_config=make_parsed_snmp_fetch_intervals_config(
                    loaded_config, ruleset_matcher, label_manager.labels_of_host
                ),
                force_stored_walks=bool(options.get("usewalk", False)),
            ),
        ),
        plugins=plugins,
        clusters=hosts_config.clusters,
        default_address_family=ip_lookup_config.default_address_family,
        file_cache_options=file_cache_options,
        force_snmp_cache_refresh=False,
        get_ip_stack_config=ip_lookup_config.ip_stack_config,
        ip_address_of=ip_address_of,
        ip_address_of_mgmt=forced_ip_lookup()
        or ip_lookup.make_lookup_mgmt_board_ip_address(ip_lookup_config),
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
    )
    summarizer = CMKSummarizer(
        hostname,
        config_cache.summary_config,
        override_non_ok_state=None,
    )
    error_handler = CheckResultErrorHandler(
        exit_spec=config_cache.exit_code_spec(hostname),
        host_name=hostname,
        service_name="Check_MK Discovery",
        plugin_name="discover",
        is_cluster=hostname in hosts_config.clusters,
        snmp_backend=config_cache.get_snmp_backend(hostname),
        keepalive=False,
    )

    check_results: Sequence[ActiveCheckResult] = []
    with error_handler:
        fetched = fetcher(hostname, ip_address=None)
        with CPUTracker(console.debug) as tracker:
            check_results = execute_check_discovery(
                hostname,
                omd_root=cmk.utils.paths.omd_root,
                autodiscovery_dir=cmk.utils.paths.autodiscovery_dir,
                is_cluster=hostname in hosts_config.clusters,
                cluster_nodes=hosts_config.clusters.get(hostname, ()),
                params=config_cache.discovery_check_parameters(hostname),
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
                    rtc_package=None,
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
                ).read(),
                read_discovered_host_labels=label_manager.discovered_labels_of_host,
            )
        check_results = [
            *check_results,
            make_timing_results(
                tracker.duration,
                tuple((f[0], f[2]) for f in fetched),
                perfdata_with_times=loaded_config.check_mk_perfdata_with_times,
            ),
        ]

    if error_handler.result is not None:
        check_results = (error_handler.result,)

    return _write_active_check_result(ActiveCheckResult.from_subresults(*check_results))


cli_command_check_discovery = CLICommand(
    long_option="check-discovery",
    handler_function=_mode_check_discovery,
    argument=True,
    argument_descr="HOSTNAME",
    sub_options=[*FETCHER_OPTIONS, SNMP_BACKEND_OPTION],
    short_help="Check for not yet monitored services",
    long_help=[
        (
            "Make Check_MK behave as monitoring plug-ins that checks if an "
            "inventory would find new or vanished services for the host. "
            "If configured to do so, this will queue those hosts for automatic "
            "autodiscovery"
        )
    ],
)


def _discovery_options(parsed: Mapping[str, object]) -> DiscoveryOptions:
    options = DiscoveryOptions()
    if "cache" in parsed:
        options["cache"] = True
    if "no-cache" in parsed:
        options["no-cache"] = True
    if "no-tcp" in parsed:
        options["no-tcp"] = True
    if "usewalk" in parsed:
        options["usewalk"] = True
    if "snmp-backend" in parsed:
        options["snmp-backend"] = option_string(parsed, "snmp-backend") or ""
    if "detect-sections" in parsed:
        options["detect-sections"] = option_names(parsed, "detect-sections", SectionName)
    if "plugins" in parsed:
        options["plugins"] = option_names(parsed, "plugins", CheckPluginName)
    if "detect-plugins" in parsed:
        options["detect-plugins"] = option_names(parsed, "detect-plugins", str)
    if "discover" in parsed:
        options["discover"] = option_count(parsed, "discover")
    if "only-host-labels" in parsed:
        options["only-host-labels"] = True
    return options


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
    app: CheckmkBaseApp, global_options: GlobalOptions, parsed: Options, args: Args
) -> int:
    set_fake_dns(global_options.fake_dns)
    options = _discovery_options(parsed)
    plugins = load_checks()
    loading_result = config.load()
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
        debug=cmk.ccc.debug.enabled(),
    )

    discovery_config = DiscoveryConfig(
        ruleset_matcher,
        label_manager.labels_of_host,
        loaded_config.discovery_parameters,
    )
    hosts_config = config.make_hosts_config(loaded_config)
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
    ip_lookup_config = config_cache.ip_lookup_config()
    ip_address_of = ip_lookup.ConfiguredIPLookup(
        forced_ip_lookup() or ip_lookup.make_lookup_ip_address(ip_lookup_config),
        allow_empty=hosts_config.clusters,
        error_handler=config.handle_ip_lookup_failure,
    )

    hostnames = config.parse_hostname_list(config_cache, hosts_config, host_tags, args)
    if hostnames:
        # In case of discovery with host restriction, do not use the cache
        # file by default as -I and -II are used for debugging.
        file_cache_options = FileCacheOptions(disabled=True, use_outdated=False)
        config_cache.ruleset_matcher.ruleset_optimizer.set_all_processed_hosts(set(hostnames))
    else:
        # In case of discovery without host restriction, use the cache file
        # by default. Otherwise Checkmk would have to connect to ALL hosts.
        file_cache_options = FileCacheOptions(disabled=False, use_outdated=True)

    file_cache_options = handle_fetcher_options(options, defaults=file_cache_options)
    try:
        snmp_backend_override = parse_snmp_backend(options.get("snmp-backend"))
    except ValueError as exc:
        raise MKBailOut("Unknown SNMP backend") from exc

    on_error = OnError.RAISE if cmk.ccc.debug.enabled() else OnError.WARN
    selected_sections, run_plugin_names = extract_plugin_selection(
        detect_plugins=options.get("detect-plugins"),
        detect_sections=options.get("detect-sections"),
        selected_plugins=options.get("plugins"),
        plugins=plugins.check_plugins,
        sections=itertools.chain(plugins.agent_sections.values(), plugins.snmp_sections.values()),
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
                        SNMPSectionName(n) for n in selected_sections if n in plugins.snmp_sections
                    )
                ),
                backend_override=snmp_backend_override,
                base_path=cmk.utils.paths.omd_root,
                relative_stored_walk_path=cmk.utils.paths.relative_snmpwalks_dir,
                relative_walk_cache_path=cmk.utils.paths.relative_walk_cache_dir,
                relative_section_cache_path=cmk.utils.paths.relative_snmp_section_cache_dir,
                caching_config=make_parsed_snmp_fetch_intervals_config(
                    loaded_config, ruleset_matcher, label_manager.labels_of_host
                ),
                force_stored_walks=bool(options.get("usewalk", False)),
            ),
        ),
        plugins=plugins,
        clusters=hosts_config.clusters,
        default_address_family=ip_lookup_config.default_address_family,
        file_cache_options=file_cache_options,
        force_snmp_cache_refresh=False,
        get_ip_stack_config=ip_lookup_config.ip_stack_config,
        ip_address_of=ip_address_of,
        ip_address_of_mgmt=forced_ip_lookup()
        or ip_lookup.make_lookup_mgmt_board_ip_address(ip_lookup_config),
        mode=(
            FetchMode.DISCOVERY if selected_sections is NO_SELECTION else FetchMode.FORCE_SECTIONS
        ),
        simulation_mode=loaded_config.simulation_mode,
        secrets_config_relay=AdHocSecrets(
            path=cmk.utils.password_store.generate_ad_hoc_secrets_path(
                cmk.utils.paths.relative_tmp_dir
            ),
            secrets=(
                secrets := load_secrets_file(cmk.utils.password_store.pending_secrets_path_site())
            ),
        ),
        secrets_config_site=StoredSecrets(
            path=cmk.utils.password_store.pending_secrets_path_site(),
            secrets=secrets,
        ),
    )
    any_failed = False
    known_hosts = frozenset(hosts_config.all_configured_hosts)
    for hostname in sorted(
        _preprocess_hostnames(
            frozenset(hostnames),
            is_cluster=lambda hn: hn in hosts_config.clusters,
            resolve_nodes=lambda hn: hosts_config.clusters.get(hn, ()),
            hosts_config=hosts_config,
            config_cache=config_cache,
            only_host_labels="only-host-labels" in options,
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
                rtc_package=None,
            )

        succeeded = commandline_discovery(
            hostname,
            clear_ruleset_matcher_caches=ruleset_matcher.clear_caches,
            parser=parser,
            fetcher=fetcher,
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
            arg_only_new=options["discover"] == 1,
            only_host_labels="only-host-labels" in options,
            on_error=on_error,
            autochecks_dir=cmk.utils.paths.autochecks_dir,
            discovered_host_labels_dir=cmk.utils.paths.discovered_host_labels_dir,
        )
        any_failed |= not succeeded

    return 1 if any_failed else 0


cli_command_discover = CLICommand(
    long_option="discover",
    short_option="I",
    handler_function=_mode_discover,
    argument=True,
    argument_descr="[-I] HOST1 HOST2...",
    argument_optional=True,
    sub_options=[
        *FETCHER_OPTIONS,
        SNMP_BACKEND_OPTION,
        CLIOption(
            long_option="discover",
            short_option="I",
            short_help="Delete existing services before starting discovery",
            repeat=True,
        ),
        option_sections,
        get_plugins_option(CheckPluginName),
        option_detect_plugins,
        CLIOption(
            long_option="only-host-labels",
            short_option="L",
            short_help="Restrict discovery to host labels only",
        ),
    ],
    short_help="Find new services",
    long_help=[
        (
            "Make Check_MK behave as monitoring plug-ins that checks if an "
            "inventory would find new or vanished services for the host. "
            "If configured to do so, this will queue those hosts for automatic "
            "autodiscovery"
        ),
        (
            "Can be restricted to certain check types. Write '--checks df -I' if "
            "you just want to look for new filesystems. Use 'cmk -L' for a "
            "list of all check types."
        ),
        (
            "Can also be restricted to only discovering new host labels. "
            "Use: '--only-host-labels' or '-L' "
        ),
        "-II does the same as -I but deletes all existing checks of the specified types and hosts.",
        (
            "Exits with 1 if the discovery failed for at least one host, or if one of "
            "a host's data sources could not be contacted -- the services of such a "
            "source are missing from the result. The discovery of the remaining hosts "
            "is carried out regardless."
        ),
    ],
)
