#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections import OrderedDict
import ast
import copy
import inspect
import marshal
import numbers
import os
import py_compile
import struct
import sys
import itertools
import contextlib
from typing import (  # pylint: disable=unused-import
    Iterator, Iterable, Set, Text, Any, Callable, Dict, List, Tuple, Union, Optional, cast,
)

if sys.version_info[0] >= 3:
    from pathlib import Path  # pylint: disable=import-error
else:
    from pathlib2 import Path  # pylint: disable=import-error

if sys.version_info[0] >= 3:
    from importlib.util import MAGIC_NUMBER as _MAGIC_NUMBER  # pylint: disable=no-name-in-module,import-error
else:
    from py_compile import MAGIC as _MAGIC_NUMBER  # type: ignore[attr-defined] # pylint: disable=no-name-in-module,ungrouped-imports

import six

import cmk.utils.version as cmk_version
import cmk.utils.debug
import cmk.utils.paths
from cmk.utils.regex import regex
import cmk.utils.translations
import cmk.utils.tags
import cmk.utils.rulesets.tuple_rulesets as tuple_rulesets
import cmk.utils.rulesets.ruleset_matcher as ruleset_matcher
import cmk.utils.store as store
import cmk.utils
from cmk.utils.labels import LabelManager
from cmk.utils.rulesets.ruleset_matcher import RulesetMatchObject
from cmk.utils.exceptions import MKGeneralException, MKTerminate
from cmk.utils.encoding import convert_to_unicode
import cmk.utils.piggyback as piggyback
from cmk.utils.plugin_loader import load_plugins_with_exceptions
from cmk.utils.type_defs import (  # pylint: disable=unused-import
    HostName, ServiceName, Item, HostAddress, CheckPluginName, ActiveCheckPluginName,
    TimeperiodName, ServicegroupName, Labels, RulesetName, ContactgroupName, HostgroupName,
    LabelSources, TagValue, Tags, TagList, TagGroups, Ruleset, CheckVariables)

from cmk.base.caching import config_cache as _config_cache, runtime_cache as _runtime_cache
import cmk.base.autochecks as autochecks
import cmk.base.console as console
import cmk.base.default_config as default_config
import cmk.base.check_utils
import cmk.base.check_api_utils as check_api_utils
import cmk.base.cleanup
import cmk.base.snmp_utils
from cmk.base.snmp_utils import (  # pylint: disable=unused-import
    OIDBytes, OIDCached,  # these are required in the modules' namespace to load the configuration!
    ScanFunction, SNMPCredentials,
)
from cmk.base.check_utils import (  # pylint: disable=unused-import
    SectionName, CheckParameters, DiscoveredService,
)
try:
    from cmk.base.api import PluginName
    from cmk.base.api.agent_based.section_types import AgentSectionPlugin, SNMPSectionPlugin
    from cmk.base.api.agent_based.register.section_plugins_legacy import (
        create_agent_section_plugin_from_legacy,
        create_snmp_section_plugin_from_legacy,
    )
except ImportError:
    # API is only Python3. This script is still called by python2 modules,
    # which for the moment don't require the API and for the time being we
    # just let this import fail.
    pass

# TODO: Prefix helper functions with "_".

# This is mainly needed for pylint to detect all available
# configuration options during static analysis. The defaults
# are loaded later with load_default_config() again.
from cmk.base.default_config import *  # pylint: disable=wildcard-import,unused-wildcard-import

service_service_levels = []
host_service_levels = []

AllHosts = List[str]
ShadowHosts = Dict[str, Dict]
AllClusters = Dict[str, List[HostName]]
ExitSpecSection = Tuple[Text, int]
ExitSpec = Dict[str, Union[int, List[ExitSpecSection]]]
AgentTargetVersion = Union[None, Text, Tuple[str, str], Tuple[str, Dict[str, str]]]
RRDConfig = Dict[str, Any]
CheckContext = Dict[str, Any]
InventoryContext = Dict[str, Any]
GetCheckApiContext = Callable[[], Dict[str, Any]]
GetInventoryApiContext = Callable[[], Dict[str, Any]]
CheckIncludes = List[str]
DiscoveryCheckParameters = Dict
SpecialAgentInfoFunction = Callable[[Dict[str, Any], HostName, Optional[HostAddress]],
                                    Union[str, List[str]]]
HostCheckCommand = Union[None, str, Tuple[str, Union[int, str]]]
PingLevels = Dict[str, Union[int, Tuple[float, float]]]
ObjectAttributes = Dict  # TODO: Improve this. Have seen Dict[str, Union[str, unicode, int]]
GroupDefinitions = Dict[str, Text]
RecurringDowntime = Dict[str, Union[int, str]]
CheckInfo = Dict  # TODO: improve this type
IPMICredentials = Dict[str, str]
ManagementCredentials = Union[SNMPCredentials, IPMICredentials]


class TimespecificParamList(list):
    pass


def get_variable_names():
    # type: () -> List[str]
    """Provides the list of all known configuration variables."""
    return [k for k in default_config.__dict__ if k[0] != "_"]


def get_default_config():
    # type: () -> Dict[str, Any]
    """Provides a dictionary containing the Check_MK default configuration"""
    cfg = {}  # type: Dict[str, Any]
    for key in get_variable_names():
        value = getattr(default_config, key)

        if isinstance(value, (dict, list)):
            value = copy.deepcopy(value)

        cfg[key] = value
    return cfg


def load_default_config():
    # type: () -> None
    globals().update(get_default_config())


def register(name, default_value):
    # type: (str, Any) -> None
    """Register a new configuration variable within Check_MK base."""
    setattr(default_config, name, default_value)


def _add_check_variables_to_default_config():
    # type: () -> None
    """Add configuration variables registered by checks to config module"""
    default_config.__dict__.update(get_check_variable_defaults())


def _clear_check_variables_from_default_config(variable_names):
    # type: (List[str]) -> None
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
def set_check_variables_for_checks():
    # type: () -> None
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


def load(with_conf_d=True, validate_hosts=True, exclude_parents_mk=False):
    # type: (bool, bool, bool) -> None
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
        verify_non_invalid_variables(vars_before_config)
        _verify_no_deprecated_check_rulesets()

    _verify_no_deprecated_variables_used()


def load_packed_config():
    # type: () -> None
    """Load the configuration for the CMK helpers of CMC

    These files are written by PackedConfig().

    Should have a result similar to the load() above. With the exception that the
    check helpers would only need check related config variables.

    The validations which are performed during load() also don't need to be performed.
    """
    PackedConfig().load()


def _initialize_config():
    # type: () -> None
    _add_check_variables_to_default_config()
    load_default_config()


def _perform_post_config_loading_actions():
    # type: () -> None
    """These tasks must be performed after loading the Check_MK base configuration"""
    # First cleanup things (needed for e.g. reloading the config)
    _config_cache.clear_all()

    get_config_cache().initialize()

    # In case the checks are not loaded yet it seems the current mode
    # is not working with the checks. In this case also don't load the
    # static checks into the configuration.
    if any_check_loaded():
        set_check_variables_for_checks()


class SetFolderPathAbstract(object):  # pylint: disable=useless-object-inheritance
    def __init__(self, the_object):
        # type: (Iterable) -> None
        # TODO: Cleanup this somehow to work nicer with mypy
        super(SetFolderPathAbstract, self).__init__(the_object)  # type: ignore[call-arg]
        self._current_path = None  # type: Optional[str]

    def set_current_path(self, current_path):
        # type: (Optional[str]) -> None
        self._current_path = current_path

    def _set_folder_paths(self, new_hosts):
        # type: (List[str]) -> None
        if self._current_path is None:
            return
        for hostname in strip_tags(list(new_hosts)):
            host_paths[hostname] = self._current_path


class SetFolderPathList(SetFolderPathAbstract, list):
    def __iadd__(self, new_hosts):
        # type: (Iterable[Any]) -> SetFolderPathList
        assert isinstance(new_hosts, list)
        self._set_folder_paths(new_hosts)
        return super(SetFolderPathList, self).__iadd__(new_hosts)

    # Probably unused
    def __add__(self, new_hosts):
        # type: (Iterable[Any]) -> SetFolderPathList
        assert isinstance(new_hosts, list)
        self._set_folder_paths(new_hosts)
        return SetFolderPathList(super(SetFolderPathList, self).__add__(new_hosts))

    # Probably unused
    def append(self, new_host):
        # type: (str) -> None
        self._set_folder_paths([new_host])
        super(SetFolderPathList, self).append(new_host)


class SetFolderPathDict(SetFolderPathAbstract, dict):
    # TODO: How to annotate this?
    def update(self, new_hosts):
        # not-yet-a-type
        self._set_folder_paths(new_hosts)
        return super(SetFolderPathDict, self).update(new_hosts)

    # Probably unused
    def __setitem__(self, cluster_name, value):
        # type: (Any, Any) -> Any
        self._set_folder_paths([cluster_name])
        return super(SetFolderPathDict, self).__setitem__(cluster_name, value)


def _load_config(with_conf_d, exclude_parents_mk):
    # type: (bool, bool) -> None
    helper_vars = {
        "FOLDER_PATH": None,
    }

    global all_hosts
    global clusters

    all_hosts = SetFolderPathList(all_hosts)
    clusters = SetFolderPathDict(clusters)

    global_dict = globals()
    global_dict.update(helper_vars)

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
            current_path = None  # type: Optional[str]
            folder_path = None  # type: Optional[str]
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


def _transform_mgmt_config_vars_from_140_to_150():
    # type: () -> None
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


# Create list of all files to be included during configuration loading
def _get_config_file_paths(with_conf_d):
    # type: (bool) -> List[Path]
    list_of_files = [Path(cmk.utils.paths.main_config_file)]
    if with_conf_d:
        list_of_files += sorted(Path(cmk.utils.paths.check_mk_config_dir).glob("**/*.mk"),
                                key=cmk.utils.key_config_paths)
    for path in [Path(cmk.utils.paths.final_config_file), Path(cmk.utils.paths.local_config_file)]:
        if path.exists():
            list_of_files.append(path)
    return list_of_files


def _initialize_derived_config_variables():
    # type: () -> None
    global service_service_levels, host_service_levels
    service_service_levels = extra_service_conf.get("_ec_sl", [])
    host_service_levels = extra_host_conf.get("_ec_sl", [])


def get_derived_config_variable_names():
    # type: () -> Set[str]
    """These variables are computed from other configuration variables and not configured directly.

    The origin variable (extra_service_conf) should not be exported to the helper config. Only
    the service levels are needed."""
    return {"service_service_levels", "host_service_levels"}


def _verify_non_duplicate_hosts():
    # type: () -> None
    duplicates = duplicate_hosts()
    if duplicates:
        # TODO: Raise an exception
        console.error("Error in configuration: duplicate hosts: %s\n", ", ".join(duplicates))
        sys.exit(3)


def verify_non_invalid_variables(vars_before_config):
    # type: (Set[str]) -> None
    # Check for invalid configuration variables
    vars_after_config = all_nonfunction_vars()
    ignored_variables = {
        'vars_before_config', 'parts', 'seen_hostnames', 'taggedhost', 'hostname',
        'service_service_levels', 'host_service_levels'
    }

    found_invalid = 0
    for name in vars_after_config:
        if name not in ignored_variables and name not in vars_before_config:
            console.error("Invalid configuration variable '%s'\n", name)
            found_invalid += 1

    if found_invalid:
        console.error("--> Found %d invalid variables\n" % found_invalid)
        console.error("If you use own helper variables, please prefix them with _.\n")
        sys.exit(1)


def _verify_no_deprecated_variables_used():
    # type: () -> None
    if isinstance(snmp_communities, dict):
        console.error("ERROR: snmp_communities cannot be a dict any more.\n")
        sys.exit(1)

    # Legacy checks have never been supported by CMC, were not configurable via WATO
    # and have been removed with Check_MK 1.6
    if legacy_checks:
        console.error(
            "Check_MK does not support the configuration variable \"legacy_checks\" anymore. "
            "Please use custom_checks or active_checks instead.\n")
        sys.exit(1)

    # "checks" declarations were never possible via WATO. They can be configured using
    # "static_checks" using the GUI. "checks" has been removed with Check_MK 1.6.
    if checks:
        console.error(
            "Check_MK does not support the configuration variable \"checks\" anymore. "
            "Please use \"static_checks\" instead (which is configurable via \"Manual checks\" in WATO).\n"
        )
        sys.exit(1)


