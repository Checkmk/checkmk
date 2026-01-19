#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="misc"
# mypy: disable-error-code="type-arg"

"""Concrete implementation of checkers functionality."""

from __future__ import annotations

import functools
import logging
import socket
import time
from collections.abc import Callable, Container, Iterable, Iterator, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Final, Literal

import livestatus

import cmk.ccc.debug
import cmk.ccc.resulttype as result
import cmk.checkengine.plugin_backend as agent_based_register
import cmk.utils.paths
from cmk.agent_based.prediction_backend import (
    InjectedParameters,
    lookup_predictive_levels,
    PredictionParameters,
)
from cmk.agent_based.v1 import IgnoreResults, IgnoreResultsError, Metric, State
from cmk.agent_based.v1 import Result as CheckFunctionResult
from cmk.base.config import ConfigCache
from cmk.base.errorhandling import create_check_crash_dump
from cmk.base.sources import (
    FetcherFactory,
    make_parser,
    make_sources,
    ParserConfig,
    Source,
)
from cmk.ccc import tty
from cmk.ccc.cpu_tracking import CPUTracker, Snapshot
from cmk.ccc.exceptions import MKTimeout
from cmk.ccc.hostaddress import HostAddress, HostName
from cmk.checkengine.checkerplugin import AggregatedResult, CheckerPlugin, ConfiguredService
from cmk.checkengine.checking import cluster_mode
from cmk.checkengine.checkresults import (
    ActiveCheckResult,
    MetricTuple,
    ServiceCheckResult,
    state_markers,
    SubmittableServiceCheckResult,
    UnsubmittableServiceCheckResult,
)
from cmk.checkengine.discovery import (
    ABCDiscoveryConfig,
    get_plugin_parameters,
    HostLabelPlugin,
)
from cmk.checkengine.fetcher import HostKey
from cmk.checkengine.parameters import Parameters
from cmk.checkengine.parser import HostSections, parse_raw_data, SectionNameCollection
from cmk.checkengine.plugins import (
    AgentBasedPlugins,
    AutocheckEntry,
    CheckPluginName,
    DiscoveryPlugin,
    ParsedSectionName,
    SectionName,
)
from cmk.checkengine.plugins import AgentSectionPlugin as AgentSectionPluginAPI
from cmk.checkengine.plugins import CheckPlugin as CheckPluginAPI
from cmk.checkengine.plugins import SNMPSectionPlugin as SNMPSectionPluginAPI
from cmk.checkengine.sectionparser import (
    Provider,
    ResolvedResult,
    SectionPlugin,
)
from cmk.checkengine.sectionparserutils import (
    get_cache_info,
    get_section_cluster_kwargs,
    get_section_kwargs,
)
from cmk.checkengine.submitters import ServiceState
from cmk.checkengine.summarize import summarize, SummaryConfig
from cmk.checkengine.value_store import ValueStoreManager
from cmk.fetchers import (
    AdHocSecrets,
    Fetcher,
    FetcherSecrets,
    FetcherTrigger,
    FetcherTriggerFactory,
    Mode,
    ProgramFetcher,
    StoredSecrets,
    TLSConfig,
)
from cmk.fetchers.config import make_persisted_section_dir
from cmk.fetchers.filecache import FileCache, FileCacheOptions, MaxAge, NoCache
from cmk.helper_interface import AgentRawData, FetcherType, SourceInfo, SourceType
from cmk.server_side_calls_backend import ExecutableFinder, SpecialAgentCommandLine
from cmk.snmplib import SNMPBackendEnum, SNMPRawData
from cmk.utils.check_utils import ParametersTypeAlias
from cmk.utils.ip_lookup import (
    IPLookup,
    IPLookupOptional,
    IPStackConfig,
)
from cmk.utils.log import console
from cmk.utils.prediction import make_updated_predictions, MetricRecord, PredictionStore
from cmk.utils.rulesets import RuleSetName
from cmk.utils.servicename import ServiceName

__all__ = [
    "CheckerPluginMapper",
    "CMKFetcher",
    "CMKParser",
    "CMKSummarizer",
    "DiscoveryPluginMapper",
    "get_aggregated_result",
    "HostLabelPluginMapper",
    "SectionPluginMapper",
    "SpecialAgentFetcher",
]

type _Labels = Mapping[str, str]


@dataclass(frozen=True)
class CheckerConfig:
    only_from: Callable[[HostName], None | str | list[str]]
    effective_service_level: Callable[[HostName, ServiceName, _Labels], int]
    get_clustered_service_configuration: Callable[
        [HostName, ServiceName, _Labels],
        tuple[cluster_mode.ClusterMode, Mapping[str, object]],
    ]
    nodes: Callable[[HostName], Sequence[HostName]]
    effective_host: Callable[[HostName, ServiceName, _Labels], HostName]
    get_snmp_backend: Callable[[HostName], SNMPBackendEnum]
    timeperiods_active: Mapping[str, bool]


