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

import cmk.debug
from cmk.regex import regex, is_regex
from cmk.exceptions import MKGeneralException

import cmk_base
import cmk_base.console as console

# TODO: Prefix helper functions with "_".

#.
#   .--Service rules-------------------------------------------------------.
#   |      ____                  _                       _                 |
#   |     / ___|  ___ _ ____   _(_) ___ ___   _ __ _   _| | ___  ___       |
#   |     \___ \ / _ \ '__\ \ / / |/ __/ _ \ | '__| | | | |/ _ \/ __|      |
#   |      ___) |  __/ |   \ V /| | (_|  __/ | |  | |_| | |  __/\__ \      |
#   |     |____/ \___|_|    \_/ |_|\___\___| |_|   \__,_|_|\___||___/      |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | Service rule set matching                                            |
#   '----------------------------------------------------------------------'

# Compute outcome of a service rule set that has an item
def service_extra_conf(hostname, service, ruleset):
    import cmk_base.config
    # When the requested host is part of the local sites configuration,
    # then use only the sites hosts for processing the rules
    with_foreign_hosts = hostname not in cmk_base.config.all_active_hosts()
    cache_id = id(ruleset), with_foreign_hosts
    ruleset_cache = cmk_base.config_cache.get_dict("converted_service_rulesets")
    try:
        ruleset = ruleset_cache[cache_id]
    except KeyError:
        ruleset = _convert_service_ruleset(ruleset, with_foreign_hosts)
        ruleset_cache[cache_id] = ruleset

    entries = []
    cache = cmk_base.config_cache.get_dict("extraconf_servicelist")
    for item, hosts, service_matchers in ruleset:
        if hostname in hosts:
            cache_id = service_matchers, service
            try:
                match = cache[cache_id]
            except KeyError:
                match = _in_servicematcher_list(service_matchers, service)
                cache[cache_id] = match

            if match:
                entries.append(item)
    return entries


def _convert_service_ruleset(ruleset, with_foreign_hosts):
    new_rules = []
    for rule in ruleset:
        rule, rule_options = get_rule_options(rule)
        if rule_options.get("disabled"):
            continue

        num_elements = len(rule)
        if num_elements == 3:
            item, hostlist, servlist = rule
            tags = []
        elif num_elements == 4:
            item, tags, hostlist, servlist = rule
        else:
            raise MKGeneralException("Invalid rule '%r' in service configuration "
                                     "list: must have 3 or 4 elements" % (rule,))

        # Directly compute set of all matching hosts here, this
        # will avoid recomputation later
        hosts = all_matching_hosts(tags, hostlist, with_foreign_hosts)

        # And now preprocess the configured patterns in the servlist
        new_rules.append((item, hosts, _convert_pattern_list(servlist)))

    return new_rules


# Compute outcome of a service rule set that just say yes/no
def in_boolean_serviceconf_list(hostname, service_description, ruleset):
    # When the requested host is part of the local sites configuration,
    # then use only the sites hosts for processing the rules
    with_foreign_hosts = hostname not in cmk_base.config.all_active_hosts()
    cache_id = id(ruleset), with_foreign_hosts
    ruleset_cache = cmk_base.config_cache.get_dict("converted_service_rulesets")
    try:
        ruleset = ruleset_cache[cache_id]
    except KeyError:
        ruleset = _convert_boolean_service_ruleset(ruleset, with_foreign_hosts)
        ruleset_cache[cache_id] = ruleset

    cache = cmk_base.config_cache.get_dict("extraconf_servicelist")
    for negate, hosts, service_matchers in ruleset:
        if hostname in hosts:
            cache_id = service_matchers, service_description
            try:
                match = cache[cache_id]
            except KeyError:
                match = _in_servicematcher_list(service_matchers, service_description)
                cache[cache_id] = match

            if match:
                return not negate
    return False # no match. Do not ignore