def _verify_no_deprecated_check_rulesets():
    # type: () -> None
    deprecated_rulesets = [
        ("services", "inventory_services"),
        ("domino_tasks", "inv_domino_tasks"),
        ("ps", "inventory_processes"),
        ("logwatch", "logwatch_patterns"),
    ]
    for check_plugin_name, varname in deprecated_rulesets:
        check_context = get_check_context(check_plugin_name)
        if check_context[varname]:
            console.warning(
                "Found rules for deprecated ruleset %r. These rules are not applied "
                "anymore. In case you still need them, you need to migrate them by hand. "
                "Otherwise you can remove them from your configuration." % varname)


def all_nonfunction_vars():
    # type: () -> Set[str]
    return {
        name for name, value in globals().items()
        if name[0] != '_' and not hasattr(value, '__call__')
    }


class PackedConfig(object):  # pylint: disable=useless-object-inheritance
    """The precompiled host checks and the CMC Check_MK helpers use a
    "precompiled" part of the Check_MK configuration during runtime.

    a) They must not use the live config from etc/check_mk during
       startup. They are only allowed to load the config activated by
       the user.

    b) They must not load the whole Check_MK config. Because they only
       need the options needed for checking
    """

    # These variables are part of the Check_MK configuration, but are not needed
    # by the Check_MK keepalive mode, so exclude them from the packed config
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

    def __init__(self):
        # type: () -> None
        super(PackedConfig, self).__init__()
        self._path = os.path.join(cmk.utils.paths.var_dir, "base", "precompiled_check_config.mk")

    def save(self):
        # type: () -> None
        self._write(self._pack())

    def _pack(self):
        # type: () -> str
        helper_config = ("#!/usr/bin/env python\n"
                         "# encoding: utf-8\n"
                         "# Created by Check_MK. Dump of the currently active configuration\n\n")

        config_cache = get_config_cache()

        # These functions purpose is to filter out hosts which are monitored on different sites
        active_hosts = config_cache.all_active_hosts()
        active_clusters = config_cache.all_active_clusters()

        def filter_all_hosts(all_hosts_orig):
            # type: (AllHosts) -> List[HostName]
            all_hosts_red = []
            for host_entry in all_hosts_orig:
                hostname = host_entry.split("|", 1)[0]
                if hostname in active_hosts:
                    all_hosts_red.append(host_entry)
            return all_hosts_red

        def filter_clusters(clusters_orig):
            # type: (AllClusters) -> Dict[HostName, List[HostName]]
            clusters_red = {}
            for cluster_entry, cluster_nodes in clusters_orig.items():
                clustername = cluster_entry.split("|", 1)[0]
                if clustername in active_clusters:
                    clusters_red[cluster_entry] = cluster_nodes
            return clusters_red

        def filter_hostname_in_dict(values):
            # type: (Dict[HostName, Dict[str, str]]) -> Dict[HostName, Dict[str, str]]
            values_red = {}
            for hostname, attributes in values.items():
                if hostname in active_hosts:
                    values_red[hostname] = attributes
            return values_red

        filter_var_functions = {
            "all_hosts": filter_all_hosts,
            "clusters": filter_clusters,
            "host_attributes": filter_hostname_in_dict,
            "ipaddresses": filter_hostname_in_dict,
            "ipv6addresses": filter_hostname_in_dict,
            "explicit_snmp_communities": filter_hostname_in_dict,
            "hosttags": filter_hostname_in_dict
        }  # type: Dict[str, Callable[[Any], Any]]

        #
        # Add modified Check_MK base settings
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

            if not self._packable(varname, val):
                continue

            if varname in filter_var_functions:
                val = filter_var_functions[varname](val)

            helper_config += "\n%s = %r\n" % (varname, val)

        #
        # Add modified check specific Check_MK base settings
        #

        check_variable_defaults = get_check_variable_defaults()

        for varname, val in get_check_variables().items():
            if val == check_variable_defaults[varname]:
                continue

            if not self._packable(varname, val):
                continue

            helper_config += "\n%s = %r\n" % (varname, val)

        return helper_config

    def _packable(self, varname, val):
        # type: (str, Any) -> bool
        """Checks whether or not a variable can be written to the config.mk
        and read again from it."""
        if isinstance(val, six.string_types + (int, bool)) or not val:
            return True

        try:
            eval(repr(val))
            return True
        except SyntaxError:
            return False

    def _write(self, helper_config):
        # type: (str) -> None
        store.makedirs(os.path.dirname(self._path))

        store.save_file(self._path + ".orig", helper_config + "\n")

        code = compile(helper_config, '<string>', 'exec')
        with open(self._path + ".compiled", "wb") as compiled_file:
            marshal.dump(code, compiled_file)

        os.rename(self._path + ".compiled", self._path)

    def load(self):
        # type: () -> None
        _initialize_config()
        with open(self._path, "rb") as f:
            exec(marshal.load(f), globals())
        _perform_post_config_loading_actions()


@contextlib.contextmanager
def set_use_core_config(use_core_config):
    # type: (bool) -> Iterator[None]
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
            cmk.utils.paths.autochecks_dir = cmk.utils.paths.core_autochecks_dir
            cmk.utils.paths.discovered_host_labels_dir = cmk.utils.paths.core_discovered_host_labels_dir
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


def strip_tags(tagged_hostlist):
    # type: (List[str]) -> List[str]
    cache = _config_cache.get_dict("strip_tags")

    cache_id = tuple(tagged_hostlist)
    try:
        return cache[cache_id]
    except KeyError:
        result = [h.split('|', 1)[0] for h in tagged_hostlist]
        cache[cache_id] = result
        return result


def _get_shadow_hosts():
    # type: () -> ShadowHosts
    # Only available with CEE
    return shadow_hosts if "shadow_hosts" in globals() else {}  # type: ignore[name-defined] # pylint: disable=undefined-variable


# This function should only be used during duplicate host check! It has to work like
# all_active_hosts() but with the difference that duplicates are not removed.
def _all_active_hosts_with_duplicates():
    # type: () -> List[str]
    return _filter_active_hosts(get_config_cache(),
                                (strip_tags(list(all_hosts)) + strip_tags(list(clusters)) +
                                 strip_tags(list(_get_shadow_hosts()))))


def _filter_active_hosts(config_cache, hostlist, keep_offline_hosts=False):
    # type: (ConfigCache, Iterable[str], bool) -> List[str]
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
        if (keep_offline_hosts or config_cache.in_binary_hostlist(hostname, only_hosts)) and
        _host_is_member_of_site(config_cache, hostname, distributed_wato_site)
    ]


def _host_is_member_of_site(config_cache, hostname, site):
    # type: (ConfigCache, str, str) -> bool
    # hosts without a site: tag belong to all sites
    return config_cache.tags_of_host(hostname).get("site",
                                                   distributed_wato_site) == distributed_wato_site


def duplicate_hosts():
    # type: () -> List[str]
    seen_hostnames = set()  # type: Set[str]
    duplicates = set()  # type: Set[str]

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
def all_offline_hosts():
    # type: () -> Set[str]
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


def all_configured_offline_hosts():
    # type: () -> Set[str]
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
def _get_old_cmciii_temp_description(item):
    # type: (Item) -> Tuple[bool, ServiceName]
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
    "brocade_sys.mem": "Memory used",
    "casa_cpu_temp": "Temperature %s",
    "cisco_mem": "Mem used %s",
    "cisco_mem_asa": "Mem used %s",
    "cisco_mem_asa64": "Mem used %s",
    "cmciii.temp": _get_old_cmciii_temp_description,
    "cmciii.psm_current": "%s",
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
    "esx_vsphere_hostsystem.mem_usage": "Memory used",
    "esx_vsphere_hostsystem.mem_usage_cluster": "Memory usage",
    "etherbox.temp": "Sensor %s",
    "fortigate_memory": "Memory usage",
    "fortigate_memory_base": "Memory usage",
    "fortigate_node.memory": "Memory usage %s",
    "hr_fs": "fs_%s",
    "hr_mem": "Memory used",
    "huawei_switch_mem": "Memory used %s",
    "hyperv_vm": "hyperv_vms",
    "ibm_svc_mdiskgrp": "MDiskGrp %s",
    "ibm_svc_system": "IBM SVC Info",
    "ibm_svc_systemstats.cache": "IBM SVC Cache Total",
    "ibm_svc_systemstats.diskio": "IBM SVC Throughput %s Total",
    "ibm_svc_systemstats.disk_latency": "IBM SVC Latency %s Total",
    "ibm_svc_systemstats.iops": "IBM SVC IOPS %s Total",
    "innovaphone_mem": "Memory used",
    "innovaphone_temp": lambda item: (False, "Temperature"),
    "juniper_mem": "Memory Utilization %s",
    "juniper_screenos_mem": "Memory used",
    "juniper_trpz_mem": "Memory used",
    "liebert_bat_temp": lambda item: (False, "Battery Temp"),
    "logwatch": "LOG %s",
    "logwatch.groups": "LOG %s",
    "mem.used": "Memory used",
    "mem.win": "Memory and pagefile",
    "mknotifyd": "Notification Spooler %s",
    "mknotifyd.connection": "Notification Connection %s",
    "mssql_backup": "%s Backup",
    "mssql_blocked_sessions": lambda item: (False, "MSSQL Blocked Sessions"),
    "mssql_counters.cache_hits": "%s",
    "mssql_counters.file_sizes": "%s File Sizes",
    "mssql_counters.locks": "%s Locks",
    "mssql_counters.locks_per_batch": "%s Locks per Batch",
    "mssql_counters.pageactivity": "%s Page Activity",
    "mssql_counters.sqlstats": "%s",
    "mssql_counters.transactions": "%s Transactions",
    "mssql_databases": "%s Database",
    "mssql_datafiles": "Datafile %s",
    "mssql_tablespaces": "%s Sizes",
    "mssql_transactionlogs": "Transactionlog %s",
    "mssql_versions": "%s Version",
    "netscaler_mem": "Memory used",
    "nullmailer_mailq": lambda item: (False, "Nullmailer Queue"),
    "nvidia.temp": "Temperature NVIDIA %s",
    "postfix_mailq": lambda item: (False, "Postfix Queue"),
    "ps": "proc_%s",
    "ps.perf": "proc_%s",
    "qmail_stats": lambda item: (False, "Qmail Queue"),
    "raritan_emx": "Rack %s",
    "raritan_pdu_inlet": "Input Phase %s",
    "services": "service_%s",
    "solaris_mem": "Memory used",
    "sophos_memory": "Memory usage",
    "statgrab_mem": "Memory used",
    "tplink_mem": "Memory used",
    "ups_bat_temp": "Temperature Battery %s",
    "vms_diskstat.df": "fs_%s",
    "wmic_process": "proc_%s",
    "zfsget": "fs_%s",
}


def service_description(hostname, check_plugin_name, item):
    # type: (HostName, CheckPluginName, Item) -> ServiceName
    if check_plugin_name not in check_info:
        if item:
            return "Unimplemented check %s / %s" % (check_plugin_name, item)
        return "Unimplemented check %s" % check_plugin_name

    # use user-supplied service description, if available
    add_item = True
    descr_format = service_descriptions.get(check_plugin_name)
    if not descr_format:
        # handle renaming for backward compatibility
        if check_plugin_name in _old_service_descriptions and \
            check_plugin_name not in use_new_descriptions_for:

            # Can be a fucntion to generate the old description more flexible.
            old_descr = _old_service_descriptions[check_plugin_name]
            if callable(old_descr):
                add_item, descr_format = old_descr(item)
            else:
                descr_format = old_descr

        else:
            descr_format = check_info[check_plugin_name]["service_description"]

    descr_format = six.ensure_text(descr_format)

    # Note: we strip the service description (remove spaces).
    # One check defines "Pages %s" as a description, but the item
    # can by empty in some cases. Nagios silently drops leading
    # and trailing spaces in the configuration file.
    if add_item and isinstance(item, six.string_types + (numbers.Integral,)):
        if "%s" not in descr_format:
            descr_format += " %s"
        descr = descr_format % (item,)
    else:
        descr = descr_format

    if "%s" in descr:
        raise MKGeneralException(
            "Found '%%s' in service description (Host: %s, Check type: %s, Item: %s). "
            "Please try to rediscover the service to fix this issue." %
            (hostname, check_plugin_name, item))

    return get_final_service_description(hostname, descr)


