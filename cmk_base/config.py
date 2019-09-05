#!/usr/bin/env python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2014             mk@mathias-kettner.de |
# +------------------------------------------------------------------+
#
# This file is part of Check_MK.
# The official homepage is at http://mathias-kettner.de/check_mk.
#
# check_mk is free software;  you can redistribute it and/or modify it
# under the  terms of the  GNU General Public License  as published by
# the Free Software Foundation in version 2.  check_mk is  distributed
# in the hope that it will be useful, but WITHOUT ANY WARRANTY;  with-
# out even the implied warranty of  MERCHANTABILITY  or  FITNESS FOR A
# PARTICULAR PURPOSE. See the  GNU General Public License for more de-
# tails. You should have  received  a copy of the  GNU  General Public
# License along with GNU Make; see the file  COPYING.  If  not,  write
# to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
# Boston, MA 02110-1301 USA.

import os
import sys
import copy
import marshal

import cmk.debug
import cmk.paths
import cmk.translations
import cmk.store as store
from cmk.exceptions import MKGeneralException

import cmk_base
import cmk_base.console as console
import cmk_base.default_config as default_config
import cmk_base.rulesets as rulesets

# This is mainly needed for pylint to detect all available
# configuration options during static analysis. The defaults
# are loaded later with load_default_config() again.
from cmk_base.default_config import *

def get_variable_names():
    """Provides the list of all known configuration variables."""
    return [ k for k in default_config.__dict__.keys() if k[0] != "_" ]


def get_default_config():
    """Provides a dictionary containing the Check_MK default configuration"""
    cfg = {}
    for key in get_variable_names():
        value = getattr(default_config, key)

        if isinstance(value, dict) or isinstance(value, list):
            value = copy.deepcopy(value)

        cfg[key] = value
    return cfg


def load_default_config():
    globals().update(get_default_config())


def register(name, default_value):
    """Register a new configuration variable within Check_MK base."""
    setattr(default_config, name, default_value)


def _add_check_variables_to_default_config():
    """Add configuration variables registered by checks to config module"""
    import cmk_base.checks
    default_config.__dict__.update(cmk_base.checks.get_check_variable_defaults())


def _clear_check_variables_from_default_config(check_variable_names):
    """Remove previously registered check variables from the config module"""
    for varname in check_variable_names:
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
    import cmk_base.checks

    global_dict = globals()
    check_variable_names = cmk_base.checks.check_variable_names()

    check_variables = {}
    for varname in check_variable_names:
        check_variables[varname] = global_dict.pop(varname)

    cmk_base.checks.set_check_variables(check_variables)
    _clear_check_variables_from_default_config(check_variable_names)


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
    _initialize_config()

    vars_before_config = all_nonfunction_vars()

    _load_config(with_conf_d, exclude_parents_mk)
    _transform_mgmt_config_vars_from_140_to_150()
    _initialize_derived_config_variables()

    _perform_post_config_loading_actions()

    if validate_hosts:
        _verify_non_duplicate_hosts()

    # Such validation only makes sense when all checks have been loaded
    if cmk_base.checks.all_checks_loaded():
        verify_non_invalid_variables(vars_before_config)

    verify_snmp_communities_type()


def load_packed_config():
    """Load the configuration for the CMK helpers of CMC

    These files are written by PackedConfig().

    Should have a result similar to the load() above. With the exception that the
    check helpers would only need check related config variables.

    The validations which are performed during load() also don't need to be performed.
    """
    PackedConfig().load()


def _initialize_config():
    _add_check_variables_to_default_config()
    load_default_config()


def _perform_post_config_loading_actions():
    """These tasks must be performed after loading the Check_MK base configuration"""
    # First cleanup things (needed for e.g. reloading the config)
    cmk_base.config_cache.clear_all()

    initialize_config_caches()

    # In case the checks are not loaded yet it seems the current mode
    # is not working with the checks. In this case also don't load the
    # static checks into the configuration.
    if cmk_base.checks.any_check_loaded():
        add_wato_static_checks_to_checks()
        initialize_check_caches()
        set_check_variables_for_checks()


def _load_config(with_conf_d, exclude_parents_mk):
    import cmk_base.checks
    helper_vars = {
        "FILE_PATH"      : None,
        "FOLDER_PATH"    : None,
        "PHYSICAL_HOSTS" : rulesets.PHYSICAL_HOSTS,
        "CLUSTER_HOSTS"  : rulesets.CLUSTER_HOSTS,
        "ALL_HOSTS"      : rulesets.ALL_HOSTS,
        "ALL_SERVICES"   : rulesets.ALL_SERVICES,
        "NEGATE"         : rulesets.NEGATE,
    }

    global_dict = globals()
    global_dict.update(helper_vars)

    for _f in _get_config_file_paths(with_conf_d):
        # During parent scan mode we must not read in old version of parents.mk!
        if exclude_parents_mk and _f.endswith("/parents.mk"):
            continue

        try:
            _hosts_before    = set(all_hosts)
            _clusters_before = set(clusters.keys())

            # Make the config path available as a global variable to
            # be used within the configuration file
            if _f.startswith(cmk.paths.check_mk_config_dir + "/"):
                _file_path = _f[len(cmk.paths.check_mk_config_dir) + 1:]
                global_dict.update({
                    "FILE_PATH"   : _file_path,
                    "FOLDER_PATH" : os.path.dirname(_file_path),
                })
            else:
                global_dict.update({
                    "FILE_PATH"   : None,
                    "FOLDER_PATH" : None,
                })

            execfile(_f, global_dict, global_dict)

            _new_hosts    = set(all_hosts).difference(_hosts_before)
            _new_clusters = set(clusters.keys()).difference(_clusters_before)

            set_folder_paths(_new_hosts.union(_new_clusters), _f)
        except Exception, e:
            if cmk.debug.enabled():
                raise
            elif sys.stderr.isatty():
                console.error("Cannot read in configuration file %s: %s\n", _f, e)
                sys.exit(1)

    # Cleanup global helper vars
    for helper_var in helper_vars.keys():
        del global_dict[helper_var]