def _fetch_all(
    trigger: FetcherTrigger,
    sources: Iterable[Source],
    file_cache_options: FileCacheOptions,
    mode: Mode,
    secrets: FetcherSecrets,
    *,
    simulation: bool,
) -> Sequence[
    tuple[
        SourceInfo,
        result.Result[AgentRawData | SNMPRawData, Exception],
        Snapshot,
    ]
]:
    return [
        _do_fetch(
            trigger,
            source.source_info(),
            source.file_cache(simulation=simulation, file_cache_options=file_cache_options),
            source.fetcher(),
            mode,
            secrets,
        )
        for source in sources
    ]


def _do_fetch(
    trigger: FetcherTrigger,
    source_info: SourceInfo,
    file_cache: FileCache,
    fetcher: Fetcher,
    mode: Mode,
    secrets: FetcherSecrets,
) -> tuple[
    SourceInfo,
    result.Result[AgentRawData | SNMPRawData, Exception],
    Snapshot,
]:
    console.debug(f"  Source: {source_info}")
    with CPUTracker(console.debug) as tracker:
        raw_data = trigger.get_raw_data(file_cache, fetcher, mode, secrets)
    return source_info, raw_data, tracker.duration


class CMKParser:
    def __init__(
        self,
        config: ParserConfig,
        *,
        selected_sections: SectionNameCollection,
        keep_outdated: bool,
        logger: logging.Logger,
    ) -> None:
        self.config: Final = config
        self.selected_sections: Final = selected_sections
        self.keep_outdated: Final = keep_outdated
        self.logger: Final = logger

    def __call__(
        self,
        fetched: Iterable[
            tuple[
                SourceInfo,
                result.Result[AgentRawData | SNMPRawData, Exception],
            ]
        ],
    ) -> Sequence[tuple[SourceInfo, result.Result[HostSections, Exception]]]:
        """Parse fetched data."""
        console.debug(f"{tty.yellow}+{tty.normal} PARSE FETCHER RESULTS")
        output: list[tuple[SourceInfo, result.Result[HostSections, Exception]]] = []
        section_cache_path = cmk.utils.paths.var_dir
        # Special agents can produce data for the same check_plugin_name on the same host, in this case
        # the section lines need to be extended
        for source, raw_data in fetched:
            source_result = parse_raw_data(
                make_parser(
                    self.config,
                    source.hostname,
                    source.ipaddress,
                    source.fetcher_type,
                    omd_root=cmk.utils.paths.omd_root,
                    persisted_section_dir=make_persisted_section_dir(
                        source.hostname,
                        ident=source.ident,
                        section_cache_path=section_cache_path,
                    ),
                    keep_outdated=self.keep_outdated,
                    logger=self.logger,
                ),
                raw_data,
                selection=self.selected_sections,
            )
            output.append((source, source_result))
        return output


class CMKSummarizer:
    def __init__(
        self,
        host_name: HostName,
        summary_config: Callable[[HostName, str], SummaryConfig],
        *,
        override_non_ok_state: ServiceState | None = None,
    ) -> None:
        self.host_name: Final = host_name
        self.summary_config: Final = summary_config
        self.override_non_ok_state: Final = override_non_ok_state

    def __call__(
        self,
        host_sections: Iterable[tuple[SourceInfo, result.Result[HostSections, Exception]]],
    ) -> Iterable[ActiveCheckResult]:
        return [
            _summarize_host_sections(
                host_sections,
                source,
                self.summary_config(source.hostname, source.ident),
                override_non_ok_state=self.override_non_ok_state,
            )
            for source, host_sections in host_sections
        ]


def _summarize_host_sections(
    host_sections: result.Result[HostSections, Exception],
    source: SourceInfo,
    config: SummaryConfig,
    *,
    override_non_ok_state: ServiceState | None = None,
) -> ActiveCheckResult:
    return ActiveCheckResult.from_subresults(
        *(
            ActiveCheckResult(
                state=(
                    s.state
                    if (s.state == 0 or override_non_ok_state is None)
                    else override_non_ok_state
                ),
                summary=f"[{source.ident}] {s.summary}" if idx == 0 else s.summary,
                details=s.details,
                metrics=s.metrics,
            )
            for idx, s in enumerate(
                summarize(
                    host_sections,
                    config,
                    fetcher_type=source.fetcher_type,
                )
            )
        )
    )


class SpecialAgentFetcher:
    def __init__(
        self,
        trigger: FetcherTrigger,
        secrets: FetcherSecrets,
        *,
        agent_name: str,
        cmds: Iterator[SpecialAgentCommandLine],
        is_cmc: bool,
    ) -> None:
        self.trigger: Final = trigger
        self.agent_name: Final = agent_name
        self.cmds: Final = cmds
        self.secrets: Final = secrets
        self.is_cmc: Final = is_cmc

    def __call__(
        self, host_name: HostName, *, ip_address: HostAddress | None
    ) -> Sequence[
        tuple[
            SourceInfo,
            result.Result[AgentRawData | SNMPRawData, Exception],
            Snapshot,
        ]
    ]:
        source_info = SourceInfo(
            hostname=host_name,
            ipaddress=ip_address,
            ident=f"special_{self.agent_name}",
            fetcher_type=FetcherType.SPECIAL_AGENT,
            source_type=SourceType.HOST,
        )
        return [
            _do_fetch(
                self.trigger,
                source_info,
                NoCache(),
                ProgramFetcher(cmdline=cmd.cmdline, stdin=cmd.stdin, is_cmc=self.is_cmc),
                Mode.DISCOVERY,
                self.secrets,
            )
            for cmd in self.cmds
        ]