def _old_active_http_check_service_description(params):
    # type: (Union[Dict, Tuple]) -> str
    name = params[0] if isinstance(params, tuple) else params["name"]
    return name[1:] if name.startswith("^") else "HTTP %s" % name


_old_active_check_service_descriptions = {
    "http": _old_active_http_check_service_description,
}


def active_check_service_description(hostname, active_check_name, params):
    # type: (HostName, ActiveCheckPluginName, Dict) -> ServiceName
    if active_check_name not in active_check_info:
        return "Unimplemented check %s" % active_check_name

    if (active_check_name in _old_active_check_service_descriptions and
            active_check_name not in use_new_descriptions_for):
        description = _old_active_check_service_descriptions[active_check_name](params)
    else:
        act_info = active_check_info[active_check_name]
        description = act_info["service_description"](params)

    description = description.replace('$HOSTNAME$', hostname)

    return get_final_service_description(hostname, description)


def get_final_service_description(hostname, description):
    # type: (HostName, ServiceName) -> ServiceName
    translations = get_service_translations(hostname)
    if translations:
        # Translate
        description = cmk.utils.translations.translate_service_description(
            translations, description)

    # Sanitize; Remove illegal characters from a service description
    description = description.strip()
    cache = _config_cache.get_dict("final_service_description")
    try:
        new_description = cache[description]
    except KeyError:
        new_description = "".join([c for c in description if c not in nagios_illegal_chars
                                  ]).rstrip("\\")
        cache[description] = new_description

    return new_description


def service_ignored(hostname, check_plugin_name, description):
    # type: (HostName, Optional[CheckPluginName], Optional[ServiceName]) -> bool
    if check_plugin_name and check_plugin_name in ignored_checktypes:
        return True

    if check_plugin_name and _checktype_ignored_for_host(hostname, check_plugin_name):
        return True

    if description is not None \
       and get_config_cache().in_boolean_serviceconf_list(hostname, description, ignored_services):
        return True

    return False


def _checktype_ignored_for_host(host, checktype):
    # type: (HostName, CheckPluginName) -> bool
    if checktype in ignored_checktypes:
        return True
    ignored = get_config_cache().host_extra_conf(host, ignored_checks)
    for e in ignored:
        if checktype == e or (isinstance(e, list) and checktype in e):
            return True
    return False


# TODO: Make this use the generic "rulesets" functions
# a) This function has never been configurable via WATO (see https://mathias-kettner.de/checkmk_service_dependencies.html)
# b) It only affects the Nagios core - CMC does not implement service dependencies
# c) This function implements some specific regex replacing match+replace which makes it incompatible to
#    regular service rulesets. Therefore service_extra_conf() can not easily be used :-/
def service_depends_on(hostname, servicedesc):
    # type: (HostName, ServiceName) -> List[ServiceName]
    """Return a list of services this services depends upon"""
    deps = []
    config_cache = get_config_cache()
    for entry in service_dependencies:
        entry, rule_options = tuple_rulesets.get_rule_options(entry)
        if rule_options.get("disabled"):
            continue

        if len(entry) == 3:
            depname, hostlist, patternlist = entry
            tags = []  # type: List[str]
        elif len(entry) == 4:
            depname, tags, hostlist, patternlist = entry
        else:
            raise MKGeneralException("Invalid entry '%r' in service dependencies: "
                                     "must have 3 or 4 entries" % entry)

        if tuple_rulesets.hosttags_match_taglist(config_cache.tag_list_of_host(hostname), tags) and \
           tuple_rulesets.in_extraconf_hostlist(hostlist, hostname):
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


def is_cmc():
    # type: () -> bool
    """Whether or not the site is currently configured to use the Microcore."""
    return monitoring_core == "cmc"


def translate_piggyback_host(sourcehost, backedhost):
    # type: (HostName, HostName) -> HostName
    translation = _get_piggyback_translations(sourcehost)

    # To make it possible to match umlauts we need to change the hostname
    # to a unicode string which can then be matched with regexes etc.
    # We assume the incoming name is correctly encoded in UTF-8
    decoded_backedhost = convert_to_unicode(backedhost,
                                            fallback_encoding=fallback_agent_output_encoding)
    return six.ensure_str(cmk.utils.translations.translate_hostname(translation,
                                                                    decoded_backedhost))


def _get_piggyback_translations(hostname):
    # type: (HostName) -> cmk.utils.translations.TranslationOptions
    """Get a dict that specifies the actions to be done during the hostname translation"""
    rules = get_config_cache().host_extra_conf(hostname, piggyback_translation)
    translations = {}  # type: cmk.utils.translations.TranslationOptions
    for rule in rules[::-1]:
        translations.update(rule)
    return translations


def get_service_translations(hostname):
    # type: (HostName) -> cmk.utils.translations.TranslationOptions
    translations_cache = _config_cache.get_dict("service_description_translations")
    if hostname in translations_cache:
        return translations_cache[hostname]

    rules = get_config_cache().host_extra_conf(hostname, service_description_translation)
    translations = {}  # type: cmk.utils.translations.TranslationOptions
    for rule in rules[::-1]:
        for k, v in rule.items():
            if isinstance(v, list):
                translations.setdefault(k, set())
                translations[k] |= set(v)
            else:
                translations[k] = v

    translations_cache[hostname] = translations
    return translations


def prepare_check_command(command_spec, hostname, description):
    # type: (Union[str, List[str]], HostName, Optional[ServiceName]) -> str
    """Prepares a check command for execution by Check_MK.

    This function either accepts a string or a list of arguments as
    command_spec.  In case a list is given it quotes the single elements. It
    also prepares password store entries for the command line. These entries
    will be completed by the executed program later to get the password from
    the password store.
    """
    if isinstance(command_spec, six.string_types):
        return command_spec

    if not isinstance(command_spec, list):
        raise NotImplementedError()

    passwords = []  # type: List[Tuple[str, str, str]]
    formated = []  # type: List[str]
    for arg in command_spec:
        arg_type = type(arg)

        if arg_type in [int, float]:
            formated.append("%s" % arg)

        elif isinstance(arg, six.string_types):
            formated.append(cmk.utils.quote_shell_string(arg))

        elif arg_type == tuple and len(arg) == 3:
            pw_ident, preformated_arg = arg[1:]
            try:
                password = stored_passwords[pw_ident]["password"]
            except KeyError:
                if hostname and description:
                    descr = " used by service \"%s\" on host \"%s\"" % (description, hostname)
                elif hostname:
                    descr = " used by host host \"%s\"" % (hostname)
                else:
                    descr = ""

                console.warning("The stored password \"%s\"%s does not exist (anymore)." %
                                (pw_ident, descr))
                password = "%%%"

            pw_start_index = str(preformated_arg.index("%s"))
            formated.append(cmk.utils.quote_shell_string(preformated_arg % ("*" * len(password))))
            passwords.append((str(len(formated)), pw_start_index, pw_ident))

        else:
            raise MKGeneralException("Invalid argument for command line: %r" % (arg,))

    if passwords:
        formated = ["--pwstore=%s" % ",".join(["@".join(p) for p in passwords])] + formated

    return " ".join(formated)


def get_http_proxy(http_proxy):
    # type: (Tuple[str, str]) -> Optional[str]
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


def get_registered_section_plugin(plugin_name):
    # type: (PluginName) -> Optional[Union[AgentSectionPlugin, SNMPSectionPlugin]]
    if plugin_name in registered_agent_sections:
        return registered_agent_sections[plugin_name]
    if plugin_name in registered_snmp_sections:
        return registered_snmp_sections[plugin_name]
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
def in_extraconf_servicelist(service_patterns, service):
    # type: (List[Text], Text) -> bool
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
_check_contexts = {}  # type: Dict[str, Any]
# has a separate sub-dictionary, named by the check name.
# It is populated with the includes and the check itself.

# The following data structures will be filled by the checks
# all known checks
check_info = {}  # type: Dict[str, Dict[str, Any]]
# library files needed by checks
check_includes = {}  # type: Dict[str, List[Any]]
# optional functions for parameter precompilation
precompile_params = {}  # type: Dict[str, Callable[[str, str, Dict[str, Any]], Any]]
# dictionary-configured checks declare their default level variables here
check_default_levels = {}  # type: Dict[str, Any]
# factory settings for dictionary-configured checks
factory_settings = {}  # type: Dict[str, Dict[str, Any]]
# variables (names) in checks/* needed for check itself
check_config_variables = []  # type:  List[Any]
# whichs OIDs to fetch for which check (for tabular information)
snmp_info = {}  # type: Dict[str, Union[Tuple[Any], List[Tuple[Any]]]]
# SNMP autodetection
snmp_scan_functions = {}  # type: Dict[str, ScanFunction]
# definitions of active "legacy" checks
active_check_info = {}  # type: Dict[str, Dict[str, Any]]
special_agent_info = {}  # type: Dict[str, SpecialAgentInfoFunction]

# The following data structures hold information registered by the API functions
# with the correspondig name, e.g. register.agent_section -> registered_agent_sections
registered_agent_sections = {}  # type: Dict[PluginName, AgentSectionPlugin]
registered_snmp_sections = {}  # type: Dict[PluginName, SNMPSectionPlugin]

# Names of variables registered in the check files. This is used to
# keep track of the variables needed by each file. Those variables are then
# (if available) read from the config and applied to the checks module after
# reading in the configuration of the user.
_check_variables = {}  # type: Dict[str, List[Any]]
# keeps the default values of all the check variables
_check_variable_defaults = {}  # type: Dict[str, Any]
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


def load_all_checks(get_check_api_context):
    # type: (GetCheckApiContext) -> None
    """Load all checks and includes"""
    global _all_checks_loaded

    _initialize_data_structures()

    for plugin, exception in load_plugins_with_exceptions(
            "cmk.base.plugins.agent_based",
            cmk.utils.paths.agent_based_plugins_dir,
            cmk.utils.paths.local_agent_based_plugins_dir,
    ):
        console.error("Error in agent based plugin %s: %s\n", plugin, exception)
        if cmk.utils.debug.enabled():
            raise exception

    # LEGACY CHECK PLUGINS
    filelist = get_plugin_paths(str(cmk.utils.paths.local_checks_dir), cmk.utils.paths.checks_dir)
    load_checks(get_check_api_context, filelist)

    _all_checks_loaded = True


def _initialize_data_structures():
    # type: () -> None
    """Initialize some data structures which are populated while loading the checks"""
    global _all_checks_loaded
    _all_checks_loaded = False

    _check_variables.clear()
    _check_variable_defaults.clear()

    _check_contexts.clear()
    check_info.clear()
    check_includes.clear()
    precompile_params.clear()
    check_default_levels.clear()
    factory_settings.clear()
    del check_config_variables[:]
    snmp_info.clear()
    snmp_scan_functions.clear()
    active_check_info.clear()
    special_agent_info.clear()

    registered_agent_sections.clear()
    registered_snmp_sections.clear()


def get_plugin_paths(*dirs):
    # type: (str) -> List[str]
    filelist = []  # type: List[str]
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
def load_checks(get_check_api_context, filelist):
    # type: (GetCheckApiContext, List[str]) -> None
    cmk_global_vars = set(get_variable_names())

    loaded_files = set()  # type: Set[str]

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

            load_check_includes(f, check_context)

            load_precompiled_plugin(f, check_context)
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
        for varname, value in new_check_vars.items():
            # Do not allow checks to override Check_MK builtin global variables. Silently
            # skip them here. The variables will only be locally available to the checks.
            if varname in cmk_global_vars:
                continue

            if varname.startswith("_"):
                continue

            # NOTE: Classes and builtin functions are callable, too!
            if callable(value) or inspect.ismodule(value):
                continue

            _check_variable_defaults[varname] = value

            # Keep track of which variable needs to be set to which context
            context_ident_list = _check_variables.setdefault(varname, [])
            context_ident_list += new_checks
            context_ident_list += new_active_checks

    # Now convert check_info to new format.
    convert_check_info()
    _extract_agent_and_snmp_sections()
    verify_checkgroup_members()
    initialize_check_type_caches()


