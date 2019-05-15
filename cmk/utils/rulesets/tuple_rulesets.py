#!/usr/bin/env python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2019             mk@mathias-kettner.de |
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
from typing import Generator, Dict, Text, Pattern, Tuple, List  # pylint: disable=unused-import

from cmk.utils.regex import regex
import cmk.utils.paths
from cmk.utils.exceptions import MKGeneralException

# Conveniance macros for legacy tuple based host and service rules
PHYSICAL_HOSTS = ['@physical']  # all hosts but not clusters
CLUSTER_HOSTS = ['@cluster']  # all cluster hosts
ALL_HOSTS = ['@all']  # physical and cluster hosts
ALL_SERVICES = [""]  # optical replacement"
NEGATE = '@negate'  # negation in boolean lists

# TODO: We could make some more optimizations to host/item list matching:
# - Is it worth to detect matches that are no regex matches?
# - We could remove .* from end of regexes
# - What's about compilation of the regexes?


def get_rule_options(entry):
    """Get the options from a rule.

    Pick out the option element of a rule. Currently the options "disabled"
    and "comments" are being honored."""
    if isinstance(entry[-1], dict):
        return entry[:-1], entry[-1]

    return entry, {}


class RulesetMatcher(object):
    def __init__(self, config_cache):
        super(RulesetMatcher, self).__init__()
        self._config_cache = config_cache

        self.ruleset_optimizer = RulesetOptimizier(config_cache)

        # Caches for host_extra_conf
        self._host_match_cache = {}

    def is_matching(self, hostname, ruleset):
        # type: (str, List[Dict]) -> bool
        """Compute outcome of a ruleset set that just says yes/no

        The binary match only cares about the first matching rule of an object.
        Depending on the value the outcome is negated or not.

        Replaces in_binary_hostlist / in_boolean_serviceconf_list"""
        for value in self.get_values(hostname, ruleset, is_binary=True):
            return value
        return False  # no match. Do not ignore

    def get_merged_dict(self, hostname, ruleset):
        # type: (str, List[Dict]) -> Dict
        """Returns a dictionary of the merged dict values of the matched rules
        The first dict setting a key defines the final value.

        Replaces host_extra_conf_merged / service_extra_conf_merged"""
        merged_dict = {}  # type: Dict
        for rule_dict in self.get_values(hostname, ruleset, is_binary=False):
            for key, value in rule_dict.items():
                merged_dict.setdefault(key, value)
        return merged_dict

    def get_values(self, hostname, ruleset, is_binary):
        # type: (str, List, bool) -> Generator
        """Returns a list of the values of the matched rules

        Replaces host_extra_conf / service_extra_conf"""

        # When the requested host is part of the local sites configuration,
        # then use only the sites hosts for processing the rules
        with_foreign_hosts = hostname not in self._config_cache.all_processed_hosts()
        cache_id = id(ruleset), with_foreign_hosts

        if cache_id in self._host_match_cache:
            cached = self._host_match_cache[cache_id]
        else:
            optimized_ruleset = self.ruleset_optimizer.get_host_ruleset(
                ruleset, with_foreign_hosts, is_binary=is_binary)

            cached = {}
            for value, hostname_list in optimized_ruleset:
                for other_hostname in hostname_list:
                    cached.setdefault(other_hostname, []).append(value)
            self._host_match_cache[cache_id] = cached

        for value in cached.get(hostname, []):
            yield value

    # TODO: Find a way to use the generic get_values
    def get_values_for_generic_agent_host(self, ruleset):
        """Compute ruleset for "generic" host

        This fictious host has no name and no tags. It matches all rules that
        do not require specific hosts or tags. But it matches rules that e.g.
        except specific hosts or tags (is not, has not set)
        """
        entries = []

        for rule in ruleset:
            rule, _rule_options = get_rule_options(rule)
            item, tags, hostlist = self.ruleset_optimizer.parse_host_rule(rule, is_binary=False)
            if tags and not hosttags_match_taglist([], tags):
                continue
            if not in_extraconf_hostlist(hostlist, ""):
                continue

            entries.append(item)
        return entries