def _transform_mgmt_config_vars_from_140_to_150():
    #FIXME We have to transform some configuration variables from host attributes
    # to cmk_base configuration variables because during the migration step from
    # 1.4.0 to 1.5.0 some config variables are not known in cmk_base. These variables
    # are 'management_protocol' and 'management_snmp_community'.
    # Clean this up one day!
    for hostname, attributes in host_attributes.iteritems():
        for name, var in [
            ('management_protocol',       management_protocol),
            ('management_snmp_community', management_snmp_credentials),
        ]:
            if attributes.get(name):
                var.setdefault(hostname, attributes[name])


# Create list of all files to be included during configuration loading
def _get_config_file_paths(with_conf_d):
    if with_conf_d:
        list_of_files = sorted(
            reduce(lambda a,b: a+b, [ [ "%s/%s" % (d, f) for f in fs if f.endswith(".mk")]
                   for d, _unused_sb, fs in os.walk(cmk.paths.check_mk_config_dir) ], []),
           cmp=_cmp_config_paths
        )
        list_of_files = [ cmk.paths.main_config_file ] + list_of_files
    else:
        list_of_files = [ cmk.paths.main_config_file ]

    for path in [ cmk.paths.final_config_file, cmk.paths.local_config_file ]:
        if os.path.exists(path):
            list_of_files.append(path)

    return list_of_files


def initialize_config_caches():
    collect_hosttags()


def _initialize_derived_config_variables():
    global service_service_levels, host_service_levels
    service_service_levels = extra_service_conf.get("_ec_sl", [])
    host_service_levels = extra_host_conf.get("_ec_sl", [])


def get_derived_config_variable_names():
    """These variables are computed from other configuration variables and not configured directly.

    The origin variable (extra_service_conf) should not be exported to the helper config. Only
    the service levels are needed."""
    return set([ "service_service_levels", "host_service_levels" ])


def _verify_non_duplicate_hosts():
    duplicates = duplicate_hosts()
    if duplicates:
        # TODO: Raise an exception
        console.error("Error in configuration: duplicate hosts: %s\n",
                                                ", ".join(duplicates))
        sys.exit(3)


# Add WATO-configured explicit checks to (possibly empty) checks
# statically defined in checks.
def add_wato_static_checks_to_checks():
    global checks

    static = []
    for entries in static_checks.values():
        for entry in entries:
            entry, rule_options = rulesets.get_rule_options(entry)
            if rule_options.get("disabled"):
                continue

            # Parameters are optional
            if len(entry[0]) == 2:
                checktype, item = entry[0]
                params = None
            else:
                checktype, item, params = entry[0]
            if len(entry) == 3:
                taglist, hostlist = entry[1:3]
            else:
                hostlist = entry[1]
                taglist = []

            # Do not process manual checks that are related to not existing or have not
            # loaded check files
            try:
                check_plugin_info = cmk_base.checks.check_info[checktype]
            except KeyError:
                continue

            # Make sure, that for dictionary based checks
            # at least those keys defined in the factory
            # settings are present in the parameters
            if type(params) == dict:
                def_levels_varname = check_plugin_info.get("default_levels_variable")
                if def_levels_varname:
                    for key, value in cmk_base.checks.factory_settings.get(def_levels_varname, {}).items():
                        if key not in params:
                            params[key] = value

            static.append((taglist, hostlist, checktype, item, params))

    # Note: We need to reverse the order of the static_checks. This is because
    # users assume that earlier rules have precedence over later ones. For static
    # checks that is important if there are two rules for a host with the same
    # combination of check type and item. When the variable 'checks' is evaluated,
    # *later* rules have precedence. This is not consistent with the rest, but a
    # result of this "historic implementation".
    static.reverse()

    # Now prepend to checks. That makes that checks variable have precedence
    # over WATO.
    checks = static + checks


def initialize_check_caches():
    single_host_checks = cmk_base.config_cache.get_dict("single_host_checks")
    multi_host_checks  = cmk_base.config_cache.get_list("multi_host_checks")

    for entry in checks:
        if len(entry) == 4 and type(entry[0]) == str:
            single_host_checks.setdefault(entry[0], []).append(entry)
        else:
            multi_host_checks.append(entry)


def set_folder_paths(new_hosts, filename):
    if not filename.startswith(cmk.paths.check_mk_config_dir):
        return

    path = filename[len(cmk.paths.check_mk_config_dir):]

    for hostname in strip_tags(new_hosts):
        host_paths[hostname] = path


