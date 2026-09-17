#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""The dumping commands: --dump-agent and --dump."""

import itertools
import logging
import sys
from collections.abc import Iterable
from pathlib import Path

import cmk.base.dump_host
import cmk.livestatus_client as livestatus
import cmk.utils.password_store
import cmk.utils.paths
from cmk.base import config
from cmk.base.base_app import CheckmkBaseApp
from cmk.base.config import handle_ip_lookup_failure
from cmk.base.configlib.fetchers import make_parsed_snmp_fetch_intervals_config
from cmk.base.configlib.servicename import make_final_service_name_config
from cmk.base.modes.check_mk import (
    FETCHER_OPTIONS,
    forced_ip_lookup,
    handle_fetcher_options,
    host_address,
    host_addresses,
    load_checks,
    parse_snmp_backend,
    set_fake_dns,
    SNMP_BACKEND_OPTION,
)
from cmk.ccc.exceptions import MKBailOut, OnError
from cmk.ccc.hostaddress import HostName
from cmk.checkengine.fetcher_abc import Mode as FetchMode
from cmk.checkengine.fetcher_utils.secrets import AdHocSecrets, StoredSecrets
from cmk.checkengine.fetchers.snmp import NoSelectedSNMPSections, SNMPFetcherConfig
from cmk.checkengine.fetchers.tcp import TLSConfig
from cmk.checkengine.filecache import MaxAge
from cmk.checkengine.helper_interface import FetcherType
from cmk.checkengine.parser import make_parser, NO_SELECTION, parse_raw_data, SectionStore
from cmk.checkengine.source_builder import SourceBuilder
from cmk.checkengine.summarize import summarize
from cmk.cli.engine.modes import write_stdout
from cmk.cli.internal import Args, CLICommand, GlobalOptions, Options
from cmk.ruleset_matcher.matcher import BundledHostRulesetMatcher
from cmk.server_side_calls_backend import ExecutableFinder, load_secrets_file
from cmk.utils import ip_lookup, timeperiod
from cmk.utils.ip_lookup import ConfiguredIPLookup
from cmk.utils.log import console

# .
#   .--dump-agent----------------------------------------------------------.
#   |        _                                                    _        |
#   |     __| |_   _ _ __ ___  _ __         __ _  __ _  ___ _ __ | |_      |
#   |    / _` | | | | '_ ` _ \| '_ \ _____ / _` |/ _` |/ _ \ '_ \| __|     |
#   |   | (_| | |_| | | | | | | |_) |_____| (_| | (_| |  __/ | | | |_      |
#   |    \__,_|\__,_|_| |_| |_| .__/       \__,_|\__, |\___|_| |_|\__|     |
#   |                         |_|                |___/                     |
#   '----------------------------------------------------------------------'