class RulesetOptimizier(object):
    def __init__(self, config_cache):
        super(RulesetOptimizier, self).__init__()
        self._config_cache = config_cache

        self._service_ruleset_cache = {}
        self._host_ruleset_cache = {}
        self._all_matching_hosts_match_cache = {}

        # Reference dirname -> hosts in this dir including subfolders
        self._folder_host_lookup = {}
        # All used folders used for various set intersection operations
        self._folder_path_set = set()
        # Provides a list of hosts with the same hosttags, excluding the folder
        self._hosts_grouped_by_tags = {}
        # Reference hostname -> tag group reference
        self._host_grouped_ref = {}

        # TODO: The folder will not be part of new dict tags anymore. This can
        # be cleaned up then.
        self._hosttags_without_folder = {}

        # TODO: Clean this one up?
        self._initialize_host_lookup()

    def get_host_ruleset(self, ruleset, with_foreign_hosts, is_binary):
        cache_id = id(ruleset), with_foreign_hosts

        if cache_id in self._host_ruleset_cache:
            return self._host_ruleset_cache[cache_id]

        ruleset = self._convert_host_ruleset(ruleset, with_foreign_hosts, is_binary)
        self._host_ruleset_cache[cache_id] = ruleset
        return ruleset

    def _convert_host_ruleset(self, ruleset, with_foreign_hosts, is_binary):
        new_rules = []
        for rule in ruleset:
            rule, rule_options = get_rule_options(rule)
            if rule_options.get("disabled"):
                continue

            value, tags, hostlist = self.parse_host_rule(rule, is_binary)

            # Directly compute set of all matching hosts here, this
            # will avoid recomputation later
            new_rules.append((value, self._all_matching_hosts(tags, hostlist, with_foreign_hosts)))

        return new_rules

    def parse_host_rule(self, rule, is_binary):
        if is_binary:
            if rule[0] == NEGATE:  # this entry is logically negated
                value = False
                rule = rule[1:]
            else:
                value = True

            num_elements = len(rule)
            if num_elements == 1:
                hostlist = rule
                tags = []
            elif num_elements == 2:
                tags, hostlist = rule
            else:
                raise MKGeneralException("Invalid entry '%r' in configuration: "
                                         "must have 1 or 2 elements" % (rule,))
        else:
            num_elements = len(rule)
            if num_elements == 2:
                value, hostlist = rule
                tags = []
            elif num_elements == 3:
                value, tags, hostlist = rule
            else:
                raise MKGeneralException("Invalid entry '%r' in host configuration list: must "
                                         "have 2 or 3 entries" % (rule,))

        return value, tags, hostlist

    def get_service_ruleset(self, ruleset, with_foreign_hosts, is_binary):
        cache_id = id(ruleset), with_foreign_hosts

        if cache_id in self._service_ruleset_cache:
            return self._service_ruleset_cache[cache_id]

        cached_ruleset = self._convert_service_ruleset(
            ruleset, with_foreign_hosts=with_foreign_hosts, is_binary=is_binary)
        self._service_ruleset_cache[cache_id] = cached_ruleset
        return cached_ruleset

    def _convert_service_ruleset(self, ruleset, with_foreign_hosts, is_binary):
        new_rules = []
        for rule in ruleset:
            rule, rule_options = get_rule_options(rule)
            if rule_options.get("disabled"):
                continue

            if is_binary:
                if rule[0] == NEGATE:  # this entry is logically negated
                    value = False
                    rule = rule[1:]
                else:
                    value = True

                num_elements = len(rule)
                if num_elements == 2:
                    hostlist, servlist = rule
                    tags = []
                elif num_elements == 3:
                    tags, hostlist, servlist = rule
                else:
                    raise MKGeneralException("Invalid entry '%r' in configuration: "
                                             "must have 2 or 3 elements" % (rule,))
            else:
                num_elements = len(rule)
                if num_elements == 3:
                    value, hostlist, servlist = rule
                    tags = []
                elif num_elements == 4:
                    value, tags, hostlist, servlist = rule
                else:
                    raise MKGeneralException("Invalid rule '%r' in service configuration "
                                             "list: must have 3 or 4 elements" % (rule,))

            # Directly compute set of all matching hosts here, this
            # will avoid recomputation later
            hosts = self._all_matching_hosts(tags, hostlist, with_foreign_hosts)

            # And now preprocess the configured patterns in the servlist
            new_rules.append((value, hosts, convert_pattern_list(servlist)))

        return new_rules

    def _all_matching_hosts(self, tags, hostlist, with_foreign_hosts):
        """Returns a set containing the names of hosts that match the given
        tags and hostlist conditions."""
        cache_id = tuple(tags), tuple(hostlist), with_foreign_hosts

        try:
            return self._all_matching_hosts_match_cache[cache_id]
        except KeyError:
            pass

        if with_foreign_hosts:
            valid_hosts = self._config_cache.all_configured_hosts()
        else:
            valid_hosts = self._config_cache.all_processed_hosts()

        tags_set = set(tags)
        tags_set_without_folder = tags_set
        # TODO: Scope
        rule_path_set = tags_set.intersection(self._folder_path_set)
        tags_set_without_folder = tags_set - rule_path_set

        if rule_path_set:
            # More than one dynamic folder in one rule is simply wrong..
            rule_path = list(rule_path_set)[0]
        else:
            rule_path = "/+"

        # Thin out the valid hosts further. If the rule is located in a folder
        # we only need the intersection of the folders hosts and the previously determined valid_hosts
        valid_hosts = self.get_hosts_within_folder(rule_path,
                                                   with_foreign_hosts).intersection(valid_hosts)

        # Contains matched hosts

        if tags_set_without_folder and hostlist == ALL_HOSTS:
            return self._match_hosts_by_tags(cache_id, valid_hosts, tags_set_without_folder)

        matching = set([])
        only_specific_hosts = not bool([x for x in hostlist if x[0] in ["@", "!", "~"]])

        # If no tags are specified and there are only specific hosts we already have the matches
        if not tags_set_without_folder and only_specific_hosts:
            matching = valid_hosts.intersection(hostlist)
        # If no tags are specified and the hostlist only include @all (all hosts)
        elif not tags_set_without_folder and hostlist == ALL_HOSTS:
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
                if (not tags or hosttags_match_taglist(
                        self._config_cache.tag_list_of_host(hostname), tags_set_without_folder)):
                    if in_extraconf_hostlist(hostlist, hostname):
                        matching.add(hostname)

        self._all_matching_hosts_match_cache[cache_id] = matching
        return matching

    def _match_hosts_by_tags(self, cache_id, valid_hosts, tags_set_without_folder):
        matching = set([])
        has_specific_folder_tag = sum([x[0] == "/" for x in tags_set_without_folder])
        negative_match_tags = set()
        positive_match_tags = set()
        for tag in tags_set_without_folder:
            if tag[0] == "!":
                negative_match_tags.add(tag[1:])
            else:
                positive_match_tags.add(tag)

        if has_specific_folder_tag or self._config_cache.all_processed_hosts_similarity < 3:
            # Without shared folders
            for hostname in valid_hosts:
                tags = self._config_cache.tag_list_of_host(hostname)
                if not positive_match_tags - tags:
                    if not negative_match_tags.intersection(tags):
                        matching.add(hostname)

            self._all_matching_hosts_match_cache[cache_id] = matching
            return matching

        # With shared folders
        checked_hosts = set()
        for hostname in valid_hosts:
            if hostname in checked_hosts:
                continue

            hosts_with_same_tag = self._filter_hosts_with_same_tags_as_host(hostname, valid_hosts)
            checked_hosts.update(hosts_with_same_tag)

            tags = self._config_cache.tag_list_of_host(hostname)
            if not positive_match_tags - tags:
                if not negative_match_tags.intersection(tags):
                    matching.update(hosts_with_same_tag)

        self._all_matching_hosts_match_cache[cache_id] = matching
        return matching

    def _filter_hosts_with_same_tags_as_host(self, hostname, hosts):
        return self._hosts_grouped_by_tags[self._host_grouped_ref[hostname]].intersection(hosts)

    def get_hosts_within_folder(self, folder_path, with_foreign_hosts):
        cache_id = with_foreign_hosts, folder_path
        if cache_id not in self._folder_host_lookup:
            hosts_in_folder = set()
            # Strip off "+"
            folder_path_tmp = folder_path[:-1]
            relevant_hosts = self._config_cache.all_configured_hosts(
            ) if with_foreign_hosts else self._config_cache.all_processed_hosts()
            for hostname in relevant_hosts:
                if self._config_cache.host_path(hostname).startswith(folder_path_tmp):
                    hosts_in_folder.add(hostname)
            self._folder_host_lookup[cache_id] = hosts_in_folder
            return hosts_in_folder
        return self._folder_host_lookup[cache_id]

    def _initialize_host_lookup(self):
        # Determine hosts within folders
        # TODO: Cleanup this directory access for folder computation
        dirnames = [
            x[0][len(cmk.utils.paths.check_mk_config_dir):] + "/+"
            for x in os.walk(cmk.utils.paths.check_mk_config_dir)
        ]
        self._folder_path_set = set(dirnames)

        # Determine hosttags without folder tag
        for hostname in self._config_cache.all_configured_hosts():
            tags_without_folder = set(self._config_cache.tag_list_of_host(hostname))
            try:
                tags_without_folder.remove(self._config_cache.host_path(hostname))
            except KeyError:
                pass

            self._hosttags_without_folder[hostname] = tags_without_folder

        # Determine hosts with same tag setup (ignoring folder tag)
        for hostname in self._config_cache.all_configured_hosts():
            group_ref = tuple(sorted(self._hosttags_without_folder[hostname]))
            self._hosts_grouped_by_tags.setdefault(group_ref, set()).add(hostname)
            self._host_grouped_ref[hostname] = group_ref


