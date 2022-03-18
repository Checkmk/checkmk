#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import ast
import contextlib
import copy
import inspect
import itertools
import marshal
import numbers
import os
import pickle
import py_compile
import struct
import sys
from collections import OrderedDict
from importlib.util import MAGIC_NUMBER as _MAGIC_NUMBER
from pathlib import Path
from typing import (
    Any,
    Callable,
    cast,
    Dict,
    Iterable,
    Iterator,
    List,
    Literal,
    NamedTuple,
    Mapping,
    MutableMapping,
    Optional,
    Sequence,
    Set,
    Tuple,
    TypedDict,
    Union,
    Final,
)

from six import ensure_str

import cmk.utils
from cmk.utils.check_utils import (
    maincheckify,
    unwrap_parameters,
)
import cmk.utils.cleanup
import cmk.utils.debug
import cmk.utils.paths
import cmk.utils.piggyback as piggyback
import cmk.utils.rulesets.ruleset_matcher as ruleset_matcher
import cmk.utils.rulesets.tuple_rulesets as tuple_rulesets
import cmk.utils.store as store
import cmk.utils.tags
import cmk.utils.translations
import cmk.utils.version as cmk_version
from cmk.utils.check_utils import section_name_of
from cmk.utils.encoding import ensure_str_with_fallback
from cmk.utils.exceptions import MKGeneralException, MKTerminate
from cmk.utils.labels import LabelManager
from cmk.utils.log import console
import cmk.utils.migrated_check_variables
from cmk.utils.regex import regex
from cmk.utils.rulesets.ruleset_matcher import RulesetMatchObject
from cmk.utils.type_defs import (
    ActiveCheckPluginName,
    BuiltinBakeryHostName,
    CheckPluginName,
    CheckPluginNameStr,
    CheckVariables,
    ContactgroupName,
    HostAddress,
    HostgroupName,
    HostKey,
    HostName,
    Item,
    Labels,
    LabelSources,
    Ruleset,
    RulesetName,  # alias for str
    RuleSetName,
    SectionName,
    ServicegroupName,
    ServiceName,
    SourceType,
    TaggroupIDToTagID,
    TagIDs,
    TagIDToTaggroupID,
    TimeperiodName,
    OptionalConfigSerial,
    LATEST_SERIAL,
)

from cmk.snmplib.type_defs import (  # noqa: F401 # pylint: disable=unused-import; these are required in the modules' namespace to load the configuration!
    SNMPScanFunction, SNMPCredentials, SNMPHostConfig, SNMPTiming, SNMPBackend)

from cmk.fetchers import MaxAge

import cmk.base.api.agent_based.register as agent_based_register
import cmk.base.autochecks as autochecks
import cmk.base.check_api_utils as check_api_utils
import cmk.base.check_utils
import cmk.base.default_config as default_config
from cmk.base.api.agent_based.checking_classes import CheckPlugin
from cmk.base.api.agent_based.register.check_plugins_legacy import create_check_plugin_from_legacy
from cmk.base.api.agent_based.register.section_plugins_legacy import (
    create_agent_section_plugin_from_legacy,
    create_snmp_section_plugin_from_legacy,
)
from cmk.base.api.agent_based.type_defs import (
    Parameters,
    SectionPlugin,
    SNMPSectionPlugin,
)
from cmk.base.caching import config_cache as _config_cache
from cmk.base.caching import runtime_cache as _runtime_cache
from cmk.base.check_utils import LegacyCheckParameters
from cmk.base.default_config import *  # pylint: disable=wildcard-import,unused-wildcard-import
from cmk.base.autochecks import ServiceWithNodes

# TODO: Prefix helper functions with "_".

service_service_levels = []
host_service_levels = []

AllHosts = List[str]
ShadowHosts = Dict[str, Dict]
AllClusters = Dict[str, List[HostName]]
AgentTargetVersion = Union[None, str, Tuple[str, str], Tuple[str, Dict[str, str]]]
RRDConfig = Dict[str, Any]
CheckContext = Dict[str, Any]
GetCheckApiContext = Callable[[], Dict[str, Any]]
CheckIncludes = List[str]
DiscoveryCheckParameters = Dict
SpecialAgentConfiguration = NamedTuple(
    "SpecialAgentConfiguration",
    [
        ("args", List[str]),
        # None makes the stdin of suprocess /dev/null
        ("stdin", Optional[str]),
    ])
SpecialAgentInfoFunctionResult = Union[str, List[Union[str, int, float, Tuple[str, str, str]]],
                                       SpecialAgentConfiguration]
SpecialAgentInfoFunction = Callable[[Mapping[str, Any], HostName, Optional[HostAddress]],
                                    SpecialAgentInfoFunctionResult]
HostCheckCommand = Union[None, str, Tuple[str, Union[int, str]]]
PingLevels = Dict[str, Union[int, Tuple[float, float]]]
ObjectAttributes = Dict  # TODO: Improve this. Have seen Dict[str, Union[str, unicode, int]]
GroupDefinitions = Dict[str, str]
RecurringDowntime = Dict[str, Union[int, str]]
CheckInfo = Dict  # TODO: improve this type
IPMICredentials = Dict[str, str]
ManagementCredentials = Union[SNMPCredentials, IPMICredentials]


def max_cachefile_age(
    *,
    checking: Optional[int] = None,
    discovery: Optional[int] = None,
    inventory: Optional[int] = None,
) -> MaxAge:
    return MaxAge(
        checking=check_max_cachefile_age if checking is None else checking,
        # next line: inventory_max_cachefile_age is *not a typo*, old name for discovery!
        discovery=inventory_max_cachefile_age if discovery is None else discovery,
        # next line: hard coded default, not configurable.
        inventory=120 if inventory is None else inventory,
    )


class ExitSpec(TypedDict, total=False):
    empty_output: int
    connection: int
    timeout: int
    exception: int
    wrong_version: int
    missing_sections: int
    specific_missing_sections: List[Tuple[str, int]]
    restricted_address_mismatch: int


class _NestedExitSpec(ExitSpec, total=False):
    overall: ExitSpec
    individual: Dict[str, ExitSpec]


class TimespecificParamList(list):
    pass


def get_variable_names() -> List[str]:
    """Provides the list of all known configuration variables."""
    return [k for k in default_config.__dict__ if k[0] != "_"]


def get_default_config() -> Dict[str, Any]:
    """Provides a dictionary containing the Check_MK default configuration"""
    cfg: Dict[str, Any] = {}
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


def _clear_check_variables_from_default_config(variable_names: List[str]) -> None:
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
    cvn = check_variable_names()

    check_variables = {}
    for varname in cvn:
        check_variables[varname] = global_dict.pop(varname)

    set_check_variables(check_variables)
    _clear_check_variables_from_default_config(cvn)


#.
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


def load(with_conf_d: bool = True,
         validate_hosts: bool = True,
         exclude_parents_mk: bool = False) -> None:
    _initialize_config()

    vars_before_config = all_nonfunction_vars()

    _load_config(with_conf_d, exclude_parents_mk)
    _transform_mgmt_config_vars_from_140_to_150()
    _initialize_derived_config_variables()

    _perform_post_config_loading_actions()

    if validate_hosts:
        _verify_non_duplicate_hosts()

    # Such validation only makes sense when all checks have been loaded
    if all_checks_loaded():
        _validate_configuraton_variables(vars_before_config)
        _verify_no_deprecated_check_rulesets()

    _verify_no_deprecated_variables_used()


def load_packed_config(serial: OptionalConfigSerial) -> None:
    """Load the configuration for the CMK helpers of CMC

    These files are written by PackedConfig().

    Should have a result similar to the load() above. With the exception that the
    check helpers would only need check related config variables.

    The validations which are performed during load() also don't need to be performed.
    """
    _initialize_config()
    globals().update(PackedConfigStore(serial).read())
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
        super(SetFolderPathAbstract, self).__init__(the_object)  # type: ignore[call-arg]
        self._current_path: Optional[str] = None

    def set_current_path(self, current_path: Optional[str]) -> None:
        self._current_path = current_path

    def _set_folder_paths(self, new_hosts: List[str]) -> None:
        if self._current_path is None:
            return
        for hostname in strip_tags(list(new_hosts)):
            host_paths[hostname] = self._current_path


class SetFolderPathList(SetFolderPathAbstract, list):
    def __iadd__(self, new_hosts: Iterable[Any]) -> 'SetFolderPathList':
        assert isinstance(new_hosts, list)
        self._set_folder_paths(new_hosts)
        return super(SetFolderPathList, self).__iadd__(new_hosts)

    # Probably unused
    def __add__(self, new_hosts: Iterable[Any]) -> 'SetFolderPathList':
        assert isinstance(new_hosts, list)
        self._set_folder_paths(new_hosts)
        return SetFolderPathList(super(SetFolderPathList, self).__add__(new_hosts))

    # Probably unused
    def append(self, new_host: str) -> None:
        self._set_folder_paths([new_host])
        super(SetFolderPathList, self).append(new_host)


class SetFolderPathDict(SetFolderPathAbstract, dict):
    # TODO: How to annotate this?
    def update(self, new_hosts):
        # not-yet-a-type
        self._set_folder_paths(new_hosts)
        return super(SetFolderPathDict, self).update(new_hosts)

    # Probably unused
    def __setitem__(self, cluster_name: Any, value: Any) -> Any:
        self._set_folder_paths([cluster_name])
        return super(SetFolderPathDict, self).__setitem__(cluster_name, value)


def cleanup_fs_used_marker_flag(log):
    # Test if User migrated during 1.6 to new name fs_used. If so delete marker flag file
    old_config_flag = os.path.join(cmk.utils.paths.omd_root, 'etc/check_mk/conf.d/fs_cap.mk')
    if os.path.exists(old_config_flag):
        log('remove flag %s\n' % old_config_flag)
        os.remove(old_config_flag)


def _load_config(with_conf_d: bool, exclude_parents_mk: bool) -> None:
    helper_vars = {
        "FOLDER_PATH": None,
    }

    global all_hosts
    global clusters

    all_hosts = SetFolderPathList(all_hosts)
    clusters = SetFolderPathDict(clusters)

    global_dict = globals()
    global_dict.update(helper_vars)

    cleanup_fs_used_marker_flag(console.info)  # safety cleanup for 1.6->1.7 update

    for path in _get_config_file_paths(with_conf_d):
        _f = str(path)
        # During parent scan mode we must not read in old version of parents.mk!
        if exclude_parents_mk and _f.endswith("/parents.mk"):
            continue

        try:
            # Make the config path available as a global variable to be used
            # within the configuration file. The FOLDER_PATH is only used by
            # rules.mk files these days, but may also be used in some legacy
            # config files or files generated by 3rd party mechanisms.
            current_path: Optional[str] = None
            folder_path: Optional[str] = None
            if _f.startswith(cmk.utils.paths.check_mk_config_dir + "/"):
                current_path = _f[len(cmk.utils.paths.check_mk_config_dir):]
                folder_path = os.path.dirname(current_path[1:])

            global_dict.update({
                "FOLDER_PATH": folder_path,
            })

            all_hosts.set_current_path(current_path)
            clusters.set_current_path(current_path)

            exec(open(_f).read(), global_dict, global_dict)

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
                console.error("Cannot read in configuration file %s: %s\n", _f, e)
            sys.exit(1)

    # Cleanup global helper vars
    for helper_var in helper_vars:
        del global_dict[helper_var]

    # Revert specialised SetFolderPath classes back to normal, because it improves
    # the lookup performance and the helper_vars are no longer available anyway..
    all_hosts = list(all_hosts)
    clusters = dict(clusters)


def _transform_mgmt_config_vars_from_140_to_150() -> None:
    #FIXME We have to transform some configuration variables from host attributes
    # to cmk.base configuration variables because during the migration step from
    # 1.4.0 to 1.5.0 some config variables are not known in cmk.base. These variables
    # are 'management_protocol' and 'management_snmp_community'.
    # Clean this up one day!
    for hostname, attributes in host_attributes.items():
        for name, var in [
            ('management_protocol', management_protocol),
            ('management_snmp_community', management_snmp_credentials),
        ]:
            if attributes.get(name):
                var.setdefault(hostname, attributes[name])


def _transform_plugin_names_from_160_to_170(global_dict: Dict[str, Any]) -> None:
    # Pre 1.7.0 check plugin names may have dots or dashes (one case) in them.
    # Now they don't, and we have to translate all variables that may use them:
    if "service_descriptions" in global_dict:
        global_dict["service_descriptions"] = {
            maincheckify(k): v for k, v in global_dict["service_descriptions"].items()
        }
    if "use_new_descriptions_for" in global_dict:
        global_dict["use_new_descriptions_for"] = [
            maincheckify(n) for n in global_dict["use_new_descriptions_for"]
        ]
    if "ignored_checktypes" in global_dict:
        global_dict["ignored_checktypes"] = [
            maincheckify(n) for n in global_dict["ignored_checktypes"]
        ]


def _collect_parameter_rulesets_from_globals(global_dict: Dict[str, Any]) -> None:

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
    }

    for var_name in vars_to_remove - partially_migrated:
        del global_dict[var_name]


