#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

import ast
import contextlib
import copy
import ipaddress
import itertools
import logging
import marshal
import numbers
import os
import pickle
import py_compile
import shlex
import socket
import struct
import sys
import types
from collections import Counter, OrderedDict
from collections.abc import (
    Callable,
    Container,
    Iterable,
    Iterator,
    Mapping,
    MutableMapping,
    Sequence,
)
from enum import Enum
from importlib.util import MAGIC_NUMBER as _MAGIC_NUMBER
from pathlib import Path
from typing import Any, AnyStr, Final, Literal, NamedTuple, overload, Protocol, TypedDict, Union

from typing_extensions import assert_never

import cmk.utils
import cmk.utils.check_utils
import cmk.utils.cleanup
import cmk.utils.config_path
import cmk.utils.config_warnings as config_warnings
import cmk.utils.debug
import cmk.utils.migrated_check_variables
import cmk.utils.password_store as password_store
import cmk.utils.paths
import cmk.utils.piggyback as piggyback
import cmk.utils.rulesets.ruleset_matcher as ruleset_matcher
import cmk.utils.rulesets.tuple_rulesets as tuple_rulesets
import cmk.utils.store as store
import cmk.utils.store.host_storage
import cmk.utils.tags
import cmk.utils.translations
import cmk.utils.version as cmk_version
from cmk.utils.agent_registration import connection_mode_from_host_config
from cmk.utils.caching import config_cache as _config_cache
from cmk.utils.check_utils import maincheckify, section_name_of, unwrap_parameters
from cmk.utils.config_path import ConfigPath
from cmk.utils.exceptions import MKGeneralException, MKIPAddressLookupError, MKTerminate, OnError
from cmk.utils.http_proxy_config import http_proxy_config_from_user_setting, HTTPProxyConfig
from cmk.utils.labels import Labels
from cmk.utils.log import console
from cmk.utils.macros import replace_macros_in_str
from cmk.utils.parameters import TimespecificParameters, TimespecificParameterSet
from cmk.utils.regex import regex
from cmk.utils.rulesets.ruleset_matcher import (
    LabelManager,
    LabelSources,
    RulesetMatchObject,
    RulesetName,
    RuleSpec,
    TagIDToTaggroupID,
)
from cmk.utils.site import omd_site
from cmk.utils.store.host_storage import apply_hosts_file_to_object, get_host_storage_loaders
from cmk.utils.structured_data import RawIntervalsFromConfig
from cmk.utils.tags import ComputedDataSources, TaggroupIDToTagID, TagID
from cmk.utils.type_defs import (
    ActiveCheckPluginName,
    AgentTargetVersion,
    CheckPluginName,
    CheckPluginNameStr,
    CheckVariables,
    ClusterMode,
    ContactgroupName,
    ExitSpec,
    HostAddress,
    HostAgentConnectionMode,
    HostgroupName,
    HostName,
    HWSWInventoryParameters,
    IPMICredentials,
    Item,
    RuleSetName,
    Seconds,
    SectionName,
    ServicegroupName,
    ServiceID,
    ServiceName,
    TimeperiodName,
)

from cmk.snmplib.type_defs import (  # these are required in the modules' namespace to load the configuration!
    SNMPBackendEnum,
    SNMPCredentials,
    SNMPHostConfig,
    SNMPScanFunction,
    SNMPTiming,
)

from cmk.fetchers import (
    FetcherType,
    IPMIFetcher,
    PiggybackFetcher,
    SNMPFetcher,
    SNMPSectionMeta,
    TCPEncryptionHandling,
    TCPFetcher,
)
from cmk.fetchers.cache import SectionStore
from cmk.fetchers.config import make_persisted_section_dir
from cmk.fetchers.filecache import MaxAge

from cmk.checkers import AgentParser, PHostLabelDiscoveryPlugin, PInventoryPlugin, SourceType
from cmk.checkers.check_table import (
    ConfiguredService,
    FilterMode,
    HostCheckTable,
    LegacyCheckParameters,
)
from cmk.checkers.discovery import AutocheckServiceWithNodes
from cmk.checkers.type_defs import AgentRawDataSection, NO_SELECTION, SectionNameCollection

import cmk.base._autochecks as autochecks
import cmk.base.api.agent_based.register as agent_based_register
import cmk.base.default_config as default_config
import cmk.base.ip_lookup as ip_lookup
from cmk.base._autochecks import AutochecksManager
from cmk.base.api.agent_based.checking_classes import CheckPlugin
from cmk.base.api.agent_based.register.check_plugins_legacy import create_check_plugin_from_legacy
from cmk.base.api.agent_based.register.section_plugins_legacy import (
    create_agent_section_plugin_from_legacy,
    create_snmp_section_plugin_from_legacy,
)
from cmk.base.api.agent_based.type_defs import Parameters, ParametersTypeAlias, SNMPSectionPlugin
from cmk.base.default_config import *  # pylint: disable=wildcard-import,unused-wildcard-import
from cmk.base.ip_lookup import AddressFamily

TagIDs = set[TagID]

# TODO: Prefix helper functions with "_".

# Default values for retry and check intervals in minutes
# Hosts. Check and retry intervals are same
SMARTPING_CHECK_INTERVAL: Final = 0.1
HOST_CHECK_INTERVAL: Final = 1.0
# Services. Check and retry intervals may differ
SERVICE_RETRY_INTERVAL: Final = 1.0
SERVICE_CHECK_INTERVAL: Final = 1.0

service_service_levels = []
host_service_levels = []

AllHosts = list[HostName]
ShadowHosts = dict[HostName, dict]
AllClusters = dict[HostName, list[HostName]]

ObjectMacros = dict[str, AnyStr]

CheckCommandArguments = Iterable[Union[int, float, str, tuple[str, str, str]]]


class IgnoredServices(Container[ServiceName]):
    def __init__(self, config_cache: ConfigCache, host_name: HostName) -> None:
        self._config_cache = config_cache
        self._host_name = host_name

    def __contains__(self, _item: object) -> bool:
        if not isinstance(_item, ServiceName):
            return False
        return self._config_cache.service_ignored(self._host_name, _item)


