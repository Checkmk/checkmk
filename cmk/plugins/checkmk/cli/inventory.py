#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""The HW/SW inventory commands: --inventory and --inventorize-marked-hosts."""

import dataclasses
import itertools
import time
from collections.abc import Container, Mapping, Sequence

import cmk.ccc.cleanup
import cmk.ccc.debug
import cmk.livestatus_client as livestatus
import cmk.utils.password_store
import cmk.utils.paths
from cmk.base import config
from cmk.base.base_app import CheckmkBaseApp
from cmk.base.checkers import CMKFetcher, CMKParser, CMKSummarizer, SectionPluginMapper
from cmk.base.configlib.fetchers import make_parsed_snmp_fetch_intervals_config
from cmk.base.configlib.servicename import make_final_service_name_config
from cmk.base.core.active_config_layout import (
    RELATIVE_PATH_SECRETS,
    RELATIVE_PATH_TRUSTED_CAS,
)
from cmk.base.errorhandling import create_section_crash_dump
from cmk.base.modes.check_mk import (
    execute_active_check_inventory,
    extract_plugin_selection,
    FETCHER_OPTIONS,
    forced_ip_lookup,
    get_plugins_option,
    handle_fetcher_options,
    InventoryOptions,
    load_checks,
    option_detect_plugins,
    option_sections,
    parse_snmp_backend,
    set_fake_dns,
    SNMP_BACKEND_OPTION,
)
from cmk.ccc.config_path import VersionedConfigPath
from cmk.ccc.exceptions import MKBailOut, MKTimeout, OnError
from cmk.ccc.hostaddress import HostName
from cmk.ccc.timeout import Timeout
from cmk.checkengine import inventory
from cmk.checkengine.auto_queue import AutoQueue
from cmk.checkengine.fetcher_abc import Mode as FetchMode
from cmk.checkengine.fetcher_utils.secrets import AdHocSecrets, StoredSecrets
from cmk.checkengine.fetchers.snmp import NoSelectedSNMPSections, SNMPFetcherConfig
from cmk.checkengine.parser import NO_SELECTION
from cmk.checkengine.plugins import InventoryPluginName, SectionName
from cmk.checkengine.snmplib import SNMPSectionName
from cmk.checkengine.specs.checkresults import ActiveCheckResult
from cmk.cli.engine.modes import option_names, option_string
from cmk.cli.internal import Args, CLICommand, CLIOption, GlobalOptions, Options
from cmk.inventory.paths import Paths as InventoryPaths
from cmk.inventory.structured_data import InventoryStore
from cmk.ruleset_matcher.matcher import BundledHostRulesetMatcher
from cmk.server_side_calls_backend import load_secrets_file
from cmk.utils import ip_lookup
from cmk.utils.everythingtype import EVERYTHING
from cmk.utils.log import console, section

# .
#   .--inventory-----------------------------------------------------------.
#   |             _                      _                                 |
#   |            (_)_ ____   _____ _ __ | |_ ___  _ __ _   _               |
#   |            | | '_ \ \ / / _ \ '_ \| __/ _ \| '__| | | |              |
#   |            | | | | \ V /  __/ | | | || (_) | |  | |_| |              |
#   |            |_|_| |_|\_/ \___|_| |_|\__\___/|_|   \__, |              |
#   |                                                  |___/               |
#   '----------------------------------------------------------------------'


def _inventory_options(parsed: Mapping[str, object]) -> InventoryOptions:
    options = InventoryOptions()
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
    if "force" in parsed:
        options["force"] = True
    if "detect-sections" in parsed:
        options["detect-sections"] = option_names(parsed, "detect-sections", SectionName)
    if "plugins" in parsed:
        options["plugins"] = option_names(parsed, "plugins", InventoryPluginName)
    if "detect-plugins" in parsed:
        options["detect-plugins"] = option_names(parsed, "detect-plugins", str)
    return options