def verify_non_invalid_variables(vars_before_config):
    # Check for invalid configuration variables
    vars_after_config = all_nonfunction_vars()
    ignored_variables = set(['vars_before_config', 'parts',
                             'seen_hostnames',
                             'taggedhost' ,'hostname',
                             'service_service_levels',
                             'host_service_levels'])

    found_invalid = 0
    for name in vars_after_config:
        if name not in ignored_variables and name not in vars_before_config:
            console.error("Invalid configuration variable '%s'\n", name)
            found_invalid += 1

    if found_invalid:
        console.error("--> Found %d invalid variables\n" % found_invalid)
        console.error("If you use own helper variables, please prefix them with _.\n")
        sys.exit(1)


def verify_snmp_communities_type():
    # Special handling for certain deprecated variables
    if type(snmp_communities) == dict:
        console.error("ERROR: snmp_communities cannot be a dict any more.\n")
        sys.exit(1)


def all_nonfunction_vars():
    return set([ name for name,value in globals().items()
                if name[0] != '_' and type(value) != type(lambda:0) ])


# Helper functions that determines the sort order of the
# configuration files. The following two rules are implemented:
# 1. *.mk files in the same directory will be read
#    according to their lexical order.
# 2. subdirectories in the same directory will be
#    scanned according to their lexical order.
# 3. subdirectories of a directory will always be read *after*
#    the *.mk files in that directory.
def _cmp_config_paths(a, b):
    pa = a.split('/')
    pb = b.split('/')
    return cmp(pa[:-1], pb[:-1]) or \
           cmp(len(pa), len(pb)) or \
           cmp(pa, pb)


class PackedConfig(object):
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
        "host_paths",
        "timeperiods",
        "extra_service_conf",
        "extra_nagios_conf",
    ]

    def __init__(self):
        super(PackedConfig, self).__init__()
        self._path = os.path.join(cmk.paths.var_dir, "base", "precompiled_check_config.mk")


    def save(self):
        self._write(self._pack())


    def _pack(self):
        import cmk_base.checks

        helper_config = (
            "#!/usr/bin/env python\n"
            "# encoding: utf-8\n"
            "# Created by Check_MK. Dump of the currently active configuration\n\n"
        )

        # These functions purpose is to filter out hosts which are monitored on different sites
        active_hosts    = all_active_hosts()
        active_clusters = all_active_clusters()
        def filter_all_hosts(all_hosts):
            all_hosts_red = []
            for host_entry in all_hosts:
                hostname = host_entry.split("|", 1)[0]
                if hostname in active_hosts:
                    all_hosts_red.append(host_entry)
            return all_hosts_red

        def filter_clusters(clusters):
            clusters_red = {}
            for cluster_entry, cluster_nodes in clusters.items():
                clustername = cluster_entry.split("|", 1)[0]
                if clustername in active_clusters:
                    clusters_red[cluster_entry] = cluster_nodes
            return clusters_red

        def filter_hostname_in_dict(values):
            values_red = {}
            for hostname, attributes in values.items():
                if hostname in active_hosts:
                    values_red[hostname] = attributes
            return values_red

        filter_var_functions = {
            "all_hosts"                : filter_all_hosts,
            "clusters"                 : filter_clusters,
            "host_attributes"          : filter_hostname_in_dict,
            "ipaddresses"              : filter_hostname_in_dict,
            "ipv6addresses"            : filter_hostname_in_dict,
            "explicit_snmp_communities": filter_hostname_in_dict,
            "hosttags"                 : filter_hostname_in_dict
        }

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

        check_variable_defaults = cmk_base.checks.get_check_variable_defaults()

        for varname, val in cmk_base.checks.get_check_variables().items():
            if val == check_variable_defaults[varname]:
                continue

            if not self._packable(varname, val):
                continue

            helper_config += "\n%s = %r\n" % (varname, val)

        return helper_config


    def _packable(self, varname, val):
        """Checks whether or not a variable can be written to the config.mk
        and read again from it."""
        if type(val) in [ int, str, unicode, bool ] or not val:
            return True

        try:
            eval(repr(val))
            return True
        except:
            return False


    def _write(self, helper_config):
        store.makedirs(os.path.dirname(self._path))

        store.save_file(self._path + ".orig", helper_config + "\n")

        import marshal
        code = compile(helper_config, '<string>', 'exec')
        with open(self._path + ".compiled", "w") as compiled_file:
            marshal.dump(code, compiled_file)

        os.rename(self._path + ".compiled", self._path)


    def load(self):
        _initialize_config()
        exec(marshal.load(open(self._path)), globals())
        _perform_post_config_loading_actions()


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
    cache = cmk_base.config_cache.get_dict("strip_tags")

    cache_id = tuple(tagged_hostlist)
    try:
        return cache[cache_id]
    except KeyError:
        result = map(lambda h: h.split('|', 1)[0], tagged_hostlist)
        cache[cache_id] = result
        return result


def tags_of_host(hostname):
    """Returns the list of all configured tags of a host. In case
    a host has no tags configured or is not known, it returns an
    empty list."""
    hosttags = cmk_base.config_cache.get_dict("hosttags")
    try:
        return hosttags[hostname]
    except KeyError:
        return []


def collect_hosttags():
    hosttags = cmk_base.config_cache.get_dict("hosttags")
    for tagged_host in all_hosts + clusters.keys():
        parts = tagged_host.split("|")
        hosttags[parts[0]] = sorted(parts[1:])