def _aggregate_check_table_services(
    host_name: HostName,
    *,
    config_cache: ConfigCache,
    skip_autochecks: bool,
    skip_ignored: bool,
    filter_mode: FilterMode,
) -> Iterable[ConfiguredService]:
    sfilter = _ServiceFilter(
        host_name,
        config_cache=config_cache,
        mode=filter_mode,
        skip_ignored=skip_ignored,
    )

    # process all entries that are specific to the host
    # in search (single host) or that might match the host.
    if not (skip_autochecks or config_cache.is_ping_host(host_name)):
        yield from (s for s in config_cache.get_autochecks_of(host_name) if sfilter.keep(s))

    # Now add checks a cluster might receive from its nodes
    if config_cache.is_cluster(host_name):
        yield from (
            s
            for s in _get_clustered_services(config_cache, host_name, skip_autochecks)
            if sfilter.keep(s)
        )

    yield from (s for s in _get_enforced_services(config_cache, host_name) if sfilter.keep(s))

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
        for s in _get_services_from_cluster_nodes(config_cache, host_name)
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
        FilterMode.ONLY_CLUSTERED    -> returns only checks belonging to clusters
        FilterMode.INCLUDE_CLUSTERED -> returns checks of own host, including clustered checks
        """
        self._host_name = host_name
        self._config_cache = config_cache
        self._mode = mode
        self._skip_ignored = skip_ignored

    def keep(self, service: ConfiguredService) -> bool:
        if self._skip_ignored and (
            self._config_cache.check_plugin_ignored(self._host_name, service.check_plugin_name)
            or self._config_cache.service_ignored(self._host_name, service.description)
        ):
            return False

        if self._mode is FilterMode.INCLUDE_CLUSTERED:
            return True

        if not self._config_cache.clusters_of(self._host_name):
            return self._mode is not FilterMode.ONLY_CLUSTERED

        svc_is_mine = self.is_mine(service)

        if self._mode is FilterMode.NONE:
            return svc_is_mine

        # self._mode is FilterMode.ONLY_CLUSTERED
        return not svc_is_mine

    def is_mine(self, service: ConfiguredService) -> bool:
        """Determine whether a service should be displayed on this host's service overview.

        If the service should be displayed elsewhere, this means the service is clustered and
        should be displayed on the cluster host's service overview.
        """
        return (
            self._config_cache.host_of_clustered_service(
                self._host_name,
                service.description,
                part_of_clusters=self._config_cache.clusters_of(self._host_name),
            )
            == self._host_name
        )


def _get_enforced_services(
    config_cache: ConfigCache, host_name: HostName
) -> list[ConfiguredService]:
    return [
        service
        for _ruleset_name, service in config_cache.enforced_services_table(host_name).values()
    ]


def _get_services_from_cluster_nodes(
    config_cache: ConfigCache, hostname: HostName
) -> Iterable[ConfiguredService]:
    for cluster in config_cache.clusters_of(hostname):
        yield from _get_clustered_services(config_cache, cluster, False)


def _get_clustered_services(
    config_cache: ConfigCache,
    host_name: HostName,
    skip_autochecks: bool,
) -> Iterable[ConfiguredService]:
    for node in config_cache.nodes_of(host_name) or []:
        node_checks: list[ConfiguredService] = []
        if not (skip_autochecks or config_cache.is_ping_host(host_name)):
            node_checks += config_cache.get_autochecks_of(node)
        node_checks.extend(_get_enforced_services(config_cache, node))

        yield from (
            service
            for service in node_checks
            if config_cache.host_of_clustered_service(node, service.description) == host_name
        )


class ClusterCacheInfo(NamedTuple):
    clusters_of: dict[HostName, list[HostName]]
    nodes_of: dict[HostName, list[HostName]]


class RRDConfig(TypedDict):
    """RRDConfig
    This typing might not be complete or even wrong, feel free to improve"""

    cfs: Iterable[Literal["MIN", "MAX", "AVERAGE"]]  # conceptually a Set[Literal[...]]
    rras: list[tuple[float, int, int]]
    step: Seconds
    format: Literal["pnp_multiple", "cmc_single"]


CheckContext = dict[str, Any]
GetCheckApiContext = Callable[[], dict[str, Any]]
GetInventoryApiContext = Callable[[], dict[str, Any]]
CheckIncludes = list[str]


class CheckmkCheckParameters(NamedTuple):
    enabled: bool


class DiscoveryCheckParameters(NamedTuple):
    commandline_only: bool
    check_interval: int
    severity_new_services: int
    severity_vanished_services: int
    severity_new_host_labels: int
    rediscovery: dict[str, Any]  # TODO: improve this

    @classmethod
    def commandline_only_defaults(cls) -> DiscoveryCheckParameters:
        return cls.default()._replace(commandline_only=True)

    @classmethod
    def default(cls) -> DiscoveryCheckParameters:
        """Support legacy single value global configurations. Otherwise return the defaults"""
        return cls(
            commandline_only=inventory_check_interval is None,
            check_interval=int(inventory_check_interval or 0),
            severity_new_services=int(inventory_check_severity),
            severity_vanished_services=0,
            severity_new_host_labels=1,
            # TODO: defaults are currently all over the place :-(
            rediscovery={},
        )


class SpecialAgentConfiguration(Protocol):
    args: Sequence[str]
    # None makes the stdin of subprocess /dev/null
    stdin: str | None


SpecialAgentInfoFunctionResult = (
    str | Sequence[Union[str, int, float, tuple[str, str, str]]] | SpecialAgentConfiguration
)
SpecialAgentInfoFunction = Callable[
    [Mapping[str, object], str, str | None], SpecialAgentInfoFunctionResult
]
HostCheckCommand = Union[None, str, tuple[str, int | str]]
PingLevels = dict[str, Union[int, tuple[float, float]]]

# TODO (sk): Make the type narrower: TypedDict isn't easy in the case - "too chaotic usage"(c) SP
ObjectAttributes = dict[str, Any]

GroupDefinitions = dict[str, str]
RecurringDowntime = dict[str, int | str]  # TODO(sk): TypedDict here
CheckInfo = dict  # TODO: improve this type


class _NestedExitSpec(ExitSpec, total=False):
    overall: ExitSpec
    individual: dict[str, ExitSpec]


_ignore_ip_lookup_failures = False
_failed_ip_lookups: list[HostName] = []


def ip_address_of(
    config_cache: ConfigCache, host_name: HostName, family: socket.AddressFamily | AddressFamily
) -> str | None:
    try:
        return lookup_ip_address(config_cache, host_name, family=family)
    except Exception as e:
        if config_cache.is_cluster(host_name):
            return ""

        _failed_ip_lookups.append(host_name)
        if not _ignore_ip_lookup_failures:
            config_warnings.warn(
                "Cannot lookup IP address of '%s' (%s). "
                "The host will not be monitored correctly." % (host_name, e)
            )
        return ip_lookup.fallback_ip_for(family)


def ignore_ip_lookup_failures() -> None:
    global _ignore_ip_lookup_failures
    _ignore_ip_lookup_failures = True


def failed_ip_lookups() -> list[HostName]:
    return _failed_ip_lookups


def get_variable_names() -> list[str]:
    """Provides the list of all known configuration variables."""
    return [k for k in default_config.__dict__ if k[0] != "_"]


def get_default_config() -> dict[str, Any]:
    """Provides a dictionary containing the Check_MK default configuration"""
    cfg: dict[str, Any] = {}
    for key in get_variable_names():
        value = getattr(default_config, key)

        if isinstance(value, (dict, list)):
            value = copy.deepcopy(value)

        cfg[key] = value
    return cfg


def load_default_config() -> None:
    globals().update(get_default_config())


def register(name: str, default_value: Any) -> None:
    """Register a new configuration variable within Check_MK base."""
    setattr(default_config, name, default_value)


def _add_check_variables_to_default_config() -> None:
    """Add configuration variables registered by checks to config module"""
    default_config.__dict__.update(_check_variable_defaults)


def _clear_check_variables_from_default_config(variable_names: list[str]) -> None:
    """Remove previously registered check variables from the config module"""
    for varname in variable_names:
        try:
            delattr(default_config, varname)
        except AttributeError:
            pass


# Load user configured values of check related configuration variables
# into the check module to make it available during checking.
#
# In the same step we remove the check related configuration settings from the
# config module because they are not needed there anymore.
#
# And also remove it from the default config (in case it was present)
def set_check_variables_for_checks() -> None:
    global_dict = globals()
    check_variable_names = list(_check_variables)

    check_variables = {}
    for varname in check_variable_names:
        check_variables[varname] = global_dict.pop(varname)

    set_check_variables(check_variables)
    _clear_check_variables_from_default_config(check_variable_names)


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


def load(
    with_conf_d: bool = True,
    validate_hosts: bool = True,
    exclude_parents_mk: bool = False,
    *,
    changed_vars_handler: Callable[[set[str]], None] | None = None,
) -> None:
    _initialize_config()

    changed_var_names = _load_config(with_conf_d, exclude_parents_mk)
    if changed_vars_handler is not None:
        changed_vars_handler(changed_var_names)

    _transform_mgmt_config_vars_from_140_to_150()
    _initialize_derived_config_variables()

    _perform_post_config_loading_actions()

    if validate_hosts:
        _verify_non_duplicate_hosts()


def load_packed_config(config_path: ConfigPath) -> None:
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
    _perform_post_config_loading_actions()


def _initialize_config() -> None:
    _add_check_variables_to_default_config()
    load_default_config()


def _perform_post_config_loading_actions() -> None:
    """These tasks must be performed after loading the Check_MK base configuration"""
    # First cleanup things (needed for e.g. reloading the config)
    _config_cache.clear_all()

    global_dict = globals()
    _collect_parameter_rulesets_from_globals(global_dict)
    _transform_plugin_names_from_160_to_170(global_dict)

    get_config_cache().initialize()

    # In case the checks are not loaded yet it seems the current mode
    # is not working with the checks. In this case also don't load the
    # static checks into the configuration.
    if any_check_loaded():
        set_check_variables_for_checks()


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
        for hostname in strip_tags(list(new_hosts)):
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


class SetFolderPathDict(SetFolderPathAbstract, dict):
    # TODO: How to annotate this?
    def update(self, new_hosts):
        # not-yet-a-type
        self._set_folder_paths(new_hosts)
        return super().update(new_hosts)

    # Probably unused
    def __setitem__(self, cluster_name: Any, value: Any) -> Any:
        self._set_folder_paths([cluster_name])
        return super().__setitem__(cluster_name, value)


def cleanup_fs_used_marker_flag(log):
    # Test if User migrated during 1.6 to new name fs_used. If so delete marker flag file
    old_config_flag = os.path.join(cmk.utils.paths.omd_root, "etc/check_mk/conf.d/fs_cap.mk")
    if os.path.exists(old_config_flag):
        log("remove flag %s\n" % old_config_flag)
        os.remove(old_config_flag)


def _load_config_file(file_to_load: Path, into_dict: dict[str, Any]) -> None:
    exec(file_to_load.read_text(), into_dict, into_dict)


def _load_config(with_conf_d: bool, exclude_parents_mk: bool) -> set[str]:
    helper_vars = {
        "FOLDER_PATH": None,
    }

    global all_hosts
    global clusters

    all_hosts = SetFolderPathList(all_hosts)
    clusters = SetFolderPathDict(clusters)

    global_dict = globals()
    pre_load_vars = {**global_dict}

    global_dict.update(helper_vars)

    # Load assorted experimental parameters if any
    experimental_config = cmk.utils.paths.make_experimental_config_file()
    if experimental_config.exists():
        _load_config_file(experimental_config, global_dict)

    cleanup_fs_used_marker_flag(console.info)  # safety cleanup for 1.6->1.7 update

    host_storage_loaders = get_host_storage_loaders(config_storage_format)
    config_dir_path = Path(cmk.utils.paths.check_mk_config_dir)
    for path in get_config_file_paths(with_conf_d):
        # During parent scan mode we must not read in old version of parents.mk!
        if exclude_parents_mk and path.name == "parents.mk":
            continue

        try:
            # Make the config path available as a global variable to be used
            # within the configuration file. The FOLDER_PATH is only used by
            # rules.mk files these days, but may also be used in some legacy
            # config files or files generated by 3rd party mechanisms.
            current_path: str | None = None
            folder_path: str | None = None
            try:
                relative_path = path.relative_to(config_dir_path)
                current_path = "/" + str(relative_path)
                folder_path = str(relative_path.parent)
            except ValueError:
                pass

            global_dict.update(
                {
                    "FOLDER_PATH": folder_path,
                }
            )

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
            if cmk.utils.debug.enabled():
                raise
            if sys.stderr.isatty():
                console.error("Cannot read in configuration file %s: %s\n", path, e)
            sys.exit(1)

    # Cleanup global helper vars
    for helper_var in helper_vars:
        del global_dict[helper_var]

    # Revert specialised SetFolderPath classes back to normal, because it improves
    # the lookup performance and the helper_vars are no longer available anyway..
    all_hosts = list(all_hosts)
    clusters = dict(clusters)

    return {k for k, v in global_dict.items() if k not in pre_load_vars or v != pre_load_vars[k]}


def _transform_mgmt_config_vars_from_140_to_150() -> None:
    # FIXME We have to transform some configuration variables from host attributes
    # to cmk.base configuration variables because during the migration step from
    # 1.4.0 to 1.5.0 some config variables are not known in cmk.base. These variables
    # are 'management_protocol' and 'management_snmp_community'.
    # Clean this up one day!
    for hostname, attributes in host_attributes.items():
        if attributes.get("management_protocol"):
            management_protocol.setdefault(hostname, attributes["management_protocol"])
        if attributes.get("management_snmp_community"):
            management_snmp_credentials.setdefault(
                hostname, attributes["management_snmp_community"]
            )


def _transform_plugin_names_from_160_to_170(global_dict: dict[str, Any]) -> None:
    # Pre 1.7.0 check plugin names may have dots or dashes (one case) in them.
    # Now they don't, and we have to translate all variables that may use them:
    if "service_descriptions" in global_dict:
        global_dict["service_descriptions"] = {
            maincheckify(k): str(v) for k, v in global_dict["service_descriptions"].items()
        }
    if "ignored_checktypes" in global_dict:
        global_dict["ignored_checktypes"] = [
            maincheckify(n) for n in global_dict["ignored_checktypes"]
        ]


def _collect_parameter_rulesets_from_globals(global_dict: dict[str, Any]) -> None:
    vars_to_remove = set()

    for ruleset_name in agent_based_register.iter_all_discovery_rulesets():
        var_name = str(ruleset_name)
        if var_name in global_dict:
            agent_based_register.set_discovery_ruleset(ruleset_name, global_dict[var_name])
            # do not remove it yet, it may be a host_label ruleset as well!
            vars_to_remove.add(var_name)

    for ruleset_name in agent_based_register.iter_all_host_label_rulesets():
        var_name = str(ruleset_name)
        if var_name in global_dict:
            agent_based_register.set_host_label_ruleset(ruleset_name, global_dict[var_name])
            vars_to_remove.add(var_name)

    # list of discovery ruleset names which are used in migrated AND in legacy code; can be removed
    # once we have no such cases any more
    partially_migrated = {
        "diskstat_inventory",
        "filesystem_groups",
    }

    for var_name in vars_to_remove - partially_migrated:
        del global_dict[var_name]


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
    host_service_levels = extra_host_conf.get("_ec_sl", [])


def get_derived_config_variable_names() -> set[str]:
    """These variables are computed from other configuration variables and not configured directly.

    The origin variable (extra_service_conf) should not be exported to the helper config. Only
    the service levels are needed."""
    return {"service_service_levels", "host_service_levels"}


def _verify_non_duplicate_hosts() -> None:
    duplicates = duplicate_hosts()
    if duplicates:
        # TODO: Raise an exception
        console.error("Error in configuration: duplicate hosts: %s\n", ", ".join(duplicates))
        sys.exit(3)


def save_packed_config(config_path: ConfigPath, config_cache: ConfigCache) -> None:
    """Create and store a precompiled configuration for Checkmk helper processes"""
    PackedConfigStore.from_serial(config_path).write(PackedConfigGenerator(config_cache).generate())


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

    def __init__(self, config_cache: ConfigCache) -> None:
        self._config_cache = config_cache

    def generate(self) -> Mapping[str, Any]:
        helper_config: MutableMapping[str, Any] = {}

        # These functions purpose is to filter out hosts which are monitored on different sites
        active_hosts = self._config_cache.all_active_hosts()
        # Include inactive cluster hosts.
        # Otherwise services clustered to those hosts will wrongly be checked by the nodes.
        sites_clusters = self._config_cache.all_sites_clusters()

        def filter_all_hosts(all_hosts_orig: AllHosts) -> list[HostName]:
            all_hosts_red = []
            for host_entry in all_hosts_orig:
                hostname = host_entry.split("|", 1)[0]
                if hostname in active_hosts:
                    all_hosts_red.append(host_entry)
            return all_hosts_red

        def filter_clusters(clusters_orig: AllClusters) -> dict[HostName, list[HostName]]:
            clusters_red = {}
            for cluster_entry, cluster_nodes in clusters_orig.items():
                clustername = cluster_entry.split("|", 1)[0]
                if clustername in sites_clusters:
                    clusters_red[cluster_entry] = cluster_nodes
            return clusters_red

        def filter_hostname_in_dict(
            values: dict[HostName, dict[str, str]]
        ) -> dict[HostName, dict[str, str]]:
            values_red = {}
            for hostname, attributes in values.items():
                if hostname in active_hosts:
                    values_red[hostname] = attributes
            return values_red

        def filter_extra_service_conf(
            values: dict[str, list[dict[str, str]]]
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

        for varname in get_variable_names() + list(derived_config_variable_names):
            if varname in self._skipped_config_variable_names:
                continue

            val = global_variables[varname]

            if varname not in derived_config_variable_names and val == variable_defaults[varname]:
                continue

            if varname in filter_var_functions:
                val = filter_var_functions[varname](val)

            helper_config[varname] = val

        #
        # Add discovery rules
        #

        for ruleset_name in agent_based_register.iter_all_discovery_rulesets():
            value = agent_based_register.get_discovery_ruleset(ruleset_name)
            if not value:
                continue

            helper_config[str(ruleset_name)] = value

        #
        # Add modified check specific Checkmk base settings
        #

        for varname, val in get_check_variables().items():
            if val == _check_variable_defaults[varname]:
                continue

            helper_config[varname] = val

        return helper_config


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
        tmp_path = self.path.with_suffix(self.path.suffix + ".compiled")
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


def strip_tags(tagged_hostlist: list[str]) -> list[HostName]:
    cache = _config_cache.get("strip_tags")

    cache_id = tuple(tagged_hostlist)
    with contextlib.suppress(KeyError):
        return cache[cache_id]
    return cache.setdefault(cache_id, [HostName(h.split("|", 1)[0]) for h in tagged_hostlist])


def get_shadow_hosts() -> ShadowHosts:
    try:
        # Only available with CEE
        return shadow_hosts  # type: ignore[name-defined]
    except NameError:
        return {}


def _filter_active_hosts(
    config_cache: ConfigCache, hostlist: Iterable[HostName], keep_offline_hosts: bool = False
) -> list[HostName]:
    """Returns a set of active hosts for this site"""
    if only_hosts is None:
        if distributed_wato_site is None:
            return list(hostlist)

        return [
            hostname
            for hostname in hostlist
            if _host_is_member_of_site(hostname, distributed_wato_site)
        ]

    if distributed_wato_site is None:
        if keep_offline_hosts:
            return list(hostlist)
        return [
            hostname
            for hostname in hostlist
            if config_cache.in_binary_hostlist(hostname, only_hosts)
        ]

    return [
        hostname
        for hostname in hostlist
        if _host_is_member_of_site(hostname, distributed_wato_site)
        and (keep_offline_hosts or config_cache.in_binary_hostlist(hostname, only_hosts))
    ]


def _host_is_member_of_site(hostname: HostName, site: str) -> bool:
    # hosts without a site: tag belong to all sites
    return ConfigCache.tags(hostname).get("site", distributed_wato_site) == distributed_wato_site


def duplicate_hosts() -> Sequence[HostName]:
    return sorted(
        hostname
        for hostname, count in Counter(
            # This function should only be used during duplicate host check! It has to work like
            # all_active_hosts() but with the difference that duplicates are not removed.
            _filter_active_hosts(
                get_config_cache(),
                strip_tags(list(all_hosts) + list(clusters) + list(get_shadow_hosts())),
            )
        ).items()
        if count > 1
    )


# Returns a list of all hosts which are associated with this site,
# but have been removed by the "only_hosts" rule. Normally these
# are the hosts which have the tag "offline".
#
# This is not optimized for performance, so use in specific situations.
def all_offline_hosts() -> set[HostName]:
    config_cache = get_config_cache()

    hostlist = set(
        _filter_active_hosts(
            config_cache,
            config_cache.all_configured_realhosts().union(config_cache.all_configured_clusters()),
            keep_offline_hosts=True,
        )
    )

    if only_hosts is None:
        return set()

    return {
        hostname
        for hostname in hostlist
        if not config_cache.in_binary_hostlist(hostname, only_hosts)
    }


def all_configured_offline_hosts() -> set[HostName]:
    config_cache = get_config_cache()
    hostlist = config_cache.all_configured_realhosts().union(config_cache.all_configured_clusters())

    if only_hosts is None:
        return set()

    return {
        hostname
        for hostname in hostlist
        if not config_cache.in_binary_hostlist(hostname, only_hosts)
    }


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

# Renaming of service descriptions while keeping backward compatibility with
# existing installations.
# Synchronize with htdocs/wato.py and plugins/wato/check_mk_configuration.py!


# Cleanup! .. some day
def _get_old_cmciii_temp_description(item: Item) -> tuple[bool, ServiceName]:
    if item is None:
        raise TypeError()

    if "Temperature" in item:
        return False, item  # old item format, no conversion

    parts = item.split(" ")
    if parts[0] == "Ambient":
        return False, "%s Temperature" % parts[1]

    if len(parts) == 2:
        return False, f"{parts[1]} {parts[0]}.Temperature"

    if parts[1] == "LCP":
        parts[1] = "Liquid_Cooling_Package"
    return False, f"{parts[1]} {parts[0]}.{parts[2]}-Temperature"


_old_service_descriptions: Mapping[
    str, ServiceName | Callable[[Item], tuple[bool, ServiceName]]
] = {
    "aix_memory": "Memory used",
    # While using the old description, don't append the item, even when discovered
    # with the new check which creates an item.
    "barracuda_mailqueues": lambda item: (False, "Mail Queue"),
    "brocade_sys_mem": "Memory used",
    "casa_cpu_temp": "Temperature %s",
    "cisco_asa_failover": "Cluster Status",
    "cisco_mem": "Mem used %s",
    "cisco_mem_asa": "Mem used %s",
    "cisco_mem_asa64": "Mem used %s",
    "cmciii_temp": _get_old_cmciii_temp_description,
    "cmciii_psm_current": "%s",
    "cmciii_lcp_airin": "LCP Fanunit Air IN",
    "cmciii_lcp_airout": "LCP Fanunit Air OUT",
    "cmciii_lcp_water": "LCP Fanunit Water %s",
    "db2_mem": "Mem of %s",
    "df": "fs_%s",
    "df_netapp": "fs_%s",
    "df_netapp32": "fs_%s",
    "docker_container_mem": "Memory used",
    "enterasys_temp": lambda item: (False, "Temperature"),
    "esx_vsphere_datastores": "fs_%s",
    "esx_vsphere_hostsystem_mem_usage": "Memory used",
    "esx_vsphere_hostsystem_mem_usage_cluster": "Memory usage",
    "etherbox_temp": "Sensor %s",
    "fortigate_memory": "Memory usage",
    "fortigate_memory_base": "Memory usage",
    "fortigate_node_memory": "Memory usage %s",
    "hr_fs": "fs_%s",
    "hr_mem": "Memory used",
    "huawei_switch_mem": "Memory used %s",
    "hyperv_vm": "hyperv_vms",
    "ibm_svc_mdiskgrp": "MDiskGrp %s",
    "ibm_svc_system": "IBM SVC Info",
    "ibm_svc_systemstats_cache": "IBM SVC Cache Total",
    "ibm_svc_systemstats_diskio": "IBM SVC Throughput %s Total",
    "ibm_svc_systemstats_disk_latency": "IBM SVC Latency %s Total",
    "ibm_svc_systemstats_iops": "IBM SVC IOPS %s Total",
    "innovaphone_mem": "Memory used",
    "innovaphone_temp": lambda item: (False, "Temperature"),
    "juniper_mem": "Memory Utilization %s",
    "juniper_screenos_mem": "Memory used",
    "juniper_trpz_mem": "Memory used",
    "liebert_bat_temp": lambda item: (False, "Battery Temp"),
    "logwatch": "LOG %s",
    "logwatch_groups": "LOG %s",
    "megaraid_bbu": "RAID Adapter/BBU %s",
    "megaraid_pdisks": "RAID PDisk Adapt/Enc/Sl %s",
    "megaraid_ldisks": "RAID Adapter/LDisk %s",
    "mem_used": "Memory used",
    "mem_win": "Memory and pagefile",
    "mknotifyd": "Notification Spooler %s",
    "mknotifyd_connection": "Notification Connection %s",
    "mssql_backup": "%s Backup",
    "mssql_blocked_sessions": lambda item: (False, "MSSQL Blocked Sessions"),
    "mssql_counters_cache_hits": "%s",
    "mssql_counters_file_sizes": "%s File Sizes",
    "mssql_counters_locks": "%s Locks",
    "mssql_counters_locks_per_batch": "%s Locks per Batch",
    "mssql_counters_pageactivity": "%s Page Activity",
    "mssql_counters_sqlstats": "%s",
    "mssql_counters_transactions": "%s Transactions",
    "mssql_databases": "%s Database",
    "mssql_datafiles": "Datafile %s",
    "mssql_tablespaces": "%s Sizes",
    "mssql_transactionlogs": "Transactionlog %s",
    "mssql_versions": "%s Version",
    "netscaler_mem": "Memory used",
    "nullmailer_mailq": lambda item: (False, "Nullmailer Queue"),
    "nvidia_temp": "Temperature NVIDIA %s",
    "postfix_mailq": lambda item: (False, "Postfix Queue"),
    "ps": "proc_%s",
    "qmail_stats": lambda item: (False, "Qmail Queue"),
    "raritan_emx": "Rack %s",
    "raritan_pdu_inlet": "Input Phase %s",
    "services": "service_%s",
    "solaris_mem": "Memory used",
    "sophos_memory": "Memory usage",
    "statgrab_mem": "Memory used",
    "tplink_mem": "Memory used",
    "ups_bat_temp": "Temperature Battery %s",
    "vms_diskstat_df": "fs_%s",
    "wmic_process": "proc_%s",
    "zfsget": "fs_%s",
}


def service_description(
    hostname: HostName,
    check_plugin_name: CheckPluginName,
    item: Item,
) -> ServiceName:
    plugin = agent_based_register.get_check_plugin(check_plugin_name)
    if plugin is None:
        if item:
            return f"Unimplemented check {check_plugin_name} / {item}"
        return "Unimplemented check %s" % check_plugin_name

    return get_final_service_description(
        hostname,
        _format_item_with_template(*_get_service_description_template_and_item(plugin, item)),
    )


def _get_service_description_template_and_item(plugin: CheckPlugin, item: Item) -> tuple[str, Item]:
    plugin_name_str = str(plugin.name)

    # use user-supplied service description, if available
    descr_format: ServiceName | None = service_descriptions.get(plugin_name_str)
    if descr_format:
        return descr_format, item

    old_descr = _old_service_descriptions.get(plugin_name_str)
    if old_descr is None or plugin_name_str in use_new_descriptions_for:
        return plugin.service_name, item

    if isinstance(old_descr, str):
        return old_descr, item

    preserve_item, descr_format = old_descr(item)
    return descr_format, item if preserve_item else None


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


def _old_active_http_check_service_description(params: dict | tuple) -> str:
    name = params[0] if isinstance(params, tuple) else params["name"]
    return name[1:] if name.startswith("^") else "HTTP %s" % name


_old_active_check_service_descriptions = {
    "http": _old_active_http_check_service_description,
}


def active_check_service_description(
    hostname: HostName,
    hostalias: str,
    active_check_name: ActiveCheckPluginName,
    params: dict,
) -> ServiceName:
    if active_check_name not in active_check_info:
        return "Unimplemented check %s" % active_check_name

    if (
        active_check_name in _old_active_check_service_descriptions
        and active_check_name not in use_new_descriptions_for
    ):
        description = _old_active_check_service_descriptions[active_check_name](params)
    else:
        act_info = active_check_info[active_check_name]
        description = act_info["service_description"](params)

    description = description.replace("$HOSTNAME$", hostname).replace("$HOSTALIAS$", hostalias)

    return get_final_service_description(hostname, description)


def get_final_service_description(hostname: HostName, description: ServiceName) -> ServiceName:
    translations = get_service_translations(hostname)
    # Note: at least strip the service description.
    # Some plugins introduce trailing whitespaces, but Nagios silently drops leading
    # and trailing spaces in the configuration file.
    description = (
        cmk.utils.translations.translate_service_description(translations, description).strip()
        if translations
        else description.strip()
    )

    # Sanitize: remove illegal characters from a service description
    cache = _config_cache.get("final_service_description")
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
def service_depends_on(hostname: HostName, servicedesc: ServiceName) -> list[ServiceName]:
    """Return a list of services this services depends upon"""
    deps = []
    config_cache = get_config_cache()
    for entry in service_dependencies:
        entry, rule_options = tuple_rulesets.get_rule_options(entry)
        if rule_options.get("disabled"):
            continue

        if len(entry) == 3:
            depname, hostlist, patternlist = entry
            tags: list[str] = []
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
                matchobject = regex(pattern).search(servicedesc)
                if matchobject:
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
    """Whether or not the site is currently configured to use the Microcore."""
    return monitoring_core == "cmc"


def get_piggyback_translations(hostname: HostName) -> cmk.utils.translations.TranslationOptions:
    """Get a dict that specifies the actions to be done during the hostname translation"""
    rules = get_config_cache().host_extra_conf(hostname, piggyback_translation)
    translations: cmk.utils.translations.TranslationOptions = {}
    for rule in rules[::-1]:
        translations.update(rule)
    return translations


def get_service_translations(hostname: HostName) -> cmk.utils.translations.TranslationOptions:
    translations_cache = _config_cache.get("service_description_translations")
    with contextlib.suppress(KeyError):
        return translations_cache[hostname]

    rules = get_config_cache().host_extra_conf(hostname, service_description_translation)
    rule: cmk.utils.translations.TranslationOptionsSpec
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


def _prepare_check_command(
    command_spec: CheckCommandArguments,
    hostname: HostName,
    description: ServiceName | None,
    passwords_from_store: Mapping[str, str],
) -> str:
    """Prepares a check command for execution by Checkmk

    In case a list is given it quotes element if necessary. It also prepares password store entries
    for the command line. These entries will be completed by the executed program later to get the
    password from the password store.
    """
    passwords: list[tuple[str, str, str]] = []
    formatted: list[str] = []
    for arg in command_spec:
        if isinstance(arg, (int, float)):
            formatted.append("%s" % arg)

        elif isinstance(arg, str):
            formatted.append(shlex.quote(arg))

        elif isinstance(arg, tuple) and len(arg) == 3:
            pw_ident, preformated_arg = arg[1:]
            try:
                password = passwords_from_store[pw_ident]
            except KeyError:
                if hostname and description:
                    descr = f' used by service "{description}" on host "{hostname}"'
                elif hostname:
                    descr = ' used by host host "%s"' % (hostname)
                else:
                    descr = ""

                console.warning(
                    f'The stored password "{pw_ident}"{descr} does not exist (anymore).'
                )
                password = "%%%"

            pw_start_index = str(preformated_arg.index("%s"))
            # the * placeholder may seem random, but the (binary!) length of the string is actually
            # important because there is a C implementation of resolve_password_hack that relies on the
            # binary lengths of the password and the placeholder being equal.
            # check `cmk_replace_passwords` in `omd/packages/monitoring-plugins/cmk_password_store.h`
            formatted.append(shlex.quote(preformated_arg % ("*" * len(password.encode("utf-8")))))
            passwords.append((str(len(formatted)), pw_start_index, pw_ident))

        else:
            raise MKGeneralException(f"Invalid argument for command line: {arg!r}")

    if passwords:
        pw_store_arg = "--pwstore=%s" % ",".join(["@".join(p) for p in passwords])
        formatted = [shlex.quote(pw_store_arg)] + formatted

    return " ".join(formatted)


def commandline_arguments(
    hostname: HostName,
    description: ServiceName | None,
    commandline_args: SpecialAgentInfoFunctionResult,
    passwords_from_store: Mapping[str, str] | None = None,
) -> str:
    """Commandline arguments for special agents or active checks."""
    if isinstance(commandline_args, str):
        return commandline_args

    # Some special agents also have stdin configured
    args = getattr(commandline_args, "args", commandline_args)

    if not isinstance(args, list):
        raise MKGeneralException(
            "The check argument function needs to return either a list of arguments or a "
            "string of the concatenated arguments (Host: %s, Service: %s)."
            % (hostname, description)
        )

    return _prepare_check_command(
        args,
        hostname,
        description,
        cmk.utils.password_store.load() if passwords_from_store is None else passwords_from_store,
    )


# .
#   .--Host matching-------------------------------------------------------.
#   |  _   _           _                     _       _     _               |
#   | | | | | ___  ___| |_   _ __ ___   __ _| |_ ___| |__ (_)_ __   __ _   |
#   | | |_| |/ _ \/ __| __| | '_ ` _ \ / _` | __/ __| '_ \| | '_ \ / _` |  |
#   | |  _  | (_) \__ \ |_  | | | | | | (_| | || (__| | | | | | | | (_| |  |
#   | |_| |_|\___/|___/\__| |_| |_| |_|\__,_|\__\___|_| |_|_|_| |_|\__, |  |
#   |                                                              |___/   |
#   +----------------------------------------------------------------------+
#   | Code for calculating the host condition matching of rules            |
#   '----------------------------------------------------------------------'

hosttags_match_taglist = tuple_rulesets.hosttags_match_taglist


# Slow variant of checking wether a service is matched by a list
# of regexes - used e.g. by cmk --notify
def in_extraconf_servicelist(service_patterns: list[str], service: str) -> bool:
    optimized_pattern = tuple_rulesets.convert_pattern_list(service_patterns)
    if not optimized_pattern:
        return False
    return optimized_pattern.match(service) is not None


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

# TODO: Cleanup access to check_info[] -> replace it by different function calls
# like for example check_exists(...)

# BE AWARE: sync these global data structures with
#           _initialize_data_structures()
# TODO: Refactor this.

# The checks are loaded into this dictionary. Each check
_check_contexts: dict[str, Any] = {}
# has a separate sub-dictionary, named by the check name.
# It is populated with the includes and the check itself.

# The following data structures will be filled by the checks
# all known checks
check_info: dict[str, dict[str, Any]] = {}
# Lookup for legacy names
legacy_check_plugin_names: dict[CheckPluginName, str] = {}
# library files needed by checks
check_includes: dict[str, list[Any]] = {}
# optional functions for parameter precompilation
precompile_params: dict[str, Callable[[str, str, dict[str, Any]], Any]] = {}
# dictionary-configured checks declare their default level variables here
check_default_levels: dict[str, Any] = {}
# factory settings for dictionary-configured checks
factory_settings: dict[str, dict[str, Any]] = {}
# variables (names) in checks/* needed for check itself
check_config_variables: list[Any] = []
# whichs OIDs to fetch for which check (for tabular information)
snmp_info: dict[str, tuple[Any] | list[tuple[Any]]] = {}
# SNMP autodetection
snmp_scan_functions: dict[str, SNMPScanFunction] = {}
# definitions of active "legacy" checks
active_check_info: dict[str, dict[str, Any]] = {}
special_agent_info: dict[str, SpecialAgentInfoFunction] = {}

# Names of variables registered in the check files. This is used to
# keep track of the variables needed by each file. Those variables are then
# (if available) read from the config and applied to the checks module after
# reading in the configuration of the user.
_check_variables: dict[str, list[Any]] = {}
# keeps the default values of all the check variables
_check_variable_defaults: dict[str, Any] = {}
_all_checks_loaded = False

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
#   | Loading of check plugins                                             |
#   '----------------------------------------------------------------------'


def load_all_agent_based_plugins(
    get_check_api_context: GetCheckApiContext,
) -> list[str]:
    """Load all checks and includes"""
    global _all_checks_loaded

    _initialize_data_structures()

    errors = agent_based_register.load_all_plugins()

    # LEGACY CHECK PLUGINS
    filelist = get_plugin_paths(
        str(cmk.utils.paths.local_checks_dir),
        cmk.utils.paths.checks_dir,
    )

    errors.extend(load_checks(get_check_api_context, filelist))

    _all_checks_loaded = True

    return errors


def _initialize_data_structures() -> None:
    """Initialize some data structures which are populated while loading the checks"""
    global _all_checks_loaded
    _all_checks_loaded = False

    _check_variables.clear()
    _check_variable_defaults.clear()

    _check_contexts.clear()
    check_info.clear()
    legacy_check_plugin_names.clear()
    check_includes.clear()
    precompile_params.clear()
    check_default_levels.clear()
    factory_settings.clear()
    del check_config_variables[:]
    snmp_info.clear()
    snmp_scan_functions.clear()
    active_check_info.clear()
    special_agent_info.clear()


def get_plugin_paths(*dirs: str) -> list[str]:
    filelist: list[str] = []
    for directory in dirs:
        filelist += _plugin_pathnames_in_directory(directory)
    return filelist


# Now read in all checks. Note: this is done *before* reading the
# configuration, because checks define variables with default
# values user can override those variables in his configuration.
# If a check or check.include is both found in local/ and in the
# normal structure, then only the file in local/ must be read!
# NOTE: The given file names should better be absolute, otherwise
# we depend on the current working directory, which is a bad idea,
# especially in tests.
def load_checks(  # pylint: disable=too-many-branches
    get_check_api_context: GetCheckApiContext,
    filelist: list[str],
) -> list[str]:
    cmk_global_vars = set(get_variable_names())

    loaded_files: set[str] = set()

    did_compile = False
    for f in filelist:
        if f[0] == "." or f[-1] == "~":
            continue  # ignore editor backup / temp files

        file_name = os.path.basename(f)
        if file_name in loaded_files:
            continue  # skip already loaded files (e.g. from local)

        try:
            check_context = new_check_context(get_check_api_context)

            # Make a copy of known check plugin names
            known_vars = set(check_context)
            known_checks = set(check_info)
            known_active_checks = set(active_check_info)

            did_compile |= load_check_includes(f, check_context)
            did_compile |= load_precompiled_plugin(f, check_context)

            loaded_files.add(file_name)

        except MKTerminate:
            raise

        except Exception as e:
            console.error("Error in plugin file %s: %s\n", f, e)
            if cmk.utils.debug.enabled():
                raise
            continue

        new_checks = set(check_info).difference(known_checks)
        new_active_checks = set(active_check_info).difference(known_active_checks)

        # Now store the check context for all checks found in this file
        for check_plugin_name in new_checks:
            _check_contexts[check_plugin_name] = check_context

        for check_plugin_name in new_active_checks:
            _check_contexts[check_plugin_name] = check_context

        # Collect all variables that the check file did introduce compared to the
        # default check context
        new_check_vars = {}
        for varname in set(check_context).difference(known_vars):
            new_check_vars[varname] = check_context[varname]

        # The default_levels_variable of check_info also declares use of a global
        # variable. Register it here for this context.
        for check_plugin_name in new_checks:
            # The check_info is not converted yet (convert_check_info()). This means we need
            # to deal with old style tuple configured checks
            if isinstance(check_info[check_plugin_name], tuple):
                default_levels_varname = check_default_levels.get(check_plugin_name)
            else:
                default_levels_varname = check_info[check_plugin_name].get(
                    "default_levels_variable"
                )

            if default_levels_varname:
                # Add the initial configuration to the check context to have a consistent state
                check_context[default_levels_varname] = factory_settings.get(
                    default_levels_varname, {}
                )
                new_check_vars[default_levels_varname] = check_context[default_levels_varname]

        # Save check variables for e.g. after config loading that the config can
        # be added to the check contexts
        _set_check_variable_defaults(
            variables=new_check_vars,
            # Keep track of which variable needs to be set to which context
            context_idents=list(new_checks) + list(new_active_checks),
            # Do not allow checks to override Checkmk builtin global variables. Silently
            # skip them here. The variables will only be locally available to the checks.
            skip_names=cmk_global_vars,
        )

    # add variables corresponding to check plugins that may have been migrated to new API
    migrated_vars = vars(cmk.utils.migrated_check_variables)
    _set_check_variable_defaults(
        migrated_vars,
        ["__migrated_plugins_variables__"],
    )
    _check_contexts.setdefault("__migrated_plugins_variables__", migrated_vars)

    # Now convert check_info to new format.
    convert_check_info()
    legacy_check_plugin_names.update({CheckPluginName(maincheckify(n)): n for n in check_info})

    return _extract_agent_and_snmp_sections(
        validate_creation_kwargs=did_compile
    ) + _extract_check_plugins(validate_creation_kwargs=did_compile)


def all_checks_loaded() -> bool:
    """Whether or not all(!) checks have been loaded into the current process"""
    return _all_checks_loaded


def any_check_loaded() -> bool:
    """Whether or not some checks have been loaded into the current process"""
    return bool(_check_contexts)


# Constructs a new check context dictionary. It contains the whole check API.
def new_check_context(get_check_api_context: GetCheckApiContext) -> CheckContext:
    # Add the data structures where the checks register with Checkmk
    context = {
        "check_info": check_info,
        "check_includes": check_includes,
        "precompile_params": precompile_params,
        "check_default_levels": check_default_levels,
        "factory_settings": factory_settings,
        "check_config_variables": check_config_variables,
        "snmp_info": snmp_info,
        "snmp_scan_functions": snmp_scan_functions,
        "active_check_info": active_check_info,
        "special_agent_info": special_agent_info,
    }
    # NOTE: For better separation it would be better to copy the values, but
    # this might consume too much memory, so we simply reference them.
    context.update(get_check_api_context())
    return context


# Load the definitions of the required include files for this check
# Working with imports when specifying the includes would be much cleaner,
# sure. But we need to deal with the current check API.
def load_check_includes(check_file_path: str, check_context: CheckContext) -> bool:
    """Returns `True` if something has been compiled, else `False`."""
    did_compile = False
    for include_file_name in cached_includes_of_plugin(check_file_path):
        include_file_path = check_include_file_path(include_file_name)
        try:
            did_compile |= load_precompiled_plugin(include_file_path, check_context)
        except MKTerminate:
            raise

        except Exception as e:
            console.error("Error in check include file %s: %s\n", include_file_path, e)
            if cmk.utils.debug.enabled():
                raise
            continue

    return did_compile


def check_include_file_path(include_file_name: str) -> str:
    return str(cmk.utils.paths.local_checks_dir / include_file_name)


def cached_includes_of_plugin(check_file_path: str) -> CheckIncludes:
    cache_file_path = _include_cache_file_path(check_file_path)
    try:
        return _get_cached_check_includes(check_file_path, cache_file_path)
    except OSError:
        pass  # No usable cache. Terminate

    includes = includes_of_plugin(check_file_path)
    _write_check_include_cache(cache_file_path, includes)
    return includes


def _get_cached_check_includes(check_file_path: str, cache_file_path: str) -> CheckIncludes:
    check_stat = os.stat(check_file_path)
    cache_stat = os.stat(cache_file_path)

    if check_stat.st_mtime >= cache_stat.st_mtime:
        raise OSError("Cache is too old")

    # There are no includes (just the newline at the end)
    if cache_stat.st_size == 1:
        return []  # No includes

    # store.save_text_to_file() creates file empty for locking (in case it does not exists).
    # Skip loading the file.
    # Note: When raising here this process will also write the file. This means it
    # will write it another time after it was written by the other process. This
    # could be optimized. Since the whole caching here is a temporary(tm) soltion,
    # we leave it as it is.
    if cache_stat.st_size == 0:
        raise OSError("Cache generation in progress (file is locked)")

    x = Path(cache_file_path).read_text().strip()
    if not x:
        return []  # Shouldn't happen. Empty files are handled above
    return x.split("|")


def _write_check_include_cache(cache_file_path: str, includes: CheckIncludes) -> None:
    store.makedirs(os.path.dirname(cache_file_path))
    store.save_text_to_file(cache_file_path, "%s\n" % "|".join(includes))


def _include_cache_file_path(path: str) -> str:
    is_local = path.startswith(str(cmk.utils.paths.local_checks_dir))
    return os.path.join(
        cmk.utils.paths.include_cache_dir,
        "local" if is_local else "builtin",
        os.path.basename(path),
    )


# Parse the check file without executing the code to find the check include
# files the check uses. The following statements are extracted:
# check_info[...] = { "includes": [...] }
# inv_info[...] = { "includes": [...] }
# check_includes[...] = [...]
def includes_of_plugin(check_file_path: str) -> CheckIncludes:
    include_names = OrderedDict()

    def _load_from_check_info(node: ast.Assign) -> None:
        if not isinstance(node.value, ast.Dict):
            return

        for key, val in zip(node.value.keys, node.value.values):
            if not isinstance(key, ast.Constant):
                continue
            if key.s == "includes":
                if isinstance(val, ast.List):
                    for element in val.elts:
                        if not isinstance(element, ast.Constant):
                            raise MKGeneralException(
                                "Includes must be a list of include file "
                                "names, found '%s'" % type(element)
                            )
                        include_names[element.s] = True
                else:
                    raise MKGeneralException(
                        "Includes must be a list of include file names, " "found '%s'" % type(val)
                    )

    def _load_from_check_includes(node: ast.Assign) -> None:
        if isinstance(node.value, ast.List):
            for element in node.value.elts:
                if not isinstance(element, ast.Constant):
                    raise MKGeneralException(
                        "Includes must be a list of include file "
                        "names, found '%s'" % type(element)
                    )
                include_names[element.s] = True

    tree = ast.parse(Path(check_file_path).read_text())
    for child in ast.iter_child_nodes(tree):
        if not isinstance(child, ast.Assign):
            continue  # We only care about top level assigns

        # Filter out assignments to check_info dictionary
        for target in child.targets:
            if isinstance(target, ast.Subscript) and isinstance(target.value, ast.Name):
                if target.value.id in ["check_info", "inv_info"]:
                    _load_from_check_info(child)
                elif target.value.id == "check_includes":
                    _load_from_check_includes(child)

    return list(include_names)


def _plugin_pathnames_in_directory(path: str) -> list[str]:
    if path and os.path.exists(path):
        return sorted(
            [
                path + "/" + f
                for f in os.listdir(path)
                if not f.startswith(".") and not f.endswith(".include")
            ]
        )
    return []


class _PYCHeader:
    """A pyc header according to https://www.python.org/dev/peps/pep-0552/"""

    SIZE = 16

    def __init__(self, magic: bytes, hash_: int, origin_mtime: int, f_size: int) -> None:
        self.magic = magic
        self.hash = hash_
        self.origin_mtime = origin_mtime
        self.f_size = f_size

    @classmethod
    def from_file(cls, path: str) -> _PYCHeader:
        with open(path, "rb") as handle:
            raw_bytes = handle.read(cls.SIZE)
        return cls(*struct.unpack("4s3I", raw_bytes))