def _convert_boolean_service_ruleset(ruleset, with_foreign_hosts):
    new_rules = []
    for rule in ruleset:
        entry, rule_options = get_rule_options(rule)
        if rule_options.get("disabled"):
            continue

        if entry[0] == NEGATE: # this entry is logically negated
            negate = True
            entry = entry[1:]
        else:
            negate = False

        if len(entry) == 2:
            hostlist, servlist = entry
            tags = []
        elif len(entry) == 3:
            tags, hostlist, servlist = entry
        else:
            raise MKGeneralException("Invalid entry '%r' in configuration: "
                                     "must have 2 or 3 elements" % (entry,))

        # Directly compute set of all matching hosts here, this
        # will avoid recomputation later
        hosts = all_matching_hosts(tags, hostlist, with_foreign_hosts)
        new_rules.append((negate, hosts, _convert_pattern_list(servlist)))

    return new_rules


#.
#   .--Host rulesets-------------------------------------------------------.
#   |      _   _           _                _                _             |
#   |     | | | | ___  ___| |_   _ __ _   _| | ___  ___  ___| |_ ___       |
#   |     | |_| |/ _ \/ __| __| | '__| | | | |/ _ \/ __|/ _ \ __/ __|      |
#   |     |  _  | (_) \__ \ |_  | |  | |_| | |  __/\__ \  __/ |_\__ \      |
#   |     |_| |_|\___/|___/\__| |_|   \__,_|_|\___||___/\___|\__|___/      |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | Host ruleset matching                                                |
#   '----------------------------------------------------------------------'

def host_extra_conf(hostname, ruleset):
    # When the requested host is part of the local sites configuration,
    # then use only the sites hosts for processing the rules
    with_foreign_hosts = hostname not in cmk_base.config.all_active_hosts()

    ruleset_cache = cmk_base.config_cache.get_dict("converted_host_rulesets")
    cache_id = id(ruleset), with_foreign_hosts

    conf_cache = cmk_base.config_cache.get_dict("host_extra_conf")

    try:
        ruleset = ruleset_cache[cache_id]
    except KeyError:
        ruleset = _convert_host_ruleset(ruleset, with_foreign_hosts)
        ruleset_cache[cache_id] = ruleset

        # TODO: LM: Why is this not on one indent level upper?
        #           The regular case of the above exception handler
        #           assigns "ruleset", but it is never used. Is this OK?
        #           And if it is OK, why is it different to service_extra_conf()?

        # Generate single match cache
        conf_cache[cache_id] = {}
        for item, hostname_list in ruleset:
            for name in hostname_list:
                conf_cache[cache_id].setdefault(name, []).append(item)

    if hostname not in conf_cache[cache_id]:
        return []

    return conf_cache[cache_id][hostname]


def _convert_host_ruleset(ruleset, with_foreign_hosts):
    new_rules = []
    if len(ruleset) == 1 and ruleset[0] == "":
        console.warning('deprecated entry [ "" ] in host configuration list')

    for rule in ruleset:
        item, tags, hostlist, rule_options = parse_host_rule(rule)
        if rule_options.get("disabled"):
            continue

        # Directly compute set of all matching hosts here, this
        # will avoid recomputation later
        new_rules.append((item, all_matching_hosts(tags, hostlist, with_foreign_hosts)))

    return new_rules


def host_extra_conf_merged(hostname, conf):
    rule_dict = {}
    for rule in host_extra_conf(hostname, conf):
        for key, value in rule.items():
            rule_dict.setdefault(key, value)
    return rule_dict

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