class CMKFetcher:
    def __init__(
        self,
        config_cache: ConfigCache,
        get_relay_id: Callable[[HostName], str | None],
        make_trigger: FetcherTriggerFactory,
        factory: FetcherFactory,
        plugins: AgentBasedPlugins,
        *,
        # alphabetically sorted
        default_address_family: Callable[
            [HostName], Literal[socket.AddressFamily.AF_INET, socket.AddressFamily.AF_INET6]
        ],
        file_cache_options: FileCacheOptions,
        force_snmp_cache_refresh: bool,
        get_ip_stack_config: Callable[[HostName], IPStackConfig],
        ip_address_of: IPLookup,
        ip_address_of_mandatory: IPLookup,  # slightly different :-| TODO: clean up!!
        ip_address_of_mgmt: IPLookupOptional,
        mode: Mode,
        secrets_config_relay: AdHocSecrets | StoredSecrets,
        secrets_config_site: StoredSecrets,
        simulation_mode: bool,
        metric_backend_fetcher_factory: Callable[[HostAddress], ProgramFetcher | None],
        max_cachefile_age: MaxAge | None = None,
    ) -> None:
        self.config_cache: Final = config_cache
        self.get_relay_id: Final = get_relay_id
        self.make_trigger: Final = make_trigger
        self.default_address_family: Final = default_address_family
        self.factory: Final = factory
        self.plugins: Final = plugins
        self.file_cache_options: Final = file_cache_options
        self.force_snmp_cache_refresh: Final = force_snmp_cache_refresh
        self.get_ip_stack_config: Final = get_ip_stack_config
        self.ip_address_of: Final = ip_address_of
        self.ip_address_of_mandatory: Final = ip_address_of_mandatory
        self.ip_address_of_mgmt: Final = ip_address_of_mgmt
        self.mode: Final = mode
        self.secrets_config_relay: Final = secrets_config_relay
        self.secrets_config_site: Final = secrets_config_site
        self.simulation_mode: Final = simulation_mode
        self.max_cachefile_age: Final = max_cachefile_age
        self.metric_backend_fetcher_factory: Final = metric_backend_fetcher_factory

    def __call__(
        self, host_name: HostName, *, ip_address: HostAddress | None
    ) -> Sequence[
        tuple[
            SourceInfo,
            result.Result[AgentRawData | SNMPRawData, Exception],
            Snapshot,
        ]
    ]:
        hosts_config = self.config_cache.hosts_config

        # we might be checking a cluster, but the relay id is always the same.
        relay_id = self.get_relay_id(host_name)

        is_cluster = host_name in hosts_config.clusters
        if not is_cluster:
            # In case of keepalive we always have an ipaddress (can be 0.0.0.0 or :: when
            # address is unknown). When called as non keepalive ipaddress may be None or
            # is already an address (2nd argument)
            hosts = [
                (
                    host_name,
                    self.default_address_family(host_name),
                    (ip_stack_config := self.config_cache.ip_stack_config(host_name)),
                    ip_address
                    or (
                        None
                        if ip_stack_config is IPStackConfig.NO_IP
                        else self.ip_address_of_mandatory(
                            host_name, self.default_address_family(host_name)
                        )
                    ),
                )
            ]
        else:
            hosts = [
                (
                    node,
                    self.default_address_family(node),
                    (ip_stack_config := self.get_ip_stack_config(node)),
                    (
                        None
                        if ip_stack_config is IPStackConfig.NO_IP
                        else self.ip_address_of_mandatory(node, self.default_address_family(node))
                    ),
                )
                for node in self.config_cache.nodes(host_name)
            ]

        tls_config = TLSConfig(
            cas_dir=Path(cmk.utils.paths.agent_cas_dir),
            ca_store=Path(cmk.utils.paths.agent_cert_store),
            site_crt=Path(cmk.utils.paths.site_cert_file),
        )
        secrets_config = self.secrets_config_relay if relay_id else self.secrets_config_site
        console.verbose(f"{tty.yellow}+{tty.normal} FETCHING DATA")
        return [
            fetched
            for current_host_name, current_ip_family, current_ip_stack_config, current_ip_address in hosts
            for fetched in _fetch_all(
                self.make_trigger(relay_id),
                make_sources(
                    self.plugins,
                    current_host_name,
                    current_ip_family,
                    current_ip_address,
                    current_ip_stack_config,
                    fetcher_factory=self.factory,
                    force_snmp_cache_refresh=(
                        self.force_snmp_cache_refresh if not is_cluster else False
                    ),
                    simulation_mode=self.simulation_mode,
                    file_cache_options=self.file_cache_options,
                    file_cache_max_age=(
                        self.max_cachefile_age or self.config_cache.max_cachefile_age(host_name)
                    ),
                    snmp_backend=self.config_cache.get_snmp_backend(current_host_name),
                    file_cache_path_base=cmk.utils.paths.omd_root,
                    file_cache_path_relative=cmk.utils.paths.relative_data_source_cache_dir,
                    tcp_cache_path_relative=cmk.utils.paths.relative_tcp_cache_dir,
                    tls_config=tls_config,
                    computed_datasources=self.config_cache.computed_datasources(current_host_name),
                    datasource_programs=self.config_cache.datasource_programs(current_host_name),
                    tag_list=self.config_cache.host_tags.tag_list(current_host_name),
                    management_ip=self.ip_address_of_mgmt(
                        current_host_name, self.default_address_family(current_host_name)
                    ),
                    management_protocol=self.config_cache.management_protocol(current_host_name),
                    special_agent_command_lines=self.config_cache.special_agent_command_lines(
                        current_host_name,
                        current_ip_family,
                        current_ip_address,
                        secrets_config=secrets_config,
                        ip_address_of=self.ip_address_of,
                        executable_finder=ExecutableFinder(
                            # NOTE: we can't ignore these, they're an API promise.
                            cmk.utils.paths.local_special_agents_dir,
                            cmk.utils.paths.special_agents_dir,
                            prefix_map=(
                                () if relay_id is None else ((cmk.utils.paths.omd_root, Path()),)
                            ),
                        ),
                        for_relay=relay_id is not None,
                    ),
                    agent_connection_mode=self.config_cache.agent_connection_mode(
                        current_host_name
                    ),
                    check_mk_check_interval=self.config_cache.check_mk_check_interval(
                        current_host_name
                    ),
                    metric_backend_fetcher=self.metric_backend_fetcher_factory(current_host_name),
                ),
                file_cache_options=self.file_cache_options,
                mode=self.mode,
                secrets=secrets_config,
                simulation=self.simulation_mode,
            )
        ]


