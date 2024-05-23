#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Concrete implementation of checkers functionality."""

from __future__ import annotations

import functools
import itertools
import logging
import time
from collections.abc import Callable, Container, Iterable, Iterator, Mapping, Sequence
from functools import partial
from pathlib import Path
from typing import Final, Literal

import livestatus

import cmk.utils.debug
import cmk.utils.paths
import cmk.utils.resulttype as result
import cmk.utils.tty as tty
from cmk.utils import password_store
from cmk.utils.agentdatatype import AgentRawData
from cmk.utils.check_utils import unwrap_parameters, wrap_parameters
from cmk.utils.cpu_tracking import CPUTracker, Snapshot
from cmk.utils.exceptions import MKTimeout, OnError
from cmk.utils.hostaddress import HostAddress, HostName
from cmk.utils.log import console
from cmk.utils.misc import pnp_cleanup
from cmk.utils.piggyback import PiggybackTimeSettings
from cmk.utils.prediction import make_updated_predictions, PredictionStore
from cmk.utils.rulesets.ruleset_matcher import RulesetMatcher
from cmk.utils.sectionname import SectionMap, SectionName
from cmk.utils.servicename import ServiceName
from cmk.utils.timeperiod import timeperiod_active

from cmk.snmplib import SNMPBackendEnum, SNMPRawData

from cmk.fetchers import Fetcher, get_raw_data, Mode
from cmk.fetchers.filecache import FileCache, FileCacheOptions, MaxAge

from cmk.checkengine.checking import (
    AggregatedResult,
    CheckPlugin,
    CheckPluginName,
    ConfiguredService,
)
from cmk.checkengine.checkresults import (
    ActiveCheckResult,
    MetricTuple,
    ServiceCheckResult,
    state_markers,
)
from cmk.checkengine.discovery import AutocheckEntry, DiscoveryPlugin, HostLabelPlugin
from cmk.checkengine.exitspec import ExitSpec
from cmk.checkengine.fetcher import HostKey, SourceInfo, SourceType
from cmk.checkengine.inventory import InventoryPlugin, InventoryPluginName
from cmk.checkengine.legacy import LegacyCheckParameters
from cmk.checkengine.parameters import Parameters, TimespecificParameters
from cmk.checkengine.parser import HostSections, NO_SELECTION, parse_raw_data, SectionNameCollection
from cmk.checkengine.sectionparser import ParsedSectionName, Provider, ResolvedResult, SectionPlugin
from cmk.checkengine.sectionparserutils import (
    get_cache_info,
    get_section_cluster_kwargs,
    get_section_kwargs,
)
from cmk.checkengine.submitters import ServiceState
from cmk.checkengine.summarize import summarize

import cmk.base.api.agent_based.register as agent_based_register
import cmk.base.api.agent_based.register._config as _api
import cmk.base.config as config
from cmk.base import plugin_contexts
from cmk.base.api.agent_based import cluster_mode, value_store
from cmk.base.api.agent_based.plugin_classes import CheckPlugin as CheckPluginAPI
from cmk.base.api.agent_based.value_store import ValueStoreManager
from cmk.base.config import ConfigCache
from cmk.base.errorhandling import create_check_crash_dump
from cmk.base.sources import make_parser, make_sources, Source

from cmk.agent_based.prediction_backend import (
    InjectedParameters,
    lookup_predictive_levels,
    PredictionParameters,
)
from cmk.agent_based.v1 import IgnoreResults, IgnoreResultsError, Metric
from cmk.agent_based.v1 import Result as CheckFunctionResult
from cmk.agent_based.v1 import State

__all__ = [
    "CheckPluginMapper",
    "CMKFetcher",
    "CMKParser",
    "CMKSummarizer",
    "DiscoveryPluginMapper",
    "get_aggregated_result",
    "HostLabelPluginMapper",
    "InventoryPluginMapper",
    "SectionPluginMapper",
]


def _fetch_all(
    sources: Iterable[Source], *, simulation: bool, file_cache_options: FileCacheOptions, mode: Mode
) -> Sequence[
    tuple[
        SourceInfo,
        result.Result[AgentRawData | SNMPRawData, Exception],
        Snapshot,
    ]
]:
    console.verbose("%s+%s %s\n", tty.yellow, tty.normal, "Fetching data".upper())
    return [
        _do_fetch(
            source.source_info(),
            source.file_cache(simulation=simulation, file_cache_options=file_cache_options),
            source.fetcher(),
            mode=mode,
        )
        for source in sources
    ]


