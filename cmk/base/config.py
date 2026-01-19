#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="comparison-overlap"

# mypy: disable-error-code="no-any-return"
# mypy: disable-error-code="no-untyped-call"
# mypy: disable-error-code="no-untyped-def"
# mypy: disable-error-code="redundant-expr"
# mypy: disable-error-code="type-arg"
# mypy: disable-error-code="unreachable"

# ruff: noqa: F405

from __future__ import annotations

import contextlib
import copy
import dataclasses
import enum
import itertools
import numbers
import os
import pickle
import socket
import sys
import time
from collections.abc import Callable, Container, Iterable, Iterator, Mapping, Sequence
from pathlib import Path
from typing import (
    Any,
    AnyStr,
    assert_never,
    Final,
    Literal,
    NamedTuple,
    overload,
    TypeGuard,
)

import cmk.ccc.debug
import cmk.ccc.version as cmk_version
import cmk.checkengine.plugin_backend as agent_based_register
import cmk.utils
import cmk.utils.paths
import cmk.utils.tags
from cmk import trace
from cmk.agent_based.legacy import discover_legacy_checks, FileLoader, find_plugin_files
from cmk.base import default_config
from cmk.base.configlib.checkengine import CheckingConfig
from cmk.base.configlib.fetchers import make_tcp_fetcher_config
from cmk.base.configlib.labels import LabelConfig
from cmk.base.configlib.loaded_config import LoadedConfigFragment
from cmk.base.configlib.piggyback import (
    guess_piggybacked_hosts_time_settings,
    make_piggyback_time_settings,
)
from cmk.base.configlib.scheduling import make_check_interval_config
from cmk.base.configlib.servicename import PassiveServiceNameConfig
from cmk.base.default_config import *  # noqa: F403
from cmk.base.parent_scan import ScanConfig as ParentScanConfig
from cmk.base.snmp_plugin_store import make_plugin_store
from cmk.base.sources import ParserConfig
from cmk.ccc import tty
from cmk.ccc.exceptions import MKBailOut, MKGeneralException
from cmk.ccc.hostaddress import HostAddress, HostName, Hosts
from cmk.ccc.regex import regex
from cmk.ccc.site import omd_site, SiteId
from cmk.checkengine.checkerplugin import ConfiguredService
from cmk.checkengine.checking import (
    merge_enforced_services,
    ServiceConfigurer,
)
from cmk.checkengine.checking.cluster_mode import ClusterMode
from cmk.checkengine.discovery import (
    AutochecksMemoizer,
    CheckPreviewEntry,
    DiscoveryCheckParameters,
    merge_cluster_autochecks,
)
from cmk.checkengine.exitspec import ExitSpec
from cmk.checkengine.inventory import HWSWInventoryParameters
from cmk.checkengine.parameters import TimespecificParameters, TimespecificParameterSet
from cmk.checkengine.plugin_backend.check_plugins_legacy import convert_legacy_check_plugins
from cmk.checkengine.plugin_backend.section_plugins_legacy import (
    convert_legacy_sections,
)
from cmk.checkengine.plugins import (
    AgentBasedPlugins,
    AgentSectionPlugin,
    AutocheckEntry,
    CheckPlugin,
    CheckPluginName,
    InventoryPlugin,
    SectionName,
    ServiceID,
    SNMPSectionPlugin,
)
from cmk.checkengine.summarize import SummaryConfig
from cmk.fetchers import (
    IPMICredentials,
    IPMIFetcher,
    NoSelectedSNMPSections,
    PiggybackFetcher,
    ProgramFetcher,
    SNMPFetcher,
    SNMPFetcherConfig,
    SNMPScanConfig,
    SNMPSectionMeta,
    TCPFetcher,
    TCPFetcherConfig,
    TLSConfig,
)
from cmk.fetchers.config import make_persisted_section_dir
from cmk.fetchers.filecache import MaxAge
from cmk.helper_interface import SourceType
from cmk.inventory.structured_data import RawIntervalFromConfig
from cmk.password_store.v1_unstable import Secret
from cmk.piggyback import backend as piggyback_backend
from cmk.server_side_calls import v1 as server_side_calls_api
from cmk.server_side_calls_backend import (
    ActiveCheck,
    ActiveServiceData,
    config_processing,
    ExecutableFinder,
    ExecutableFinderProtocol,
    load_active_checks,
    load_special_agents,
    relay_compatible_plugin_families,
    SecretsConfig,
    SpecialAgent,
    SpecialAgentCommandLine,
    SSCRules,
)
from cmk.server_side_calls_backend.config_processing import (
    extract_all_adhoc_secrets,
)
from cmk.snmplib import (  # some of these are required in the modules' namespace to load the configuration!
    parse_oid_range_config,
    SNMPBackendEnum,
    SNMPContextConfig,
    SNMPCredentials,
    SNMPHostConfig,
    SNMPSectionName,
    SNMPTiming,
    SNMPVersion,
)
from cmk.utils import config_warnings, ip_lookup, password_store
from cmk.utils.agent_registration import connection_mode_from_host_config, HostAgentConnectionMode
from cmk.utils.caching import cache_manager
from cmk.utils.check_utils import maincheckify, section_name_of
from cmk.utils.experimental_config import load_experimental_config
from cmk.utils.host_storage import (
    apply_hosts_file_to_object,
    get_host_storage_loaders,
)
from cmk.utils.ip_lookup import IPLookup, IPLookupOptional, IPStackConfig
from cmk.utils.labels import LabelManager, Labels, LabelSources
from cmk.utils.log import console
from cmk.utils.macros import replace_macros_in_str
from cmk.utils.misc import key_config_paths
from cmk.utils.password_store import make_configured_passwords_lookup
from cmk.utils.rulesets import ruleset_matcher, RuleSetName, tuple_rulesets
from cmk.utils.rulesets.ruleset_matcher import (
    RulesetMatcher,
    RulesetName,
    RuleSpec,
    SingleHostRulesetMatcherMerge,
    SingleServiceRulesetMatcherFirstParsed,
)
from cmk.utils.servicename import Item, ServiceName
from cmk.utils.tags import ComputedDataSources, TagGroupID, TagID

tracer = trace.get_tracer()

_ContactgroupName = str

# TODO: Prefix helper functions with "_".

# Default values for retry and check intervals in MINUTES
# Hosts. Check and retry intervals are same
SMARTPING_CHECK_INTERVAL: Final = 0.1
HOST_CHECK_INTERVAL: Final = 1.0
# Services. Check and retry intervals may differ
SERVICE_RETRY_INTERVAL: Final = 1.0
# SERVICE_CHECK_INTERVAL see configlib/scheduling (wip)

ServicegroupName = str
HostgroupName = str

ObjectMacros = dict[str, AnyStr]

CheckCommandArguments = Iterable[int | float | str | tuple[str, str, str]]


class FilterMode(enum.Enum):
    NONE = enum.auto()
    INCLUDE_CLUSTERED = enum.auto()


class HostCheckTable(Mapping[ServiceID, ConfiguredService]):
    def __init__(
        self,
        *,
        services: Iterable[ConfiguredService],
    ) -> None:
        self._data = {s.id(): s for s in services}

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(services={list(self._data.values())!r})"

    def __getitem__(self, key: ServiceID) -> ConfiguredService:
        return self._data[key]

    def __len__(self) -> int:
        return len(self._data)

    def __iter__(self) -> Iterator[ServiceID]:
        return iter(self._data)

    def needed_check_names(self) -> set[CheckPluginName]:
        return {s.check_plugin_name for s in self.values()}


class IgnoredActiveServices(Container[ServiceName]):
    # only works for active and custom services, b/c we assume there are no discovered labels
    def __init__(self, config_cache: ConfigCache, host_name: HostName) -> None:
        self._config_cache = config_cache
        self._host_name = host_name

    def __contains__(self, service_name: object) -> bool:
        if not isinstance(service_name, ServiceName):
            return False
        return self._config_cache.service_ignored(
            self._host_name,
            service_name,
            self._config_cache.label_manager.labels_of_service(self._host_name, service_name, {}),
        )


def _aggregate_check_table_services(
    host_name: HostName,
    *,
    config_cache: ConfigCache,
    service_name_config: Callable[[HostName, ServiceID, str | None], ServiceName],
    enforced_services_table: Callable[
        [HostName], Mapping[ServiceID, tuple[object, ConfiguredService]]
    ],
    skip_ignored: bool,
    filter_mode: FilterMode,
    get_autochecks: Callable[[HostAddress], Sequence[AutocheckEntry]],
    configure_autochecks: Callable[
        [HostName, Sequence[AutocheckEntry]],
        Iterable[ConfiguredService],
    ],
    plugins: Mapping[CheckPluginName, CheckPlugin],
) -> Iterable[ConfiguredService]:
    sfilter = _ServiceFilter(
        host_name,
        config_cache=config_cache,
        mode=filter_mode,
        skip_ignored=skip_ignored,
    )

    is_cluster = host_name in config_cache.hosts_config.clusters

    # process all entries that are specific to the host
    # in search (single host) or that might match the host.
    if not config_cache.is_ping_host(host_name):
        if is_cluster:
            # Add checks a cluster might receive from its nodes
            yield from (
                s
                for s in _get_clustered_services(
                    config_cache,
                    service_name_config,
                    host_name,
                    get_autochecks,
                    configure_autochecks,
                    enforced_services_table,
                    plugins,
                )
                if sfilter.keep(s)
            )
        else:
            yield from (
                s
                for s in configure_autochecks(host_name, get_autochecks(host_name))
                if sfilter.keep(s)
            )

    yield from (svc for _, svc in enforced_services_table(host_name).values() if sfilter.keep(svc))

    # NOTE: as far as I can see, we only have two cases with the filter mode.
    # Either we compute services to check, or we compute services for fetching.
    if filter_mode is not FilterMode.INCLUDE_CLUSTERED:
        return
    # Now we are in the latter case.
    # Since the clusters don't fetch data themselves, we may have to include more
    # services than are attached to the host itself, so that we get the needed data
    # even if a failover occurred since the last discovery.

    # Consider the case where we've clustered 3 nodes `node{1,2,3}`.
    # Let `service A` be
    #  * (only) in the autochecks of node1
    #  * clustered by a clustered service rule matching hosts node1 and node2.
    #
    # The following must include `service A` for node1 and node2 but *not* for node3.
    # Failing to exclude node3 might add an undesired service to it.
    # For node1 it was added from the autochecks above.

    yield from (
        s
        # ... this adds it for node2
        for s in _get_services_from_cluster_nodes(
            config_cache,
            service_name_config,
            host_name,
            get_autochecks,
            configure_autochecks,
            enforced_services_table,
            plugins,
        )
        if sfilter.keep(s)
        # ... and this condition prevents it from being added on node3
        # 'not is_mine' means: would it be there, it would be clustered.
        and not sfilter.is_mine(s)
    )


class _ServiceFilter:
    def __init__(
        self,
        host_name: HostName,
        *,
        config_cache: ConfigCache,
        mode: FilterMode,
        skip_ignored: bool,
    ) -> None:
        """Filter services for a specific host

        FilterMode.NONE              -> default, returns only checks for this host
        FilterMode.INCLUDE_CLUSTERED -> returns checks of own host, including clustered checks
        """
        self._host_name = host_name
        self._config_cache = config_cache
        self._mode = mode
        self._skip_ignored = skip_ignored

    def keep(self, service: ConfiguredService) -> bool:
        if self._skip_ignored and (
            self._config_cache.check_plugin_ignored(self._host_name, service.check_plugin_name)
            or self._config_cache.service_ignored(
                self._host_name,
                service.description,
                service.labels,
            )
        ):
            return False

        if self._mode is FilterMode.INCLUDE_CLUSTERED:
            return True
        if self._mode is FilterMode.NONE:
            return self.is_mine(service)

        return assert_never(self._mode)

    def is_mine(self, service: ConfiguredService) -> bool:
        """Determine whether a service should be displayed on this host's service overview.

        If the service should be displayed elsewhere, this means the service is clustered and
        should be displayed on the cluster host's service overview.
        """
        return (
            self._config_cache.effective_host(
                self._host_name,
                service.description,
                service.labels,
            )
            == self._host_name
        )


def _get_services_from_cluster_nodes(
    config_cache: ConfigCache,
    service_name_config: Callable[[HostName, ServiceID, str | None], ServiceName],
    node_name: HostName,
    get_autochecks: Callable[[HostAddress], Sequence[AutocheckEntry]],
    configure_autochecks: Callable[
        [HostName, Sequence[AutocheckEntry]],
        Iterable[ConfiguredService],
    ],
    enforced_services_table: Callable[
        [HostName], Mapping[ServiceID, tuple[object, ConfiguredService]]
    ],
    plugins: Mapping[CheckPluginName, CheckPlugin],
) -> Iterable[ConfiguredService]:
    for cluster in config_cache.clusters_of(node_name):
        yield from _get_clustered_services(
            config_cache,
            service_name_config,
            cluster,
            get_autochecks,
            configure_autochecks,
            enforced_services_table,
            plugins,
        )


def _get_clustered_services(
    config_cache: ConfigCache,
    service_name_config: Callable[[HostName, ServiceID, str | None], ServiceName],
    cluster_name: HostName,
    get_autochecks: Callable[[HostAddress], Sequence[AutocheckEntry]],
    configure_autochecks: Callable[
        [HostName, Sequence[AutocheckEntry]],
        Iterable[ConfiguredService],
    ],
    enforced_services_table: Callable[
        [HostName], Mapping[ServiceID, tuple[object, ConfiguredService]]
    ],
    plugins: Mapping[CheckPluginName, CheckPlugin],
) -> Iterable[ConfiguredService]:
    nodes = config_cache.nodes(cluster_name)

    if not config_cache.is_ping_host(cluster_name):

        def appears_on_cluster(node_name: HostAddress, entry: AutocheckEntry) -> bool:
            if config_cache.check_plugin_ignored(node_name, entry.check_plugin_name):
                return False
            service_name = service_name_config(
                node_name,
                entry.id(),
                (
                    None
                    if (
                        p := agent_based_register.get_check_plugin(entry.check_plugin_name, plugins)
                    )
                    is None
                    else p.service_name
                ),
            )
            service_labels = config_cache.label_manager.labels_of_service(
                node_name, service_name, entry.service_labels
            )

            return not config_cache.service_ignored(node_name, service_name, service_labels) and (
                config_cache.effective_host(node_name, service_name, service_labels) == cluster_name
            )

        yield from configure_autochecks(
            cluster_name,
            merge_cluster_autochecks(
                {node: get_autochecks(node) for node in nodes},
                appears_on_cluster,
            ),
        )

    yield from merge_enforced_services(
        {node_name: enforced_services_table(node_name) for node_name in nodes},
        # similiar to appears_on_cluster, but we don't check for ignored services
        lambda node_name, service_name, discovered_labels: (
            config_cache.effective_host(
                node_name,
                service_name,
                config_cache.label_manager.labels_of_service(
                    node_name, service_name, discovered_labels
                ),
            )
            == cluster_name
        ),
        lambda description, disovered_labels: config_cache.label_manager.labels_of_service(
            cluster_name, description, disovered_labels
        ),
    )


@dataclasses.dataclass(frozen=True, kw_only=True)
class ClusterCacheInfo:
    clusters_of: Mapping[HostName, Sequence[HostName]]
    nodes_of: Mapping[HostName, Sequence[HostName]]


CheckContext = dict[str, Any]
GetCheckApiContext = Callable[[], dict[str, Any]]
GetInventoryApiContext = Callable[[], dict[str, Any]]
CheckIncludes = list[str]


class CheckmkCheckParameters(NamedTuple):
    enabled: bool


HostCheckCommand = None | str | tuple[str, int | str]
PingLevels = dict[str, int | tuple[float, float]]

# TODO (sk): Make the type narrower: TypedDict isn't easy in the case - "too chaotic usage"(c) SP
ObjectAttributes = dict[str, Any]

GroupDefinitions = dict[str, str]


class _NestedExitSpec(ExitSpec, total=False):
    overall: ExitSpec
    individual: dict[str, ExitSpec]


def handle_ip_lookup_failure(host_name: HostName, exc: Exception) -> None:
    """Writes error messages to the console (stdout)."""
    console.warning(
        tty.format_warning(
            f"\nCannot lookup IP address of '{host_name}' ({exc}). "
            "The host will not be monitored correctly.\n"
        )
    )


def get_default_config() -> dict[str, Any]:
    """Provides a dictionary containing the Check_MK default configuration"""
    return {
        key: copy.deepcopy(value) if isinstance(value, dict | list) else value
        for key, value in default_config.__dict__.items()
        if key[0] != "_"
    }


def load_default_config() -> None:
    globals().update(get_default_config())


def register(name: str, default_value: Any) -> None:
    """Register a new configuration variable within Check_MK base."""
    setattr(default_config, name, default_value)


# .
#   .--Read Config---------------------------------------------------------.
#   |        ____                _    ____             __ _                |
#   |       |  _ \ ___  __ _  __| |  / ___|___  _ __  / _(_) __ _          |
#   |       | |_) / _ \/ _` |/ _` | | |   / _ \| '_ \| |_| |/ _` |         |
#   |       |  _ <  __/ (_| | (_| | | |__| (_) | | | |  _| | (_| |         |
#   |       |_| \_\___|\__,_|\__,_|  \____\___/|_| |_|_| |_|\__, |         |
#   |                                                       |___/          |
#   +----------------------------------------------------------------------+
#   | Code for reading the configuration files.                            |
#   '----------------------------------------------------------------------'