def in_extraconf_hostlist(hostlist, hostname):
    """Whether or not the given host matches the hostlist.

    Entries in list are hostnames that must equal the hostname.
    Expressions beginning with ! are negated: if they match,
    the item is excluded from the list.

    Expressions beginning with ~ are treated as regular expression.
    Also the three special tags '@all', '@clusters', '@physical'
    are allowed.
    """

    # Migration help: print error if old format appears in config file
    # FIXME: When can this be removed?
    try:
        if hostlist[0] == "":
            raise MKGeneralException('Invalid empty entry [ "" ] in configuration')
    except IndexError:
        pass  # Empty list, no problem.

    for hostentry in hostlist:
        if hostentry == '':
            raise MKGeneralException('Empty hostname in host list %r' % hostlist)
        negate = False
        use_regex = False
        if hostentry[0] == '@':
            if hostentry == '@all':
                return True
            # TODO: Is not used anymore for a long time. Will be cleaned up
            # with 1.6 tuple ruleset cleanup
            #ic = is_cluster(hostname)
            #if hostentry == '@cluster' and ic:
            #    return True
            #elif hostentry == '@physical' and not ic:
            #    return True

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
                if regex(hostentry).match(hostname) is not None:
                    return not negate
        except MKGeneralException:
            if cmk.utils.debug.enabled():
                raise

    return False