def _do_fetch(
    source_info: SourceInfo,
    file_cache: FileCache,
    fetcher: Fetcher,
    *,
    mode: Mode,
) -> tuple[
    SourceInfo,
    result.Result[AgentRawData | SNMPRawData, Exception],
    Snapshot,
]:
    console.vverbose(f"  Source: {source_info}\n")
    with CPUTracker() as tracker:
        raw_data = get_raw_data(file_cache, fetcher, mode)
    return source_info, raw_data, tracker.duration


class CMKParser:
    def __init__(
        self,
        config_cache: ConfigCache,
        *,
        selected_sections: SectionNameCollection,
        keep_outdated: bool,
        logger: logging.Logger,
    ) -> None:
        self.config_cache: Final = config_cache
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
        console.vverbose("%s+%s %s\n", tty.yellow, tty.normal, "Parse fetcher results".upper())
        output: list[tuple[SourceInfo, result.Result[HostSections, Exception]]] = []
        # Special agents can produce data for the same check_plugin_name on the same host, in this case
        # the section lines need to be extended
        for source, raw_data in fetched:
            source_result = parse_raw_data(
                make_parser(
                    self.config_cache,
                    source,
                    checking_sections=self.config_cache.make_checking_sections(
                        source.hostname, selected_sections=NO_SELECTION
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
        config_cache: ConfigCache,
        host_name: HostName,
        *,
        override_non_ok_state: ServiceState | None = None,
    ) -> None:
        self.config_cache: Final = config_cache
        self.host_name: Final = host_name
        self.override_non_ok_state: Final = override_non_ok_state

    def __call__(
        self,
        host_sections: Iterable[tuple[SourceInfo, result.Result[HostSections, Exception]]],
    ) -> Iterable[ActiveCheckResult]:
        return [
            _summarize_host_sections(
                host_sections,
                source,
                override_non_ok_state=self.override_non_ok_state,
                exit_spec=self.config_cache.exit_code_spec(source.hostname, source.ident),
                time_settings=self.config_cache.get_piggybacked_hosts_time_settings(
                    piggybacked_hostname=source.hostname
                ),
                is_piggyback=self.config_cache.is_piggyback_host(source.hostname),
            )
            for source, host_sections in host_sections
        ]


def _summarize_host_sections(
    host_sections: result.Result[HostSections, Exception],
    source: SourceInfo,
    *,
    override_non_ok_state: ServiceState | None = None,
    exit_spec: ExitSpec,
    time_settings: PiggybackTimeSettings,
    is_piggyback: bool,
) -> ActiveCheckResult:
    return ActiveCheckResult.from_subresults(
        *(
            ActiveCheckResult(
                (
                    s.state
                    if (s.state == 0 or override_non_ok_state is None)
                    else override_non_ok_state
                ),
                f"[{source.ident}] {s.summary}" if idx == 0 else s.summary,
                s.details,
                s.metrics,
            )
            for idx, s in enumerate(
                summarize(
                    source.hostname,
                    source.ipaddress,
                    host_sections,
                    exit_spec=exit_spec,
                    time_settings=time_settings,
                    is_piggyback=is_piggyback,
                    fetcher_type=source.fetcher_type,
                )
            )
        )
    )


class CMKFetcher:
    def __init__(
        self,
        config_cache: ConfigCache,
        *,
        # alphabetically sorted
        file_cache_options: FileCacheOptions,
        force_snmp_cache_refresh: bool,
        mode: Mode,
        on_error: OnError,
        password_store_file: Path,
        selected_sections: SectionNameCollection,
        simulation_mode: bool,
        max_cachefile_age: MaxAge | None = None,
        snmp_backend_override: SNMPBackendEnum | None,
    ) -> None:
        self.config_cache: Final = config_cache
        self.file_cache_options: Final = file_cache_options
        self.force_snmp_cache_refresh: Final = force_snmp_cache_refresh
        self.mode: Final = mode
        self.on_error: Final = on_error
        self.password_store_file: Final = password_store_file
        self.selected_sections: Final = selected_sections
        self.simulation_mode: Final = simulation_mode
        self.max_cachefile_age: Final = max_cachefile_age
        self.snmp_backend_override: Final = snmp_backend_override

    def __call__(self, host_name: HostName, *, ip_address: HostAddress | None) -> Sequence[
        tuple[
            SourceInfo,
            result.Result[AgentRawData | SNMPRawData, Exception],
            Snapshot,
        ]
    ]:
        nodes = self.config_cache.nodes_of(host_name)
        hosts_config = self.config_cache.hosts_config
        if nodes is None:
            # In case of keepalive we always have an ipaddress (can be 0.0.0.0 or :: when
            # address is unknown). When called as non keepalive ipaddress may be None or
            # is already an address (2nd argument)
            hosts = [
                (host_name, ip_address or config.lookup_ip_address(self.config_cache, host_name))
            ]
        else:
            hosts = [(node, config.lookup_ip_address(self.config_cache, node)) for node in nodes]

        return _fetch_all(
            itertools.chain.from_iterable(
                make_sources(
                    current_host_name,
                    current_ip_address,
                    ConfigCache.address_family(current_host_name),
                    config_cache=self.config_cache,
                    is_cluster=current_host_name in hosts_config.clusters,
                    force_snmp_cache_refresh=(
                        self.force_snmp_cache_refresh if nodes is None else False
                    ),
                    selected_sections=self.selected_sections if nodes is None else NO_SELECTION,
                    on_scan_error=self.on_error if nodes is None else OnError.RAISE,
                    simulation_mode=self.simulation_mode,
                    file_cache_options=self.file_cache_options,
                    file_cache_max_age=(
                        self.max_cachefile_age or self.config_cache.max_cachefile_age(host_name)
                    ),
                    snmp_backend_override=self.snmp_backend_override,
                    password_store_file=self.password_store_file,
                    passwords=password_store.load(self.password_store_file),
                )
                for current_host_name, current_ip_address in hosts
            ),
            simulation=self.simulation_mode,
            file_cache_options=self.file_cache_options,
            mode=self.mode,
        )


class SectionPluginMapper(SectionMap[SectionPlugin]):
    # We should probably not tap into the private `register._config` module but
    # the data we need doesn't seem to be available elsewhere.  Anyway, this is
    # an *immutable* Mapping so we are actually on the safe side.

    def __getitem__(self, __key: SectionName) -> SectionPlugin:
        plugin = _api.get_section_plugin(__key)
        return SectionPlugin(
            supersedes=plugin.supersedes,
            parse_function=plugin.parse_function,
            parsed_section_name=plugin.parsed_section_name,
        )

    def __iter__(self) -> Iterator[SectionName]:
        return iter(
            frozenset(_api.registered_agent_sections) | frozenset(_api.registered_snmp_sections)
        )

    def __len__(self) -> int:
        return len(
            frozenset(_api.registered_agent_sections) | frozenset(_api.registered_snmp_sections)
        )


class HostLabelPluginMapper(SectionMap[HostLabelPlugin]):
    def __init__(self, *, ruleset_matcher: RulesetMatcher) -> None:
        super().__init__()
        self.ruleset_matcher: Final = ruleset_matcher

    def __getitem__(self, __key: SectionName) -> HostLabelPlugin:
        plugin = _api.get_section_plugin(__key)
        return HostLabelPlugin(
            function=plugin.host_label_function,
            parameters=partial(
                config.get_plugin_parameters,
                matcher=self.ruleset_matcher,
                default_parameters=plugin.host_label_default_parameters,
                ruleset_name=plugin.host_label_ruleset_name,
                ruleset_type=plugin.host_label_ruleset_type,
                rules_getter_function=agent_based_register.get_host_label_ruleset,
            ),
        )

    def __iter__(self) -> Iterator[SectionName]:
        return iter(
            frozenset(_api.registered_agent_sections) | frozenset(_api.registered_snmp_sections)
        )

    def __len__(self) -> int:
        return len(
            frozenset(_api.registered_agent_sections) | frozenset(_api.registered_snmp_sections)
        )


class CheckPluginMapper(Mapping[CheckPluginName, CheckPlugin]):
    # See comment to SectionPluginMapper.
    def __init__(
        self,
        config_cache: ConfigCache,
        value_store_manager: ValueStoreManager,
        *,
        clusters: Container[HostName],
        rtc_package: AgentRawData | None,
    ):
        self.config_cache: Final = config_cache
        self.value_store_manager: Final = value_store_manager
        self.clusters: Final = clusters
        self.rtc_package: Final = rtc_package

    def __getitem__(self, __key: CheckPluginName) -> CheckPlugin:
        plugin = _api.get_check_plugin(__key)
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
                self.config_cache,
                host_name,
                service,
                self.value_store_manager,
                clusters=self.clusters,
            )
            # Whatch out. The CMC has to agree on the path.
            prediction_store = PredictionStore(
                cmk.utils.paths.predictions_dir / host_name / pnp_cleanup(service.description)
            )
            return get_aggregated_result(
                host_name,
                host_name in self.clusters,
                cluster_nodes=self.config_cache.nodes_of(host_name) or (),
                providers=providers,
                service=service,
                plugin=plugin,
                check_function=check_function,
                rtc_package=self.rtc_package,
                get_effective_host=self.config_cache.effective_host,
                snmp_backend=self.config_cache.get_snmp_backend(host_name),
                # In the past the creation of predictions (and the livestatus query needed)
                # was performed inside the check plug-ins context.
                # We should consider moving this side effect even further up the stack
                injected_p=InjectedParameters(
                    meta_file_path_template=prediction_store.meta_file_path_template,
                    predictions=make_updated_predictions(
                        prediction_store,
                        partial(
                            livestatus.get_rrd_data,
                            livestatus.LocalConnection(),
                            host_name,
                            service.description,
                        ),
                        time.time(),
                    ),
                ),
            )

        return CheckPlugin(
            sections=plugin.sections,
            function=check_function,
            default_parameters=plugin.check_default_parameters,
            ruleset_name=plugin.check_ruleset_name,
            discovery_ruleset_name=plugin.discovery_ruleset_name,
        )

    def __iter__(self) -> Iterator[CheckPluginName]:
        return iter(_api.registered_check_plugins)

    def __len__(self) -> int:
        return len(_api.registered_check_plugins)


def _get_check_function(
    plugin: CheckPluginAPI,
    config_cache: ConfigCache,
    host_name: HostName,
    service: ConfiguredService,
    value_store_manager: value_store.ValueStoreManager,
    *,
    clusters: Container[HostName],
) -> Callable[..., ServiceCheckResult]:
    assert plugin.name == service.check_plugin_name
    check_function = (
        cluster_mode.get_cluster_check_function(
            *config_cache.get_clustered_service_configuration(host_name, service.description),
            plugin=plugin,
            service_id=service.id(),
            value_store_manager=value_store_manager,
        )
        if host_name in clusters
        else plugin.check_function
    )

    @functools.wraps(check_function)
    def __check_function(*args: object, **kw: object) -> ServiceCheckResult:
        with (
            plugin_contexts.current_service(str(service.check_plugin_name), service.description),
            value_store_manager.namespace(service.id()),
        ):
            return _aggregate_results(consume_check_results(check_function(*args, **kw)))

    return __check_function


def _aggregate_results(
    subresults: tuple[Sequence[MetricTuple], Sequence[CheckFunctionResult]]
) -> ServiceCheckResult:
    # Impedance matching part of `get_check_function()`.
    perfdata, results = subresults
    needs_marker = len(results) > 1
    summaries: list[str] = []
    details: list[str] = []
    status = State.OK

    def _add_state_marker(result_str: str, state_marker: str) -> str:
        return result_str if state_marker in result_str else result_str + state_marker

    for result_ in results:
        status = State.worst(status, result_.state)
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

    # Empty list? Check returned nothing
    if not details:
        return ServiceCheckResult.item_not_found()

    if not summaries:
        count = len(details)
        summaries.append(
            "Everything looks OK - %d detail%s available" % (count, "" if count == 1 else "s")
        )
    all_text = [", ".join(summaries)] + details
    return ServiceCheckResult(int(status), "\n".join(all_text).strip(), perfdata)


def consume_check_results(
    # we need to accept `object`, in order to explicitly protect against plugins
    # creating invalid output.
    # Typing this as `CheckResult` will make linters complain about unreachable code.
    subresults: Iterable[object],
) -> tuple[Sequence[MetricTuple], Sequence[CheckFunctionResult]]:
    """Impedance matching between the Check API and the Check Engine."""
    ignore_results: list[IgnoreResults] = []
    results: list[CheckFunctionResult] = []
    perfdata: list[MetricTuple] = []
    for subr in subresults:
        if isinstance(subr, IgnoreResults):
            ignore_results.append(subr)
        elif isinstance(subr, Metric):
            perfdata.append((subr.name, subr.value) + subr.levels + subr.boundaries)
        elif isinstance(subr, CheckFunctionResult):
            results.append(subr)
        else:
            raise TypeError(subr)

    # Consume *all* check results, and *then* raise, if we encountered
    # an IgnoreResults instance.
    if ignore_results:
        raise IgnoreResultsError(str(ignore_results[-1]))

    return perfdata, results


def _get_monitoring_data_kwargs(
    host_name: HostName,
    is_cluster: bool,
    providers: Mapping[HostKey, Provider],
    service: ConfiguredService,
    sections: Sequence[ParsedSectionName],
    source_type: SourceType | None = None,
    *,
    cluster_nodes: Sequence[HostName],
    get_effective_host: Callable[[HostName, ServiceName], HostName],
) -> tuple[Mapping[str, object], ServiceCheckResult]:
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
            service.description,
            cluster_nodes=cluster_nodes,
            get_effective_host=get_effective_host,
        )
        return (
            get_section_cluster_kwargs(
                providers,
                nodes,
                sections,
            ),
            ServiceCheckResult.cluster_received_no_data([nk.hostname for nk in nodes]),
        )

    return (
        get_section_kwargs(
            providers,
            HostKey(host_name, source_type),
            sections,
        ),
        ServiceCheckResult.received_no_data(),
    )