@dataclasses.dataclass(frozen=True, kw_only=True)
class LoadingResult:
    """Return the result of the config loading process.

    This is hopefully temporary, until ConfigCache is dissolved ...
    """

    loaded_config: LoadedConfigFragment
    config_cache: ConfigCache


# This function still mostly manipulates a global state.
# Passing the discovery rulesets as an argument is a first step to make it more functional.
def load(
    discovery_rulesets: Iterable[RuleSetName],
    get_builtin_host_labels: Callable[[SiteId], Labels],
    with_conf_d: bool = True,
    validate_hosts: bool = True,
) -> LoadingResult:
    _initialize_config()

    _changed_var_names = _load_config(with_conf_d)

    loading_result = _perform_post_config_loading_actions(
        discovery_rulesets, get_builtin_host_labels
    )

    if validate_hosts:
        hosts_config = loading_result.config_cache.hosts_config
        if duplicates := sorted(
            hosts_config.duplicates(
                lambda hn: loading_result.config_cache.is_active(hn)
                and loading_result.config_cache.is_online(hn)
            )
        ):
            # TODO: Raise an exception
            console.error(
                f"Error in configuration: duplicate hosts: {', '.join(duplicates)}",
                file=sys.stderr,
            )
            sys.exit(3)

    return loading_result


# This function still mostly manipulates a global state.
# Passing the discovery rulesets as an argument is a first step to make it more functional.
def load_packed_config(
    config_path: Path,
    discovery_rulesets: Iterable[RuleSetName],
    get_builtin_host_labels: Callable[[SiteId], Labels],
) -> LoadingResult:
    """Load the configuration for the CMK helpers of CMC

    These files are written by PackedConfig().

    Should have a result similar to the load() above. With the exception that the
    check helpers would only need check related config variables.

    The validations which are performed during load() also don't need to be performed.

    See Also:
        cmk.base.core.nagios._dump_precompiled_hostcheck()

    """
    _initialize_config()
    globals().update(PackedConfigStore.from_serial(config_path).read())
    return _perform_post_config_loading_actions(discovery_rulesets, get_builtin_host_labels)


def _initialize_config() -> None:
    load_default_config()


def _perform_post_config_loading_actions(
    discovery_rulesets: Iterable[RuleSetName],
    get_builtin_host_labels: Callable[[SiteId], Labels],
) -> LoadingResult:
    """These tasks must be performed after loading the Check_MK base configuration"""
    # First cleanup things (needed for e.g. reloading the config)
    cache_manager.clear_all()

    global_dict = globals()
    discovery_settings = _collect_parameter_rulesets_from_globals(global_dict, discovery_rulesets)
    _transform_plugin_names_from_160_to_170(global_dict)
    _drop_invalid_ssc_rules(global_dict)

    loaded_config = LoadedConfigFragment(
        folder_attributes=folder_attributes,
        discovery_rules=discovery_settings,
        checkgroup_parameters=checkgroup_parameters,
        static_checks=static_checks,
        service_rule_groups=service_rule_groups,
        service_descriptions=service_descriptions,
        service_description_translation=service_description_translation,
        use_new_descriptions_for=use_new_descriptions_for,
        monitoring_core=monitoring_core,
        nagios_illegal_chars=nagios_illegal_chars,
        cmc_illegal_chars=cmc_illegal_chars,
        all_hosts=all_hosts,
        clusters=clusters,
        shadow_hosts=shadow_hosts,
        service_dependencies=service_dependencies,
        fallback_agent_output_encoding=fallback_agent_output_encoding,
        agent_config=agent_config,
        agent_port=agent_port,
        agent_ports=agent_ports,
        tcp_connect_timeout=tcp_connect_timeout,
        tcp_connect_timeouts=tcp_connect_timeouts,
        encryption_handling=encryption_handling,
        piggyback_translation=piggyback_translation,
        piggybacked_host_files=piggybacked_host_files,
        piggyback_max_cachefile_age=piggyback_max_cachefile_age,
        agent_encryption=agent_encryption,
        agent_exclude_sections=agent_exclude_sections,
        cmc_real_time_checks=cmc_real_time_checks,
        snmp_check_interval=snmp_check_interval,
        agent_bakery_logging=agent_bakery_logging,
        apply_bake_revision=apply_bake_revision,
        bake_agents_on_restart=bake_agents_on_restart,
        is_distributed_setup_remote_site=is_distributed_setup_remote_site,
        simulation_mode=simulation_mode,
        use_dns_cache=use_dns_cache,
        ipaddresses=ipaddresses,
        ipv6addresses=ipv6addresses,
        inventory_check_interval=inventory_check_interval,
        fake_dns=fake_dns,
        tag_config=tag_config,
        host_tags=host_tags,
        cmc_log_rrdcreation=cmc_log_rrdcreation,
        cmc_host_rrd_config=cmc_host_rrd_config,
        cmc_statehist_cache=cmc_statehist_cache,
        cmc_timeperiod_horizon=cmc_timeperiod_horizon,
        host_recurring_downtimes=host_recurring_downtimes,
        cmc_flap_settings=cmc_flap_settings,
        cmc_host_flap_settings=cmc_host_flap_settings,
        cmc_host_long_output_in_monitoring_history=cmc_host_long_output_in_monitoring_history,
        host_state_translation=host_state_translation,
        cmc_smartping_settings=cmc_smartping_settings,
        cmc_service_rrd_config=cmc_service_rrd_config,
        service_recurring_downtimes=service_recurring_downtimes,
        cmc_service_flap_settings=cmc_service_flap_settings,
        cmc_service_long_output_in_monitoring_history=cmc_service_long_output_in_monitoring_history,
        service_state_translation=service_state_translation,
        cmc_check_timeout=cmc_check_timeout,
        cmc_service_check_timeout=cmc_service_check_timeout,
        cmc_graphite_host_metrics=cmc_graphite_host_metrics,
        cmc_graphite_service_metrics=cmc_graphite_service_metrics,
        cmc_influxdb_service_metrics=cmc_influxdb_service_metrics,
        cmc_log_levels=cmc_log_levels,
        cluster_max_cachefile_age=cluster_max_cachefile_age,
        http_proxies=http_proxies,
        oauth2_connections=oauth2_connections,
        extra_service_conf=extra_service_conf,
        timeperiods=timeperiods,
        check_periods=check_periods,
        relays=relays,
        product_telemetry=product_telemetry,
        cmc_config_multiprocessing=cmc_config_multiprocessing,
    )

    config_cache = ConfigCache(loaded_config, get_builtin_host_labels).initialize(
        get_builtin_host_labels
    )
    _globally_cache_config_cache(config_cache)
    return LoadingResult(
        loaded_config=loaded_config,
        config_cache=config_cache,
    )


class SetFolderPathAbstract:
    def __init__(self, the_object: Iterable) -> None:
        # TODO: Cleanup this somehow to work nicer with mypy
        super().__init__(the_object)  # type: ignore[call-arg]
        self._current_path: str | None = None
        self._collected_host_paths: dict[HostName, str] = {}

    def set_current_path(self, current_path: str | None) -> None:
        self._current_path = current_path

    @property
    def collected_host_paths(self) -> Mapping[HostName, str]:
        return self._collected_host_paths

    def _set_folder_paths(self, new_hosts: Iterable[str]) -> None:
        if self._current_path is None:
            return
        for hostname in strip_tags(new_hosts):
            self._collected_host_paths[hostname] = self._current_path


class SetFolderPathList(SetFolderPathAbstract, list):
    def __iadd__(self, new_hosts: Iterable[str]) -> SetFolderPathList:  # type: ignore[override]
        assert isinstance(new_hosts, list)
        self._set_folder_paths(new_hosts)
        super().__iadd__(new_hosts)
        return self

    def extend(self, new_hosts: Iterable[str]) -> None:
        self._set_folder_paths(new_hosts)
        super().extend(new_hosts)

    # Probably unused
    def __add__(self, new_hosts: Iterable[str]) -> SetFolderPathList:  # type: ignore[override]
        assert isinstance(new_hosts, list)
        self._set_folder_paths(new_hosts)
        return SetFolderPathList(super().__add__(new_hosts))

    # Probably unused
    def append(self, new_host: str) -> None:
        self._set_folder_paths([new_host])
        super().append(new_host)


# TODO: This whole class must die!
class SetFolderPathDict(SetFolderPathAbstract, dict):
    # TODO: How to annotate this?
    def update(self, new_hosts):  # type: ignore[override]
        self._set_folder_paths(new_hosts)
        return super().update(new_hosts)

    # Probably unused
    def __setitem__(self, cluster_name: Any, value: Any) -> Any:
        self._set_folder_paths([cluster_name])
        return super().__setitem__(cluster_name, value)


def _load_config_file(file_to_load: Path, into_dict: dict[str, Any]) -> None:
    exec(compile(file_to_load.read_text(), file_to_load, "exec"), into_dict, into_dict)  # nosec B102 # BNS:aee528


def _load_config(with_conf_d: bool) -> set[str]:
    helper_vars = {
        "FOLDER_PATH": None,
    }

    global all_hosts
    global clusters

    all_hosts = SetFolderPathList(all_hosts)
    clusters = SetFolderPathDict(clusters)

    global_dict = globals()
    pre_load_vars = {**global_dict}

    global_dict |= helper_vars

    # Load assorted experimental parameters if any
    experimental_config = load_experimental_config(cmk.utils.paths.default_config_dir)

    host_storage_loaders = get_host_storage_loaders(
        experimental_config.get("config_storage_format")
    )
    for path in get_config_file_paths(with_conf_d):
        try:
            # Make the config path available as a global variable to be used
            # within the configuration file. The FOLDER_PATH is only used by
            # rules.mk files these days, but may also be used in some legacy
            # config files or files generated by 3rd party mechanisms.
            current_path: str | None = None
            folder_path: str | None = None
            with contextlib.suppress(ValueError):
                relative_path = path.relative_to(cmk.utils.paths.check_mk_config_dir)
                current_path = f"/{relative_path}"
                folder_path = str(relative_path.parent)
            global_dict["FOLDER_PATH"] = folder_path

            all_hosts.set_current_path(current_path)
            clusters.set_current_path(current_path)

            if path.name == "hosts.mk":
                apply_hosts_file_to_object(path.with_suffix(""), host_storage_loaders, global_dict)
            else:
                _load_config_file(path, global_dict)

            if not isinstance(all_hosts, SetFolderPathList):
                raise MKGeneralException(
                    "Load config error: The all_hosts parameter was modified through an other method than: x+=a or x=x+a"
                )
            host_paths.update(all_hosts.collected_host_paths)

            if not isinstance(clusters, SetFolderPathDict):
                raise MKGeneralException(
                    "Load config error: The clusters parameter was modified through an other method than: x['a']=b or x.update({'a': b})"
                )
            host_paths.update(clusters.collected_host_paths)

        except Exception as e:
            if cmk.ccc.debug.enabled():
                raise
            if sys.stderr.isatty():
                console.error(f"Cannot read in configuration file {path}: {e}", file=sys.stderr)
            sys.exit(1)

    # Cleanup global helper vars
    for helper_var in helper_vars:
        del global_dict[helper_var]

    # Revert specialised SetFolderPath classes back to normal, because it improves
    # the lookup performance and the helper_vars are no longer available anyway..
    all_hosts = list(all_hosts)
    clusters = dict(clusters)

    return {k for k, v in global_dict.items() if k not in pre_load_vars or v != pre_load_vars[k]}


def _transform_plugin_names_from_160_to_170(global_dict: dict[str, Any]) -> None:
    # Pre 1.7.0 check plug-in names may have dots or dashes (one case) in them.
    # Now they don't, and we have to translate all variables that may use them:
    if "service_descriptions" in global_dict:
        global_dict["service_descriptions"] = {
            maincheckify(k): str(v) for k, v in global_dict["service_descriptions"].items()
        }


def _is_mapping_rulespec(rs: RuleSpec[object]) -> TypeGuard[RuleSpec[Mapping[str, object]]]:
    return isinstance(rs["value"], dict) and all(isinstance(k, str) for k in rs["value"])


def _drop_invalid_ssc_rules(global_dict: dict[str, Any]) -> None:
    """Drop all SSC rules whos values are not Mapping[str, object]s

    These days, we rely on all values of these type of rules to be Mappings.
    This is ensured by the new ruleset types, but users could have old
    configurations flying around.
    """
    for ssc_rule_type in ("active_checks", "special_agents"):
        if ssc_rule_type not in global_dict:
            continue
        global_dict[ssc_rule_type] = {
            k: [rs for rs in rulespecs if _is_mapping_rulespec(rs)]
            for k, rulespecs in global_dict[ssc_rule_type].items()
        }


def _collect_parameter_rulesets_from_globals(
    global_dict: dict[str, Any], discovery_rulesets: Iterable[RuleSetName]
) -> Mapping[RuleSetName, Sequence[RuleSpec]]:
    return {
        ruleset_name: global_dict.pop(str(ruleset_name), []) for ruleset_name in discovery_rulesets
    }


# Create list of all files to be included during configuration loading
def get_config_file_paths(with_conf_d: bool) -> list[Path]:
    list_of_files = [cmk.utils.paths.main_config_file]
    if with_conf_d:
        all_files = cmk.utils.paths.check_mk_config_dir.rglob("*")
        list_of_files += sorted([p for p in all_files if p.suffix in {".mk"}], key=key_config_paths)
    for path in [cmk.utils.paths.final_config_file, cmk.utils.paths.local_config_file]:
        if path.exists():
            list_of_files.append(path)
    return list_of_files


def save_packed_config(
    config_path: Path,
    config_cache: ConfigCache,
    discovery_rules: Mapping[RuleSetName, Sequence[RuleSpec]],
) -> None:
    """Create and store a precompiled configuration for Checkmk helper processes"""
    PackedConfigStore.from_serial(config_path).write(
        PackedConfigGenerator(config_cache, discovery_rules).generate()
    )


class PackedConfigGenerator:
    """The precompiled host checks and the CMC Check_MK helpers use a
    "precompiled" part of the Check_MK configuration during runtime.

    a) They must not use the live config from etc/check_mk during
       startup. They are only allowed to load the config activated by
       the user.

    b) They must not load the whole Check_MK config. Because they only
       need the options needed for checking
    """

    # These variables are part of the Checkmk configuration, but are not needed
    # by the Checkmk keepalive mode, so exclude them from the packed config
    _skipped_config_variable_names = [
        "define_contactgroups",
        "define_hostgroups",
        "define_servicegroups",
        "service_contactgroups",
        "host_contactgroups",
        "service_groups",
        "host_groups",
        "contacts",
        "timeperiods",
        "extra_nagios_conf",
    ]

    def __init__(
        self, config_cache: ConfigCache, discovery_rules: Mapping[RuleSetName, Sequence[RuleSpec]]
    ) -> None:
        self._config_cache = config_cache
        self._discovery_rules = discovery_rules

    def generate(self) -> Mapping[str, Any]:
        helper_config: dict[str, Any] = {}

        # These functions purpose is to filter out hosts which are monitored on different sites
        hosts_config = self._config_cache.hosts_config
        active_hosts = frozenset(
            hn
            for hn in itertools.chain(hosts_config.hosts, hosts_config.clusters)
            if self._config_cache.is_active(hn) and self._config_cache.is_online(hn)
        )

        def filter_all_hosts(all_hosts_orig: list[HostName]) -> list[HostName]:
            all_hosts_red = []
            for host_entry in all_hosts_orig:
                hostname = host_entry.split("|", 1)[0]
                if hostname in active_hosts:
                    all_hosts_red.append(host_entry)
            return all_hosts_red

        def filter_clusters(
            clusters_orig: dict[HostName, list[HostName]],
        ) -> dict[HostName, list[HostName]]:
            clusters_red = {}
            for cluster_entry, cluster_nodes in clusters_orig.items():
                clustername = HostName(cluster_entry.split("|", 1)[0])
                # Include offline cluster HOSTS.
                # Otherwise, services clustered to those hosts will wrongly be checked by the NODES.
                if clustername in hosts_config.clusters and self._config_cache.is_active(
                    clustername
                ):
                    # But exclude offline cluster NODES.
                    # Otherwise, the check on the cluster HOST will fail.
                    clusters_red[cluster_entry] = [
                        node for node in cluster_nodes if node in active_hosts
                    ]
            return clusters_red

        def filter_hostname_in_dict(
            values: dict[HostName, dict[str, str]],
        ) -> dict[HostName, dict[str, str]]:
            values_red = {}
            for hostname, attributes in values.items():
                if hostname in active_hosts:
                    values_red[hostname] = attributes
            return values_red

        def filter_extra_service_conf(
            values: dict[str, list[dict[str, str]]],
        ) -> dict[str, list[dict[str, str]]]:
            return {
                "check_interval": values.get("check_interval", []),
                "_ec_sl": values.get("_ec_sl", []),
            }

        filter_var_functions: dict[str, Callable[[Any], Any]] = {
            "all_hosts": filter_all_hosts,
            "clusters": filter_clusters,
            "host_attributes": filter_hostname_in_dict,
            "ipaddresses": filter_hostname_in_dict,
            "ipv6addresses": filter_hostname_in_dict,
            "explicit_snmp_communities": filter_hostname_in_dict,
            "hosttags": filter_hostname_in_dict,  # unknown key, might be typo or legacy option
            "host_tags": filter_hostname_in_dict,
            "host_paths": filter_hostname_in_dict,
            "extra_service_conf": filter_extra_service_conf,
        }

        #
        # Add modified Checkmk base settings
        #

        variable_defaults = get_default_config()

        global_variables = globals()

        for varname, default_value in variable_defaults.items():
            if varname in self._skipped_config_variable_names:
                continue

            val = global_variables[varname]

            if val == default_value:
                continue

            if varname in filter_var_functions:
                val = filter_var_functions[varname](val)

            helper_config[varname] = val

        return helper_config | {str(k): v for k, v in self._discovery_rules.items()}