#.
#   .--HostCollections-----------------------------------------------------.
#   | _   _           _    ____      _ _           _   _                   |
#   || | | | ___  ___| |_ / ___|___ | | | ___  ___| |_(_) ___  _ __  ___   |
#   || |_| |/ _ \/ __| __| |   / _ \| | |/ _ \/ __| __| |/ _ \| '_ \/ __|  |
#   ||  _  | (_) \__ \ |_| |__| (_) | | |  __/ (__| |_| | (_) | | | \__ \  |
#   ||_| |_|\___/|___/\__|\____\___/|_|_|\___|\___|\__|_|\___/|_| |_|___/  |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |                                                                      |
#   '----------------------------------------------------------------------'


# Returns a set of all active hosts
def all_active_hosts():
    cache = cmk_base.config_cache.get_set("all_active_hosts")
    if not cache.is_populated():
        cache.update(all_active_realhosts(), all_active_clusters())
        cache.set_populated()
    return cache


# Returns a set of all host names to be handled by this site
# hosts of other sitest or disabled hosts are excluded
def all_active_realhosts():
    active_realhosts = cmk_base.config_cache.get_set("active_realhosts")

    if not active_realhosts.is_populated():
        active_realhosts.update(filter_active_hosts(all_configured_realhosts()))
        active_realhosts.set_populated()

    return active_realhosts


# Returns a set of all cluster host names to be handled by
# this site hosts of other sitest or disabled hosts are excluded
def all_active_clusters():
    active_clusters = cmk_base.config_cache.get_set("active_clusters")

    if not active_clusters.is_populated():
        active_clusters.update(filter_active_hosts(all_configured_clusters()))
        active_clusters.set_populated()

    return active_clusters


# Returns a set of all hosts, regardless if currently
# disabled or monitored on a remote site.
def all_configured_hosts():
    cache = cmk_base.config_cache.get_set("all_configured_hosts")
    if not cache.is_populated():
        cache.update(all_configured_realhosts(), all_configured_clusters())
        cache.set_populated()
    return cache


# Returns a set of all host names, regardless if currently
# disabled or monitored on a remote site. Does not return
# cluster hosts.
def all_configured_realhosts():
    cache = cmk_base.config_cache.get_set("all_configured_realhosts")
    if not cache.is_populated():
        cache.update(strip_tags(all_hosts))
        cache.set_populated()
    return cache


# Returns a set of all cluster names, regardless if currently
# disabled or monitored on a remote site. Does not return
# normal hosts.
def all_configured_clusters():
    cache = cmk_base.config_cache.get_set("all_configured_clusters")
    if not cache.is_populated():
        cache.update(strip_tags(clusters.keys()))
        cache.set_populated()
    return cache


# This function should only be used during duplicate host check! It has to work like
# all_active_hosts() but with the difference that duplicates are not removed.
def all_active_hosts_with_duplicates():
    # Only available with CEE
    if "shadow_hosts" in globals():
        shadow_host_entries = shadow_hosts.keys()
    else:
        shadow_host_entries = []

    return filter_active_hosts(strip_tags(all_hosts)  \
                               + strip_tags(clusters.keys()) \
                               + strip_tags(shadow_host_entries), keep_duplicates=True)


# Returns a set of active hosts for this site
def filter_active_hosts(hostlist, keep_offline_hosts=False, keep_duplicates=False):
    if only_hosts == None and distributed_wato_site == None:
        active_hosts = hostlist

    elif only_hosts == None:
        active_hosts = [ hostname for hostname in hostlist
                 if host_is_member_of_site(hostname, distributed_wato_site) ]

    elif distributed_wato_site == None:
        if keep_offline_hosts:
            active_hosts = hostlist
        else:
            active_hosts = [ hostname for hostname in hostlist
                     if rulesets.in_binary_hostlist(hostname, only_hosts) ]

    else:
        active_hosts = [ hostname for hostname in hostlist
                 if (keep_offline_hosts or rulesets.in_binary_hostlist(hostname, only_hosts))
                 and host_is_member_of_site(hostname, distributed_wato_site) ]

    if keep_duplicates:
        return active_hosts
    else:
        return set(active_hosts)


def duplicate_hosts():
    seen_hostnames = set([])
    duplicates = set([])

    for hostname in all_active_hosts_with_duplicates():
        if hostname in seen_hostnames:
            duplicates.add(hostname)
        else:
            seen_hostnames.add(hostname)

    return sorted(list(duplicates))


# Returns a list of all hosts which are associated with this site,
# but have been removed by the "only_hosts" rule. Normally these
# are the hosts which have the tag "offline".
#
# This is not optimized for performance, so use in specific situations.
def all_offline_hosts():
    hostlist = filter_active_hosts(all_configured_realhosts().union(all_configured_clusters()),
                                   keep_offline_hosts=True)

    return [ hostname for hostname in hostlist
             if not rulesets.in_binary_hostlist(hostname, only_hosts) ]



def all_configured_offline_hosts():
    hostlist = all_configured_realhosts().union(all_configured_clusters())

    return set([ hostname for hostname in hostlist
             if not rulesets.in_binary_hostlist(hostname, only_hosts) ])