# Create list of all files to be included during configuration loading
def _get_config_file_paths(with_conf_d: bool) -> List[Path]:
    list_of_files = [Path(cmk.utils.paths.main_config_file)]
    if with_conf_d:
        list_of_files += sorted(Path(cmk.utils.paths.check_mk_config_dir).glob("**/*.mk"),
                                key=cmk.utils.key_config_paths)
    for path in [Path(cmk.utils.paths.final_config_file), Path(cmk.utils.paths.local_config_file)]:
        if path.exists():
            list_of_files.append(path)
    return list_of_files


def _initialize_derived_config_variables() -> None:
    global service_service_levels, host_service_levels
    service_service_levels = extra_service_conf.get("_ec_sl", [])
    host_service_levels = extra_host_conf.get("_ec_sl", [])


def get_derived_config_variable_names() -> Set[str]:
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


def _validate_configuraton_variables(vars_before_config: Set[str]) -> None:
    """Check for invalid and deprecated configuration variables"""
    ignored_variables = {
        'hostname',
        'host_service_levels',
        'inventory_check_do_scan',
        'parts',
        'seen_hostnames',
        'service_service_levels',
        'taggedhost',
        'vars_before_config',
    }
    deprecated_variables = {
        # variable name                                # warning introduced *after* version
        'oracle_tablespaces_check_default_increment',  # 1.6
        'logwatch_dir',  # 1.6
        'logwatch_max_filesize',  # 1.6
        'logwatch_service_output',  # 1.6
        'logwatch_spool_dir',  # 1.6
    }

    unhandled_variables = all_nonfunction_vars() - vars_before_config - ignored_variables
    deprecated_found = unhandled_variables.intersection(deprecated_variables)
    invalid_found = unhandled_variables - deprecated_variables

    if deprecated_found:
        for name in sorted(deprecated_found):
            console.error("Deprecated configuration variable %r\n", name)
        console.error("--> Found %d deprecated variables\n" % len(deprecated_found))
        console.error("These variables will have no effect at best. Consider removing them.\n")

    if invalid_found:
        for name in sorted(invalid_found):
            console.error("Invalid configuration variable %r\n", name)
        console.error("--> Found %d invalid variables\n" % len(invalid_found))
        console.error("If you use own helper variables, please prefix them with _.\n")
        sys.exit(1)


def _verify_no_deprecated_variables_used() -> None:
    if isinstance(snmp_communities, dict):
        console.error("ERROR: snmp_communities cannot be a dict any more.\n")
        sys.exit(1)

    # Legacy checks have never been supported by CMC, were not configurable via WATO
    # and have been removed with Checkmk 1.6
    if legacy_checks:
        console.error(
            "Check_MK does not support the configuration variable \"legacy_checks\" anymore. "
            "Please use custom_checks or active_checks instead.\n")
        sys.exit(1)

    # "checks" declarations were never possible via WATO. They can be configured using
    # "static_checks" using the GUI. "checks" has been removed with Checkmk 1.6.
    if checks:
        console.error(
            "Check_MK does not support the configuration variable \"checks\" anymore. "
            "Please use \"static_checks\" instead (which is configurable via \"Manual checks\" in WATO).\n"
        )
        sys.exit(1)


def _verify_no_deprecated_check_rulesets() -> None:
    # this used to do something until the migration of logwatch.
    # TODO: decide wether we might still need this.
    deprecated_rulesets: List[Tuple[str, str]] = []
    for check_plugin_name, varname in deprecated_rulesets:
        check_context = get_check_context(check_plugin_name)
        if check_context.get(varname):
            console.warning(
                "Found rules for deprecated ruleset %r. These rules are not applied "
                "anymore. In case you still need them, you need to migrate them by hand. "
                "Otherwise you can remove them from your configuration." % varname)


def all_nonfunction_vars() -> Set[str]:
    return {
        name for name, value in globals().items()
        if name[0] != '_' and not hasattr(value, '__call__')
    }