def _get_clustered_service_node_keys(
    cluster_name: HostName,
    source_type: SourceType,
    service_descr: ServiceName,
    *,
    cluster_nodes: Sequence[HostName],
    get_effective_host: Callable[[HostName, ServiceName], HostName],
) -> Sequence[HostKey]:
    """Returns the node keys if a service is clustered, otherwise an empty sequence"""
    used_nodes = (
        [nn for nn in cluster_nodes if cluster_name == get_effective_host(nn, service_descr)]
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
    injected_p: InjectedParameters,
    rtc_package: AgentRawData | None,
    get_effective_host: Callable[[HostName, ServiceName], HostName],
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
            submit=False,
            data_received=False,
            result=error_result,
            cache_info=None,
        )

    item_kw = {} if service.item is None else {"item": service.item}
    params_kw = (
        {}
        if plugin.check_default_parameters is None
        else {"params": _final_read_only_check_parameters(service.parameters, injected_p)}
    )

    try:
        check_result = check_function(**item_kw, **params_kw, **section_kws)
    except IgnoreResultsError as e:
        msg = str(e) or "No service summary available"
        return AggregatedResult(
            service=service,
            submit=False,
            data_received=True,
            result=ServiceCheckResult(output=msg),
            cache_info=None,
        )
    except MKTimeout:
        raise
    except Exception:
        if cmk.utils.debug.enabled():
            raise
        check_result = ServiceCheckResult(
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
        submit=True,
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


def _final_read_only_check_parameters(
    entries: TimespecificParameters | LegacyCheckParameters,
    injected_p: InjectedParameters,
) -> Parameters:
    params = (
        entries.evaluate(timeperiod_active)
        if isinstance(entries, TimespecificParameters)
        else entries
    )
    return Parameters(
        # TODO (mo): this needs cleaning up, once we've gotten rid of tuple parameters.
        # wrap_parameters is a no-op for dictionaries.
        # For auto-migrated plugins expecting tuples, they will be
        # unwrapped by a decorator of the original check_function.
        wrap_parameters(
            (
                inject_prediction_params_recursively(params, injected_p)
                if _contains_predictive_levels(params)
                else params
            ),
        )
    )


def _contains_predictive_levels(params: LegacyCheckParameters) -> bool:
    if isinstance(params, (list, tuple)):
        return any(_contains_predictive_levels(p) for p in params)

    if isinstance(params, dict):
        return (
            "__injected__" in params
            or "__reference_metric__" in params
            or any(_contains_predictive_levels(p) for p in params.values())
        )

    return False


def inject_prediction_params_recursively(
    params: LegacyCheckParameters | Mapping[str, object],
    injected_p: InjectedParameters,
) -> LegacyCheckParameters | Mapping[str, object]:
    """This currently supports two ways to handle predictive levels.

    The "__injected__" case is legacy, the other case is the new one.
    Once the legacy case is removed, this can be simplified significantly.

    Hopefully we can move this out of this scope entirely someday (and get
    rid of the recursion).
    """
    match params:
        case (
            "cmk_postprocessed",
            "predictive_levels",
            {
                "__reference_metric__": str(metric),
                "__direction__": "upper" | "lower" as direction,
            } as p,
        ):
            if not isinstance(p, dict):  # to keep mypy happy
                raise TypeError(p)
            return _get_prediction_and_levels(p, injected_p, metric, direction)
        case tuple():
            return tuple(inject_prediction_params_recursively(v, injected_p) for v in params)
        case list():
            return list(inject_prediction_params_recursively(v, injected_p) for v in params)
        case dict():
            return {
                k: (
                    injected_p.model_dump()
                    if k == "__injected__"
                    else inject_prediction_params_recursively(v, injected_p)
                )
                for k, v in params.items()
            }
    return params


def _get_prediction_and_levels(
    params: dict, injected_p: InjectedParameters, metric: str, direction: Literal["upper", "lower"]
) -> tuple[Literal["predictive"], tuple[str, float | None, tuple[float, float] | None]]:
    return (
        "predictive",
        (
            metric,
            *lookup_predictive_levels(
                metric,
                direction,
                PredictionParameters.model_validate(
                    {k: v for k, v in params.items() if not k.startswith("__")}
                ),
                injected_p,
            ),
        ),
    )


class DiscoveryPluginMapper(Mapping[CheckPluginName, DiscoveryPlugin]):
    # See comment to SectionPluginMapper.
    def __init__(self, *, ruleset_matcher: RulesetMatcher) -> None:
        super().__init__()
        self.ruleset_matcher: Final = ruleset_matcher

    def __getitem__(self, __key: CheckPluginName) -> DiscoveryPlugin:
        # `get_check_plugin()` is not an error.  Both check plug-ins and
        # discovery are declared together in the check API.
        plugin = _api.get_check_plugin(__key)
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
                    parameters=unwrap_parameters(service.parameters),
                    service_labels={label.name: label.value for label in service.labels},
                )
                for service in plugin.discovery_function(*args, **kw)
            )

        return DiscoveryPlugin(
            sections=plugin.sections,
            service_name=plugin.service_name,
            function=__discovery_function,
            parameters=partial(
                config.get_plugin_parameters,
                matcher=self.ruleset_matcher,
                default_parameters=plugin.discovery_default_parameters,
                ruleset_name=plugin.discovery_ruleset_name,
                ruleset_type=plugin.discovery_ruleset_type,
                rules_getter_function=agent_based_register.get_discovery_ruleset,
            ),
        )

    def __iter__(self) -> Iterator[CheckPluginName]:
        return iter(_api.registered_check_plugins)

    def __len__(self) -> int:
        return len(_api.registered_check_plugins)


class InventoryPluginMapper(Mapping[InventoryPluginName, InventoryPlugin]):
    # See comment to SectionPluginMapper.
    def __getitem__(self, __key: InventoryPluginName) -> InventoryPlugin:
        plugin = _api.registered_inventory_plugins[__key]
        return InventoryPlugin(
            sections=plugin.sections,
            function=plugin.inventory_function,
            ruleset_name=plugin.inventory_ruleset_name,
            defaults=plugin.inventory_default_parameters,
        )

    def __iter__(self) -> Iterator[InventoryPluginName]:
        return iter(_api.registered_inventory_plugins)

    def __len__(self) -> int:
        return len(_api.registered_inventory_plugins)