def _mode_inventory(
    app: CheckmkBaseApp, global_options: GlobalOptions, parsed: Options, args: Args
) -> int:
    set_fake_dns(global_options.fake_dns)
    options = _inventory_options(parsed)
    file_cache_options = handle_fetcher_options(options)
    try:
        snmp_backend_override = parse_snmp_backend(options.get("snmp-backend"))
    except ValueError as exc:
        raise MKBailOut("Unknown SNMP backend") from exc

    plugins = load_checks()
    loading_result = config.load()
    loaded_config = loading_result.loaded_config
    host_tags = loading_result.host_tags
    ruleset_matcher = loading_result.config_cache.ruleset_matcher
    label_manager = loading_result.config_cache.label_manager
    config_cache = loading_result.config_cache

    hosts_config = config.make_hosts_config(loaded_config)
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
    ip_lookup_config = config_cache.ip_lookup_config()
    ip_address_of = ip_lookup.ConfiguredIPLookup(
        forced_ip_lookup() or ip_lookup.make_lookup_ip_address(ip_lookup_config),
        allow_empty=hosts_config.clusters,
        error_handler=config.handle_ip_lookup_failure,
    )

    if args:
        hostnames = config.parse_hostname_list(
            config_cache, hosts_config, host_tags, args, with_clusters=True
        )
        config_cache.ruleset_matcher.ruleset_optimizer.set_all_processed_hosts(set(hostnames))
        console.verbose(f"Doing HW/SW Inventory on: {', '.join(hostnames)}")
    else:
        # No hosts specified: do all hosts and force caching
        hostnames = sorted(
            {
                hn
                for hn in itertools.chain(hosts_config.hosts, hosts_config.clusters)
                if config_cache.is_active(hn) and config_cache.is_online(hn)
            }
        )
        console.verbose("Doing HW/SW Inventory on all hosts")

    if "force" in options:
        file_cache_options = dataclasses.replace(file_cache_options, keep_outdated=True)

    selected_sections, run_plugin_names = extract_plugin_selection(
        detect_plugins=options.get("detect-plugins"),
        detect_sections=options.get("detect-sections"),
        selected_plugins=options.get("plugins"),
        plugins=plugins.inventory_plugins,
        sections=itertools.chain(plugins.agent_sections.values(), plugins.snmp_sections.values()),
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
            SNMPFetcherConfig(
                on_error=OnError.RAISE,
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
        ip_address_of_mandatory=forced_ip_lookup()
        or ip_lookup.make_lookup_ip_address(ip_lookup_config),
        ip_address_of_mgmt=forced_ip_lookup()
        or ip_lookup.make_lookup_mgmt_board_ip_address(ip_lookup_config),
        mode=(
            FetchMode.INVENTORY if selected_sections is NO_SELECTION else FetchMode.FORCE_SECTIONS
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
            path=cmk.utils.password_store.pending_secrets_path_site(), secrets=secrets
        ),
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
                rtc_package=None,
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
                    fetcher=fetcher,
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
                ).check_results

            check_result = ActiveCheckResult.from_subresults(*check_results)
            if check_result.state:
                section.section_error(check_result.summary)
            else:
                section.section_success(check_result.summary)

        except Exception as e:
            if cmk.ccc.debug.enabled():
                raise
            section.section_error("%s" % e)
        finally:
            cmk.ccc.cleanup.cleanup_globals()
    return 0


cli_command_inventory = CLICommand(
    long_option="inventory",
    short_option="i",
    handler_function=_mode_inventory,
    argument=True,
    argument_descr="HOST1 HOST2...",
    argument_optional=True,
    sub_options=[
        *FETCHER_OPTIONS,
        SNMP_BACKEND_OPTION,
        CLIOption(
            long_option="force",
            short_option="f",
            short_help="Use cached agent data even if it's outdated.",
        ),
        option_sections,
        get_plugins_option(InventoryPluginName),
        option_detect_plugins,
    ],
    short_help="Do a HW/SW Inventory on some or all hosts",
    long_help=[
        (
            "Does a HW/SW Inventory for all, one or several "
            "hosts. If you add the option -f, --force then persisted sections "
            "will be used even if they are outdated."
        )
    ],
)


def _mode_inventorize_marked_hosts(
    app: CheckmkBaseApp, global_options: GlobalOptions, options: Options, _args: Args
) -> int:
    set_fake_dns(global_options.fake_dns)
    file_cache_options = handle_fetcher_options(options)
    try:
        snmp_backend_override = parse_snmp_backend(options.get("snmp-backend"))
    except ValueError as exc:
        raise MKBailOut("Unknown SNMP backend") from exc

    if not (queue := AutoQueue(InventoryPaths(cmk.utils.paths.omd_root).auto_dir)):
        console.verbose("Autoinventory: No hosts marked by inventory check")
        return 0

    # We do not resolve the `latest` link here, as any given serial might be removed by the core.
    latest_config_path = VersionedConfigPath.make_latest_path(cmk.utils.paths.omd_root)

    plugins = load_checks()
    loading_result = config.load()
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
    ip_lookup_config = config_cache.ip_lookup_config()
    ip_address_of = ip_lookup.ConfiguredIPLookup(
        forced_ip_lookup() or ip_lookup.make_lookup_ip_address(ip_lookup_config),
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
            SNMPFetcherConfig(
                on_error=OnError.RAISE,
                missing_sys_description=config_cache.missing_sys_description,
                selected_sections=(NoSelectedSNMPSections()),
                backend_override=snmp_backend_override,
                base_path=cmk.utils.paths.var_dir,
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
        ip_address_of_mandatory=forced_ip_lookup()
        or ip_lookup.make_lookup_ip_address(ip_lookup_config),
        ip_address_of_mgmt=forced_ip_lookup()
        or ip_lookup.make_lookup_mgmt_board_ip_address(ip_lookup_config),
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
        return 0

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
                )
    except (MKTimeout, TimeoutError) as exc:
        console.verbose_no_lf(str(exc))
    return 0


cli_command_inventorize_marked_hosts = CLICommand(
    long_option="inventorize-marked-hosts",
    handler_function=_mode_inventorize_marked_hosts,
    sub_options=[*FETCHER_OPTIONS, SNMP_BACKEND_OPTION],
    short_help="Run inventory for hosts which previously had no tree data",
    long_help=[
        "Run actual service HW/SW Inventory on all hosts that had no tree data",
        "in the previous run",
    ],
)