# TODO: Can we make this private?
def all_matching_hosts(tags, hostlist, with_foreign_hosts):
    cache_id = tuple(tags), tuple(hostlist), with_foreign_hosts
    cache = cmk_base.config_cache.get_dict("hostlist_match")

    try:
        return cache[cache_id]
    except KeyError:
        pass

    if with_foreign_hosts:
        valid_hosts = cmk_base.config.all_configured_hosts()
    else:
        valid_hosts = cmk_base.config.all_active_hosts()

    # Contains matched hosts
    matching = set([])

    # Check if the rule has only specific hosts set
    only_specific_hosts = not bool([x for x in hostlist if x[0] in ["@", "!", "~"]])

    # If no tags are specified and there are only specific hosts we already have the matches
    if not tags and only_specific_hosts:
        matching = valid_hosts.intersection(hostlist)
    # If no tags are specified and the hostlist only include @all (all hosts)
    elif not tags and hostlist == [ "@all" ]:
        matching = valid_hosts
    else:
        # If the rule has only exact host restrictions, we can thin out the list of hosts to check
        if only_specific_hosts:
            hosts_to_check = valid_hosts.intersection(set(hostlist))
        else:
            hosts_to_check = valid_hosts

        for hostname in hosts_to_check:
            # When no tag matching is requested, do not filter by tags. Accept all hosts
            # and filter only by hostlist
            if in_extraconf_hostlist(hostlist, hostname) and \
               (not tags or hosttags_match_taglist(cmk_base.config.tags_of_host(hostname), tags)):
               matching.add(hostname)

    cache[cache_id] = matching
    return matching


# Entries in list are hostnames that must equal the hostname.
# Expressions beginning with ! are negated: if they match,
# the item is excluded from the list. Expressions beginning
# withy ~ are treated as Regular Expression. Also the three
# special tags '@all', '@clusters', '@physical' are allowed.
def in_extraconf_hostlist(hostlist, hostname):

    # Migration help: print error if old format appears in config file
    # FIXME: When can this be removed?
    try:
        if hostlist[0] == "":
            raise MKGeneralException('Invalid empty entry [ "" ] in configuration')
    except IndexError:
        pass # Empty list, no problem.

    for hostentry in hostlist:
        if hostentry == '':
            raise MKGeneralException('Empty hostname in host list %r' % hostlist)
        negate = False
        use_regex = False
        if hostentry[0] == '@':
            if hostentry == '@all':
                return True
            ic = cmk_base.config.is_cluster(hostname)
            if hostentry == '@cluster' and ic:
                return True
            elif hostentry == '@physical' and not ic:
                return True

        # Allow negation of hostentry with prefix '!'
        else:
            if hostentry[0] == '!':
                hostentry = hostentry[1:]
                negate = True

            # Allow regex with prefix '~'
            if hostentry[0] == '~':
                hostentry = hostentry[1:]
                use_regex = True

        try:
            if not use_regex and hostname == hostentry:
                return not negate
            # Handle Regex. Note: hostname == True -> generic unknown host
            elif use_regex and hostname != True:
                if regex(hostentry).match(hostname) != None:
                    return not negate
        except MKGeneralException:
            if cmk.debug.enabled():
                raise

    return False



def in_binary_hostlist(hostname, conf):
    cache = cmk_base.config_cache.get_dict("in_binary_hostlist")
    cache_id = id(conf), hostname

    try:
        return cache[cache_id]
    except KeyError:
        pass

    # if we have just a list of strings just take it as list of hostnames
    if conf and type(conf[0]) == str:
        result = hostname in conf
        cache[cache_id] = result
    else:
        for entry in conf:
            entry, rule_options = get_rule_options(entry)
            if rule_options.get("disabled"):
                continue

            try:
                # Negation via 'NEGATE'
                if entry[0] == NEGATE:
                    entry = entry[1:]
                    negate = True
                else:
                    negate = False
                # entry should be one-tuple or two-tuple. Tuple's elements are
                # lists of strings. User might forget comma in one tuple. Then the
                # entry is the list itself.
                if type(entry) == list:
                    hostlist = entry
                    tags = []
                else:
                    if len(entry) == 1: # 1-Tuple with list of hosts
                        hostlist = entry[0]
                        tags = []
                    else:
                        tags, hostlist = entry

                if hosttags_match_taglist(cmk_base.config.tags_of_host(hostname), tags) and \
                       in_extraconf_hostlist(hostlist, hostname):
                    cache[cache_id] = not negate
                    break
            except:
                # TODO: Fix this too generic catching (+ bad error message)
                raise MKGeneralException("Invalid entry '%r' in host configuration list: "
                                   "must be tuple with 1 or 2 entries" % (entry,))
        else:
            cache[cache_id] = False

    return cache[cache_id]