#.
#   .--Hosts---------------------------------------------------------------.
#   |                       _   _           _                              |
#   |                      | | | | ___  ___| |_ ___                        |
#   |                      | |_| |/ _ \/ __| __/ __|                       |
#   |                      |  _  | (_) \__ \ |_\__ \                       |
#   |                      |_| |_|\___/|___/\__|___/                       |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |  Helper functions for dealing with hosts.                            |
#   '----------------------------------------------------------------------'

def host_is_member_of_site(hostname, site):
    for tag in tags_of_host(hostname):
        if tag.startswith("site:"):
            return site == tag[5:]
    # hosts without a site: tag belong to all sites
    return True


def alias_of(hostname, fallback):
    aliases = rulesets.host_extra_conf(hostname, extra_host_conf.get("alias", []))
    if len(aliases) == 0:
        if fallback:
            return fallback
        else:
            return hostname
    else:
        return aliases[0]


def get_additional_ipaddresses_of(hostname):
    #TODO Regarding the following configuration variables from WATO
    # there's no inheritance, thus we use 'host_attributes'.
    # Better would be to use cmk_base configuration variables,
    # eg. like 'management_protocol'.
    return (host_attributes.get(hostname, {}).get("additional_ipv4addresses", []),
            host_attributes.get(hostname, {}).get("additional_ipv6addresses", []))


def parents_of(hostname):
    par = rulesets.host_extra_conf(hostname, parents)
    # Use only those parents which are defined and active in
    # all_hosts.
    used_parents = []
    for p in par:
        ps = p.split(",")
        for pss in ps:
            if pss in all_active_realhosts():
                used_parents.append(pss)
    return used_parents


# If host is node of one or more clusters, return a list of the cluster host names.
# If not, return an empty list.
def clusters_of(hostname):
    cache = cmk_base.config_cache.get_dict("clusters_of")
    if not cache.is_populated():
        for cluster, hosts in clusters.items():
            clustername = cluster.split('|', 1)[0]
            for name in hosts:
                cache.setdefault(name, []).append(clustername)
        cache.set_populated()

    return cache.get(hostname, [])


#
# Agent type
#

def is_tcp_host(hostname):
    return rulesets.in_binary_hostlist(hostname, tcp_hosts)


def is_snmp_host(hostname):
    return rulesets.in_binary_hostlist(hostname, snmp_hosts)


def is_ping_host(hostname):
    return not is_snmp_host(hostname) \
       and not is_agent_host(hostname) \
       and not has_management_board(hostname)


def is_agent_host(hostname):
    import cmk_base.piggyback as piggyback
    import cmk_base.data_sources as data_sources
    return (is_tcp_host(hostname) or
            piggyback.has_piggyback_raw_data(piggyback_max_cachefile_age, hostname) or
            data_sources.has_persisted_piggyback_agent_sections(hostname))


def is_dual_host(hostname):
    return is_tcp_host(hostname) and is_snmp_host(hostname)


def is_all_agents_host(hostname):
    return "all-agents" in tags_of_host(hostname)


def is_all_special_agents_host(hostname):
    return "special-agents" in tags_of_host(hostname)


#
# IPv4/IPv6
#

def is_ipv6_primary(hostname):
    """Whether or not the given host is configured to be monitored
    primarily via IPv6."""
    dual_stack_host = is_ipv4v6_host(hostname)
    return (not dual_stack_host and is_ipv6_host(hostname)) \
            or (dual_stack_host and _primary_ip_address_family_of(hostname) == "ipv6")


def _primary_ip_address_family_of(hostname):
    rules = rulesets.host_extra_conf(hostname, primary_address_family)
    if rules:
        return rules[0]
    return "ipv4"


def is_ipv4v6_host(hostname):
    tags = tags_of_host(hostname)
    return "ip-v6" in tags and "ip-v4" in tags


def is_ipv6_host(hostname):
    return "ip-v6" in tags_of_host(hostname)


def is_ipv4_host(hostname):
    """Whether or not the given host is configured to be monitored via IPv4.
    This is the case when it is set to be explicit IPv4 or implicit
    (when host is not an IPv6 host and not a "No IP" host)"""
    tags = tags_of_host(hostname)

    if "ip-v4" in tags:
       return True

    return "ip-v6" not in tags and "no-ip" not in tags


def is_no_ip_host(hostname):
    """Whether or not the given host is configured not to be monitored via IP"""
    return "no-ip" in tags_of_host(hostname)

#
# Management board
#

def has_management_board(hostname):
    return management_protocol_of(hostname) is not None


def management_address_of(hostname):
    attributes_of_host = host_attributes.get(hostname, {})
    if attributes_of_host.get("management_address"):
        return attributes_of_host["management_address"]
    else:
        return ipaddresses.get(hostname)


def management_protocol_of(hostname):
    return management_protocol.get(hostname)


def management_credentials_of(hostname):
    protocol = management_protocol_of(hostname)
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
        return credentials_variable[hostname]
    except KeyError:
        pass

    # If a rule matches, use the first rule for the management board protocol of the host
    rule_settings = rulesets.host_extra_conf(hostname, management_board_config)
    for protocol, credentials in rule_settings:
        if protocol == management_protocol_of(hostname):
            return credentials

    return default_value


#
# Agent communication
#