def all_checks_loaded():
    # type: () -> bool
    """Whether or not all(!) checks have been loaded into the current process"""
    return _all_checks_loaded


def any_check_loaded():
    # type: () -> bool
    """Whether or not some checks have been loaded into the current process"""
    return bool(_check_contexts)


# Constructs a new check context dictionary. It contains the whole check API.
def new_check_context(get_check_api_context):
    # type: (GetCheckApiContext) -> CheckContext
    # Add the data structures where the checks register with Check_MK
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
def load_check_includes(check_file_path, check_context):
    # type: (str, CheckContext) -> None
    for include_file_name in cached_includes_of_plugin(check_file_path):
        include_file_path = check_include_file_path(include_file_name)
        try:
            load_precompiled_plugin(include_file_path, check_context)
        except MKTerminate:
            raise

        except Exception as e:
            console.error("Error in check include file %s: %s\n", include_file_path, e)
            if cmk.utils.debug.enabled():
                raise
            continue


def check_include_file_path(include_file_name):
    # type: (str) -> str
    local_path = cmk.utils.paths.local_checks_dir / include_file_name
    if local_path.exists():
        return str(local_path)
    return os.path.join(cmk.utils.paths.checks_dir, include_file_name)


def cached_includes_of_plugin(check_file_path):
    # type: (str) -> CheckIncludes
    cache_file_path = _include_cache_file_path(check_file_path)
    try:
        return _get_cached_check_includes(check_file_path, cache_file_path)
    except OSError:
        pass  # No usable cache. Terminate

    includes = includes_of_plugin(check_file_path)
    _write_check_include_cache(cache_file_path, includes)
    return includes


def _get_cached_check_includes(check_file_path, cache_file_path):
    # type: (str, str) -> CheckIncludes
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


def _write_check_include_cache(cache_file_path, includes):
    # type: (str, CheckIncludes) -> None
    store.makedirs(os.path.dirname(cache_file_path))
    store.save_file(cache_file_path, "%s\n" % "|".join(includes))


def _include_cache_file_path(path):
    # type: (str) -> str
    is_local = path.startswith(str(cmk.utils.paths.local_checks_dir))
    return os.path.join(cmk.utils.paths.include_cache_dir, "local" if is_local else "builtin",
                        os.path.basename(path))


# Parse the check file without executing the code to find the check include
# files the check uses. The following statements are extracted:
# check_info[...] = { "includes": [...] }
# inv_info[...] = { "includes": [...] }
# check_includes[...] = [...]
def includes_of_plugin(check_file_path):
    # type: (str) -> CheckIncludes
    include_names = OrderedDict()

    def _load_from_check_info(node):
        # type: (ast.Assign) -> None
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

    def _load_from_check_includes(node):
        # type: (ast.Assign) -> None
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


def _plugin_pathnames_in_directory(path):
    # type: (str) -> List[str]
    if path and os.path.exists(path):
        return sorted([
            path + "/" + f
            for f in os.listdir(path)
            if not f.startswith(".") and not f.endswith(".include")
        ])
    return []


# TODO: Check if this totally non-portable Kung Fu still works with Python 3!
def load_precompiled_plugin(path, check_context):
    # type: (str, CheckContext) -> None
    """Loads the given check or check include plugin into the given
    check context.

    To improve loading speed the files are not read directly. The files are
    python byte-code compiled before in case it has not been done before. In
    case there is already a compiled file that is newer than the current one,
    then the precompiled file is loaded."""

    # https://docs.python.org/3/library/py_compile.html
    # https://www.python.org/dev/peps/pep-0552/
    # HACK:
    header_size = 16 if sys.version_info[0] >= 3 else 8
    precompiled_path = _precompiled_plugin_path(path)

    if not _is_plugin_precompiled(path, precompiled_path):
        console.vverbose("Precompile %s to %s\n" % (path, precompiled_path))
        store.makedirs(os.path.dirname(precompiled_path))
        py_compile.compile(path, precompiled_path, doraise=True)

    exec(marshal.loads(open(precompiled_path, "rb").read()[header_size:]), check_context)


def _is_plugin_precompiled(path, precompiled_path):
    # type: (str, str) -> bool
    if not os.path.exists(precompiled_path):
        return False

    # Check precompiled file header
    f = open(precompiled_path, "rb")

    file_magic = f.read(4)
    if file_magic != _MAGIC_NUMBER:
        return False

    if sys.version_info[0] >= 3:
        # Skip the hash and assure that the timestamp format is used, i.e. the hash is 0.
        # For further details see: https://www.python.org/dev/peps/pep-0552/#id15
        file_hash = int(struct.unpack("I", f.read(4))[0])
        assert file_hash == 0

    try:
        origin_file_mtime = struct.unpack("I", f.read(4))[0]
    except struct.error:
        return False

    if int(os.stat(path).st_mtime) != origin_file_mtime:
        return False

    return True


def _precompiled_plugin_path(path):
    # type: (str) -> str
    is_local = path.startswith(str(cmk.utils.paths.local_checks_dir))
    return os.path.join(cmk.utils.paths.precompiled_checks_dir, "local" if is_local else "builtin",
                        os.path.basename(path))


def check_variable_names():
    # type: () -> List[str]
    return list(_check_variables)


def get_check_variable_defaults():
    # type: () -> CheckVariables
    """Returns the check variable default settings. These are the settings right
    after loading the checks."""
    return _check_variable_defaults


def set_check_variables(check_variables):
    # type: (CheckVariables) -> None
    """Update the check related config variables in the relevant check contexts"""
    for varname, value in check_variables.items():
        for context_ident in _check_variables[varname]:
            _check_contexts[context_ident][varname] = value


def get_check_variables():
    # type: () -> CheckVariables
    """Returns the currently effective check variable settings

    Since the variables are only stored in the individual check contexts and not stored
    in a central place, this function needs to collect the values from the check contexts.
    We assume a single variable has the same value in all relevant contexts, which means
    that it is enough to get the variable from the first context."""
    check_config = {}
    for varname, context_ident_list in _check_variables.items():
        check_config[varname] = _check_contexts[context_ident_list[0]][varname]
    return check_config


def get_check_context(check_plugin_name):
    # type: (CheckPluginName) -> CheckContext
    """Returns the context dictionary of the given check plugin"""
    return _check_contexts[check_plugin_name]


# FIXME: Clear / unset all legacy variables to prevent confusions in other code trying to
# use the legacy variables which are not set by newer checks.
def convert_check_info():
    # type: () -> None
    check_info_defaults = {
        "check_function": None,
        "inventory_function": None,
        "parse_function": None,
        "group": None,
        "snmp_info": None,
        "snmp_scan_function": None,
        # TODO: The 'handle_empty_info' feature predates the 'parse_function'
        #        and is not needed anymore.
        "handle_empty_info": False,
        "handle_real_time_checks": False,
        "default_levels_variable": None,
        "node_info": False,
        "extra_sections": [],
        "service_description": None,
        "has_perfdata": False,
        "management_board": None,
    }  # type: CheckInfo

    for check_plugin_name, info in check_info.items():
        section_name = cmk.base.check_utils.section_name_of(check_plugin_name)

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
                # TODO: The 'handle_empty_info' feature predates the 'parse_function'
                #        and is not needed anymore.
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
            section_name = cmk.base.check_utils.section_name_of(check_plugin_name)
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
        section_name = cmk.base.check_utils.section_name_of(check_plugin_name)
        if info["snmp_info"] and section_name not in snmp_info:
            snmp_info[section_name] = info["snmp_info"]

        if info["snmp_scan_function"] and section_name not in snmp_scan_functions:
            snmp_scan_functions[section_name] = info["snmp_scan_function"]


AUTO_MIGRATION_ERR_MSG = ("Failed to auto-migrate legacy plugin to %s: %s\n"
                          "Please refer to Werk 10601 for more information.")


def _extract_agent_and_snmp_sections():
    # type: () -> None
    """Here comes the next layer of converting-to-"new"-api.

    For the new check-API in cmk/base/api/agent_based, we use the accumulated information
    in check_info, snmp_scan_functions and snmp_info to create API compliant plugin objects.
    """
    for check_plugin_name in sorted(check_info):
        section_name = cmk.base.check_utils.section_name_of(check_plugin_name)
        is_snmp_plugin = section_name in snmp_info

        if get_registered_section_plugin(PluginName(section_name)):
            continue

        check_info_dict = check_info.get(section_name, check_info[check_plugin_name])
        try:
            if is_snmp_plugin:
                snmp_section_plugin = create_snmp_section_plugin_from_legacy(
                    section_name,
                    check_info_dict,
                    snmp_scan_functions[section_name],
                    snmp_info[section_name],
                )
                registered_snmp_sections[snmp_section_plugin.name] = snmp_section_plugin
            else:
                agent_section_plugin = create_agent_section_plugin_from_legacy(
                    section_name,
                    check_info_dict,
                )
                registered_agent_sections[agent_section_plugin.name] = agent_section_plugin
        except (NotImplementedError, KeyError, AssertionError, ValueError):
            # TODO (mo): Clean this up once we have a solution for the plugins currently
            # failing here. For now we need too keep it commented out, because we can't
            # test otherwise.
            #if cmk.utils.debug.enabled():
            #    raise MKGeneralException(exc)
            #console.warning(AUTO_MIGRATION_ERR_MSG % ("section", check_plugin_name))
            pass


# This function validates the checks which are members of checkgroups to have either
# all or none an item. Mixed checkgroups lead to strange exceptions when processing
# the check parameters. So it is much better to catch these errors in a central place
# with a clear error message.
def verify_checkgroup_members():
    # type: () -> None
    groups = checks_by_checkgroup()

    for group_name, check_entries in groups.items():
        with_item, without_item = [], []
        for check_plugin_name, check_info_entry in check_entries:
            # Trying to detect whether or not the check has an item. But this mechanism is not
            # 100% reliable since Check_MK appends an item to the service_description when "%s"
            # is not in the checks service_description template.
            # Maybe we need to define a new rule which enforces the developer to use the %s in
            # the service_description. At least for grouped checks.
            if "%s" in check_info_entry["service_description"]:
                with_item.append(check_plugin_name)
            else:
                without_item.append(check_plugin_name)

        if with_item and without_item:
            raise MKGeneralException(
                "Checkgroup %s has checks with and without item! At least one of "
                "the checks in this group needs to be changed (With item: %s, "
                "Without item: %s)" % (group_name, ", ".join(with_item), ", ".join(without_item)))


def checks_by_checkgroup():
    # type: () -> Dict[RulesetName, List[Tuple[CheckPluginName, CheckInfo]]]
    groups = {}  # type: Dict[RulesetName, List[Tuple[CheckPluginName, CheckInfo]]]
    for check_plugin_name, check in check_info.items():
        group_name = check["group"]
        if group_name:
            groups.setdefault(group_name, [])
            groups[group_name].append((check_plugin_name, check))
    return groups


# These caches both only hold the base names of the checks
def initialize_check_type_caches():
    # type: () -> None
    snmp_cache = _runtime_cache.get_set("check_type_snmp")
    snmp_cache.update(snmp_info)

    tcp_cache = _runtime_cache.get_set("check_type_tcp")
    for check_plugin_name in check_info:
        section_name = cmk.base.check_utils.section_name_of(check_plugin_name)
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


def discoverable_tcp_checks():
    # type: () -> Set[CheckPluginName]
    types = set()
    for check_plugin_name, check in check_info.items():
        if cmk.base.check_utils.is_tcp_check(check_plugin_name) and check["inventory_function"]:
            types.add(check_plugin_name)
    return types


def discoverable_snmp_checks():
    # type: () -> Set[CheckPluginName]
    types = set()
    for check_plugin_name, check in check_info.items():
        if cmk.base.check_utils.is_snmp_check(check_plugin_name) and check["inventory_function"]:
            types.add(check_plugin_name)
    return types