class SectionPluginMapper(Mapping[SectionName, SectionPlugin]):
    def __init__(
        self,
        sections: Mapping[SectionName, AgentSectionPluginAPI | SNMPSectionPluginAPI],
    ) -> None:
        self._sections = sections

    def __getitem__(self, __key: SectionName) -> SectionPlugin:
        plugin = self._sections.get(__key)
        return (
            SectionPlugin.trivial(__key)
            if plugin is None
            else SectionPlugin(
                supersedes=plugin.supersedes,
                parse_function=plugin.parse_function,
                parsed_section_name=plugin.parsed_section_name,
            )
        )

    def __iter__(self) -> Iterator[SectionName]:
        return iter(self._sections)

    def __len__(self) -> int:
        return len(self._sections)


def _make_parameters_getter(
    discovery_config: ABCDiscoveryConfig,
    plugin: AgentSectionPluginAPI | SNMPSectionPluginAPI,
) -> Callable[[HostName], Sequence[Parameters] | Parameters | None]:
    """wrapper for partial, which is not supported by mypy"""

    def get_parameters(host_name: HostName) -> Sequence[Parameters] | Parameters | None:
        return get_plugin_parameters(
            host_name,
            discovery_config,
            default_parameters=plugin.host_label_default_parameters,
            ruleset_name=plugin.host_label_ruleset_name,
            ruleset_type=plugin.host_label_ruleset_type,
        )

    return get_parameters


class HostLabelPluginMapper(Mapping[SectionName, HostLabelPlugin]):
    def __init__(
        self,
        *,
        discovery_config: ABCDiscoveryConfig,
        sections: Mapping[SectionName, AgentSectionPluginAPI | SNMPSectionPluginAPI],
    ) -> None:
        super().__init__()
        self._discovery_config: Final = discovery_config
        self._sections = sections

    def __getitem__(self, __key: SectionName) -> HostLabelPlugin:
        plugin = self._sections.get(__key)
        return (
            HostLabelPlugin(
                function=plugin.host_label_function,
                parameters=_make_parameters_getter(self._discovery_config, plugin),
            )
            if plugin is not None
            else HostLabelPlugin.trivial()
        )

    def __iter__(self) -> Iterator[SectionName]:
        return iter(self._sections)

    def __len__(self) -> int:
        return len(self._sections)