def save_packed_config(serial: OptionalConfigSerial, config_cache: "ConfigCache") -> None:
    """Create and store a precompiled configuration for Checkmk helper processes"""
    PackedConfigStore(serial).write(PackedConfigGenerator(config_cache).generate())


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
        "extra_service_conf",
        "extra_nagios_conf",
    ]

    def __init__(self, config_cache: "ConfigCache") -> None:
        self._config_cache = config_cache

    def generate(self) -> Mapping[str, Any]:
        helper_config: MutableMapping[str, Any] = {}

        # These functions purpose is to filter out hosts which are monitored on different sites
        active_hosts = self._config_cache.all_active_hosts()
        active_clusters = self._config_cache.all_active_clusters()

        def filter_all_hosts(all_hosts_orig: AllHosts) -> List[HostName]:
            all_hosts_red = []
            for host_entry in all_hosts_orig:
                hostname = host_entry.split("|", 1)[0]
                if hostname in active_hosts:
                    all_hosts_red.append(host_entry)
            return all_hosts_red

        def filter_clusters(clusters_orig: AllClusters) -> Dict[HostName, List[HostName]]:
            clusters_red = {}
            for cluster_entry, cluster_nodes in clusters_orig.items():
                clustername = cluster_entry.split("|", 1)[0]
                if clustername in active_clusters:
                    clusters_red[cluster_entry] = cluster_nodes
            return clusters_red

        def filter_hostname_in_dict(
                values: Dict[HostName, Dict[str, str]]) -> Dict[HostName, Dict[str, str]]:
            values_red = {}
            for hostname, attributes in values.items():
                if hostname in active_hosts:
                    values_red[hostname] = attributes
            return values_red

        filter_var_functions: Dict[str, Callable[[Any], Any]] = {
            "all_hosts": filter_all_hosts,
            "clusters": filter_clusters,
            "host_attributes": filter_hostname_in_dict,
            "ipaddresses": filter_hostname_in_dict,
            "ipv6addresses": filter_hostname_in_dict,
            "explicit_snmp_communities": filter_hostname_in_dict,
            "hosttags": filter_hostname_in_dict,  # unknown key, might be typo or legacy option
            "host_tags": filter_hostname_in_dict,
            "host_paths": filter_hostname_in_dict
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
    def __init__(self, serial: OptionalConfigSerial) -> None:
        base_path: Final[Path] = cmk.utils.paths.make_helper_config_path(serial)
        self.path: Final[Path] = base_path / "precompiled_check_config.mk"

    def write(self, helper_config: Mapping[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = self.path.with_suffix(self.path.suffix + ".compiled")
        with tmp_path.open("wb") as compiled_file:
            pickle.dump(helper_config, compiled_file)
        tmp_path.rename(self.path)

    def read(self) -> Mapping[str, Any]:
        with self.path.open("rb") as f:
            return pickle.load(f)


def make_core_autochecks_dir(serial: OptionalConfigSerial) -> Path:
    return cmk.utils.paths.make_helper_config_path(serial) / "autochecks"


def make_core_discovered_host_labels_dir(serial: OptionalConfigSerial) -> Path:
    return cmk.utils.paths.make_helper_config_path(serial) / "discovered_host_labels"


@contextlib.contextmanager
def set_use_core_config(use_core_config: bool) -> Iterator[None]:
    """The keepalive helpers should always use the core configuration that
    has been created with "cmk -U". This includes the dynamic configuration
    parts like the autochecks.

    Instead of loading e.g. the autochecks from the regular path
    "var/check_mk/autochecks" the helper should always load the files from
    "var/check_mk/core/autochecks" instead.

    We ensure this by changing the global paths in cmk.utils.paths to point
    to the helper paths."""
    _orig_autochecks_dir = cmk.utils.paths.autochecks_dir
    _orig_discovered_host_labels_dir = cmk.utils.paths.discovered_host_labels_dir
    try:
        if use_core_config:
            cmk.utils.paths.autochecks_dir = str(make_core_autochecks_dir(LATEST_SERIAL))
            cmk.utils.paths.discovered_host_labels_dir = make_core_discovered_host_labels_dir(
                LATEST_SERIAL)
        else:
            cmk.utils.paths.autochecks_dir = cmk.utils.paths.base_autochecks_dir
            cmk.utils.paths.discovered_host_labels_dir = cmk.utils.paths.base_discovered_host_labels_dir
        yield
    finally:
        cmk.utils.paths.autochecks_dir = _orig_autochecks_dir
        cmk.utils.paths.discovered_host_labels_dir = _orig_discovered_host_labels_dir


#.
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


def strip_tags(tagged_hostlist: List[str]) -> List[str]:
    cache = _config_cache.get_dict("strip_tags")

    cache_id = tuple(tagged_hostlist)
    try:
        return cache[cache_id]
    except KeyError:
        result = [h.split('|', 1)[0] for h in tagged_hostlist]
        cache[cache_id] = result
        return result


def _get_shadow_hosts() -> ShadowHosts:
    # Only available with CEE
    return shadow_hosts if "shadow_hosts" in globals() else {}  # type: ignore[name-defined] # pylint: disable=undefined-variable


# This function should only be used during duplicate host check! It has to work like
# all_active_hosts() but with the difference that duplicates are not removed.
def _all_active_hosts_with_duplicates() -> List[str]:
    return _filter_active_hosts(get_config_cache(),
                                (strip_tags(list(all_hosts)) + strip_tags(list(clusters)) +
                                 strip_tags(list(_get_shadow_hosts()))))


def _filter_active_hosts(config_cache: 'ConfigCache',
                         hostlist: Iterable[str],
                         keep_offline_hosts: bool = False) -> List[str]:
    """Returns a set of active hosts for this site"""
    if only_hosts is None:
        if distributed_wato_site is None:
            return list(hostlist)

        return [
            hostname for hostname in hostlist
            if _host_is_member_of_site(config_cache, hostname, distributed_wato_site)
        ]

    if distributed_wato_site is None:
        if keep_offline_hosts:
            return list(hostlist)
        return [
            hostname for hostname in hostlist
            if config_cache.in_binary_hostlist(hostname, only_hosts)
        ]

    return [
        hostname for hostname in hostlist
        if _host_is_member_of_site(config_cache, hostname, distributed_wato_site) and
        (keep_offline_hosts or config_cache.in_binary_hostlist(hostname, only_hosts))
    ]


def _host_is_member_of_site(config_cache: 'ConfigCache', hostname: str, site: str) -> bool:
    # hosts without a site: tag belong to all sites
    return config_cache.tags_of_host(hostname).get("site",
                                                   distributed_wato_site) == distributed_wato_site


def duplicate_hosts() -> List[str]:
    seen_hostnames: Set[str] = set()
    duplicates: Set[str] = set()

    for hostname in _all_active_hosts_with_duplicates():
        if hostname in seen_hostnames:
            duplicates.add(hostname)
        else:
            seen_hostnames.add(hostname)

    return sorted(duplicates)


# Returns a list of all hosts which are associated with this site,
# but have been removed by the "only_hosts" rule. Normally these
# are the hosts which have the tag "offline".
#
# This is not optimized for performance, so use in specific situations.
def all_offline_hosts() -> Set[str]:
    config_cache = get_config_cache()

    hostlist = set(
        _filter_active_hosts(config_cache,
                             config_cache.all_configured_realhosts().union(
                                 config_cache.all_configured_clusters()),
                             keep_offline_hosts=True))

    if only_hosts is None:
        return set()

    return {
        hostname for hostname in hostlist
        if not config_cache.in_binary_hostlist(hostname, only_hosts)
    }


def all_configured_offline_hosts() -> Set[str]:
    config_cache = get_config_cache()
    hostlist = config_cache.all_configured_realhosts().union(config_cache.all_configured_clusters())

    if only_hosts is None:
        return set()

    return {
        hostname for hostname in hostlist
        if not config_cache.in_binary_hostlist(hostname, only_hosts)
    }


#.
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
def _get_old_cmciii_temp_description(item: Item) -> Tuple[bool, ServiceName]:
    if item is None:
        raise TypeError()

    if "Temperature" in item:
        return False, item  # old item format, no conversion

    parts = item.split(" ")
    if parts[0] == "Ambient":
        return False, "%s Temperature" % parts[1]

    if len(parts) == 2:
        return False, "%s %s.Temperature" % (parts[1], parts[0])

    if parts[1] == "LCP":
        parts[1] = "Liquid_Cooling_Package"
    return False, "%s %s.%s-Temperature" % (parts[1], parts[0], parts[2])


_old_service_descriptions = {
    "aix_memory": "Memory used",
    # While using the old description, don't append the item, even when discovered
    # with the new check which creates an item.
    "barracuda_mailqueues": lambda item: (False, "Mail Queue"),
    "brocade_sys_mem": "Memory used",
    "casa_cpu_temp": "Temperature %s",
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
            return "Unimplemented check %s / %s" % (check_plugin_name, item)
        return "Unimplemented check %s" % check_plugin_name

    plugin_name_str = str(plugin.name)
    # use user-supplied service description, if available
    add_item = True
    descr_format = service_descriptions.get(plugin_name_str)
    if not descr_format:
        old_descr = _old_service_descriptions.get(plugin_name_str)
        # handle renaming for backward compatibility
        if old_descr and plugin_name_str not in use_new_descriptions_for:
            # Can be a function to generate the old description more flexible.
            if callable(old_descr):
                add_item, descr_format = old_descr(item)
            else:
                descr_format = old_descr

        else:
            descr_format = plugin.service_name

    descr_format = ensure_str(descr_format)

    if add_item and isinstance(item, (str, numbers.Integral)):
        if "%s" not in descr_format:
            descr_format += " %s"
        descr = descr_format % (item,)
    else:
        descr = descr_format

    if "%s" in descr:
        raise MKGeneralException(
            "Found '%%s' in service description (Host: %s, Check plugin: %s, Item: %s). "
            "Please try to rediscover the service to fix this issue." %
            (hostname, plugin.name, item))

    return get_final_service_description(hostname, descr)


def _old_active_http_check_service_description(params: Union[Dict, Tuple]) -> str:
    name = params[0] if isinstance(params, tuple) else params["name"]
    return name[1:] if name.startswith("^") else "HTTP %s" % name


_old_active_check_service_descriptions = {
    "http": _old_active_http_check_service_description,
}


def active_check_service_description(
    hostname: HostName,
    hostalias: str,
    active_check_name: ActiveCheckPluginName,
    params: Dict,
) -> ServiceName:
    if active_check_name not in active_check_info:
        return "Unimplemented check %s" % active_check_name

    if (active_check_name in _old_active_check_service_descriptions and
            active_check_name not in use_new_descriptions_for):
        description = _old_active_check_service_descriptions[active_check_name](params)
    else:
        act_info = active_check_info[active_check_name]
        description = act_info["service_description"](params)

    description = description.replace('$HOSTNAME$', hostname).replace('$HOSTALIAS$', hostalias)

    return get_final_service_description(hostname, description)


def get_final_service_description(hostname: HostName, description: ServiceName) -> ServiceName:
    translations = get_service_translations(hostname)
    if translations:
        # Translate
        description = cmk.utils.translations.translate_service_description(
            translations, description)

    # Note: we strip the service description (remove spaces).
    # One check defines "Pages %s" as a description, but the item
    # can by empty in some cases. Nagios silently drops leading
    # and trailing spaces in the configuration file.
    description = description.strip()

    # Sanitize; Remove illegal characters from a service description
    cache = _config_cache.get_dict("final_service_description")
    try:
        new_description = cache[description]
    except KeyError:
        new_description = "".join([
            c for c in description
            if c not in (cmc_illegal_chars if is_cmc() else nagios_illegal_chars)
        ]).rstrip("\\")
        cache[description] = new_description

    return new_description


def service_ignored(
    host_name: HostName,
    check_plugin_name: Optional[CheckPluginName],
    description: Optional[ServiceName],
) -> bool:
    if check_plugin_name is not None:
        check_plugin_name_str = str(check_plugin_name)

        if check_plugin_name_str in ignored_checktypes:
            return True

        if _checktype_ignored_for_host(host_name, check_plugin_name_str):
            return True

    return (description is not None and get_config_cache().in_boolean_serviceconf_list(
        host_name,
        description,
        ignored_services,
    ))


def _checktype_ignored_for_host(
    host_name: HostName,
    check_plugin_name_str: str,
) -> bool:
    ignored = get_config_cache().host_extra_conf(host_name, ignored_checks)
    for e in ignored:
        if check_plugin_name_str in e:
            return True
    return False


# TODO: Make this use the generic "rulesets" functions
# a) This function has never been configurable via WATO (see https://mathias-kettner.de/checkmk_service_dependencies.html)
# b) It only affects the Nagios core - CMC does not implement service dependencies
# c) This function implements some specific regex replacing match+replace which makes it incompatible to
#    regular service rulesets. Therefore service_extra_conf() can not easily be used :-/
def service_depends_on(hostname: HostName, servicedesc: ServiceName) -> List[ServiceName]:
    """Return a list of services this services depends upon"""
    deps = []
    config_cache = get_config_cache()
    for entry in service_dependencies:
        entry, rule_options = tuple_rulesets.get_rule_options(entry)
        if rule_options.get("disabled"):
            continue

        if len(entry) == 3:
            depname, hostlist, patternlist = entry
            tags: List[str] = []
        elif len(entry) == 4:
            depname, tags, hostlist, patternlist = entry
        else:
            raise MKGeneralException("Invalid entry '%r' in service dependencies: "
                                     "must have 3 or 4 entries" % entry)

        if tuple_rulesets.hosttags_match_taglist(config_cache.tag_list_of_host(hostname),
                                                 tags) and tuple_rulesets.in_extraconf_hostlist(
                                                     hostlist, hostname):
            for pattern in patternlist:
                matchobject = regex(pattern).search(servicedesc)
                if matchobject:
                    try:
                        item = matchobject.groups()[-1]
                        deps.append(depname % item)
                    except Exception:
                        deps.append(depname)
    return deps


#.
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


def translate_piggyback_host(sourcehost: HostName, backedhost: HostName) -> HostName:
    translation = _get_piggyback_translations(sourcehost)

    # To make it possible to match umlauts we need to change the hostname
    # to a unicode string which can then be matched with regexes etc.
    # We assume the incoming name is correctly encoded in UTF-8
    decoded_backedhost = ensure_str_with_fallback(backedhost,
                                                  encoding="utf-8",
                                                  fallback=fallback_agent_output_encoding)
    return ensure_str(cmk.utils.translations.translate_hostname(translation, decoded_backedhost))


def _get_piggyback_translations(hostname: HostName) -> cmk.utils.translations.TranslationOptions:
    """Get a dict that specifies the actions to be done during the hostname translation"""
    rules = get_config_cache().host_extra_conf(hostname, piggyback_translation)
    translations: cmk.utils.translations.TranslationOptions = {}
    for rule in rules[::-1]:
        translations.update(rule)
    return translations


def get_service_translations(hostname: HostName) -> cmk.utils.translations.TranslationOptions:
    translations_cache = _config_cache.get_dict("service_description_translations")
    if hostname in translations_cache:
        return translations_cache[hostname]

    rules = get_config_cache().host_extra_conf(hostname, service_description_translation)
    translations: cmk.utils.translations.TranslationOptions = {}
    for rule in rules[::-1]:
        for k, v in rule.items():
            if isinstance(v, list):
                translations.setdefault(k, set())
                translations[k] |= set(v)
            else:
                translations[k] = v

    translations_cache[hostname] = translations
    return translations


def get_http_proxy(http_proxy: Tuple[str, str]) -> Optional[str]:
    """Returns proxy URL to be used for HTTP requests

    Pass a value configured by the user using the HTTPProxyReference valuespec to this function
    and you will get back ether a proxy URL, an empty string to enforce no proxy usage or None
    to use the proxy configuration from the process environment.
    """
    if not isinstance(http_proxy, tuple):
        return None

    proxy_type, value = http_proxy

    if proxy_type == "environment":
        return None

    if proxy_type == "global":
        return http_proxies.get(value, {}).get("proxy_url", None)

    if proxy_type == "url":
        return value

    if proxy_type == "no_proxy":
        return ""

    return None


#.
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
def in_extraconf_servicelist(service_patterns: List[str], service: str) -> bool:
    optimized_pattern = tuple_rulesets.convert_pattern_list(service_patterns)
    if not optimized_pattern:
        return False
    return optimized_pattern.match(service) is not None


#.
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
_check_contexts: Dict[str, Any] = {}
# has a separate sub-dictionary, named by the check name.
# It is populated with the includes and the check itself.

# The following data structures will be filled by the checks
# all known checks
check_info: Dict[str, Dict[str, Any]] = {}
# Lookup for legacy names
legacy_check_plugin_names: Dict[CheckPluginName, str] = {}
# library files needed by checks
check_includes: Dict[str, List[Any]] = {}
# optional functions for parameter precompilation
precompile_params: Dict[str, Callable[[str, str, Dict[str, Any]], Any]] = {}
# dictionary-configured checks declare their default level variables here
check_default_levels: Dict[str, Any] = {}
# factory settings for dictionary-configured checks
factory_settings: Dict[str, Dict[str, Any]] = {}
# variables (names) in checks/* needed for check itself
check_config_variables: List[Any] = []
# whichs OIDs to fetch for which check (for tabular information)
snmp_info: Dict[str, Union[Tuple[Any], List[Tuple[Any]]]] = {}
# SNMP autodetection
snmp_scan_functions: Dict[str, SNMPScanFunction] = {}
# definitions of active "legacy" checks
active_check_info: Dict[str, Dict[str, Any]] = {}
special_agent_info: Dict[str, SpecialAgentInfoFunction] = {}

# Names of variables registered in the check files. This is used to
# keep track of the variables needed by each file. Those variables are then
# (if available) read from the config and applied to the checks module after
# reading in the configuration of the user.
_check_variables: Dict[str, List[Any]] = {}
# keeps the default values of all the check variables
_check_variable_defaults: Dict[str, Any] = {}
_all_checks_loaded = False

# workaround: set of check-groups that are to be treated as service-checks even if
#   the item is None
service_rule_groups = {"temperature"}

#.
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


def load_all_agent_based_plugins(get_check_api_context: GetCheckApiContext,) -> List[str]:
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

    # LEGACY INVENTORY PLUGINS
    # unfortunately, inventory_plugins will import cmk.base.config,
    # so we have to use a local import for now.
    # We could do further refactoring to resolve this, but the time would probably
    # be spent better migrating the legacy inventory plugins to the new API...
    import cmk.base.inventory_plugins as inventory_plugins  # pylint: disable=import-outside-toplevel
    errors.extend(
        inventory_plugins.load_legacy_inventory_plugins(
            get_check_api_context,
            agent_based_register.inventory_plugins_legacy.get_inventory_context,
        ))

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


def get_plugin_paths(*dirs: str) -> List[str]:
    filelist: List[str] = []
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
def load_checks(get_check_api_context: GetCheckApiContext, filelist: List[str]) -> List[str]:
    cmk_global_vars = set(get_variable_names())

    loaded_files: Set[str] = set()

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
                    "default_levels_variable")

            if default_levels_varname:
                # Add the initial configuration to the check context to have a consistent state
                check_context[default_levels_varname] = factory_settings.get(
                    default_levels_varname, {})
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

    errors = (_extract_agent_and_snmp_sections(validate_creation_kwargs=did_compile) +
              _extract_check_plugins(validate_creation_kwargs=did_compile))
    initialize_check_type_caches()

    return errors


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

    # store.save_file() creates file empty for locking (in case it does not exists).
    # Skip loading the file.
    # Note: When raising here this process will also write the file. This means it
    # will write it another time after it was written by the other process. This
    # could be optimized. Since the whole caching here is a temporary(tm) soltion,
    # we leave it as it is.
    if cache_stat.st_size == 0:
        raise OSError("Cache generation in progress (file is locked)")

    x = open(cache_file_path).read().strip()
    if not x:
        return []  # Shouldn't happen. Empty files are handled above
    return x.split("|")


def _write_check_include_cache(cache_file_path: str, includes: CheckIncludes) -> None:
    store.makedirs(os.path.dirname(cache_file_path))
    store.save_file(cache_file_path, "%s\n" % "|".join(includes))


def _include_cache_file_path(path: str) -> str:
    is_local = path.startswith(str(cmk.utils.paths.local_checks_dir))
    return os.path.join(cmk.utils.paths.include_cache_dir, "local" if is_local else "builtin",
                        os.path.basename(path))


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
            if not isinstance(key, ast.Str):
                continue
            if key.s == "includes":
                if isinstance(val, ast.List):
                    for element in val.elts:
                        if not isinstance(element, ast.Str):
                            raise MKGeneralException("Includes must be a list of include file "
                                                     "names, found '%s'" % type(element))
                        include_names[element.s] = True
                else:
                    raise MKGeneralException("Includes must be a list of include file names, "
                                             "found '%s'" % type(val))

    def _load_from_check_includes(node: ast.Assign) -> None:
        if isinstance(node.value, ast.List):
            for element in node.value.elts:
                if not isinstance(element, ast.Str):
                    raise MKGeneralException("Includes must be a list of include file "
                                             "names, found '%s'" % type(element))
                include_names[element.s] = True

    tree = ast.parse(open(check_file_path).read())
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


def _plugin_pathnames_in_directory(path: str) -> List[str]:
    if path and os.path.exists(path):
        return sorted([
            path + "/" + f
            for f in os.listdir(path)
            if not f.startswith(".") and not f.endswith(".include")
        ])
    return []


class _PYCHeader():
    """ A pyc header according to https://www.python.org/dev/peps/pep-0552/"""
    SIZE = 16

    def __init__(self, magic: bytes, hash_: int, origin_mtime: int, f_size: int) -> None:
        self.magic = magic
        self.hash = hash_
        self.origin_mtime = origin_mtime
        self.f_size = f_size

    @classmethod
    def from_file(cls, path: str) -> "_PYCHeader":
        with open(path, "rb") as handle:
            raw_bytes = handle.read(cls.SIZE)
        return cls(*struct.unpack("4s3I", raw_bytes))


# TODO: Check if this totally non-portable Kung Fu still works with Python 3!
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
        console.vverbose("Precompile %s to %s\n" % (path, precompiled_path))
        store.makedirs(os.path.dirname(precompiled_path))
        py_compile.compile(path, precompiled_path, doraise=True)

    exec(marshal.loads(open(precompiled_path, "rb").read()[_PYCHeader.SIZE:]), check_context)

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
    return os.path.join(cmk.utils.paths.precompiled_checks_dir, "local" if is_local else "builtin",
                        os.path.basename(path))


def check_variable_names() -> List[str]:
    return list(_check_variables)


def _set_check_variable_defaults(
    variables: Dict[str, Any],
    context_idents: List[str],
    skip_names: Optional[Set[str]] = None,
):
    """Save check variables for e.g. after config loading that the config can
    be added to the check contexts."""
    for varname, value in variables.items():
        if skip_names is not None and varname in skip_names:
            continue

        if varname.startswith("_"):
            continue

        # NOTE: Classes and builtin functions are callable, too!
        if callable(value) or inspect.ismodule(value):
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
def convert_check_info() -> None:
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
        "handle_real_time_checks": False,
        "default_levels_variable": None,
        "node_info": False,
        "extra_sections": [],
        "service_description": None,
        "has_perfdata": False,
        "management_board": None,
    }

    for check_plugin_name, info in check_info.items():
        section_name = section_name_of(check_plugin_name)

        if not isinstance(info, dict):
            # Convert check declaration from old style to new API
            check_function, descr, has_perfdata, inventory_function = info

            scan_function = snmp_scan_functions.get(check_plugin_name,
                                                    snmp_scan_functions.get(section_name))

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
                        "The check '%s' declares an unexpected key '%s' in 'check_info'." %
                        (check_plugin_name, key))

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
                    raise MKGeneralException("Invalid check implementation: node_info for %s is "
                                             "True, but base check %s not defined" %
                                             (check_plugin_name, section_name))

            elif check_info[section_name]["node_info"] != info["node_info"]:
                raise MKGeneralException("Invalid check implementation: node_info for %s "
                                         "and %s are different." %
                                         ((section_name, check_plugin_name)))

    # Now gather snmp_info and snmp_scan_function back to the
    # original arrays. Note: these information is tied to a "agent section",
    # not to a check. Several checks may use the same SNMP info and scan function.
    for check_plugin_name, info in check_info.items():
        section_name = section_name_of(check_plugin_name)
        if info["snmp_info"] and section_name not in snmp_info:
            snmp_info[section_name] = info["snmp_info"]

        if info["snmp_scan_function"] and section_name not in snmp_scan_functions:
            snmp_scan_functions[section_name] = info["snmp_scan_function"]


AUTO_MIGRATION_ERR_MSG = ("Failed to auto-migrate legacy plugin to %s: %s\n"
                          "Please refer to Werk 10601 for more information.\n")


def _extract_agent_and_snmp_sections(
    *,
    validate_creation_kwargs: bool,
) -> List[str]:
    """Here comes the next layer of converting-to-"new"-api.

    For the new check-API in cmk/base/api/agent_based, we use the accumulated information
    in check_info, snmp_scan_functions and snmp_info to create API compliant section plugins.
    """
    errors = []
    # start with the "main"-checks, the ones without '.' in their names:
    for check_plugin_name in sorted(check_info, key=lambda name: ('.' in name, name)):
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
                    ))
            else:
                agent_based_register.add_section_plugin(
                    create_agent_section_plugin_from_legacy(
                        section_name,
                        check_info_dict,
                        validate_creation_kwargs=validate_creation_kwargs,
                    ))
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
) -> List[str]:
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
                CheckPluginName(maincheckify(check_plugin_name)))
            if present_plugin is not None and present_plugin.module is not None:
                # module is not None => it's a new plugin.
                # implemented here instead of the agent based register so that new API code does not
                # need to include any handling of legacy cases
                raise ValueError(
                    f'Legacy check plugin still exists for check plugin {check_plugin_name}. '
                    'Please remove legacy plugin.')
            agent_based_register.add_check_plugin(
                create_check_plugin_from_legacy(
                    check_plugin_name,
                    check_info_dict,
                    check_info.get(check_plugin_name.split('.')[0], {}).get('extra_sections', []),
                    factory_settings,
                    get_check_context,
                    validate_creation_kwargs=validate_creation_kwargs,
                ))
        except (NotImplementedError, KeyError, AssertionError, ValueError) as exc:
            # NOTE: as a result of a missing check plugin, the corresponding services
            #       will be silently droppend on most (all?) occasions.
            if cmk.utils.debug.enabled():
                raise MKGeneralException(exc) from exc
            errors.append(AUTO_MIGRATION_ERR_MSG % ("check plugin", check_plugin_name))

    return errors