def compute_check_parameters(host, checktype, item, params):
    # type: (HostName, CheckPluginName, Item, CheckParameters) -> Optional[CheckParameters]
    """Compute parameters for a check honoring factory settings,
    default settings of user in main.mk, check_parameters[] and
    the values code in autochecks (given as parameter params)"""
    if checktype not in check_info:  # handle vanished checktype
        return None

    params = _update_with_default_check_parameters(checktype, params)
    params = _update_with_configured_check_parameters(host, checktype, item, params)

    return params


def _update_with_default_check_parameters(checktype, params):
    # type: (CheckPluginName, CheckParameters) -> CheckParameters
    # Handle dictionary based checks
    def_levels_varname = check_info[checktype].get("default_levels_variable")

    # Handle case where parameter is None but the type of the
    # default value is a dictionary. This is for example the
    # case if a check type has gotten parameters in a new version
    # but inventory of the old version left None as a parameter.
    # Also from now on we support that the inventory simply puts
    # None as a parameter. We convert that to an empty dictionary
    # that will be updated with the factory settings and default
    # levels, if possible.
    if params is None and def_levels_varname:
        fs = factory_settings.get(def_levels_varname)
        if isinstance(fs, dict):
            params = {}

    # Honor factory settings for dict-type checks. Merge
    # dict type checks with multiple matching rules
    if isinstance(params, dict):

        # Start with factory settings
        if def_levels_varname:
            new_params = factory_settings.get(def_levels_varname, {}).copy()
        else:
            new_params = {}

        # Merge user's default settings onto it
        check_context = _check_contexts[checktype]
        if def_levels_varname and def_levels_varname in check_context:
            def_levels = check_context[def_levels_varname]
            if isinstance(def_levels, dict):
                new_params.update(def_levels)

        # Merge params from inventory onto it
        new_params.update(params)
        params = new_params

    return params


def _update_with_configured_check_parameters(host, checktype, item, params):
    # type: (HostName, CheckPluginName, Item, CheckParameters) -> CheckParameters
    descr = service_description(host, checktype, item)

    config_cache = get_config_cache()

    # Get parameters configured via checkgroup_parameters
    entries = _get_checkgroup_parameters(config_cache, host, checktype, item, descr)

    # Get parameters configured via check_parameters
    entries += config_cache.service_extra_conf(host, descr, check_parameters)

    if entries:
        if _has_timespecific_params(entries):
            # some parameters include timespecific settings
            # these will be executed just before the check execution
            return TimespecificParamList(entries + [params])

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


def _has_timespecific_params(entries):
    # type: (List[CheckParameters]) -> bool
    for entry in entries:
        if isinstance(entry, dict) and "tp_default_value" in entry:
            return True
    return False


def _get_checkgroup_parameters(config_cache, host, checktype, item, descr):
    # type: (ConfigCache, HostName, CheckPluginName, Item, ServiceName) -> List[CheckParameters]
    checkgroup = check_info[checktype]["group"]
    if not checkgroup:
        return []
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
        if item is not None and not isinstance(item, six.string_types):
            item = six.text_type(item)

        # checks with an item need service-specific rules
        match_object = config_cache.ruleset_match_object_for_checkgroup_parameters(
            host, item, descr)
        return list(
            config_cache.ruleset_matcher.get_service_ruleset_values(match_object,
                                                                    rules,
                                                                    is_binary=False))
    except MKGeneralException as e:
        raise MKGeneralException(str(e) + " (on host %s, checktype %s)" % (host, checktype))


def filter_by_management_board(hostname,
                               found_check_plugin_names,
                               for_mgmt_board,
                               for_discovery=False,
                               for_inventory=False):
    # type: (HostName, Set[CheckPluginName], bool, bool, bool) -> Set[CheckPluginName]
    """
    In order to decide which check is used for which data source
    we have to filter the found check plugins. This is done via
    the check_info key "management_board". There are three values
    with the following meanings:
    - MGMT_ONLY
        These check plugins
        - are only used for management board data sources,
        - have the prefix 'mgmt_' in their name,
        - have the prefix 'Management Interface:' in their service description.
        - If there is an equivalent host check plugin then it must be 'HOST_ONLY'.

    - HOST_PRECEDENCE
        - Default value for all check plugins.
        - It does not have to be declared in the check_info.
        - Special situation for SNMP management boards:
            - If a host is not a SNMP host these checks are used for
              the SNMP management boards.
            - If a host is a SNMP host these checks are used for
              the host itself.

    - HOST_ONLY
        These check plugins
        - are used for 'real' host data sources, not for host management board data sources
        - there is an equivalent 'MGMT_ONLY'-management board check plugin.
    """

    mgmt_only, host_precedence_snmp, host_only_snmp, host_precedence_tcp, host_only_tcp =\
        _get_categorized_check_plugins(found_check_plugin_names, for_inventory=for_inventory)

    config_cache = get_config_cache()
    host_config = config_cache.get_host_config(hostname)

    final_collection = set()  # type: Set[CheckPluginName]
    if not host_config.has_management_board:
        if host_config.is_snmp_host:
            final_collection.update(host_precedence_snmp)
            final_collection.update(host_only_snmp)
        if host_config.is_agent_host:
            final_collection.update(host_precedence_tcp)
            final_collection.update(host_only_tcp)
        return final_collection

    if for_mgmt_board:
        final_collection.update(mgmt_only)
        if not host_config.is_snmp_host:
            final_collection.update(host_precedence_snmp)
            if not for_discovery:
                # Migration from 1.4 to 1.5:
                # in 1.4 TCP hosts with SNMP management boards discovered TCP and
                # SNMP checks, eg. uptime and snmp_uptime.  During checking phase
                # these checks should be executed
                # further on.
                # In versions >= 1.5 there are management board specific check
                # plugins, eg. mgmt_snmp_uptime.
                # After a re-discovery Check_MK finds the uptime check plugin for
                # the TCP host and the mgmt_snmp_uptime check for the SNMP
                # management board. Moreover Check_MK eliminates 'HOST_ONLT'
                # checks like snmp_uptime.
                final_collection.update(host_only_snmp)

    else:
        if host_config.is_snmp_host:
            final_collection.update(host_precedence_snmp)
            final_collection.update(host_only_snmp)
        if host_config.is_agent_host:
            final_collection.update(host_precedence_tcp)
            final_collection.update(host_only_tcp)

    return final_collection


def _get_categorized_check_plugins(check_plugin_names, for_inventory=False):
    # type: (Set[CheckPluginName], bool) -> Tuple[Set[CheckPluginName], Set[CheckPluginName], Set[CheckPluginName], Set[CheckPluginName], Set[CheckPluginName]]
    # Local import needed to prevent import cycle. Sorry for this hack :-/
    import cmk.base.inventory_plugins  # pylint: disable=redefined-outer-name,import-outside-toplevel

    if for_inventory:
        is_snmp_check_f = cmk.base.inventory_plugins.is_snmp_plugin
        plugins_info = cmk.base.inventory_plugins.inv_info
    else:
        is_snmp_check_f = cmk.base.check_utils.is_snmp_check
        plugins_info = check_info

    mgmt_only = set()
    host_precedence_snmp = set()
    host_precedence_tcp = set()
    host_only_snmp = set()
    host_only_tcp = set()

    for check_plugin_name in check_plugin_names:
        lookup_plugin_name = check_plugin_name
        if check_plugin_name not in plugins_info:
            # Some plugins do not properly specify a main check.
            # This is accounted for at various places, and in order to migrate to the new check API
            # we need to add this one: If we don't find the section, we just look at the first
            # matching subcheck.
            # The 'is_snmp_*' functions convert to section_name anyway, so this only affects
            # '_get_management_board_precedence'.
            for name in plugins_info:
                if cmk.base.check_utils.section_name_of(name) == check_plugin_name:
                    lookup_plugin_name = name
                    break

        if lookup_plugin_name not in plugins_info:
            msg = "Unknown plugin file %s" % check_plugin_name
            if cmk.utils.debug.enabled():
                raise MKGeneralException(msg)
            console.verbose("%s\n" % msg)
            continue

        is_snmp_check_ = is_snmp_check_f(lookup_plugin_name)
        mgmt_board = _get_management_board_precedence(lookup_plugin_name, plugins_info)
        if mgmt_board == check_api_utils.HOST_PRECEDENCE:
            if is_snmp_check_:
                host_precedence_snmp.add(check_plugin_name)
            else:
                host_precedence_tcp.add(check_plugin_name)

        elif mgmt_board == check_api_utils.MGMT_ONLY:
            mgmt_only.add(check_plugin_name)

        elif mgmt_board == check_api_utils.HOST_ONLY:
            if is_snmp_check_:
                host_only_snmp.add(check_plugin_name)
            else:
                host_only_tcp.add(check_plugin_name)

    return mgmt_only, host_precedence_snmp, host_only_snmp,\
           host_precedence_tcp, host_only_tcp


def _get_management_board_precedence(check_plugin_name, plugins_info):
    # type: (CheckPluginName, CheckInfo) -> str
    mgmt_board = plugins_info[check_plugin_name].get("management_board")
    if mgmt_board is None:
        return check_api_utils.HOST_PRECEDENCE
    return mgmt_board


cmk.base.cleanup.register_cleanup(check_api_utils.reset_hostname)

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