def agent_port_of(hostname):
    ports = rulesets.host_extra_conf(hostname, agent_ports)
    if len(ports) == 0:
        return agent_port
    else:
        return ports[0]


def tcp_connect_timeout_of(hostname):
    timeouts = rulesets.host_extra_conf(hostname, tcp_connect_timeouts)
    if len(timeouts) == 0:
        return tcp_connect_timeout
    else:
        return timeouts[0]


def agent_encryption_of(hostname):
    settings = rulesets.host_extra_conf(hostname, agent_encryption)
    if settings:
        return settings[0]
    else:
        return {'use_regular': 'disable',
                'use_realtime': 'enforce'}


def agent_target_version(hostname):
    agent_target_versions = rulesets.host_extra_conf(hostname, check_mk_agent_target_versions)
    if agent_target_versions:
        spec = agent_target_versions[0]
        if spec == "ignore":
            return None
        elif spec == "site":
            return cmk.__version__
        elif type(spec) == str:
            # Compatibility to old value specification format (a single version string)
            return spec
        elif spec[0] == 'specific':
            return spec[1]
        else:
            return spec # return the whole spec in case of an "at least version" config


#
# Explicit custom variables
#
def get_explicit_service_custom_variables(hostname, service_description):
    try:
        return explicit_service_custom_variables[(hostname, service_description)]
    except KeyError:
        return {}

#
# SNMP
#

# Determine SNMP community for a specific host.  It the host is found
# int the map snmp_communities, that community is returned. Otherwise
# the snmp_default_community is returned (wich is preset with
# "public", but can be overridden in main.mk
def snmp_credentials_of(hostname):
    try:
        return explicit_snmp_communities[hostname]
    except KeyError:
        pass

    communities = rulesets.host_extra_conf(hostname, snmp_communities)
    if len(communities) > 0:
        return communities[0]

    # nothing configured for this host -> use default
    return snmp_default_community


def snmp_character_encoding_of(hostname):
    entries = rulesets.host_extra_conf(hostname, snmp_character_encodings)
    if len(entries) > 0:
        return entries[0]


def snmp_timing_of(hostname):
    timing = rulesets.host_extra_conf(hostname, snmp_timing)
    if len(timing) > 0:
        return timing[0]
    else:
        return {}


def snmpv3_contexts_of(hostname):
    return rulesets.host_extra_conf(hostname, snmpv3_contexts)


def oid_range_limits_of(hostname):
    return rulesets.host_extra_conf(hostname, snmp_limit_oid_range)


def snmp_port_of(hostname):
    ports = rulesets.host_extra_conf(hostname, snmp_ports)
    if len(ports) == 0:
        return None # do not specify a port, use default
    else:
        return ports[0]


def is_snmpv3_host(hostname):
    return type(snmp_credentials_of(hostname)) == tuple


def is_bulkwalk_host(hostname):
    if bulkwalk_hosts:
        return rulesets.in_binary_hostlist(hostname, bulkwalk_hosts)
    else:
        return False


def bulk_walk_size_of(hostname):
    bulk_sizes = rulesets.host_extra_conf(hostname, snmp_bulk_size)
    if not bulk_sizes:
        return 10
    else:
        return bulk_sizes[0]


def is_snmpv2c_host(hostname):
    return is_bulkwalk_host(hostname) or \
        rulesets.in_binary_hostlist(hostname, snmpv2c_hosts)


def is_usewalk_host(hostname):
    return rulesets.in_binary_hostlist(hostname, usewalk_hosts)


def is_inline_snmp_host(hostname):
    # TODO: Better use "inline_snmp" once we have moved the code to an own module
    has_inline_snmp = "netsnmp" in sys.modules
    return has_inline_snmp and use_inline_snmp \
           and not rulesets.in_binary_hostlist(hostname, non_inline_snmp_hosts)


#
# Groups
#

def hostgroups_of(hostname):
    return rulesets.host_extra_conf(hostname, host_groups)


def summary_hostgroups_of(hostname):
    return rulesets.host_extra_conf(hostname, summary_host_groups)


def contactgroups_of(hostname):
    cgrs = []

    # host_contactgroups may take single values as well as
    # lists as item value. Of all list entries only the first
    # one is used. The single-contact-groups entries are all
    # recognized.
    first_list = True
    for entry in rulesets.host_extra_conf(hostname, host_contactgroups):
        if type(entry) == list and first_list:
            cgrs += entry
            first_list = False
        else:
            cgrs.append(entry)

    if monitoring_core == "nagios" and enable_rulebased_notifications:
        cgrs.append("check-mk-notify")

    return list(set(cgrs))

#
# Misc
#

def exit_code_spec(hostname):
    spec = {}
    specs = rulesets.host_extra_conf(hostname, check_mk_exit_status)
    for entry in specs[::-1]:
        spec.update(entry)
    return spec


def check_period_of(hostname, service):
    periods = rulesets.service_extra_conf(hostname, service, check_periods)
    if periods:
        period = periods[0]
        if period == "24X7":
            return None
        else:
            return period
    else:
        return None


def check_interval_of(hostname, section_name):
    import cmk_base.checks
    if not cmk_base.checks.is_snmp_check(section_name):
        return # no values at all for non snmp checks

    # Previous to 1.5 "match" could be a check name (including subchecks) instead of
    # only main check names -> section names. This has been cleaned up, but we still
    # need to be compatible. Strip of the sub check part of "match".
    for match, minutes in rulesets.host_extra_conf(hostname, snmp_check_interval):
        if match is None or match.split(".")[0] == section_name:
            return minutes # use first match