def parse_host_rule(rule):
    rule, rule_options = get_rule_options(rule)

    num_elements = len(rule)
    if num_elements == 2:
        item, hostlist = rule
        tags = []
    elif num_elements == 3:
        item, tags, hostlist = rule
    else:
        raise MKGeneralException("Invalid entry '%r' in host configuration list: must "
                                 "have 2 or 3 entries" % (rule,))

    return item, tags, hostlist, rule_options


# Pick out the last element of an entry if it is a dictionary.
# This is a new feature (1.2.0p3) that allows to add options
# to rules. Currently only the option "disabled" is being
# honored. WATO also uses the option "comment".
def get_rule_options(entry):
    if type(entry[-1]) == dict:
        return entry[:-1], entry[-1]
    else:
        return entry, {}


# Check if a host fulfills the requirements of a tags
# list. The host must have all tags in the list, except
# for those negated with '!'. Those the host must *not* have!
# New in 1.1.13: a trailing + means a prefix match
def hosttags_match_taglist(hosttags, required_tags):
    for tag in required_tags:
        negate, tag = _parse_negated(tag)
        if tag and tag[-1] == '+':
            tag = tag[:-1]
            matches = False
            for t in hosttags:
                if t.startswith(tag):
                    matches = True
                    break

        else:
            matches = tag in hosttags

        if matches == negate:
            return False

    return True


def _parse_negated(pattern):
    # Allow negation of pattern with prefix '!'
    try:
        negate = pattern[0] == '!'
        if negate:
            pattern = pattern[1:]
    except IndexError:
        negate = False

    return negate, pattern


# Converts a regex pattern which is used to e.g. match services within Check_MK
# to a function reference to a matching function which takes one parameter to
# perform the matching and returns a two item tuple where the first element
# tells wether or not the pattern is negated and the second element the outcome
# of the match.
# This function tries to parse the pattern and return different kind of matching
# functions which can then be performed faster than just using the regex match.
def _convert_pattern(pattern):
    def is_infix_string_search(pattern):
        return pattern.startswith('.*') and not is_regex(pattern[2:])

    def is_exact_match(pattern):
        return pattern[-1] == '$' and not is_regex(pattern[:-1])

    def is_prefix_match(pattern):
        return pattern[-2:] == '.*' and not is_regex(pattern[:-2])

    if pattern == '':
        return False, lambda txt: True # empty patterns match always

    negate, pattern = _parse_negated(pattern)

    if is_exact_match(pattern):
        # Exact string match
        return negate, lambda txt: pattern[:-1] == txt

    elif is_infix_string_search(pattern):
        # Using regex to search a substring within text
        return negate, lambda txt: pattern[2:] in txt

    elif is_prefix_match(pattern):
        # prefix match with tailing .*
        pattern = pattern[:-2]
        return negate, lambda txt: txt[:len(pattern)] == pattern

    elif is_regex(pattern):
        # Non specific regex. Use real prefix regex matching
        return negate, lambda txt: regex(pattern).match(txt) != None

    else:
        # prefix match without any regex chars
        return negate, lambda txt: txt[:len(pattern)] == pattern


def _convert_pattern_list(patterns):
    return tuple([ _convert_pattern(p) for p in patterns ])


# Slow variant of checking wether a service is matched by a list
# of regexes - used e.g. by cmk --notify
def in_extraconf_servicelist(servicelist, service):
    return _in_servicematcher_list(_convert_pattern_list(servicelist), service)


def _in_servicematcher_list(service_matchers, item):
    for negate, func in service_matchers:
        result = func(item)
        if result:
            return not negate

    # no match in list -> negative answer
    return False


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

# Conveniance macros for host and service rules
PHYSICAL_HOSTS = [ '@physical' ] # all hosts but not clusters
CLUSTER_HOSTS  = [ '@cluster' ]  # all cluster hosts
ALL_HOSTS      = [ '@all' ]      # physical and cluster hosts
ALL_SERVICES   = [ "" ]          # optical replacement"
NEGATE         = '@negate'       # negation in boolean lists
