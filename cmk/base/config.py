#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# ruff: noqa: F405

from __future__ import annotations

import contextlib
import copy
import dataclasses
import enum
import ipaddress
import itertools
import logging
import numbers
import os
import pickle
import socket
import sys
import time
from collections.abc import Callable, Container, Iterable, Iterator, Mapping, Sequence
from enum import Enum
from pathlib import Path
from typing import (
    Any,
    AnyStr,
    assert_never,
    Final,
    Generic,
    Literal,
    NamedTuple,
    overload,
    TypeGuard,
    TypeVar,
)

import cmk.ccc.debug
import cmk.ccc.version as cmk_version
from cmk.ccc import store
from cmk.ccc.exceptions import MKGeneralException, MKIPAddressLookupError
from cmk.ccc.site import omd_site

import cmk.utils
import cmk.utils.check_utils
import cmk.utils.cleanup
import cmk.utils.config_path
import cmk.utils.paths
import cmk.utils.tags
import cmk.utils.translations
from cmk.utils import config_warnings, ip_lookup, password_store, tty
from cmk.utils.agent_registration import connection_mode_from_host_config, HostAgentConnectionMode
from cmk.utils.caching import cache_manager
from cmk.utils.check_utils import maincheckify, section_name_of
from cmk.utils.config_path import ConfigPath
from cmk.utils.host_storage import apply_hosts_file_to_object, get_host_storage_loaders
from cmk.utils.hostaddress import HostAddress, HostName, Hosts
from cmk.utils.http_proxy_config import http_proxy_config_from_user_setting, HTTPProxyConfig
from cmk.utils.ip_lookup import IPStackConfig
from cmk.utils.labels import LabelManager, Labels, LabelSources
from cmk.utils.log import console
from cmk.utils.macros import replace_macros_in_str
from cmk.utils.regex import regex
from cmk.utils.rulesets import ruleset_matcher, RuleSetName, tuple_rulesets
from cmk.utils.rulesets.ruleset_matcher import (
    RulesetMatcher,
    RulesetName,
    RuleSpec,
)
from cmk.utils.sectionname import SectionName
from cmk.utils.servicename import Item, ServiceName
from cmk.utils.structured_data import RawIntervalFromConfig
from cmk.utils.tags import ComputedDataSources, TagGroupID, TagID
from cmk.utils.timeperiod import TimeperiodName

from cmk.snmplib import (  # these are required in the modules' namespace to load the configuration!
    SNMPBackendEnum,
    SNMPContextConfig,
    SNMPCredentials,
    SNMPHostConfig,
    SNMPRawDataElem,
    SNMPTiming,
    SNMPVersion,
)

from cmk.fetchers import (
    IPMICredentials,
    IPMIFetcher,
    PiggybackFetcher,
    ProgramFetcher,
    SNMPFetcher,
    SNMPSectionMeta,
    TCPEncryptionHandling,
    TCPFetcher,
    TLSConfig,
)
from cmk.fetchers.config import make_persisted_section_dir
from cmk.fetchers.filecache import MaxAge

import cmk.checkengine.plugin_backend as agent_based_register
from cmk.checkengine.checking import (
    merge_enforced_services,
    ServiceConfigurer,
)
from cmk.checkengine.checking.cluster_mode import ClusterMode
from cmk.checkengine.discovery import (
    AutochecksManager,
    CheckPreviewEntry,
    DiscoveryCheckParameters,
    merge_cluster_autochecks,
)
from cmk.checkengine.exitspec import ExitSpec
from cmk.checkengine.fetcher import FetcherType, SourceType
from cmk.checkengine.inventory import HWSWInventoryParameters
from cmk.checkengine.parameters import TimespecificParameters, TimespecificParameterSet
from cmk.checkengine.parser import (
    AgentParser,
    AgentRawDataSectionElem,
    NO_SELECTION,
    SectionNameCollection,
    SectionStore,
    SNMPParser,
)
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
    ConfiguredService,
    InventoryPlugin,
    ServiceID,
    SNMPSectionPlugin,
)
from cmk.checkengine.summarize import SummaryConfig

from cmk.base import default_config
from cmk.base.configlib.checkengine import CheckingConfig
from cmk.base.configlib.labels import LabelConfig
from cmk.base.default_config import *  # noqa: F403
from cmk.base.parent_scan import ScanConfig as ParentScanConfig
from cmk.base.sources import SNMPFetcherConfig

from cmk import trace
from cmk.agent_based.legacy import discover_legacy_checks, FileLoader, find_plugin_files
from cmk.piggyback import backend as piggyback_backend
from cmk.rrd.config import RRDObjectConfig  # pylint: disable=cmk-module-layer-violation
from cmk.server_side_calls import v1 as server_side_calls_api
from cmk.server_side_calls_backend import (
    ActiveCheck,
    ActiveServiceData,
    ExecutableFinder,
    load_active_checks,
    load_special_agents,
    SpecialAgent,
    SpecialAgentCommandLine,
    SSCRules,
)
from cmk.server_side_calls_backend.config_processing import PreprocessingResult

try:
    from cmk.utils.cme.labels import (  # type: ignore[import-not-found, import-untyped, unused-ignore]
        get_builtin_host_labels,
    )
except ModuleNotFoundError:
    from cmk.utils.labels import get_builtin_host_labels


tracer = trace.get_tracer()

_ContactgroupName = str

# TODO: Prefix helper functions with "_".

# Default values for retry and check intervals in minutes
# Hosts. Check and retry intervals are same
SMARTPING_CHECK_INTERVAL: Final = 0.1
HOST_CHECK_INTERVAL: Final = 1.0
# Services. Check and retry intervals may differ
SERVICE_RETRY_INTERVAL: Final = 1.0
SERVICE_CHECK_INTERVAL: Final = 1.0

ServicegroupName = str
HostgroupName = str

service_service_levels: list[RuleSpec[int]] = []
host_service_levels: list[RuleSpec[int]] = []

_AgentTargetVersion = None | str | tuple[str, str] | tuple[str, dict[str, str]]

ShadowHosts = dict[HostName, dict[str, Any]]

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
                    config_cache, host_name, get_autochecks, configure_autochecks, plugins
                )
                if sfilter.keep(s)
            )
        else:
            yield from (
                s
                for s in configure_autochecks(
                    host_name, config_cache.autochecks_manager.get_autochecks(host_name)
                )
                if sfilter.keep(s)
            )

    yield from (
        svc
        for _, svc in config_cache.enforced_services_table(host_name, plugins).values()
        if sfilter.keep(svc)
    )

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
            config_cache, host_name, get_autochecks, configure_autochecks, plugins
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
    node_name: HostName,
    get_autochecks: Callable[[HostAddress], Sequence[AutocheckEntry]],
    configure_autochecks: Callable[
        [HostName, Sequence[AutocheckEntry]],
        Iterable[ConfiguredService],
    ],
    plugins: Mapping[CheckPluginName, CheckPlugin],
) -> Iterable[ConfiguredService]:
    for cluster in config_cache.clusters_of(node_name):
        yield from _get_clustered_services(
            config_cache, cluster, get_autochecks, configure_autochecks, plugins
        )


def _get_clustered_services(
    config_cache: ConfigCache,
    cluster_name: HostName,
    get_autochecks: Callable[[HostAddress], Sequence[AutocheckEntry]],
    configure_autochecks: Callable[
        [HostName, Sequence[AutocheckEntry]],
        Iterable[ConfiguredService],
    ],
    plugins: Mapping[CheckPluginName, CheckPlugin],
) -> Iterable[ConfiguredService]:
    nodes = config_cache.nodes(cluster_name)

    if not config_cache.is_ping_host(cluster_name):

        def appears_on_cluster(node_name: HostAddress, entry: AutocheckEntry) -> bool:
            if config_cache.check_plugin_ignored(node_name, entry.check_plugin_name):
                return False
            service_name = service_description(
                config_cache.ruleset_matcher,
                config_cache.label_manager.labels_of_host,
                node_name,
                entry.check_plugin_name,
                service_name_template=(
                    None
                    if (
                        p := agent_based_register.get_check_plugin(entry.check_plugin_name, plugins)
                    )
                    is None
                    else p.service_name
                ),
                item=entry.item,
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
        {
            node_name: config_cache.enforced_services_table(node_name, plugins)
            for node_name in nodes
        },
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
RecurringDowntime = Mapping[str, int | str]  # TODO(sk): TypedDict here


class _NestedExitSpec(ExitSpec, total=False):
    overall: ExitSpec
    individual: dict[str, ExitSpec]


IPLookup = Callable[
    [HostName, Literal[socket.AddressFamily.AF_INET, socket.AddressFamily.AF_INET6]],
    HostAddress | None,
]

_TErrHandler = TypeVar("_TErrHandler", bound=Callable[[HostName, Exception], None])


class ConfiguredIPLookup(Generic[_TErrHandler]):
    def __init__(self, config_cache: ConfigCache, *, error_handler: _TErrHandler) -> None:
        self._config_cache = config_cache
        self.error_handler: Final[_TErrHandler] = error_handler

    def __call__(
        self,
        host_name: HostName,
        family: Literal[socket.AddressFamily.AF_INET, socket.AddressFamily.AF_INET6],
    ) -> HostAddress | None:
        try:
            return lookup_ip_address(self._config_cache, host_name, family=family)
        except Exception as e:
            if host_name in self._config_cache.hosts_config.clusters:
                return HostAddress("")
            self.error_handler(host_name, e)

        return ip_lookup.fallback_ip_for(family)


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
        key: copy.deepcopy(value) if isinstance(value, (dict, list)) else value
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
class LoadedConfigFragment:
    """Return *some of* the values that have been loaded as part of the config loading process.

    The config loading currently mostly manipulates a global state.
    Return an instance of this class, to indicate that the config has been loaded.

    Someday (TM): return the actual loaded config, at which point this class will be quite big
    (compare cmk/base/default_config/base ...)
    """

    discovery_rules: Mapping[RuleSetName, Sequence[RuleSpec]]
    checkgroup_parameters: Mapping[str, Sequence[RuleSpec[Mapping[str, object]]]]
    service_rule_groups: set[str]


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
    with_conf_d: bool = True,
    validate_hosts: bool = True,
) -> LoadingResult:
    _initialize_config()

    _changed_var_names = _load_config(with_conf_d)

    _initialize_derived_config_variables()

    loading_result = _perform_post_config_loading_actions(discovery_rulesets)

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
    config_path: ConfigPath, discovery_rulesets: Iterable[RuleSetName]
) -> LoadingResult:
    """Load the configuration for the CMK helpers of CMC

    These files are written by PackedConfig().

    Should have a result similar to the load() above. With the exception that the
    check helpers would only need check related config variables.

    The validations which are performed during load() also don't need to be performed.

    See Also:
        cmk.base.core_nagios._dump_precompiled_hostcheck()

    """
    _initialize_config()
    globals().update(PackedConfigStore.from_serial(config_path).read())
    return _perform_post_config_loading_actions(discovery_rulesets)


def _initialize_config() -> None:
    load_default_config()


def _perform_post_config_loading_actions(
    discovery_rulesets: Iterable[RuleSetName],
) -> LoadingResult:
    """These tasks must be performed after loading the Check_MK base configuration"""
    # First cleanup things (needed for e.g. reloading the config)
    cache_manager.clear_all()

    global_dict = globals()
    discovery_settings = _collect_parameter_rulesets_from_globals(global_dict, discovery_rulesets)
    _transform_plugin_names_from_160_to_170(global_dict)
    _drop_invalid_ssc_rules(global_dict)

    loaded_config = LoadedConfigFragment(
        discovery_rules=discovery_settings,
        checkgroup_parameters=checkgroup_parameters,
        service_rule_groups=service_rule_groups,
    )

    config_cache = _create_config_cache(loaded_config).initialize()
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

    def set_current_path(self, current_path: str | None) -> None:
        self._current_path = current_path

    def _set_folder_paths(self, new_hosts: Iterable[str]) -> None:
        if self._current_path is None:
            return
        for hostname in strip_tags(new_hosts):
            host_paths[hostname] = self._current_path


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
    experimental_config = cmk.utils.paths.make_experimental_config_file()
    if experimental_config.exists():
        _load_config_file(experimental_config, global_dict)

    host_storage_loaders = get_host_storage_loaders(config_storage_format)
    config_dir_path = Path(cmk.utils.paths.check_mk_config_dir)
    for path in get_config_file_paths(with_conf_d):
        try:
            # Make the config path available as a global variable to be used
            # within the configuration file. The FOLDER_PATH is only used by
            # rules.mk files these days, but may also be used in some legacy
            # config files or files generated by 3rd party mechanisms.
            current_path: str | None = None
            folder_path: str | None = None
            with contextlib.suppress(ValueError):
                relative_path = path.relative_to(config_dir_path)
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

            if not isinstance(clusters, SetFolderPathDict):
                raise MKGeneralException(
                    "Load config error: The clusters parameter was modified through an other method than: x['a']=b or x.update({'a': b})"
                )

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
    list_of_files = [Path(cmk.utils.paths.main_config_file)]
    if with_conf_d:
        all_files = Path(cmk.utils.paths.check_mk_config_dir).rglob("*")
        list_of_files += sorted(
            [p for p in all_files if p.suffix in {".mk"}], key=cmk.utils.key_config_paths
        )
    for path in [Path(cmk.utils.paths.final_config_file), Path(cmk.utils.paths.local_config_file)]:
        if path.exists():
            list_of_files.append(path)
    return list_of_files