class HostConfig(object):  # pylint: disable=useless-object-inheritance
    def __init__(self, config_cache, hostname):
        # type: (ConfigCache, str) -> None
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
        self.is_tcp_host = self._config_cache.in_binary_hostlist(hostname, tcp_hosts)  # type: bool
        self.is_snmp_host = self._config_cache.in_binary_hostlist(hostname,
                                                                  snmp_hosts)  # type: bool
        self.is_usewalk_host = self._config_cache.in_binary_hostlist(hostname,
                                                                     usewalk_hosts)  # type: bool

        if self.tag_groups["piggyback"] == "piggyback":
            self.is_piggyback_host = True
        elif self.tag_groups["piggyback"] == "no-piggyback":
            self.is_piggyback_host = False
        else:  # Legacy automatic detection
            self.is_piggyback_host = self.has_piggyback_data

        # Agent types
        self.is_agent_host = self.is_tcp_host or self.is_piggyback_host  # type: bool
        self.management_protocol = management_protocol.get(hostname)
        self.has_management_board = self.management_protocol is not None  # type: bool

        self.is_ping_host = not self.is_snmp_host and\
                            not self.is_agent_host and\
                            not self.has_management_board

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
        self.is_ipv4_host = "ip-v4" in self.tag_groups \
                or (not self.is_ipv6_host and not self.is_no_ip_host)

        self.is_ipv4v6_host = "ip-v6" in self.tag_groups and "ip-v4" in self.tag_groups

        # Whether or not the given host is configured to be monitored primarily via IPv6
        self.is_ipv6_primary = (not self.is_ipv4v6_host and self.is_ipv6_host) \
                                or (self.is_ipv4v6_host and self._primary_ip_address_family_of() == "ipv6")

    @property
    def has_piggyback_data(self):
        # type: () -> bool
        time_settings = self.piggybacked_host_files  # type: List[Tuple[Optional[str], str, int]]
        time_settings.append((None, "max_cache_age", piggyback_max_cachefile_age))

        if piggyback.has_piggyback_raw_data(self.hostname, time_settings):
            return True

        return Path(cmk.utils.paths.var_dir, "persisted_sections", "piggyback",
                    self.hostname).exists()

    @property
    def piggybacked_host_files(self):
        # type: () -> List[Tuple[Optional[str], str, int]]
        rules = self._config_cache.host_extra_conf(self.hostname, piggybacked_host_files)
        if rules:
            return self._flatten_piggybacked_host_files_rule(rules[0])
        return []

    def _flatten_piggybacked_host_files_rule(self, rule):
        # type: (Dict[str, Any]) -> List[Tuple[Optional[str], str, int]]
        """This rule is a first match rule.

        Max cache age, validity period and state are configurable wihtin this
        rule for all piggybacked host or per piggybacked host of this source.
        In order to differentiate later for which piggybacked hosts a parameter
        is used we flat this rule to a homogeneous data structure:
            (HOST, KEY): VALUE
        Then piggyback.py:_get_piggyback_processed_file_info can evaluate the
        parameters generically."""
        flat_rule = []  # type: List[Tuple[Optional[str], str, int]]

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
    def check_mk_check_interval(self):
        # type: () -> int
        return self._config_cache.extra_attributes_of_service(self.hostname,
                                                              'Check_MK')['check_interval']

    def _primary_ip_address_family_of(self):
        # type: () -> str
        rules = self._config_cache.host_extra_conf(self.hostname, primary_address_family)
        if rules:
            return rules[0]
        return "ipv4"

    @property
    def alias(self):
        # type: () -> Text

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
    def parents(self):
        # type: () -> List[str]
        """Returns the parents of a host configured via ruleset "parents"

        Use only those parents which are defined and active in all_hosts"""
        used_parents = []

        # Respect the ancient parents ruleset. This can not be configured via WATO and should be removed one day
        for parent_names in self._config_cache.host_extra_conf(self.hostname, parents):
            for parent_name in parent_names.split(","):
                if parent_name in self._config_cache.all_active_realhosts():
                    used_parents.append(parent_name)

        return used_parents

    def snmp_config(self, ipaddress):
        # type: (HostAddress) -> cmk.base.snmp_utils.SNMPHostConfig
        return cmk.base.snmp_utils.SNMPHostConfig(
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
            is_inline_snmp_host=self._is_inline_snmp_host(),
        )

    def _snmp_credentials(self):
        # type: () -> SNMPCredentials
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

    def snmp_credentials_of_version(self, snmp_version):
        # type: (int) -> Optional[SNMPCredentials]
        for entry in self._config_cache.host_extra_conf(self.hostname, snmp_communities):
            if snmp_version == 3 and not isinstance(entry, tuple):
                continue

            if snmp_version != 3 and isinstance(entry, tuple):
                continue

            return entry

        return None

    def _snmp_port(self):
        # type: () -> int
        ports = self._config_cache.host_extra_conf(self.hostname, snmp_ports)
        if not ports:
            return 161
        return ports[0]

    def _snmp_timing(self):
        # type: () -> cmk.base.snmp_utils.SNMPTiming
        timing = self._config_cache.host_extra_conf(self.hostname, snmp_timing)
        if not timing:
            return {}
        return timing[0]

    def _bulk_walk_size(self):
        # type: () -> int
        bulk_sizes = self._config_cache.host_extra_conf(self.hostname, snmp_bulk_size)
        if not bulk_sizes:
            return 10
        return bulk_sizes[0]

    def _snmp_character_encoding(self):
        # type: () -> Optional[str]
        entries = self._config_cache.host_extra_conf(self.hostname, snmp_character_encodings)
        if not entries:
            return None
        return entries[0]

    def _is_inline_snmp_host(self):
        # type: () -> bool
        # TODO: Better use "inline_snmp" once we have moved the code to an own module
        has_inline_snmp = "netsnmp" in sys.modules
        return has_inline_snmp and use_inline_snmp \
               and not self._config_cache.in_binary_hostlist(self.hostname, non_inline_snmp_hosts)

    def _is_cluster(self):
        # type: () -> bool
        """Checks whether or not the given host is a cluster host
        all_configured_clusters() needs to be used, because this function affects
        the agent bakery, which needs all configured hosts instead of just the hosts
        of this site"""
        return self.hostname in self._config_cache.all_configured_clusters()

    def snmp_check_interval(self, section_name):
        # type: (str) -> Optional[int]
        """Return the check interval of SNMP check sections

        This has been added to reduce the check interval of single SNMP checks (or
        more precise: sections) to be executed less frequent that the "Check_MK"
        service is executed.
        """
        if not cmk.base.check_utils.is_snmp_check(section_name):
            return None  # no values at all for non snmp checks

        # Previous to 1.5 "match" could be a check name (including subchecks) instead of
        # only main check names -> section names. This has been cleaned up, but we still
        # need to be compatible. Strip of the sub check part of "match".
        for match, minutes in self._config_cache.host_extra_conf(self.hostname,
                                                                 snmp_check_interval):
            if match is None or match.split(".")[0] == section_name:
                return minutes  # use first match

        return None

    @property
    def agent_port(self):
        # type: () -> int
        ports = self._config_cache.host_extra_conf(self.hostname, agent_ports)
        if not ports:
            return agent_port

        return ports[0]

    @property
    def tcp_connect_timeout(self):
        # type: () -> float
        timeouts = self._config_cache.host_extra_conf(self.hostname, tcp_connect_timeouts)
        if not timeouts:
            return tcp_connect_timeout

        return timeouts[0]

    @property
    def agent_encryption(self):
        # type: () -> Dict[str, str]
        settings = self._config_cache.host_extra_conf(self.hostname, agent_encryption)
        if not settings:
            return {'use_regular': 'disable', 'use_realtime': 'enforce'}
        return settings[0]

    @property
    def agent_target_version(self):
        # type: () -> AgentTargetVersion
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
    def datasource_program(self):
        # type: () -> Optional[str]
        """Return the command line to execute instead of contacting the agent

        In case no datasource program is configured for a host return None
        """
        programs = self._config_cache.host_extra_conf(self.hostname, datasource_programs)
        if not programs:
            return None

        return programs[0]

    @property
    def special_agents(self):
        # type: () -> List[Tuple[str, Dict]]
        matched = []  # type: List[Tuple[str, Dict]]
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
    def only_from(self):
        # type: () -> Union[None, List[str], str]
        """The agent of a host may be configured to be accessible only from specific IPs"""
        ruleset = agent_config.get("only_from", [])
        if not ruleset:
            return None

        entries = self._config_cache.host_extra_conf(self.hostname, ruleset)
        if not entries:
            return None

        return entries[0]

    @property
    def explicit_check_command(self):
        # type: () -> HostCheckCommand
        entries = self._config_cache.host_extra_conf(self.hostname, host_check_commands)
        if not entries:
            return None

        if entries[0] == "smart" and monitoring_core != "cmc":
            return "ping"  # avoid problems when switching back to nagios core

        return entries[0]

    @property
    def ping_levels(self):
        # type: () -> PingLevels
        levels = {}  # type: PingLevels

        values = self._config_cache.host_extra_conf(self.hostname, ping_levels)
        # TODO: Use host_extra_conf_merged?)
        for value in values[::-1]:  # make first rules have precedence
            levels.update(value)

        return levels

    @property
    def icons_and_actions(self):
        # type: () -> List[str]
        return list(set(self._config_cache.host_extra_conf(self.hostname, host_icons_and_actions)))

    @property
    def extra_host_attributes(self):
        # type: () -> ObjectAttributes
        attrs = {}  # type: ObjectAttributes
        attrs.update(self._explicit_host_attributes)

        for key, ruleset in extra_host_conf.items():
            if key in attrs:
                # An explicit value is already set
                values = [attrs[key]]
            else:
                values = self._config_cache.host_extra_conf(self.hostname, ruleset)

            if values:
                if key[0] == "_":
                    key = key.upper()

                if values[0] is not None:
                    attrs[key] = values[0]

        return attrs

    @property
    def _explicit_host_attributes(self):
        # type: () -> ObjectAttributes
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
    def discovery_check_parameters(self):
        # type: () -> Optional[DiscoveryCheckParameters]
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

    def default_discovery_check_parameters(self):
        # type: () -> DiscoveryCheckParameters
        """Support legacy single value global configurations. Otherwise return the defaults"""
        return {
            "check_interval": inventory_check_interval,
            "severity_unmonitored": inventory_check_severity,
            "severity_vanished": 0,
            "inventory_check_do_scan": inventory_check_do_scan,
        }

    def add_service_discovery_check(self, params, service_discovery_name):
        # type: (Optional[Dict[Text, Any]], Text) -> bool
        if not params:
            return False

        if not params["check_interval"]:
            return False

        if service_ignored(self.hostname, None, service_discovery_name):
            return False

        if self.is_ping_host:
            return False

        return True

    def inventory_parameters(self, section_name):
        # type: (str) -> Dict
        return self._config_cache.host_extra_conf_merged(self.hostname,
                                                         inv_parameters.get(section_name, []))

    @property
    def inventory_export_hooks(self):
        # type: () -> List[Tuple[str, Dict]]
        hooks = []  # type: List[Tuple[str, Dict]]
        for hookname, ruleset in sorted(inv_exports.items(), key=lambda x: x[0]):
            entries = self._config_cache.host_extra_conf(self.hostname, ruleset)
            if entries:
                hooks.append((hookname, entries[0]))
        return hooks

    def notification_plugin_parameters(self, plugin_name):
        # type: (CheckPluginName) -> Dict
        return self._config_cache.host_extra_conf_merged(
            self.hostname, notification_parameters.get(plugin_name, []))

    @property
    def active_checks(self):
        # type: () -> List[Tuple[str, List[Any]]]
        """Returns the list of active checks configured for this host

        These are configured using the active check formalization of WATO
        where the whole parameter set is configured using valuespecs.
        """
        configured_checks = []  # type: List[Tuple[str, List[Any]]]
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
    def custom_checks(self):
        # type: () -> List[Dict]
        """Return the free form configured custom checks without formalization"""
        return self._config_cache.host_extra_conf(self.hostname, custom_checks)

    @property
    def static_checks(self):
        # type: () -> List[Tuple[RulesetName, CheckPluginName, Item, CheckParameters]]
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
    def hostgroups(self):
        # type: () -> List[HostgroupName]
        """Returns the list of hostgroups of this host

        If the host has no hostgroups it will be added to the default hostgroup
        (Nagios requires each host to be member of at least on group)."""
        groups = self._config_cache.host_extra_conf(self.hostname, host_groups)
        if not groups:
            return [default_host_group]
        return groups

    @property
    def contactgroups(self):
        # type: () -> List[ContactgroupName]
        """Returns the list of contactgroups of this host"""
        cgrs = []  # type: List[ContactgroupName]

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
    def management_address(self):
        # type: () -> Optional[HostAddress]
        attributes_of_host = host_attributes.get(self.hostname, {})
        if attributes_of_host.get("management_address"):
            return attributes_of_host["management_address"]

        return ipaddresses.get(self.hostname)

    @property
    def management_credentials(self):
        # type: () -> Optional[ManagementCredentials]
        protocol = self.management_protocol
        default_value = None  # type: Optional[ManagementCredentials]
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
    def management_snmp_config(self):
        # type: () -> cmk.base.snmp_utils.SNMPHostConfig
        if self.management_protocol != "snmp":
            raise MKGeneralException("Management board is not configured to be contacted via SNMP")

        address = self.management_address
        if address is None:
            raise MKGeneralException("Management board address is not configured")

        return cmk.base.snmp_utils.SNMPHostConfig(
            is_ipv6_primary=self.is_ipv6_primary,
            hostname=self.hostname,
            ipaddress=address,
            credentials=cast(SNMPCredentials, self.management_credentials),
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
            is_inline_snmp_host=self._is_inline_snmp_host(),
        )

    @property
    def additional_ipaddresses(self):
        # type: () -> Tuple[List[HostAddress], List[HostAddress]]
        #TODO Regarding the following configuration variables from WATO
        # there's no inheritance, thus we use 'host_attributes'.
        # Better would be to use cmk.base configuration variables,
        # eg. like 'management_protocol'.
        return (host_attributes.get(self.hostname, {}).get("additional_ipv4addresses", []),
                host_attributes.get(self.hostname, {}).get("additional_ipv6addresses", []))

    def exit_code_spec(self, data_source_id=None):
        # type: (Optional[str]) -> ExitSpec
        spec = {}  # type: ExitSpec
        # TODO: Can we use host_extra_conf_merged?
        specs = self._config_cache.host_extra_conf(self.hostname, check_mk_exit_status)
        for entry in specs[::-1]:
            spec.update(entry)
        return self._merge_with_data_source_exit_code_spec(spec, data_source_id)

    def _merge_with_data_source_exit_code_spec(self, spec, data_source_id):
        # type: (Dict, Optional[str]) -> ExitSpec
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

    @property
    def do_status_data_inventory(self):
        # type: () -> bool

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
    def service_level(self):
        # type: () -> Optional[int]
        entries = self._config_cache.host_extra_conf(self.hostname, host_service_levels)
        if not entries:
            return None
        return entries[0]

    def set_autochecks(self, new_items):
        # type: (List[DiscoveredService]) -> None
        """Merge existing autochecks with the given autochecks for a host and save it"""
        if self.is_cluster:
            if self.nodes:
                autochecks.set_autochecks_of_cluster(self.nodes, self.hostname, new_items,
                                                     self._config_cache.host_of_clustered_service,
                                                     service_description)
        else:
            autochecks.set_autochecks_of_real_hosts(self.hostname, new_items, service_description)

    def remove_autochecks(self):
        # type: () -> int
        """Remove all autochecks of a host while being cluster-aware

        Cluster aware means that the autocheck files of the nodes are handled. Instead
        of removing the whole file the file is loaded and only the services associated
        with the given cluster are removed."""
        hostnames = self.nodes if self.nodes else [self.hostname]
        return sum(
            autochecks.remove_autochecks_of_host(
                hostname, self._config_cache.host_of_clustered_service, service_description)  #
            for hostname in hostnames)


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
class ConfigCache(object):  # pylint: disable=useless-object-inheritance
    def __init__(self):
        # type: () -> None
        super(ConfigCache, self).__init__()
        self._initialize_caches()

    def initialize(self):
        # type: () -> None
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
            host_tag_lists=self._hosttags,
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

    def _initialize_caches(self):
        # type: () -> None
        self.check_table_cache = _config_cache.get_dict("check_tables")

        self._cache_is_snmp_check = _runtime_cache.get_dict("is_snmp_check")
        self._cache_is_tcp_check = _runtime_cache.get_dict("is_tcp_check")
        self._cache_section_name_of = {}  # type: Dict[CheckPluginName, SectionName]

        self._cache_match_object_service = {
        }  # type: Dict[Tuple[HostName, ServiceName], RulesetMatchObject]
        self._cache_match_object_service_checkgroup = {
        }  # type: Dict[Tuple[HostName, Item, ServiceName], RulesetMatchObject]
        self._cache_match_object_host = {}  # type: Dict[HostName, RulesetMatchObject]

        # Host lookup

        self._all_configured_hosts = set()
        self._all_configured_clusters = set()
        self._all_configured_realhosts = set()
        self._all_active_clusters = set()
        self._all_active_realhosts = set()

        # Reference hostname -> dirname including /
        self._host_paths = self._get_host_paths(host_paths)  # type: Dict[HostName, str]

        # Host tags
        self._hosttags = {}  # type: Dict[HostName, TagList]

        # Autochecks cache
        self._autochecks_manager = autochecks.AutochecksManager()

        # Caches for nodes and clusters
        self._clusters_of_cache = {}  # type: Dict[HostName, List[HostName]]
        self._nodes_of_cache = {}  # type: Dict[HostName, List[HostName]]

        # Keep HostConfig instances created with the current configuration cache
        self._host_configs = {}  # type: Dict[HostName, HostConfig]

    def _discovered_labels_of_service(self, hostname, service_desc):
        # type: (HostName, ServiceName) -> Labels
        return self._autochecks_manager.discovered_labels_of(hostname, service_desc,
                                                             service_description,
                                                             get_check_variables).to_dict()

    def get_tag_to_group_map(self):
        # type: () -> TagGroups
        tags = cmk.utils.tags.get_effective_tag_config(tag_config)
        return ruleset_matcher.get_tag_to_group_map(tags)

    def get_host_config(self, hostname):
        # type: (HostName) -> HostConfig
        """Returns a HostConfig instance for the given host

        It lazy initializes the host config object and caches the objects during the livetime
        of the ConfigCache."""
        host_config = self._host_configs.get(hostname)
        if host_config:
            return host_config

        config_class = HostConfig if cmk_version.is_raw_edition() else CEEHostConfig
        host_config = self._host_configs[hostname] = config_class(self, hostname)
        return host_config

    def invalidate_host_config(self, hostname):
        # type: (HostName) -> None
        try:
            del self._host_configs[hostname]
        except KeyError:
            pass

    def _get_host_paths(self, config_host_paths):
        # type: (Dict[HostName, str]) -> Dict[HostName, str]
        """Reference hostname -> dirname including /"""
        host_dirs = {}
        for hostname, filename in config_host_paths.items():
            dirname_of_host = os.path.dirname(filename)
            if dirname_of_host[-1] != "/":
                dirname_of_host += "/"
            host_dirs[hostname] = dirname_of_host
        return host_dirs

    def host_path(self, hostname):
        # type: (HostName) -> str
        return self._host_paths.get(hostname, "/")

    def _collect_hosttags(self, tag_to_group_map):
        # type: (TagGroups) -> None
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

    def _tag_groups_to_tag_list(self, host_path, tag_groups):
        # type: (str, Dict[str, str]) -> Set[str]
        # The pre 1.6 tags contained only the tag group values (-> chosen tag id),
        # but there was a single tag group added with it's leading tag group id. This
        # was the internal "site" tag that is created by HostAttributeSite.
        tags = set(v for k, v in tag_groups.items() if k != "site")
        tags.add(host_path)
        tags.add("site:%s" % tag_groups["site"])
        return tags

    def _tag_list_to_tag_groups(self, tag_to_group_map, tag_list):
        # type: (TagGroups, TagList) -> Tags
        # This assumes all needed aux tags of grouped are already in the tag_list

        # Ensure the internal mandatory tag groups are set for all hosts
        # TODO: This immitates the logic of cmk.gui.watolib.CREHost.tag_groups which
        # is currently responsible for calculating the host tags of a host.
        # Would be better to untie the GUI code there and move it over to cmk.utils.tags.
        tag_groups = {
            'piggyback': 'auto-piggyback',
            'networking': 'lan',
            'agent': 'cmk-agent',
            'criticality': 'prod',
            'snmp_ds': 'no-snmp',
            'site': cmk_version.omd_site(),
            'address_family': 'ip-v4-only',
        }  # type: Tags

        for tag_id in tag_list:
            # Assume it's an aux tag in case there is a tag configured without known group
            tag_group_id = tag_to_group_map.get(tag_id, tag_id)
            tag_groups[tag_group_id] = tag_id

        return tag_groups

    # Kept for compatibility with pre 1.6 sites
    # TODO: Clean up all call sites one day (1.7?)
    # TODO: check all call sites and remove this
    def tag_list_of_host(self, hostname):
        # type: (HostName) -> Set[TagValue]
        """Returns the list of all configured tags of a host. In case
        a host has no tags configured or is not known, it returns an
        empty list."""
        if hostname in self._hosttags:
            return self._hosttags[hostname]

        # Handle not existing hosts (No need to performance optimize this)
        return self._tag_groups_to_tag_list("/", self.tags_of_host(hostname))

    # TODO: check all call sites and remove this or make it private?
    def tags_of_host(self, hostname):
        # type: (HostName) -> Tags
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

    def tags_of_service(self, hostname, svc_desc):
        # type: (HostName, ServiceName) -> Tags
        """Returns the dict of all configured tags of a service
        It takes all explicitly configured tag groups into account.
        """
        tags = {}  # type: Tags
        for entry in self.service_extra_conf(hostname, svc_desc, service_tag_rules):
            tags.update(entry)
        return tags

    def labels_of_service(self, hostname, svc_desc):
        # type: (HostName, ServiceName) -> Labels
        """Returns the effective set of service labels from all available sources

        1. Discovered labels
        2. Ruleset "Service labels"

        Last one wins.
        """
        return self.labels.labels_of_service(self.ruleset_matcher, hostname, svc_desc)

    def label_sources_of_service(self, hostname, svc_desc):
        # type: (HostName, ServiceName) -> LabelSources
        """Returns the effective set of service label keys with their source identifier instead of the value
        Order and merging logic is equal to labels_of_service()"""
        return self.labels.label_sources_of_service(self.ruleset_matcher, hostname, svc_desc)

    def extra_attributes_of_service(self, hostname, description):
        # type: (HostName, ServiceName) -> Dict[str, Any]
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

    def icons_and_actions_of_service(self, hostname, description, checkname, params):
        # type: (HostName, ServiceName, Optional[CheckPluginName], CheckParameters) -> List[str]
        actions = set(self.service_extra_conf(hostname, description, service_icons_and_actions))

        # Some WATO rules might register icons on their own
        if checkname:
            checkgroup = check_info[checkname]["group"]
            if checkgroup in ['ps', 'services'] and isinstance(params, dict):
                icon = params.get('icon')
                if icon:
                    actions.add(icon)

        return list(actions)

    def servicegroups_of_service(self, hostname, description):
        # type: (HostName, ServiceName) -> List[ServicegroupName]
        """Returns the list of servicegroups of this services"""
        return self.service_extra_conf(hostname, description, service_groups)

    def contactgroups_of_service(self, hostname, description):
        # type: (HostName, ServiceName) -> List[str]
        """Returns the list of contactgroups of this service"""
        cgrs = set()  # type: Set[str]
        cgrs.update(self.service_extra_conf(hostname, description, service_contactgroups))

        if monitoring_core == "nagios" and enable_rulebased_notifications:
            cgrs.add("check-mk-notify")

        return list(cgrs)

    def passive_check_period_of_service(self, hostname, description):
        # type: (HostName, ServiceName) -> str
        return self.get_service_ruleset_value(hostname, description, check_periods, deflt="24X7")

    def custom_attributes_of_service(self, hostname, description):
        # type: (HostName, ServiceName) -> Dict[str, str]
        return dict(
            itertools.chain(
                *self.service_extra_conf(hostname, description, custom_service_attributes)))

    def service_level_of_service(self, hostname, description):
        # type: (HostName, ServiceName) -> Optional[int]
        return self.get_service_ruleset_value(hostname,
                                              description,
                                              service_service_levels,
                                              deflt=None)

    def check_period_of_service(self, hostname, description):
        # type: (HostName, ServiceName) -> Optional[TimeperiodName]
        entry = self.get_service_ruleset_value(hostname, description, check_periods, deflt=None)
        if entry == "24X7":
            return None
        return entry

    def get_explicit_service_custom_variables(self, hostname, description):
        # type: (HostName, ServiceName) -> Dict[str, str]
        try:
            return explicit_service_custom_variables[(hostname, description)]
        except KeyError:
            return {}

    def ruleset_match_object_of_service(self, hostname, svc_desc):
        # type: (HostName, ServiceName) -> RulesetMatchObject
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

        result = RulesetMatchObject(host_name=hostname,
                                    service_description=svc_desc,
                                    service_labels=self.labels.labels_of_service(
                                        self.ruleset_matcher, hostname, svc_desc))
        self._cache_match_object_service[cache_id] = result
        return result

    def ruleset_match_object_for_checkgroup_parameters(self, hostname, item, svc_desc):
        # type: (HostName, Item, ServiceName) -> RulesetMatchObject
        """Construct the object that is needed to match checkgroup parameters rulesets

        Please note that the host attributes like host_folder and host_tags are
        not set in the object, because the rule optimizer already processes all
        these host conditions. Adding these attributes here would be
        consequent, but create some overhead.
        """

        cache_id = (hostname, item, svc_desc)
        if cache_id in self._cache_match_object_service_checkgroup:
            return self._cache_match_object_service_checkgroup[cache_id]

        result = RulesetMatchObject(host_name=hostname,
                                    service_description=item,
                                    service_labels=self.labels.labels_of_service(
                                        self.ruleset_matcher, hostname, svc_desc))
        self._cache_match_object_service_checkgroup[cache_id] = result
        return result

    def ruleset_match_object_of_host(self, hostname):
        # type: (HostName) -> RulesetMatchObject
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

    def get_autochecks_of(self, hostname):
        # type: (HostName) -> List[cmk.base.check_utils.Service]
        return self._autochecks_manager.get_autochecks_of(hostname, compute_check_parameters,
                                                          service_description, get_check_variables)

    def section_name_of(self, section):
        # type: (CheckPluginName) -> SectionName
        try:
            return self._cache_section_name_of[section]
        except KeyError:
            section_name = cmk.base.check_utils.section_name_of(section)
            self._cache_section_name_of[section] = section_name
            return section_name

    def is_snmp_check(self, check_plugin_name):
        # type: (CheckPluginName) -> bool
        try:
            return self._cache_is_snmp_check[check_plugin_name]
        except KeyError:
            snmp_checks = _runtime_cache.get_set("check_type_snmp")
            result = self.section_name_of(check_plugin_name) in snmp_checks
            self._cache_is_snmp_check[check_plugin_name] = result
            return result

    def is_tcp_check(self, check_plugin_name):
        # type: (CheckPluginName) -> bool
        try:
            return self._cache_is_tcp_check[check_plugin_name]
        except KeyError:
            tcp_checks = _runtime_cache.get_set("check_type_tcp")
            result = self.section_name_of(check_plugin_name) in tcp_checks
            self._cache_is_tcp_check[check_plugin_name] = result
            return result

    def host_extra_conf_merged(self, hostname, ruleset):
        # type: (HostName, Ruleset) -> Dict[str, Any]
        return self.ruleset_matcher.get_host_ruleset_merged_dict(
            self.ruleset_match_object_of_host(hostname), ruleset)

    def host_extra_conf(self, hostname, ruleset):
        # type: (HostName, Ruleset) -> List
        return list(
            self.ruleset_matcher.get_host_ruleset_values(
                self.ruleset_match_object_of_host(hostname), ruleset, is_binary=False))

    # TODO: Cleanup external in_binary_hostlist call sites
    def in_binary_hostlist(self, hostname, ruleset):
        # type: (HostName, Ruleset) -> bool
        return self.ruleset_matcher.is_matching_host_ruleset(
            self.ruleset_match_object_of_host(hostname), ruleset)

    def service_extra_conf(self, hostname, description, ruleset):
        # type: (HostName, ServiceName, Ruleset) -> List
        """Compute outcome of a service rule set that has an item."""
        return list(
            self.ruleset_matcher.get_service_ruleset_values(self.ruleset_match_object_of_service(
                hostname, description),
                                                            ruleset,
                                                            is_binary=False))

    def get_service_ruleset_value(self, hostname, description, ruleset, deflt):
        # type: (HostName, ServiceName, Ruleset, Any) -> Any
        """Compute first match service ruleset outcome with fallback to a default value"""
        return next(
            self.ruleset_matcher.get_service_ruleset_values(self.ruleset_match_object_of_service(
                hostname, description),
                                                            ruleset,
                                                            is_binary=False), deflt)

    def service_extra_conf_merged(self, hostname, description, ruleset):
        # type: (HostName, ServiceName, Ruleset) -> Dict[str, Any]
        return self.ruleset_matcher.get_service_ruleset_merged_dict(
            self.ruleset_match_object_of_service(hostname, description), ruleset)

    def in_boolean_serviceconf_list(self, hostname, description, ruleset):
        # type: (HostName, ServiceName, Ruleset) -> bool
        """Compute outcome of a service rule set that just say yes/no"""
        return self.ruleset_matcher.is_matching_service_ruleset(
            self.ruleset_match_object_of_service(hostname, description), ruleset)

    def all_active_hosts(self):
        # type: () -> Set[HostName]
        """Returns a set of all active hosts"""
        return self._all_active_hosts

    def _get_all_active_hosts(self):
        # type: () -> Set[HostName]
        hosts = set()  # type: Set[HostName]
        hosts.update(self.all_active_realhosts(), self.all_active_clusters())
        return hosts

    def all_active_realhosts(self):
        # type: () -> Set[HostName]
        """Returns a set of all host names to be handled by this site hosts of other sites or disabled hosts are excluded"""
        return self._all_active_realhosts

    def _get_all_active_realhosts(self):
        # type: () -> Set[HostName]
        return set(_filter_active_hosts(self, self._all_configured_realhosts))

    def all_configured_realhosts(self):
        # type: () -> Set[HostName]
        return self._all_configured_realhosts

    def _get_all_configured_realhosts(self):
        # type: () -> Set[HostName]
        """Returns a set of all host names, regardless if currently disabled or
        monitored on a remote site. Does not return cluster hosts."""
        return set(strip_tags(all_hosts))

    def _get_all_configured_shadow_hosts(self):
        # type: () -> Set[HostName]
        """Returns a set of all shadow host names, regardless if currently disabled or
        monitored on a remote site"""
        return set(_get_shadow_hosts())

    def all_configured_hosts(self):
        # type: () -> Set[HostName]
        return self._all_configured_hosts

    def _get_all_configured_hosts(self):
        # type: () -> Set[HostName]
        """Returns a set of all hosts, regardless if currently disabled or monitored on a remote site."""
        hosts = set()  # type: Set[HostName]
        hosts.update(self.all_configured_realhosts(), self.all_configured_clusters(),
                     self._get_all_configured_shadow_hosts())
        return hosts

    def _setup_clusters_nodes_cache(self):
        # type: () -> None
        for cluster, hosts in clusters.items():
            clustername = cluster.split('|', 1)[0]
            for name in hosts:
                self._clusters_of_cache.setdefault(name, []).append(clustername)
            self._nodes_of_cache[clustername] = hosts

    def clusters_of(self, hostname):
        # type: (str) -> List[HostName]
        """Returns names of cluster hosts the host is a node of"""
        return self._clusters_of_cache.get(hostname, [])

    # TODO: cleanup None case
    def nodes_of(self, hostname):
        # type: (str) -> Optional[List[HostName]]
        """Returns the nodes of a cluster. Returns None if no match.

        Use host_config.nodes instead of this method to get the node list"""
        return self._nodes_of_cache.get(hostname)

    def all_active_clusters(self):
        # type: () -> Set[HostName]
        """Returns a set of all cluster host names to be handled by this site hosts of other sites or disabled hosts are excluded"""
        return self._all_active_clusters

    def _get_all_active_clusters(self):
        # type: () -> Set[HostName]
        return set(_filter_active_hosts(self, self.all_configured_clusters()))

    def all_configured_clusters(self):
        # type: () -> Set[HostName]
        """Returns a set of all cluster names
        Regardless if currently disabled or monitored on a remote site. Does not return normal hosts.
        """
        return self._all_configured_clusters

    def _get_all_configured_clusters(self):
        # type: () -> Set[HostName]
        return set(strip_tags(list(clusters)))

    def host_of_clustered_service(self, hostname, servicedesc, part_of_clusters=None):
        # type: (HostName, Text, Optional[List[str]]) -> str
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
            if hostname in nodes and \
                self.in_boolean_serviceconf_list(hostname, servicedesc, conf):
                return cluster

        # 1. Old style: clustered_services assumes that each host belong to
        #    exactly on cluster
        if self.in_boolean_serviceconf_list(hostname, servicedesc, clustered_services):
            return the_clusters[0]

        return hostname

    def get_piggybacked_hosts_time_settings(self, piggybacked_hostname=None):
        # type: (Optional[HostName]) -> List[Tuple[Optional[str], str, int]]
        time_settings = []  # type: List[Tuple[Optional[str], str, int]]
        for source_hostname in sorted(piggyback.get_source_hostnames(piggybacked_hostname)):
            time_settings.extend(self.get_host_config(source_hostname).piggybacked_host_files)

        # From global settings
        time_settings.append((None, 'max_cache_age', piggyback_max_cachefile_age))
        return time_settings

    # TODO: Remove old name one day
    def service_discovery_name(self):
        # type: () -> ServiceName
        if 'cmk-inventory' in use_new_descriptions_for:
            return u'Check_MK Discovery'
        return u'Check_MK inventory'