def hosttags_match_taglist(hosttags, required_tags):
    """Check if a host fulfills the requirements of a tag list.

    The host must have all tags in the list, except
    for those negated with '!'. Those the host must *not* have!
    A trailing + means a prefix match."""
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


def convert_pattern_list(patterns):
    # type: (List[Text]) -> Tuple[bool, Pattern[Text]]
    """Compiles a list of service match patterns to a single regex

    Reducing the number of individual regex matches improves the performance dramatically.
    This function assumes either all or no pattern is negated (like WATO creates the rules).
    """
    if not patterns:
        return False, regex("")  # No pattern -> match everything

    pattern_parts = []
    negate = patterns[0].startswith("!")

    for pattern in patterns:
        # Skip ALL_SERVICES from end of negated lists
        if negate and pattern == ALL_SERVICES[0]:
            continue
        pattern_parts.append(_parse_negated(pattern)[1])

    return negate, regex("(?:%s)" % "|".join("(?:%s)" % p for p in pattern_parts))


def _parse_negated(pattern):
    # Allow negation of pattern with prefix '!'
    try:
        negate = pattern[0] == '!'
        if negate:
            pattern = pattern[1:]
    except IndexError:
        negate = False

    return negate, pattern


class RulesetToDictTransformer(object):
    """Transforms all rules in the given ruleset from the pre 1.6 tuple format to the dict format
    This is done in place to keep the references to the ruleset working.
    """

    def __init__(self, tag_to_group_map):
        super(RulesetToDictTransformer, self).__init__()
        self._tag_groups = tag_to_group_map

    def transform_in_place(self, ruleset, is_service, is_binary):
        for index, rule in enumerate(ruleset):
            if not isinstance(rule, dict):
                ruleset[index] = self._transform_rule(rule, is_service, is_binary)

    def _transform_rule(self, tuple_rule, is_service, is_binary):
        rule = {
            "condition": {},
        }

        tuple_rule = list(tuple_rule)

        # Extract optional rule_options from the end of the tuple
        if isinstance(tuple_rule[-1], dict):
            rule["options"] = tuple_rule.pop()

        # Extract value from front, if rule has a value
        if not is_binary:
            value = tuple_rule.pop(0)
        else:
            value = True
            if tuple_rule[0] == NEGATE:
                value = False
                tuple_rule = tuple_rule[1:]
        rule["value"] = value

        # Extract list of items from back, if rule has items
        service_condition = {}
        if is_service:
            service_condition = self._transform_item_list(tuple_rule.pop())

        # Rest is host list or tag list + host list
        host_condition = self._transform_host_conditions(tuple_rule)

        if "$or" in service_condition and "$or" in host_condition:
            rule["condition"] = {
                "$and": [
                    {
                        "$or": host_condition.pop("$or")
                    },
                    {
                        "$or": service_condition.pop("$or")
                    },
                ]
            }
        elif "$nor" in service_condition and "$nor" in host_condition:
            rule["condition"] = {
                "$and": [
                    {
                        "$nor": host_condition.pop("$nor")
                    },
                    {
                        "$nor": service_condition.pop("$nor")
                    },
                ]
            }

        rule["condition"].update(service_condition)
        rule["condition"].update(host_condition)

        return rule

    def _transform_item_list(self, item_list):
        if item_list == ALL_SERVICES:
            return {}

        if not item_list:
            return {"service_description": {"$in": []}}

        sub_conditions = []

        # Assume WATO conforming rule where either *all* or *none* of the
        # host expressions are negated.
        # TODO: This is WATO specific. Should we handle this like base did before?
        negate = item_list[0].startswith("!")

        # Remove ALL_SERVICES from end of negated lists
        if negate and item_list[-1] == ALL_SERVICES[0]:
            item_list = item_list[:-1]

        # Construct list of all item conditions
        for check_item in item_list:
            if check_item[0] == '!':  # strip negate character
                check_item = check_item[1:]
            check_item = "^" + check_item
            sub_conditions.append({"service_description": {"$regex": check_item}})

        return self._build_sub_condition("service_description", negate, "$regex", check_item,
                                         sub_conditions)

    def _transform_host_conditions(self, tuple_rule):
        if len(tuple_rule) == 1:
            host_tags = []
            host_list = tuple_rule[0]
        else:
            host_tags = tuple_rule[0]
            host_list = tuple_rule[1]

        condition = {}
        condition.update(self._transform_host_tags(host_tags))
        condition.update(self._transform_host_list(host_list))
        return condition

    def _transform_host_list(self, host_list):
        if host_list == ALL_HOSTS:
            return {}

        if not host_list:
            return {"host_name": {"$in": []}}

        sub_conditions = []

        # Assume WATO conforming rule where either *all* or *none* of the
        # host expressions are negated.
        # TODO: This is WATO specific. Should we handle this like base did before?
        negate = host_list[0].startswith("!")

        # Remove ALL_HOSTS from end of negated lists
        if negate and host_list[-1] == ALL_HOSTS[0]:
            host_list = host_list[:-1]

        num_conditions = len(host_list)
        has_regex = self._host_list_has_regex(host_list)

        # Simplify case where we only have full host name matches
        if not has_regex and num_conditions > 1:
            list_op = "$nin" if negate else "$in"
            return {"host_name": {list_op: [h.lstrip("!") for h in host_list]}}

        # Construct list of all host item conditions
        for check_item in host_list:
            if check_item[0] == '!':  # strip negate character
                check_item = check_item[1:]

            if check_item[0] == '~':
                check_item = "^" + check_item[1:]
                regex_match = True
            else:
                regex_match = False

            if check_item == CLUSTER_HOSTS[0]:
                raise MKGeneralException(
                    "Found a ruleset using CLUSTER_HOSTS as host condition. "
                    "This is not supported anymore. These rules can not be transformed "
                    "automatically to the new format. Please check out your configuration and "
                    "replace the rules in question.")
            if check_item == PHYSICAL_HOSTS[0]:
                raise MKGeneralException(
                    "Found a ruleset using PHYSICAL_HOSTS as host condition. "
                    "This is not supported anymore. These rules can not be transformed "
                    "automatically to the new format. Please check out your configuration and "
                    "replace the rules in question.")

            sub_op = "$regex" if regex_match else "$eq"

            sub_conditions.append({"host_name": {sub_op: check_item}})

        return self._build_sub_condition("host_name", negate, sub_op, check_item, sub_conditions)

    def _host_list_has_regex(self, host_list):
        for check_item in host_list:
            if check_item[0] == '!':  # strip negate character
                check_item = check_item[1:]

            if check_item[0] == '~':
                return True
        return False

    def _build_sub_condition(self, field, negate, sub_op, check_item, sub_conditions):
        """This function simplifies the constructed conditions

        - The or/nor condition is skipped where we only have a single condition
        - "$eq" is skipped where we only have a simple field equality match
        """
        if len(sub_conditions) == 1:
            if sub_op == "$eq":
                return {field: {"$ne": check_item} if negate else check_item}
            if sub_op == "$regex":
                if negate:
                    return {field: {"$not": {"$regex": check_item}}}
                return sub_conditions[0]
            raise NotImplementedError()

        op = "$nor" if negate else "$or"
        return {op: sub_conditions}

    def _transform_host_tags(self, host_tags):
        if not host_tags:
            return {}

        conditions = {}
        for tag_id in host_tags:
            # Folder is either not present (main folder) or in this format
            # "/abc/+" which matches on folder "abc" and all subfolders.
            if tag_id.startswith("/"):
                conditions["host_folder"] = {"$regex": "^%s" % tag_id.rstrip("+")}
                continue

            negate = False
            if tag_id[0] == '!':
                tag_id = tag_id[1:]
                negate = True

            # Assume it's an aux tag in case there is a tag configured without known group
            tag_group_id = self._tag_groups.get(tag_id, tag_id)

            conditions["host_tags." + tag_group_id] = {"$ne": tag_id} if negate else tag_id

        return conditions


def get_tag_to_group_map(tag_config):
    """The old rules only have a list of tags and don't know anything about the
    tag groups they are coming from. Create a map based on the current tag config
    """
    tag_id_to_tag_group_id_map = {}

    for aux_tag in tag_config.aux_tag_list.get_tags():
        tag_id_to_tag_group_id_map[aux_tag.id] = aux_tag.id

    for tag_group in tag_config.tag_groups:
        for grouped_tag in tag_group.tags:
            tag_id_to_tag_group_id_map[grouped_tag.id] = tag_group.id
    return tag_id_to_tag_group_id_map