def _initialize_derived_config_variables() -> None:
    global service_service_levels, host_service_levels
    service_service_levels = extra_service_conf.get("_ec_sl", [])
    _default: list[RuleSpec[int]] = []
    host_service_levels = extra_host_conf.get("_ec_sl", _default)


def get_derived_config_variable_names() -> set[str]:
    """These variables are computed from other configuration variables and not configured directly.

    The origin variable (extra_service_conf) should not be exported to the helper config. Only
    the service levels are needed."""
    return {"service_service_levels", "host_service_levels"}


def save_packed_config(
    config_path: ConfigPath,
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
                # Include offline cluster hosts.
                # Otherwise services clustered to those hosts will wrongly be checked by the nodes.
                if clustername in hosts_config.clusters and self._config_cache.is_active(
                    clustername
                ):
                    clusters_red[cluster_entry] = cluster_nodes
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
            return {"check_interval": values.get("check_interval", [])}

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
        derived_config_variable_names = get_derived_config_variable_names()

        global_variables = globals()

        for varname in (*variable_defaults, *derived_config_variable_names):
            if varname in self._skipped_config_variable_names:
                continue

            val = global_variables[varname]

            if varname not in derived_config_variable_names and val == variable_defaults[varname]:
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
    def from_serial(cls, config_path: ConfigPath) -> PackedConfigStore:
        return cls(cls.make_packed_config_store_path(config_path))

    @classmethod
    def make_packed_config_store_path(cls, config_path: ConfigPath) -> Path:
        return Path(config_path) / "precompiled_check_config.mk"

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
        cmk.utils.paths.autochecks_dir = str(autochecks_dir)
        cmk.utils.paths.discovered_host_labels_dir = discovered_host_labels_dir
        yield
    finally:
        cmk.utils.paths.autochecks_dir = orig_autochecks_dir
        cmk.utils.paths.discovered_host_labels_dir = orig_discovered_host_labels_dir


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


def _get_shadow_hosts() -> ShadowHosts:
    try:
        # Only available with CEE
        return shadow_hosts  # type: ignore[name-defined,unused-ignore]
    except NameError:
        return {}


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

# Renaming of service names while keeping backward compatibility with
# existing installations.
# Synchronize with htdocs/wato.py and plugins/wato/check_mk_configuration.py!


# Cleanup! .. some day
def _get_old_cmciii_temp_description(item: Item) -> tuple[ServiceName, None]:
    if item is None:
        raise TypeError()

    if "Temperature" in item:
        return item, None  # old item format, no conversion

    parts = item.split(" ")
    if parts[0] == "Ambient":
        return f"{parts[1]} Temperature", None

    if len(parts) == 2:
        return f"{parts[1]} {parts[0]}.Temperature", None

    if parts[1] == "LCP":
        parts[1] = "Liquid_Cooling_Package"
    return f"{parts[1]} {parts[0]}.{parts[2]}-Temperature", None


_old_service_descriptions: Mapping[str, Callable[[Item], tuple[ServiceName, Item]]] = {
    "aix_memory": lambda item: ("Memory used", item),
    # While using the old description, don't append the item, even when discovered
    # with the new check which creates an item.
    "barracuda_mailqueues": lambda item: ("Mail Queue", None),
    "brocade_sys_mem": lambda item: ("Memory used", item),
    "casa_cpu_temp": lambda item: ("Temperature %s", item),
    "cisco_asa_failover": lambda item: ("Cluster Status", item),
    "cisco_mem": lambda item: ("Mem used %s", item),
    "cisco_mem_asa": lambda item: ("Mem used %s", item),
    "cisco_mem_asa64": lambda item: ("Mem used %s", item),
    "cmciii_temp": _get_old_cmciii_temp_description,
    "cmciii_psm_current": lambda item: ("%s", item),
    "cmciii_lcp_airin": lambda item: ("LCP Fanunit Air IN", item),
    "cmciii_lcp_airout": lambda item: ("LCP Fanunit Air OUT", item),
    "cmciii_lcp_water": lambda item: ("LCP Fanunit Water %s", item),
    "db2_mem": lambda item: ("Mem of %s", item),
    "df": lambda item: ("fs_%s", item),
    "df_netapp": lambda item: ("fs_%s", item),
    "df_netapp32": lambda item: ("fs_%s", item),
    "docker_container_mem": lambda item: ("Memory used", item),
    "enterasys_temp": lambda item: ("Temperature", None),
    "esx_vsphere_datastores": lambda item: ("fs_%s", item),
    "esx_vsphere_hostsystem_mem_usage": lambda item: ("Memory used", item),
    "esx_vsphere_hostsystem_mem_usage_cluster": lambda item: ("Memory usage", item),
    "etherbox_temp": lambda item: ("Sensor %s", item),
    "fortigate_memory": lambda item: ("Memory usage", item),
    "fortigate_memory_base": lambda item: ("Memory usage", item),
    "fortigate_node_memory": lambda item: ("Memory usage %s", item),
    "hr_fs": lambda item: ("fs_%s", item),
    "hr_mem": lambda item: ("Memory used", item),
    "huawei_switch_mem": lambda item: ("Memory used %s", item),
    "hyperv_vm": lambda item: ("hyperv_vms", item),
    "ibm_svc_mdiskgrp": lambda item: ("MDiskGrp %s", item),
    "ibm_svc_system": lambda item: ("IBM SVC Info", item),
    "ibm_svc_systemstats_cache": lambda item: ("IBM SVC Cache Total", item),
    "ibm_svc_systemstats_diskio": lambda item: ("IBM SVC Throughput %s Total", item),
    "ibm_svc_systemstats_disk_latency": lambda item: ("IBM SVC Latency %s Total", item),
    "ibm_svc_systemstats_iops": lambda item: ("IBM SVC IOPS %s Total", item),
    "innovaphone_mem": lambda item: ("Memory used", item),
    "innovaphone_temp": lambda item: ("Temperature", None),
    "juniper_mem": lambda item: ("Memory Utilization %s", item),
    "juniper_screenos_mem": lambda item: ("Memory used", item),
    "juniper_trpz_mem": lambda item: ("Memory used", item),
    "liebert_bat_temp": lambda item: ("Battery Temp", None),
    "logwatch": lambda item: ("LOG %s", item),
    "logwatch_groups": lambda item: ("LOG %s", item),
    "megaraid_bbu": lambda item: ("RAID Adapter/BBU %s", item),
    "megaraid_pdisks": lambda item: ("RAID PDisk Adapt/Enc/Sl %s", item),
    "megaraid_ldisks": lambda item: ("RAID Adapter/LDisk %s", item),
    "mem_used": lambda item: ("Memory used", item),
    "mem_win": lambda item: ("Memory and pagefile", item),
    "mknotifyd": lambda item: ("Notification Spooler %s", item),
    "mknotifyd_connection": lambda item: ("Notification Connection %s", item),
    "mssql_backup": lambda item: ("%s Backup", item),
    "mssql_blocked_sessions": lambda item: ("MSSQL Blocked Sessions", None),
    "mssql_counters_cache_hits": lambda item: ("%s", item),
    "mssql_counters_file_sizes": lambda item: ("%s File Sizes", item),
    "mssql_counters_locks": lambda item: ("%s Locks", item),
    "mssql_counters_locks_per_batch": lambda item: ("%s Locks per Batch", item),
    "mssql_counters_pageactivity": lambda item: ("%s Page Activity", item),
    "mssql_counters_sqlstats": lambda item: ("%s", item),
    "mssql_counters_transactions": lambda item: ("%s Transactions", item),
    "mssql_databases": lambda item: ("%s Database", item),
    "mssql_datafiles": lambda item: ("Datafile %s", item),
    "mssql_tablespaces": lambda item: ("%s Sizes", item),
    "mssql_transactionlogs": lambda item: ("Transactionlog %s", item),
    "mssql_versions": lambda item: ("%s Version", item),
    "netscaler_mem": lambda item: ("Memory used", item),
    "nullmailer_mailq": lambda item: ("Nullmailer Queue", None),
    "nvidia_temp": lambda item: ("Temperature NVIDIA %s", item),
    "postfix_mailq": lambda item: (
        ("Postfix Queue", None) if item == "default" else ("Postfix Queue %s", item)
    ),
    "ps": lambda item: ("proc_%s", item),
    "qmail_stats": lambda item: ("Qmail Queue", None),
    "raritan_emx": lambda item: ("Rack %s", item),
    "raritan_pdu_inlet": lambda item: ("Input Phase %s", item),
    "services": lambda item: ("service_%s", item),
    "solaris_mem": lambda item: ("Memory used", item),
    "sophos_memory": lambda item: ("Memory usage", item),
    "statgrab_mem": lambda item: ("Memory used", item),
    "tplink_mem": lambda item: ("Memory used", item),
    "ups_bat_temp": lambda item: ("Temperature Battery %s", item),
    "vms_diskstat_df": lambda item: ("fs_%s", item),
    "wmic_process": lambda item: ("proc_%s", item),
    "zfsget": lambda item: ("fs_%s", item),
    "prism_alerts": lambda item: ("Prism Alerts", None),
    "prism_containers": lambda item: ("Containers %s", item),
    "prism_info": lambda item: ("Prism Cluster", None),
    "prism_storage_pools": lambda item: ("Storage Pool %s", item),
}


def _make_service_description_cb(
    matcher: RulesetMatcher,
    labels_of_host: Callable[[HostName], Labels],
    check_plugins: Mapping[CheckPluginName, CheckPlugin],
) -> Callable[[HostName, CheckPluginName, Item], ServiceName]:
    """Replacement for functool.partial(service_description, matcher)

    functools.partial is not supported by the mypy type checker.
    """

    def callback(hostname: HostName, check_plugin_name: CheckPluginName, item: Item) -> ServiceName:
        return service_description(
            matcher,
            labels_of_host,
            hostname,
            check_plugin_name,
            service_name_template=(
                None
                if (p := agent_based_register.get_check_plugin(check_plugin_name, check_plugins))
                is None
                else p.service_name
            ),
            item=item,
        )

    return callback


def service_description(
    matcher: RulesetMatcher,
    labels_of_host: Callable[[HostName], Labels],
    hostname: HostName,
    check_plugin_name: CheckPluginName,
    *,
    service_name_template: str | None,
    item: Item,
) -> ServiceName:
    if service_name_template is None:
        return (
            f"Unimplemented check {check_plugin_name} / {item}"
            if item
            else f"Unimplemented check {check_plugin_name}"
        )

    return get_final_service_description(
        _format_item_with_template(
            *_get_service_description_template_and_item(
                check_plugin_name, service_name_template, item
            )
        ),
        get_service_translations(matcher, labels_of_host, hostname),
    )


def _get_service_description_template_and_item(
    plugin_name: CheckPluginName, service_name_template: str, item: Item
) -> tuple[ServiceName, Item]:
    plugin_name_str = str(plugin_name)

    # use user-supplied service name, if available
    if descr_format := service_descriptions.get(plugin_name_str):
        return descr_format, item

    old_descr = _old_service_descriptions.get(plugin_name_str)
    if old_descr is None or plugin_name_str in use_new_descriptions_for:
        return service_name_template, item
    return old_descr(item)


def _format_item_with_template(template: str, item: Item) -> str:
    """
    >>> _format_item_with_template("Foo", None)
    'Foo'
    >>> _format_item_with_template("Foo %s", None)
    'Foo <missing an item>'
    >>> _format_item_with_template("Foo", "bar")
    'Foo bar'
    >>> _format_item_with_template("Foo %s", "bar")
    'Foo bar'
    """
    try:
        return template % ("<missing an item>" if item is None else item)
    except TypeError:
        return f"{template} {item or ''}".strip()


def get_final_service_description(
    description: ServiceName, translations: cmk.utils.translations.TranslationOptions
) -> ServiceName:
    # Note: at least strip the service name.
    # Some plugins introduce trailing whitespaces, but Nagios silently drops leading
    # and trailing spaces in the configuration file.
    description = (
        cmk.utils.translations.translate_service_description(translations, description).strip()
        if translations
        else description.strip()
    )

    # Sanitize: remove illegal characters from a service name
    cache = cache_manager.obtain_cache("final_service_description")
    with contextlib.suppress(KeyError):
        return cache[description]

    illegal_chars = cmc_illegal_chars if is_cmc() else nagios_illegal_chars

    return cache.setdefault(
        description, "".join(c for c in description if c not in illegal_chars).rstrip("\\")
    )


# TODO: Make this use the generic "rulesets" functions
# a) This function has never been configurable via WATO (see https://mathias-kettner.de/checkmk_service_dependencies.html)
# b) It only affects the Nagios core - CMC does not implement service dependencies
# c) This function implements some specific regex replacing match+replace which makes it incompatible to
#    regular service rulesets. Therefore service_extra_conf() can not easily be used :-/
def service_depends_on(
    config_cache: ConfigCache, hostname: HostName, servicedesc: ServiceName
) -> list[ServiceName]:
    """Return a list of services this service depends upon"""
    deps = []
    for entry in service_dependencies:
        entry, rule_options = tuple_rulesets.get_rule_options(entry)
        if rule_options.get("disabled"):
            continue

        if len(entry) == 3:
            depname, hostlist, patternlist = entry
            tags: list[TagID] = []
        elif len(entry) == 4:
            depname, tags, hostlist, patternlist = entry
        else:
            raise MKGeneralException(
                "Invalid entry '%r' in service dependencies: must have 3 or 4 entries" % entry
            )

        if tuple_rulesets.hosttags_match_taglist(
            config_cache.tag_list(hostname), tags
        ) and tuple_rulesets.in_extraconf_hostlist(hostlist, hostname):
            for pattern in patternlist:
                if matchobject := regex(pattern).search(servicedesc):
                    try:
                        item = matchobject.groups()[-1]
                        deps.append(depname % item)
                    except Exception:
                        deps.append(depname)
    return deps


# .
#   .--Misc Helpers--------------------------------------------------------.
#   |        __  __ _            _   _      _                              |
#   |       |  \/  (_)___  ___  | | | | ___| |_ __   ___ _ __ ___          |
#   |       | |\/| | / __|/ __| | |_| |/ _ \ | '_ \ / _ \ '__/ __|         |
#   |       | |  | | \__ \ (__  |  _  |  __/ | |_) |  __/ |  \__ \         |
#   |       |_|  |_|_|___/\___| |_| |_|\___|_| .__/ \___|_|  |___/         |
#   |                                        |_|                           |
#   +----------------------------------------------------------------------+
#   | Different helper functions                                           |
#   '----------------------------------------------------------------------'


def is_cmc() -> bool:
    """Whether or not the site is currently configured to use the Micro Core."""
    return monitoring_core == "cmc"


def get_piggyback_translations(
    matcher: RulesetMatcher, labels_of_host: Callable[[HostName], Labels], hostname: HostName
) -> cmk.utils.translations.TranslationOptions:
    """Get a dict that specifies the actions to be done during the hostname translation"""
    rules = matcher.get_host_values(hostname, piggyback_translation, labels_of_host)
    translations: cmk.utils.translations.TranslationOptions = {}
    for rule in rules[::-1]:
        translations.update(rule)
    return translations


def get_service_translations(
    matcher: RulesetMatcher, labels_of_host: Callable[[HostName], Labels], hostname: HostName
) -> cmk.utils.translations.TranslationOptions:
    translations_cache = cache_manager.obtain_cache("service_description_translations")
    with contextlib.suppress(KeyError):
        return translations_cache[hostname]

    rules = matcher.get_host_values(hostname, service_description_translation, labels_of_host)
    translations: cmk.utils.translations.TranslationOptions = {}
    for rule in rules[::-1]:
        if "case" in rule:
            translations["case"] = rule["case"]
        if "drop_domain" in rule:
            translations["drop_domain"] = rule["drop_domain"]
        if "regex" in rule:
            translations["regex"] = list(set(translations.get("regex", [])) | set(rule["regex"]))
        if "mapping" in rule:
            translations["mapping"] = list(
                set(translations.get("mapping", [])) | set(rule["mapping"])
            )

    return translations_cache.setdefault(hostname, translations)


def get_http_proxy(http_proxy: tuple[str, str]) -> HTTPProxyConfig:
    """Returns a proxy config object to be used for HTTP requests

    Intended to receive a value configured by the user using the HTTPProxyReference valuespec.
    """
    return http_proxy_config_from_user_setting(
        http_proxy,
        http_proxies,
    )


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


def load_all_plugins(
    checks_dir: str,
) -> AgentBasedPlugins:
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
            makedirs=store.makedirs,
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


def lookup_mgmt_board_ip_address(
    config_cache: ConfigCache, host_name: HostName
) -> HostAddress | None:
    mgmt_address: Final = config_cache.management_address(host_name)
    try:
        mgmt_ipa = (
            None if mgmt_address is None else HostAddress(str(ipaddress.ip_address(mgmt_address)))
        )
    except (ValueError, TypeError):
        mgmt_ipa = None

    try:
        return ip_lookup.lookup_ip_address(
            # host name is ignored, if mgmt_ipa is trueish.
            host_name=mgmt_address or host_name,
            family=config_cache.default_address_family(host_name),
            configured_ip_address=mgmt_ipa,
            simulation_mode=simulation_mode,
            is_snmp_usewalk_host=(
                config_cache.get_snmp_backend(host_name) is SNMPBackendEnum.STORED_WALK
                and (config_cache.management_protocol(host_name) == "snmp")
            ),
            override_dns=HostAddress(fake_dns) if fake_dns is not None else None,
            is_dyndns_host=config_cache.is_dyndns_host(host_name),
            force_file_cache_renewal=not use_dns_cache,
        )
    except MKIPAddressLookupError:
        return None


def lookup_ip_address(
    config_cache: ConfigCache,
    host_name: HostName | HostAddress,
    *,
    family: Literal[socket.AddressFamily.AF_INET, socket.AddressFamily.AF_INET6] | None = None,
) -> HostAddress:
    if family is None:
        family = config_cache.default_address_family(host_name)
    return ip_lookup.lookup_ip_address(
        host_name=host_name,
        family=family,
        configured_ip_address=(
            ipaddresses if family is socket.AddressFamily.AF_INET else ipv6addresses
        ).get(host_name),
        simulation_mode=simulation_mode,
        is_snmp_usewalk_host=(
            config_cache.get_snmp_backend(host_name) is SNMPBackendEnum.STORED_WALK
            and config_cache.computed_datasources(host_name).is_snmp
        ),
        override_dns=HostAddress(fake_dns) if fake_dns is not None else None,
        is_dyndns_host=config_cache.is_dyndns_host(host_name),
        force_file_cache_renewal=not use_dns_cache,
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


def get_resource_macros() -> Mapping[str, str]:
    macros = {}
    try:
        for line in (cmk.utils.paths.omd_root / "etc/nagios/resource.cfg").open():
            line = line.strip()
            if not line or line[0] == "#":
                continue
            varname, value = line.split("=", 1)
            macros[varname] = value
    except Exception:
        if cmk.ccc.debug.enabled():
            raise
    return macros


def get_ssc_host_config(
    host_name: HostName,
    host_alias: str,
    host_primary_family: Literal[socket.AddressFamily.AF_INET, socket.AddressFamily.AF_INET6],
    host_ip_stack_config: IPStackConfig,
    host_additional_addresses_ipv4: Sequence[HostAddress],
    host_additional_addresses_ipv6: Sequence[HostAddress],
    macros: Mapping[str, object],
    ip_address_of: IPLookup,
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


def make_hosts_config() -> Hosts:
    return Hosts(
        hosts=strip_tags(all_hosts),
        clusters=strip_tags(clusters),
        shadow_hosts=list(_get_shadow_hosts()),
    )


def _make_clusters_nodes_maps() -> tuple[
    Mapping[HostName, Sequence[HostName]], Mapping[HostName, Sequence[HostName]]
]:
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
        self, config_cache: ConfigCache, check_plugins: Mapping[CheckPluginName, CheckPlugin]
    ) -> None:
        self._config_cache = config_cache
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
        return service_description(
            self._config_cache.ruleset_matcher,
            self._label_manager.labels_of_host,
            host_name,
            entry.check_plugin_name,
            service_name_template=(
                None
                if (
                    p := agent_based_register.get_check_plugin(
                        entry.check_plugin_name, self._check_plugins
                    )
                )
                is None
                else p.service_name
            ),
            item=entry.item,
        )

    def service_labels(self, host_name: HostName, entry: AutocheckEntry) -> Labels:
        return self._label_manager.labels_of_service(
            host_name,
            self.service_description(host_name, entry),
            entry.service_labels,
        )


class ConfigCache:
    def __init__(self, loaded_config: LoadedConfigFragment) -> None:
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
        self.initialize()

    def initialize(self) -> ConfigCache:
        self.invalidate_host_config()

        self._check_table_cache = cache_manager.obtain_cache("check_tables")
        self._cache_section_name_of: dict[str, str] = {}
        self._host_paths: dict[HostName, str] = ConfigCache._get_host_paths(host_paths)
        self._hosttags: dict[HostName, Sequence[TagID]] = {}

        (
            self._clusters_of_cache,
            self._nodes_cache,
        ) = _make_clusters_nodes_maps()

        # TODO: remove this from the config cache. It is a completely
        # self-contained object that should be passed around (if it really
        # has to exist at all).
        self.autochecks_manager = AutochecksManager()
        self._effective_host_cache: dict[
            tuple[HostName, ServiceName, tuple[tuple[str, str], ...]],
            HostName,
        ] = {}
        self._check_mk_check_interval: dict[HostName, float] = {}

        self.hosts_config = make_hosts_config()

        tag_to_group_map = ConfigCache.get_tag_to_group_map()
        self._collect_hosttags(tag_to_group_map)

        self.ruleset_matcher = ruleset_matcher.RulesetMatcher(
            host_tags=host_tags,
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
        self.label_manager = LabelManager(
            LabelConfig(
                self.ruleset_matcher,
                host_label_rules,
                service_label_rules,
            ),
            self._nodes_cache,
            host_labels,
            get_builtin_host_labels=get_builtin_host_labels,
        )

        self.ruleset_matcher.ruleset_optimizer.set_all_processed_hosts(
            {
                hn
                for hn in set(self.hosts_config.hosts).union(self.hosts_config.clusters)
                if self.is_active(hn) and self.is_online(hn)
            }
        )
        return self

    def make_service_configurer(
        self, check_plugins: Mapping[CheckPluginName, CheckPlugin]
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
            _make_service_description_cb(
                self.ruleset_matcher, self.label_manager.labels_of_host, check_plugins
            ),
            self.effective_host,
            lambda host_name, service_name, discovered_labels: self.label_manager.labels_of_service(
                host_name, service_name, discovered_labels
            ),
        )

    def fetcher_factory(self, service_configurer: ServiceConfigurer) -> FetcherFactory:
        return FetcherFactory(self, self.ruleset_matcher, service_configurer)

    def parser_factory(self) -> ParserFactory:
        return ParserFactory(self, self.ruleset_matcher)

    def summary_config(self, host_name: HostName, source_id: str) -> SummaryConfig:
        return SummaryConfig(
            exit_spec=self.exit_code_spec(host_name, source_id),
            time_settings=self.get_piggybacked_hosts_time_settings(piggybacked_hostname=host_name),
            expect_data=self.is_piggyback_host(host_name),
        )

    def make_parent_scan_config(self, host_name: HostName) -> ParentScanConfig:
        return ParentScanConfig(
            active=self.is_active(host_name),
            online=self.is_online(host_name),
            ip_stack_config=ConfigCache.ip_stack_config(host_name),
            parents=self.parents(host_name),
        )

    def datasource_programs(self, host_name: HostName) -> Sequence[str]:
        return self.ruleset_matcher.get_host_values(
            host_name, datasource_programs, self.label_manager.labels_of_host
        )

    @staticmethod
    def get_tag_to_group_map() -> Mapping[TagID, TagGroupID]:
        tags = cmk.utils.tags.get_effective_tag_config(tag_config)
        return ruleset_matcher.get_tag_to_group_map(tags)

    def ip_lookup_config(self, host_name: HostName) -> ip_lookup.IPLookupConfig:
        return ip_lookup.IPLookupConfig(
            hostname=host_name,
            ip_stack_config=ConfigCache.ip_stack_config(host_name),
            is_snmp_host=self.computed_datasources(host_name).is_snmp,
            is_use_walk_host=self.get_snmp_backend(host_name) is SNMPBackendEnum.STORED_WALK,
            default_address_family=self.default_address_family(host_name),
            management_address=self.management_address(host_name),
            is_dyndns_host=self.is_dyndns_host(host_name),
        )

    def make_snmp_config(
        self,
        host_name: HostName,
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
                is_ipv6_primary=self.default_address_family(host_name) is socket.AF_INET6,
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
                oid_range_limits={
                    SectionName(name): rule
                    for name, rule in reversed(
                        self.ruleset_matcher.get_host_values(
                            host_name, snmp_limit_oid_range, self.label_manager.labels_of_host
                        )
                    )
                },
                snmpv3_contexts=[
                    SNMPContextConfig(
                        section=SectionName(name) if name is not None else None,
                        contexts=contexts,
                        timeout_policy=_timeout_policy(timeout_policy),
                    )
                    for name, contexts, timeout_policy in self.ruleset_matcher.get_host_values(
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
        hostname: HostName,
        *,
        selected_sections: SectionNameCollection,
    ) -> frozenset[SectionName]:
        if selected_sections is not NO_SELECTION:
            checking_sections = selected_sections
        else:
            checking_sections = frozenset(
                agent_based_register.filter_relevant_raw_sections(
                    consumers=[
                        plugins.check_plugins[n]
                        for n in self.check_table(
                            hostname,
                            plugins.check_plugins,
                            service_configurer,
                            filter_mode=FilterMode.INCLUDE_CLUSTERED,
                            skip_ignored=True,
                        ).needed_check_names()
                        if n in plugins.check_plugins
                    ],
                    sections=itertools.chain(
                        plugins.agent_sections.values(), plugins.snmp_sections.values()
                    ),
                )
            )
        return frozenset(s for s in checking_sections if s in plugins.snmp_sections)

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
        *,
        use_cache: bool = True,
        filter_mode: FilterMode = FilterMode.NONE,
        skip_ignored: bool = True,
    ) -> HostCheckTable:
        # we blissfully ignore the plugins parameter here
        cache_key = (hostname, filter_mode, skip_ignored) if use_cache else None
        if cache_key:
            with contextlib.suppress(KeyError):
                return self._check_table_cache[cache_key]

        host_check_table = HostCheckTable(
            services=_aggregate_check_table_services(
                hostname,
                config_cache=self,
                skip_ignored=skip_ignored,
                filter_mode=filter_mode,
                get_autochecks=self.autochecks_manager.get_autochecks,
                configure_autochecks=service_configurer.configure_autochecks,
                plugins=plugins,
            )
        )

        if cache_key:
            self._check_table_cache[cache_key] = host_check_table

        return host_check_table

    def _sorted_services(
        self,
        hostname: HostName,
        plugins: Mapping[CheckPluginName, CheckPlugin],
        service_configurer: ServiceConfigurer,
    ) -> Sequence[ConfiguredService]:
        # This method is only useful for the monkeypatching orgy of the "unit"-tests.
        return sorted(
            self.check_table(hostname, plugins, service_configurer).values(),
            key=lambda service: service.description,
        )

    def configured_services(
        self,
        hostname: HostName,
        plugins: Mapping[CheckPluginName, CheckPlugin],
        service_configurer: ServiceConfigurer,
    ) -> Sequence[ConfiguredService]:
        services = self._sorted_services(hostname, plugins, service_configurer)
        if is_cmc():
            return services

        unresolved = [(s, set(service_depends_on(self, hostname, s.description))) for s in services]

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

    def enforced_services_table(
        self,
        hostname: HostName,
        plugins: Mapping[CheckPluginName, CheckPlugin],
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
            return self.__enforced_services_table[hostname]

        return self.__enforced_services_table.setdefault(
            hostname,
            {
                ServiceID(check_plugin_name, item): (
                    RulesetName(checkgroup_name),
                    ConfiguredService(
                        check_plugin_name=check_plugin_name,
                        item=item,
                        description=service_description(
                            self.ruleset_matcher,
                            self.label_manager.labels_of_host,
                            hostname,
                            check_plugin_name,
                            service_name_template=(
                                None
                                if (
                                    p := agent_based_register.get_check_plugin(
                                        check_plugin_name, plugins
                                    )
                                )
                                is None
                                else p.service_name
                            ),
                            item=item,
                        ),
                        parameters=compute_enforced_service_parameters(
                            plugins, check_plugin_name, params
                        ),
                        discovered_parameters={},
                        discovered_labels={},
                        labels={},
                        is_enforced=True,
                    ),
                )
                for checkgroup_name, ruleset in static_checks.items()
                for check_plugin_name, item, params in (
                    ConfigCache._sanitize_enforced_entry(*entry)
                    for entry in reversed(
                        self.ruleset_matcher.get_host_values(
                            hostname, ruleset, self.label_manager.labels_of_host
                        )
                    )
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

    def hwsw_inventory_parameters(self, host_name: HostName) -> HWSWInventoryParameters:
        def get_hwsw_inventory_parameters() -> HWSWInventoryParameters:
            if host_name in self.hosts_config.clusters:
                return HWSWInventoryParameters.from_raw({})

            # 'get_host_values' is already cached thus we can
            # use it after every check cycle.
            if not (
                entries := self.ruleset_matcher.get_host_values(
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

    def management_address(self, host_name: HostName) -> HostAddress | None:
        if mgmt_host_address := host_attributes.get(host_name, {}).get("management_address"):
            return mgmt_host_address

        if self.default_address_family(host_name) is socket.AF_INET6:
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
        rule_settings = self.ruleset_matcher.get_host_values(
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
        aliases = self.ruleset_matcher.get_host_values(
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
        for parent_names in self.ruleset_matcher.get_host_values(
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
                values = self.ruleset_matcher.get_host_values(
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
            host_name, cmk.utils.tags.compute_datasources(ConfigCache.tags(host_name))
        )

    def is_piggyback_host(self, host_name: HostName) -> bool:
        def get_is_piggyback_host() -> bool:
            tag_groups: Final = ConfigCache.tags(host_name)
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
        return (
            ConfigCache.tags(host_name).get(TagGroupID("site"), distributed_wato_site)
            == distributed_wato_site
        )

    def is_dyndns_host(self, host_name: HostName | HostAddress) -> bool:
        return self.ruleset_matcher.get_host_bool_value(
            host_name, dyndns_hosts, self.label_manager.labels_of_host
        )

    def discovery_check_parameters(self, host_name: HostName) -> DiscoveryCheckParameters:
        """Compute the parameters for the discovery check for a host"""

        defaults = DiscoveryCheckParameters(
            commandline_only=inventory_check_interval is None,
            check_interval=int(inventory_check_interval or 0),
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

            entries = self.ruleset_matcher.get_host_values(
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
            **self.ruleset_matcher.get_host_merged_dict(
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

                entries = self.ruleset_matcher.get_host_values(
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
        host_attrs: ObjectAttributes,
        ip_address_of: IPLookup,
        passwords: Mapping[str, str],
        password_store_file: Path,
        single_plugin: str | None = None,
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
        resource_macros = get_resource_macros()
        macros = {**host_macros, **resource_macros}
        active_check_config = ActiveCheck(
            load_active_checks(raise_errors=cmk.ccc.debug.enabled()),
            host_name,
            get_ssc_host_config(
                host_name,
                self.alias(host_name),
                self.default_address_family(host_name),
                self.ip_stack_config(host_name),
                additional_addresses_ipv4,
                additional_addresses_ipv6,
                macros,
                ip_address_of,
            ),
            http_proxies,
            lambda x: get_final_service_description(
                x,
                get_service_translations(
                    self.ruleset_matcher, self.label_manager.labels_of_host, host_name
                ),
            ),
            passwords,
            password_store_file,
            ExecutableFinder(
                cmk.utils.paths.local_nagios_plugins_dir, cmk.utils.paths.nagios_plugins_dir
            ),
            ip_lookup_failed=ip_lookup.is_fallback_ip(host_attrs["address"]),
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
        return self.ruleset_matcher.get_host_values(
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
            # Previous to 1.5.0 it was not defined in which order the special agent
            # rules overwrite each other. When multiple special agents were configured
            # for a single host a "random" one was picked (depending on the iteration
            # over config.special_agents.
            # We now sort the matching special agents by their name to at least get
            # a deterministic order of the special agents.
            for agentname, ruleset in sorted(special_agents.items()):
                params = self.ruleset_matcher.get_host_values(
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
        ip_address: HostAddress | None,
        passwords: Mapping[str, str],
        password_store_file: Path,
        ip_address_of: IPLookup,
    ) -> Iterable[tuple[str, SpecialAgentCommandLine]]:
        if not (host_special_agents := self.special_agents(host_name)):
            return

        host_attrs = self.get_host_attributes(host_name, ip_address_of)
        special_agent = SpecialAgent(
            load_special_agents(raise_errors=cmk.ccc.debug.enabled()),
            host_name,
            ip_address,
            get_ssc_host_config(
                host_name,
                self.alias(host_name),
                self.default_address_family(host_name),
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
            http_proxies,
            passwords,
            password_store_file,
            ExecutableFinder(
                cmk.utils.paths.local_special_agents_dir, cmk.utils.paths.special_agents_dir
            ),
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
                        f"Config creation for special agent {agentname} failed on {host_name}: {exc}"
                    )

    def collect_passwords(self) -> Mapping[str, str]:
        # consider making the hosts an argument. Sometimes we only need one.

        def _compose_filtered_ssc_rules(
            ssc_config: Iterable[tuple[str, Sequence[RuleSpec[Mapping[str, object]]]]],
        ) -> Sequence[tuple[str, Sequence[Mapping[str, object]]]]:
            """Get _all_ configured rulesets (not only the ones matching any host)"""
            return [(name, [r["value"] for r in ruleset]) for name, ruleset in ssc_config]

        return {
            **password_store.load(password_store.password_store_path()),
            **PreprocessingResult.from_config(
                _compose_filtered_ssc_rules(active_checks.items())
            ).ad_hoc_secrets,
            **PreprocessingResult.from_config(
                _compose_filtered_ssc_rules(special_agents.items())
            ).ad_hoc_secrets,
        }

    def hostgroups(self, host_name: HostName) -> Sequence[str]:
        """Returns the list of hostgroups of this host

        If the host has no hostgroups it will be added to the default hostgroup
        (Nagios requires each host to be member of at least on group)."""

        def hostgroups_impl() -> Sequence[str]:
            groups = self.ruleset_matcher.get_host_values(
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
            for entry in self.ruleset_matcher.get_host_values(
                host_name, host_contactgroups, self.label_manager.labels_of_host
            ):
                if isinstance(entry, list):
                    folder_cgrs.append(entry)
                else:
                    cgrs.append(entry)

            # Use the match of the nearest folder, which is the first entry in the list
            if folder_cgrs:
                cgrs += folder_cgrs[0]

            if monitoring_core == "nagios" and enable_rulebased_notifications:
                cgrs.append("check-mk-notify")

            return list(set(cgrs))

        with contextlib.suppress(KeyError):
            return self.__contactgroups[host_name]

        return self.__contactgroups.setdefault(host_name, contactgroups_impl())

    def explicit_check_command(self, host_name: HostName) -> HostCheckCommand:
        def explicit_check_command_impl() -> HostCheckCommand:
            entries = self.ruleset_matcher.get_host_values(
                host_name, host_check_commands, self.label_manager.labels_of_host
            )
            if not entries:
                return None

            if entries[0] == "smart" and monitoring_core != "cmc":
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
        if ConfigCache.ip_stack_config(host_name) is IPStackConfig.NO_IP:
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
                    self.ruleset_matcher.get_host_values(
                        host_name, snmp_check_interval, self.label_manager.labels_of_host
                    )
                )
                for section_name in sections
            }

        with contextlib.suppress(KeyError):
            return self.__snmp_fetch_interval[host_name]

        return self.__snmp_fetch_interval.setdefault(host_name, snmp_fetch_interval_impl())

    def _collect_hosttags(self, tag_to_group_map: Mapping[TagID, TagGroupID]) -> None:
        """Calculate the effective tags for all configured hosts

        WATO ensures that all hosts configured with WATO have host_tags set, but there may also be hosts defined
        by the etc/check_mk/conf.d directory that are not managed by WATO. They may use the old style pipe separated
        all_hosts configuration. Detect it and try to be compatible.
        """
        for tagged_host in all_hosts + list(clusters):
            parts = tagged_host.split("|")
            hostname = parts[0]

            if hostname in host_tags:
                # New dict host_tags are available: only need to compute the tag list
                self._hosttags[hostname] = ConfigCache._tag_groups_to_tag_list(
                    self._host_paths.get(hostname, "/"), host_tags[hostname]
                )
            else:
                # Only tag list available. Use it and compute the tag groups.
                self._hosttags[hostname] = tuple(parts[1:])
                host_tags[hostname] = ConfigCache._tag_list_to_tag_groups(
                    tag_to_group_map, self._hosttags[hostname]
                )

        for shadow_host_name, shadow_host_spec in list(_get_shadow_hosts().items()):
            self._hosttags[shadow_host_name] = tuple(
                set(shadow_host_spec.get("custom_variables", {}).get("TAGS", TagID("")).split())
            )
            host_tags[shadow_host_name] = ConfigCache._tag_list_to_tag_groups(
                tag_to_group_map, self._hosttags[shadow_host_name]
            )

    @staticmethod
    def _tag_groups_to_tag_list(
        host_path: str, tag_groups: Mapping[TagGroupID, TagID]
    ) -> Sequence[TagID]:
        # The pre 1.6 tags contained only the tag group values (-> chosen tag id),
        # but there was a single tag group added with it's leading tag group id. This
        # was the internal "site" tag that is created by HostAttributeSite.
        tags = {v for k, v in tag_groups.items() if k != TagGroupID("site")}
        tags.add(TagID(host_path))
        tags.add(TagID(f"site:{tag_groups[TagGroupID('site')]}"))
        return tuple(tags)

    @staticmethod
    def _tag_list_to_tag_groups(
        tag_to_group_map: Mapping[TagID, TagGroupID], tag_list: Iterable[TagID]
    ) -> Mapping[TagGroupID, TagID]:
        # This assumes all needed aux tags of grouped are already in the tag_list

        # Ensure the internal mandatory tag groups are set for all hosts
        # TODO: This immitates the logic of cmk.gui.watolib.Host.tag_groups which
        # is currently responsible for calculating the host tags of a host.
        # Would be better to untie the GUI code there and move it over to cmk.utils.tags.
        return {
            TagGroupID("piggyback"): TagID("auto-piggyback"),
            TagGroupID("networking"): TagID("lan"),
            TagGroupID("agent"): TagID("cmk-agent"),
            TagGroupID("criticality"): TagID("prod"),
            TagGroupID("snmp_ds"): TagID("no-snmp"),
            TagGroupID("site"): TagID(omd_site()),
            TagGroupID("address_family"): TagID("ip-v4-only"),
            # Assume it's an aux tag in case there is a tag configured without known group
            **{tag_to_group_map.get(tag_id, TagGroupID(tag_id)): tag_id for tag_id in tag_list},
        }

    def tag_list(self, hostname: HostName) -> Sequence[TagID]:
        """Returns the list of all configured tags of a host. In case
        a host has no tags configured or is not known, it returns an
        empty list."""
        if hostname in self._hosttags:
            return self._hosttags[hostname]

        # Handle not existing hosts (No need to performance optimize this)
        return ConfigCache._tag_groups_to_tag_list("/", ConfigCache.tags(hostname))

    # TODO: check all call sites and remove this or make it private?
    @staticmethod
    def tags(hostname: HostName | HostAddress) -> Mapping[TagGroupID, TagID]:
        """Returns the dict of all configured tag groups and values of a host."""
        with contextlib.suppress(KeyError):
            return host_tags[hostname]

        # Handle not existing hosts (No need to performance optimize this)
        # TODO: This immitates the logic of cmk.gui.watolib.Host.tag_groups which
        # is currently responsible for calculating the host tags of a host.
        # Would be better to untie the GUI code there and move it over to cmk.utils.tags.
        return {
            TagGroupID("piggyback"): TagID("auto-piggyback"),
            TagGroupID("networking"): TagID("lan"),
            TagGroupID("agent"): TagID("cmk-agent"),
            TagGroupID("criticality"): TagID("prod"),
            TagGroupID("snmp_ds"): TagID("no-snmp"),
            TagGroupID("site"): TagID(omd_site()),
            TagGroupID("address_family"): TagID("ip-v4-only"),
        }

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
            return self.ruleset_matcher.get_host_merged_dict(
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
        specs = self.ruleset_matcher.get_host_values(
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
            for entry in self.ruleset_matcher.get_host_values(
                hostname, inv_retention_intervals, self.label_manager.labels_of_host
            )
            for raw in entry
        ]

    def service_level(self, hostname: HostName) -> int | None:
        entries = self.ruleset_matcher.get_host_values(
            hostname, host_service_levels, self.label_manager.labels_of_host
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
        if communities := self.ruleset_matcher.get_host_values(
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
            and cmk_version.edition(cmk.utils.paths.omd_root) is not cmk_version.Edition.CRE
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

        if host_backend_config := self.ruleset_matcher.get_host_values(
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
        for entry in self.ruleset_matcher.get_host_values(
            hostname, snmp_communities, self.label_manager.labels_of_host
        ):
            if snmp_version == 3 and not isinstance(entry, tuple):
                continue

            if snmp_version != 3 and isinstance(entry, tuple):
                continue

            return entry

        return None

    def _snmp_port(self, hostname: HostName) -> int:
        ports = self.ruleset_matcher.get_host_values(
            hostname, snmp_ports, self.label_manager.labels_of_host
        )
        return ports[0] if ports else 161

    def _snmp_timing(self, hostname: HostName) -> SNMPTiming:
        timing = self.ruleset_matcher.get_host_values(
            hostname, snmp_timing, self.label_manager.labels_of_host
        )
        return timing[0] if timing else {}

    def _bulk_walk_size(self, hostname: HostName) -> int:
        bulk_sizes = self.ruleset_matcher.get_host_values(
            hostname, snmp_bulk_size, self.label_manager.labels_of_host
        )
        return bulk_sizes[0] if bulk_sizes else 10

    def _snmp_character_encoding(self, hostname: HostName) -> str | None:
        entries = self.ruleset_matcher.get_host_values(
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

    def check_mk_check_interval(self, hostname: HostName) -> float:
        if (interval := self._check_mk_check_interval.get(hostname)) is not None:
            return interval

        description = "Check_MK"
        return self._check_mk_check_interval.setdefault(
            hostname,
            self.extra_attributes_of_service(
                hostname,
                description,
                self.label_manager.labels_of_service(hostname, description, discovered_labels={}),
            )["check_interval"]
            * 60,
        )

    @staticmethod
    def ip_stack_config(host_name: HostName | HostAddress) -> IPStackConfig:
        # TODO(ml): [IPv6] clarify tag_groups vs tag_groups["address_family"]
        tag_groups = ConfigCache.tags(host_name)
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
            rules = self.ruleset_matcher.get_host_values(
                hostname, primary_address_family, self.label_manager.labels_of_host
            )
            return (
                socket.AddressFamily.AF_INET6
                if rules and rules[0] == "ipv6"
                else socket.AddressFamily.AF_INET
            )

        def is_ipv6_primary() -> bool:
            # Whether or not the given host is configured to be monitored primarily via IPv6
            return ConfigCache.ip_stack_config(hostname) is IPStackConfig.IPv6 or (
                ConfigCache.ip_stack_config(hostname) is IPStackConfig.DUAL_STACK
                and primary_ip_address_family_of() is socket.AF_INET6
            )

        return socket.AddressFamily.AF_INET6 if is_ipv6_primary() else socket.AddressFamily.AF_INET

    def _has_piggyback_data(self, host_name: HostName) -> bool:
        return (
            self._host_has_piggyback_data_right_now(host_name)
            or make_persisted_section_dir(
                fetcher_type=FetcherType.PIGGYBACK,
                host_name=host_name,
                ident="piggyback",
                section_cache_path=Path(cmk.utils.paths.var_dir),
            ).exists()
        )

    def _host_has_piggyback_data_right_now(self, host_name: HostAddress) -> bool:
        # This duplicates logic and should be kept in sync with what the fetcher does.
        # Can we somehow instanciate the hypothetical fetcher here, and just let it fetch?
        piggy_config = piggyback_backend.Config(
            host_name,
            [
                *self._piggybacked_host_files(host_name),
                (None, "max_cache_age", piggyback_max_cachefile_age),
            ],
        )

        now = time.time()

        def _is_usable(data: piggyback_backend.PiggybackMessage) -> bool:
            return (now - data.meta.last_update) <= piggy_config.max_cache_age(data.meta.source)

        return any(
            map(_is_usable, piggyback_backend.get_messages_for(host_name, cmk.utils.paths.omd_root))
        )

    def _piggybacked_host_files(
        self, host_name: HostName
    ) -> piggyback_backend.PiggybackTimeSettings:
        if rules := self.ruleset_matcher.get_host_values(
            host_name, piggybacked_host_files, self.label_manager.labels_of_host
        ):
            return self._flatten_piggybacked_host_files_rule(host_name, rules[0])
        return []

    def _flatten_piggybacked_host_files_rule(
        self, host_name: HostName, rule: Mapping[str, Any]
    ) -> piggyback_backend.PiggybackTimeSettings:
        """This rule is a first match rule.

        Max cache age, validity period and state are configurable wihtin this
        rule for all piggybacked host or per piggybacked host of this source.
        In order to differentiate later for which piggybacked hosts a parameter
        is used we flatten this rule to a homogeneous data structure:
            (HOST, KEY, VALUE)
        Then piggyback.py:_get_piggyback_processed_file_info can evaluate the
        parameters generically."""
        flat_rule: list[
            tuple[
                tuple[Literal["exact_match"], str] | tuple[Literal["regular_expression"], str],
                str,
                int,
            ]
        ] = []

        max_cache_age = rule.get("global_max_cache_age")
        if max_cache_age is not None and max_cache_age != "global":
            flat_rule.append((("exact_match", host_name), "max_cache_age", max_cache_age))

        global_validity_setting = rule.get("global_validity", {})

        period = global_validity_setting.get("period")
        if period is not None:
            flat_rule.append((("exact_match", host_name), "validity_period", period))

        check_mk_state = global_validity_setting.get("check_mk_state")
        if check_mk_state is not None:
            flat_rule.append((("exact_match", host_name), "validity_state", check_mk_state))

        for setting in rule.get("per_piggybacked_host", []):
            for piggybacked_hostname_cond in setting["piggybacked_hostname_conditions"]:
                max_cache_age = setting.get("max_cache_age")
                if max_cache_age is not None and max_cache_age != "global":
                    flat_rule.append((piggybacked_hostname_cond, "max_cache_age", max_cache_age))

                validity_setting = setting.get("validity", {})
                if not validity_setting:
                    continue

                period = validity_setting.get("period")
                if period is not None:
                    flat_rule.append((piggybacked_hostname_cond, "validity_period", period))

                check_mk_state = validity_setting.get("check_mk_state")
                if check_mk_state is not None:
                    flat_rule.append((piggybacked_hostname_cond, "validity_state", check_mk_state))

        return flat_rule

    def tags_of_service(
        self, host_name: HostName, service_name: ServiceName, service_labels: Labels
    ) -> Mapping[TagGroupID, TagID]:
        """Returns the dict of all configured tags of a service
        It takes all explicitly configured tag groups into account.
        """
        return {
            TagGroupID(k): TagID(v)
            for entry in self.ruleset_matcher.service_extra_conf(
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
        attrs = {
            "check_interval": SERVICE_CHECK_INTERVAL,
        }
        for key, ruleset in extra_service_conf.items():
            values = self.ruleset_matcher.service_extra_conf(
                host_name, service_name, service_labels, ruleset, self.label_manager.labels_of_host
            )
            if not values:
                continue

            value: float = values[0]
            if value is None:
                continue

            if key == "check_interval":
                value = float(value)

            if key[0] == "_":
                key = key.upper()

            attrs[key] = value

        return attrs

    def make_extra_icon(
        self, check_ruleset_name: RuleSetName | None, params: TimespecificParameters | None
    ) -> str | None:
        # Some WATO rules might register icons on their own
        if not isinstance(params, dict):
            # Note: according to the typing this function will always return None,
            # meaning the 'icon' parameters of the 'ps' and 'services' rulesets do not do anything.
            # It seems like this last worked in 2.0.0. CMK-16562
            return None
        return str(params.get("icon")) if str(check_ruleset_name) in {"ps", "services"} else None

    def icons_and_actions_of_service(
        self,
        host_name: HostName,
        service_name: ServiceName,
        service_labels: Labels,
        extra_icon: str | None,
    ) -> list[str]:
        actions = set(
            self.ruleset_matcher.service_extra_conf(
                host_name,
                service_name,
                service_labels,
                service_icons_and_actions,
                self.label_manager.labels_of_host,
            )
        )

        if extra_icon:
            actions.add(extra_icon)

        return list(actions)

    def servicegroups_of_service(
        self, host_name: HostName, service_name: ServiceName, service_labels: Labels
    ) -> list[ServicegroupName]:
        """Returns the list of servicegroups of this service"""
        return self.ruleset_matcher.service_extra_conf(
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
        for entry in self.ruleset_matcher.service_extra_conf(
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

        if monitoring_core == "nagios":
            cgrs.add("check-mk-notify")

        return list(cgrs)

    def passive_check_period_of_service(
        self, host_name: HostName, service_name: ServiceName, service_labels: Labels
    ) -> str:
        out = self.ruleset_matcher.service_extra_conf(
            host_name,
            service_name,
            service_labels,
            check_periods,
            self.label_manager.labels_of_host,
        )
        return out[0] if out else "24X7"

    def custom_attributes_of_service(
        self, host_name: HostName, service_name: ServiceName, service_labels: Labels
    ) -> dict[str, str]:
        return dict(
            itertools.chain(
                *self.ruleset_matcher.service_extra_conf(
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
        out = self.ruleset_matcher.service_extra_conf(
            host_name,
            service_name,
            service_labels,
            service_service_levels,
            self.label_manager.labels_of_host,
        )
        return out[0] if out else None

    def check_period_of_service(
        self, host_name: HostName, service_name: ServiceName, service_labels: Labels
    ) -> TimeperiodName | None:
        out = self.ruleset_matcher.service_extra_conf(
            host_name,
            service_name,
            service_labels,
            check_periods,
            self.label_manager.labels_of_host,
        )
        return TimeperiodName(out[0]) if out and out[0] != "24X7" else None

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
        ip_address_of: IPLookup,
    ) -> ObjectAttributes:
        def _set_addresses(
            attrs: ObjectAttributes,
            addresses: list[HostAddress] | None,
            what: Literal["4", "6"],
        ) -> None:
            key_base = f"_ADDRESSES_{what}"
            if not addresses:
                # If other addresses are not available, set to empty string in order to avoid unresolved macros
                attrs[key_base] = ""
                return
            attrs[key_base] = " ".join(addresses)
            for nr, address in enumerate(addresses):
                key = f"{key_base}_{nr + 1}"
                attrs[key] = address

        attrs = self.extra_host_attributes(hostname)

        # Pre 1.6 legacy attribute. We have changed our whole code to use the
        # livestatus column "tags" which is populated by all attributes starting with
        # "__TAG_" instead. We may deprecate this is one day.
        attrs["_TAGS"] = " ".join(sorted(self.tag_list(hostname)))
        attrs.update(ConfigCache._get_tag_attributes(self.tags(hostname), "TAG"))
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

        ip_stack_config = ConfigCache.ip_stack_config(hostname)

        # Now lookup configured IP addresses
        v4address: str | None = None
        if IPStackConfig.IPv4 in ip_stack_config:
            v4address = ip_address_of(hostname, socket.AddressFamily.AF_INET)

        if v4address is None:
            v4address = ""
        attrs["_ADDRESS_4"] = v4address

        v6address: str | None = None
        if IPStackConfig.IPv6 in ip_stack_config:
            v6address = ip_address_of(hostname, socket.AddressFamily.AF_INET6)
        if v6address is None:
            v6address = ""
        attrs["_ADDRESS_6"] = v6address

        if self.default_address_family(hostname) is socket.AF_INET6:
            attrs["address"] = attrs["_ADDRESS_6"]
            attrs["_ADDRESS_FAMILY"] = "6"
        else:
            attrs["address"] = attrs["_ADDRESS_4"]
            attrs["_ADDRESS_FAMILY"] = "4"

        add_ipv4addrs, add_ipv6addrs = self.additional_ipaddresses(hostname)
        _set_addresses(attrs, add_ipv4addrs, "4")
        _set_addresses(attrs, add_ipv6addrs, "6")

        # Add the optional WATO folder path
        path = host_paths.get(hostname)
        if path:
            attrs["_FILENAME"] = path

        # Add custom user icons and actions
        actions = self.icons_and_actions(hostname)
        if actions:
            attrs["_ACTIONS"] = ",".join(actions)

        if cmk_version.edition(cmk.utils.paths.omd_root) is cmk_version.Edition.CME:
            attrs["_CUSTOMER"] = current_customer  # type: ignore[name-defined,unused-ignore]

        return attrs

    def get_cluster_attributes(
        self,
        hostname: HostName,
        nodes: Sequence[HostName],
        ip_address_of: IPLookup,
    ) -> dict:
        sorted_nodes = sorted(nodes)

        attrs = {
            "_NODENAMES": " ".join(sorted_nodes),
        }
        ip_stack_config = ConfigCache.ip_stack_config(hostname)
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

        node_ips = (
            node_ips_6 if self.default_address_family(hostname) is socket.AF_INET6 else node_ips_4
        )

        for suffix, val in [("", node_ips), ("_4", node_ips_4), ("_6", node_ips_6)]:
            attrs[f"_NODEIPS{suffix}"] = " ".join(val)

        return attrs

    def get_cluster_nodes_for_config(self, host_name: HostName) -> Sequence[HostName]:
        nodes = self.nodes(host_name)
        if not nodes:
            return ()

        self._verify_cluster_address_family(host_name, nodes)
        self._verify_cluster_datasource(host_name, nodes)
        nodes = list(nodes[:])
        active_hosts = {
            hn for hn in self.hosts_config.hosts if self.is_active(hn) and self.is_online(hn)
        }
        for node in nodes:
            if node not in active_hosts:
                config_warnings.warn(
                    f"Node '{node}' of cluster '{host_name}' is not a monitored host in this site."
                )
                nodes.remove(node)
        return nodes

    def _verify_cluster_address_family(
        self,
        host_name: HostName,
        nodes: Iterable[HostName],
    ) -> None:
        cluster_host_family = (
            "IPv6" if self.default_address_family(host_name) is socket.AF_INET6 else "IPv4"
        )
        address_families = [
            f"{host_name}: {cluster_host_family}",
        ]

        address_family = cluster_host_family
        mixed = False
        for nodename in nodes:
            family = "IPv6" if self.default_address_family(nodename) is socket.AF_INET6 else "IPv4"
            address_families.append(f"{nodename}: {family}")
            if address_family is None:
                address_family = family
            elif address_family != family:
                mixed = True

        if mixed:
            config_warnings.warn(
                f"""Cluster '{host_name}' has different primary address families: {", ".join(address_families)}"""
            )

    def _verify_cluster_datasource(
        self,
        host_name: HostName,
        nodes: Iterable[HostName],
    ) -> None:
        cluster_tg = self.tags(host_name)
        cluster_agent_ds = cluster_tg.get(TagGroupID("agent"))
        cluster_snmp_ds = cluster_tg.get(TagGroupID("snmp_ds"))
        for nodename in nodes:
            node_tg = self.tags(nodename)
            node_agent_ds = node_tg.get(TagGroupID("agent"))
            node_snmp_ds = node_tg.get(TagGroupID("snmp_ds"))
            warn_text = f"Cluster '{host_name}' has different datasources as its node"
            if node_agent_ds != cluster_agent_ds:
                config_warnings.warn(
                    f"{warn_text} '{nodename}': {cluster_agent_ds} vs. {node_agent_ds}"
                )
            if node_snmp_ds != cluster_snmp_ds:
                config_warnings.warn(
                    f"{warn_text} '{nodename}': {cluster_snmp_ds} vs. {node_snmp_ds}"
                )

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
            if isinstance(value, (numbers.Integral, float)):
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

    def translate_commandline(
        self,
        host_name: HostName,
        ip_address: HostAddress | None,
        template: str,
        ip_address_of: IPLookup,
    ) -> str:
        def _translate_host_macros(cmd: str) -> str:
            attrs = self.get_host_attributes(host_name, ip_address_of)
            if host_name in self.hosts_config.clusters:
                # TODO(ml): What is the difference between this and `self.parents()`?
                parents_list = self.get_cluster_nodes_for_config(host_name)
                attrs.setdefault("alias", f"cluster of {', '.join(parents_list)}")
                attrs.update(
                    self.get_cluster_attributes(
                        host_name,
                        parents_list,
                        ip_address_of,
                    )
                )

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
            ignored = self.ruleset_matcher.get_host_values(
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

        cluster_mapping = self.ruleset_matcher.service_extra_conf(
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
        matching_rules = self.ruleset_matcher.service_extra_conf(
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

    def get_piggybacked_hosts_time_settings(
        self, piggybacked_hostname: HostName | None = None
    ) -> piggyback_backend.PiggybackTimeSettings:
        all_sources = piggyback_backend.get_piggybacked_host_with_sources(
            cmk.utils.paths.omd_root, piggybacked_hostname
        )
        used_sources = (
            {m.source for sources in all_sources.values() for m in sources}
            if piggybacked_hostname is None
            else {m.source for m in all_sources.get(piggybacked_hostname, [])}
        )

        return [
            *(
                setting
                for source in sorted(used_sources)
                for setting in self._piggybacked_host_files(source)
            ),
            # From global settings
            (None, "max_cache_age", piggyback_max_cachefile_age),
        ]

    def get_definitive_piggybacked_data_expiry_age(self) -> float:
        """Get the interval after which we definitively can get rid of piggybacked data."""
        return max(
            (
                value
                for _, key, value in self.get_piggybacked_hosts_time_settings()
                if key in {"max_cache_age", "validity_period"}
            )
        )

    # TODO: Remove old name one day
    @staticmethod
    def service_discovery_name() -> ServiceName:
        if "cmk_inventory" in use_new_descriptions_for:
            return "Check_MK Discovery"
        return "Check_MK inventory"

    def agent_exclude_sections(self, host_name: HostName) -> dict[str, str]:
        settings = self.ruleset_matcher.get_host_values(
            host_name, agent_exclude_sections, self.label_manager.labels_of_host
        )
        return settings[0] if settings else {}

    def only_from(self, host_name: HostName) -> None | list[str] | str:
        """The agent of a host may be configured to be accessible only from specific IPs"""
        ruleset = agent_config.get("only_from", [])
        if not ruleset:
            return None

        entries = self.ruleset_matcher.get_host_values(
            host_name, ruleset, self.label_manager.labels_of_host
        )
        return entries[0] if entries else None

    def ping_levels(self, host_name: HostName) -> PingLevels:
        levels: PingLevels = {}

        values = self.ruleset_matcher.get_host_values(
            host_name, ping_levels, self.label_manager.labels_of_host
        )
        # TODO: Use get_host_merged_dict?)
        for value in values[::-1]:  # make first rules have precedence
            levels.update(value)

        return levels

    def icons_and_actions(self, host_name: HostName) -> list[str]:
        return list(
            set(
                self.ruleset_matcher.get_host_values(
                    host_name, host_icons_and_actions, self.label_manager.labels_of_host
                )
            )
        )


def access_globally_cached_config_cache() -> ConfigCache:
    """Get the global config cache"""
    return cache_manager.obtain_cache("config_cache")["cache"]


def _globally_cache_config_cache(config_cache: ConfigCache) -> None:
    """Create a new ConfigCache and set it in the cache manager"""
    cache_manager.obtain_cache("config_cache")["cache"] = config_cache


def _create_config_cache(loaded_config: LoadedConfigFragment) -> ConfigCache:
    """create clean config cache"""
    if cmk_version.edition(cmk.utils.paths.omd_root) is cmk_version.Edition.CRE:
        return ConfigCache(loaded_config)
    if cmk_version.edition(cmk.utils.paths.omd_root) is cmk_version.Edition.CME:
        return CMEConfigCache(loaded_config)
    return CEEConfigCache(loaded_config)


# TODO(au): Find a way to retreive the matchtype_information directly from the
# rulespecs. This is not possible atm because they live in cmk.gui
class _Matchtype(Enum):
    LIST = "list"
    FIRST = "first"
    DICT = "dict"
    ALL = "all"


_BAKERY_PLUGINS_WITH_SPECIAL_MATCHTYPES = {
    "agent_paths": _Matchtype.DICT,
    "cmk_update_agent": _Matchtype.DICT,
    "custom_files": _Matchtype.LIST,
    "fileinfo": _Matchtype.LIST,
    "logging": _Matchtype.DICT,
    "lnx_remote_alert_handlers": _Matchtype.ALL,
    "mk_logwatch": _Matchtype.ALL,
    "mk_filestats": _Matchtype.DICT,
    "mk_oracle": _Matchtype.DICT,
    "mrpe": _Matchtype.LIST,
    "bakery_packages": _Matchtype.DICT,
    "real_time_checks": _Matchtype.DICT,
    "runas": _Matchtype.LIST,
    "win_script_cache_age": _Matchtype.ALL,
    "win_script_execution": _Matchtype.ALL,
    "win_script_retry_count": _Matchtype.ALL,
    "win_script_runas": _Matchtype.ALL,
    "win_script_timeout": _Matchtype.ALL,
    "unix_plugins_cache_age": _Matchtype.ALL,
}


def boil_down_agent_rules(
    *, defaults: Mapping[str, Any], rulesets: Mapping[str, Any]
) -> Mapping[str, Any]:
    boiled_down = {**defaults}

    # TODO: Better move whole computation to cmk.base.config for making
    # ruleset matching transparent
    for varname, entries in rulesets.items():
        if not entries:
            continue

        if (
            len(entries) > 0
            and isinstance(first_entry := entries[0], dict)
            and (cmk_match_type := first_entry.get("cmk-match-type", None)) is not None
        ):
            # new Ruleset API will use merge as default match_type
            match_type = _Matchtype(cmk_match_type)
        else:
            match_type = _BAKERY_PLUGINS_WITH_SPECIAL_MATCHTYPES.get(varname, _Matchtype.FIRST)

        if match_type is _Matchtype.FIRST:
            boiled_down[varname] = entries[0]
        elif match_type is _Matchtype.LIST:
            boiled_down[varname] = [it for entry in entries for it in entry]
        elif match_type is _Matchtype.DICT:
            # Watch out! In this case we have to merge all rules on top of the defaults!
            # Compare #14868
            boiled_down[varname] = {
                **defaults.get(varname, {}),
                **{
                    k: v
                    for entry in entries[::-1]
                    for k, v in entry.items()
                    if k != "cmk-match-type"
                },
            }
        elif match_type is _Matchtype.ALL:
            boiled_down[varname] = entries
        else:
            assert_never(match_type)

    return boiled_down


class ParserFactory:
    # TODO: better and clearer separation between ConfigCache and this class.
    def __init__(self, config_cache: ConfigCache, ruleset_matcher_: RulesetMatcher) -> None:
        self._config_cache: Final = config_cache
        self._label_manager: Final = config_cache.label_manager
        self._ruleset_matcher: Final = ruleset_matcher_

    def make_agent_parser(
        self,
        host_name: HostName,
        section_store: SectionStore[Sequence[AgentRawDataSectionElem]],
        *,
        keep_outdated: bool,
        logger: logging.Logger,
    ) -> AgentParser:
        return AgentParser(
            host_name,
            section_store,
            keep_outdated=keep_outdated,
            host_check_interval=self._config_cache.check_mk_check_interval(host_name),
            translation=get_piggyback_translations(
                self._ruleset_matcher, self._label_manager.labels_of_host, host_name
            ),
            encoding_fallback=fallback_agent_output_encoding,
            logger=logger,
        )

    def make_snmp_parser(
        self,
        host_name: HostName,
        section_store: SectionStore[SNMPRawDataElem],
        *,
        keep_outdated: bool,
        logger: logging.Logger,
    ) -> SNMPParser:
        return SNMPParser(
            host_name,
            section_store,
            persist_periods=self._config_cache.snmp_fetch_intervals(host_name),
            host_check_interval=self._config_cache.check_mk_check_interval(host_name),
            keep_outdated=keep_outdated,
            logger=logger,
        )


class FetcherFactory:
    # TODO: better and clearer separation between ConfigCache and this class.
    def __init__(
        self,
        config_cache: ConfigCache,
        ruleset_matcher_: RulesetMatcher,
        service_configurer: ServiceConfigurer,
    ) -> None:
        self._config_cache: Final = config_cache
        self._label_manager: Final = config_cache.label_manager
        self._ruleset_matcher: Final = ruleset_matcher_
        self._service_configurer: Final = service_configurer
        self.__disabled_snmp_sections: dict[HostName, frozenset[SectionName]] = {}

    def clear(self) -> None:
        self.__disabled_snmp_sections.clear()

    def _disabled_snmp_sections(self, host_name: HostName) -> frozenset[SectionName]:
        def disabled_snmp_sections_impl() -> frozenset[SectionName]:
            """Return a set of disabled snmp sections"""
            rules = self._ruleset_matcher.get_host_values(
                host_name, snmp_exclude_sections, self._label_manager.labels_of_host
            )
            merged_section_settings = {"if64adm": True}
            for rule in reversed(rules):
                for section in rule.get("sections_enabled", ()):
                    merged_section_settings[section] = False
                for section in rule.get("sections_disabled", ()):
                    merged_section_settings[section] = True

            return frozenset(
                SectionName(name)
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
        checking_sections: frozenset[SectionName],
        sections: Iterable[SNMPSectionPlugin],
    ) -> dict[SectionName, SNMPSectionMeta]:
        disabled_sections = self._disabled_snmp_sections(host_name)
        redetect_sections = agent_based_register.sections_needing_redetection(sections)
        return {
            name: SNMPSectionMeta(
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
        ip_address: HostAddress,
        *,
        source_type: SourceType,
        fetcher_config: SNMPFetcherConfig,
    ) -> SNMPFetcher:
        snmp_config = self._config_cache.make_snmp_config(
            host_name,
            ip_address,
            source_type,
            backend_override=fetcher_config.backend_override,
        )
        return SNMPFetcher(
            sections=self._make_snmp_sections(
                host_name,
                checking_sections=self._config_cache.make_checking_sections(
                    plugins,
                    self._service_configurer,
                    host_name,
                    selected_sections=fetcher_config.selected_sections,
                ),
                sections=plugins.snmp_sections.values(),
            ),
            scan_config=fetcher_config.scan_config,
            do_status_data_inventory=self._config_cache.hwsw_inventory_parameters(
                host_name
            ).status_data_inventory,
            section_store_path=make_persisted_section_dir(
                host_name,
                fetcher_type=FetcherType.SNMP,
                ident="snmp",
                section_cache_path=Path(cmk.utils.paths.var_dir),
            ),
            snmp_config=snmp_config,
            stored_walk_path=fetcher_config.stored_walk_path,
            walk_cache_path=fetcher_config.walk_cache_path,
        )

    def _agent_port(self, host_name: HostName) -> int:
        ports = self._ruleset_matcher.get_host_values(
            host_name, agent_ports, self._label_manager.labels_of_host
        )
        return ports[0] if ports else agent_port

    def _tcp_connect_timeout(self, host_name: HostName) -> float:
        timeouts = self._ruleset_matcher.get_host_values(
            host_name, tcp_connect_timeouts, self._label_manager.labels_of_host
        )
        return timeouts[0] if timeouts else tcp_connect_timeout

    def _encryption_handling(self, host_name: HostName) -> TCPEncryptionHandling:
        if not (
            settings := self._ruleset_matcher.get_host_values(
                host_name, encryption_handling, self._label_manager.labels_of_host
            )
        ):
            return TCPEncryptionHandling.ANY_AND_PLAIN
        match settings[0]["accept"]:
            case "tls_encrypted_only":
                return TCPEncryptionHandling.TLS_ENCRYPTED_ONLY
            case "any_encrypted":
                return TCPEncryptionHandling.ANY_ENCRYPTED
            case "any_and_plain":
                return TCPEncryptionHandling.ANY_AND_PLAIN
        raise ValueError("Unknown setting: %r" % settings[0])

    def _symmetric_agent_encryption(self, host_name: HostName) -> str | None:
        return (
            settings[0]
            if (
                settings := self._ruleset_matcher.get_host_values(
                    host_name, agent_encryption, self._label_manager.labels_of_host
                )
            )
            else None
        )

    def make_tcp_fetcher(
        self,
        host_name: HostName,
        ip_address: HostAddress,
        *,
        tls_config: TLSConfig,
    ) -> TCPFetcher:
        return TCPFetcher(
            host_name=host_name,
            address=(ip_address, self._agent_port(host_name)),
            family=self._config_cache.default_address_family(host_name),
            timeout=self._tcp_connect_timeout(host_name),
            encryption_handling=self._encryption_handling(host_name),
            pre_shared_secret=self._symmetric_agent_encryption(host_name),
            tls_config=tls_config,
        )

    def make_ipmi_fetcher(self, host_name: HostName, ip_address: HostAddress) -> IPMIFetcher:
        ipmi_credentials = self._config_cache.management_credentials(host_name, "ipmi")
        return IPMIFetcher(
            address=ip_address,
            username=ipmi_credentials.get("username"),
            password=ipmi_credentials.get("password"),
        )

    def _make_program_commandline(
        self,
        host_name: HostName,
        ip_address: HostAddress | None,
        ip_address_of: IPLookup,
        program: str,
    ) -> str:
        return self._config_cache.translate_commandline(
            host_name, ip_address, program, ip_address_of
        )

    def make_program_fetcher(
        self,
        host_name: HostName,
        ip_address: HostAddress | None,
        *,
        program: str,
        stdin: str | None,
    ) -> ProgramFetcher:
        cmdline = self._make_program_commandline(
            host_name,
            ip_address,
            ConfiguredIPLookup(self._config_cache, error_handler=handle_ip_lookup_failure),
            program,
        )
        return ProgramFetcher(cmdline=cmdline, stdin=stdin, is_cmc=is_cmc())

    def make_special_agent_fetcher(self, *, cmdline: str, stdin: str | None) -> ProgramFetcher:
        return ProgramFetcher(cmdline=cmdline, stdin=stdin, is_cmc=is_cmc())

    def make_piggyback_fetcher(
        self, host_name: HostName, ip_address: HostAddress | None
    ) -> PiggybackFetcher:
        return PiggybackFetcher(
            hostname=host_name,
            address=ip_address,
            time_settings=self._config_cache.get_piggybacked_hosts_time_settings(
                piggybacked_hostname=host_name
            ),
        )


class CEEConfigCache(ConfigCache):
    def __init__(self, loaded_config: LoadedConfigFragment) -> None:
        self.__rrd_config: dict[HostName, RRDObjectConfig | None] = {}
        self.__recuring_downtimes: dict[HostName, Sequence[RecurringDowntime]] = {}
        self.__flap_settings: dict[HostName, tuple[float, float, float]] = {}
        self.__log_long_output: dict[HostName, bool] = {}
        self.__state_translation: dict[HostName, dict] = {}
        self.__smartping_settings: dict[HostName, dict] = {}
        self.__lnx_remote_alert_handlers: dict[HostName, Sequence[Mapping[str, str]]] = {}
        self.__rtc_secret: dict[HostName, str | None] = {}
        self.__agent_config: dict[HostName, Mapping[str, Any]] = {}
        super().__init__(loaded_config)

    def invalidate_host_config(self) -> None:
        super().invalidate_host_config()
        self.__rrd_config.clear()
        self.__recuring_downtimes.clear()
        self.__flap_settings.clear()
        self.__log_long_output.clear()
        self.__state_translation.clear()
        self.__smartping_settings.clear()
        self.__lnx_remote_alert_handlers.clear()
        self.__rtc_secret.clear()
        self.__agent_config.clear()

    def cmc_log_rrdcreation(self) -> Literal["terse", "full"] | None:
        return cmc_log_rrdcreation

    def rrd_config(self, host_name: HostName) -> RRDObjectConfig | None:
        def _rrd_config() -> RRDObjectConfig | None:
            entries = self.ruleset_matcher.get_host_values(
                host_name, cmc_host_rrd_config, self.label_manager.labels_of_host
            )
            return entries[0] if entries else None

        with contextlib.suppress(KeyError):
            return self.__rrd_config[host_name]

        return self.__rrd_config.setdefault(host_name, _rrd_config())

    def recurring_downtimes(self, host_name: HostName) -> Sequence[RecurringDowntime]:
        def _impl() -> Sequence[RecurringDowntime]:
            return self.ruleset_matcher.get_host_values(
                host_name,
                host_recurring_downtimes,  # type: ignore[name-defined,unused-ignore]
                self.label_manager.labels_of_host,
            )

        with contextlib.suppress(KeyError):
            return self.__recuring_downtimes[host_name]

        return self.__recuring_downtimes.setdefault(host_name, _impl())

    def flap_settings(self, host_name: HostName) -> tuple[float, float, float]:
        def _impl() -> tuple[float, float, float]:
            values = self.ruleset_matcher.get_host_values(
                host_name,
                cmc_host_flap_settings,  # type: ignore[name-defined,unused-ignore]
                self.label_manager.labels_of_host,
            )
            return (
                values[0] if values else cmc_flap_settings  # type: ignore[name-defined,unused-ignore]
            )

        with contextlib.suppress(KeyError):
            return self.__flap_settings[host_name]

        return self.__flap_settings.setdefault(host_name, _impl())

    def log_long_output(self, host_name: HostName) -> bool:
        def _impl() -> bool:
            entries = self.ruleset_matcher.get_host_values(
                host_name,
                cmc_host_long_output_in_monitoring_history,  # type: ignore[name-defined,unused-ignore]
                self.label_manager.labels_of_host,
            )
            return entries[0] if entries else False

        with contextlib.suppress(KeyError):
            return self.__log_long_output[host_name]

        return self.__log_long_output.setdefault(host_name, _impl())

    def state_translation(self, host_name: HostName) -> dict:
        def _impl() -> dict:
            entries = self.ruleset_matcher.get_host_values(
                host_name,
                host_state_translation,  # type: ignore[name-defined,unused-ignore]
                self.label_manager.labels_of_host,
            )

            spec: dict[object, object] = {}
            for entry in entries[::-1]:
                spec |= entry
            return spec

        with contextlib.suppress(KeyError):
            return self.__state_translation[host_name]

        return self.__state_translation.setdefault(host_name, _impl())

    def smartping_settings(self, host_name: HostName) -> dict:
        def _impl() -> dict:
            settings = {"timeout": 2.5}
            settings |= self.ruleset_matcher.get_host_merged_dict(
                host_name,
                cmc_smartping_settings,  # type: ignore[name-defined,unused-ignore]
                self.label_manager.labels_of_host,
            )
            return settings

        with contextlib.suppress(KeyError):
            return self.__smartping_settings[host_name]

        return self.__smartping_settings.setdefault(host_name, _impl())

    def lnx_remote_alert_handlers(self, host_name: HostName) -> Sequence[Mapping[str, str]]:
        def _impl() -> Sequence[Mapping[str, str]]:
            default: Sequence[RuleSpec[Mapping[str, str]]] = []
            return self.ruleset_matcher.get_host_values(
                host_name,
                agent_config.get("lnx_remote_alert_handlers", default),
                self.label_manager.labels_of_host,
            )

        with contextlib.suppress(KeyError):
            return self.__lnx_remote_alert_handlers[host_name]

        return self.__lnx_remote_alert_handlers.setdefault(host_name, _impl())

    def rtc_secret(self, host_name: HostName) -> str | None:
        def _impl() -> str | None:
            default: Sequence[RuleSpec[object]] = []
            if not (
                settings := self.ruleset_matcher.get_host_values(
                    host_name,
                    agent_config.get("real_time_checks", default),
                    self.label_manager.labels_of_host,
                )
            ):
                return None
            match settings[0]["encryption"]:
                case ("disabled", None):
                    return None
                case ("enabled", password_spec):
                    return password_store.extract(password_spec)
                case unknown_value:
                    raise ValueError(unknown_value)

        with contextlib.suppress(KeyError):
            return self.__rtc_secret[host_name]

        return self.__rtc_secret.setdefault(host_name, _impl())

    @staticmethod
    def cmc_real_time_checks() -> object:
        return cmc_real_time_checks  # type: ignore[name-defined,unused-ignore]

    def agent_config(self, host_name: HostName, default: Mapping[str, Any]) -> Mapping[str, Any]:
        def _impl() -> Mapping[str, Any]:
            return {
                **boil_down_agent_rules(
                    defaults=default,
                    rulesets=self.matched_agent_config_entries(host_name),
                ),
                "is_ipv6_primary": (self.default_address_family(host_name) is socket.AF_INET6),
            }

        with contextlib.suppress(KeyError):
            return self.__agent_config[host_name]

        return self.__agent_config.setdefault(host_name, _impl())

    def rrd_config_of_service(
        self, host_name: HostName, service_name: ServiceName
    ) -> RRDObjectConfig | None:
        out = self.ruleset_matcher.service_extra_conf(
            host_name,
            service_name,
            self.label_manager.labels_of_service(host_name, service_name, {}),
            cmc_service_rrd_config,
            self.label_manager.labels_of_host,
        )
        return out[0] if out else None

    def recurring_downtimes_of_service(
        self, host_name: HostName, service_name: ServiceName, service_labels: Labels
    ) -> list[RecurringDowntime]:
        return self.ruleset_matcher.service_extra_conf(
            host_name,
            service_name,
            service_labels,
            service_recurring_downtimes,  # type: ignore[name-defined,unused-ignore]
            self.label_manager.labels_of_host,
        )

    def flap_settings_of_service(
        self, host_name: HostName, service_name: ServiceName, service_labels: Labels
    ) -> tuple[float, float, float]:
        out = self.ruleset_matcher.service_extra_conf(
            host_name,
            service_name,
            service_labels,
            cmc_service_flap_settings,  # type: ignore[name-defined,unused-ignore]
            self.label_manager.labels_of_host,
        )
        return out[0] if out else cmc_flap_settings  # type: ignore[name-defined,unused-ignore]

    def log_long_output_of_service(
        self, host_name: HostName, service_name: ServiceName, service_labels: Labels
    ) -> bool:
        out = self.ruleset_matcher.service_extra_conf(
            host_name,
            service_name,
            service_labels,
            cmc_service_long_output_in_monitoring_history,  # type: ignore[name-defined,unused-ignore]
            self.label_manager.labels_of_host,
        )
        return out[0] if out else False

    def state_translation_of_service(
        self, host_name: HostName, service_name: ServiceName, service_labels: Labels
    ) -> dict:
        entries = self.ruleset_matcher.service_extra_conf(
            host_name,
            service_name,
            service_labels,
            service_state_translation,  # type: ignore[name-defined,unused-ignore]
            self.label_manager.labels_of_host,
        )

        spec: dict = {}
        for entry in entries[::-1]:
            spec |= entry
        return spec

    def check_timeout_of_service(
        self, host_name: HostName, service_name: ServiceName, service_labels: Labels
    ) -> int:
        """Returns the check timeout in seconds"""
        out = self.ruleset_matcher.service_extra_conf(
            host_name,
            service_name,
            service_labels,
            cmc_service_check_timeout,  # type: ignore[name-defined,unused-ignore]
            self.label_manager.labels_of_host,
        )
        return out[0] if out else cmc_check_timeout  # type: ignore[name-defined,unused-ignore]

    def graphite_metrics_of_host(
        self,
        host_name: HostName,
    ) -> Sequence[str] | None:
        out = self.ruleset_matcher.get_host_values(
            host_name,
            cmc_graphite_host_metrics,  # type: ignore[name-defined,unused-ignore]
            self.label_manager.labels_of_host,
        )
        return out[0] if out else None

    def graphite_metrics_of_service(
        self,
        host_name: HostName,
        service_name: ServiceName,
        service_labels: Labels,
    ) -> Sequence[str] | None:
        out = self.ruleset_matcher.service_extra_conf(
            host_name,
            service_name,
            service_labels,
            cmc_graphite_service_metrics,  # type: ignore[name-defined,unused-ignore]
            self.label_manager.labels_of_host,
        )
        return out[0] if out else None

    def influxdb_metrics_of_service(
        self,
        host_name: HostName,
        service_name: ServiceName,
        service_labels: Labels,
    ) -> Mapping[str, Any] | None:
        out = self.ruleset_matcher.service_extra_conf(
            host_name,
            service_name,
            service_labels,
            cmc_influxdb_service_metrics,  # type: ignore[name-defined,unused-ignore]
            self.label_manager.labels_of_host,
        )
        return out[0] if out else None

    def matched_agent_config_entries(self, hostname: HostName) -> dict[str, Any]:
        return {
            varname: self.ruleset_matcher.get_host_values(
                hostname, ruleset, self.label_manager.labels_of_host
            )
            for varname, ruleset in CEEConfigCache._agent_config_rulesets()
        }

    @staticmethod
    def generic_agent_config_entries(
        *, defaults: Mapping[str, object]
    ) -> Iterable[tuple[str, Mapping[str, object]]]:
        yield from (
            (
                match_path,
                boil_down_agent_rules(
                    defaults=defaults,
                    rulesets={
                        varname: CEEConfigCache._get_values_for_generic_agent(ruleset, match_path)
                        for varname, ruleset in CEEConfigCache._agent_config_rulesets()
                    },
                ),
            )
            for match_path, attributes in folder_attributes.items()
            if attributes.get("bake_agent_package", False)
        )

    @staticmethod
    def _get_values_for_generic_agent(
        ruleset: Iterable[RuleSpec[tuple[str, Any]]], path_for_rule_matching: str
    ) -> Sequence[tuple[str, Any]]:
        """Compute rulesets for "generic" hosts

        This fictious host has no name and no tags.
        It matches all rules that do not require specific hosts or tags.
        It matches rules that e.g. except specific hosts or tags (is not, has not set).
        """
        entries: list[tuple[str, Any]] = []
        for rule in ruleset:
            if ruleset_matcher.is_disabled(rule):
                continue

            rule_path = (cond := rule["condition"]).get("host_folder")
            if rule_path is not None and not path_for_rule_matching.startswith(rule_path):
                continue

            if (tags := cond.get("host_tags", {})) and not ruleset_matcher.matches_host_tags(
                set(), tags
            ):
                continue

            if (
                label_groups := cond.get("host_label_groups", [])
            ) and not ruleset_matcher.matches_labels({}, label_groups):
                continue

            if not ruleset_matcher.matches_host_name(cond.get("host_name"), HostName("")):
                continue

            entries.append(rule["value"])

        return entries

    @staticmethod
    def _agent_config_rulesets() -> Iterable[tuple[str, Any]]:
        return list(agent_config.items()) + [
            ("agent_port", agent_ports),
            ("agent_encryption", agent_encryption),
            ("agent_exclude_sections", agent_exclude_sections),
        ]


class CMEConfigCache(CEEConfigCache):
    pass
