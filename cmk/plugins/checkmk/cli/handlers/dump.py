#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import itertools
import logging
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

import cmk.base.dump_host
import cmk.livestatus_client as livestatus
import cmk.utils.password_store
import cmk.utils.paths
from cmk.base import config
from cmk.base.app import make_app
from cmk.base.config import handle_ip_lookup_failure
from cmk.base.configlib.servicename import make_final_service_name_config
from cmk.ccc.exceptions import MKBailOut, MKGeneralException, OnError
from cmk.ccc.hostaddress import HostAddress
from cmk.checkengine.fetcher_abc import Mode as FetchMode
from cmk.checkengine.fetcher_utils.secrets import AdHocSecrets, StoredSecrets
from cmk.checkengine.fetchers.snmp import NoSelectedSNMPSections
from cmk.checkengine.fetchers.tcp import TLSConfig
from cmk.checkengine.filecache import MaxAge
from cmk.checkengine.helper_interface import FetcherType
from cmk.checkengine.parser import make_parser, NO_SELECTION, parse_raw_data, SectionStore
from cmk.checkengine.source_builder import SourceBuilder
from cmk.checkengine.specs.checkresults import ActiveCheckResult
from cmk.checkengine.summarize import summarize
from cmk.cli.internal import Context as CLIContext
from cmk.cli.internal import ExitCode as CLIExitCode
from cmk.cli.internal import Handler as CLIHandler
from cmk.plugins.checkmk.cli.dump import (
    cli_command_dump,
    cli_command_dump_agent,
    DumpAgentRequest,
    DumpHostsRequest,
)
from cmk.plugins.checkmk.cli.output import write_stdout
from cmk.ruleset_matcher.matcher import BundledHostRulesetMatcher
from cmk.server_side_calls_backend import ExecutableFinder, load_secrets_file
from cmk.utils import ip_lookup, timeperiod
from cmk.utils.ip_lookup import ConfiguredIPLookup
from cmk.utils.log import console

from ._file_cache import make_file_cache_options
from ._snmp_fetcher import snmp_fetcher_config
from .agent_based import load_checks


@dataclass(frozen=True)
class _AgentDump:
    output: bytes
    warnings: Sequence[str]
    errors: Sequence[str]


def _source_dump(ident: str, output: bytes, results: Sequence[ActiveCheckResult]) -> _AgentDump:
    summaries = ", ".join(r.summary for r in results)
    if any(r.state not in (0, 1) for r in results):
        return _AgentDump(output, (), (f"ERROR [{ident}]: {summaries}",))
    if any(r.state == 1 for r in results):
        return _AgentDump(output, (f"WARNING [{ident}]: {summaries}",), ())
    return _AgentDump(output, (), ())


class _DumpAgent(Protocol):
    def __call__(
        self, host: HostAddress, /, request: DumpAgentRequest, *, omd_root: Path, debug: bool
    ) -> _AgentDump: ...


def _dump_agent(
    hostname: HostAddress, request: DumpAgentRequest, *, omd_root: Path, debug: bool
) -> _AgentDump:
    app = make_app(omd_root)
    file_cache_options = make_file_cache_options(request.file_cache)

    plugins = load_checks(debug=debug)
    loading_result = config.load(validate_hosts=True, debug=debug)
    loaded_config = loading_result.loaded_config
    ruleset_matcher = loading_result.config_cache.ruleset_matcher
    label_manager = loading_result.config_cache.label_manager
    hosts_config = loading_result.hosts_config

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

    ip_lookup_config = config_cache.ip_lookup_config(fake_dns=request.fake_dns)
    ip_family = ip_lookup_config.default_address_family(hostname)
    ip_address_of_bare = ip_lookup.make_lookup_ip_address(ip_lookup_config)
    ip_address_of = ip_lookup.ConfiguredIPLookup(
        ip_address_of_bare,
        allow_empty=(),
        error_handler=config.handle_ip_lookup_failure,
    )
    ip_address_of_mgmt = ip_lookup.make_lookup_mgmt_board_ip_address(ip_lookup_config)
    with ruleset_matcher.ruleset_optimizer.processed_hosts({hostname}):
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

        dumps = []

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
                snmp_fetcher_config(
                    loading_result,
                    NoSelectedSNMPSections(),
                    on_error=OnError.RAISE,
                    backend_override=request.snmp_backend,
                    force_stored_walks=False,
                    debug=debug,
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
                debug=debug,
            ).raw_data
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
                    cached_at=None,
                    omd_root=cmk.utils.paths.omd_root,
                    persisted_section_dir=SectionStore.make_persisted_section_dir(
                        source_info.hostname,
                        ident=source_info.ident,
                        section_cache_path=section_cache_path,
                    ),
                    keep_outdated=file_cache_options.keep_outdated,
                    debug=debug,
                ),
                raw_data,
                selection=NO_SELECTION,
            )
            source_results = summarize(
                host_sections,
                config_cache.summary_config(hostname, source_info.ident),
                fetcher_type=source_info.fetcher_type,
            )
            output = b""
            if raw_data.is_ok():
                assert raw_data.ok is not None
                output = raw_data.ok
            dumps.append(_source_dump(source_info.ident, output, source_results))

        return _AgentDump(
            b"".join(dump.output for dump in dumps),
            [warning for dump in dumps for warning in dump.warnings],
            [error for dump in dumps for error in dump.errors],
        )