class CheckerPluginMapper(Mapping[CheckPluginName, CheckerPlugin]):
    # See comment to SectionPluginMapper.
    def __init__(
        self,
        config: CheckerConfig,
        check_plugins: Mapping[CheckPluginName, CheckPluginAPI],
        value_store_manager: ValueStoreManager,
        logger: logging.Logger,
        *,
        clusters: Container[HostName],
        rtc_package: AgentRawData | None,
    ):
        self.config: Final = config
        self.value_store_manager: Final = value_store_manager
        self._logger: Final = logger
        self.clusters: Final = clusters
        self.rtc_package: Final = rtc_package
        self.check_plugins: Final = check_plugins

    def __getitem__(self, __key: CheckPluginName) -> CheckerPlugin:
        plugin = agent_based_register.get_check_plugin(__key, self.check_plugins)
        if plugin is None:
            raise KeyError(__key)

        def check_function(
            host_name: HostName,
            service: ConfiguredService,
            *,
            providers: Mapping[HostKey, Provider],
        ) -> AggregatedResult:
            check_function = _get_check_function(
                plugin,
                lambda: self.config.get_clustered_service_configuration(
                    host_name, service.description, service.labels
                ),
                host_name,
                service,
                self.value_store_manager,
                clusters=self.clusters,
            )
            return get_aggregated_result(
                host_name,
                host_name in self.clusters,
                cluster_nodes=self.config.nodes(host_name),
                providers=providers,
                service=service,
                plugin=plugin,
                check_function=check_function,
                rtc_package=self.rtc_package,
                get_effective_host=self.config.effective_host,
                snmp_backend=self.config.get_snmp_backend(host_name),
                parameters=_compute_final_check_parameters(
                    host_name, service, self.config, self._logger
                ),
            )

        return CheckerPlugin(
            sections=plugin.sections,
            function=check_function,
            default_parameters=plugin.check_default_parameters,
            ruleset_name=plugin.check_ruleset_name,
            discovery_ruleset_name=plugin.discovery_ruleset_name,
        )

    def __iter__(self) -> Iterator[CheckPluginName]:
        return iter(self.check_plugins)

    def __len__(self) -> int:
        return len(self.check_plugins)


def _make_rrd_data_getter(
    host_name: HostAddress, service_name: ServiceName, logger: logging.Logger
) -> Callable[[str, int, int], MetricRecord | None]:
    """Replacement for `partial` which is not supported by mypy"""

    def get_rrd_data(rpn: str, fromtime: int, untiltime: int) -> MetricRecord | None:
        try:
            return livestatus.get_rrd_data(
                livestatus.LocalConnection(), host_name, service_name, rpn, fromtime, untiltime
            )
        except (
            ()
            if cmk.ccc.debug.enabled()
            else (
                livestatus.MKLivestatusSocketError,
                livestatus.MKLivestatusNotFoundError,
            )
        ) as e:
            logger.warning(f"Cannot get historic metrics via Livestatus: {e}")
        return None

    return get_rrd_data


def update_predictive_levels(
    metric_name: str, levels: tuple, direction: Literal["upper", "lower"]
) -> tuple:
    match levels:
        case ("cmk_postprocessed", "predictive_levels", dict() as lvl):
            return (
                "cmk_postprocessed",
                "predictive_levels",
                {
                    **lvl,
                    "__reference_metric__": metric_name,
                    "__direction__": direction,
                },
            )
        case _:
            return levels


def _special_processing_hack_for_predictive_otel_metrics(
    params: Mapping[str, object],
) -> Mapping[str, object]:
    match params:
        case {"metrics": ("multi_metrics", list() as metrics)}:
            for metric in metrics:
                metric["levels_lower"] = update_predictive_levels(
                    metric["metric_name"], metric["levels_lower"], "lower"
                )
                metric["levels_upper"] = update_predictive_levels(
                    metric["metric_name"], metric["levels_upper"], "upper"
                )
            return {"metrics": ("multi_metrics", metrics)}
        case _:
            return params


def _compute_final_check_parameters(
    host_name: HostName,
    service: ConfiguredService,
    checker_config: CheckerConfig,
    logger: logging.Logger,
) -> Parameters:
    params = service.parameters.evaluate(checker_config.timeperiods_active.get)

    if not _needs_postprocessing(params):
        return Parameters(params)

    # We have this special case for the otel plugin, where we want to have predictive levels,
    # but don't know the metric names ahead of time.
    if service.check_plugin_name == CheckPluginName("otel_metrics"):
        params = _special_processing_hack_for_predictive_otel_metrics(params)

    # Most of the following are only needed for individual plugins, actually.
    # We delay every computation until needed.

    def make_prediction() -> InjectedParameters:
        prediction_store = PredictionStore(host_name=host_name, service_name=service.description)
        # In the past the creation of predictions (and the livestatus query needed)
        # was performed inside the check plug-ins context.
        # We should consider moving this side effect even further up the stack
        return InjectedParameters(
            meta_file_path_template=prediction_store.meta_file_path_template,
            predictions=make_updated_predictions(
                prediction_store,
                _make_rrd_data_getter(host_name, service.description, logger),
                time.time(),
            ),
        )

    config = PostprocessingServiceConfig(
        only_from=lambda: checker_config.only_from(host_name),
        prediction=make_prediction,
        service_level=lambda: checker_config.effective_service_level(
            host_name, service.description, service.labels
        ),
        host_name=str(host_name),
        service_name=str(service.description),
    )
    return Parameters({k: postprocess_configuration(v, config) for k, v in params.items()})