def get_config_cache():
    # type: () -> ConfigCache
    config_cache = _config_cache.get_dict("config_cache")
    if not config_cache:
        cache_class = ConfigCache if cmk_version.is_raw_edition() else CEEConfigCache
        config_cache["cache"] = cache_class()
    return config_cache["cache"]


# TODO: Find a clean way to move this to cmk.base.cee. This will be possible once the
# configuration settings are not held in cmk.base.config namespace anymore.
class CEEConfigCache(ConfigCache):
    """Encapsulates the CEE specific functionality"""
    def rrd_config_of_service(self, hostname, description):
        # type: (HostName, ServiceName) -> Optional[RRDConfig]
        return self.get_service_ruleset_value(hostname,
                                              description,
                                              cmc_service_rrd_config,
                                              deflt=None)

    def recurring_downtimes_of_service(self, hostname, description):
        # type: (HostName, ServiceName) -> List[RecurringDowntime]
        return self.service_extra_conf(hostname, description, service_recurring_downtimes)  # type: ignore[name-defined] # pylint: disable=undefined-variable

    def flap_settings_of_service(self, hostname, description):
        # type: (HostName, ServiceName) -> Tuple[float, float, float]
        return self.get_service_ruleset_value(
            hostname,
            description,
            cmc_service_flap_settings,  # type: ignore[name-defined] # pylint: disable=undefined-variable
            deflt=cmc_flap_settings)  # type: ignore[name-defined] # pylint: disable=undefined-variable

    def log_long_output_of_service(self, hostname, description):
        # type: (HostName, ServiceName) -> bool
        return self.get_service_ruleset_value(
            hostname,
            description,
            cmc_service_long_output_in_monitoring_history,  # type: ignore[name-defined] # pylint: disable=undefined-variable
            deflt=False)

    def state_translation_of_service(self, hostname, description):
        # type: (HostName, ServiceName) -> Dict
        entries = self.service_extra_conf(hostname, description, service_state_translation)  # type: ignore[name-defined] # pylint: disable=undefined-variable

        spec = {}  # type: Dict
        for entry in entries[::-1]:
            spec.update(entry)
        return spec

    def check_timeout_of_service(self, hostname, description):
        # type: (HostName, ServiceName) -> int
        """Returns the check timeout in seconds"""
        return self.get_service_ruleset_value(
            hostname,
            description,
            cmc_service_check_timeout,  # type: ignore[name-defined] # pylint: disable=undefined-variable
            deflt=cmc_check_timeout)  # type: ignore[name-defined] # pylint: disable=undefined-variable

    def graphite_metrics_of_service(self, hostname, description):
        # type: (HostName, ServiceName) -> Optional[List[str]]
        return self.get_service_ruleset_value(
            hostname,
            description,
            cmc_graphite_service_metrics,  # type: ignore[name-defined] # pylint: disable=undefined-variable
            deflt=None)

    def matched_agent_config_entries(self, hostname):
        # type: (Union[bool, HostName]) -> Dict[str, Any]
        matched = {}
        for varname, ruleset in list(agent_config.items()) + [("agent_port", agent_ports),
                                                              ("agent_encryption", agent_encryption)
                                                             ]:
            # mypy compatible check of cmk.base.cee.agent_bakyery.GENERIC_AGENT
            # GENERIC_AGENT = True
            if isinstance(hostname, bool):
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
    def rrd_config(self):
        # type: () -> Optional[RRDConfig]
        entries = self._config_cache.host_extra_conf(self.hostname, cmc_host_rrd_config)
        if not entries:
            return None
        return entries[0]

    @property
    def recurring_downtimes(self):
        # type: () -> List[RecurringDowntime]
        return self._config_cache.host_extra_conf(self.hostname, host_recurring_downtimes)  # type: ignore[name-defined] # pylint: disable=undefined-variable

    @property
    def flap_settings(self):
        # type: () -> Tuple[float, float, float]
        values = self._config_cache.host_extra_conf(self.hostname, cmc_host_flap_settings)  # type: ignore[name-defined] # pylint: disable=undefined-variable
        if not values:
            return cmc_flap_settings  # type: ignore[name-defined] # pylint: disable=undefined-variable

        return values[0]

    @property
    def log_long_output(self):
        # type: () -> bool
        entries = self._config_cache.host_extra_conf(self.hostname,
                                                     cmc_host_long_output_in_monitoring_history)  # type: ignore[name-defined] # type: ignore[name-defined] # pylint: disable=undefined-variable
        if not entries:
            return False
        return entries[0]

    @property
    def state_translation(self):
        # type: () -> Dict
        entries = self._config_cache.host_extra_conf(self.hostname, host_state_translation)  # type: ignore[name-defined] # pylint: disable=undefined-variable

        spec = {}  # type: Dict
        for entry in entries[::-1]:
            spec.update(entry)
        return spec

    @property
    def smartping_settings(self):
        # type: () -> Dict
        settings = {"timeout": 2.5}
        settings.update(
            self._config_cache.host_extra_conf_merged(self.hostname, cmc_smartping_settings))  # type: ignore[name-defined] # pylint: disable=undefined-variable
        return settings

    @property
    def lnx_remote_alert_handlers(self):
        # type: () -> List[Dict[str, str]]
        return self._config_cache.host_extra_conf(self.hostname,
                                                  agent_config.get("lnx_remote_alert_handlers", []))