# These caches both only hold the base names of the checks
def initialize_check_type_caches() -> None:
    snmp_cache = _runtime_cache.get_set("check_type_snmp")
    snmp_cache.update(snmp_info)

    tcp_cache = _runtime_cache.get_set("check_type_tcp")
    for check_plugin_name in check_info:
        section_name = section_name_of(check_plugin_name)
        if section_name not in snmp_cache:
            tcp_cache.add(section_name)


#.
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
    default_parameters: Optional[Dict[str, Any]],
    ruleset_name: Optional[RuleSetName],
    ruleset_type: Literal["all", "merged"],
    rules_getter_function: Callable[[RuleSetName], List[Dict[str, Any]]],
) -> Union[None, Parameters, List[Parameters]]:
    if default_parameters is None:
        # This means the function will not acctept any params.
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
        params = default_parameters.copy()
        params.update(config_cache.host_extra_conf_merged(host_name, rules))
        return Parameters(params)

    # validation should have prevented this
    raise NotImplementedError(f"unknown discovery rule set type {ruleset_type!r}")


def get_discovery_parameters(
    host_name: HostName,
    check_plugin: CheckPlugin,
) -> Union[None, Parameters, List[Parameters]]:
    return _get_plugin_parameters(
        host_name=host_name,
        default_parameters=check_plugin.discovery_default_parameters,
        ruleset_name=check_plugin.discovery_ruleset_name,
        ruleset_type=check_plugin.discovery_ruleset_type,
        rules_getter_function=agent_based_register.get_discovery_ruleset,
    )


def get_host_label_parameters(
    host_name: HostName,
    section_plugin: SectionPlugin,
) -> Union[None, Parameters, List[Parameters]]:
    return _get_plugin_parameters(
        host_name=host_name,
        default_parameters=section_plugin.host_label_default_parameters,
        ruleset_name=section_plugin.host_label_ruleset_name,
        ruleset_type=section_plugin.host_label_ruleset_type,
        rules_getter_function=agent_based_register.get_host_label_ruleset,
    )


def compute_check_parameters(
    host: HostName,
    checktype: Union[CheckPluginNameStr, CheckPluginName],
    item: Item,
    params: LegacyCheckParameters,
    for_static_checks: bool = False,
) -> Optional[LegacyCheckParameters]:
    """Compute parameters for a check honoring factory settings,
    default settings of user in main.mk, check_parameters[] and
    the values code in autochecks (given as parameter params)"""
    # TODO (mo): The signature of this function has been broadened to accept CheckPluginNameStr
    # *or* CheckPluginName alternatively (to ease migration).
    # Once we're ready, it should only accept the CheckPluginName (or even the plugin itself, we will
    # see)
    if isinstance(checktype, CheckPluginName):
        plugin_name = checktype
    else:
        plugin_name = CheckPluginName(maincheckify(checktype))

    plugin = agent_based_register.get_check_plugin(plugin_name)
    if plugin is None:  # handle vanished check plugin
        return None

    if plugin.check_default_parameters is not None:
        params = _update_with_default_check_parameters(plugin.check_default_parameters, params)

    if not for_static_checks:
        params = _update_with_configured_check_parameters(host, plugin, item, params)

    return params


def _update_with_default_check_parameters(
    check_default_parameters: Dict[str, Any],
    params: LegacyCheckParameters,
) -> LegacyCheckParameters:

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
        host: HostName, plugin: CheckPlugin, item: Item,
        params: LegacyCheckParameters) -> LegacyCheckParameters:
    descr = service_description(host, plugin.name, item)

    config_cache = get_config_cache()

    # Get parameters configured via checkgroup_parameters
    entries = _get_checkgroup_parameters(
        config_cache,
        host,
        str(plugin.check_ruleset_name),
        item,
        descr,
    ) if plugin.check_ruleset_name is not None else []

    # Get parameters configured via check_parameters
    entries += config_cache.service_extra_conf(host, descr, check_parameters)

    if entries:
        if has_timespecific_params(entries):
            # some parameters include timespecific settings
            # these will be executed just before the check execution
            return set_timespecific_param_list(entries, params)

        # loop from last to first (first must have precedence)
        for entry in entries[::-1]:
            if isinstance(params, dict) and isinstance(entry, dict):
                params.update(entry)
            else:
                if isinstance(entry, dict):
                    # The entry still has the reference from the rule..
                    # If we don't make a deepcopy the rule might be modified by
                    # a followup params.update(...)
                    entry = copy.deepcopy(entry)
                params = entry
    return params


def has_timespecific_params(entries: Any) -> bool:
    if entries is None:
        return False
    if isinstance(entries, dict) and "tp_default_value" in entries:
        return True
    try:
        for entry in entries:
            if isinstance(entry, dict) and "tp_default_value" in entry:
                return True
    except TypeError:
        return False
    return False


def set_timespecific_param_list(entries, params):
    return TimespecificParamList(entries + [params])


def _get_checkgroup_parameters(config_cache: 'ConfigCache', host: HostName, checkgroup: RulesetName,
                               item: Item, descr: ServiceName) -> List[LegacyCheckParameters]:
    rules = checkgroup_parameters.get(checkgroup)
    if rules is None:
        return []

    try:
        # checks without an item
        if item is None and checkgroup not in service_rule_groups:
            return config_cache.host_extra_conf(host, rules)

        # At the moment the items are not validated strictly, this means we can have
        # integers or something else here. Convert them to unicode for easier handling
        # in the following code.
        # TODO: This should be strictly validated by the check API in 1.7.
        if item is not None and not isinstance(item, str):
            item = str(item)

        # checks with an item need service-specific rules
        match_object = config_cache.ruleset_match_object_for_checkgroup_parameters(
            host, item, descr)
        return list(
            config_cache.ruleset_matcher.get_service_ruleset_values(match_object,
                                                                    rules,
                                                                    is_binary=False))
    except MKGeneralException as e:
        raise MKGeneralException(str(e) + " (on host %s, checkgroup %s)" % (host, checkgroup))


def get_management_board_precedence(check_plugin_name: CheckPluginNameStr,
                                    plugins_info: CheckInfo) -> str:
    # TODO(mo): The first .get() has been added as quick fix for an issue during new Check-API
    # development. This should not be kept after the situation in clearer.
    mgmt_board = plugins_info.get(check_plugin_name, {}).get("management_board")
    if mgmt_board is None:
        return check_api_utils.HOST_PRECEDENCE
    return mgmt_board


cmk.utils.cleanup.register_cleanup(check_api_utils.reset_hostname)

#.
#   .--Host Configuration--------------------------------------------------.
#   |                         _   _           _                            |
#   |                        | | | | ___  ___| |_                          |
#   |                        | |_| |/ _ \/ __| __|                         |
#   |                        |  _  | (_) \__ \ |_                          |
#   |                        |_| |_|\___/|___/\__|                         |
#   |                                                                      |
#   |    ____             __ _                       _   _                 |
#   |   / ___|___  _ __  / _(_) __ _ _   _ _ __ __ _| |_(_) ___  _ __      |
#   |  | |   / _ \| '_ \| |_| |/ _` | | | | '__/ _` | __| |/ _ \| '_ \     |
#   |  | |__| (_) | | | |  _| | (_| | |_| | | | (_| | |_| | (_) | | | |    |
#   |   \____\___/|_| |_|_| |_|\__, |\__,_|_|  \__,_|\__|_|\___/|_| |_|    |
#   |                          |___/                                       |
#   +----------------------------------------------------------------------+