def _get_check_function(
    plugin: CheckPluginAPI,
    get_clustered_service_configuration: Callable[
        [], tuple[cluster_mode.ClusterMode, Mapping[str, object]]
    ],
    host_name: HostName,
    service: ConfiguredService,
    value_store_manager: ValueStoreManager,
    *,
    clusters: Container[HostName],
) -> Callable[..., ServiceCheckResult]:
    assert plugin.name == service.check_plugin_name
    check_function = (
        cluster_mode.get_cluster_check_function(
            *get_clustered_service_configuration(),
            plugin=plugin,
            service_id=service.id(),
            value_store_manager=value_store_manager,
        )
        if host_name in clusters
        else plugin.check_function
    )

    @functools.wraps(check_function)
    def __check_function(*args: object, **kw: object) -> ServiceCheckResult:
        with value_store_manager.namespace(service.id()):
            return _aggregate_results(consume_check_results(check_function(*args, **kw)))

    return __check_function


def _aggregate_results(
    subresults: tuple[
        Sequence[IgnoreResults], Sequence[MetricTuple], Sequence[CheckFunctionResult]
    ],
) -> ServiceCheckResult:
    # Impedance matching part of `get_check_function()`.
    ignore_results, metrics, results = subresults

    if not ignore_results and not results:  # Check returned nothing
        return SubmittableServiceCheckResult.item_not_found()

    state = int(State.worst(*(r.state for r in results))) if results else 0
    output = _aggregate_texts(ignore_results, results)

    return (
        UnsubmittableServiceCheckResult(state, output, metrics)
        if ignore_results
        else SubmittableServiceCheckResult(state, output, metrics)
    )


def _aggregate_texts(
    ignore_results: Sequence[IgnoreResults],
    results: Sequence[CheckFunctionResult],
) -> str:
    summaries = [t for e in ignore_results if (t := str(e))]
    details: list[str] = []
    needs_marker = len(results) > 1

    def _add_state_marker(result_str: str, state_marker: str) -> str:
        return result_str if state_marker in result_str else result_str + state_marker

    for result_ in results:
        state_marker = state_markers[int(result_.state)] if needs_marker else ""
        if result_.summary:
            summaries.append(
                _add_state_marker(
                    result_.summary,
                    state_marker,
                )
            )
        details.append(
            _add_state_marker(
                result_.details,
                state_marker,
            )
        )

    if not summaries:
        count = len(details)
        summaries.append(
            "Everything looks OK - %d detail%s available" % (count, "" if count == 1 else "s")
        )
    return "\n".join([", ".join(summaries)] + details)


def consume_check_results(
    # we need to accept `object`, in order to explicitly protect against plugins
    # creating invalid output.
    # Typing this as `CheckResult` will make linters complain about unreachable code.
    subresults: Iterable[object],
) -> tuple[Sequence[IgnoreResults], Sequence[MetricTuple], Sequence[CheckFunctionResult]]:
    """Impedance matching between the Check API and the Check Engine."""
    ignore_results: list[IgnoreResults] = []
    results: list[CheckFunctionResult] = []
    perfdata: list[MetricTuple] = []
    try:
        for subr in subresults:
            match subr:
                case IgnoreResults():
                    ignore_results.append(subr)
                case Metric():
                    perfdata.append((subr.name, subr.value) + subr.levels + subr.boundaries)
                case CheckFunctionResult():
                    results.append(subr)
                case _:
                    raise TypeError(subr)
    except IgnoreResultsError as exc:
        return [IgnoreResults(str(exc))], perfdata, results

    return ignore_results, perfdata, results


def _get_monitoring_data_kwargs(
    host_name: HostName,
    is_cluster: bool,
    providers: Mapping[HostKey, Provider],
    service: ConfiguredService,
    sections: Sequence[ParsedSectionName],
    source_type: SourceType | None = None,
    *,
    cluster_nodes: Sequence[HostName],
    get_effective_host: Callable[[HostName, ServiceName, _Labels], HostName],
) -> tuple[Mapping[str, object], UnsubmittableServiceCheckResult]:
    # Mapping[str, object] stands for either
    #  * Mapping[HostName, Mapping[str, ParsedSectionContent | None]] for clusters, or
    #  * Mapping[str, ParsedSectionContent | None] otherwise.
    if source_type is None:
        source_type = (
            SourceType.MANAGEMENT
            if service.check_plugin_name.is_management_name()
            else SourceType.HOST
        )

    if is_cluster:
        nodes = _get_clustered_service_node_keys(
            host_name,
            source_type,
            service,
            cluster_nodes=cluster_nodes,
            get_effective_host=get_effective_host,
        )
        return (
            get_section_cluster_kwargs(
                providers,
                nodes,
                sections,
            ),
            UnsubmittableServiceCheckResult.cluster_received_no_data([nk.hostname for nk in nodes]),
        )

    return (
        get_section_kwargs(
            providers,
            HostKey(host_name, source_type),
            sections,
        ),
        UnsubmittableServiceCheckResult.received_no_data(),
    )