def load_precompiled_plugin(path: str, check_context: CheckContext) -> bool:
    """Loads the given check or check include plugin into the given
    check context.

    To improve loading speed the files are not read directly. The files are
    python byte-code compiled before in case it has not been done before. In
    case there is already a compiled file that is newer than the current one,
    then the precompiled file is loaded.

    Returns `True` if something has been compiled, else `False`.
    """

    # https://docs.python.org/3/library/py_compile.html
    # HACK:
    precompiled_path = _precompiled_plugin_path(path)

    do_compile = not _is_plugin_precompiled(path, precompiled_path)
    if do_compile:
        console.vverbose(f"Precompile {path} to {precompiled_path}\n")
        store.makedirs(os.path.dirname(precompiled_path))
        py_compile.compile(path, precompiled_path, doraise=True)
        # The original file is from the version so the calculated mode is world readable...
        os.chmod(precompiled_path, 0o640)

    exec(marshal.loads(Path(precompiled_path).read_bytes()[_PYCHeader.SIZE :]), check_context)

    return do_compile


def _is_plugin_precompiled(path: str, precompiled_path: str) -> bool:
    # Check precompiled file header
    try:
        header = _PYCHeader.from_file(precompiled_path)
    except (FileNotFoundError, struct.error):
        return False

    if header.magic != _MAGIC_NUMBER:
        return False

    # Skip the hash and assure that the timestamp format is used, i.e. the hash is 0.
    # For further details see: https://www.python.org/dev/peps/pep-0552/#id15
    assert header.hash == 0

    return int(os.stat(path).st_mtime) == header.origin_mtime