@dataclass(frozen=True, kw_only=True)
class _DumpAgentCommand:
    dump_agent: _DumpAgent

    def run(self, context: CLIContext, request: DumpAgentRequest) -> CLIExitCode:
        assert request.host is not None
        try:
            dump = self.dump_agent(
                request.host, request, omd_root=context.omd_root, debug=context.global_options.debug
            )
        except (MKBailOut, MKGeneralException) as e:
            context.logger.error("%(error)s", {"error": e})  # noqa: TRY400
            if context.global_options.debug:
                raise
            return CLIExitCode.UNKNOWN

        write_stdout(dump.output.decode(errors="surrogateescape"))
        for warn in dump.warnings:
            console.warning(warn, file=sys.stderr)
        for err in dump.errors:
            console.error(err, file=sys.stderr)
        return CLIExitCode.FAILURE if dump.errors else CLIExitCode.SUCCESS


class _DumpHosts(Protocol):
    def __call__(self, request: DumpHostsRequest, *, debug: bool) -> None: ...


def _dump_hosts(request: DumpHostsRequest, *, debug: bool) -> None:
    logger = logging.getLogger("cmk.base.modes")  # this might go nowhere.
    plugins = load_checks(debug=debug)
    loading_result = config.load(validate_hosts=True, debug=debug)
    loaded_config = loading_result.loaded_config
    ruleset_matcher = loading_result.config_cache.ruleset_matcher
    label_manager = loading_result.config_cache.label_manager
    config_cache = loading_result.config_cache
    core_objects_config = config.CoreObjectsConfig(loaded_config, ruleset_matcher, label_manager)
    hosts_config = loading_result.hosts_config
    ip_lookup_config = config_cache.ip_lookup_config(fake_dns=request.fake_dns)

    ip_address_of = ip_lookup.ConfiguredIPLookup(
        ip_lookup.make_lookup_ip_address(ip_lookup_config),
        allow_empty=hosts_config.clusters,
        error_handler=config.handle_ip_lookup_failure,
    )
    ip_address_of_mgmt = ip_lookup.make_lookup_mgmt_board_ip_address(ip_lookup_config)

    all_hosts = {
        hn
        for hn in itertools.chain(hosts_config.hosts, hosts_config.clusters)
        if config_cache.is_active(hn) and config_cache.is_online(hn)
    }
    hosts = set(request.hosts) or all_hosts

    with ruleset_matcher.ruleset_optimizer.processed_hosts(hosts):
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
                debug=debug,
            )


@dataclass(frozen=True, kw_only=True)
class _DumpHostsCommand:
    dump_hosts: _DumpHosts

    def run(self, context: CLIContext, request: DumpHostsRequest) -> CLIExitCode:
        try:
            self.dump_hosts(request, debug=context.global_options.debug)
        except MKGeneralException as e:
            context.logger.error("%(error)s", {"error": e})  # noqa: TRY400
            if context.global_options.debug:
                raise
            return CLIExitCode.UNKNOWN
        return CLIExitCode.SUCCESS


cli_handler_dump_agent = CLIHandler(
    command=cli_command_dump_agent, run=_DumpAgentCommand(dump_agent=_dump_agent).run
)

cli_handler_dump = CLIHandler(
    command=cli_command_dump, run=_DumpHostsCommand(dump_hosts=_dump_hosts).run
)