class HostConfig:
    def __init__(self, config_cache: 'ConfigCache', hostname: str) -> None:
        super(HostConfig, self).__init__()
        self.hostname = hostname

        self._config_cache = config_cache

        self._explicit_attributes_lookup = None
        self.is_cluster = self._is_cluster()
        # TODO: Rename this to self.clusters?
        self.part_of_clusters = self._config_cache.clusters_of(hostname)
        self.nodes = self._config_cache.nodes_of(hostname)

        # TODO: Rename self.tags to self.tag_list and self.tag_groups to self.tags
        self.tags = self._config_cache.tag_list_of_host(hostname)
        self.tag_groups = self._config_cache.tags_of_host(hostname)

        self.labels = self._config_cache.labels.labels_of_host(self._config_cache.ruleset_matcher,
                                                               hostname)
        self.label_sources = self._config_cache.labels.label_sources_of_host(
            self._config_cache.ruleset_matcher, hostname)

        # Basic types
        self.is_tcp_host: bool = self._config_cache.in_binary_hostlist(hostname, tcp_hosts)
        self.is_snmp_host: bool = self._config_cache.in_binary_hostlist(hostname, snmp_hosts)
        self.is_usewalk_host: bool = self._config_cache.in_binary_hostlist(hostname, usewalk_hosts)

        if self.tag_groups["piggyback"] == "piggyback":
            self.is_piggyback_host = True
        elif self.tag_groups["piggyback"] == "no-piggyback":
            self.is_piggyback_host = False
        else:  # Legacy automatic detection
            self.is_piggyback_host = self.has_piggyback_data

        # Agent types
        self.is_agent_host: bool = self.is_tcp_host or self.is_piggyback_host
        self.management_protocol = management_protocol.get(hostname)
        self.has_management_board: bool = self.management_protocol is not None
        self.is_ping_host = not (self.is_snmp_host or self.is_agent_host or
                                 self.has_management_board)

        self.is_dual_host = self.is_tcp_host and self.is_snmp_host
        self.is_all_agents_host = self.tag_groups["agent"] == "all-agents"
        self.is_all_special_agents_host = self.tag_groups["agent"] == "special-agents"

        # IP addresses
        # Whether or not the given host is configured not to be monitored via IP
        self.is_no_ip_host = self.tag_groups["address_family"] == "no-ip"
        self.is_ipv6_host = "ip-v6" in self.tag_groups
        # Whether or not the given host is configured to be monitored via IPv4.
        # This is the case when it is set to be explicit IPv4 or implicit (when
        # host is not an IPv6 host and not a "No IP" host)
        self.is_ipv4_host = "ip-v4" in self.tag_groups or (not self.is_ipv6_host and
                                                           not self.is_no_ip_host)

        self.is_ipv4v6_host = "ip-v6" in self.tag_groups and "ip-v4" in self.tag_groups

        # Whether or not the given host is configured to be monitored primarily via IPv6
        self.is_ipv6_primary = (not self.is_ipv4v6_host and self.is_ipv6_host) or (
            self.is_ipv4v6_host and self._primary_ip_address_family_of() == "ipv6")

    @staticmethod
    def make_snmp_config(hostname: HostName, address: HostAddress) -> SNMPHostConfig:
        return get_config_cache().get_host_config(hostname).snmp_config(address)

    @staticmethod
    def make_host_config(hostname: HostName) -> 'HostConfig':
        return get_config_cache().get_host_config(hostname)

    @property
    def has_piggyback_data(self) -> bool:
        time_settings: List[Tuple[Optional[str], str, int]] = self.piggybacked_host_files
        time_settings.append((None, "max_cache_age", piggyback_max_cachefile_age))

        if piggyback.has_piggyback_raw_data(self.hostname, time_settings):
            return True

        return Path(cmk.utils.paths.var_dir, "persisted_sections", "piggyback",
                    self.hostname).exists()

    @property
    def piggybacked_host_files(self) -> List[Tuple[Optional[str], str, int]]:
        rules = self._config_cache.host_extra_conf(self.hostname, piggybacked_host_files)
        if rules:
            return self._flatten_piggybacked_host_files_rule(rules[0])
        return []

    def _flatten_piggybacked_host_files_rule(
            self, rule: Dict[str, Any]) -> List[Tuple[Optional[str], str, int]]:
        """This rule is a first match rule.

        Max cache age, validity period and state are configurable wihtin this
        rule for all piggybacked host or per piggybacked host of this source.
        In order to differentiate later for which piggybacked hosts a parameter
        is used we flat this rule to a homogeneous data structure:
            (HOST, KEY): VALUE
        Then piggyback.py:_get_piggyback_processed_file_info can evaluate the
        parameters generically."""
        flat_rule: List[Tuple[Optional[str], str, int]] = []

        max_cache_age = rule.get('global_max_cache_age')
        if max_cache_age is not None and max_cache_age != "global":
            flat_rule.append((self.hostname, 'max_cache_age', max_cache_age))

        global_validity_setting = rule.get('global_validity', {})

        period = global_validity_setting.get("period")
        if period is not None:
            flat_rule.append((self.hostname, 'validity_period', period))

        check_mk_state = global_validity_setting.get("check_mk_state")
        if check_mk_state is not None:
            flat_rule.append((self.hostname, 'validity_state', check_mk_state))

        for setting in rule.get('per_piggybacked_host', []):
            if "piggybacked_hostname" in setting:
                piggybacked_hostname_expressions = [setting["piggybacked_hostname"]]
            elif "piggybacked_hostname_expressions" in setting:
                piggybacked_hostname_expressions = setting["piggybacked_hostname_expressions"]
            else:
                piggybacked_hostname_expressions = []

            for piggybacked_hostname_expr in piggybacked_hostname_expressions:
                max_cache_age = setting.get('max_cache_age')
                if max_cache_age is not None and max_cache_age != "global":
                    flat_rule.append((piggybacked_hostname_expr, 'max_cache_age', max_cache_age))

                validity_setting = setting.get('validity', {})
                if not validity_setting:
                    continue

                period = validity_setting.get("period")
                if period is not None:
                    flat_rule.append((piggybacked_hostname_expr, 'validity_period', period))

                check_mk_state = validity_setting.get("check_mk_state")
                if check_mk_state is not None:
                    flat_rule.append((piggybacked_hostname_expr, 'validity_state', check_mk_state))

        return flat_rule

    @property
    def check_mk_check_interval(self) -> int:
        return self._config_cache.extra_attributes_of_service(self.hostname,
                                                              'Check_MK')['check_interval']

    def _primary_ip_address_family_of(self) -> str:
        rules = self._config_cache.host_extra_conf(self.hostname, primary_address_family)
        if rules:
            return rules[0]
        return "ipv4"

    @property
    def alias(self) -> str:

        # Alias by explicit matching
        alias = self._explicit_host_attributes.get("alias")
        if alias:
            return alias

        # Alias by rule matching
        aliases = self._config_cache.host_extra_conf(self.hostname,
                                                     extra_host_conf.get("alias", []))

        # Fallback alias
        if not aliases:
            return self.hostname

        # First rule match
        return aliases[0]

    # TODO: Move cluster/node parent handling to this function
    @property
    def parents(self) -> List[str]:
        """Returns the parents of a host configured via ruleset "parents"

        Use only those parents which are defined and active in all_hosts"""
        parent_candidates = set()

        # Parent by explicit matching
        explicit_parents = self._explicit_host_attributes.get("parents")
        if explicit_parents:
            parent_candidates.update(explicit_parents.split(","))

        # Respect the ancient parents ruleset. This can not be configured via WATO and should be removed one day
        for parent_names in self._config_cache.host_extra_conf(self.hostname, parents):
            parent_candidates.update(parent_names.split(","))

        return list(parent_candidates.intersection(self._config_cache.all_active_realhosts()))

    def snmp_config(self, ipaddress: Optional[HostAddress]) -> SNMPHostConfig:
        return SNMPHostConfig(
            is_ipv6_primary=self.is_ipv6_primary,
            hostname=self.hostname,
            ipaddress=ipaddress,
            credentials=self._snmp_credentials(),
            port=self._snmp_port(),
            is_bulkwalk_host=self._config_cache.in_binary_hostlist(self.hostname, bulkwalk_hosts),
            is_snmpv2or3_without_bulkwalk_host=self._config_cache.in_binary_hostlist(
                self.hostname, snmpv2c_hosts),
            bulk_walk_size_of=self._bulk_walk_size(),
            timing=self._snmp_timing(),
            oid_range_limits=self._config_cache.host_extra_conf(self.hostname,
                                                                snmp_limit_oid_range),
            snmpv3_contexts=self._config_cache.host_extra_conf(self.hostname, snmpv3_contexts),
            character_encoding=self._snmp_character_encoding(),
            is_usewalk_host=self.is_usewalk_host,
            snmp_backend=self._get_snmp_backend(),
        )

    def _snmp_credentials(self) -> SNMPCredentials:
        """Determine SNMP credentials for a specific host

        It the host is found int the map snmp_communities, that community is
        returned. Otherwise the snmp_default_community is returned (wich is
        preset with "public", but can be overridden in main.mk.
        """
        try:
            return explicit_snmp_communities[self.hostname]
        except KeyError:
            pass

        communities = self._config_cache.host_extra_conf(self.hostname, snmp_communities)
        if communities:
            return communities[0]

        # nothing configured for this host -> use default
        return snmp_default_community

    def snmp_credentials_of_version(self, snmp_version: int) -> Optional[SNMPCredentials]:
        for entry in self._config_cache.host_extra_conf(self.hostname, snmp_communities):
            if snmp_version == 3 and not isinstance(entry, tuple):
                continue

            if snmp_version != 3 and isinstance(entry, tuple):
                continue

            return entry

        return None

    def _snmp_port(self) -> int:
        ports = self._config_cache.host_extra_conf(self.hostname, snmp_ports)
        if not ports:
            return 161
        return ports[0]

    def _snmp_timing(self) -> SNMPTiming:
        timing = self._config_cache.host_extra_conf(self.hostname, snmp_timing)
        if not timing:
            return {}
        return timing[0]

    def _bulk_walk_size(self) -> int:
        bulk_sizes = self._config_cache.host_extra_conf(self.hostname, snmp_bulk_size)
        if not bulk_sizes:
            return 10
        return bulk_sizes[0]

    def _snmp_character_encoding(self) -> Optional[str]:
        entries = self._config_cache.host_extra_conf(self.hostname, snmp_character_encodings)
        if not entries:
            return None
        return entries[0]

    def _is_host_snmp_v1(self) -> bool:
        """Determines is host snmp-v1 using a bit Heuristic algorithm"""
        if isinstance(self._snmp_credentials(), tuple):
            return False  # v3

        if self._config_cache.in_binary_hostlist(self.hostname, bulkwalk_hosts):
            return False

        return not self._config_cache.in_binary_hostlist(self.hostname, snmpv2c_hosts)

    def _is_inline_backend_supported(self) -> bool:
        return "netsnmp" in sys.modules and not cmk_version.is_raw_edition()

    def _is_pysnmp_backend_supported(self) -> bool:
        return "pysnmp" in sys.modules and not cmk_version.is_raw_edition()

    def _get_snmp_backend(self) -> SNMPBackend:
        with_inline_snmp = self._is_inline_backend_supported()
        with_pysnmp = self._is_pysnmp_backend_supported()

        host_backend_config = self._config_cache.host_extra_conf(self.hostname, snmp_backend_hosts)

        if host_backend_config:
            # If more backends are configured for this host take the first one
            host_backend = host_backend_config[0]
            if with_pysnmp and host_backend == "pysnmp":
                return SNMPBackend.pysnmp
            if with_inline_snmp and host_backend == "inline":
                return SNMPBackend.inline
            if host_backend == "classic":
                return SNMPBackend.classic
            raise MKGeneralException("Bad Host SNMP Backend configuration: %s" % host_backend)

        # TODO(sk): remove this when netsnmp is fixed
        # NOTE: Force usage of CLASSIC with SNMP-v1 to prevent memory leak in the netsnmp
        if self._is_host_snmp_v1():
            return SNMPBackend.classic

        if with_pysnmp and snmp_backend_default == "pysnmp":
            return SNMPBackend.pysnmp
        if with_inline_snmp and snmp_backend_default == "inline":
            return SNMPBackend.inline
        return SNMPBackend.classic

    def _is_cluster(self) -> bool:
        """Checks whether or not the given host is a cluster host
        all_configured_clusters() needs to be used, because this function affects
        the agent bakery, which needs all configured hosts instead of just the hosts
        of this site"""
        return self.hostname in self._config_cache.all_configured_clusters()

    def snmp_fetch_interval(self, section_name: SectionName) -> Optional[int]:
        """Return the fetch interval of SNMP sections

        This has been added to reduce the fetch interval of single SNMP sections
        to be executed less frequently than the "Check_MK" service is executed.
        """
        section = agent_based_register.get_section_plugin(section_name)
        if not isinstance(section, SNMPSectionPlugin):
            return None  # no values at all for non snmp section

        # Previous to 1.5 "match" could be a check name (including subchecks) instead of
        # only main check names -> section names. This has been cleaned up, but we still
        # need to be compatible. Strip of the sub check part of "match".
        for match, minutes in self._config_cache.host_extra_conf(
                self.hostname,
                snmp_check_interval,
        ):
            if match is None or match.split(".")[0] == str(section_name):
                return minutes  # use first match

        return None

    def disabled_snmp_sections(self) -> Set[SectionName]:
        """Return a set of disabled snmp sections
        """
        rules = self._config_cache.host_extra_conf(self.hostname, snmp_exclude_sections)
        merged_section_settings = {'if64adm': True}
        for rule in reversed(rules):
            for section in rule.get("sections_enabled", ()):
                merged_section_settings[section] = False
            for section in rule.get("sections_disabled", ()):
                merged_section_settings[section] = True

        return {
            SectionName(name)
            for name, is_disabled in merged_section_settings.items()
            if is_disabled
        }

    @property
    def agent_port(self) -> int:
        ports = self._config_cache.host_extra_conf(self.hostname, agent_ports)
        if not ports:
            return agent_port

        return ports[0]

    @property
    def tcp_connect_timeout(self) -> float:
        timeouts = self._config_cache.host_extra_conf(self.hostname, tcp_connect_timeouts)
        if not timeouts:
            return tcp_connect_timeout

        return timeouts[0]

    @property
    def agent_encryption(self) -> Dict[str, str]:
        settings = self._config_cache.host_extra_conf(self.hostname, agent_encryption)
        if not settings:
            return {'use_regular': 'disable', 'use_realtime': 'enforce'}
        return settings[0]

    @property
    def agent_description(self) -> str:
        if self.is_all_agents_host:
            return "Normal Checkmk agent, all configured special agents"

        if self.is_all_special_agents_host:
            return "No Checkmk agent, all configured special agents"

        if self.is_tcp_host:
            return "Normal Checkmk agent, or special agent if configured"

        return "No agent"

    @property
    def agent_exclude_sections(self) -> Dict[str, str]:
        settings = self._config_cache.host_extra_conf(self.hostname, agent_exclude_sections)
        if not settings:
            return {}
        return settings[0]

    @property
    def agent_target_version(self) -> AgentTargetVersion:
        agent_target_versions = self._config_cache.host_extra_conf(self.hostname,
                                                                   check_mk_agent_target_versions)
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
        if spec[0] == 'specific':
            return spec[1]

        return spec  # return the whole spec in case of an "at least version" config

    @property
    def datasource_program(self) -> Optional[str]:
        """Return the command line to execute instead of contacting the agent

        In case no datasource program is configured for a host return None
        """
        programs = self._config_cache.host_extra_conf(self.hostname, datasource_programs)
        if not programs:
            return None

        return programs[0]

    @property
    def special_agents(self) -> List[Tuple[str, Dict]]:
        matched: List[Tuple[str, Dict]] = []
        # Previous to 1.5.0 it was not defined in which order the special agent
        # rules overwrite each other. When multiple special agents were configured
        # for a single host a "random" one was picked (depending on the iteration
        # over config.special_agents.
        # We now sort the matching special agents by their name to at least get
        # a deterministic order of the special agents.
        for agentname, ruleset in sorted(special_agents.items()):
            params = self._config_cache.host_extra_conf(self.hostname, ruleset)
            if params:
                matched.append((agentname, params[0]))
        return matched

    @property
    def only_from(self) -> Union[None, List[str], str]:
        """The agent of a host may be configured to be accessible only from specific IPs"""
        ruleset = agent_config.get("only_from", [])
        if not ruleset:
            return None

        entries = self._config_cache.host_extra_conf(self.hostname, ruleset)
        if not entries:
            return None

        return entries[0]

    @property
    def explicit_check_command(self) -> HostCheckCommand:
        entries = self._config_cache.host_extra_conf(self.hostname, host_check_commands)
        if not entries:
            return None

        if entries[0] == "smart" and monitoring_core != "cmc":
            return "ping"  # avoid problems when switching back to nagios core

        return entries[0]

    @property
    def ping_levels(self) -> PingLevels:
        levels: PingLevels = {}

        values = self._config_cache.host_extra_conf(self.hostname, ping_levels)
        # TODO: Use host_extra_conf_merged?)
        for value in values[::-1]:  # make first rules have precedence
            levels.update(value)

        return levels

    @property
    def icons_and_actions(self) -> List[str]:
        return list(set(self._config_cache.host_extra_conf(self.hostname, host_icons_and_actions)))

    @property
    def extra_host_attributes(self) -> ObjectAttributes:
        attrs: ObjectAttributes = {}
        attrs.update(self._explicit_host_attributes)

        for key, ruleset in extra_host_conf.items():
            if key in attrs:
                # An explicit value is already set
                values = [attrs[key]]
            else:
                values = self._config_cache.host_extra_conf(self.hostname, ruleset)
                if not values:
                    continue

            if values[0] is not None:
                attrs[key] = values[0]

        # Convert _keys to uppercase. Affects explicit and rule based keys
        attrs = {key.upper() if key[0] == "_" else key: value for key, value in attrs.items()}
        return attrs

    @property
    def _explicit_host_attributes(self) -> ObjectAttributes:
        if self._explicit_attributes_lookup is not None:
            return self._explicit_attributes_lookup

        hostname = self.hostname
        cache = {}
        for key, hostnames in explicit_host_conf.items():
            if hostname in hostnames:
                cache[key] = hostnames[hostname]
        self._explicit_attributes_lookup = cache
        return self._explicit_attributes_lookup

    @property
    def discovery_check_parameters(self) -> Optional[DiscoveryCheckParameters]:
        """Compute the parameters for the discovery check for a host

        Note:
        - If a rule is configured to disable the check, this function returns None.
        - If there is no rule configured, a value is constructed from the legacy global
          settings and will be returned. In this structure a "check_interval" of None
          means the check should not be added.
        """
        entries = self._config_cache.host_extra_conf(self.hostname, periodic_discovery)
        if not entries:
            return self.default_discovery_check_parameters()

        return entries[0]

    def default_discovery_check_parameters(self) -> DiscoveryCheckParameters:
        """Support legacy single value global configurations. Otherwise return the defaults"""
        return {
            "check_interval": inventory_check_interval,
            "severity_unmonitored": inventory_check_severity,
            "severity_vanished": 0,
        }

    def add_service_discovery_check(self, params: Optional[Dict[str, Any]],
                                    service_discovery_name: str) -> bool:
        if not params:
            return False

        if not params["check_interval"]:
            return False

        if service_ignored(self.hostname, None, service_discovery_name):
            return False

        if self.is_ping_host:
            return False

        return True

    def inventory_parameters(self, section_name: str) -> Dict:
        return self._config_cache.host_extra_conf_merged(self.hostname,
                                                         inv_parameters.get(section_name, []))

    @property
    def inventory_export_hooks(self) -> List[Tuple[str, Dict]]:
        hooks: List[Tuple[str, Dict]] = []
        for hookname, ruleset in sorted(inv_exports.items(), key=lambda x: x[0]):
            entries = self._config_cache.host_extra_conf(self.hostname, ruleset)
            if entries:
                hooks.append((hookname, entries[0]))
        return hooks

    def notification_plugin_parameters(self, plugin_name: CheckPluginNameStr) -> Dict:
        return self._config_cache.host_extra_conf_merged(
            self.hostname, notification_parameters.get(plugin_name, []))

    @property
    def active_checks(self) -> List[Tuple[str, List[Any]]]:
        """Returns the list of active checks configured for this host

        These are configured using the active check formalization of WATO
        where the whole parameter set is configured using valuespecs.
        """
        configured_checks: List[Tuple[str, List[Any]]] = []
        for plugin_name, ruleset in sorted(active_checks.items(), key=lambda x: x[0]):
            # Skip Check_MK HW/SW Inventory for all ping hosts, even when the
            # user has enabled the inventory for ping only hosts
            if plugin_name == "cmk_inv" and self.is_ping_host:
                continue

            entries = self._config_cache.host_extra_conf(self.hostname, ruleset)
            if not entries:
                continue

            configured_checks.append((plugin_name, entries))

        return configured_checks

    @property
    def custom_checks(self) -> List[Dict]:
        """Return the free form configured custom checks without formalization"""
        return self._config_cache.host_extra_conf(self.hostname, custom_checks)

    @property
    def static_checks(
            self) -> List[Tuple[RulesetName, CheckPluginNameStr, Item, LegacyCheckParameters]]:
        """Returns a table of all "manual checks" configured for this host"""
        matched = []
        for checkgroup_name in static_checks:
            for entry in self._config_cache.host_extra_conf(self.hostname,
                                                            static_checks.get(checkgroup_name, [])):
                if len(entry) == 2:
                    checktype, item = entry
                    params = None
                else:
                    checktype, item, params = entry

                matched.append((checkgroup_name, checktype, item, params))

        return matched

    @property
    def hostgroups(self) -> List[HostgroupName]:
        """Returns the list of hostgroups of this host

        If the host has no hostgroups it will be added to the default hostgroup
        (Nagios requires each host to be member of at least on group)."""
        groups = self._config_cache.host_extra_conf(self.hostname, host_groups)
        if not groups:
            return [default_host_group]
        return groups

    @property
    def contactgroups(self) -> List[ContactgroupName]:
        """Returns the list of contactgroups of this host"""
        cgrs: List[ContactgroupName] = []

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
        for entry in self._config_cache.host_extra_conf(self.hostname, host_contactgroups):
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

    @property
    def management_address(self) -> Optional[HostAddress]:
        mgmt_ip_address = host_attributes.get(self.hostname, {}).get("management_address")
        if mgmt_ip_address:
            return mgmt_ip_address

        if self.is_ipv6_primary:
            return ipv6addresses.get(self.hostname)

        return ipaddresses.get(self.hostname)

    @property
    def management_credentials(self) -> Optional[ManagementCredentials]:
        protocol = self.management_protocol
        default_value: Optional[ManagementCredentials] = None
        if protocol == "snmp":
            credentials_variable, default_value = management_snmp_credentials, snmp_default_community
        elif protocol == "ipmi":
            credentials_variable, default_value = management_ipmi_credentials, None
        elif protocol is None:
            return None
        else:
            raise NotImplementedError()

        # First try to use the explicit configuration of the host
        # (set directly for a host or via folder inheritance in WATO)
        try:
            return credentials_variable[self.hostname]
        except KeyError:
            pass

        # If a rule matches, use the first rule for the management board protocol of the host
        rule_settings = self._config_cache.host_extra_conf(self.hostname, management_board_config)
        for rule_protocol, credentials in rule_settings:
            if rule_protocol == protocol:
                return credentials

        return default_value

    @property
    def management_snmp_config(self) -> SNMPHostConfig:
        if self.management_protocol != "snmp":
            raise MKGeneralException("Management board is not configured to be contacted via SNMP")

        address = self.management_address
        if address is None:
            raise MKGeneralException("Management board address is not configured")

        return SNMPHostConfig(
            is_ipv6_primary=self.is_ipv6_primary,
            hostname=self.hostname,
            ipaddress=address,
            credentials=cast(SNMPCredentials, self.management_credentials),
            port=self._snmp_port(),
            is_bulkwalk_host=self._config_cache.in_binary_hostlist(self.hostname,
                                                                   management_bulkwalk_hosts),
            is_snmpv2or3_without_bulkwalk_host=self._config_cache.in_binary_hostlist(
                self.hostname, snmpv2c_hosts),
            bulk_walk_size_of=self._bulk_walk_size(),
            timing=self._snmp_timing(),
            oid_range_limits=self._config_cache.host_extra_conf(self.hostname,
                                                                snmp_limit_oid_range),
            snmpv3_contexts=self._config_cache.host_extra_conf(self.hostname, snmpv3_contexts),
            character_encoding=self._snmp_character_encoding(),
            is_usewalk_host=self.is_usewalk_host,
            snmp_backend=self._get_snmp_backend(),
        )

    @property
    def additional_ipaddresses(self) -> Tuple[List[HostAddress], List[HostAddress]]:
        #TODO Regarding the following configuration variables from WATO
        # there's no inheritance, thus we use 'host_attributes'.
        # Better would be to use cmk.base configuration variables,
        # eg. like 'management_protocol'.
        return (host_attributes.get(self.hostname, {}).get("additional_ipv4addresses", []),
                host_attributes.get(self.hostname, {}).get("additional_ipv6addresses", []))

    def exit_code_spec(self, data_source_id: Optional[str] = None) -> ExitSpec:
        spec: _NestedExitSpec = {}
        # TODO: Can we use host_extra_conf_merged?
        specs = self._config_cache.host_extra_conf(self.hostname, check_mk_exit_status)
        for entry in specs[::-1]:
            spec.update(entry)

        merged_spec = self._extract_data_source_exit_code_spec(spec, data_source_id)
        return self._merge_with_optional_exit_code_parameters(spec, merged_spec)

    def _extract_data_source_exit_code_spec(
        self,
        spec: _NestedExitSpec,
        data_source_id: Optional[str],
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

    def _merge_with_optional_exit_code_parameters(
        self,
        spec: _NestedExitSpec,
        merged_spec: ExitSpec,
    ) -> ExitSpec:
        # Additional optional parameters which are not part of individual
        # or overall parameters
        value = spec.get('restricted_address_mismatch')
        if value is not None:
            merged_spec['restricted_address_mismatch'] = value
        return merged_spec

    @property
    def do_status_data_inventory(self) -> bool:
        if self.is_cluster:
            return False

        # TODO: Use dict(self.active_checks).get("cmk_inv", [])?
        rules = active_checks.get('cmk_inv')
        if rules is None:
            return False

        # 'host_extra_conf' is already cached thus we can
        # use it after every check cycle.
        entries = self._config_cache.host_extra_conf(self.hostname, rules)

        if not entries:
            return False  # No matching rule -> disable

        # Convert legacy rules to current dict format (just like the valuespec)
        params = {} if entries[0] is None else entries[0]

        return params.get('status_data_inventory', False)

    @property
    def service_level(self) -> Optional[int]:
        entries = self._config_cache.host_extra_conf(self.hostname, host_service_levels)
        if not entries:
            return None
        return entries[0]

    def set_autochecks(
        self,
        new_services: Sequence[ServiceWithNodes],
    ) -> None:
        """Merge existing autochecks with the given autochecks for a host and save it"""
        if self.is_cluster:
            if self.nodes:
                autochecks.set_autochecks_of_cluster(
                    self.nodes,
                    self.hostname,
                    new_services,
                    self._config_cache.host_of_clustered_service,
                    service_description,  # top level function!
                )
        else:
            autochecks.set_autochecks_of_real_hosts(
                self.hostname,
                new_services,
                service_description,  # top level function!
            )

    def remove_autochecks(self) -> int:
        """Remove all autochecks of a host while being cluster-aware

        Cluster aware means that the autocheck files of the nodes are handled. Instead
        of removing the whole file the file is loaded and only the services associated
        with the given cluster are removed."""
        hostnames = self.nodes if self.nodes else [self.hostname]
        return sum(
            autochecks.remove_autochecks_of_host(
                hostname,
                self.hostname,
                self._config_cache.host_of_clustered_service,
                service_description,
            ) for hostname in hostnames)

    @property
    def max_cachefile_age(self) -> MaxAge:
        return max_cachefile_age(
            checking=check_max_cachefile_age if self.nodes is None else cluster_max_cachefile_age)

    @property
    def is_dyndns_host(self) -> bool:
        return self._config_cache.in_binary_hostlist(self.hostname, dyndns_hosts)


#.
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


# TODO: Shouldn't we find a better place for the *_of_service() methods?
# Wouldn't it be better to make them part of HostConfig?
class ConfigCache:
    def __init__(self) -> None:
        super(ConfigCache, self).__init__()
        self._initialize_caches()

    def initialize(self) -> None:
        self._initialize_caches()
        self._setup_clusters_nodes_cache()

        self._all_configured_clusters = self._get_all_configured_clusters()
        self._all_configured_realhosts = self._get_all_configured_realhosts()
        self._all_configured_hosts = self._get_all_configured_hosts()

        tag_to_group_map = self.get_tag_to_group_map()
        self._collect_hosttags(tag_to_group_map)

        self.labels = LabelManager(host_labels, host_label_rules, service_label_rules,
                                   self._discovered_labels_of_service)

        self.ruleset_matcher = ruleset_matcher.RulesetMatcher(
            tag_to_group_map=tag_to_group_map,
            host_tags=host_tags,
            host_paths=self._host_paths,
            labels=self.labels,
            clusters_of=self._clusters_of_cache,
            nodes_of=self._nodes_of_cache,
            all_configured_hosts=self._all_configured_hosts,
        )

        # Warning: do not change call order. all_active_hosts relies on the other values
        self._all_active_clusters = self._get_all_active_clusters()
        self._all_active_realhosts = self._get_all_active_realhosts()
        self._all_active_hosts = self._get_all_active_hosts()

        self.ruleset_matcher.ruleset_optimizer.set_all_processed_hosts(self._all_active_hosts)

    def _initialize_caches(self) -> None:
        self.check_table_cache = _config_cache.get_dict("check_tables")

        self._cache_section_name_of: Dict[CheckPluginNameStr, str] = {}

        self._cache_match_object_service: Dict[Tuple[HostName, ServiceName],
                                               RulesetMatchObject] = {}
        self._cache_match_object_service_checkgroup: Dict[Tuple[HostName, Item, ServiceName],
                                                          RulesetMatchObject] = {}
        self._cache_match_object_host: Dict[HostName, RulesetMatchObject] = {}

        # Host lookup

        self._all_configured_hosts = set()
        self._all_configured_clusters = set()
        self._all_configured_realhosts = set()
        self._all_active_clusters = set()
        self._all_active_realhosts = set()

        # Reference hostname -> dirname including /
        self._host_paths: Dict[HostName, str] = self._get_host_paths(host_paths)

        # Host tags
        self._hosttags: Dict[HostName, TagIDs] = {}

        # Autochecks cache
        self._autochecks_manager = autochecks.AutochecksManager()

        # Caches for nodes and clusters
        self._clusters_of_cache: Dict[HostName, List[HostName]] = {}
        self._nodes_of_cache: Dict[HostName, List[HostName]] = {}

        # Keep HostConfig instances created with the current configuration cache
        self._host_configs: Dict[HostName, HostConfig] = {}

    def _discovered_labels_of_service(
        self,
        hostname: HostName,
        service_desc: ServiceName,
    ) -> Labels:
        return self._autochecks_manager.discovered_labels_of(
            hostname,
            service_desc,
            service_description,  # this is the global function!
        ).to_dict()

    def get_tag_to_group_map(self) -> TagIDToTaggroupID:
        tags = cmk.utils.tags.get_effective_tag_config(tag_config)
        return ruleset_matcher.get_tag_to_group_map(tags)

    def get_host_config(self, hostname: HostName) -> HostConfig:
        """Returns a HostConfig instance for the given host

        It lazy initializes the host config object and caches the objects during the livetime
        of the ConfigCache."""
        host_config = self._host_configs.get(hostname)
        if host_config:
            return host_config

        config_class = HostConfig if cmk_version.is_raw_edition() else CEEHostConfig
        host_config = self._host_configs[hostname] = config_class(self, hostname)
        return host_config

    def invalidate_host_config(self, hostname: HostName) -> None:
        try:
            del self._host_configs[hostname]
        except KeyError:
            pass

    def _get_host_paths(self, config_host_paths: Dict[HostName, str]) -> Dict[HostName, str]:
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
                self._hosttags[hostname] = self._tag_groups_to_tag_list(
                    self._host_paths.get(hostname, "/"), host_tags[hostname])
            else:
                # Only tag list available. Use it and compute the tag groups.
                self._hosttags[hostname] = set(parts[1:])
                host_tags[hostname] = self._tag_list_to_tag_groups(tag_to_group_map,
                                                                   self._hosttags[hostname])

        for shadow_host_name, shadow_host_spec in list(_get_shadow_hosts().items()):
            self._hosttags[shadow_host_name] = set(
                shadow_host_spec.get("custom_variables", {}).get("TAGS", "").split())
            host_tags[shadow_host_name] = self._tag_list_to_tag_groups(
                tag_to_group_map, self._hosttags[shadow_host_name])

    def _tag_groups_to_tag_list(
        self,
        host_path: str,
        tag_groups: TaggroupIDToTagID,
    ) -> TagIDs:
        # The pre 1.6 tags contained only the tag group values (-> chosen tag id),
        # but there was a single tag group added with it's leading tag group id. This
        # was the internal "site" tag that is created by HostAttributeSite.
        tags = set(v for k, v in tag_groups.items() if k != "site")
        tags.add(host_path)
        tags.add("site:%s" % tag_groups["site"])
        return tags

    def _tag_list_to_tag_groups(
        self,
        tag_to_group_map: TagIDToTaggroupID,
        tag_list: TagIDs,
    ) -> TaggroupIDToTagID:
        # This assumes all needed aux tags of grouped are already in the tag_list

        # Ensure the internal mandatory tag groups are set for all hosts
        # TODO: This immitates the logic of cmk.gui.watolib.CREHost.tag_groups which
        # is currently responsible for calculating the host tags of a host.
        # Would be better to untie the GUI code there and move it over to cmk.utils.tags.
        return {
            'piggyback': 'auto-piggyback',
            'networking': 'lan',
            'agent': 'cmk-agent',
            'criticality': 'prod',
            'snmp_ds': 'no-snmp',
            'site': cmk_version.omd_site(),
            'address_family': 'ip-v4-only',
            # Assume it's an aux tag in case there is a tag configured without known group
            **{tag_to_group_map.get(tag_id, tag_id): tag_id for tag_id in tag_list},
        }

    # Kept for compatibility with pre 1.6 sites
    # TODO: Clean up all call sites one day (1.7?)
    # TODO: check all call sites and remove this
    def tag_list_of_host(self, hostname: HostName) -> TagIDs:
        """Returns the list of all configured tags of a host. In case
        a host has no tags configured or is not known, it returns an
        empty list."""
        if hostname in self._hosttags:
            return self._hosttags[hostname]

        # Handle not existing hosts (No need to performance optimize this)
        return self._tag_groups_to_tag_list("/", self.tags_of_host(hostname))

    # TODO: check all call sites and remove this or make it private?
    def tags_of_host(self, hostname: HostName) -> TaggroupIDToTagID:
        """Returns the dict of all configured tag groups and values of a host

        In case you have a HostConfig object available better use HostConfig.tag_groups"""
        if hostname in host_tags:
            return host_tags[hostname]

        # Handle not existing hosts (No need to performance optimize this)
        # TODO: This immitates the logic of cmk.gui.watolib.CREHost.tag_groups which
        # is currently responsible for calculating the host tags of a host.
        # Would be better to untie the GUI code there and move it over to cmk.utils.tags.
        return {
            'piggyback': 'auto-piggyback',
            'networking': 'lan',
            'agent': 'cmk-agent',
            'criticality': 'prod',
            'snmp_ds': 'no-snmp',
            'site': cmk_version.omd_site(),
            'address_family': 'ip-v4-only',
        }

    def tags_of_service(self, hostname: HostName, svc_desc: ServiceName) -> TaggroupIDToTagID:
        """Returns the dict of all configured tags of a service
        It takes all explicitly configured tag groups into account.
        """
        return {
            k: v for entry in self.service_extra_conf(hostname, svc_desc, service_tag_rules)
            for k, v in entry
        }

    def labels_of_service(self, hostname: HostName, svc_desc: ServiceName) -> Labels:
        """Returns the effective set of service labels from all available sources

        1. Discovered labels
        2. Ruleset "Service labels"

        Last one wins.
        """
        return self.labels.labels_of_service(self.ruleset_matcher, hostname, svc_desc)

    def label_sources_of_service(self, hostname: HostName, svc_desc: ServiceName) -> LabelSources:
        """Returns the effective set of service label keys with their source identifier instead of the value
        Order and merging logic is equal to labels_of_service()"""
        return self.labels.label_sources_of_service(self.ruleset_matcher, hostname, svc_desc)

    def extra_attributes_of_service(self, hostname: HostName,
                                    description: ServiceName) -> Dict[str, Any]:
        attrs = {
            "check_interval": 1.0,  # 1 minute
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
        check_plugin_name: Optional[CheckPluginName],
        params: LegacyCheckParameters,
    ) -> List[str]:
        actions = set(self.service_extra_conf(hostname, description, service_icons_and_actions))

        # Some WATO rules might register icons on their own
        if check_plugin_name:
            plugin = agent_based_register.get_check_plugin(check_plugin_name)
            if (plugin is not None and str(plugin.check_ruleset_name) in ('ps', 'services') and
                    isinstance(params, dict)):
                icon = params.get('icon')
                if icon:
                    actions.add(icon)

        return list(actions)

    def servicegroups_of_service(self, hostname: HostName,
                                 description: ServiceName) -> List[ServicegroupName]:
        """Returns the list of servicegroups of this services"""
        return self.service_extra_conf(hostname, description, service_groups)

    def contactgroups_of_service(self, hostname: HostName, description: ServiceName) -> List[str]:
        """Returns the list of contactgroups of this service"""
        cgrs: Set[str] = set()

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
        folder_cgrs: List[List[str]] = []
        for entry in self.service_extra_conf(hostname, description, service_contactgroups):
            if isinstance(entry, list):
                folder_cgrs.append(entry)
            else:
                cgrs.add(entry)

        # Use the match of the nearest folder, which is the first entry in the list
        if folder_cgrs:
            cgrs.update(folder_cgrs[0])

        if monitoring_core == "nagios" and enable_rulebased_notifications:
            cgrs.add("check-mk-notify")

        return list(cgrs)

    def passive_check_period_of_service(self, hostname: HostName, description: ServiceName) -> str:
        return self.get_service_ruleset_value(hostname, description, check_periods, deflt="24X7")

    def custom_attributes_of_service(self, hostname: HostName,
                                     description: ServiceName) -> Dict[str, str]:
        return dict(
            itertools.chain(
                *self.service_extra_conf(hostname, description, custom_service_attributes)))

    def service_level_of_service(self, hostname: HostName,
                                 description: ServiceName) -> Optional[int]:
        return self.get_service_ruleset_value(
            hostname,
            description,
            service_service_levels,
            deflt=None,
        )

    def check_period_of_service(self, hostname: HostName,
                                description: ServiceName) -> Optional[TimeperiodName]:
        entry = self.get_service_ruleset_value(hostname, description, check_periods, deflt=None)
        if entry == "24X7":
            return None
        return entry

    def get_explicit_service_custom_variables(self, hostname: HostName,
                                              description: ServiceName) -> Dict[str, str]:
        try:
            return explicit_service_custom_variables[(hostname, description)]
        except KeyError:
            return {}

    def ruleset_match_object_of_service(self, hostname: HostName,
                                        svc_desc: ServiceName) -> RulesetMatchObject:
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

        result = RulesetMatchObject(
            host_name=hostname,
            service_description=svc_desc,
            service_labels=self.labels.labels_of_service(self.ruleset_matcher, hostname, svc_desc),
        )
        self._cache_match_object_service[cache_id] = result
        return result

    def ruleset_match_object_for_checkgroup_parameters(self, hostname: HostName, item: Item,
                                                       svc_desc: ServiceName) -> RulesetMatchObject:
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
            service_labels=self.labels.labels_of_service(self.ruleset_matcher, hostname, svc_desc),
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

    def get_autochecks_of(self, hostname: HostName) -> List[cmk.base.check_utils.Service]:
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

    def host_extra_conf_merged(self, hostname: HostName, ruleset: Ruleset) -> Dict[str, Any]:
        return self.ruleset_matcher.get_host_ruleset_merged_dict(
            self.ruleset_match_object_of_host(hostname),
            ruleset,
        )

    def host_extra_conf(self, hostname: HostName, ruleset: Ruleset) -> List:
        return list(
            self.ruleset_matcher.get_host_ruleset_values(
                self.ruleset_match_object_of_host(hostname),
                ruleset,
                is_binary=False,
            ))

    # TODO: Cleanup external in_binary_hostlist call sites
    def in_binary_hostlist(self, hostname: HostName, ruleset: Ruleset) -> bool:
        return self.ruleset_matcher.is_matching_host_ruleset(
            self.ruleset_match_object_of_host(hostname), ruleset)

    def service_extra_conf(self, hostname: HostName, description: ServiceName,
                           ruleset: Ruleset) -> List:
        """Compute outcome of a service rule set that has an item."""
        return list(
            self.ruleset_matcher.get_service_ruleset_values(
                self.ruleset_match_object_of_service(hostname, description),
                ruleset,
                is_binary=False,
            ))

    def get_service_ruleset_value(self, hostname: HostName, description: ServiceName,
                                  ruleset: Ruleset, deflt: Any) -> Any:
        """Compute first match service ruleset outcome with fallback to a default value"""
        return next(
            self.ruleset_matcher.get_service_ruleset_values(
                self.ruleset_match_object_of_service(hostname, description),
                ruleset,
                is_binary=False,
            ), deflt)

    def service_extra_conf_merged(self, hostname: HostName, description: ServiceName,
                                  ruleset: Ruleset) -> Dict[str, Any]:
        return self.ruleset_matcher.get_service_ruleset_merged_dict(
            self.ruleset_match_object_of_service(hostname, description), ruleset)

    def in_boolean_serviceconf_list(self, hostname: HostName, description: ServiceName,
                                    ruleset: Ruleset) -> bool:
        """Compute outcome of a service rule set that just say yes/no"""
        return self.ruleset_matcher.is_matching_service_ruleset(
            self.ruleset_match_object_of_service(hostname, description), ruleset)

    def all_active_hosts(self) -> Set[HostName]:
        """Returns a set of all active hosts"""
        return self._all_active_hosts

    def _get_all_active_hosts(self) -> Set[HostName]:
        hosts: Set[HostName] = set()
        hosts.update(self.all_active_realhosts(), self.all_active_clusters())
        return hosts

    def all_active_realhosts(self) -> Set[HostName]:
        """Returns a set of all host names to be handled by this site hosts of other sites or disabled hosts are excluded"""
        return self._all_active_realhosts

    def _get_all_active_realhosts(self) -> Set[HostName]:
        return set(_filter_active_hosts(self, self._all_configured_realhosts))

    def all_configured_realhosts(self) -> Set[HostName]:
        return self._all_configured_realhosts

    def _get_all_configured_realhosts(self) -> Set[HostName]:
        """Returns a set of all host names, regardless if currently disabled or
        monitored on a remote site. Does not return cluster hosts."""
        return set(strip_tags(all_hosts))

    def _get_all_configured_shadow_hosts(self) -> Set[HostName]:
        """Returns a set of all shadow host names, regardless if currently disabled or
        monitored on a remote site"""
        return set(_get_shadow_hosts())

    def all_configured_hosts(self) -> Set[HostName]:
        return self._all_configured_hosts

    def _get_all_configured_hosts(self) -> Set[HostName]:
        """Returns a set of all hosts, regardless if currently disabled or monitored on a remote site."""
        hosts: Set[HostName] = set()
        hosts.update(
            self.all_configured_realhosts(),
            self.all_configured_clusters(),
            self._get_all_configured_shadow_hosts(),
        )
        return hosts

    def _setup_clusters_nodes_cache(self) -> None:
        for cluster, hosts in clusters.items():
            clustername = cluster.split('|', 1)[0]
            for name in hosts:
                self._clusters_of_cache.setdefault(name, []).append(clustername)
            self._nodes_of_cache[clustername] = hosts

    def clusters_of(self, hostname: str) -> List[HostName]:
        """Returns names of cluster hosts the host is a node of"""
        return self._clusters_of_cache.get(hostname, [])

    # TODO: cleanup None case
    def nodes_of(self, hostname: str) -> Optional[List[HostName]]:
        """Returns the nodes of a cluster. Returns None if no match.

        Use host_config.nodes instead of this method to get the node list"""
        return self._nodes_of_cache.get(hostname)

    def all_active_clusters(self) -> Set[HostName]:
        """Returns a set of all cluster host names to be handled by this site hosts of other sites or disabled hosts are excluded"""
        return self._all_active_clusters

    def _get_all_active_clusters(self) -> Set[HostName]:
        return set(_filter_active_hosts(self, self.all_configured_clusters()))

    def all_configured_clusters(self) -> Set[HostName]:
        """Returns a set of all cluster names
        Regardless if currently disabled or monitored on a remote site. Does not return normal hosts.
        """
        return self._all_configured_clusters

    def _get_all_configured_clusters(self) -> Set[HostName]:
        return set(strip_tags(list(clusters)))

    def host_of_clustered_service(self,
                                  hostname: HostName,
                                  servicedesc: str,
                                  part_of_clusters: Optional[List[str]] = None) -> str:
        """Return hostname to assign the service to
        Determine weather a service (found on a physical host) is a clustered
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
                    "Invalid entry clustered_services_of['%s']: %s is not a cluster." %
                    (cluster, cluster))
            if hostname in nodes and self.in_boolean_serviceconf_list(hostname, servicedesc, conf):
                return cluster

        # 1. Old style: clustered_services assumes that each host belong to
        #    exactly on cluster
        if self.in_boolean_serviceconf_list(hostname, servicedesc, clustered_services):
            return the_clusters[0]

        return hostname

    def get_clustered_service_node_keys(
        self,
        hostname: HostName,
        source_type: SourceType,
        service_descr: Optional[ServiceName],
        lookup_ip_address: Callable[[HostConfig], Optional[HostAddress]],
    ) -> Optional[List[HostKey]]:
        """Returns the node keys if a service is clustered, otherwise 'None' in order to
        decide whether we collect section content of the host or the nodes.

        For real hosts or nodes for which the service is not clustered we return 'None',
        thus the caching works as before.

        If a service is assigned to a cluster we receive the real nodename. In this
        case we have to sort out data from the nodes for which the same named service
        is not clustered (Clustered service for overlapping clusters).

        We also use the result for the section cache.
        """
        if not service_descr:
            return None

        nodes = self.get_host_config(hostname).nodes
        if nodes is None:
            return None

        return [
            HostKey(
                nodename,
                lookup_ip_address(self.get_host_config(nodename)),
                source_type,
            )
            for nodename in nodes
            if hostname == self.host_of_clustered_service(nodename, service_descr)
        ]

    def get_piggybacked_hosts_time_settings(
            self,
            piggybacked_hostname: Optional[HostName] = None
    ) -> List[Tuple[Optional[str], str, int]]:
        time_settings: List[Tuple[Optional[str], str, int]] = []
        for source_hostname in sorted(piggyback.get_source_hostnames(piggybacked_hostname)):
            time_settings.extend(self.get_host_config(source_hostname).piggybacked_host_files)

        # From global settings
        time_settings.append((None, 'max_cache_age', piggyback_max_cachefile_age))
        return time_settings

    # TODO: Remove old name one day
    def service_discovery_name(self) -> ServiceName:
        if 'cmk_inventory' in use_new_descriptions_for:
            return u'Check_MK Discovery'
        return u'Check_MK inventory'


def get_config_cache() -> ConfigCache:
    config_cache = _config_cache.get_dict("config_cache")
    if not config_cache:
        cache_class = ConfigCache if cmk_version.is_raw_edition() else CEEConfigCache
        config_cache["cache"] = cache_class()
    return config_cache["cache"]


# TODO: Find a clean way to move this to cmk.base.cee. This will be possible once the
# configuration settings are not held in cmk.base.config namespace anymore.
class CEEConfigCache(ConfigCache):
    """Encapsulates the CEE specific functionality"""
    def rrd_config_of_service(self, hostname: HostName,
                              description: ServiceName) -> Optional[RRDConfig]:
        return self.get_service_ruleset_value(hostname,
                                              description,
                                              cmc_service_rrd_config,
                                              deflt=None)

    def recurring_downtimes_of_service(self, hostname: HostName,
                                       description: ServiceName) -> List[RecurringDowntime]:
        return self.service_extra_conf(hostname, description, service_recurring_downtimes)  # type: ignore[name-defined] # pylint: disable=undefined-variable

    def flap_settings_of_service(self, hostname: HostName,
                                 description: ServiceName) -> Tuple[float, float, float]:
        return self.get_service_ruleset_value(
            hostname,
            description,
            cmc_service_flap_settings,  # type: ignore[name-defined] # pylint: disable=undefined-variable
            deflt=cmc_flap_settings)  # type: ignore[name-defined] # pylint: disable=undefined-variable

    def log_long_output_of_service(self, hostname: HostName, description: ServiceName) -> bool:
        return self.get_service_ruleset_value(
            hostname,
            description,
            cmc_service_long_output_in_monitoring_history,  # type: ignore[name-defined] # pylint: disable=undefined-variable
            deflt=False)

    def state_translation_of_service(self, hostname: HostName, description: ServiceName) -> Dict:
        entries = self.service_extra_conf(hostname, description, service_state_translation)  # type: ignore[name-defined] # pylint: disable=undefined-variable

        spec: Dict = {}
        for entry in entries[::-1]:
            spec.update(entry)
        return spec

    def check_timeout_of_service(self, hostname: HostName, description: ServiceName) -> int:
        """Returns the check timeout in seconds"""
        return self.get_service_ruleset_value(
            hostname,
            description,
            cmc_service_check_timeout,  # type: ignore[name-defined] # pylint: disable=undefined-variable
            deflt=cmc_check_timeout)  # type: ignore[name-defined] # pylint: disable=undefined-variable

    def graphite_metrics_of_service(self, hostname: HostName,
                                    description: ServiceName) -> Optional[List[str]]:
        return self.get_service_ruleset_value(
            hostname,
            description,
            cmc_graphite_service_metrics,  # type: ignore[name-defined] # pylint: disable=undefined-variable
            deflt=None)

    def matched_agent_config_entries(
            self, hostname: Union[HostName,
                                  Literal[BuiltinBakeryHostName.GENERIC]]) -> Dict[str, Any]:
        matched = {}
        for varname, ruleset in list(
                agent_config.items()) + [("agent_port", agent_ports),
                                         ("agent_encryption", agent_encryption),
                                         ("agent_exclude_sections", agent_exclude_sections)]:

            if hostname is BuiltinBakeryHostName.GENERIC:
                matched[varname] = self.ruleset_matcher.get_values_for_generic_agent_host(ruleset)
            else:
                matched[varname] = self.host_extra_conf(hostname, ruleset)

        return matched


# TODO: Find a clean way to move this to cmk.base.cee. This will be possible once the
# configuration settings are not held in cmk.base.config namespace anymore.
# All the "disable=undefined-variable" can be cleaned up once this has been cleaned up
class CEEHostConfig(HostConfig):
    """Encapsulates the CEE specific functionality"""
    @property
    def rrd_config(self) -> Optional[RRDConfig]:
        entries = self._config_cache.host_extra_conf(self.hostname, cmc_host_rrd_config)
        if not entries:
            return None
        return entries[0]

    @property
    def recurring_downtimes(self) -> List[RecurringDowntime]:
        return self._config_cache.host_extra_conf(self.hostname, host_recurring_downtimes)  # type: ignore[name-defined] # pylint: disable=undefined-variable

    @property
    def flap_settings(self) -> Tuple[float, float, float]:
        values = self._config_cache.host_extra_conf(self.hostname, cmc_host_flap_settings)  # type: ignore[name-defined] # pylint: disable=undefined-variable
        if not values:
            return cmc_flap_settings  # type: ignore[name-defined] # pylint: disable=undefined-variable

        return values[0]

    @property
    def log_long_output(self) -> bool:
        entries = self._config_cache.host_extra_conf(self.hostname,
                                                     cmc_host_long_output_in_monitoring_history)  # type: ignore[name-defined] # type: ignore[name-defined] # pylint: disable=undefined-variable
        if not entries:
            return False
        return entries[0]

    @property
    def state_translation(self) -> Dict:
        entries = self._config_cache.host_extra_conf(self.hostname, host_state_translation)  # type: ignore[name-defined] # pylint: disable=undefined-variable

        spec: Dict = {}
        for entry in entries[::-1]:
            spec.update(entry)
        return spec

    @property
    def smartping_settings(self) -> Dict:
        settings = {"timeout": 2.5}
        settings.update(
            self._config_cache.host_extra_conf_merged(self.hostname, cmc_smartping_settings))  # type: ignore[name-defined] # pylint: disable=undefined-variable
        return settings

    @property
    def lnx_remote_alert_handlers(self) -> List[Dict[str, str]]:
        return self._config_cache.host_extra_conf(self.hostname,
                                                  agent_config.get("lnx_remote_alert_handlers", []))