def _precompiled_plugin_path(path: str) -> str:
    is_local = path.startswith(str(cmk.utils.paths.local_checks_dir))
    return os.path.join(
        cmk.utils.paths.precompiled_checks_dir,
        "local" if is_local else "builtin",
        os.path.basename(path),
    )


def _set_check_variable_defaults(
    variables: dict[str, Any],
    context_idents: list[str],
    skip_names: set[str] | None = None,
) -> None:
    """Save check variables for e.g. after config loading that the config can
    be added to the check contexts."""
    for varname, value in variables.items():
        if skip_names is not None and varname in skip_names:
            continue

        if varname.startswith("_"):
            continue

        # NOTE: Classes and builtin functions are callable, too!
        if callable(value) or isinstance(value, types.ModuleType):
            continue

        _check_variable_defaults[varname] = copy.copy(value)

        # Keep track of which variable needs to be set to which context
        _check_variables.setdefault(varname, []).extend(context_idents)


def set_check_variables(check_variables: CheckVariables) -> None:
    """Update the check related config variables in the relevant check contexts"""
    for varname, value in check_variables.items():
        for context_ident in _check_variables[varname]:
            # This case is important for discovery rulesets which are accessed in legacy-includes.
            # Without the "[:]", we would write the value to a variable in the check plugin.
            # However, we want to write it to the variable in the legacy-include.
            if isinstance(_check_contexts[context_ident][varname], list):
                _check_contexts[context_ident][varname][:] = value
            else:
                _check_contexts[context_ident][varname] = value


def get_check_variables() -> CheckVariables:
    """Returns the currently effective check variable settings

    Since the variables are only stored in the individual check contexts and not stored
    in a central place, this function needs to collect the values from the check contexts.
    We assume a single variable has the same value in all relevant contexts, which means
    that it is enough to get the variable from the first context."""
    check_config = {}
    for varname, context_ident_list in _check_variables.items():
        check_config[varname] = _check_contexts[context_ident_list[0]][varname]
    return check_config


def get_check_context(check_plugin_name: CheckPluginNameStr) -> CheckContext:
    """Returns the context dictionary of the given check plugin"""
    return _check_contexts[check_plugin_name]


# FIXME: Clear / unset all legacy variables to prevent confusions in other code trying to
# use the legacy variables which are not set by newer checks.
def convert_check_info() -> None:  # pylint: disable=too-many-branches
    check_info_defaults: CheckInfo = {
        "check_function": None,
        "inventory_function": None,
        "parse_function": None,
        "group": None,
        "snmp_info": None,
        "snmp_scan_function": None,
        # The 'handle_empty_info' feature predates the 'parse_function'
        # and is not needed nor used anymore.
        "handle_empty_info": False,
        # The handle_real_time_checks was only used to determine the valid choices of the
        # WATO rule, these are now hardcoded.
        "handle_real_time_checks": False,
        "default_levels_variable": None,
        "node_info": False,
        "extra_sections": [],
        "service_description": None,
        "has_perfdata": False,
        "management_board": None,
        "supersedes": None,
    }

    for check_plugin_name, info in check_info.items():
        section_name = section_name_of(check_plugin_name)

        if not isinstance(info, dict):
            # Convert check declaration from old style to new API. We need some Kung Fu to
            # explain this typing chaos to mypy, otherwise info has the funny type <nothing>.
            old_skool_info: Any = info
            check_function, descr, has_perfdata, inventory_function = old_skool_info

            scan_function = snmp_scan_functions.get(
                check_plugin_name, snmp_scan_functions.get(section_name)
            )

            check_info[check_plugin_name] = {
                "check_function": check_function,
                "service_description": descr,
                "has_perfdata": bool(has_perfdata),
                "inventory_function": inventory_function,
                # Insert check name as group if no group is being defined
                "group": check_plugin_name,
                "snmp_info": snmp_info.get(check_plugin_name),
                # Sometimes the scan function is assigned to the check_plugin_name
                # rather than to the base name.
                "snmp_scan_function": scan_function,
                # The 'handle_empty_info' feature predates the 'parse_function'
                # and is not needed nor used anymore.
                "handle_empty_info": False,
                "handle_real_time_checks": False,
                "default_levels_variable": check_default_levels.get(check_plugin_name),
                "node_info": False,
                "parse_function": None,
                "extra_sections": [],
                "management_board": None,
            }
        else:
            # Ensure that there are only the known keys set. Is meant to detect typos etc.
            for key in info:
                if key != "includes" and key not in check_info_defaults:
                    raise MKGeneralException(
                        "The check '%s' declares an unexpected key '%s' in 'check_info'."
                        % (check_plugin_name, key)
                    )

            # Check does already use new API. Make sure that all keys are present,
            # extra check-specific information into file-specific variables.
            for key, val in check_info_defaults.items():
                info.setdefault(key, val)

            # Include files are related to the check file (= the section_name),
            # not to the (sub-)check. So we keep them in check_includes.
            check_includes.setdefault(section_name, [])
            check_includes[section_name] += info.get("includes", [])

    # Make sure that setting for node_info of check and subcheck matches
    for check_plugin_name, info in check_info.items():
        if "." in check_plugin_name:
            section_name = section_name_of(check_plugin_name)
            if section_name not in check_info:
                if info["node_info"]:
                    raise MKGeneralException(
                        "Invalid check implementation: node_info for %s is "
                        "True, but base check %s not defined" % (check_plugin_name, section_name)
                    )

            elif check_info[section_name]["node_info"] != info["node_info"]:
                raise MKGeneralException(
                    "Invalid check implementation: node_info for %s "
                    "and %s are different." % ((section_name, check_plugin_name))
                )

    # Now gather snmp_info and snmp_scan_function back to the
    # original arrays. Note: these information is tied to a "agent section",
    # not to a check. Several checks may use the same SNMP info and scan function.
    for check_plugin_name, info in check_info.items():
        section_name = section_name_of(check_plugin_name)
        if info["snmp_info"] and section_name not in snmp_info:
            snmp_info[section_name] = info["snmp_info"]

        if info["snmp_scan_function"] and section_name not in snmp_scan_functions:
            snmp_scan_functions[section_name] = info["snmp_scan_function"]


AUTO_MIGRATION_ERR_MSG = (
    "Failed to auto-migrate legacy plugin to %s: %s\n"
    "Please refer to Werk 10601 for more information.\n"
)


def _extract_agent_and_snmp_sections(
    *,
    validate_creation_kwargs: bool,
) -> list[str]:
    """Here comes the next layer of converting-to-"new"-api.

    For the new check-API in cmk/base/api/agent_based, we use the accumulated information
    in check_info, snmp_scan_functions and snmp_info to create API compliant section plugins.
    """
    errors = []
    # start with the "main"-checks, the ones without '.' in their names:
    for check_plugin_name in sorted(check_info, key=lambda name: ("." in name, name)):
        section_name = section_name_of(check_plugin_name)

        if agent_based_register.is_registered_section_plugin(SectionName(section_name)):
            continue

        check_info_dict = check_info.get(section_name, check_info[check_plugin_name])
        try:
            if section_name in snmp_info:
                agent_based_register.add_section_plugin(
                    create_snmp_section_plugin_from_legacy(
                        section_name,
                        check_info_dict,
                        snmp_scan_functions[section_name],
                        snmp_info[section_name],
                        validate_creation_kwargs=validate_creation_kwargs,
                    )
                )
            else:
                agent_based_register.add_section_plugin(
                    create_agent_section_plugin_from_legacy(
                        section_name,
                        check_info_dict,
                        validate_creation_kwargs=validate_creation_kwargs,
                    )
                )
        except (NotImplementedError, KeyError, AssertionError, ValueError) as exc:
            # NOTE: missing section pugins may lead to missing data for a check plugin
            #       *or* to more obscure errors, when a check/inventory plugin will be
            #       passed un-parsed data unexpectedly.
            if cmk.utils.debug.enabled():
                raise MKGeneralException(exc) from exc
            errors.append(AUTO_MIGRATION_ERR_MSG % ("section", check_plugin_name))

    return errors


def _extract_check_plugins(
    *,
    validate_creation_kwargs: bool,
) -> list[str]:
    """Here comes the next layer of converting-to-"new"-api.

    For the new check-API in cmk/base/api/agent_based, we use the accumulated information
    in check_info to create API compliant check plugins.
    """
    errors = []
    for check_plugin_name, check_info_dict in sorted(check_info.items()):
        # skip pure section declarations:
        if check_info_dict.get("service_description") is None:
            continue
        try:
            present_plugin = agent_based_register.get_check_plugin(
                CheckPluginName(maincheckify(check_plugin_name))
            )
            if present_plugin is not None and present_plugin.module is not None:
                # module is not None => it's a new plugin
                # (allow loading multiple times, e.g. update-config)
                # implemented here instead of the agent based register so that new API code does not
                # need to include any handling of legacy cases
                raise ValueError(
                    f"Legacy check plugin still exists for check plugin {check_plugin_name}. "
                    "Please remove legacy plugin."
                )
            agent_based_register.add_check_plugin(
                create_check_plugin_from_legacy(
                    check_plugin_name,
                    check_info_dict,
                    check_info.get(check_plugin_name.split(".")[0], {}).get("extra_sections", []),
                    factory_settings,
                    get_check_context,
                    validate_creation_kwargs=validate_creation_kwargs,
                )
            )
        except (NotImplementedError, KeyError, AssertionError, ValueError) as exc:
            # NOTE: as a result of a missing check plugin, the corresponding services
            #       will be silently droppend on most (all?) occasions.
            if cmk.utils.debug.enabled():
                raise MKGeneralException(exc) from exc
            errors.append(AUTO_MIGRATION_ERR_MSG % ("check plugin", check_plugin_name))

    return errors


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


def _get_plugin_parameters(
    *,
    host_name: HostName,
    default_parameters: ParametersTypeAlias | None,
    ruleset_name: RuleSetName | None,
    ruleset_type: Literal["all", "merged"],
    rules_getter_function: Callable[[RuleSetName], Sequence[RuleSpec]],
) -> None | Parameters | list[Parameters]:
    if default_parameters is None:
        # This means the function will not accept any params.
        return None
    if ruleset_name is None:
        # This means we have default params, but no rule set.
        # Not very sensical for discovery functions, but not forbidden by the API either.
        return Parameters(default_parameters)

    config_cache = get_config_cache()
    rules = rules_getter_function(ruleset_name)

    if ruleset_type == "all":
        host_rules = config_cache.host_extra_conf(host_name, rules)
        host_rules.append(default_parameters)
        return [Parameters(d) for d in host_rules]

    if ruleset_type == "merged":
        return Parameters(
            {
                **default_parameters,
                **config_cache.host_extra_conf_merged(host_name, rules),
            }
        )

    # validation should have prevented this
    raise NotImplementedError(f"unknown discovery rule set type {ruleset_type!r}")


def get_discovery_parameters(
    host_name: HostName,
    check_plugin: CheckPlugin,
) -> None | Parameters | list[Parameters]:
    return _get_plugin_parameters(
        host_name=host_name,
        default_parameters=check_plugin.discovery_default_parameters,
        ruleset_name=check_plugin.discovery_ruleset_name,
        ruleset_type=check_plugin.discovery_ruleset_type,
        rules_getter_function=agent_based_register.get_discovery_ruleset,
    )


def get_host_label_parameters(
    host_name: HostName,
    host_label_plugin: PHostLabelDiscoveryPlugin,
) -> None | Parameters | list[Parameters]:
    return _get_plugin_parameters(
        host_name=host_name,
        default_parameters=host_label_plugin.host_label_default_parameters,
        ruleset_name=host_label_plugin.host_label_ruleset_name,
        ruleset_type=host_label_plugin.host_label_ruleset_type,
        rules_getter_function=agent_based_register.get_host_label_ruleset,
    )


def compute_check_parameters(
    host: HostName,
    plugin_name: CheckPluginName,
    item: Item,
    params: LegacyCheckParameters,
    configured_parameters: TimespecificParameters | None = None,
) -> TimespecificParameters:
    """Compute parameters for a check honoring factory settings,
    default settings of user in main.mk, check_parameters[] and
    the values code in autochecks (given as parameter params)"""
    plugin = agent_based_register.get_check_plugin(plugin_name)
    if plugin is None:  # handle vanished check plugin
        return TimespecificParameters()

    if configured_parameters is None:
        configured_parameters = _get_configured_parameters(host, plugin, item)

    return _update_with_configured_check_parameters(
        _update_with_default_check_parameters(plugin.check_default_parameters, params),
        configured_parameters,
    )


def _update_with_default_check_parameters(
    check_default_parameters: ParametersTypeAlias | None,
    params: LegacyCheckParameters,
) -> LegacyCheckParameters:
    if check_default_parameters is None:
        return params

    # Handle case where parameter is None but the type of the
    # default value is a dictionary. This is for example the
    # case if a check type has gotten parameters in a new version
    # but inventory of the old version left None as a parameter.
    # Also from now on we support that the inventory simply puts
    # None as a parameter. We convert that to an empty dictionary
    # that will be updated with the factory settings and default
    # levels, if possible.
    if params is None:
        params = {}

    if not isinstance(params, dict):
        # if discovered params is not updateable, it wins
        return params

    default_params = unwrap_parameters(check_default_parameters)
    if not isinstance(default_params, dict):
        # if default params are not updatetable, discovered params win
        return params

    # Merge params from inventory onto default parameters (if params is not updateable, it wins):
    return {**default_params, **params}


def _update_with_configured_check_parameters(
    params: LegacyCheckParameters,
    configured_parameters: TimespecificParameters,
) -> TimespecificParameters:
    return TimespecificParameters(
        [
            *configured_parameters.entries,
            TimespecificParameterSet.from_parameters(params),
        ]
    )


def _get_configured_parameters(
    host: HostName,
    plugin: CheckPlugin,
    item: Item,
) -> TimespecificParameters:
    config_cache = get_config_cache()
    descr = service_description(host, plugin.name, item)

    # parameters configured via check_parameters
    extra = [
        TimespecificParameterSet.from_parameters(p)
        for p in config_cache.service_extra_conf(host, descr, check_parameters)
    ]

    if plugin.check_ruleset_name is None:
        return TimespecificParameters(extra)

    return TimespecificParameters(
        [
            # parameters configured via checkgroup_parameters
            TimespecificParameterSet.from_parameters(p)
            for p in _get_checkgroup_parameters(
                config_cache,
                host,
                str(plugin.check_ruleset_name),
                item,
                descr,
            )
        ]
        + extra
    )


def _get_checkgroup_parameters(
    config_cache: ConfigCache,
    host: HostName,
    checkgroup: RulesetName,
    item: Item,
    descr: ServiceName,
) -> list[LegacyCheckParameters]:
    rules = checkgroup_parameters.get(checkgroup)
    if rules is None:
        return []

    try:
        # checks without an item
        if item is None and checkgroup not in service_rule_groups:
            return config_cache.host_extra_conf(host, rules)

        # checks with an item need service-specific rules
        match_object = config_cache.ruleset_match_object_for_checkgroup_parameters(
            host, item, descr
        )
        return list(
            config_cache.ruleset_matcher.get_service_ruleset_values(
                match_object, rules, is_binary=False
            )
        )
    except MKGeneralException as e:
        raise MKGeneralException(str(e) + f" (on host {host}, checkgroup {checkgroup})")


def lookup_mgmt_board_ip_address(
    config_cache: ConfigCache, host_name: HostName
) -> HostAddress | None:
    mgmt_address: Final = config_cache.management_address(host_name)
    try:
        mgmt_ipa = None if mgmt_address is None else HostAddress(ipaddress.ip_address(mgmt_address))
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
            override_dns=fake_dns,
            is_dyndns_host=config_cache.is_dyndns_host(host_name),
            force_file_cache_renewal=not use_dns_cache,
        )
    except MKIPAddressLookupError:
        return None