class PackedConfigStore:
    """Caring about persistence of the packed configuration"""

    def __init__(self, path: Path) -> None:
        self.path: Final = path

    @classmethod
    def from_serial(cls, config_path: Path) -> PackedConfigStore:
        return cls(cls.make_packed_config_store_path(config_path))

    @classmethod
    def make_packed_config_store_path(cls, config_path: Path) -> Path:
        return config_path / "precompiled_check_config.mk"

    def write(self, helper_config: Mapping[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = self.path.with_suffix(f"{self.path.suffix}.compiled")
        with tmp_path.open("wb") as compiled_file:
            pickle.dump(helper_config, compiled_file)
        tmp_path.rename(self.path)

    def read(self) -> Mapping[str, Any]:
        with self.path.open("rb") as f:
            return pickle.load(f)  # nosec B301 # BNS:c3c5e9


@contextlib.contextmanager
def set_use_core_config(
    *, autochecks_dir: Path, discovered_host_labels_dir: Path
) -> Iterator[None]:
    """The keepalive helpers should always use the core configuration that
    has been created with "cmk -U". This includes the dynamic configuration
    parts like the autochecks.

    Instead of loading e.g. the autochecks from the regular path
    "var/check_mk/autochecks" the helper should always load the files from
    "var/check_mk/core/autochecks" instead.

    We ensure this by changing the global paths in cmk.utils.paths to point
    to the helper paths."""
    orig_autochecks_dir: Final = cmk.utils.paths.autochecks_dir
    orig_discovered_host_labels_dir: Final = cmk.utils.paths.discovered_host_labels_dir
    try:
        cmk.utils.paths.autochecks_dir = autochecks_dir
        cmk.utils.paths.discovered_host_labels_dir = discovered_host_labels_dir
        yield
    finally:
        cmk.utils.paths.autochecks_dir = orig_autochecks_dir
        cmk.utils.paths.discovered_host_labels_dir = orig_discovered_host_labels_dir


def parse_hostname_list(
    config_cache: ConfigCache,
    hosts_config: Hosts,
    args: list[str],
    with_clusters: bool = True,
    with_foreign_hosts: bool = False,
) -> Sequence[HostName]:
    if with_foreign_hosts:
        valid_hosts = set(hosts_config.hosts)
    else:
        valid_hosts = {
            hn
            for hn in hosts_config.hosts
            if config_cache.is_active(hn) and config_cache.is_online(hn)
        }

    if with_clusters:
        valid_hosts = valid_hosts.union(
            hn
            for hn in hosts_config.clusters
            # Inconsistent with `with_foreign_hosts` above.
            if config_cache.is_active(hn) and config_cache.is_online(hn)
        )

    hostlist: list[HostName] = []
    for arg in args:
        if arg[0] != "@" and arg in valid_hosts:
            hostlist.append(HostName(arg))
        else:
            if arg[0] == "@":
                arg = arg[1:]
            tagspec = arg.split(",")

            num_found = 0
            for hostname in valid_hosts:
                if tuple_rulesets.hosttags_match_taglist(
                    config_cache.host_tags.tag_list(hostname), (TagID(_) for _ in tagspec)
                ):
                    hostlist.append(hostname)
                    num_found += 1
            if num_found == 0:
                raise MKBailOut(
                    "Host name or tag specification '%s' does not match any host." % arg
                )
    return hostlist


# .
#   .--Host tags-----------------------------------------------------------.
#   |              _   _           _     _                                 |
#   |             | | | | ___  ___| |_  | |_ __ _  __ _ ___                |
#   |             | |_| |/ _ \/ __| __| | __/ _` |/ _` / __|               |
#   |             |  _  | (_) \__ \ |_  | || (_| | (_| \__ \               |
#   |             |_| |_|\___/|___/\__|  \__\__,_|\__, |___/               |
#   |                                             |___/                    |
#   +----------------------------------------------------------------------+
#   |  Helper functions for dealing with host tags                         |
#   '----------------------------------------------------------------------'


def strip_tags(tagged_hostlist: Iterable[str]) -> Sequence[HostName]:
    cache = cache_manager.obtain_cache("strip_tags")

    cache_id = tuple(tagged_hostlist)
    with contextlib.suppress(KeyError):
        return cache[cache_id]
    return cache.setdefault(cache_id, [HostName(h.split("|", 1)[0]) for h in tagged_hostlist])


# .
#   .--Services------------------------------------------------------------.
#   |                ____                  _                               |
#   |               / ___|  ___ _ ____   _(_) ___ ___  ___                 |
#   |               \___ \ / _ \ '__\ \ / / |/ __/ _ \/ __|                |
#   |                ___) |  __/ |   \ V /| | (_|  __/\__ \                |
#   |               |____/ \___|_|    \_/ |_|\___\___||___/                |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | Service related helper functions                                     |
#   '----------------------------------------------------------------------'


def _make_service_description_cb(
    passive_service_name_config: Callable[[HostName, ServiceID, str | None], ServiceName],
    check_plugins: Mapping[CheckPluginName, CheckPlugin],
) -> Callable[[HostName, ServiceID], ServiceName]:
    """Replacement for functool.partial(service_description, matcher)

    functools.partial is not supported by the mypy type checker.
    """

    def callback(hostname: HostName, service_id: ServiceID) -> ServiceName:
        return passive_service_name_config(
            hostname,
            service_id,
            (
                None
                if (p := agent_based_register.get_check_plugin(service_id.name, check_plugins))
                is None
                else p.service_name
            ),
        )

    return callback


# TODO: Make this use the generic "rulesets" functions
# a) This function has never been configurable via WATO (see https://mathias-kettner.de/checkmk_service_dependencies.html)
# b) It only affects the Nagios core - CMC does not implement service dependencies
# c) This function implements some specific regex replacing match+replace which makes it incompatible to
#    regular service rulesets. Therefore service_extra_conf() can not easily be used :-/
@dataclasses.dataclass(frozen=True)
class ServiceDependsOn:
    tag_list: Callable[[HostName], Sequence[TagID]]
    service_dependencies: Sequence[
        tuple[str, Sequence[TagID], Sequence[str], Sequence[str]]
        | tuple[str, Sequence[TagID], Sequence[str], Sequence[str], dict[str, Any]]
        | tuple[str, Sequence[str], Sequence[str]]
        | tuple[str, Sequence[str], Sequence[str], dict[str, Any]]
    ]

    def __call__(self, hostname: HostName, servicedesc: ServiceName) -> list[ServiceName]:
        """Return a list of services this service depends on"""
        deps = []
        for entry in self.service_dependencies:
            entry, rule_options = tuple_rulesets.get_rule_options(entry)
            if rule_options.get("disabled"):
                continue
            if len(entry) == 3:
                depname, hostlist, patternlist = entry
                tags: Sequence[TagID] = []
            elif len(entry) == 4:
                depname, tags, hostlist, patternlist = entry
            else:
                raise MKGeneralException(
                    "Invalid entry '%r' in service dependencies: must have 3 or 4 entries" % entry
                )
            if tuple_rulesets.hosttags_match_taglist(
                self.tag_list(hostname), tags
            ) and tuple_rulesets.in_extraconf_hostlist(hostlist, hostname):
                for pattern in patternlist:
                    if matchobject := regex(pattern).search(servicedesc):
                        try:
                            item = matchobject.groups()[-1]
                            deps.append(depname % item)
                        except (IndexError, TypeError):
                            deps.append(depname)
        return deps


# .
#   .--Constants-----------------------------------------------------------.
#   |              ____                _              _                    |
#   |             / ___|___  _ __  ___| |_ __ _ _ __ | |_ ___              |
#   |            | |   / _ \| '_ \/ __| __/ _` | '_ \| __/ __|             |
#   |            | |__| (_) | | | \__ \ || (_| | | | | |_\__ \             |
#   |             \____\___/|_| |_|___/\__\__,_|_| |_|\__|___/             |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | Some constants to be used in the configuration and at other places   |
#   '----------------------------------------------------------------------'

# Conveniance macros for legacy tuple based host and service rules
# TODO: Deprecate these in a gentle way
PHYSICAL_HOSTS = tuple_rulesets.PHYSICAL_HOSTS
CLUSTER_HOSTS = tuple_rulesets.CLUSTER_HOSTS
ALL_HOSTS = tuple_rulesets.ALL_HOSTS
ALL_SERVICES = tuple_rulesets.ALL_SERVICES
NEGATE = tuple_rulesets.NEGATE


# workaround: set of check-groups that are to be treated as service-checks even if
#   the item is None
service_rule_groups = {"temperature"}


# .
#   .--Loading-------------------------------------------------------------.
#   |                _                    _ _                              |
#   |               | |    ___   __ _  __| (_)_ __   __ _                  |
#   |               | |   / _ \ / _` |/ _` | | '_ \ / _` |                 |
#   |               | |__| (_) | (_| | (_| | | | | | (_| |                 |
#   |               |_____\___/ \__,_|\__,_|_|_| |_|\__, |                 |
#   |                                               |___/                  |
#   +----------------------------------------------------------------------+
#   | Loading of check plug-ins                                            |
#   '----------------------------------------------------------------------'


def load_all_pluginX(checks_dir: Path) -> AgentBasedPlugins:
    with tracer.span("load_legacy_check_plugins"):
        with tracer.span("discover_legacy_check_plugins"):
            filelist = find_plugin_files(checks_dir)

        legacy_errors, sections, checks = load_and_convert_legacy_checks(filelist)

    return agent_based_register.load_all_plugins(
        sections=sections,
        checks=checks,
        legacy_errors=legacy_errors,
        raise_errors=cmk.ccc.debug.enabled(),
    )


@tracer.instrument("load_and_convert_legacy_checks")
def load_and_convert_legacy_checks(
    filelist: Iterable[str],
) -> tuple[list[str], Sequence[SNMPSectionPlugin | AgentSectionPlugin], Sequence[CheckPlugin]]:
    discovered_legacy_checks = discover_legacy_checks(
        filelist,
        FileLoader(
            precomile_path=cmk.utils.paths.precompiled_checks_dir,
            makedirs=lambda path: Path(path).mkdir(mode=0o770, parents=True, exist_ok=True),
        ),
        raise_errors=cmk.ccc.debug.enabled(),
    )

    section_errors, sections = convert_legacy_sections(
        discovered_legacy_checks.sane_check_info,
        discovered_legacy_checks.plugin_files,
        raise_errors=cmk.ccc.debug.enabled(),
    )
    check_errors, checks = convert_legacy_check_plugins(
        discovered_legacy_checks.sane_check_info,
        discovered_legacy_checks.plugin_files,
        validate_creation_kwargs=discovered_legacy_checks.did_compile,
        raise_errors=cmk.ccc.debug.enabled(),
    )

    return (section_errors + check_errors, sections, checks)


# .
#   .--Helpers-------------------------------------------------------------.
#   |                  _   _      _                                        |
#   |                 | | | | ___| |_ __   ___ _ __ ___                    |
#   |                 | |_| |/ _ \ | '_ \ / _ \ '__/ __|                   |
#   |                 |  _  |  __/ | |_) |  __/ |  \__ \                   |
#   |                 |_| |_|\___|_| .__/ \___|_|  |___/                   |
#   |                              |_|                                     |
#   +----------------------------------------------------------------------+
#   | Misc check related helper functions                                  |
#   '----------------------------------------------------------------------'


def compute_enforced_service_parameters(
    plugins: Mapping[CheckPluginName, CheckPlugin],
    plugin_name: CheckPluginName,
    configured_parameters: TimespecificParameterSet,
) -> TimespecificParameters:
    """Compute effective check parameters for enforced services.

    Honoring (in order of precedence):
     * the configured parameters
     * the plugins defaults
    """
    defaults = (
        {}
        if (check_plugin := agent_based_register.get_check_plugin(plugin_name, plugins)) is None
        else check_plugin.check_default_parameters or {}
    )

    return TimespecificParameters(
        [configured_parameters, TimespecificParameterSet.from_parameters(defaults)]
    )


def _get_ssc_ip_family(
    ip_family: Literal[socket.AddressFamily.AF_INET, socket.AddressFamily.AF_INET6],
) -> server_side_calls_api.IPAddressFamily:
    match ip_family:
        case socket.AddressFamily.AF_INET:
            return server_side_calls_api.IPAddressFamily.IPV4
        case socket.AddressFamily.AF_INET6:
            return server_side_calls_api.IPAddressFamily.IPV6
        case other:
            assert_never(other)


# Should not be here, but can't be moved to cmk.base.core (yet) because of import cycles
def load_resource_cfg_macros(
    resource_cfg: Path, error_handler: Callable[[str], None] | None | None
) -> Mapping[str, str]:
    """Load user macros from resource.cfg

    Example for resource.cfg:

    ```
        ############################################
        # OMD settings, please use them to make your config
        # portable, but don't change them
        $USER1$=/omd/sites/prod/lib/nagios/plugins
        $USER2$=/omd/sites/prod/local/lib/nagios/plugins
        $USER3$=prod
        $USER4$=/omd/sites/prod
        ############################################
        # set your own macros here:
        $USER32$=wrdlpfrmpt
    ```
    """

    try:
        raw = resource_cfg.read_text()
    except FileNotFoundError:
        return {}

    try:
        return dict(
            stripped.split("=", 1)
            for line in raw.splitlines()
            if (stripped := line.strip()) and not stripped.startswith("#")
        )
    except ValueError as exc:
        if error_handler is None:
            raise
        error_handler(f"Cannot read {resource_cfg}: {exc}")
    return {}


def get_ssc_host_config(
    host_name: HostName,
    host_alias: str,
    host_primary_family: Literal[socket.AddressFamily.AF_INET, socket.AddressFamily.AF_INET6],
    host_ip_stack_config: IPStackConfig,
    host_additional_addresses_ipv4: Sequence[HostAddress],
    host_additional_addresses_ipv6: Sequence[HostAddress],
    macros: Mapping[str, object],
    ip_address_of: IPLookupOptional,
) -> server_side_calls_api.HostConfig:
    """Translates our internal config into the HostConfig exposed to and expected by server_side_calls plugins."""
    return server_side_calls_api.HostConfig(
        name=host_name,
        alias=host_alias,
        ipv4_config=(
            server_side_calls_api.IPv4Config(
                address=ip_address_of(host_name, socket.AddressFamily.AF_INET),
                additional_addresses=host_additional_addresses_ipv4,
            )
            if ip_lookup.IPStackConfig.IPv4 in host_ip_stack_config
            else None
        ),
        ipv6_config=(
            server_side_calls_api.IPv6Config(
                address=ip_address_of(host_name, socket.AddressFamily.AF_INET6),
                additional_addresses=host_additional_addresses_ipv6,
            )
            if ip_lookup.IPStackConfig.IPv6 in host_ip_stack_config
            else None
        ),
        primary_family=_get_ssc_ip_family(host_primary_family),
        macros={k: str(v) for k, v in macros.items()},
    )


# .
#   .--Configuration Cache-------------------------------------------------.
#   |    ____             __ _                       _   _                 |
#   |   / ___|___  _ __  / _(_) __ _ _   _ _ __ __ _| |_(_) ___  _ __      |
#   |  | |   / _ \| '_ \| |_| |/ _` | | | | '__/ _` | __| |/ _ \| '_ \     |
#   |  | |__| (_) | | | |  _| | (_| | |_| | | | (_| | |_| | (_) | | | |    |
#   |   \____\___/|_| |_|_| |_|\__, |\__,_|_|  \__,_|\__|_|\___/|_| |_|    |
#   |                          |___/                                       |
#   |                      ____           _                                |
#   |                     / ___|__ _  ___| |__   ___                       |
#   |                    | |   / _` |/ __| '_ \ / _ \                      |
#   |                    | |__| (_| | (__| | | |  __/                      |
#   |                     \____\__,_|\___|_| |_|\___|                      |
#   |                                                                      |
#   +----------------------------------------------------------------------+


def make_hosts_config(loaded_config: LoadedConfigFragment) -> Hosts:
    return Hosts(
        hosts=strip_tags(loaded_config.all_hosts),
        clusters=strip_tags(loaded_config.clusters),
        shadow_hosts=list(loaded_config.shadow_hosts),
    )


def _make_clusters_nodes_maps(
    clusters: Mapping[HostName, Sequence[HostName]],
) -> tuple[Mapping[HostName, Sequence[HostName]], Mapping[HostName, Sequence[HostName]]]:
    clusters_of_cache: dict[HostName, list[HostName]] = {}
    nodes_cache: dict[HostName, Sequence[HostName]] = {}
    for cluster, hosts in clusters.items():
        clustername = HostName(cluster.split("|", 1)[0])
        for name in hosts:
            clusters_of_cache.setdefault(name, []).append(clustername)
        nodes_cache[clustername] = [HostName(h) for h in hosts]
    return clusters_of_cache, nodes_cache


class AutochecksConfigurer:
    """Implementation of the autochecks configuration"""

    def __init__(
        self,
        config_cache: ConfigCache,
        check_plugins: Mapping[CheckPluginName, CheckPlugin],
        service_name_config: Callable[[HostName, ServiceID, str | None], ServiceName],
    ) -> None:
        self._config_cache = config_cache
        self.service_name_config: Final = service_name_config
        self._label_manager = config_cache.label_manager
        self._check_plugins = check_plugins

    def ignore_plugin(self, host_name: HostName, plugin_name: CheckPluginName) -> bool:
        return self._config_cache.check_plugin_ignored(host_name, plugin_name)

    def ignore_service(self, host_name: HostName, entry: AutocheckEntry) -> bool:
        service_name = self.service_description(host_name, entry)
        service_labels = self._label_manager.labels_of_service(
            host_name, service_name, entry.service_labels
        )
        return self._config_cache.service_ignored(host_name, service_name, service_labels)

    def effective_host(self, host_name: HostName, entry: AutocheckEntry) -> HostName:
        service_name = self.service_description(host_name, entry)
        service_labels = self._label_manager.labels_of_service(
            host_name, service_name, entry.service_labels
        )
        return self._config_cache.effective_host(host_name, service_name, service_labels)

    def service_description(self, host_name: HostName, entry: AutocheckEntry) -> ServiceName:
        return self.service_name_config(
            host_name,
            entry.id(),
            (
                None
                if (
                    p := agent_based_register.get_check_plugin(
                        entry.check_plugin_name, self._check_plugins
                    )
                )
                is None
                else p.service_name
            ),
        )

    def service_labels(self, host_name: HostName, entry: AutocheckEntry) -> Labels:
        return self._label_manager.labels_of_service(
            host_name,
            self.service_description(host_name, entry),
            entry.service_labels,
        )


class ConfigCache:
    def __init__(
        self,
        loaded_config: LoadedConfigFragment,
        get_builtin_host_labels: Callable[[SiteId], Labels],
    ) -> None:
        super().__init__()
        self._loaded_config: Final = loaded_config
        self.hosts_config = Hosts(hosts=(), clusters=(), shadow_hosts=())
        self.__enforced_services_table: dict[
            HostName,
            Mapping[
                ServiceID,
                tuple[RulesetName, ConfiguredService],
            ],
        ] = {}
        self.__is_piggyback_host: dict[HostName, bool] = {}
        self.__is_waiting_for_discovery_host: dict[HostName, bool] = {}
        self.__snmp_config: dict[tuple[HostName, HostAddress, SourceType], SNMPHostConfig] = {}
        self.__hwsw_inventory_parameters: dict[HostName, HWSWInventoryParameters] = {}
        self.__explicit_host_attributes: dict[HostName, dict[str, str]] = {}
        self.__computed_datasources: dict[HostName | HostAddress, ComputedDataSources] = {}
        self.__discovery_check_parameters: dict[HostName, DiscoveryCheckParameters] = {}
        self.__active_checks: dict[HostName, Sequence[SSCRules]] = {}
        self.__special_agents: dict[HostName, Sequence[SSCRules]] = {}
        self.__hostgroups: dict[HostName, Sequence[str]] = {}
        self.__contactgroups: dict[HostName, Sequence[_ContactgroupName]] = {}
        self.__explicit_check_command: dict[HostName, HostCheckCommand] = {}
        self.__snmp_fetch_interval: dict[HostName, Mapping[SectionName, int | None]] = {}
        self.__notification_plugin_parameters: dict[tuple[HostName, str], Mapping[str, object]] = {}
        self.__snmp_backend: dict[HostName, SNMPBackendEnum] = {}
        self.initialize(get_builtin_host_labels)

    def initialize(self, get_builtin_host_labels: Callable[[SiteId], Labels]) -> ConfigCache:
        self.invalidate_host_config()

        self._check_table_cache = cache_manager.obtain_cache("check_tables")
        self._cache_section_name_of: dict[str, str] = {}
        self._host_paths: dict[HostName, str] = ConfigCache._get_host_paths(host_paths)

        (
            self._clusters_of_cache,
            self._nodes_cache,
        ) = _make_clusters_nodes_maps(self._loaded_config.clusters)

        # TODO: remove this from the config cache. It is a completely
        # self-contained object that should be passed around (if it really
        # has to exist at all).
        self.autochecks_memoizer = AutochecksMemoizer()
        self._effective_host_cache: dict[
            tuple[HostName, ServiceName, tuple[tuple[str, str], ...]],
            HostName,
        ] = {}

        self.hosts_config = make_hosts_config(self._loaded_config)

        self.host_tags = cmk.utils.tags.HostTags.make(
            self._host_paths,
            self._loaded_config.tag_config,
            self._loaded_config.host_tags,
            [*self._loaded_config.all_hosts, *self._loaded_config.clusters],
            self._loaded_config.shadow_hosts,
        )

        self.ruleset_matcher = ruleset_matcher.RulesetMatcher(
            host_tags=self.host_tags.host_tags_maps,
            host_paths=self._host_paths,
            clusters_of=self._clusters_of_cache,
            nodes_of=self._nodes_cache,
            all_configured_hosts=frozenset(
                itertools.chain(
                    self.hosts_config.hosts,
                    self.hosts_config.clusters,
                    self.hosts_config.shadow_hosts,
                )
            ),
        )
        builtin_host_labels = {
            hostname: get_builtin_host_labels(self._site_of_host(hostname))
            for hostname in self.hosts_config
        }
        self.label_manager = LabelManager(
            LabelConfig(
                self.ruleset_matcher,
                host_label_rules,
                service_label_rules,
            ),
            self._nodes_cache,
            host_labels,
            builtin_host_labels=builtin_host_labels,
        )

        self.ruleset_matcher.ruleset_optimizer.set_all_processed_hosts(
            {
                hn
                for hn in set(self.hosts_config.hosts).union(self.hosts_config.clusters)
                if self.is_active(hn) and self.is_online(hn)
            }
        )
        self.check_interval = make_check_interval_config(
            self._loaded_config, self.ruleset_matcher, self.label_manager
        )
        self.check_period_of_passive_service = SingleServiceRulesetMatcherFirstParsed(
            self._loaded_config.check_periods,
            "24X7",
            self.ruleset_matcher,
            self.label_manager.labels_of_host,
            parser=str,
        )
        return self

    def make_passive_service_name_config(
        self,
        final_service_name_config: Callable[
            [HostName, ServiceName, Callable[[HostName], Labels]], ServiceName
        ],
    ) -> PassiveServiceNameConfig:
        return PassiveServiceNameConfig(
            final_service_name_config,
            user_defined_service_names=self._loaded_config.service_descriptions,
            use_new_names_for=self._loaded_config.use_new_descriptions_for,
            labels_of_host=self.label_manager.labels_of_host,
        )

    def make_service_configurer(
        self,
        check_plugins: Mapping[CheckPluginName, CheckPlugin],
        passive_service_name_config: Callable[[HostName, ServiceID, str | None], ServiceName],
    ) -> ServiceConfigurer:
        # This function is not part of the checkengine, because it still has
        # hidden dependencies to the loaded config in the global scope of this module.
        return ServiceConfigurer(
            CheckingConfig(
                self.ruleset_matcher,
                self.label_manager.labels_of_host,
                self._loaded_config.checkgroup_parameters,
                service_rule_groups,
            ),
            check_plugins,
            _make_service_description_cb(passive_service_name_config, check_plugins),
            self.effective_host,
            lambda host_name, service_name, discovered_labels: self.label_manager.labels_of_service(
                host_name, service_name, discovered_labels
            ),
        )

    def fetcher_factory(
        self,
        service_configurer: ServiceConfigurer,
        ip_lookup: ip_lookup.IPLookup,
        service_name_config: Callable[[HostName, ServiceID, str | None], ServiceName],
        enforced_services_table: Callable[
            [HostName], Mapping[ServiceID, tuple[object, ConfiguredService]]
        ],
        snmp_fetcher_config: SNMPFetcherConfig,
    ) -> FetcherFactory:
        return FetcherFactory(
            self,
            ip_lookup,
            make_tcp_fetcher_config(
                self._loaded_config, self.ruleset_matcher, self.label_manager.labels_of_host
            ),
            snmp_fetcher_config,
            self.ruleset_matcher,
            service_configurer,
            service_name_config,
            enforced_services_table,
            is_cmc=self._loaded_config.monitoring_core == "cmc",
        )

    def summary_config(self, host_name: HostName, source_id: str) -> SummaryConfig:
        return SummaryConfig(
            exit_spec=self.exit_code_spec(host_name, source_id),
            piggyback_config=piggyback_backend.Config(
                host_name,
                guess_piggybacked_hosts_time_settings(
                    self._loaded_config,
                    self.ruleset_matcher,
                    self.label_manager.labels_of_host,
                    piggybacked_hostname=host_name,
                ),
            ),
            expect_data=self.is_piggyback_host(host_name),
        )

    def make_parent_scan_config(self, host_name: HostName) -> ParentScanConfig:
        return ParentScanConfig(
            active=self.is_active(host_name),
            online=self.is_online(host_name),
            ip_stack_config=self.ip_stack_config(host_name),
            parents=self.parents(host_name),
        )

    def datasource_programs(self, host_name: HostName) -> Sequence[str]:
        return self.ruleset_matcher.get_host_values_all(
            host_name, datasource_programs, self.label_manager.labels_of_host
        )

    def ip_lookup_config(self) -> ip_lookup.IPLookupConfig:
        return ip_lookup.IPLookupConfig(
            ip_stack_config=self.ip_stack_config,
            is_snmp_host=lambda host_name: self.computed_datasources(host_name).is_snmp,
            is_snmp_management=lambda host_name: self.management_protocol(host_name) == "snmp",
            is_use_walk_host=lambda host_name: self.get_snmp_backend(host_name)
            is SNMPBackendEnum.STORED_WALK,
            default_address_family=self.default_address_family,
            management_address=self.management_address,
            is_dyndns_host=self.is_dyndns_host,
            simulation_mode=self._loaded_config.simulation_mode,
            fake_dns=None
            if self._loaded_config.fake_dns is None
            else HostAddress(self._loaded_config.fake_dns),
            use_dns_cache=self._loaded_config.use_dns_cache,
            ipv4_addresses=self._loaded_config.ipaddresses,
            ipv6_addresses=self._loaded_config.ipv6addresses,
        )

    def make_snmp_config(
        self,
        host_name: HostName,
        host_ip_family: Literal[socket.AddressFamily.AF_INET, socket.AddressFamily.AF_INET6],
        ip_address: HostAddress,
        source_type: SourceType,
        *,
        backend_override: SNMPBackendEnum | None,
    ) -> SNMPHostConfig:
        with contextlib.suppress(KeyError):
            return self.__snmp_config[(host_name, ip_address, source_type)]

        def _timeout_policy(
            policy: Literal["stop_on_timeout", "continue_on_timeout"],
        ) -> Literal["stop", "continue"]:
            match policy:
                case "stop_on_timeout":
                    return "stop"
                case "continue_on_timeout":
                    return "continue"
                case _:
                    assert_never(policy)

        def _snmp_version(v2_enabled: bool, credentials: SNMPCredentials) -> SNMPVersion:
            """Guess SNMP version from credentials :-("""
            if isinstance(credentials, tuple):
                return SNMPVersion.V3
            if v2_enabled:
                return SNMPVersion.V2C
            return SNMPVersion.V1

        credentials = (
            self._snmp_credentials(host_name)
            if source_type is SourceType.HOST
            else self.management_credentials(host_name, "snmp")
        )

        snmp_config = self.__snmp_config.setdefault(
            (host_name, ip_address, source_type),
            SNMPHostConfig(
                is_ipv6_primary=host_ip_family is socket.AF_INET6,
                hostname=host_name,
                ipaddress=ip_address,
                credentials=credentials,
                port=self._snmp_port(host_name),
                snmp_version=_snmp_version(
                    self.ruleset_matcher.get_host_bool_value(
                        host_name,
                        # This is the ruleset "Enable SNMPv2c",
                        # (Which enables SNMP version 2, implying the *possibility* to use bulkwalk.)
                        # Very poor naming of the variable.
                        (
                            bulkwalk_hosts
                            if source_type is SourceType.HOST
                            else management_bulkwalk_hosts
                        ),
                        self.label_manager.labels_of_host,
                    ),
                    credentials,
                ),
                bulkwalk_enabled=not self.ruleset_matcher.get_host_bool_value(
                    host_name,
                    # This is the ruleset "Disable bulk walks".
                    # Very poor naming of the variable.
                    snmpv2c_hosts,
                    self.label_manager.labels_of_host,
                ),
                bulk_walk_size_of=self._bulk_walk_size(host_name),
                timing=self._snmp_timing(host_name),
                oid_range_limits=parse_oid_range_config(
                    self.ruleset_matcher.get_host_values_all(
                        host_name, snmp_limit_oid_range, self.label_manager.labels_of_host
                    )
                ),
                snmpv3_contexts=[
                    SNMPContextConfig(
                        section=SNMPSectionName(name) if name is not None else None,
                        contexts=contexts,
                        timeout_policy=_timeout_policy(timeout_policy),
                    )
                    for name, contexts, timeout_policy in self.ruleset_matcher.get_host_values_all(
                        host_name, snmpv3_contexts, self.label_manager.labels_of_host
                    )
                ],
                character_encoding=self._snmp_character_encoding(host_name),
                snmp_backend=self.get_snmp_backend(host_name),
            ),
        )
        if backend_override:
            return dataclasses.replace(snmp_config, snmp_backend=backend_override)
        return snmp_config

    def make_checking_sections(
        self,
        plugins: AgentBasedPlugins,
        service_configurer: ServiceConfigurer,
        service_name_config: Callable[[HostName, ServiceID, str | None], ServiceName],
        hostname: HostName,
        enforced_services_table: Callable[
            [HostName], Mapping[ServiceID, tuple[object, ConfiguredService]]
        ],
        *,
        selected_sections: frozenset[SNMPSectionName] | NoSelectedSNMPSections,
    ) -> frozenset[SNMPSectionName]:
        if not isinstance(selected_sections, NoSelectedSNMPSections):
            return selected_sections

        checking_sections = frozenset(
            agent_based_register.filter_relevant_raw_sections(
                consumers=[
                    p
                    for n in self.check_table(
                        hostname,
                        plugins.check_plugins,
                        service_configurer,
                        service_name_config,
                        enforced_services_table,
                        filter_mode=FilterMode.INCLUDE_CLUSTERED,
                        skip_ignored=True,
                    ).needed_check_names()
                    if (p := agent_based_register.get_check_plugin(n, plugins.check_plugins))
                    is not None
                ],
                sections=itertools.chain(
                    plugins.agent_sections.values(), plugins.snmp_sections.values()
                ),
            )
        )
        return frozenset(
            SNMPSectionName(s) for s in checking_sections if SectionName(s) in plugins.snmp_sections
        )

    def invalidate_host_config(self) -> None:
        self.__enforced_services_table.clear()
        self.__is_piggyback_host.clear()
        self.__snmp_config.clear()
        self.__hwsw_inventory_parameters.clear()
        self.__explicit_host_attributes.clear()
        self.__computed_datasources.clear()
        self.__discovery_check_parameters.clear()
        self.__active_checks.clear()
        self.__special_agents.clear()
        self.__hostgroups.clear()
        self.__contactgroups.clear()
        self.__explicit_check_command.clear()
        self.__snmp_fetch_interval.clear()
        self.__notification_plugin_parameters.clear()
        self.__snmp_backend.clear()

    @staticmethod
    def _get_host_paths(config_host_paths: dict[HostName, str]) -> dict[HostName, str]:
        """Reference hostname -> dirname including /"""
        host_dirs = {}
        for hostname, filename in config_host_paths.items():
            dirname_of_host = os.path.dirname(filename)
            if dirname_of_host[-1] != "/":
                dirname_of_host += "/"
            host_dirs[hostname] = dirname_of_host
        return host_dirs

    def host_path(self, hostname: HostName) -> str:
        return self._host_paths.get(hostname, "/")

    def check_table(
        self,
        hostname: HostName,
        plugins: Mapping[CheckPluginName, CheckPlugin],
        service_configurer: ServiceConfigurer,
        service_name_config: Callable[[HostName, ServiceID, str | None], ServiceName],
        enforced_services_table: Callable[
            [HostName], Mapping[ServiceID, tuple[object, ConfiguredService]]
        ],
        *,
        filter_mode: FilterMode = FilterMode.NONE,
        # This was last set to `False` when computing the precompiled host
        # checks for nagios in Checkmk 2.4.
        # Let's keep this code around in the 2.5 branch in case changing that
        # was a mistake.
        skip_ignored: Literal[True] = True,
    ) -> HostCheckTable:
        # we blissfully ignore the plugins parameter here
        cache_key = (hostname, filter_mode, skip_ignored)
        with contextlib.suppress(KeyError):
            return self._check_table_cache[cache_key]

        host_check_table = HostCheckTable(
            services=_aggregate_check_table_services(
                hostname,
                config_cache=self,
                service_name_config=service_name_config,
                enforced_services_table=enforced_services_table,
                skip_ignored=skip_ignored,
                filter_mode=filter_mode,
                get_autochecks=self.autochecks_memoizer.read,
                configure_autochecks=service_configurer.configure_autochecks,
                plugins=plugins,
            )
        )

        self._check_table_cache[cache_key] = host_check_table

        return host_check_table

    def _sorted_services(
        self,
        hostname: HostName,
        plugins: Mapping[CheckPluginName, CheckPlugin],
        service_configurer: ServiceConfigurer,
        passive_service_name_config: Callable[[HostName, ServiceID, str | None], ServiceName],
        enforced_services_table: Callable[
            [HostName], Mapping[ServiceID, tuple[object, ConfiguredService]]
        ],
    ) -> Sequence[ConfiguredService]:
        # This method is only useful for the monkeypatching orgy of the "unit"-tests.
        return sorted(
            self.check_table(
                hostname,
                plugins,
                service_configurer,
                passive_service_name_config,
                enforced_services_table,
            ).values(),
            key=lambda service: service.description,
        )

    def configured_services(
        self,
        hostname: HostName,
        plugins: Mapping[CheckPluginName, CheckPlugin],
        service_configurer: ServiceConfigurer,
        passive_service_name_config: Callable[[HostName, ServiceID, str | None], ServiceName],
        enforced_services_table: Callable[
            [HostName], Mapping[ServiceID, tuple[object, ConfiguredService]]
        ],
        service_depends_on: Callable[[HostAddress, ServiceName], Sequence[ServiceName]],
    ) -> Sequence[ConfiguredService]:
        services = self._sorted_services(
            hostname,
            plugins,
            service_configurer,
            passive_service_name_config,
            enforced_services_table,
        )
        if self._loaded_config.monitoring_core == "cmc":
            return services

        unresolved = [(s, set(service_depends_on(hostname, s.description))) for s in services]

        resolved: list[ConfiguredService] = []
        while unresolved:
            resolved_descriptions = {service.description for service in resolved}
            newly_resolved = {
                service.id(): service
                for service, dependencies in unresolved
                if dependencies <= resolved_descriptions
            }
            if not newly_resolved:
                problems = ", ".join(
                    f"{s.description!r} ({s.check_plugin_name} / {s.item})" for s, _ in unresolved
                )
                raise MKGeneralException(
                    f"Cyclic service dependency of host {hostname}: {problems}"
                )

            unresolved = [(s, d) for s, d in unresolved if s.id() not in newly_resolved]
            resolved.extend(newly_resolved.values())

        return resolved

    def hwsw_inventory_parameters(self, host_name: HostName) -> HWSWInventoryParameters:
        def get_hwsw_inventory_parameters() -> HWSWInventoryParameters:
            if host_name in self.hosts_config.clusters:
                return HWSWInventoryParameters.from_raw({})

            # 'get_host_values' is already cached thus we can
            # use it after every check cycle.
            if not (
                entries := self.ruleset_matcher.get_host_values_all(
                    host_name, active_checks.get("cmk_inv") or (), self.label_manager.labels_of_host
                )
            ):
                return HWSWInventoryParameters.from_raw({})  # No matching rule -> disable

            # Convert legacy rules to current dict format (just like the valuespec)
            # we can only have None or a dict here, but mypy doesn't know that
            return HWSWInventoryParameters.from_raw(
                entries[0] if isinstance(entries[0], dict) else {}
            )

        with contextlib.suppress(KeyError):
            return self.__hwsw_inventory_parameters[host_name]

        return self.__hwsw_inventory_parameters.setdefault(
            host_name, get_hwsw_inventory_parameters()
        )

    def management_protocol(self, host_name: HostName) -> Literal["snmp", "ipmi"] | None:
        return management_protocol.get(host_name)

    def has_management_board(self, host_name: HostName) -> bool:
        return self.management_protocol(host_name) is not None

    def management_address(
        self,
        host_name: HostName,
        host_ip_family: Literal[socket.AddressFamily.AF_INET, socket.AddressFamily.AF_INET6],
    ) -> HostAddress | None:
        if mgmt_host_address := host_attributes.get(host_name, {}).get("management_address"):
            return mgmt_host_address

        if host_ip_family is socket.AF_INET6:
            return ipv6addresses.get(host_name)

        return ipaddresses.get(host_name)

    @overload
    def management_credentials(
        self, host_name: HostName, protocol: Literal["snmp"]
    ) -> SNMPCredentials: ...

    @overload
    def management_credentials(
        self, host_name: HostName, protocol: Literal["ipmi"]
    ) -> IPMICredentials: ...

    def management_credentials(
        self, host_name: HostName, protocol: Literal["snmp", "ipmi"]
    ) -> SNMPCredentials | IPMICredentials:
        # First try to use the explicit configuration of the host
        # (set directly for a host or via folder inheritance in WATO)
        with contextlib.suppress(KeyError):
            match protocol:
                case "snmp":
                    return management_snmp_credentials[host_name]
                case "ipmi":
                    return management_ipmi_credentials[host_name]
                case _:
                    assert_never(protocol)

        # If a rule matches, use the first rule for the management board protocol of the host
        rule_settings = self.ruleset_matcher.get_host_values_all(
            host_name, management_board_config, self.label_manager.labels_of_host
        )
        for rule_protocol, credentials in rule_settings:
            if rule_protocol == protocol:
                return credentials

        match protocol:
            case "snmp":
                return snmp_default_community
            case "ipmi":
                return {}
            case _:
                assert_never(protocol)

    def explicit_host_attributes(self, host_name: HostName) -> ObjectAttributes:
        def make_explicit_host_attributes() -> Iterator[tuple[str, str]]:
            for key, mapping in explicit_host_conf.items():
                with contextlib.suppress(KeyError):
                    yield key, mapping[host_name]

        with contextlib.suppress(KeyError):
            return self.__explicit_host_attributes[host_name]

        return self.__explicit_host_attributes.setdefault(
            host_name, dict(make_explicit_host_attributes())
        )

    def alias(self, host_name: HostName) -> str:
        # Alias by explicit matching
        if alias_ := self.explicit_host_attributes(host_name).get("alias"):
            return alias_

        # Alias by rule matching
        default: Sequence[RuleSpec[HostName]] = []
        aliases = self.ruleset_matcher.get_host_values_all(
            host_name, extra_host_conf.get("alias", default), self.label_manager.labels_of_host
        )

        # First rule match and Fallback alias
        return aliases[0] if aliases else host_name

    def parents(self, host_name: HostName) -> Sequence[HostName]:
        """Returns the parents of a host configured via ruleset "parents"

        Use only those parents which are defined and active in all_hosts"""
        parent_candidates = set()

        # Parent by explicit matching
        if explicit_parents := self.explicit_host_attributes(host_name).get("parents"):
            parent_candidates.update(explicit_parents.split(","))

        # Respect the ancient parents ruleset. This can not be configured via WATO and should be removed one day
        for parent_names in self.ruleset_matcher.get_host_values_all(
            host_name, parents, self.label_manager.labels_of_host
        ):
            parent_candidates.update(parent_names.split(","))

        return list(
            parent_candidates.intersection(
                hn for hn in self.hosts_config.hosts if self.is_active(hn) and self.is_online(hn)
            )
        )

    def agent_connection_mode(self, host_name: HostName) -> HostAgentConnectionMode:
        return connection_mode_from_host_config(self.explicit_host_attributes(host_name))

    def extra_host_attributes(self, host_name: HostName) -> ObjectAttributes:
        attrs: ObjectAttributes = {}
        attrs.update(self.explicit_host_attributes(host_name))

        for key, ruleset in extra_host_conf.items():
            if key in attrs:
                # An explicit value is already set
                values: Sequence[object] = [attrs[key]]
            else:
                values = self.ruleset_matcher.get_host_values_all(
                    host_name, ruleset, self.label_manager.labels_of_host
                )
                if not values:
                    continue

            if values[0] is not None:
                attrs[key] = values[0]

        # Convert _keys to uppercase. Affects explicit and rule based keys
        attrs = {key.upper() if key[0] == "_" else key: value for key, value in attrs.items()}
        return attrs

    def computed_datasources(self, host_name: HostName | HostAddress) -> ComputedDataSources:
        with contextlib.suppress(KeyError):
            return self.__computed_datasources[host_name]

        return self.__computed_datasources.setdefault(
            host_name, cmk.utils.tags.compute_datasources(self.host_tags.tags(host_name))
        )

    def is_piggyback_host(self, host_name: HostName) -> bool:
        def get_is_piggyback_host() -> bool:
            tag_groups: Final = self.host_tags.tags(host_name)
            if tag_groups[TagGroupID("piggyback")] == TagID("piggyback"):
                return True
            if tag_groups[TagGroupID("piggyback")] == TagID("no-piggyback"):
                return False

            # for clusters with an auto-piggyback tag check if nodes have piggyback data
            nodes = self.nodes(host_name)
            if nodes and host_name in self.hosts_config.clusters:
                return any(self._has_piggyback_data(node) for node in nodes)

            # Legacy automatic detection
            return self._has_piggyback_data(host_name)

        with contextlib.suppress(KeyError):
            return self.__is_piggyback_host[host_name]

        return self.__is_piggyback_host.setdefault(host_name, get_is_piggyback_host())

    def is_waiting_for_discovery_host(self, host_name: HostName) -> bool:
        with contextlib.suppress(KeyError):
            return self.__is_waiting_for_discovery_host[host_name]

        return self.__is_waiting_for_discovery_host.setdefault(
            host_name, ConfigCache._is_waiting_for_discovery(host_name)
        )

    def is_ping_host(self, host_name: HostName) -> bool:
        cds = self.computed_datasources(host_name)
        return not (
            cds.is_snmp
            or cds.is_tcp
            or self.is_piggyback_host(host_name)
            or self.has_management_board(host_name)
        )

    def is_tcp(self, host_name: HostName) -> bool:
        return self.computed_datasources(host_name).is_tcp

    def _is_only_host(self, host_name: HostName) -> bool:
        if only_hosts is None:
            return True
        return self.ruleset_matcher.get_host_bool_value(
            host_name, only_hosts, self.label_manager.labels_of_host
        )

    def is_offline(self, host_name: HostName) -> bool:
        # Returns True if host_name is associated with this site,
        # but has been removed by the "only_hosts" rule. Normally these
        # are the hosts which have the tag "offline".
        return not self.is_online(host_name)

    def is_online(self, host_name: HostName) -> bool:
        return self._is_only_host(host_name)

    def is_active(self, host_name: HostName) -> bool:
        """Return True if host is active, else False."""
        if distributed_wato_site is None:
            return True

        # hosts without a site: tag belong to all sites
        return self._site_of_host(host_name) == distributed_wato_site

    def is_dyndns_host(self, host_name: HostName | HostAddress) -> bool:
        return self.ruleset_matcher.get_host_bool_value(
            host_name, dyndns_hosts, self.label_manager.labels_of_host
        )

    def discovery_check_parameters(self, host_name: HostName) -> DiscoveryCheckParameters:
        """Compute the parameters for the discovery check for a host"""

        match self._loaded_config.inventory_check_interval:
            case int() | None as inv_interval:
                pass
            case other:
                raise TypeError(other)

        defaults = DiscoveryCheckParameters(
            commandline_only=inv_interval is None,
            check_interval=int(inv_interval or 0),
            severity_new_services=int(inventory_check_severity),
            severity_vanished_services=0,
            severity_new_host_labels=1,
            severity_changed_service_labels=0,
            severity_changed_service_params=0,
            # TODO: defaults are currently all over the place :-(
            rediscovery={},
        )

        def make_discovery_check_parameters() -> DiscoveryCheckParameters:
            if self.is_ping_host(host_name) or self.service_ignored(
                host_name, ConfigCache.service_discovery_name(), {}
            ):
                return dataclasses.replace(defaults, commandline_only=True)

            entries = self.ruleset_matcher.get_host_values_all(
                host_name, periodic_discovery, self.label_manager.labels_of_host
            )
            if not entries:
                return defaults

            if (entry := entries[0]) is None or not (
                check_interval := int(entry["check_interval"])
            ):
                return dataclasses.replace(defaults, commandline_only=True)

            return DiscoveryCheckParameters(
                commandline_only=False,
                check_interval=check_interval,
                severity_new_services=int(entry["severity_unmonitored"]),
                severity_vanished_services=int(entry["severity_vanished"]),
                # TODO: should be changed via Transform & update-action of the periodic discovery rule
                severity_changed_service_labels=int(
                    entry.get("severity_changed_service_labels", 0)
                ),
                severity_changed_service_params=int(
                    entry.get("severity_changed_service_params", 0)
                ),
                severity_new_host_labels=int(entry.get("severity_new_host_label", 1)),
                rediscovery=entry.get("inventory_rediscovery", {}),
            )

        with contextlib.suppress(KeyError):
            return self.__discovery_check_parameters[host_name]

        return self.__discovery_check_parameters.setdefault(
            host_name, make_discovery_check_parameters()
        )

    def inventory_parameters(
        self, host_name: HostName, plugin: InventoryPlugin
    ) -> Mapping[str, object]:
        if plugin.ruleset_name is None:
            raise ValueError(plugin)
        return {
            **plugin.defaults,
            **self.ruleset_matcher.get_host_values_merged(
                host_name,
                inv_parameters.get(str(plugin.ruleset_name), []),
                self.label_manager.labels_of_host,
            ),
        }

    def active_checks(self, host_name: HostName) -> Sequence[SSCRules]:
        """Returns active checks configured for this host

        These are configured using the active check formalization of WATO
        where the whole parameter set is configured using valuespecs.
        """

        def make_active_checks() -> Sequence[SSCRules]:
            configured_checks: list[SSCRules] = []
            for plugin_name, ruleset in sorted(active_checks.items()):
                # Skip Check_MK HW/SW Inventory for all ping hosts, even when the
                # user has enabled the inventory for ping only hosts
                if plugin_name == "cmk_inv" and self.is_ping_host(host_name):
                    continue

                entries = self.ruleset_matcher.get_host_values_all(
                    host_name, ruleset, self.label_manager.labels_of_host
                )
                if not entries:
                    continue

                configured_checks.append((plugin_name, entries))

            return configured_checks

        with contextlib.suppress(KeyError):
            return self.__active_checks[host_name]

        return self.__active_checks.setdefault(host_name, make_active_checks())

    def active_check_services(
        self,
        host_name: HostName,
        host_ip_stack_config: ip_lookup.IPStackConfig,
        host_ip_family: Literal[socket.AddressFamily.AF_INET, socket.AddressFamily.AF_INET6],
        host_attrs: ObjectAttributes,
        final_service_name_config: Callable[
            [HostName, ServiceName, Callable[[HostName], Labels]], ServiceName
        ],
        ip_address_of: IPLookupOptional,
        secrets_config: SecretsConfig,
        single_plugin: str | None = None,
        *,
        for_relay: bool,
    ) -> Iterator[ActiveServiceData]:
        plugin_configs = (
            self.active_checks(host_name)
            if single_plugin is None
            else [
                (single_plugin, plugin_params)
                for plugin_name, plugin_params in self.active_checks(host_name)
                if plugin_name == single_plugin
            ]
        )

        if not plugin_configs:
            return

        additional_addresses_ipv4, additional_addresses_ipv6 = self.additional_ipaddresses(
            host_name
        )
        host_macros = ConfigCache.get_host_macros_from_attributes(host_name, host_attrs)
        resource_macros = load_resource_cfg_macros(
            cmk.utils.paths.nagios_resource_cfg, None if cmk.ccc.debug.enabled() else lambda x: None
        )
        macros = {**host_macros, **resource_macros}
        active_check_config = ActiveCheck(
            load_active_checks(raise_errors=cmk.ccc.debug.enabled()),
            host_name,
            get_ssc_host_config(
                host_name,
                self.alias(host_name),
                host_ip_family,
                host_ip_stack_config,
                additional_addresses_ipv4,
                additional_addresses_ipv6,
                macros,
                ip_address_of,
            ),
            config_processing.GlobalProxiesWithLookup(
                global_proxies={
                    name: config_processing.BackendProxy.model_validate(raw["proxy_config"])
                    for name, raw in self._loaded_config.http_proxies.items()
                },
                password_lookup=make_configured_passwords_lookup(),
            ),
            {
                ident: config_processing.OAuth2Connection(**entry)
                for ident, entry in self._loaded_config.oauth2_connections.items()
            },
            lambda x: final_service_name_config(host_name, x, self.label_manager.labels_of_host),
            secrets_config,
            ExecutableFinder(
                cmk.utils.paths.local_nagios_plugins_dir,
                cmk.utils.paths.nagios_plugins_dir,
                prefix_map=(),  # no relay support yet.
            ),
            ip_lookup_failed=ip_lookup.is_fallback_ip(host_attrs["address"]),
            for_relay=for_relay,
        )

        for plugin_name, plugin_params in plugin_configs:
            try:
                yield from active_check_config.get_active_service_data(plugin_name, plugin_params)
            except Exception as e:
                if cmk.ccc.debug.enabled():
                    raise
                config_warnings.warn(
                    f"Config creation for active check {plugin_name} failed on {host_name}: {e}"
                )
                continue

    def custom_checks(self, host_name: HostName) -> Sequence[dict[Any, Any]]:
        """Return the free form configured custom checks without formalization"""
        return self.ruleset_matcher.get_host_values_all(
            host_name, custom_checks, self.label_manager.labels_of_host
        )

    def custom_check_preview_rows(self, host_name: HostName) -> Sequence[CheckPreviewEntry]:
        custom_checks_ = self.custom_checks(host_name)
        ignored_services = IgnoredActiveServices(self, host_name)

        def make_check_source(desc: str) -> str:
            return "ignored_custom" if desc in ignored_services else "custom"

        def make_output(desc: str) -> str:
            pretty = make_check_source(desc).rsplit("_", maxsplit=1)[-1].title()
            return f"WAITING - {pretty} check, cannot be done offline"

        return list(
            {
                entry["service_description"]: CheckPreviewEntry(
                    check_source=make_check_source(entry["service_description"]),
                    check_plugin_name="custom",
                    ruleset_name=None,
                    discovery_ruleset_name=None,
                    item=entry["service_description"],
                    new_discovered_parameters={},
                    old_discovered_parameters={},
                    effective_parameters={},
                    description=entry["service_description"],
                    state=None,
                    output=make_output(entry["service_description"]),
                    metrics=[],
                    old_labels={},
                    new_labels={},
                    found_on_nodes=[host_name],
                )
                for entry in custom_checks_
            }.values()
        )

    def special_agents(self, host_name: HostName) -> Sequence[SSCRules]:
        def special_agents_impl() -> Sequence[SSCRules]:
            matched: list[tuple[str, Sequence[Mapping[str, object]]]] = []
            for agentname, ruleset in sorted(special_agents.items()):
                params = self.ruleset_matcher.get_host_values_all(
                    host_name, ruleset, self.label_manager.labels_of_host
                )
                if params:
                    # we have match type first, so pick the first.
                    # However, nest it in a list to have a consistent return type
                    matched.append((agentname, [params[0]]))
            return matched

        with contextlib.suppress(KeyError):
            return self.__special_agents[host_name]

        return self.__special_agents.setdefault(host_name, special_agents_impl())

    def special_agent_command_lines(
        self,
        host_name: HostName,
        host_ip_family: Literal[socket.AddressFamily.AF_INET, socket.AddressFamily.AF_INET6],
        ip_address: HostAddress | None,
        secrets_config: SecretsConfig,
        ip_address_of: IPLookup,
        executable_finder: ExecutableFinderProtocol,
        for_relay: bool,
    ) -> Iterable[tuple[str, SpecialAgentCommandLine]]:
        if not (host_special_agents := self.special_agents(host_name)):
            return

        host_attrs = self.get_host_attributes(host_name, host_ip_family, ip_address_of)
        special_agent = SpecialAgent(
            load_special_agents(raise_errors=cmk.ccc.debug.enabled()),
            host_name,
            ip_address,
            get_ssc_host_config(
                host_name,
                self.alias(host_name),
                host_ip_family,
                self.ip_stack_config(host_name),
                *self.additional_ipaddresses(host_name),
                {
                    "<IP>": ip_address or "",
                    "<HOST>": host_name,
                    **self.get_host_macros_from_attributes(host_name, host_attrs),
                },
                ip_address_of,
            ),
            host_attrs,
            config_processing.GlobalProxiesWithLookup(
                global_proxies={
                    name: config_processing.BackendProxy.model_validate(raw["proxy_config"])
                    for name, raw in self._loaded_config.http_proxies.items()
                },
                password_lookup=make_configured_passwords_lookup(),
            ),
            {
                ident: config_processing.OAuth2Connection(**entry)
                for ident, entry in self._loaded_config.oauth2_connections.items()
            },
            secrets_config,
            executable_finder,
            for_relay=for_relay,
            relay_compatible_families=relay_compatible_plugin_families(cmk.utils.paths.local_root),
        )
        for agentname, params_seq in host_special_agents:
            for params in params_seq:
                try:
                    for agent_data in special_agent.iter_special_agent_commands(agentname, params):
                        yield agentname, agent_data
                except Exception as exc:
                    if cmk.ccc.debug.enabled():
                        raise
                    config_warnings.warn(
                        f"Config creation for special agent {agentname} failed on host '{host_name}': {exc}"
                    )

    def collect_passwords(self) -> Mapping[str, Secret[str]]:
        # consider making the hosts an argument. Sometimes we only need one.

        def _compose_filtered_ssc_rules(
            ssc_config: Iterable[tuple[str, Sequence[RuleSpec[Mapping[str, object]]]]],
        ) -> Sequence[tuple[str, Sequence[Mapping[str, object]]]]:
            """Get _all_ configured rulesets (not only the ones matching any host)"""
            return [(name, [r["value"] for r in ruleset]) for name, ruleset in ssc_config]

        global_proxies_with_lookup = config_processing.GlobalProxiesWithLookup(
            global_proxies={
                name: config_processing.BackendProxy.model_validate(raw["proxy_config"])
                for name, raw in self._loaded_config.http_proxies.items()
            },
            password_lookup=make_configured_passwords_lookup(),
        )
        return {
            **{
                k: Secret(s)
                for k, s in password_store.load(password_store.password_store_path()).items()
            },
            **extract_all_adhoc_secrets(
                rules_by_name=_compose_filtered_ssc_rules(active_checks.items()),
                global_proxies_with_lookup=global_proxies_with_lookup,
                oauth2_connections={
                    ident: config_processing.OAuth2Connection(**entry)
                    for ident, entry in oauth2_connections.items()
                },
            ),
            **extract_all_adhoc_secrets(
                rules_by_name=_compose_filtered_ssc_rules(special_agents.items()),
                global_proxies_with_lookup=global_proxies_with_lookup,
                oauth2_connections={
                    ident: config_processing.OAuth2Connection(**entry)
                    for ident, entry in oauth2_connections.items()
                },
            ),
        }

    def hostgroups(self, host_name: HostName) -> Sequence[str]:
        """Returns the list of hostgroups of this host

        If the host has no hostgroups it will be added to the default hostgroup
        (Nagios requires each host to be member of at least on group)."""

        def hostgroups_impl() -> Sequence[str]:
            groups = self.ruleset_matcher.get_host_values_all(
                host_name, host_groups, self.label_manager.labels_of_host
            )
            return groups or [default_host_group]

        with contextlib.suppress(KeyError):
            return self.__hostgroups[host_name]

        return self.__hostgroups.setdefault(host_name, hostgroups_impl())

    def contactgroups(self, host_name: HostName) -> Sequence[_ContactgroupName]:
        """Returns the list of contactgroups of this host"""

        def contactgroups_impl() -> Sequence[_ContactgroupName]:
            cgrs: list[_ContactgroupName] = []

            # host_contactgroups may take single values as well as lists as item value.
            #
            # The list entries are generated by the WATO hosts.mk files and only
            # the first one is meant to be used by a host. This logic, which is similar
            # to a dedicated "first match" ruleset realizes the inheritance in the folder
            # hiearchy for the "contactgroups" attribute.
            #
            # The single-contact-groups entries (not in a list) are configured by the group
            # ruleset and should all match because the ruleset is a match all ruleset.
            #
            # It would be clearer to have independent rulesets for this...
            folder_cgrs: list[RuleSpec[str]] = []
            for entry in self.ruleset_matcher.get_host_values_all(
                host_name, host_contactgroups, self.label_manager.labels_of_host
            ):
                if isinstance(entry, list):
                    folder_cgrs.append(entry)
                else:
                    cgrs.append(entry)

            # Use the match of the nearest folder, which is the first entry in the list
            if folder_cgrs:
                cgrs += folder_cgrs[0]

            if self._loaded_config.monitoring_core == "nagios" and enable_rulebased_notifications:
                cgrs.append("check-mk-notify")

            return list(set(cgrs))

        with contextlib.suppress(KeyError):
            return self.__contactgroups[host_name]

        return self.__contactgroups.setdefault(host_name, contactgroups_impl())

    def explicit_check_command(self, host_name: HostName) -> HostCheckCommand:
        def explicit_check_command_impl() -> HostCheckCommand:
            entries = self.ruleset_matcher.get_host_values_all(
                host_name, host_check_commands, self.label_manager.labels_of_host
            )
            if not entries:
                return None

            if entries[0] == "smart" and self._loaded_config.monitoring_core == "nagios":
                return "ping"  # avoid problems when switching back to nagios core

            return entries[0]

        with contextlib.suppress(KeyError):
            return self.__explicit_check_command[host_name]

        return self.__explicit_check_command.setdefault(host_name, explicit_check_command_impl())

    def host_check_command(
        self, host_name: HostName, default_host_check_command: HostCheckCommand
    ) -> HostCheckCommand:
        explicit_command = self.explicit_check_command(host_name)
        if explicit_command is not None:
            return explicit_command
        if self.ip_stack_config(host_name) is IPStackConfig.NO_IP:
            return "ok"
        return default_host_check_command

    def missing_sys_description(self, host_name: HostName) -> bool:
        return self.ruleset_matcher.get_host_bool_value(
            host_name, snmp_without_sys_descr, self.label_manager.labels_of_host
        )

    def snmp_fetch_intervals(self, host_name: HostName) -> Mapping[SectionName, int | None]:
        """Return the configured fetch intervals of SNMP sections in seconds

        This has been added to reduce the fetch interval of single SNMP sections
        to be executed less frequently than the "Check_MK" service is executed.
        """

        def snmp_fetch_interval_impl() -> Mapping[SectionName, int | None]:
            return {
                SectionName(section_name): None if seconds is None else round(seconds)
                for sections, (_option_id, seconds) in reversed(  # use first match
                    self.ruleset_matcher.get_host_values_all(
                        host_name, snmp_check_interval, self.label_manager.labels_of_host
                    )
                )
                for section_name in sections
            }

        with contextlib.suppress(KeyError):
            return self.__snmp_fetch_interval[host_name]

        return self.__snmp_fetch_interval.setdefault(host_name, snmp_fetch_interval_impl())

    def checkmk_check_parameters(self, host_name: HostName) -> CheckmkCheckParameters:
        return CheckmkCheckParameters(enabled=not self.is_ping_host(host_name))

    @staticmethod
    def notification_logging_level() -> int:
        # The former values 1 and 2 are mapped to the values 20 (default) and 10 (debug)
        # which agree with the values used in cmk/utils/log.py.
        # The deprecated value 0 is transformed to the default logging value.
        if notification_logging in (0, 1):
            return 20
        if notification_logging == 2:
            return 10
        return notification_logging

    @staticmethod
    def notification_spooling() -> Literal["local", "remote", "both", "off"]:
        if notification_spool_to:
            if notification_spool_to[2]:
                return "both"
            return "remote"
        if notification_spooling and isinstance(notification_spooling, str):
            return notification_spooling
        return "remote"

    def notification_plugin_parameters(
        self,
        host_name: HostName,
        plugin_name: str,
    ) -> Mapping[str, object]:
        def _impl() -> Mapping[str, object]:
            default: Sequence[RuleSpec[Mapping[str, object]]] = []
            return self.ruleset_matcher.get_host_values_merged(
                host_name,
                notification_parameters.get(plugin_name, default),
                self.label_manager.labels_of_host,
            )

        with contextlib.suppress(KeyError):
            return self.__notification_plugin_parameters[(host_name, plugin_name)]

        return self.__notification_plugin_parameters.setdefault((host_name, plugin_name), _impl())

    def max_cachefile_age(self, hostname: HostName) -> MaxAge:
        check_interval = self.check_mk_check_interval(hostname)
        return MaxAge(
            checking=(
                cluster_max_cachefile_age
                if hostname in self.hosts_config.clusters
                else check_max_cachefile_age
            ),
            discovery=1.5 * check_interval,
            inventory=1.5 * check_interval,
        )

    def exit_code_spec(self, hostname: HostName, data_source_id: str | None = None) -> ExitSpec:
        spec: _NestedExitSpec = {}
        # TODO: Can we use get_host_merged_dict?
        specs = self.ruleset_matcher.get_host_values_all(
            hostname, check_mk_exit_status, self.label_manager.labels_of_host
        )
        for entry in specs[::-1]:
            spec.update(entry)

        merged_spec = ConfigCache._extract_data_source_exit_code_spec(spec, data_source_id)
        return ConfigCache._merge_with_optional_exit_code_parameters(spec, merged_spec)

    @staticmethod
    def _extract_data_source_exit_code_spec(
        spec: _NestedExitSpec,
        data_source_id: str | None,
    ) -> ExitSpec:
        if data_source_id is not None:
            with contextlib.suppress(KeyError):
                return spec["individual"][data_source_id]
        with contextlib.suppress(KeyError):
            return spec["overall"]
        # Old configuration format
        return spec

    @staticmethod
    def _merge_with_optional_exit_code_parameters(
        spec: _NestedExitSpec,
        merged_spec: ExitSpec,
    ) -> ExitSpec:
        # Additional optional parameters which are not part of individual
        # or overall parameters
        if (value := spec.get("restricted_address_mismatch")) is not None:
            merged_spec["restricted_address_mismatch"] = value
        if (value := spec.get("legacy_pull_mode")) is not None:
            merged_spec["legacy_pull_mode"] = value
        return merged_spec

    def inv_retention_intervals(self, hostname: HostName) -> Sequence[RawIntervalFromConfig]:
        return [
            raw
            for entry in self.ruleset_matcher.get_host_values_all(
                hostname, inv_retention_intervals, self.label_manager.labels_of_host
            )
            for raw in entry
        ]

    def service_level(self, hostname: HostName) -> int | None:
        entries = self.ruleset_matcher.get_host_values_all(
            hostname, extra_host_conf.get("_ec_sl", []), self.label_manager.labels_of_host
        )
        return entries[0] if entries else None

    def effective_service_level(
        self,
        host_name: HostName,
        service_name: ServiceName,
        service_labels: Labels,
    ) -> int:
        """Get the service level that applies to the current service."""
        service_level = self.service_level_of_service(host_name, service_name, service_labels)
        if service_level is not None:
            return service_level

        return self.service_level(host_name) or 0

    def _snmp_credentials(self, host_name: HostAddress) -> SNMPCredentials:
        """Determine SNMP credentials for a specific host

        It the host is found int the map snmp_communities, that community is
        returned. Otherwise the snmp_default_community is returned (wich is
        preset with "public", but can be overridden in main.mk.
        """
        with contextlib.suppress(KeyError):
            return explicit_snmp_communities[host_name]
        if communities := self.ruleset_matcher.get_host_values_all(
            host_name, snmp_communities, self.label_manager.labels_of_host
        ):
            return communities[0]

        # nothing configured for this host -> use default
        return snmp_default_community

    def _is_host_snmp_v1(self, host_name: HostName | HostAddress) -> bool:
        """Determines is host snmp-v1 using a bit Heuristic algorithm"""
        if isinstance(self._snmp_credentials(host_name), tuple):
            return False  # v3

        if self.ruleset_matcher.get_host_bool_value(
            host_name, bulkwalk_hosts, self.label_manager.labels_of_host
        ):
            return False

        return not self.ruleset_matcher.get_host_bool_value(
            host_name, snmpv2c_hosts, self.label_manager.labels_of_host
        )

    @staticmethod
    def _is_inline_backend_supported() -> bool:
        return (
            "netsnmp" in sys.modules
            and cmk_version.edition(cmk.utils.paths.omd_root) is not cmk_version.Edition.COMMUNITY
        )

    def get_snmp_backend(self, host_name: HostName | HostAddress) -> SNMPBackendEnum:
        if result := self.__snmp_backend.get(host_name):
            return result

        computed_backend = self._get_snmp_backend(host_name)
        self.__snmp_backend[host_name] = computed_backend
        return computed_backend

    def _get_snmp_backend(self, host_name: HostName | HostAddress) -> SNMPBackendEnum:
        if self.ruleset_matcher.get_host_bool_value(
            host_name, usewalk_hosts, self.label_manager.labels_of_host
        ):
            return SNMPBackendEnum.STORED_WALK

        with_inline_snmp = ConfigCache._is_inline_backend_supported()

        if host_backend_config := self.ruleset_matcher.get_host_values_all(
            host_name, snmp_backend_hosts, self.label_manager.labels_of_host
        ):
            # If more backends are configured for this host take the first one
            host_backend = host_backend_config[0]
            if with_inline_snmp and host_backend == "inline":
                return SNMPBackendEnum.INLINE
            if host_backend == "classic":
                return SNMPBackendEnum.CLASSIC
            raise MKGeneralException(f"Bad Host SNMP Backend configuration: {host_backend}")

        if with_inline_snmp and snmp_backend_default == "inline":
            return SNMPBackendEnum.INLINE
        if snmp_backend_default == "classic":
            return SNMPBackendEnum.CLASSIC
        # Note: in the above case we raise here.
        # I am not sure if this different behavior is intentional.
        return SNMPBackendEnum.CLASSIC

    def snmp_credentials_of_version(
        self, hostname: HostName, snmp_version: int
    ) -> SNMPCredentials | None:
        for entry in self.ruleset_matcher.get_host_values_all(
            hostname, snmp_communities, self.label_manager.labels_of_host
        ):
            if snmp_version == 3 and not isinstance(entry, tuple):
                continue

            if snmp_version != 3 and isinstance(entry, tuple):
                continue

            return entry

        return None

    def _snmp_port(self, hostname: HostName) -> int:
        ports = self.ruleset_matcher.get_host_values_all(
            hostname, snmp_ports, self.label_manager.labels_of_host
        )
        return ports[0] if ports else 161

    def _snmp_timing(self, hostname: HostName) -> SNMPTiming:
        timing = self.ruleset_matcher.get_host_values_all(
            hostname, snmp_timing, self.label_manager.labels_of_host
        )
        return timing[0] if timing else {}

    def _bulk_walk_size(self, hostname: HostName) -> int:
        bulk_sizes = self.ruleset_matcher.get_host_values_all(
            hostname, snmp_bulk_size, self.label_manager.labels_of_host
        )
        return bulk_sizes[0] if bulk_sizes else 10

    def _snmp_character_encoding(self, hostname: HostName) -> str | None:
        entries = self.ruleset_matcher.get_host_values_all(
            hostname, snmp_character_encodings, self.label_manager.labels_of_host
        )
        return entries[0] if entries else None

    @staticmethod
    def additional_ipaddresses(hostname: HostName) -> tuple[list[HostAddress], list[HostAddress]]:
        # TODO Regarding the following configuration variables from WATO
        # there's no inheritance, thus we use 'host_attributes'.
        # Better would be to use cmk.base configuration variables,
        # eg. like 'management_protocol'.
        return (
            host_attributes.get(hostname, {}).get("additional_ipv4addresses", []),
            host_attributes.get(hostname, {}).get("additional_ipv6addresses", []),
        )

    @staticmethod
    def _is_waiting_for_discovery(hostname: HostName) -> bool:
        """Check custom attribute set by WATO to signal
        the host may be not discovered and should be ignore"""
        return host_attributes.get(hostname, {}).get("waiting_for_discovery", False)

    def check_mk_check_interval(self, host_name: HostName) -> float:
        return self.check_interval(host_name, "Check_MK")

    def ip_stack_config(self, host_name: HostName | HostAddress) -> IPStackConfig:
        # TODO(ml): [IPv6] clarify tag_groups vs tag_groups["address_family"]
        tag_groups = self.host_tags.tags(host_name)
        if (
            TagGroupID("no-ip") in tag_groups
            or TagID("no-ip") == tag_groups[TagGroupID("address_family")]
        ):
            return IPStackConfig.NO_IP
        if (
            TagGroupID("ip-v4v6") in tag_groups
            or TagID("ip-v4v6") == tag_groups[TagGroupID("address_family")]
        ):
            return IPStackConfig.DUAL_STACK
        if (
            TagGroupID("ip-v6") in tag_groups
            or TagID("ip-v6") == tag_groups[TagGroupID("address_family")]
        ) and (
            TagGroupID("ip-v4") in tag_groups
            or TagID("ip-v4") == tag_groups[TagGroupID("address_family")]
        ):
            return IPStackConfig.DUAL_STACK
        if (
            TagGroupID("ip-v6") in tag_groups
            or TagGroupID("ip-v6-only") in tag_groups
            or tag_groups[TagGroupID("address_family")] in {TagID("ip-v6"), TagID("ip-v6-only")}
        ):
            return IPStackConfig.IPv6
        return IPStackConfig.IPv4

    def default_address_family(
        self, hostname: HostName | HostAddress
    ) -> Literal[socket.AddressFamily.AF_INET, socket.AddressFamily.AF_INET6]:
        def primary_ip_address_family_of() -> socket.AddressFamily:
            rules = self.ruleset_matcher.get_host_values_all(
                hostname, primary_address_family, self.label_manager.labels_of_host
            )
            return (
                socket.AddressFamily.AF_INET6
                if rules and rules[0] == "ipv6"
                else socket.AddressFamily.AF_INET
            )

        def is_ipv6_primary() -> bool:
            # Whether or not the given host is configured to be monitored primarily via IPv6
            return self.ip_stack_config(hostname) is IPStackConfig.IPv6 or (
                self.ip_stack_config(hostname) is IPStackConfig.DUAL_STACK
                and primary_ip_address_family_of() is socket.AF_INET6
            )

        return socket.AddressFamily.AF_INET6 if is_ipv6_primary() else socket.AddressFamily.AF_INET

    def _has_piggyback_data(self, host_name: HostName) -> bool:
        return (
            self._host_has_piggyback_data_right_now(host_name)
            or make_persisted_section_dir(
                host_name=host_name,
                ident="piggyback",
                section_cache_path=cmk.utils.paths.var_dir,
            ).exists()
            # ^- Will this ever be removed? If not, everything we do in _host_has_piggyback_data_right_now is pointless,
            # and it might as well just return `bool(piggyback_backend.get_messages_for(...))`
        )

    def _host_has_piggyback_data_right_now(self, piggybacked_host_name: HostAddress) -> bool:
        # NOTE: This is a best effort guess on whether we should create the piggyback datasource.
        # Users can still configure it to be absent or present manually.
        # In case of false positives (DS created but no data) the dasource will be OK anyway.

        # This duplicates logic and should be kept in sync with what the parser does.
        # Can we somehow instanciate the hypothetical parser here, and just let it parse?
        piggy_config = piggyback_backend.Config(
            piggybacked_host_name,
            make_piggyback_time_settings(
                self._loaded_config,
                self.ruleset_matcher,
                self.label_manager.labels_of_host,
                source_host_names=[piggybacked_host_name],  # I don't think this is right.
            ),
        )

        now = time.time()

        def _is_usable(data: piggyback_backend.PiggybackMessage) -> bool:
            return (now - data.meta.last_update) <= piggy_config.max_cache_age(data.meta.source)

        return any(
            map(
                _is_usable,
                piggyback_backend.get_messages_for(piggybacked_host_name, cmk.utils.paths.omd_root),
            )
        )

    def tags_of_service(
        self, host_name: HostName, service_name: ServiceName, service_labels: Labels
    ) -> Mapping[TagGroupID, TagID]:
        """Returns the dict of all configured tags of a service
        It takes all explicitly configured tag groups into account.
        """
        return {
            TagGroupID(k): TagID(v)
            for entry in self.ruleset_matcher.get_service_values_all(
                host_name,
                service_name,
                service_labels,
                service_tag_rules,
                self.label_manager.labels_of_host,
            )
            for k, v in entry
        }

    def extra_attributes_of_service(
        self, host_name: HostName, service_name: ServiceName, service_labels: Labels
    ) -> dict[str, Any]:
        attrs = dict[str, object](
            check_interval=self.check_interval(host_name, service_name) / 60.0,
        )
        for key, ruleset in self._loaded_config.extra_service_conf.items():
            if key == "check_interval":
                continue  # already handled above

            values = self.ruleset_matcher.get_service_values_all(
                host_name, service_name, service_labels, ruleset, self.label_manager.labels_of_host
            )
            if not values:
                continue

            value = values[0]
            if value is None:
                continue

            if key[0] == "_":
                key = key.upper()

            attrs[key] = value

        return attrs

    def icons_and_actions_of_service(
        self,
        host_name: HostName,
        service_name: ServiceName,
        service_labels: Labels,
    ) -> list[str]:
        return list(
            set(
                self.ruleset_matcher.get_service_values_all(
                    host_name,
                    service_name,
                    service_labels,
                    service_icons_and_actions,
                    self.label_manager.labels_of_host,
                )
            )
        )

    def servicegroups_of_service(
        self, host_name: HostName, service_name: ServiceName, service_labels: Labels
    ) -> list[ServicegroupName]:
        """Returns the list of servicegroups of this service"""
        return self.ruleset_matcher.get_service_values_all(
            host_name,
            service_name,
            service_labels,
            service_groups,
            self.label_manager.labels_of_host,
        )

    def contactgroups_of_service(
        self,
        host_name: HostName,
        service_name: ServiceName,
        service_labels: Labels,
    ) -> list[str]:
        """Returns the list of contactgroups of this service"""
        cgrs: set[str] = set()

        # service_contactgroups may take single values as well as lists as item value.
        # This ruleset works like host_contactgroups since 2.0.0p9.
        #
        # The list entries are generated by the WATO hosts.mk files and only
        # the first one is meant to be used by a host. This logic, which is similar
        # to a dedicated "first match" ruleset realizes the inheritance in the folder
        # hiearchy for the "contactgroups" attribute.
        #
        # The single-contact-groups entries (not in a list) are configured by the group
        # ruleset and should all match because the ruleset is a match all ruleset.
        #
        # It would be clearer to have independent rulesets for this...
        folder_cgrs: list[list[str]] = []
        for entry in self.ruleset_matcher.get_service_values_all(
            host_name,
            service_name,
            service_labels,
            service_contactgroups,
            self.label_manager.labels_of_host,
        ):
            if isinstance(entry, list):
                folder_cgrs.append(entry)
            else:
                cgrs.add(entry)

        # Use the match of the nearest folder, which is the first entry in the list
        if folder_cgrs:
            cgrs.update(folder_cgrs[0])

        if self._loaded_config.monitoring_core == "nagios":
            cgrs.add("check-mk-notify")

        return list(cgrs)

    def custom_attributes_of_service(
        self, host_name: HostName, service_name: ServiceName, service_labels: Labels
    ) -> dict[str, str]:
        return dict(
            itertools.chain(
                *self.ruleset_matcher.get_service_values_all(
                    host_name,
                    service_name,
                    service_labels,
                    custom_service_attributes,
                    self.label_manager.labels_of_host,
                )
            )
        )

    def service_level_of_service(
        self, host_name: HostName, service_name: ServiceName, service_labels: Labels
    ) -> int | None:
        out = self.ruleset_matcher.get_service_values_all(
            host_name,
            service_name,
            service_labels,
            extra_service_conf.get("_ec_sl", []),
            self.label_manager.labels_of_host,
        )
        return _parse(out[0], int) if out else None

    @staticmethod
    def get_explicit_service_custom_variables(
        hostname: HostName, description: ServiceName
    ) -> dict[str, str]:
        try:
            return explicit_service_custom_variables[(hostname, description)]
        except KeyError:
            return {}

    def section_name_of(self, section: str) -> str:
        try:
            return self._cache_section_name_of[section]
        except KeyError:
            section_name = section_name_of(section)
            self._cache_section_name_of[section] = section_name
            return section_name

    @staticmethod
    def _get_tag_attributes(
        collection: Mapping[TagGroupID, TagID] | Labels | LabelSources,
        prefix: str,
    ) -> ObjectAttributes:
        return {f"__{prefix}_{k}": str(v) for k, v in collection.items()}

    def get_host_attributes(
        self,
        hostname: HostName,
        host_ip_family: Literal[socket.AddressFamily.AF_INET, socket.AddressFamily.AF_INET6],
        ip_address_of: IPLookupOptional,
    ) -> ObjectAttributes:
        attrs = self.extra_host_attributes(hostname)

        # Pre 1.6 legacy attribute. We have changed our whole code to use the
        # livestatus column "tags" which is populated by all attributes starting with
        # "__TAG_" instead. We may deprecate this is one day.
        attrs["_TAGS"] = " ".join(sorted(self.host_tags.tag_list(hostname)))
        attrs.update(ConfigCache._get_tag_attributes(self.host_tags.tags(hostname), "TAG"))
        attrs.update(
            ConfigCache._get_tag_attributes(self.label_manager.labels_of_host(hostname), "LABEL")
        )
        attrs.update(
            ConfigCache._get_tag_attributes(
                self.label_manager.label_sources_of_host(hostname), "LABELSOURCE"
            )
        )

        if "alias" not in attrs:
            attrs["alias"] = self.alias(hostname)

        ip_stack_config = self.ip_stack_config(hostname)

        v4address = (
            ip_address_of(hostname, socket.AddressFamily.AF_INET)
            if IPStackConfig.IPv4 in ip_stack_config
            else None
        )
        attrs["_ADDRESS_4"] = "" if v4address is None else v4address

        v6address = (
            ip_address_of(hostname, socket.AddressFamily.AF_INET6)
            if IPStackConfig.IPv6 in ip_stack_config
            else None
        )
        attrs["_ADDRESS_6"] = "" if v6address is None else v6address

        ipv6_is_default = host_ip_family is socket.AF_INET6
        attrs["address"] = attrs["_ADDRESS_6"] if ipv6_is_default else attrs["_ADDRESS_4"]
        attrs["_ADDRESS_FAMILY"] = "6" if ipv6_is_default else "4"

        add_ipv4addrs, add_ipv6addrs = self.additional_ipaddresses(hostname)

        attrs["_ADDRESSES_4"] = " ".join(add_ipv4addrs)
        for n, address in enumerate(add_ipv4addrs, start=1):
            attrs[f"_ADDRESSES_4_{n}"] = address

        attrs["_ADDRESSES_6"] = " ".join(add_ipv6addrs)
        for n, address in enumerate(add_ipv6addrs, start=1):
            attrs[f"_ADDRESSES_6_{n}"] = address

        if path := host_paths.get(hostname):
            attrs["_FILENAME"] = path

        if actions := self.icons_and_actions(hostname):
            attrs["_ACTIONS"] = ",".join(actions)

        if cmk_version.edition(cmk.utils.paths.omd_root) is cmk_version.Edition.ULTIMATEMT:
            attrs["_CUSTOMER"] = current_customer  # type: ignore[name-defined,unused-ignore]

        return attrs

    def get_cluster_attributes(
        self,
        hostname: HostName,
        host_ip_family: Literal[socket.AddressFamily.AF_INET, socket.AddressFamily.AF_INET6],
        nodes: Sequence[HostName],
        ip_address_of: IPLookup,
    ) -> dict:
        sorted_nodes = sorted(nodes)

        attrs = {
            "_NODENAMES": " ".join(sorted_nodes),
        }
        ip_stack_config = self.ip_stack_config(hostname)
        node_ips_4 = []
        if IPStackConfig.IPv4 in ip_stack_config:
            family: Literal[socket.AddressFamily.AF_INET, socket.AddressFamily.AF_INET6] = (
                socket.AddressFamily.AF_INET
            )
            for h in sorted_nodes:
                addr = ip_address_of(h, family)
                if addr is not None:
                    node_ips_4.append(addr)
                else:
                    node_ips_4.append(ip_lookup.fallback_ip_for(family))

        node_ips_6 = []
        if IPStackConfig.IPv6 in ip_stack_config:
            family = socket.AddressFamily.AF_INET6
            for h in sorted_nodes:
                addr = ip_address_of(h, family)
                if addr is not None:
                    node_ips_6.append(addr)
                else:
                    node_ips_6.append(ip_lookup.fallback_ip_for(family))

        node_ips = node_ips_6 if host_ip_family is socket.AF_INET6 else node_ips_4

        for suffix, val in [("", node_ips), ("_4", node_ips_4), ("_6", node_ips_6)]:
            attrs[f"_NODEIPS{suffix}"] = " ".join(val)

        return attrs

    @staticmethod
    def get_host_macros_from_attributes(
        hostname: HostName, attrs: ObjectAttributes
    ) -> ObjectMacros:
        macros = {
            "$HOSTNAME$": hostname,
            "$HOSTADDRESS$": attrs["address"],
            "$HOSTALIAS$": attrs["alias"],
        }

        # Add custom macros
        for macro_name, value in attrs.items():
            if macro_name[0] == "_":
                macros[f"$HOST{macro_name}$"] = value
                # Be compatible to nagios making $_HOST<VARNAME>$ out of the config _<VARNAME> configs
                macros[f"$_HOST{macro_name[1:]}$"] = value

        return macros

    @staticmethod
    def get_service_macros_from_attributes(attrs: ObjectAttributes) -> ObjectMacros:
        # We may want to implement a superset of Nagios' own macros, see
        # https://assets.nagios.com/downloads/nagioscore/docs/nagioscore/3/en/macrolist.html
        return {
            f"$_SERVICE{macro_name[1:]}$": value
            for macro_name, value in attrs.items()
            if macro_name[0] == "_"
        }

    @staticmethod
    def replace_macros(s: str, macros: ObjectMacros) -> str:
        for key, value in macros.items():
            if isinstance(value, numbers.Integral | float):
                value = str(value)  # e.g. in _EC_SL (service level)

            # TODO: Clean this up
            try:
                s = s.replace(key, value)
            except Exception:  # Might have failed due to binary UTF-8 encoding in value
                try:
                    s = s.replace(key, value.decode("utf-8"))
                except Exception:
                    # If this does not help, do not replace
                    if cmk.ccc.debug.enabled():
                        raise

        return s

    def translate_fetcher_commandline(
        self,
        host_name: HostName,
        host_ip_family: Literal[socket.AddressFamily.AF_INET, socket.AddressFamily.AF_INET6],
        ip_address: HostAddress | None,
        template: str,
        ip_address_of: IPLookup,
    ) -> str:
        def _translate_host_macros(cmd: str) -> str:
            attrs = self.get_host_attributes(host_name, host_ip_family, ip_address_of)
            macros = ConfigCache.get_host_macros_from_attributes(host_name, attrs)
            return ConfigCache.replace_macros(cmd, macros)

        def _translate_legacy_macros(cmd: str) -> str:
            # Make "legacy" translation. The users should use the $...$ macros in future
            return replace_macros_in_str(
                cmd,
                {
                    "<IP>": ip_address or "",
                    "<HOST>": host_name,
                },
            )

        return _translate_host_macros(_translate_legacy_macros(template))

    def service_ignored(
        self, host_name: HostName, service_name: ServiceName, service_labels: Labels
    ) -> bool:
        return self.ruleset_matcher.get_service_bool_value(
            host_name,
            service_name,
            service_labels,
            ignored_services,
            self.label_manager.labels_of_host,
        )

    def check_plugin_ignored(
        self,
        host_name: HostName,
        check_plugin_name: CheckPluginName,
    ) -> bool:
        def _checktype_ignored_for_host(check_plugin_name_str: str) -> bool:
            ignored = self.ruleset_matcher.get_host_values_all(
                host_name, ignored_checks, self.label_manager.labels_of_host
            )
            for e in ignored:
                if check_plugin_name_str in e:
                    return True
            return False

        check_plugin_name_str = str(check_plugin_name)

        return _checktype_ignored_for_host(check_plugin_name_str)

    def get_cluster_cache_info(self) -> ClusterCacheInfo:
        return ClusterCacheInfo(clusters_of=self._clusters_of_cache, nodes_of=self._nodes_cache)

    def clusters_of(self, hostname: HostName) -> Sequence[HostName]:
        """Returns names of cluster hosts the host is a node of"""
        return self._clusters_of_cache.get(hostname, ())

    def nodes(self, hostname: HostName) -> Sequence[HostName]:
        """Returns the nodes of a cluster. Returns () if no match."""
        return self._nodes_cache.get(hostname, ())

    def effective_host(
        self,
        host_name: HostName,
        service_name: ServiceName,
        service_labels: Labels,
    ) -> HostName:
        """Compute the effective host (node or cluster) of a service

        This is the host where the service is shown at, and the one that triggers the checking.

        Determine whether a service (found on the given node) is a clustered service.
        If yes, return the cluster host of the service.
        If no, return the host name of the node.
        """
        key = (host_name, service_name, tuple(service_labels.items()))
        if (actual_hostname := self._effective_host_cache.get(key)) is not None:
            return actual_hostname

        self._effective_host_cache[key] = self._effective_host(
            host_name, service_name, service_labels
        )
        return self._effective_host_cache[key]

    def _effective_host(
        self,
        node_name: HostName,
        service_name: ServiceName,
        service_labels: Labels,
    ) -> HostName:
        if not (the_clusters := self.clusters_of(node_name)):
            return node_name

        cluster_mapping = self.ruleset_matcher.get_service_values_all(
            node_name,
            service_name,
            service_labels,
            clustered_services_mapping,
            self.label_manager.labels_of_host,
        )
        for cluster in cluster_mapping:
            # Check if the host is in this cluster
            if cluster in the_clusters:
                return cluster

        # 1. New style: explicitly assigned services
        for cluster, conf in clustered_services_of.items():
            if cluster not in self.hosts_config.clusters:
                raise MKGeneralException(
                    f"Invalid entry clustered_services_of['{cluster}']: {cluster} is not a cluster."
                )
            if node_name in self.nodes(cluster) and self.ruleset_matcher.get_service_bool_value(
                node_name, service_name, service_labels, conf, self.label_manager.labels_of_host
            ):
                return cluster

        # 1. Old style: clustered_services assumes that each host belong to
        #    exactly on cluster
        if self.ruleset_matcher.get_service_bool_value(
            node_name,
            service_name,
            service_labels,
            clustered_services,
            self.label_manager.labels_of_host,
        ):
            return the_clusters[0]

        return node_name

    def get_clustered_service_configuration(
        self, host_name: HostName, service_name: ServiceName, service_labels: Labels
    ) -> tuple[ClusterMode, Mapping[str, Any]]:
        matching_rules = self.ruleset_matcher.get_service_values_all(
            host_name,
            service_name,
            service_labels,
            clustered_services_configuration,
            self.label_manager.labels_of_host,
        )

        effective_mode = matching_rules[0][0] if matching_rules else "native"

        merged_cfg = {
            k: v
            for mode, cfg in reversed(matching_rules)
            if mode == effective_mode
            for k, v in cfg.items()
        }

        if effective_mode == "native":
            return "native", merged_cfg

        if effective_mode == "failover":
            return "failover", merged_cfg

        if effective_mode == "worst":
            return "worst", merged_cfg

        if effective_mode == "best":
            return "best", merged_cfg

        raise NotImplementedError(effective_mode)

    # TODO: Remove old name one day
    @staticmethod
    def service_discovery_name() -> ServiceName:
        if "cmk_inventory" in use_new_descriptions_for:
            return "Check_MK Discovery"
        return "Check_MK inventory"

    def agent_exclude_sections(self, host_name: HostName) -> dict[str, str]:
        settings = self.ruleset_matcher.get_host_values_all(
            host_name, agent_exclude_sections, self.label_manager.labels_of_host
        )
        return settings[0] if settings else {}

    def only_from(self, host_name: HostName) -> None | list[str] | str:
        """The agent of a host may be configured to be accessible only from specific IPs"""
        ruleset = agent_config.get("only_from", [])
        if not ruleset:
            return None

        entries = self.ruleset_matcher.get_host_values_all(
            host_name, ruleset, self.label_manager.labels_of_host
        )
        return entries[0] if entries else None

    def ping_levels(self, host_name: HostName) -> PingLevels:
        levels: PingLevels = {}

        values = self.ruleset_matcher.get_host_values_all(
            host_name, ping_levels, self.label_manager.labels_of_host
        )
        # TODO: Use get_host_merged_dict?)
        for value in values[::-1]:  # make first rules have precedence
            levels.update(value)

        return levels

    def icons_and_actions(self, host_name: HostName) -> list[str]:
        return list(
            set(
                self.ruleset_matcher.get_host_values_all(
                    host_name, host_icons_and_actions, self.label_manager.labels_of_host
                )
            )
        )

    def _site_of_host(self, host_name: HostName) -> SiteId:
        return SiteId(
            self.host_tags.tags(host_name).get(
                TagGroupID("site"), distributed_wato_site or omd_site()
            )
        )


class EnforcedServicesTable:
    """A table of enforced services"""

    def __init__(
        self,
        enforced_services_config: Callable[
            [HostName],
            Mapping[str, Sequence[Sequence[object]]],
        ],
        service_name_config: Callable[[HostName, ServiceID, str | None], ServiceName],
        plugins: Mapping[CheckPluginName, CheckPlugin],
    ) -> None:
        self._enforced_services_config = enforced_services_config
        self._service_name_config = service_name_config
        self._plugins = plugins
        self._memoized: dict[
            HostName, Mapping[ServiceID, tuple[RulesetName, ConfiguredService]]
        ] = {}

    def __call__(
        self, hostname: HostName
    ) -> Mapping[
        ServiceID,
        tuple[RulesetName, ConfiguredService],
    ]:
        """Return a table of enforced services

        Note: We need to reverse the order of the enforced services.
        Users assume that earlier rules have precedence over later ones.
        Important if there are two rules for a host with the same combination of plug-in name
        and item.
        """
        with contextlib.suppress(KeyError):
            return self._memoized[hostname]

        return self._memoized.setdefault(
            hostname,
            {
                (sid := ServiceID(check_plugin_name, item)): (
                    RulesetName(checkgroup_name),
                    ConfiguredService(
                        check_plugin_name=check_plugin_name,
                        item=item,
                        description=self._service_name_config(
                            hostname,
                            sid,
                            (
                                None
                                if (
                                    p := agent_based_register.get_check_plugin(
                                        check_plugin_name, self._plugins
                                    )
                                )
                                is None
                                else p.service_name
                            ),
                        ),
                        parameters=compute_enforced_service_parameters(
                            self._plugins, check_plugin_name, params
                        ),
                        discovered_parameters={},
                        discovered_labels={},
                        labels={},
                        is_enforced=True,
                    ),
                )
                for checkgroup_name, matched_rule_values in self._enforced_services_config(
                    hostname
                ).items()
                for check_plugin_name, item, params in (
                    self._sanitize_enforced_entry(*entry) for entry in reversed(matched_rule_values)
                )
            },
        )

    @staticmethod
    def _sanitize_enforced_entry(
        raw_name: object,
        raw_item: object,
        raw_params: Any | None = None,  # Can be any value spec supplied type :-(
    ) -> tuple[CheckPluginName, Item, TimespecificParameterSet]:
        return (
            CheckPluginName(maincheckify(str(raw_name))),
            None if raw_item is None else str(raw_item),
            TimespecificParameterSet.from_parameters({} if raw_params is None else raw_params),
        )


def access_globally_cached_config_cache() -> ConfigCache:
    """Get the global config cache"""
    return cache_manager.obtain_cache("config_cache")["cache"]


def _globally_cache_config_cache(config_cache: ConfigCache) -> None:
    """Create a new ConfigCache and set it in the cache manager"""
    cache_manager.obtain_cache("config_cache")["cache"] = config_cache


_RELAY_LABEL_KEY = "cmk/relay"


def get_relay_id(labels: Labels) -> str | None:
    return labels.get(_RELAY_LABEL_KEY)


def make_parser_config(
    loaded_config: LoadedConfigFragment,
    ruleset_matcher: RulesetMatcher,
    label_manager: LabelManager,
) -> ParserConfig:
    check_interval_config = make_check_interval_config(
        loaded_config, ruleset_matcher, label_manager
    )
    return ParserConfig(
        fallback_agent_output_encoding=loaded_config.fallback_agent_output_encoding,
        check_interval=lambda host_name: check_interval_config(host_name, "Check_MK"),
        piggyback_translations=SingleHostRulesetMatcherMerge(
            loaded_config.piggyback_translation, ruleset_matcher, label_manager.labels_of_host
        ),
        # Note: this is a reproduction of the logic we had before.
        # I think this can be simplified, fixing CMK-25914
        piggyback_max_cache_age_callbacks=lambda piggybacked_host_name: piggyback_backend.Config(
            piggybacked_host_name,
            guess_piggybacked_hosts_time_settings(
                loaded_config, ruleset_matcher, label_manager.labels_of_host, piggybacked_host_name
            ),
        ).max_cache_age,
    )


class FetcherFactory:
    # TODO: better and clearer separation between ConfigCache and this class.
    def __init__(
        self,
        config_cache: ConfigCache,
        ip_lookup: ip_lookup.IPLookup,
        tcp_fetcher_config: TCPFetcherConfig,
        snmp_fetcher_config: SNMPFetcherConfig,
        ruleset_matcher_: RulesetMatcher,
        service_configurer: ServiceConfigurer,
        service_name_config: Callable[[HostName, ServiceID, str | None], ServiceName],
        enforced_services_table: Callable[
            [HostName], Mapping[ServiceID, tuple[object, ConfiguredService]]
        ],
        *,
        is_cmc: bool,
    ) -> None:
        self._config_cache: Final = config_cache
        self._ip_lookup: Final = ip_lookup
        self._tcp_fetcher_config: Final = tcp_fetcher_config
        self._snmp_fetcher_config: Final = snmp_fetcher_config
        self._label_manager: Final = config_cache.label_manager
        self._ruleset_matcher: Final = ruleset_matcher_
        self._service_configurer: Final = service_configurer
        self._service_name_config: Final = service_name_config
        self._enforced_services_table: Final = enforced_services_table
        self.is_cmc: Final = is_cmc
        self.__disabled_snmp_sections: dict[HostName, frozenset[SNMPSectionName]] = {}

    def clear(self) -> None:
        self.__disabled_snmp_sections.clear()

    def _disabled_snmp_sections(self, host_name: HostName) -> frozenset[SNMPSectionName]:
        def disabled_snmp_sections_impl() -> frozenset[SNMPSectionName]:
            """Return a set of disabled snmp sections"""
            rules = self._ruleset_matcher.get_host_values_all(
                host_name, snmp_exclude_sections, self._label_manager.labels_of_host
            )
            merged_section_settings = {"if64adm": True}
            for rule in reversed(rules):
                for section in rule.get("sections_enabled", ()):
                    merged_section_settings[section] = False
                for section in rule.get("sections_disabled", ()):
                    merged_section_settings[section] = True

            return frozenset(
                SNMPSectionName(name)
                for name, is_disabled in merged_section_settings.items()
                if is_disabled
            )

        with contextlib.suppress(KeyError):
            return self.__disabled_snmp_sections[host_name]

        return self.__disabled_snmp_sections.setdefault(host_name, disabled_snmp_sections_impl())

    def _make_snmp_sections(
        self,
        host_name: HostName,
        *,
        checking_sections: frozenset[SNMPSectionName],
        sections: Iterable[SNMPSectionPlugin],
    ) -> Mapping[SNMPSectionName, SNMPSectionMeta]:
        disabled_sections = self._disabled_snmp_sections(host_name)
        redetect_sections = {
            SNMPSectionName(name)
            for name in agent_based_register.sections_needing_redetection(sections)
        }
        return {
            SNMPSectionName(name): SNMPSectionMeta(
                checking=name in checking_sections,
                disabled=name in disabled_sections,
                redetect=name in checking_sections and name in redetect_sections,
            )
            for name in (checking_sections | disabled_sections)
        }

    def make_snmp_fetcher(
        self,
        plugins: AgentBasedPlugins,
        host_name: HostName,
        host_ip_family: Literal[socket.AddressFamily.AF_INET, socket.AddressFamily.AF_INET6],
        ip_address: HostAddress,
        *,
        source_type: SourceType,
    ) -> SNMPFetcher:
        snmp_config = self._config_cache.make_snmp_config(
            host_name,
            host_ip_family,
            ip_address,
            source_type,
            backend_override=self._snmp_fetcher_config.backend_override,
        )
        fetcher = SNMPFetcher(
            sections=self._make_snmp_sections(
                host_name,
                checking_sections=self._config_cache.make_checking_sections(
                    plugins,
                    self._service_configurer,
                    self._service_name_config,
                    host_name,
                    self._enforced_services_table,
                    selected_sections=self._snmp_fetcher_config.selected_sections,
                ),
                sections=plugins.snmp_sections.values(),
            ),
            plugin_store=make_plugin_store(plugins),
            scan_config=SNMPScanConfig(
                on_error=self._snmp_fetcher_config.on_error,
                missing_sys_description=self._snmp_fetcher_config.missing_sys_description(
                    host_name
                ),
            ),
            do_status_data_inventory=self._config_cache.hwsw_inventory_parameters(
                host_name
            ).status_data_inventory,
            base_path=self._snmp_fetcher_config.base_path,
            relative_section_cache_path=self._snmp_fetcher_config.relative_section_cache_path,
            snmp_config=snmp_config,
            caching_config=self._snmp_fetcher_config.caching_config(host_name),
            relative_stored_walk_path=self._snmp_fetcher_config.relative_stored_walk_path,
            relative_walk_cache_path=self._snmp_fetcher_config.relative_walk_cache_path,
        )
        return fetcher

    def make_tcp_fetcher(
        self,
        host_name: HostName,
        host_ip_family: Literal[socket.AddressFamily.AF_INET, socket.AddressFamily.AF_INET6],
        ip_address: HostAddress,
        *,
        tls_config: TLSConfig,
    ) -> TCPFetcher:
        return TCPFetcher(
            host_name=host_name,
            address=(ip_address, self._tcp_fetcher_config.agent_port(host_name)),
            family=host_ip_family,
            timeout=self._tcp_fetcher_config.connect_timeout(host_name),
            encryption_handling=self._tcp_fetcher_config.parsed_encryption_handling(host_name),
            uuid_file=cmk.utils.paths.uuid_lookup_dir / host_name,
            pre_shared_secret=self._tcp_fetcher_config.symmetric_agent_encryption(host_name),
            tls_config=tls_config,
        )

    def make_ipmi_fetcher(self, host_name: HostName, ip_address: HostAddress) -> IPMIFetcher:
        ipmi_credentials = self._config_cache.management_credentials(host_name, "ipmi")
        return IPMIFetcher(
            address=ip_address,
            username=ipmi_credentials.get("username"),
            password=ipmi_credentials.get("password"),
        )

    def _make_fetcher_program_commandline(
        self,
        host_name: HostName,
        host_ip_family: Literal[socket.AddressFamily.AF_INET, socket.AddressFamily.AF_INET6],
        ip_address: HostAddress | None,
        ip_address_of: IPLookup,
        program: str,
    ) -> str:
        return self._config_cache.translate_fetcher_commandline(
            host_name, host_ip_family, ip_address, program, ip_address_of
        )

    def make_program_fetcher(
        self,
        host_name: HostName,
        host_ip_family: Literal[socket.AddressFamily.AF_INET, socket.AddressFamily.AF_INET6],
        ip_address: HostAddress | None,
        *,
        program: str,
        stdin: str | None,
    ) -> ProgramFetcher:
        cmdline = self._make_fetcher_program_commandline(
            host_name, host_ip_family, ip_address, self._ip_lookup, program
        )
        return ProgramFetcher(cmdline=cmdline, stdin=stdin, is_cmc=self.is_cmc)

    def make_special_agent_fetcher(self, *, cmdline: str, stdin: str | None) -> ProgramFetcher:
        return ProgramFetcher(cmdline=cmdline, stdin=stdin, is_cmc=self.is_cmc)

    def make_piggyback_fetcher(self) -> PiggybackFetcher:
        return PiggybackFetcher()


def _parse[T](raw: object, type_: Callable[..., T], /) -> T:
    return type_(raw)