def _mode_dump_agent(
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

    plugins = load_checks()
    loading_result = config.load()
    loaded_config = loading_result.loaded_config
    ruleset_matcher = loading_result.config_cache.ruleset_matcher
    label_manager = loading_result.config_cache.label_manager
    hosts_config = config.make_hosts_config(loaded_config)

    if hostname in hosts_config.clusters:
        raise MKBailOut("Can not be used with cluster hosts")

    config_cache = loading_result.config_cache
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

    host_labels = label_manager.labels_of_host(hostname)
    relay_id = config.get_relay_id(host_labels)
    fetcher_trigger = app.make_fetcher_trigger(relay_id, cmk.utils.paths.trusted_ca_file)

    ip_lookup_config = config_cache.ip_lookup_config()
    ip_family = ip_lookup_config.default_address_family(hostname)
    ip_address_of_bare = forced_ip_lookup() or ip_lookup.make_lookup_ip_address(ip_lookup_config)
    ip_address_of = ip_lookup.ConfiguredIPLookup(
        ip_address_of_bare,
        allow_empty=(),
        error_handler=config.handle_ip_lookup_failure,
    )
    ip_address_of_mgmt = forced_ip_lookup() or ip_lookup.make_lookup_mgmt_board_ip_address(
        ip_lookup_config
    )
    ruleset_matcher.ruleset_optimizer.set_all_processed_hosts({hostname})

    ip_stack_config = ip_lookup_config.ip_stack_config(hostname)
    ipaddress = (
        None
        if ip_stack_config is ip_lookup.IPStackConfig.NO_IP
        else ip_address_of(hostname, ip_family)
    )
    check_interval = config_cache.check_mk_check_interval(hostname)
    section_cache_path = cmk.utils.paths.var_dir
    tls_config = TLSConfig(
        cas_dir=Path(cmk.utils.paths.agent_cas_dir),
        ca_store=Path(cmk.utils.paths.agent_cert_store),
        site_crt=Path(cmk.utils.paths.site_cert_file),
    )

    output = []
    # Show errors of problematic data sources
    has_errors = False
    secrets = (
        AdHocSecrets(
            path=cmk.utils.password_store.generate_ad_hoc_secrets_path(
                cmk.utils.paths.relative_tmp_dir
            ),
            secrets=load_secrets_file(cmk.utils.password_store.pending_secrets_path_site()),
        )
        if relay_id
        else StoredSecrets(
            path=cmk.utils.password_store.pending_secrets_path_site(),
            secrets=load_secrets_file(cmk.utils.password_store.pending_secrets_path_site()),
        )
    )

    for source in SourceBuilder(
        plugins,
        hostname,
        ip_family,
        ipaddress,
        ip_stack_config,
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
                    loading_result.loaded_config,
                    config_cache.ruleset_matcher,
                    config_cache.label_manager.labels_of_host,
                ),
                # Note: 'usewalk' is not in the options of this mode. We use options.get() just for consistency.
                force_stored_walks=bool(options.get("usewalk", False)),
            ),
        ),
        simulation_mode=loaded_config.simulation_mode,
        file_cache_options=file_cache_options,
        file_cache_max_age=MaxAge(
            checking=loaded_config.check_max_cachefile_age,
            discovery=1.5 * check_interval,
            inventory=1.5 * check_interval,
        ),
        snmp_backend=config_cache.get_snmp_backend(hostname),
        file_cache_path_base=cmk.utils.paths.omd_root,
        file_cache_path_relative=cmk.utils.paths.relative_data_source_cache_dir,
        tcp_cache_path_relative=cmk.utils.paths.relative_tcp_cache_dir,
        tls_config=tls_config,
        computed_datasources=config_cache.computed_datasources(hostname),
        datasource_programs=config_cache.datasource_programs(hostname),
        tag_list=loading_result.host_tags.tag_list(hostname),
        management_ip=ip_address_of_mgmt(hostname, ip_family),
        management_protocol=config_cache.management_protocol(hostname),
        special_agent_command_lines=config_cache.special_agent_command_lines(
            hostname,
            ip_family,
            ipaddress,
            secrets_config=secrets,
            ip_address_of=ConfiguredIPLookup(
                ip_address_of_bare,
                allow_empty=hosts_config.clusters,
                error_handler=handle_ip_lookup_failure,
            ),
            executable_finder=ExecutableFinder(
                # NOTE: we can't ignore these, they're an API promise.
                cmk.utils.paths.local_special_agents_dir,
                cmk.utils.paths.special_agents_dir,
                prefix_map=(() if relay_id is None else ((cmk.utils.paths.omd_root, Path()),)),
            ),
            for_relay=relay_id is not None,
        ),
        is_pull_host=config_cache.is_pull_host(hostname),
        check_mk_check_interval=config_cache.check_mk_check_interval(hostname),
        metrics_association=config_cache.metrics_association(hostname),
        omd_root=cmk.utils.paths.omd_root,
    ).sources:
        source_info = source.source_info()
        if source_info.fetcher_type is FetcherType.SNMP:
            continue

        raw_data = fetcher_trigger.get_raw_data(
            source.file_cache(
                simulation=loaded_config.simulation_mode,
                file_cache_options=file_cache_options,
            ),
            source.fetcher(),
            FetchMode.CHECKING,
            secrets,
        )
        host_sections = parse_raw_data(
            make_parser(
                config.make_parser_config(
                    loaded_config,
                    ruleset_matcher,
                    label_manager,
                    ip_address_of=config_cache.primary_ip_address_of,
                ),
                source_info.hostname,
                source_info.ipaddress,
                source_info.fetcher_type,
                omd_root=cmk.utils.paths.omd_root,
                persisted_section_dir=SectionStore.make_persisted_section_dir(
                    source_info.hostname,
                    ident=source_info.ident,
                    section_cache_path=section_cache_path,
                ),
                keep_outdated=file_cache_options.keep_outdated,
            ),
            raw_data,
            selection=NO_SELECTION,
        )
        source_results = summarize(
            host_sections,
            config_cache.summary_config(hostname, source_info.ident),
            fetcher_type=source_info.fetcher_type,
        )
        if any(r.state != 0 for r in source_results):
            summaries = ", ".join(r.summary for r in source_results)
            console.error(f"ERROR [{source_info.ident}]: {summaries}", file=sys.stderr)
            has_errors = True
        if raw_data.is_ok():
            assert raw_data.ok is not None
            output.append(raw_data.ok)

    write_stdout(b"".join(output).decode(errors="surrogateescape"))
    if has_errors:
        sys.exit(1)
    return 0