def _get_clustered_service_node_keys(
    cluster_name: HostName,
    source_type: SourceType,
    service: ConfiguredService,
    *,
    cluster_nodes: Sequence[HostName],
    get_effective_host: Callable[[HostName, ServiceName, _Labels], HostName],
) -> Sequence[HostKey]:
    """Returns the node keys if a service is clustered, otherwise an empty sequence"""
    used_nodes = (
        [
            nn
            for nn in cluster_nodes
            if cluster_name == get_effective_host(nn, service.description, service.labels)
        ]
        or cluster_nodes  # IMHO: this can never happen, but if it does, using nodes is wrong.
        or ()
    )

    return [HostKey(nodename, source_type) for nodename in used_nodes]


def get_aggregated_result(
    host_name: HostName,
    is_cluster: bool,
    cluster_nodes: Sequence[HostName],
    providers: Mapping[HostKey, Provider],
    service: ConfiguredService,
    plugin: CheckPluginAPI,
    check_function: Callable[..., ServiceCheckResult],
    *,
    parameters: Mapping[str, object],
    rtc_package: AgentRawData | None,
    get_effective_host: Callable[[HostName, ServiceName, _Labels], HostName],
    snmp_backend: SNMPBackendEnum,
) -> AggregatedResult:
    # Mostly API-specific error-handling around the check function.
    #
    # Note that errors are handled here and in the caller in
    # the `CheckResultErrorHandler`.  So we have nearly identical, nested
    # error handling in both places.  Here the slightly simplified structure:
    #
    # ```
    # try:
    #    try:
    #        return check_function(*args, **kwargs)
    #    except Timeout:
    #        raise
    #    except Exception:
    #        create_check_crash_dump(...)
    # except Timeout:
    #        ...  # handle timeout
    # except Exception:
    #    create_check_crash_dump(...)
    #
    # ```
    #
    # Now, that is not only a terrible code structure, that's also buggy.
    #
    # Indeed, whether to handle errors and how to handle them is only
    # the callers' business.  For example, crash reports should only be
    # created on errors when the caller is a core (CMC or Nagios) but *not*
    # on the command line.  Another example: `IgnoreResultsError` is a
    # Check API feature and of no concern for the check engine.
    #
    # Because it is the callers business, this *here* is the wrong place.
    # In principle, all the error handling should occur in the caller in
    # `CheckResultErrorHandler`.
    #
    # Because this function is written so creatively (early returns,
    # reraising some exceptions for to the caller, seemingly random
    # arguments passed to the crash report ...) and `CheckResultErrorHandler`
    # isn't much better, I couldn't find an easy solution on my own.
    #
    section_kws, error_result = _get_monitoring_data_kwargs(
        host_name,
        is_cluster,
        providers,
        service,
        plugin.sections,
        cluster_nodes=cluster_nodes,
        get_effective_host=get_effective_host,
    )
    if not section_kws:  # no data found
        return AggregatedResult(
            service=service,
            data_received=False,
            result=error_result,
            cache_info=None,
        )

    item_kw = {} if service.item is None else {"item": service.item}
    params_kw = {} if plugin.check_default_parameters is None else {"params": parameters}

    try:
        check_result = check_function(**item_kw, **params_kw, **section_kws)
    except MKTimeout:
        raise
    except Exception:
        if cmk.ccc.debug.enabled():
            raise
        check_result = SubmittableServiceCheckResult(
            3,
            create_check_crash_dump(
                host_name,
                service.description,
                plugin_name=service.check_plugin_name,
                plugin_kwargs={**item_kw, **params_kw, **section_kws},
                is_cluster=is_cluster,
                is_enforced=service.is_enforced,
                snmp_backend=snmp_backend,
                rtc_package=rtc_package,
            ),
        )

    def __iter(
        section_names: Iterable[ParsedSectionName], providers: Iterable[Provider]
    ) -> Iterable[ResolvedResult]:
        for provider in providers:
            yield from (
                resolved
                for section_name in section_names
                if (resolved := provider.resolve(section_name)) is not None
            )

    return AggregatedResult(
        service=service,
        data_received=True,
        result=check_result,
        cache_info=get_cache_info(
            tuple(
                cache_info
                for resolved in __iter(plugin.sections, providers.values())
                if (cache_info := resolved.cache_info) is not None
            )
        ),
    )


def _needs_postprocessing(params: object) -> bool:
    match params:
        case tuple(("cmk_postprocessed", str(), _)):
            return True
        case tuple() | list():
            return any(_needs_postprocessing(p) for p in params)
        case {"__injected__": _}:  # legacy "valuespec" case.
            return True
        case {**mapping}:
            return any(_needs_postprocessing(p) for p in mapping.values())
        case _:
            return False


@dataclass
class PostprocessingServiceConfig:
    only_from: Callable[[], None | str | list[str]]
    prediction: Callable[[], InjectedParameters]
    service_level: Callable[[], int]
    host_name: str
    service_name: str