#.
#   .--Cluster-------------------------------------------------------------.
#   |                    ____ _           _                                |
#   |                   / ___| |_   _ ___| |_ ___ _ __                     |
#   |                  | |   | | | | / __| __/ _ \ '__|                    |
#   |                  | |___| | |_| \__ \ ||  __/ |                       |
#   |                   \____|_|\__,_|___/\__\___|_|                       |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | Code dealing with clusters (virtual hosts that are used to deal with |
#   | services that can move between physical nodes.                       |
#   '----------------------------------------------------------------------'

# Checks whether or not the given host is a cluster host
def is_cluster(hostname):
    # all_configured_clusters() needs to be used, because this function affects
    # the agent bakery, which needs all configured hosts instead of just the hosts
    # of this site
    return hostname in all_configured_clusters()


# Returns the nodes of a cluster, or None if hostname is not a cluster
def nodes_of(hostname):
    nodes_of_cache = cmk_base.config_cache.get_dict("nodes_of")
    nodes = nodes_of_cache.get(hostname, False)
    if nodes != False:
        return nodes

    for tagged_hostname, nodes in clusters.items():
        if hostname == tagged_hostname.split("|")[0]:
            nodes_of_cache[hostname] = nodes
            return nodes

    nodes_of_cache[hostname] = None
    return None


# Determine weather a service (found on a physical host) is a clustered
# service and - if yes - return the cluster host of the service. If
# no, returns the hostname of the physical host.
def host_of_clustered_service(hostname, servicedesc):
    the_clusters = clusters_of(hostname)
    if not the_clusters:
        return hostname

    cluster_mapping = rulesets.service_extra_conf(hostname, servicedesc, clustered_services_mapping)
    for cluster in cluster_mapping:
        # Check if the host is in this cluster
        if cluster in the_clusters:
            return cluster

    # 1. New style: explicitly assigned services
    for cluster, conf in clustered_services_of.items():
        nodes = nodes_of(cluster)
        if not nodes:
            raise MKGeneralException("Invalid entry clustered_services_of['%s']: %s is not a cluster." %
                   (cluster, cluster))
        if hostname in nodes and \
            rulesets.in_boolean_serviceconf_list(hostname, servicedesc, conf):
            return cluster

    # 1. Old style: clustered_services assumes that each host belong to
    #    exactly on cluster
    if rulesets.in_boolean_serviceconf_list(hostname, servicedesc, clustered_services):
        return the_clusters[0]

    return hostname


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
    if "Temperature" in item:
        return False, item # old item format, no conversion

    parts = item.split(" ")
    if parts[0] == "Ambient":
        return False, "%s Temperature" % parts[1]

    elif len(parts) == 2:
        return False, "%s %s.Temperature" % (parts[1], parts[0])

    else:
        if parts[1] == "LCP":
            parts[1] = "Liquid_Cooling_Package"
        return False, "%s %s.%s-Temperature" % (parts[1], parts[0], parts[2])


_old_service_descriptions = {
    "df"                               : "fs_%s",
    "df_netapp"                        : "fs_%s",
    "df_netapp32"                      : "fs_%s",
    "esx_vsphere_datastores"           : "fs_%s",
    "hr_fs"                            : "fs_%s",
    "vms_diskstat.df"                  : "fs_%s",
    "zfsget"                           : "fs_%s",
    "ps"                               : "proc_%s",
    "ps.perf"                          : "proc_%s",
    "wmic_process"                     : "proc_%s",
    "services"                         : "service_%s",
    "logwatch"                         : "LOG %s",
    "logwatch.groups"                  : "LOG %s",
    "hyperv_vm"                        : "hyperv_vms",
    "ibm_svc_mdiskgrp"                 : "MDiskGrp %s",
    "ibm_svc_system"                   : "IBM SVC Info",
    "ibm_svc_systemstats.diskio"       : "IBM SVC Throughput %s Total",
    "ibm_svc_systemstats.iops"         : "IBM SVC IOPS %s Total",
    "ibm_svc_systemstats.disk_latency" : "IBM SVC Latency %s Total",
    "ibm_svc_systemstats.cache"        : "IBM SVC Cache Total",
    "mknotifyd"                        : "Notification Spooler %s",
    "mknotifyd.connection"             : "Notification Connection %s",

    "casa_cpu_temp"                    : "Temperature %s",
    "cmciii.temp"                      : _get_old_cmciii_temp_description,
    "cmciii.psm_current"               : "%s",
    "cmciii_lcp_airin"                 : "LCP Fanunit Air IN",
    "cmciii_lcp_airout"                : "LCP Fanunit Air OUT",
    "cmciii_lcp_water"                 : "LCP Fanunit Water %s",
    "etherbox.temp"                    : "Sensor %s",
    # While using the old description, don't append the item, even when discovered
    # with the new check which creates an item.
    "liebert_bat_temp"                 : lambda item: (False, "Battery Temp"),
    "nvidia.temp"                      : "Temperature NVIDIA %s",
    "ups_bat_temp"                     : "Temperature Battery %s",
    "innovaphone_temp"                 : lambda item: (False, "Temperature"),
    "enterasys_temp"                   : lambda item: (False, "Temperature"),
    "raritan_emx"                      : "Rack %s",
    "raritan_pdu_inlet"                : "Input Phase %s",
    "postfix_mailq"                    : lambda item: (False, "Postfix Queue"),
    "nullmailer_mailq"                 : lambda item: (False, "Nullmailer Queue"),
    "barracuda_mailqueues"             : lambda item: (False, "Mail Queue"),
    "qmail_stats"                      : lambda item: (False, "Qmail Queue"),
    "mssql_backup"                     : "%s Backup",
    "mssql_counters.cache_hits"        : "%s",
    "mssql_counters.transactions"      : "%s Transactions",
    "mssql_counters.locks"             : "%s Locks",
    "mssql_counters.sqlstats"          : "%s",
    "mssql_counters.pageactivity"      : "%s Page Activity",
    "mssql_counters.locks_per_batch"   : "%s Locks per Batch",
    "mssql_counters.file_sizes"        : "%s File Sizes",
    "mssql_databases"                  : "%s Database",
    "mssql_datafiles"                  : "Datafile %s",
    "mssql_tablespaces"                : "%s Sizes",
    "mssql_transactionlogs"            : "Transactionlog %s",
    "mssql_versions"                   : "%s Version",

}