cli_command_dump_agent = CLICommand(
    long_option="dump-agent",
    short_option="d",
    handler_function=_mode_dump_agent,
    argument=True,
    argument_descr="HOSTNAME|ADDRESS",
    sub_options=[*FETCHER_OPTIONS[:3], SNMP_BACKEND_OPTION],
    short_help="Show raw information from agent",
    long_help=[
        (
            "Shows the raw information received from the given host. For regular "
            "hosts it shows the agent output plus possible piggyback information. "
            "Does not work on clusters but only on real hosts. "
        )
    ],
)


# .
#   .--dump----------------------------------------------------------------.
#   |                         _                                            |
#   |                      __| |_   _ _ __ ___  _ __                       |
#   |                     / _` | | | | '_ ` _ \| '_ \                      |
#   |                    | (_| | |_| | | | | | | |_) |                     |
#   |                     \__,_|\__,_|_| |_| |_| .__/                      |
#   |                                          |_|                         |
#   '----------------------------------------------------------------------'


def _mode_dump_hosts(
    _app: object, global_options: GlobalOptions, _options: Options, args: Args
) -> int:
    set_fake_dns(global_options.fake_dns)
    hostlist: Iterable[HostName] = host_addresses(args)
    logger = logging.getLogger("cmk.base.modes")  # this might go nowhere.
    plugins = load_checks()
    loading_result = config.load()
    loaded_config = loading_result.loaded_config
    ruleset_matcher = loading_result.config_cache.ruleset_matcher
    label_manager = loading_result.config_cache.label_manager
    config_cache = loading_result.config_cache
    core_objects_config = config.CoreObjectsConfig(loaded_config, ruleset_matcher, label_manager)
    hosts_config = loading_result.hosts_config
    ip_lookup_config = config_cache.ip_lookup_config()

    ip_address_of = ip_lookup.ConfiguredIPLookup(
        forced_ip_lookup() or ip_lookup.make_lookup_ip_address(ip_lookup_config),
        allow_empty=hosts_config.clusters,
        error_handler=config.handle_ip_lookup_failure,
    )
    ip_address_of_mgmt = forced_ip_lookup() or ip_lookup.make_lookup_mgmt_board_ip_address(
        ip_lookup_config
    )

    all_hosts = {
        hn
        for hn in itertools.chain(hosts_config.hosts, hosts_config.clusters)
        if config_cache.is_active(hn) and config_cache.is_online(hn)
    }
    hosts = set(hostlist)
    if not hosts:
        hosts = all_hosts

    ruleset_matcher.ruleset_optimizer.set_all_processed_hosts(hosts)
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
    for hostname in sorted(hosts - all_hosts):
        sys.stderr.write(f"unknown host: {hostname}\n")
    for hostname in sorted(hosts & all_hosts):
        cmk.base.dump_host.dump_host(
            loading_result.loaded_config,
            loading_result.hosts_config,
            loading_result.host_tags,
            config_cache,
            core_objects_config,
            service_name_config,
            enforced_services_table,
            plugins,
            hostname,
            ip_lookup_config.ip_stack_config(hostname),
            ip_lookup_config.default_address_family(hostname),
            ip_address_of=ip_address_of,
            ip_address_of_mgmt=ip_address_of_mgmt,
            simulation_mode=loaded_config.simulation_mode,
            timeperiod_active=timeperiod.TimeperiodActiveCoreLookup(
                livestatus.get_optional_timeperiods_active_map, log=logger.warning
            ).get,
        )
    return 0


cli_command_dump = CLICommand(
    long_option="dump",
    short_option="D",
    handler_function=_mode_dump_hosts,
    argument=True,
    argument_descr="H1 H2...",
    argument_optional=True,
    short_help="Dump info about all or some hosts",
    long_help=[
        (
            "Dumps out the complete configuration and information "
            "about one, several or all hosts. It shows all services, hostgroups, "
            "contacts and other information about that host."
        ),
    ],
)