def lookup_ip_address(
    config_cache: ConfigCache,
    host_name: HostName,
    *,
    family: socket.AddressFamily | AddressFamily | None = None,
) -> HostAddress | None:
    if ConfigCache.address_family(host_name) is AddressFamily.NO_IP:
        # TODO(ml): [IPv6] Silently override the `family` parameter.  Where
        # that is necessary, the callers are highly unlikely to handle IPv6
        # and DUAL_STACK correctly.
        return None
    if family is None:
        family = config_cache.default_address_family(host_name)
    if isinstance(family, socket.AddressFamily):
        family = AddressFamily.from_socket(family)
    return ip_lookup.lookup_ip_address(
        host_name=host_name,
        family=family,
        # TODO(ml): [IPv6] What about dual stack?
        configured_ip_address=(ipaddresses if AddressFamily.IPv4 in family else ipv6addresses).get(
            host_name
        ),
        simulation_mode=simulation_mode,
        is_snmp_usewalk_host=(
            config_cache.get_snmp_backend(host_name) is SNMPBackendEnum.STORED_WALK
            and config_cache.is_snmp_host(host_name)
        ),
        override_dns=fake_dns,
        is_dyndns_host=config_cache.is_dyndns_host(host_name),
        force_file_cache_renewal=not use_dns_cache,
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


class ConfigCache:
    def __init__(self) -> None:
        super().__init__()
        self.__enforced_services_table: dict[
            HostName,
            Mapping[
                ServiceID,
                tuple[RulesetName, ConfiguredService],
            ],
        ] = {}
        self.__is_piggyback_host: dict[HostName, bool] = {}
        self.__snmp_config: dict[tuple[HostName, HostAddress, SourceType], SNMPHostConfig] = {}
        self.__hwsw_inventory_parameters: dict[HostName, HWSWInventoryParameters] = {}
        self.__explicit_host_attributes: dict[HostName, dict[str, str]] = {}
        self.__computed_datasources: dict[HostName, ComputedDataSources] = {}
        self.__discovery_check_parameters: dict[HostName, DiscoveryCheckParameters] = {}
        self.__active_checks: dict[HostName, list[tuple[str, list[Any]]]] = {}
        self.__special_agents: dict[HostName, Sequence[tuple[str, Mapping[str, object]]]] = {}
        self.__hostgroups: dict[HostName, Sequence[HostgroupName]] = {}
        self.__contactgroups: dict[HostName, Sequence[ContactgroupName]] = {}
        self.__explicit_check_command: dict[HostName, HostCheckCommand] = {}
        self.__snmp_fetch_interval: dict[tuple[HostName, SectionName], int | None] = {}
        self.__disabled_snmp_sections: dict[HostName, frozenset[SectionName]] = {}
        self.__labels: dict[HostName, Labels] = {}
        self.__label_sources: dict[HostName, LabelSources] = {}
        self.__notification_plugin_parameters: dict[tuple[HostName, CheckPluginNameStr], dict] = {}
        self._initialize_caches()

    def is_cluster(self, host_name: HostName) -> bool:
        return host_name in self.all_configured_clusters()

    def initialize(self) -> ConfigCache:
        self._initialize_caches()
        self._setup_clusters_nodes_cache()

        self._all_configured_clusters = set(strip_tags(list(clusters)))
        self._all_configured_realhosts = set(strip_tags(all_hosts))
        self._all_configured_hosts = (
            self._all_configured_realhosts | self._all_configured_clusters | set(get_shadow_hosts())
        )

        tag_to_group_map = ConfigCache.get_tag_to_group_map()
        self._collect_hosttags(tag_to_group_map)

        self.ruleset_matcher = ruleset_matcher.RulesetMatcher(
            tag_to_group_map=tag_to_group_map,
            host_tags=host_tags,
            host_paths=self._host_paths,
            labels=LabelManager(
                host_labels,
                host_label_rules,
                service_label_rules,
                self._discovered_labels_of_service,
            ),
            clusters_of=self._clusters_of_cache,
            nodes_of=self._nodes_of_cache,
            all_configured_hosts=self._all_configured_hosts,
        )

        self._all_active_clusters = set(_filter_active_hosts(self, self._all_configured_clusters))
        self._all_active_realhosts = set(_filter_active_hosts(self, self._all_configured_realhosts))
        self._all_active_hosts = self._all_active_realhosts | self._all_active_clusters

        self.ruleset_matcher.ruleset_optimizer.set_all_processed_hosts(self._all_active_hosts)

        return self

    def _initialize_caches(self) -> None:
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
        self.__disabled_snmp_sections.clear()
        self.__labels.clear()
        self.__label_sources.clear()
        self.__notification_plugin_parameters.clear()
        self._check_table_cache = _config_cache.get("check_tables")

        self._cache_section_name_of: dict[CheckPluginNameStr, str] = {}

        self._cache_match_object_service: dict[
            tuple[HostName, ServiceName], RulesetMatchObject
        ] = {}
        self._cache_match_object_service_checkgroup: dict[
            tuple[HostName, Item, ServiceName], RulesetMatchObject
        ] = {}
        self._cache_match_object_host: dict[HostName, RulesetMatchObject] = {}

        # Host lookup

        self._all_configured_hosts = set()
        self._all_configured_clusters = set()
        self._all_configured_realhosts = set()
        self._all_active_clusters = set()
        self._all_active_realhosts = set()

        # Reference hostname -> dirname including /
        self._host_paths: dict[HostName, str] = ConfigCache._get_host_paths(host_paths)

        # Host tags
        self._hosttags: dict[HostName, TagIDs] = {}

        # Autochecks cache
        self._autochecks_manager = AutochecksManager()

        # Caches for nodes and clusters
        self._clusters_of_cache: dict[HostName, list[HostName]] = {}
        self._nodes_of_cache: dict[HostName, list[HostName]] = {}
        self._host_of_clustered_service_cache: dict[
            tuple[HostName, ServiceName, tuple | None], HostName
        ] = {}
        self._check_mk_check_interval: dict[HostName, float] = {}

    def make_ipmi_fetcher(self, host_name: HostName, ip_address: HostAddress) -> IPMIFetcher:
        ipmi_credentials = self.management_credentials(host_name, "ipmi")
        return IPMIFetcher(
            address=ip_address,
            username=ipmi_credentials.get("username"),
            password=ipmi_credentials.get("password"),
        )

    def make_program_commandline(self, host_name: HostName, ip_address: HostAddress | None) -> str:
        """
        raise: LookupError if no datasource is configured.
        """
        return self.translate_commandline(
            host_name,
            ip_address,
            self.host_extra_conf(host_name, datasource_programs)[0],
        )

    def make_special_agent_cmdline(
        self,
        hostname: HostName,
        ip_address: HostAddress | None,
        agentname: str,
        params: Mapping[str, object],
    ) -> str:
        """
        Raises:
            KeyError if the special agent is deactivated.

        """

        def _make_source_path(agentname: str) -> Path:
            file_name = "agent_%s" % agentname
            local_path = cmk.utils.paths.local_agents_dir / "special" / file_name
            if local_path.exists():
                return local_path
            return Path(cmk.utils.paths.agents_dir) / "special" / file_name

        def _make_source_args(
            hostname: HostName,
            ip_address: HostAddress | None,
            agentname: str,
        ) -> str:
            info_func = special_agent_info[agentname]
            # TODO: CMK-3812 (see above)
            agent_configuration = info_func(params, hostname, ip_address)
            args = commandline_arguments(hostname, None, agent_configuration)
            return self.translate_commandline(hostname, ip_address, args)

        path = _make_source_path(agentname)
        args = _make_source_args(
            hostname,
            ip_address,
            agentname,
        )
        return f"{path} {args}"

    def make_piggyback_fetcher(
        self, host_name: HostName, ip_address: HostAddress | None
    ) -> PiggybackFetcher:
        return PiggybackFetcher(
            hostname=host_name,
            address=ip_address,
            time_settings=self.get_piggybacked_hosts_time_settings(piggybacked_hostname=host_name),
        )

    def make_snmp_fetcher(
        self,
        host_name: HostName,
        ip_address: HostAddress,
        *,
        on_scan_error: OnError,
        selected_sections: SectionNameCollection,
        snmp_config: SNMPHostConfig,
    ) -> SNMPFetcher:
        return SNMPFetcher(
            sections=self._make_snmp_sections(
                host_name,
                checking_sections=self.make_checking_sections(
                    host_name, selected_sections=selected_sections
                ),
            ),
            on_error=on_scan_error,
            missing_sys_description=self._missing_sys_description(host_name),
            do_status_data_inventory=self.hwsw_inventory_parameters(
                host_name
            ).status_data_inventory,
            section_store_path=make_persisted_section_dir(
                host_name, fetcher_type=FetcherType.SNMP, ident="snmp"
            ),
            snmp_config=snmp_config,
        )

    def make_tcp_fetcher(self, host_name: HostName, ip_address: HostAddress) -> TCPFetcher:
        return TCPFetcher(
            host_name=host_name,
            address=(ip_address, self._agent_port(host_name)),
            family=self.default_address_family(host_name),
            timeout=self._tcp_connect_timeout(host_name),
            encryption_handling=self._encryption_handling(host_name),
            pre_shared_secret=self._symmetric_agent_encryption(host_name),
        )

    def make_agent_parser(
        self,
        host_name: HostName,
        section_store: SectionStore[AgentRawDataSection],
        *,
        keep_outdated: bool,
        logger: logging.Logger,
    ) -> AgentParser:
        return AgentParser(
            host_name,
            section_store,
            keep_outdated=keep_outdated,
            check_interval=self.check_mk_check_interval(host_name),
            translation=get_piggyback_translations(host_name),
            encoding_fallback=fallback_agent_output_encoding,
            simulation=agent_simulator,  # name mismatch
            logger=logger,
        )

    def _discovered_labels_of_service(
        self,
        hostname: HostName,
        service_desc: ServiceName,
    ) -> Labels:
        return {
            label.name: label.value
            for label in self._autochecks_manager.discovered_labels_of(
                hostname,
                service_desc,
                service_description,  # this is the global function!
            ).values()
        }

    @staticmethod
    def get_tag_to_group_map() -> TagIDToTaggroupID:
        tags = cmk.utils.tags.get_effective_tag_config(tag_config)
        return ruleset_matcher.get_tag_to_group_map(tags)

    def ip_lookup_config(self, host_name: HostName) -> ip_lookup.IPLookupConfig:
        return ip_lookup.IPLookupConfig(
            hostname=host_name,
            address_family=ConfigCache.address_family(host_name),
            is_snmp_host=self.is_snmp_host(host_name),
            snmp_backend=self.get_snmp_backend(host_name),
            default_address_family=self.default_address_family(host_name),
            management_address=self.management_address(host_name),
            is_dyndns_host=self.is_dyndns_host(host_name),
        )

    def make_snmp_config(
        self, host_name: HostName, ip_address: HostAddress, source_type: SourceType
    ) -> SNMPHostConfig:
        with contextlib.suppress(KeyError):
            return self.__snmp_config[(host_name, ip_address, source_type)]

        return self.__snmp_config.setdefault(
            (host_name, ip_address, source_type),
            SNMPHostConfig(
                is_ipv6_primary=self.default_address_family(host_name) is socket.AF_INET6,
                hostname=host_name,
                ipaddress=ip_address,
                credentials=(
                    self._snmp_credentials(host_name)
                    if source_type is SourceType.HOST
                    else self.management_credentials(host_name, "snmp")
                ),
                port=self._snmp_port(host_name),
                is_bulkwalk_host=(
                    self.in_binary_hostlist(
                        host_name,
                        bulkwalk_hosts
                        if source_type is SourceType.HOST
                        else management_bulkwalk_hosts,
                    )
                ),
                is_snmpv2or3_without_bulkwalk_host=self.in_binary_hostlist(
                    host_name, snmpv2c_hosts
                ),
                bulk_walk_size_of=self._bulk_walk_size(host_name),
                timing=self._snmp_timing(host_name),
                oid_range_limits={
                    SectionName(name): rule
                    for name, rule in reversed(
                        self.host_extra_conf(host_name, snmp_limit_oid_range)
                    )
                },
                snmpv3_contexts=self.host_extra_conf(host_name, snmpv3_contexts),
                character_encoding=self._snmp_character_encoding(host_name),
                snmp_backend=self.get_snmp_backend(host_name),
            ),
        )

    def make_checking_sections(
        self, hostname: HostName, *, selected_sections: SectionNameCollection
    ) -> frozenset[SectionName]:
        if selected_sections is not NO_SELECTION:
            checking_sections = selected_sections
        else:
            checking_sections = frozenset(
                agent_based_register.get_relevant_raw_sections(
                    check_plugin_names=self.check_table(
                        hostname,
                        filter_mode=FilterMode.INCLUDE_CLUSTERED,
                        skip_ignored=True,
                    ).needed_check_names(),
                    inventory_plugin_names=(),
                )
            )
        return frozenset(
            s
            for s in checking_sections
            if agent_based_register.is_registered_snmp_section_plugin(s)
        )

    def invalidate_host_config(self, hostname: HostName) -> None:
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
        self.__disabled_snmp_sections.clear()
        self.__labels.clear()
        self.__label_sources.clear()
        self.__notification_plugin_parameters.clear()

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
        *,
        use_cache: bool = True,
        skip_autochecks: bool = False,
        filter_mode: FilterMode = FilterMode.NONE,
        skip_ignored: bool = True,
    ) -> HostCheckTable:
        cache_key = (hostname, filter_mode, skip_autochecks, skip_ignored) if use_cache else None
        if cache_key:
            with contextlib.suppress(KeyError):
                return self._check_table_cache[cache_key]

        host_check_table = HostCheckTable(
            services=_aggregate_check_table_services(
                hostname,
                config_cache=self,
                skip_autochecks=skip_autochecks,
                skip_ignored=skip_ignored,
                filter_mode=filter_mode,
            )
        )

        if cache_key:
            self._check_table_cache[cache_key] = host_check_table

        return host_check_table

    def _sorted_services(self, hostname: HostName) -> Sequence[ConfiguredService]:
        # This method is only useful for the monkeypatching orgy of the "unit"-tests.
        return sorted(
            self.check_table(hostname).values(),
            key=lambda service: service.description,
        )

    def configured_services(self, hostname: HostName) -> Sequence[ConfiguredService]:
        services = self._sorted_services(hostname)
        if is_cmc():
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

    def enforced_services_table(
        self, hostname: HostName
    ) -> Mapping[ServiceID, tuple[RulesetName, ConfiguredService],]:
        """Return a table of enforced services

        Note: We need to reverse the order of the enforced services.
        Users assume that earlier rules have precedence over later ones.
        Important if there are two rules for a host with the same combination of plugin name
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
                        description=descr,
                        parameters=compute_check_parameters(
                            self.host_of_clustered_service(hostname, descr),
                            check_plugin_name,
                            item,
                            {},
                            configured_parameters=TimespecificParameters((params,)),
                        ),
                        discovered_parameters={},
                        service_labels={},
                    ),
                )
                for checkgroup_name, ruleset in static_checks.items()
                for check_plugin_name, item, params in (
                    ConfigCache._sanitize_enforced_entry(*entry)
                    for entry in reversed(self.host_extra_conf(hostname, ruleset))
                )
                if (descr := service_description(hostname, check_plugin_name, item))
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
            if self.is_cluster(host_name):
                return HWSWInventoryParameters.from_raw({})

            # TODO: Use dict(self.active_checks).get("cmk_inv", [])?
            rules = active_checks.get("cmk_inv")
            if rules is None:
                return HWSWInventoryParameters.from_raw({})

            # 'host_extra_conf' is already cached thus we can
            # use it after every check cycle.
            entries = self.host_extra_conf(host_name, rules)

            if not entries:
                return HWSWInventoryParameters.from_raw({})  # No matching rule -> disable

            # Convert legacy rules to current dict format (just like the valuespec)
            return HWSWInventoryParameters.from_raw({} if entries[0] is None else entries[0])

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
        mgmt_host_address = host_attributes.get(host_name, {}).get("management_address")
        if mgmt_host_address:
            return mgmt_host_address

        if self.default_address_family(host_name) is socket.AF_INET6:
            return ipv6addresses.get(host_name)

        return ipaddresses.get(host_name)

    @overload
    def management_credentials(
        self, host_name: HostName, protocol: Literal["snmp"]
    ) -> SNMPCredentials:
        ...

    @overload
    def management_credentials(
        self, host_name: HostName, protocol: Literal["ipmi"]
    ) -> IPMICredentials:
        ...

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
        rule_settings = self.host_extra_conf(host_name, management_board_config)
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
        alias_ = self.explicit_host_attributes(host_name).get("alias")
        if alias_:
            return alias_

        # Alias by rule matching
        default: Sequence[RuleSpec[HostName]] = []
        aliases = self.host_extra_conf(host_name, extra_host_conf.get("alias", default))

        # Fallback alias
        if not aliases:
            return host_name

        # First rule match
        return aliases[0]

    def parents(self, host_name: HostName) -> list[str]:
        """Returns the parents of a host configured via ruleset "parents"

        Use only those parents which are defined and active in all_hosts"""
        parent_candidates = set()

        # Parent by explicit matching
        explicit_parents = self.explicit_host_attributes(host_name).get("parents")
        if explicit_parents:
            parent_candidates.update(explicit_parents.split(","))

        # Respect the ancient parents ruleset. This can not be configured via WATO and should be removed one day
        for parent_names in self.host_extra_conf(host_name, parents):
            parent_candidates.update(parent_names.split(","))

        return list(parent_candidates.intersection(self.all_active_realhosts()))

    def agent_connection_mode(self, host_name: HostName) -> HostAgentConnectionMode:
        return connection_mode_from_host_config(self.explicit_host_attributes(host_name))

    def extra_host_attributes(self, host_name: HostName) -> ObjectAttributes:
        attrs: ObjectAttributes = {}
        attrs.update(self.explicit_host_attributes(host_name))

        for key, ruleset in extra_host_conf.items():
            if key in attrs:
                # An explicit value is already set
                values = [attrs[key]]
            else:
                values = self.host_extra_conf(host_name, ruleset)
                if not values:
                    continue

            if values[0] is not None:
                attrs[key] = values[0]

        # Convert _keys to uppercase. Affects explicit and rule based keys
        attrs = {key.upper() if key[0] == "_" else key: value for key, value in attrs.items()}
        return attrs

    def computed_datasources(self, host_name: HostName) -> ComputedDataSources:
        with contextlib.suppress(KeyError):
            return self.__computed_datasources[host_name]

        return self.__computed_datasources.setdefault(
            host_name, cmk.utils.tags.compute_datasources(ConfigCache.tags(host_name))
        )

    def is_tcp_host(self, host_name: HostName) -> bool:
        return self.computed_datasources(host_name).is_tcp

    def is_snmp_host(self, host_name: HostName) -> bool:
        return self.computed_datasources(host_name).is_snmp

    def is_piggyback_host(self, host_name: HostName) -> bool:
        def get_is_piggyback_host() -> bool:
            tag_groups: Final = ConfigCache.tags(host_name)
            if tag_groups["piggyback"] == "piggyback":
                return True
            if tag_groups["piggyback"] == "no-piggyback":
                return False

            # for clusters with an auto-piggyback tag check if nodes have piggyback data
            if self.is_cluster(host_name) and (nodes := self.nodes_of(host_name)) is not None:
                return any(self._has_piggyback_data(node) for node in nodes)

            # Legacy automatic detection
            return self._has_piggyback_data(host_name)

        with contextlib.suppress(KeyError):
            return self.__is_piggyback_host[host_name]

        return self.__is_piggyback_host.setdefault(host_name, get_is_piggyback_host())

    def is_ping_host(self, host_name: HostName) -> bool:
        return not (
            self.is_snmp_host(host_name)
            or self.is_tcp_host(host_name)
            or self.is_piggyback_host(host_name)
            or self.has_management_board(host_name)
        )

    def is_dyndns_host(self, host_name: HostName) -> bool:
        return self.in_binary_hostlist(host_name, dyndns_hosts)

    def is_dual_host(self, host_name: HostName) -> bool:
        return self.is_tcp_host(host_name) and self.is_snmp_host(host_name)

    def is_all_agents_host(self, host_name: HostName) -> bool:
        return self.computed_datasources(host_name).is_all_agents_host

    def is_all_special_agents_host(self, host_name: HostName) -> bool:
        return self.computed_datasources(host_name).is_all_special_agents_host

    def discovery_check_parameters(self, host_name: HostName) -> DiscoveryCheckParameters:
        """Compute the parameters for the discovery check for a host"""

        def make_discovery_check_parameters() -> DiscoveryCheckParameters:
            service_discovery_name = ConfigCache.service_discovery_name()
            if self.is_ping_host(host_name) or self.service_ignored(
                host_name, service_discovery_name
            ):
                return DiscoveryCheckParameters.commandline_only_defaults()

            entries = self.host_extra_conf(host_name, periodic_discovery)
            if not entries:
                return DiscoveryCheckParameters.default()

            if (entry := entries[0]) is None or not (check_interval := entry["check_interval"]):
                return DiscoveryCheckParameters.commandline_only_defaults()

            return DiscoveryCheckParameters(
                commandline_only=False,
                check_interval=int(check_interval),
                severity_new_services=int(entry["severity_unmonitored"]),
                severity_vanished_services=int(entry["severity_vanished"]),
                severity_new_host_labels=int(entry.get("severity_new_host_label", 1)),
                rediscovery=entry.get("inventory_rediscovery", {}),
            )

        with contextlib.suppress(KeyError):
            return self.__discovery_check_parameters[host_name]

        return self.__discovery_check_parameters.setdefault(
            host_name, make_discovery_check_parameters()
        )

    def inventory_parameters(
        self, host_name: HostName, plugin: PInventoryPlugin
    ) -> dict[str, object]:
        if plugin.inventory_ruleset_name is None:
            raise ValueError(plugin)

        return {
            **plugin.inventory_default_parameters,
            **self.host_extra_conf_merged(
                host_name, inv_parameters.get(str(plugin.inventory_ruleset_name), [])
            ),
        }

    def custom_checks(self, host_name: HostName) -> list[dict]:
        """Return the free form configured custom checks without formalization"""
        return self.host_extra_conf(host_name, custom_checks)

    def active_checks(self, host_name: HostName) -> list[tuple[str, list[Any]]]:
        """Returns the list of active checks configured for this host

        These are configured using the active check formalization of WATO
        where the whole parameter set is configured using valuespecs.
        """

        def make_active_checks() -> list[tuple[str, list[Any]]]:
            configured_checks: list[tuple[str, list[Any]]] = []
            for plugin_name, ruleset in sorted(active_checks.items(), key=lambda x: x[0]):
                # Skip Check_MK HW/SW Inventory for all ping hosts, even when the
                # user has enabled the inventory for ping only hosts
                if plugin_name == "cmk_inv" and self.is_ping_host(host_name):
                    continue

                entries = self.host_extra_conf(host_name, ruleset)
                if not entries:
                    continue

                configured_checks.append((plugin_name, entries))

            return configured_checks

        with contextlib.suppress(KeyError):
            return self.__active_checks[host_name]

        return self.__active_checks.setdefault(host_name, make_active_checks())

    def special_agents(self, host_name: HostName) -> Sequence[tuple[str, Mapping[str, object]]]:
        def special_agents_impl() -> Sequence[tuple[str, Mapping[str, object]]]:
            matched: list[tuple[str, Mapping[str, object]]] = []
            # Previous to 1.5.0 it was not defined in which order the special agent
            # rules overwrite each other. When multiple special agents were configured
            # for a single host a "random" one was picked (depending on the iteration
            # over config.special_agents.
            # We now sort the matching special agents by their name to at least get
            # a deterministic order of the special agents.
            for agentname, ruleset in sorted(special_agents.items()):
                params = self.host_extra_conf(host_name, ruleset)
                if params:
                    matched.append((agentname, params[0]))
            return matched

        with contextlib.suppress(KeyError):
            return self.__special_agents[host_name]

        return self.__special_agents.setdefault(host_name, special_agents_impl())

    def hostgroups(self, host_name: HostName) -> Sequence[HostgroupName]:
        """Returns the list of hostgroups of this host

        If the host has no hostgroups it will be added to the default hostgroup
        (Nagios requires each host to be member of at least on group)."""

        def hostgroups_impl() -> Sequence[HostgroupName]:
            groups = self.host_extra_conf(host_name, host_groups)
            if not groups:
                return [default_host_group]
            return groups

        with contextlib.suppress(KeyError):
            return self.__hostgroups[host_name]

        return self.__hostgroups.setdefault(host_name, hostgroups_impl())

    def contactgroups(self, host_name: HostName) -> Sequence[ContactgroupName]:
        """Returns the list of contactgroups of this host"""

        def contactgroups_impl() -> Sequence[ContactgroupName]:
            cgrs: list[ContactgroupName] = []

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
            folder_cgrs = []
            for entry in self.host_extra_conf(host_name, host_contactgroups):
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
            entries = self.host_extra_conf(host_name, host_check_commands)
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
        if ConfigCache.address_family(host_name) is AddressFamily.NO_IP:
            return "ok"
        return default_host_check_command

    def _missing_sys_description(self, host_name: HostName) -> bool:
        return self.in_binary_hostlist(host_name, snmp_without_sys_descr)

    def snmp_fetch_interval(self, host_name: HostName, section_name: SectionName) -> int | None:
        """Return the fetch interval of SNMP sections in seconds

        This has been added to reduce the fetch interval of single SNMP sections
        to be executed less frequently than the "Check_MK" service is executed.
        """

        def snmp_fetch_interval_impl() -> int | None:
            section = agent_based_register.get_section_plugin(section_name)
            if not isinstance(section, SNMPSectionPlugin):
                return None  # no values at all for non snmp section

            # Previous to 1.5 "match" could be a check name (including subchecks) instead of
            # only main check names -> section names. This has been cleaned up, but we still
            # need to be compatible. Strip of the sub check part of "match".
            for match, minutes in self.host_extra_conf(
                host_name,
                snmp_check_interval,
            ):
                if match is None or match.split(".")[0] == str(section_name):
                    return minutes * 60  # use first match

            return None

        with contextlib.suppress(KeyError):
            return self.__snmp_fetch_interval[(host_name, section_name)]

        return self.__snmp_fetch_interval.setdefault(
            (host_name, section_name), snmp_fetch_interval_impl()
        )

    def disabled_snmp_sections(self, host_name: HostName) -> frozenset[SectionName]:
        def disabled_snmp_sections_impl() -> frozenset[SectionName]:
            """Return a set of disabled snmp sections"""
            rules = self.host_extra_conf(host_name, snmp_exclude_sections)
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
    ) -> dict[SectionName, SNMPSectionMeta]:
        disabled_sections = self.disabled_snmp_sections(host_name)
        return {
            name: SNMPSectionMeta(
                checking=name in checking_sections,
                disabled=name in disabled_sections,
                redetect=name in checking_sections and agent_based_register.needs_redetection(name),
                fetch_interval=self.snmp_fetch_interval(host_name, name),
            )
            for name in (checking_sections | disabled_sections)
        }

    def _collect_hosttags(self, tag_to_group_map: TagIDToTaggroupID) -> None:
        """Calculate the effective tags for all configured hosts

        WATO ensures that all hosts configured with WATO have host_tags set, but there may also be hosts defined
        by the etc/check_mk/conf.d directory that are not managed by WATO. They may use the old style pipe separated
        all_hosts configuration. Detect it and try to be compatible.
        """
        # Would be better to use self._all_configured_hosts, but that is not possible as long as we need the tags
        # from the old all_hosts / clusters.keys().
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
                self._hosttags[hostname] = set(parts[1:])
                host_tags[hostname] = ConfigCache._tag_list_to_tag_groups(
                    tag_to_group_map, self._hosttags[hostname]
                )

        for shadow_host_name, shadow_host_spec in list(get_shadow_hosts().items()):
            self._hosttags[shadow_host_name] = set(
                shadow_host_spec.get("custom_variables", {}).get("TAGS", "").split()
            )
            host_tags[shadow_host_name] = ConfigCache._tag_list_to_tag_groups(
                tag_to_group_map, self._hosttags[shadow_host_name]
            )

    @staticmethod
    def _tag_groups_to_tag_list(host_path: str, tag_groups: TaggroupIDToTagID) -> TagIDs:
        # The pre 1.6 tags contained only the tag group values (-> chosen tag id),
        # but there was a single tag group added with it's leading tag group id. This
        # was the internal "site" tag that is created by HostAttributeSite.
        tags = {v for k, v in tag_groups.items() if k != "site"}
        tags.add(host_path)
        tags.add("site:%s" % tag_groups["site"])
        return tags

    @staticmethod
    def _tag_list_to_tag_groups(
        tag_to_group_map: TagIDToTaggroupID, tag_list: TagIDs
    ) -> TaggroupIDToTagID:
        # This assumes all needed aux tags of grouped are already in the tag_list

        # Ensure the internal mandatory tag groups are set for all hosts
        # TODO: This immitates the logic of cmk.gui.watolib.CREHost.tag_groups which
        # is currently responsible for calculating the host tags of a host.
        # Would be better to untie the GUI code there and move it over to cmk.utils.tags.
        return {
            "piggyback": "auto-piggyback",
            "networking": "lan",
            "agent": "cmk-agent",
            "criticality": "prod",
            "snmp_ds": "no-snmp",
            "site": omd_site(),
            "address_family": "ip-v4-only",
            # Assume it's an aux tag in case there is a tag configured without known group
            **{tag_to_group_map.get(tag_id, tag_id): tag_id for tag_id in tag_list},
        }

    def tag_list(self, hostname: HostName) -> TagIDs:
        """Returns the list of all configured tags of a host. In case
        a host has no tags configured or is not known, it returns an
        empty list."""
        if hostname in self._hosttags:
            return self._hosttags[hostname]

        # Handle not existing hosts (No need to performance optimize this)
        return ConfigCache._tag_groups_to_tag_list("/", ConfigCache.tags(hostname))

    # TODO: check all call sites and remove this or make it private?
    @staticmethod
    def tags(hostname: HostName) -> TaggroupIDToTagID:
        """Returns the dict of all configured tag groups and values of a host."""
        if hostname in host_tags:
            return host_tags[hostname]

        # Handle not existing hosts (No need to performance optimize this)
        # TODO: This immitates the logic of cmk.gui.watolib.CREHost.tag_groups which
        # is currently responsible for calculating the host tags of a host.
        # Would be better to untie the GUI code there and move it over to cmk.utils.tags.
        return {
            "piggyback": "auto-piggyback",
            "networking": "lan",
            "agent": "cmk-agent",
            "criticality": "prod",
            "snmp_ds": "no-snmp",
            "site": omd_site(),
            "address_family": "ip-v4-only",
        }

    def checkmk_check_parameters(self, host_name: HostName) -> CheckmkCheckParameters:
        return CheckmkCheckParameters(enabled=not self.is_ping_host(host_name))

    def notification_plugin_parameters(
        self, host_name: HostName, plugin_name: CheckPluginNameStr
    ) -> dict:
        def _impl() -> dict:
            default: Sequence[RuleSpec[object]] = []
            return self.host_extra_conf_merged(
                host_name, notification_parameters.get(plugin_name, default)
            )

        with contextlib.suppress(KeyError):
            return self.__notification_plugin_parameters[(host_name, plugin_name)]

        return self.__notification_plugin_parameters.setdefault((host_name, plugin_name), _impl())

    def labels(self, host_name: HostName) -> Labels:
        with contextlib.suppress(KeyError):
            return self.__labels[host_name]

        return self.__labels.setdefault(host_name, self.ruleset_matcher.labels_of_host(host_name))

    def label_sources(self, host_name: HostName) -> LabelSources:
        with contextlib.suppress(KeyError):
            return self.__label_sources[host_name]

        return self.__label_sources.setdefault(
            host_name, self.ruleset_matcher.label_sources_of_host(host_name)
        )

    def max_cachefile_age(self, hostname: HostName) -> MaxAge:
        check_interval = self.check_mk_check_interval(hostname)
        return MaxAge(
            checking=check_max_cachefile_age
            if self.nodes_of(hostname) is None
            else cluster_max_cachefile_age,
            discovery=1.5 * check_interval,
            inventory=1.5 * check_interval,
        )

    def exit_code_spec(self, hostname: HostName, data_source_id: str | None = None) -> ExitSpec:
        spec: _NestedExitSpec = {}
        # TODO: Can we use host_extra_conf_merged?
        specs = self.host_extra_conf(hostname, check_mk_exit_status)
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
            try:
                return spec["individual"][data_source_id]
            except KeyError:
                pass

        try:
            return spec["overall"]
        except KeyError:
            pass

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

    def set_autochecks(
        self,
        hostname: HostName,
        new_services: Sequence[AutocheckServiceWithNodes],
    ) -> None:
        """Merge existing autochecks with the given autochecks for a host and save it"""
        nodes = self.nodes_of(hostname)
        if self.is_cluster(hostname):
            if nodes:
                autochecks.set_autochecks_of_cluster(
                    nodes,
                    hostname,
                    new_services,
                    self.host_of_clustered_service,
                    service_description,  # top level function!
                )
        else:
            autochecks.set_autochecks_of_real_hosts(hostname, new_services)

    def remove_autochecks(self, hostname: HostName) -> int:
        """Remove all autochecks of a host while being cluster-aware

        Cluster aware means that the autocheck files of the nodes are handled. Instead
        of removing the whole file the file is loaded and only the services associated
        with the given cluster are removed."""
        nodes = self.nodes_of(hostname) or [hostname]
        return sum(
            autochecks.remove_autochecks_of_host(
                node, hostname, self.host_of_clustered_service, service_description
            )
            for node in nodes
        )

    def inv_retention_intervals(self, hostname: HostName) -> RawIntervalsFromConfig:
        return [
            raw
            for entry in self.host_extra_conf(hostname, inv_retention_intervals)
            for raw in entry
        ]

    def service_level(self, hostname: HostName) -> int | None:
        entries = self.host_extra_conf(hostname, host_service_levels)
        if not entries:
            return None
        return entries[0]

    def _snmp_credentials(self, host_name: HostName) -> SNMPCredentials:
        """Determine SNMP credentials for a specific host

        It the host is found int the map snmp_communities, that community is
        returned. Otherwise the snmp_default_community is returned (wich is
        preset with "public", but can be overridden in main.mk.
        """
        try:
            return explicit_snmp_communities[host_name]
        except KeyError:
            pass

        communities = self.host_extra_conf(host_name, snmp_communities)
        if communities:
            return communities[0]

        # nothing configured for this host -> use default
        return snmp_default_community

    def _is_host_snmp_v1(self, host_name: HostName) -> bool:
        """Determines is host snmp-v1 using a bit Heuristic algorithm"""
        if isinstance(self._snmp_credentials(host_name), tuple):
            return False  # v3

        if self.in_binary_hostlist(host_name, bulkwalk_hosts):
            return False

        return not self.in_binary_hostlist(host_name, snmpv2c_hosts)

    @staticmethod
    def _is_inline_backend_supported() -> bool:
        return "netsnmp" in sys.modules and not cmk_version.is_raw_edition()

    def get_snmp_backend(self, host_name: HostName) -> SNMPBackendEnum:
        if self.in_binary_hostlist(host_name, usewalk_hosts):
            return SNMPBackendEnum.STORED_WALK

        with_inline_snmp = ConfigCache._is_inline_backend_supported()

        host_backend_config = self.host_extra_conf(host_name, snmp_backend_hosts)

        if host_backend_config:
            # If more backends are configured for this host take the first one
            host_backend = host_backend_config[0]
            if with_inline_snmp and host_backend == "inline":
                return SNMPBackendEnum.INLINE
            if host_backend == "classic":
                return SNMPBackendEnum.CLASSIC
            raise MKGeneralException("Bad Host SNMP Backend configuration: %s" % host_backend)

        # TODO(sk): remove this when netsnmp is fixed
        # NOTE: Force usage of CLASSIC with SNMP-v1 to prevent memory leak in the netsnmp
        if self._is_host_snmp_v1(host_name):
            return SNMPBackendEnum.CLASSIC

        if with_inline_snmp and snmp_backend_default == "inline":
            return SNMPBackendEnum.INLINE

        return SNMPBackendEnum.CLASSIC

    def snmp_credentials_of_version(
        self, hostname: HostName, snmp_version: int
    ) -> SNMPCredentials | None:
        for entry in self.host_extra_conf(hostname, snmp_communities):
            if snmp_version == 3 and not isinstance(entry, tuple):
                continue

            if snmp_version != 3 and isinstance(entry, tuple):
                continue

            return entry

        return None

    def _snmp_port(self, hostname: HostName) -> int:
        ports = self.host_extra_conf(hostname, snmp_ports)
        if not ports:
            return 161
        return ports[0]

    def _snmp_timing(self, hostname: HostName) -> SNMPTiming:
        timing = self.host_extra_conf(hostname, snmp_timing)
        if not timing:
            return {}
        return timing[0]

    def _bulk_walk_size(self, hostname: HostName) -> int:
        bulk_sizes = self.host_extra_conf(hostname, snmp_bulk_size)
        if not bulk_sizes:
            return 10
        return bulk_sizes[0]

    def _snmp_character_encoding(self, hostname: HostName) -> str | None:
        entries = self.host_extra_conf(hostname, snmp_character_encodings)
        if not entries:
            return None
        return entries[0]

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

    def check_mk_check_interval(self, hostname: HostName) -> float:
        if hostname not in self._check_mk_check_interval:
            self._check_mk_check_interval[hostname] = (
                self.extra_attributes_of_service(hostname, "Check_MK")["check_interval"] * 60
            )

        return self._check_mk_check_interval[hostname]

    @staticmethod
    def address_family(host_name: HostName) -> AddressFamily:
        # TODO(ml): [IPv6] clarify tag_groups vs tag_groups["address_family"]
        tag_groups = ConfigCache.tags(host_name)
        if "no-ip" in tag_groups or "no-ip" == tag_groups["address_family"]:
            return AddressFamily.NO_IP
        if "ip-v4v6" in tag_groups or "ip-v4v6" == tag_groups["address_family"]:
            return AddressFamily.DUAL_STACK
        if ("ip-v6" in tag_groups or "ip-v6" == tag_groups["address_family"]) and (
            "ip-v4" in tag_groups or "ip-v4" == tag_groups["address_family"]
        ):
            return AddressFamily.DUAL_STACK
        if (
            "ip-v6" in tag_groups
            or "ip-v6-only" in tag_groups
            or tag_groups["address_family"] in {"ip-v6", "ip-v6-only"}
        ):
            return AddressFamily.IPv6
        return AddressFamily.IPv4

    def default_address_family(self, hostname: HostName) -> socket.AddressFamily:
        def primary_ip_address_family_of() -> socket.AddressFamily:
            rules = self.host_extra_conf(hostname, primary_address_family)
            if rules and rules[0] == "ipv6":
                return socket.AF_INET6
            return socket.AF_INET

        def is_ipv6_primary() -> bool:
            # Whether or not the given host is configured to be monitored primarily via IPv6
            return ConfigCache.address_family(hostname) is AddressFamily.IPv6 or (
                ConfigCache.address_family(hostname) is AddressFamily.DUAL_STACK
                and primary_ip_address_family_of() is socket.AF_INET6
            )

        return socket.AF_INET6 if is_ipv6_primary() else socket.AF_INET

    def _has_piggyback_data(self, host_name: HostName) -> bool:
        time_settings: list[tuple[str | None, str, int]] = self._piggybacked_host_files(host_name)
        time_settings.append((None, "max_cache_age", piggyback_max_cachefile_age))

        if piggyback.has_piggyback_raw_data(host_name, time_settings):
            return True

        return make_persisted_section_dir(
            fetcher_type=FetcherType.PIGGYBACK, host_name=host_name, ident="piggyback"
        ).exists()

    def _piggybacked_host_files(self, host_name: HostName) -> list[tuple[str | None, str, int]]:
        rules = self.host_extra_conf(host_name, piggybacked_host_files)
        if rules:
            return self._flatten_piggybacked_host_files_rule(host_name, rules[0])
        return []

    def _flatten_piggybacked_host_files_rule(
        self, host_name: HostName, rule: dict[str, Any]
    ) -> list[tuple[str | None, str, int]]:
        """This rule is a first match rule.

        Max cache age, validity period and state are configurable wihtin this
        rule for all piggybacked host or per piggybacked host of this source.
        In order to differentiate later for which piggybacked hosts a parameter
        is used we flat this rule to a homogeneous data structure:
            (HOST, KEY): VALUE
        Then piggyback.py:_get_piggyback_processed_file_info can evaluate the
        parameters generically."""
        flat_rule: list[tuple[str | None, str, int]] = []

        max_cache_age = rule.get("global_max_cache_age")
        if max_cache_age is not None and max_cache_age != "global":
            flat_rule.append((host_name, "max_cache_age", max_cache_age))

        global_validity_setting = rule.get("global_validity", {})

        period = global_validity_setting.get("period")
        if period is not None:
            flat_rule.append((host_name, "validity_period", period))

        check_mk_state = global_validity_setting.get("check_mk_state")
        if check_mk_state is not None:
            flat_rule.append((host_name, "validity_state", check_mk_state))

        for setting in rule.get("per_piggybacked_host", []):
            if "piggybacked_hostname" in setting:
                piggybacked_hostname_expressions = [setting["piggybacked_hostname"]]
            elif "piggybacked_hostname_expressions" in setting:
                piggybacked_hostname_expressions = setting["piggybacked_hostname_expressions"]
            else:
                piggybacked_hostname_expressions = []

            for piggybacked_hostname_expr in piggybacked_hostname_expressions:
                max_cache_age = setting.get("max_cache_age")
                if max_cache_age is not None and max_cache_age != "global":
                    flat_rule.append((piggybacked_hostname_expr, "max_cache_age", max_cache_age))

                validity_setting = setting.get("validity", {})
                if not validity_setting:
                    continue

                period = validity_setting.get("period")
                if period is not None:
                    flat_rule.append((piggybacked_hostname_expr, "validity_period", period))

                check_mk_state = validity_setting.get("check_mk_state")
                if check_mk_state is not None:
                    flat_rule.append((piggybacked_hostname_expr, "validity_state", check_mk_state))

        return flat_rule

    def tags_of_service(self, hostname: HostName, svc_desc: ServiceName) -> TaggroupIDToTagID:
        """Returns the dict of all configured tags of a service
        It takes all explicitly configured tag groups into account.
        """
        return {
            k: v
            for entry in self.service_extra_conf(hostname, svc_desc, service_tag_rules)
            for k, v in entry
        }

    def extra_attributes_of_service(
        self, hostname: HostName, description: ServiceName
    ) -> dict[str, Any]:
        attrs = {
            "check_interval": SERVICE_CHECK_INTERVAL,
        }
        for key, ruleset in extra_service_conf.items():
            values = self.service_extra_conf(hostname, description, ruleset)
            if not values:
                continue

            value = values[0]
            if value is None:
                continue

            if key == "check_interval":
                value = float(value)

            if key[0] == "_":
                key = key.upper()

            attrs[key] = value

        return attrs

    def icons_and_actions_of_service(
        self,
        hostname: HostName,
        description: ServiceName,
        check_plugin_name: CheckPluginName | None,
        params: LegacyCheckParameters | TimespecificParameters,
    ) -> list[str]:
        actions = set(self.service_extra_conf(hostname, description, service_icons_and_actions))

        # Some WATO rules might register icons on their own
        if check_plugin_name:
            plugin = agent_based_register.get_check_plugin(check_plugin_name)
            if (
                plugin is not None
                and str(plugin.check_ruleset_name) in ("ps", "services")
                and isinstance(params, dict)
            ):
                icon = params.get("icon")
                if icon:
                    actions.add(icon)

        return list(actions)

    def servicegroups_of_service(
        self, hostname: HostName, description: ServiceName
    ) -> list[ServicegroupName]:
        """Returns the list of servicegroups of this services"""
        return self.service_extra_conf(hostname, description, service_groups)

    def contactgroups_of_service(self, hostname: HostName, description: ServiceName) -> list[str]:
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
        for entry in self.service_extra_conf(hostname, description, service_contactgroups):
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

    def passive_check_period_of_service(self, hostname: HostName, description: ServiceName) -> str:
        return self.get_service_ruleset_value(hostname, description, check_periods, deflt="24X7")

    def custom_attributes_of_service(
        self, hostname: HostName, description: ServiceName
    ) -> dict[str, str]:
        return dict(
            itertools.chain(
                *self.service_extra_conf(hostname, description, custom_service_attributes)
            )
        )

    def service_level_of_service(self, hostname: HostName, description: ServiceName) -> int | None:
        return self.get_service_ruleset_value(
            hostname,
            description,
            service_service_levels,
            deflt=None,
        )

    def check_period_of_service(
        self, hostname: HostName, description: ServiceName
    ) -> TimeperiodName | None:
        entry = self.get_service_ruleset_value(hostname, description, check_periods, deflt=None)
        if entry == "24X7":
            return None
        return entry

    @staticmethod
    def get_explicit_service_custom_variables(
        hostname: HostName, description: ServiceName
    ) -> dict[str, str]:
        try:
            return explicit_service_custom_variables[(hostname, description)]
        except KeyError:
            return {}

    def ruleset_match_object_of_service(
        self, hostname: HostName, svc_desc: ServiceName, svc_labels: Labels | None = None
    ) -> RulesetMatchObject:
        """Construct the object that is needed to match this service to rulesets

        Please note that the host attributes like host_folder and host_tags are
        not set in the object, because the rule optimizer already processes all
        these host conditions. Adding these attributes here would be
        consequent, but create some overhead.

        BE AWARE: When matching on checkgroup_parameters (Which use the check
        item in the service_description field), you need to use the
        ruleset_match_object_for_checkgroup_parameters()
        """

        cache_id = (hostname, svc_desc)
        if cache_id in self._cache_match_object_service:
            return self._cache_match_object_service[cache_id]
        if svc_labels is None:
            svc_labels = self.ruleset_matcher.labels_of_service(hostname, svc_desc)
        result = RulesetMatchObject(
            host_name=hostname, service_description=svc_desc, service_labels=svc_labels
        )
        self._cache_match_object_service[cache_id] = result
        return result

    def ruleset_match_object_for_checkgroup_parameters(
        self,
        hostname: HostName,
        item: Item,
        svc_desc: ServiceName,
        svc_labels: Labels | None = None,
    ) -> RulesetMatchObject:
        """Construct the object that is needed to match checkgroup parameters rulesets

        Please note that the host attributes like host_folder and host_tags are
        not set in the object, because the rule optimizer already processes all
        these host conditions. Adding these attributes here would be
        consequent, but create some overhead.
        """

        cache_id = (hostname, item, svc_desc)
        if cache_id in self._cache_match_object_service_checkgroup:
            return self._cache_match_object_service_checkgroup[cache_id]

        result = RulesetMatchObject(
            host_name=hostname,
            service_description=item,
            service_labels=svc_labels
            if svc_labels is not None
            else self.ruleset_matcher.labels_of_service(hostname, svc_desc),
        )
        self._cache_match_object_service_checkgroup[cache_id] = result
        return result

    def ruleset_match_object_of_host(self, hostname: HostName) -> RulesetMatchObject:
        """Construct the object that is needed to match the host rulesets

        Please note that the host attributes like host_folder and host_tags are
        not set in the object, because the rule optimizer already processes all
        these host conditions. Adding these attributes here would be
        consequent, but create some overhead.
        """

        if hostname in self._cache_match_object_host:
            return self._cache_match_object_host[hostname]

        match_object = ruleset_matcher.RulesetMatchObject(hostname, service_description=None)
        self._cache_match_object_host[hostname] = match_object
        return match_object

    def get_autochecks_of(self, hostname: HostName) -> Sequence[ConfiguredService]:
        return self._autochecks_manager.get_autochecks_of(
            hostname,
            compute_check_parameters,
            service_description,  # this is the global function!
            self.host_of_clustered_service,
        )

    def section_name_of(self, section: CheckPluginNameStr) -> str:
        try:
            return self._cache_section_name_of[section]
        except KeyError:
            section_name = section_name_of(section)
            self._cache_section_name_of[section] = section_name
            return section_name

    @staticmethod
    def _get_tag_attributes(
        collection: TaggroupIDToTagID | Labels | LabelSources,
        prefix: str,
    ) -> ObjectAttributes:
        return {f"__{prefix}_{k}": str(v) for k, v in collection.items()}

    def get_host_attributes(self, hostname: HostName) -> ObjectAttributes:
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
        attrs.update(ConfigCache._get_tag_attributes(self.labels(hostname), "LABEL"))
        attrs.update(ConfigCache._get_tag_attributes(self.label_sources(hostname), "LABELSOURCE"))

        if "alias" not in attrs:
            attrs["alias"] = self.alias(hostname)

        family = ConfigCache.address_family(hostname)

        # Now lookup configured IP addresses
        v4address: str | None = None
        if AddressFamily.IPv4 in family:
            v4address = ip_address_of(self, hostname, socket.AF_INET)

        if v4address is None:
            v4address = ""
        attrs["_ADDRESS_4"] = v4address

        v6address: str | None = None
        if AddressFamily.IPv6 in family:
            v6address = ip_address_of(self, hostname, socket.AF_INET6)
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

        if cmk_version.is_managed_edition():
            attrs["_CUSTOMER"] = current_customer  # type: ignore[name-defined] # pylint: disable=undefined-variable

        return attrs

    def get_cluster_attributes(
        self,
        hostname: HostName,
        nodes: Sequence[HostName],
    ) -> dict:
        sorted_nodes = sorted(nodes)

        attrs = {
            "_NODENAMES": " ".join(sorted_nodes),
        }
        node_ips_4 = []
        if AddressFamily.IPv4 in ConfigCache.address_family(hostname):
            family = socket.AF_INET
            for h in sorted_nodes:
                addr = ip_address_of(self, h, family)
                if addr is not None:
                    node_ips_4.append(addr)
                else:
                    node_ips_4.append(ip_lookup.fallback_ip_for(family))

        node_ips_6 = []
        if AddressFamily.IPv6 in ConfigCache.address_family(hostname):
            family = socket.AF_INET6
            for h in sorted_nodes:
                addr = ip_address_of(self, h, family)
                if addr is not None:
                    node_ips_6.append(addr)
                else:
                    node_ips_6.append(ip_lookup.fallback_ip_for(family))

        node_ips = (
            node_ips_6 if self.default_address_family(hostname) is socket.AF_INET6 else node_ips_4
        )

        for suffix, val in [("", node_ips), ("_4", node_ips_4), ("_6", node_ips_6)]:
            attrs["_NODEIPS%s" % suffix] = " ".join(val)

        return attrs

    def get_cluster_nodes_for_config(self, host_name: HostName) -> list[HostName]:
        nodes = self.nodes_of(host_name)
        if nodes is None:
            return []

        self._verify_cluster_address_family(host_name, nodes)
        self._verify_cluster_datasource(host_name, nodes)
        nodes = nodes[:]
        for node in nodes:
            if node not in self.all_active_realhosts():
                config_warnings.warn(
                    "Node '%s' of cluster '%s' is not a monitored host in this site."
                    % (node, host_name)
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
                "Cluster '%s' has different primary address families: %s"
                % (host_name, ", ".join(address_families))
            )

    def _verify_cluster_datasource(
        self,
        host_name: HostName,
        nodes: Iterable[HostName],
    ) -> None:
        cluster_tg = self.tags(host_name)
        cluster_agent_ds = cluster_tg.get("agent")
        cluster_snmp_ds = cluster_tg.get("snmp_ds")
        for nodename in nodes:
            node_tg = self.tags(nodename)
            node_agent_ds = node_tg.get("agent")
            node_snmp_ds = node_tg.get("snmp_ds")
            warn_text = "Cluster '%s' has different datasources as its node" % host_name
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
                macros["$HOST" + macro_name + "$"] = value
                # Be compatible to nagios making $_HOST<VARNAME>$ out of the config _<VARNAME> configs
                macros["$_HOST" + macro_name[1:] + "$"] = value

        return macros

    @staticmethod
    def get_service_macros_from_attributes(attrs: ObjectAttributes) -> ObjectMacros:
        # We may want to implement a superset of Nagios' own macros, see
        # https://assets.nagios.com/downloads/nagioscore/docs/nagioscore/3/en/macrolist.html
        macros = {}
        for macro_name, value in attrs.items():
            if macro_name[0] == "_":
                macros["$_SERVICE" + macro_name[1:] + "$"] = value
        return macros

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
                    if cmk.utils.debug.enabled():
                        raise

        return s

    def translate_commandline(
        self,
        host_name: HostName,
        ip_address: HostAddress | None,
        template: str,
    ) -> str:
        def _translate_host_macros(cmd: str) -> str:
            attrs = self.get_host_attributes(host_name)
            if self.is_cluster(host_name):
                # TODO(ml): What is the difference between this and `self.parents()`?
                parents_list = self.get_cluster_nodes_for_config(host_name)
                attrs.setdefault("alias", "cluster of %s" % ", ".join(parents_list))
                attrs.update(
                    self.get_cluster_attributes(
                        host_name,
                        parents_list,
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

    def host_extra_conf_merged(
        self, hostname: HostName, ruleset: Iterable[RuleSpec]
    ) -> dict[str, Any]:
        return self.ruleset_matcher.get_host_ruleset_merged_dict(
            self.ruleset_match_object_of_host(hostname),
            ruleset,
        )

    def host_extra_conf(self, hostname: HostName, ruleset: Iterable[RuleSpec]) -> list:
        return list(
            self.ruleset_matcher.get_host_ruleset_values(
                self.ruleset_match_object_of_host(hostname),
                ruleset,
                is_binary=False,
            )
        )

    # TODO: Cleanup external in_binary_hostlist call sites
    def in_binary_hostlist(self, hostname: HostName, ruleset: Iterable[RuleSpec]) -> bool:
        return self.ruleset_matcher.is_matching_host_ruleset(
            self.ruleset_match_object_of_host(hostname), ruleset
        )

    def service_extra_conf(
        self, hostname: HostName, description: ServiceName, ruleset: Iterable[RuleSpec]
    ) -> list:
        """Compute outcome of a service rule set that has an item."""
        return list(
            self.ruleset_matcher.get_service_ruleset_values(
                self.ruleset_match_object_of_service(hostname, description),
                ruleset,
                is_binary=False,
            )
        )

    def get_service_ruleset_value(
        self, hostname: HostName, description: ServiceName, ruleset: Iterable[RuleSpec], deflt: Any
    ) -> Any:
        """Compute first match service ruleset outcome with fallback to a default value"""
        return next(
            self.ruleset_matcher.get_service_ruleset_values(
                self.ruleset_match_object_of_service(hostname, description),
                ruleset,
                is_binary=False,
            ),
            deflt,
        )

    def service_extra_conf_merged(
        self, hostname: HostName, description: ServiceName, ruleset: Iterable[RuleSpec]
    ) -> dict[str, Any]:
        return self.ruleset_matcher.get_service_ruleset_merged_dict(
            self.ruleset_match_object_of_service(hostname, description), ruleset
        )

    def in_boolean_serviceconf_list(
        self, hostname: HostName, description: ServiceName, ruleset: Iterable[RuleSpec]
    ) -> bool:
        """Compute outcome of a service rule set that just say yes/no"""
        return self.ruleset_matcher.is_matching_service_ruleset(
            self.ruleset_match_object_of_service(hostname, description), ruleset
        )

    def service_ignored(self, host_name: HostName, description: ServiceName) -> bool:
        return self.in_boolean_serviceconf_list(host_name, description, ignored_services)

    def check_plugin_ignored(
        self,
        host_name: HostName,
        check_plugin_name: CheckPluginName,
    ) -> bool:
        def _checktype_ignored_for_host(check_plugin_name_str: str) -> bool:
            ignored = self.host_extra_conf(host_name, ignored_checks)
            for e in ignored:
                if check_plugin_name_str in e:
                    return True
            return False

        check_plugin_name_str = str(check_plugin_name)

        if check_plugin_name_str in ignored_checktypes:
            return True

        if _checktype_ignored_for_host(check_plugin_name_str):
            return True

        return False

    def all_active_hosts(self) -> set[HostName]:
        """Returns a set of all active hosts"""
        return self._all_active_hosts

    def all_active_realhosts(self) -> set[HostName]:
        """Returns a set of all host names to be handled by this site hosts of other sites or disabled hosts are excluded"""
        return self._all_active_realhosts

    def all_configured_realhosts(self) -> set[HostName]:
        return self._all_configured_realhosts

    def all_configured_hosts(self) -> set[HostName]:
        return self._all_configured_hosts

    def _setup_clusters_nodes_cache(self) -> None:
        for cluster, hosts in clusters.items():
            clustername = cluster.split("|", 1)[0]
            for name in hosts:
                self._clusters_of_cache.setdefault(name, []).append(clustername)
            self._nodes_of_cache[clustername] = hosts

    def get_cluster_cache_info(self) -> ClusterCacheInfo:
        return ClusterCacheInfo(self._clusters_of_cache, self._nodes_of_cache)

    def clusters_of(self, hostname: HostName) -> list[HostName]:
        """Returns names of cluster hosts the host is a node of"""
        return self._clusters_of_cache.get(hostname, [])

    # TODO: cleanup None case
    def nodes_of(self, hostname: HostName) -> list[HostName] | None:
        """Returns the nodes of a cluster. Returns None if no match."""
        return self._nodes_of_cache.get(hostname)

    def all_active_clusters(self) -> set[HostName]:
        """Returns a set of all cluster host names to be handled by this site hosts of other sites or disabled hosts are excluded"""
        return self._all_active_clusters

    def all_configured_clusters(self) -> set[HostName]:
        """Returns a set of all cluster names
        Regardless if currently disabled or monitored on a remote site. Does not return normal hosts.
        """
        return self._all_configured_clusters

    def all_sites_clusters(self) -> set[HostName]:
        return {
            c
            for c in self._all_configured_clusters
            if distributed_wato_site is None or _host_is_member_of_site(c, distributed_wato_site)
        }

    def host_of_clustered_service(
        self,
        hostname: HostName,
        servicedesc: str,
        part_of_clusters: list[HostName] | None = None,
    ) -> HostName:
        key = (hostname, servicedesc, tuple(part_of_clusters) if part_of_clusters else None)
        if (actual_hostname := self._host_of_clustered_service_cache.get(key)) is not None:
            return actual_hostname

        self._host_of_clustered_service_cache[key] = self._host_of_clustered_service(
            hostname,
            servicedesc,
            part_of_clusters,
        )
        return self._host_of_clustered_service_cache[key]

    def _host_of_clustered_service(
        self,
        hostname: HostName,
        servicedesc: str,
        part_of_clusters: list[HostName] | None = None,
    ) -> HostName:
        """Return hostname to assign the service to
        Determine wether a service (found on a physical host) is a clustered
        service and - if yes - return the cluster host of the service. If no,
        returns the hostname of the physical host."""
        if part_of_clusters:
            the_clusters = part_of_clusters
        else:
            the_clusters = self.clusters_of(hostname)

        if not the_clusters:
            return hostname

        cluster_mapping = self.service_extra_conf(hostname, servicedesc, clustered_services_mapping)
        for cluster in cluster_mapping:
            # Check if the host is in this cluster
            if cluster in the_clusters:
                return cluster

        # 1. New style: explicitly assigned services
        for cluster, conf in clustered_services_of.items():
            nodes = self.nodes_of(cluster)
            if not nodes:
                raise MKGeneralException(
                    "Invalid entry clustered_services_of['%s']: %s is not a cluster."
                    % (cluster, cluster)
                )
            if hostname in nodes and self.in_boolean_serviceconf_list(hostname, servicedesc, conf):
                return cluster

        # 1. Old style: clustered_services assumes that each host belong to
        #    exactly on cluster
        if self.in_boolean_serviceconf_list(hostname, servicedesc, clustered_services):
            return the_clusters[0]

        return hostname

    def get_clustered_service_configuration(
        self,
        host_name: HostName,
        service_descr: str,
    ) -> tuple[ClusterMode, Mapping[str, Any]]:
        matching_rules = self.service_extra_conf(
            host_name,
            service_descr,
            clustered_services_configuration,
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
    ) -> Sequence[tuple[str | None, str, int]]:
        time_settings: list[tuple[str | None, str, int]] = []
        for source_hostname in sorted(piggyback.get_source_hostnames(piggybacked_hostname)):
            time_settings.extend(self._piggybacked_host_files(source_hostname))

        # From global settings
        time_settings.append((None, "max_cache_age", piggyback_max_cachefile_age))
        return time_settings

    # TODO: Remove old name one day
    @staticmethod
    def service_discovery_name() -> ServiceName:
        if "cmk_inventory" in use_new_descriptions_for:
            return "Check_MK Discovery"
        return "Check_MK inventory"

    def _agent_port(self, host_name: HostName) -> int:
        ports = self.host_extra_conf(host_name, agent_ports)
        if not ports:
            return agent_port

        return ports[0]

    def _tcp_connect_timeout(self, host_name: HostName) -> float:
        timeouts = self.host_extra_conf(host_name, tcp_connect_timeouts)
        if not timeouts:
            return tcp_connect_timeout

        return timeouts[0]

    def _encryption_handling(self, host_name: HostName) -> TCPEncryptionHandling:
        if not (settings := self.host_extra_conf(host_name, encryption_handling)):
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
            settings[0] if (settings := self.host_extra_conf(host_name, agent_encryption)) else None
        )

    def agent_exclude_sections(self, host_name: HostName) -> dict[str, str]:
        settings = self.host_extra_conf(host_name, agent_exclude_sections)
        if not settings:
            return {}
        return settings[0]

    def agent_target_version(self, host_name: HostName) -> AgentTargetVersion:
        agent_target_versions = self.host_extra_conf(host_name, check_mk_agent_target_versions)
        if not agent_target_versions:
            return None

        spec = agent_target_versions[0]
        if spec == "ignore":
            return None
        if spec == "site":
            return cmk_version.__version__
        if isinstance(spec, str):
            # Compatibility to old value specification format (a single version string)
            return spec
        if spec[0] == "specific":
            return spec[1]

        return spec  # return the whole spec in case of an "at least version" config

    def only_from(self, host_name: HostName) -> None | list[str] | str:
        """The agent of a host may be configured to be accessible only from specific IPs"""
        ruleset = agent_config.get("only_from", [])
        if not ruleset:
            return None

        entries = self.host_extra_conf(host_name, ruleset)
        if not entries:
            return None

        return entries[0]

    def ping_levels(self, host_name: HostName) -> PingLevels:
        levels: PingLevels = {}

        values = self.host_extra_conf(host_name, ping_levels)
        # TODO: Use host_extra_conf_merged?)
        for value in values[::-1]:  # make first rules have precedence
            levels.update(value)

        return levels

    def icons_and_actions(self, host_name: HostName) -> list[str]:
        return list(set(self.host_extra_conf(host_name, host_icons_and_actions)))


def get_config_cache() -> ConfigCache:
    config_cache = _config_cache.get("config_cache")
    if not config_cache:
        cache_class = ConfigCache if cmk_version.is_raw_edition() else CEEConfigCache
        config_cache["cache"] = cache_class().initialize()
    return config_cache["cache"]


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


def _boil_down_agent_rules(
    *, defaults: Mapping[str, Any], rulesets: Mapping[str, Any]
) -> Mapping[str, Any]:
    boiled_down = {**defaults}

    # TODO: Better move whole computation to cmk.base.config for making
    # ruleset matching transparent
    for varname, entries in rulesets.items():
        if not entries:
            continue

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
                **{k: v for entry in entries[::-1] for k, v in entry.items()},
            }
        elif match_type is _Matchtype.ALL:
            boiled_down[varname] = entries
        else:
            assert_never(match_type)

    return boiled_down


class CEEConfigCache(ConfigCache):
    def _initialize_caches(self) -> None:
        super()._initialize_caches()
        self._initialize_host_config()

    def _initialize_host_config(self) -> None:
        # Keep CEEHostConfig instances created with the current configuration cache
        # This can be ignored for now -- it only is used privately as a cache, so the
        # contravariance is not a problem here.
        self._host_configs: dict[HostName, CEEHostConfig] = {}  # type: ignore[assignment]

    def make_cee_host_config(self, hostname: HostName) -> CEEHostConfig:
        """Returns a CEEHostConfig instance for the given host

        It lazy initializes the host config object and caches the objects during the livetime
        of the ConfigCache."""
        with contextlib.suppress(KeyError):
            return self._host_configs[hostname]

        return self._host_configs.setdefault(hostname, CEEHostConfig(self, hostname))

    def rrd_config_of_service(
        self, hostname: HostName, description: ServiceName
    ) -> RRDConfig | None:
        return self.get_service_ruleset_value(
            hostname, description, cmc_service_rrd_config, deflt=None
        )

    def recurring_downtimes_of_service(
        self, hostname: HostName, description: ServiceName
    ) -> list[RecurringDowntime]:
        return self.service_extra_conf(
            hostname, description, service_recurring_downtimes  # type: ignore[name-defined] # pylint: disable=undefined-variable
        )

    def flap_settings_of_service(
        self, hostname: HostName, description: ServiceName
    ) -> tuple[float, float, float]:
        return self.get_service_ruleset_value(
            hostname,
            description,
            cmc_service_flap_settings,  # type: ignore[name-defined] # pylint: disable=undefined-variable
            deflt=cmc_flap_settings,  # type: ignore[name-defined] # pylint: disable=undefined-variable
        )

    def log_long_output_of_service(self, hostname: HostName, description: ServiceName) -> bool:
        return self.get_service_ruleset_value(
            hostname,
            description,
            cmc_service_long_output_in_monitoring_history,  # type: ignore[name-defined] # pylint: disable=undefined-variable
            deflt=False,
        )

    def state_translation_of_service(self, hostname: HostName, description: ServiceName) -> dict:
        entries = self.service_extra_conf(
            hostname, description, service_state_translation  # type: ignore[name-defined] # pylint: disable=undefined-variable
        )

        spec: dict = {}
        for entry in entries[::-1]:
            spec.update(entry)
        return spec

    def check_timeout_of_service(self, hostname: HostName, description: ServiceName) -> int:
        """Returns the check timeout in seconds"""
        return self.get_service_ruleset_value(
            hostname,
            description,
            cmc_service_check_timeout,  # type: ignore[name-defined] # pylint: disable=undefined-variable
            deflt=cmc_check_timeout,  # type: ignore[name-defined] # pylint: disable=undefined-variable
        )

    def graphite_metrics_of(
        self,
        hostname: HostName,
        description: ServiceName | None,
        *,
        default: list[str],
    ) -> Sequence[str]:
        if description is None:
            return next(
                iter(
                    self.host_extra_conf(
                        hostname,
                        cmc_graphite_host_metrics,  # type: ignore[name-defined] # pylint: disable=undefined-variable
                    )
                ),
                default,
            )

        return self.get_service_ruleset_value(
            hostname,
            description,
            cmc_graphite_service_metrics,  # type: ignore[name-defined] # pylint: disable=undefined-variable
            deflt=default,
        )

    def influxdb_metrics_of_service(
        self,
        hostname: HostName,
        description: ServiceName | None,
        *,
        default: Mapping[str, Any],
    ) -> Mapping[str, Any]:
        if description is None:
            return default

        value = self.get_service_ruleset_value(
            hostname,
            description,
            cmc_influxdb_service_metrics,  # type: ignore[name-defined] # pylint: disable=undefined-variable
            deflt=None,
        )
        if value is None:
            return default
        return value

    def matched_agent_config_entries(self, hostname: HostName) -> dict[str, Any]:
        return {
            varname: self.host_extra_conf(hostname, ruleset)
            for varname, ruleset in CEEConfigCache._agent_config_rulesets()
        }

    def generic_agent_config_entries(
        self, *, defaults: Mapping[str, Any]
    ) -> Iterable[tuple[str, Mapping[str, Any]]]:
        yield from (
            (
                match_path,
                _boil_down_agent_rules(
                    defaults=defaults,
                    rulesets={
                        varname: self.ruleset_matcher.get_values_for_generic_agent(
                            ruleset, match_path
                        )
                        for varname, ruleset in CEEConfigCache._agent_config_rulesets()
                    },
                ),
            )
            for match_path, attributes in folder_attributes.items()
            if attributes.get("bake_agent_package", False)
        )

    @staticmethod
    def _agent_config_rulesets() -> Iterable[tuple[str, Any]]:
        return list(agent_config.items()) + [
            ("agent_port", agent_ports),
            ("agent_encryption", agent_encryption),
            ("agent_exclude_sections", agent_exclude_sections),
        ]


class CEEHostConfig:
    def __init__(self, config_cache: CEEConfigCache, hostname: HostName) -> None:
        self.hostname: Final = hostname
        self._config_cache: Final = config_cache

    @property
    def rrd_config(self) -> RRDConfig | None:
        entries = self._config_cache.host_extra_conf(self.hostname, cmc_host_rrd_config)
        if not entries:
            return None
        return entries[0]

    @property
    def recurring_downtimes(self) -> list[RecurringDowntime]:
        return self._config_cache.host_extra_conf(
            self.hostname,
            host_recurring_downtimes,  # type: ignore[name-defined] # pylint: disable=undefined-variable
        )

    @property
    def flap_settings(self) -> tuple[float, float, float]:
        values = self._config_cache.host_extra_conf(
            self.hostname, cmc_host_flap_settings  # type: ignore[name-defined] # pylint: disable=undefined-variable
        )
        if not values:
            return cmc_flap_settings  # type: ignore[name-defined] # pylint: disable=undefined-variable

        return values[0]

    @property
    def log_long_output(self) -> bool:
        entries = self._config_cache.host_extra_conf(
            self.hostname,
            cmc_host_long_output_in_monitoring_history,  # type: ignore[name-defined] # pylint: disable=undefined-variable
        )
        if not entries:
            return False
        return entries[0]

    @property
    def state_translation(self) -> dict:
        entries = self._config_cache.host_extra_conf(
            self.hostname, host_state_translation  # type: ignore[name-defined] # pylint: disable=undefined-variable
        )

        spec: dict = {}
        for entry in entries[::-1]:
            spec.update(entry)
        return spec

    @property
    def smartping_settings(self) -> dict:
        settings = {"timeout": 2.5}
        settings.update(
            self._config_cache.host_extra_conf_merged(
                self.hostname, cmc_smartping_settings  # type: ignore[name-defined] # pylint: disable=undefined-variable
            )
        )
        return settings

    @property
    def lnx_remote_alert_handlers(self) -> list[dict[str, str]]:
        default: Sequence[RuleSpec[object]] = []
        return self._config_cache.host_extra_conf(
            self.hostname, agent_config.get("lnx_remote_alert_handlers", default)
        )

    def rtc_secret(self) -> str | None:
        default: Sequence[RuleSpec[object]] = []
        if not (
            settings := self._config_cache.host_extra_conf(
                self.hostname, agent_config.get("real_time_checks", default)
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

    def agent_config(self, default: Mapping[str, Any]) -> Mapping[str, Any]:
        assert isinstance(self._config_cache, CEEConfigCache)
        return {
            **_boil_down_agent_rules(
                defaults=default,
                rulesets=self._config_cache.matched_agent_config_entries(self.hostname),
            ),
            "is_ipv6_primary": (
                self._config_cache.default_address_family(self.hostname) is socket.AF_INET6
            ),
        }