def service_description(hostname, check_plugin_name, item):
    import cmk_base.checks as checks
    if check_plugin_name not in checks.check_info:
        if item:
            return "Unimplemented check %s / %s" % (check_plugin_name, item)
        else:
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
            descr_format = checks.check_info[check_plugin_name]["service_description"]

    if type(descr_format) == str:
        descr_format = descr_format.decode("utf-8")

    # Note: we strip the service description (remove spaces).
    # One check defines "Pages %s" as a description, but the item
    # can by empty in some cases. Nagios silently drops leading
    # and trailing spaces in the configuration file.
    if add_item and type(item) in [str, unicode, int, long]:
        if "%s" not in descr_format:
            descr_format += " %s"
        descr = descr_format % (item,)
    else:
        descr = descr_format

    if "%s" in descr:
        raise MKGeneralException("Found '%%s' in service description (Host: %s, Check type: %s, Item: %s). "
                                 "Please try to rediscover the service to fix this issue." % \
                                 (hostname, check_plugin_name, item))

    return get_final_service_description(hostname, descr)


_old_active_check_service_descriptions = {
    "http": lambda params: (params[0][1:] if params[0].startswith("^")
                            else "HTTP %s" % params[0])
}


def active_check_service_description(hostname, active_check_name, params):
    import cmk_base.checks as checks
    if active_check_name not in checks.active_check_info:
        return "Unimplemented check %s" % active_check_name

    if (active_check_name in _old_active_check_service_descriptions and
            active_check_name not in use_new_descriptions_for):
        description = _old_active_check_service_descriptions[active_check_name](params)
    else:
        act_info = checks.active_check_info[active_check_name]
        description = act_info["service_description"](params)

    description = description.replace('$HOSTNAME$', hostname)

    return get_final_service_description(hostname, description)


def get_final_service_description(hostname, description):
    translations = get_service_translations(hostname)
    if translations:
        # Translate
        description = cmk.translations.translate_service_description(translations, description)

    # Sanitize; Remove illegal characters from a service description
    description = description.strip()
    cache = cmk_base.config_cache.get_dict("final_service_description")
    try:
        new_description = cache[description]
    except KeyError:
        new_description = "".join([c for c in description
                          if c not in cmk_base.config.nagios_illegal_chars]).rstrip("\\")
        cache[description] = new_description

    return new_description


def service_ignored(hostname, check_plugin_name, service_description):
    if check_plugin_name and check_plugin_name in ignored_checktypes:
        return True
    if service_description != None \
       and rulesets.in_boolean_serviceconf_list(hostname, service_description, ignored_services):
        return True
    if check_plugin_name and _checktype_ignored_for_host(hostname, check_plugin_name):
        return True
    return False


def _checktype_ignored_for_host(host, checktype):
    if checktype in ignored_checktypes:
        return True
    ignored = rulesets.host_extra_conf(host, ignored_checks)
    for e in ignored:
        if checktype == e or (type(e) == list and checktype in e):
            return True
    return False


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
    """Whether or not the site is currently configured to use the Microcore."""
    return monitoring_core == "cmc"


def decode_incoming_string(s, encoding="utf-8"):
    try:
        return s.decode(encoding)
    except:
        return s.decode(fallback_agent_output_encoding)


def get_piggyback_translations(hostname):
    """Get a dict that specifies the actions to be done during the hostname translation"""
    rules = rulesets.host_extra_conf(hostname, piggyback_translation)
    translations = {}
    for rule in rules[::-1]:
        translations.update(rule)
    return translations


def get_service_translations(hostname):
    translations_cache = cmk_base.config_cache.get_dict("service_description_translations")
    if hostname in translations_cache:
        return translations_cache[hostname]

    rules = rulesets.host_extra_conf(hostname, service_description_translation)
    translations = {}
    for rule in rules[::-1]:
        for k, v in rule.items():
            if isinstance(v, list):
                translations.setdefault(k, set())
                translations[k] |= set(v)
            else:
                translations[k] = v

    translations_cache[hostname] = translations
    return translations