def postprocess_configuration(
    params: object,
    config: PostprocessingServiceConfig,
) -> object:
    """Postprocess configuration parameters.

    Parameters consisting of a 3-tuple with the first element being
    "cmk_postprocessed" and the second one one of several known string constants
    are postprocessed.

    This currently supports two ways to handle predictive levels.

    The "__injected__" case is legacy, the other case is the new one.
    Once the legacy case is removed, this can be simplified.

    Hopefully we can move this out of this scope entirely someday (and get
    rid of the recursion).
    """
    match params:
        case tuple(("cmk_postprocessed", "host_name", _)):
            return config.host_name
        case tuple(("cmk_postprocessed", "only_from", _)):
            return config.only_from()
        case tuple(("cmk_postprocessed", "predictive_levels", value)):
            return _postprocess_predictive_levels(value, config.prediction())
        case tuple(("cmk_postprocessed", "service_level", _)):
            return config.service_level()
        case tuple(("cmk_postprocessed", "service_name", _)):
            return config.service_name
        case tuple():
            return tuple(postprocess_configuration(v, config) for v in params)
        case list():
            return list(postprocess_configuration(v, config) for v in params)
        case dict():  # check for legacy predictive levels :-(
            return {
                k: (
                    config.prediction().model_dump()
                    if k == "__injected__"
                    else postprocess_configuration(v, config)
                )
                for k, v in params.items()
            }
        case _:
            return params


def _postprocess_predictive_levels(
    params: dict, injected_p: InjectedParameters
) -> tuple[Literal["predictive"], tuple[str, float | None, tuple[float, float] | None]]:
    match params:
        case {
            "__reference_metric__": str() as metric,
            "__direction__": "upper" | "lower" as direction,
            **raw_prediction_params,
        }:
            return (
                "predictive",
                (
                    metric,
                    *lookup_predictive_levels(
                        metric,
                        direction,
                        PredictionParameters.model_validate(raw_prediction_params),
                        injected_p,
                    ),
                ),
            )
        case _:
            raise ValueError(f"Invalid predictive levels: {params!r}")


class DiscoveryPluginMapper(Mapping[CheckPluginName, DiscoveryPlugin]):
    # See comment to SectionPluginMapper.
    def __init__(
        self,
        *,
        discovery_config: ABCDiscoveryConfig,
        check_plugins: Mapping[CheckPluginName, CheckPluginAPI],
    ) -> None:
        super().__init__()
        self._discovery_config: Final = discovery_config
        self._check_plugins: Final = check_plugins

    def __getitem__(self, __key: CheckPluginName) -> DiscoveryPlugin:
        # `get_check_plugin()` is not an error.  Both check plug-ins and
        # discovery are declared together in the check API.
        plugin = agent_based_register.get_check_plugin(__key, self._check_plugins)
        if plugin is None:
            raise KeyError(__key)

        def __discovery_function(
            check_plugin_name: CheckPluginName, *args: object, **kw: object
        ) -> Iterable[AutocheckEntry]:
            # Deal with impededance mismatch between check API and check engine.
            yield from (
                AutocheckEntry(
                    check_plugin_name=check_plugin_name,
                    item=service.item,
                    parameters=service.parameters,
                    service_labels={label.name: label.value for label in service.labels},
                )
                for service in plugin.discovery_function(*args, **kw)
            )

        return DiscoveryPlugin(
            sections=plugin.sections,
            function=__discovery_function,
            parameters=_make_discovery_parameters_getter(
                discovery_config=self._discovery_config,
                check_plugin_name=plugin.name,
                default_parameters=plugin.discovery_default_parameters,
                ruleset_name=plugin.discovery_ruleset_name,
                ruleset_type=plugin.discovery_ruleset_type,
            ),
        )

    def __iter__(self) -> Iterator[CheckPluginName]:
        return iter(self._check_plugins)

    def __len__(self) -> int:
        return len(self._check_plugins)


def _make_discovery_parameters_getter(
    discovery_config: ABCDiscoveryConfig,
    check_plugin_name: CheckPluginName,
    *,
    default_parameters: ParametersTypeAlias | None,
    ruleset_name: RuleSetName | None,
    ruleset_type: Literal["all", "merged"],
) -> Callable[[HostName], None | Parameters | list[Parameters]]:
    def get_discovery_parameters(host_name: HostName) -> None | Parameters | list[Parameters]:
        params = get_plugin_parameters(
            host_name,
            discovery_config,
            default_parameters=default_parameters,
            ruleset_name=ruleset_name,
            ruleset_type=ruleset_type,
        )

        #
        # We have to add an artificial parameter, the host name.
        # We really should rewrite the logwatch plugins :-(
        #
        if str(check_plugin_name) not in {
            "logwatch_ec",
            "logwatch_ec_single",
            "logwatch",
            "logwatch_groups",
        }:
            return params

        if params is None:
            return Parameters({"host_name": host_name})
        if isinstance(params, Parameters):  # we don't need this case, but let's be consistent.
            return Parameters({**params, "host_name": host_name})
        return [Parameters({**p, "host_name": host_name}) for p in params]

    return get_discovery_parameters
