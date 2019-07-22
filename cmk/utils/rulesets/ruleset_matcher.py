#!/usr/bin/env python2
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2016             mk@mathias-kettner.de |
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
"""This module provides generic Check_MK ruleset processing functionality"""

from typing import Any, Set, Optional, Generator, Dict, Text, Pattern, Tuple, List  # pylint: disable=unused-import

from cmk.utils.rulesets.tuple_rulesets import (
    ALL_HOSTS,
    ALL_SERVICES,
    CLUSTER_HOSTS,
    PHYSICAL_HOSTS,
    NEGATE,
)
from cmk.utils.regex import regex
from cmk.utils.exceptions import MKGeneralException


class RulesetMatchObject(object):
    """Wrapper around dict to ensure the ruleset match objects are correctly created"""
    __slots__ = ["host_name", "host_tags", "host_folder", "host_labels", "service_description"]

    def __init__(self,
                 host_name=None,
                 host_tags=None,
                 host_folder=None,
                 host_labels=None,
                 service_description=None):
        # type: (Optional[str], Optional[Dict[Text, Text]], Optional[str], Optional[Dict[Text, Text]], Optional[Text]) -> None
        super(RulesetMatchObject, self).__init__()
        self.host_name = host_name
        self.host_tags = host_tags
        self.host_folder = host_folder
        self.host_labels = host_labels
        self.service_description = service_description

    def to_dict(self):
        # type: () -> Dict
        # TODO: Two getattr()?
        return {k: getattr(self, k) for k in self.__slots__ if getattr(self, k) is not None}

    def copy(self):
        return RulesetMatchObject(**self.to_dict())

    def __repr__(self):
        kwargs = ", ".join(["%s=%r" % e for e in self.to_dict().iteritems()])
        return "RulesetMatchObject(%s)" % kwargs

    def service_cache_id(self):
        # type: () -> Tuple
        return (self.service_description,)


class RulesetMatcher(object):
    """Performing matching on host / service rulesets

    There is some duplicate logic for host / service rulesets. This has been
    kept for performance reasons. Especially the service rulset matching is
    done very often in large setups. Be careful when working here.
    """
    def __init__(self, tag_to_group_map, host_tag_lists, host_paths, labels, all_configured_hosts,
                 clusters_of, nodes_of):
        super(RulesetMatcher, self).__init__()

        self.tuple_transformer = RulesetToDictTransformer(tag_to_group_map=tag_to_group_map)

        self.ruleset_optimizer = RulesetOptimizer(
            self,
            host_tag_lists,
            host_paths,
            labels,
            all_configured_hosts,
            clusters_of,
            nodes_of,
        )

        self._service_match_cache = {}

    def is_matching_host_ruleset(self, match_object, ruleset):
        # type: (RulesetMatchObject, List[Dict]) -> bool
        """Compute outcome of a ruleset set that just says yes/no

        The binary match only cares about the first matching rule of an object.
        Depending on the value the outcome is negated or not.

        Replaces in_binary_hostlist / in_boolean_serviceconf_list"""
        for value in self.get_host_ruleset_values(match_object, ruleset, is_binary=True):
            return value
        return False  # no match. Do not ignore

    def get_host_ruleset_merged_dict(self, match_object, ruleset):
        # type: (RulesetMatchObject, List[Dict]) -> Dict
        """Returns a dictionary of the merged dict values of the matched rules
        The first dict setting a key defines the final value.

        Replaces host_extra_conf_merged / service_extra_conf_merged"""
        merged_dict = {}  # type: Dict
        for rule_dict in self.get_host_ruleset_values(match_object, ruleset, is_binary=False):
            for key, value in rule_dict.items():
                merged_dict.setdefault(key, value)
        return merged_dict

    def get_host_ruleset_values(self, match_object, ruleset, is_binary):
        # type: (RulesetMatchObject, List, bool) -> Generator
        """Returns a generator of the values of the matched rules
        Replaces host_extra_conf"""
        self.tuple_transformer.transform_in_place(ruleset, is_service=False, is_binary=is_binary)

        # When the requested host is part of the local sites configuration,
        # then use only the sites hosts for processing the rules
        with_foreign_hosts = match_object.host_name not in \
                                self.ruleset_optimizer.all_processed_hosts()
        optimized_ruleset = self.ruleset_optimizer.get_host_ruleset(ruleset,
                                                                    with_foreign_hosts,
                                                                    is_binary=is_binary)

        for value in optimized_ruleset.get(match_object.host_name, []):
            yield value

    def is_matching_service_ruleset(self, match_object, ruleset):
        # type: (RulesetMatchObject, List[Dict]) -> bool
        """Compute outcome of a ruleset set that just says yes/no

        The binary match only cares about the first matching rule of an object.
        Depending on the value the outcome is negated or not.

        Replaces in_binary_hostlist / in_boolean_serviceconf_list"""
        for value in self.get_service_ruleset_values(match_object, ruleset, is_binary=True):
            return value
        return False  # no match. Do not ignore

    def get_service_ruleset_merged_dict(self, match_object, ruleset):
        # type: (RulesetMatchObject, List[Dict]) -> Dict
        """Returns a dictionary of the merged dict values of the matched rules
        The first dict setting a key defines the final value.

        Replaces host_extra_conf_merged / service_extra_conf_merged"""
        merged_dict = {}  # type: Dict
        for rule_dict in self.get_service_ruleset_values(match_object, ruleset, is_binary=False):
            for key, value in rule_dict.items():
                merged_dict.setdefault(key, value)
        return merged_dict

    def get_service_ruleset_values(self, match_object, ruleset, is_binary):
        # type: (RulesetMatchObject, List, bool) -> Generator
        """Returns a generator of the values of the matched rules
        Replaces service_extra_conf"""
        self.tuple_transformer.transform_in_place(ruleset, is_service=True, is_binary=is_binary)

        with_foreign_hosts = match_object.host_name not in \
                                self.ruleset_optimizer.all_processed_hosts()
        optimized_ruleset = self.ruleset_optimizer.get_service_ruleset(ruleset,
                                                                       with_foreign_hosts,
                                                                       is_binary=is_binary)

        for value, hosts, service_description_condition in optimized_ruleset:
            if match_object.host_name not in hosts:
                continue

            if match_object.service_description is None:
                continue

            service_cache_id = (match_object.service_cache_id(), service_description_condition)
            if service_cache_id in self._service_match_cache:
                match = self._service_match_cache[service_cache_id]
            else:
                match = self._matches_service_conditions(service_description_condition,
                                                         match_object.service_description)
                self._service_match_cache[service_cache_id] = match

            if match:
                yield value

    def _matches_service_conditions(self, service_description_condition, service_description):
        # type: (Tuple[bool, Pattern[Text]], Text) -> bool
        negate, pattern = service_description_condition
        if pattern.match(service_description) is not None:
            return not negate
        return negate

    # TODO: Find a way to use the generic get_values
    def get_values_for_generic_agent_host(self, ruleset):
        """Compute ruleset for "generic" host

        This fictious host has no name and no tags. It matches all rules that
        do not require specific hosts or tags. But it matches rules that e.g.
        except specific hosts or tags (is not, has not set)
        """
        self.tuple_transformer.transform_in_place(ruleset, is_service=False, is_binary=False)
        entries = []
        for rule in ruleset:
            if "options" in rule and "disabled" in rule["options"]:
                continue

            hostlist = rule["condition"].get("host_name")
            tags = rule["condition"].get("host_tags", {})
            labels = rule["condition"].get("host_labels", {})

            if tags and not self.ruleset_optimizer.matches_host_tags([], tags):
                continue

            if labels and not _matches_labels({}, labels):
                continue

            if not self.ruleset_optimizer.matches_host_name(hostlist, ""):
                continue

            entries.append(rule["value"])
        return entries


class RulesetOptimizer(object):
    """Performs some precalculations on the configured rulesets to improve the
    processing performance"""
    def __init__(self, ruleset_matcher, host_tag_lists, host_paths, labels, all_configured_hosts,
                 clusters_of, nodes_of):
        super(RulesetOptimizer, self).__init__()
        self._ruleset_matcher = ruleset_matcher
        self._labels = labels
        self._host_tag_lists = host_tag_lists
        self._host_paths = host_paths
        self._clusters_of = clusters_of
        self._nodes_of = nodes_of

        self._all_configured_hosts = all_configured_hosts

        # Contains all hostnames which are currently relevant for this cache
        # Most of the time all_processed hosts is similar to all_active_hosts
        # Howewer, in a multiprocessing environment all_processed_hosts only
        # may contain a reduced set of hosts, since each process handles a subset
        self._all_processed_hosts = self._all_configured_hosts

        # A factor which indicates how much hosts share the same host tag configuration (excluding folders).
        # len(all_processed_hosts) / len(different tag combinations)
        # It is used to determine the best rule evualation method
        self._all_processed_hosts_similarity = 1

        self._service_ruleset_cache = {}
        self._host_ruleset_cache = {}
        self._all_matching_hosts_match_cache = {}

        # Reference dirname -> hosts in this dir including subfolders
        self._folder_host_lookup = {}
        # Provides a list of hosts with the same hosttags, excluding the folder
        self._hosts_grouped_by_tags = {}
        # Reference hostname -> tag group reference
        self._host_grouped_ref = {}

        # TODO: The folder will not be part of new dict tags anymore. This can
        # be cleaned up then.
        self._hosttags_without_folder = {}

        # TODO: Clean this one up?
        self._initialize_host_lookup()

    def all_processed_hosts(self):
        # type: () -> Set[str]
        """Returns a set of all processed hosts"""
        return self._all_processed_hosts

    def set_all_processed_hosts(self, all_processed_hosts):
        self._all_processed_hosts = set(all_processed_hosts)

        nodes_and_clusters = set()
        for hostname in self._all_processed_hosts:
            nodes_and_clusters.update(self._nodes_of.get(hostname, []))
            nodes_and_clusters.update(self._clusters_of.get(hostname, []))

        # Only add references to configured hosts
        nodes_and_clusters.intersection_update(self._all_configured_hosts)

        self._all_processed_hosts.update(nodes_and_clusters)

        # The folder host lookup includes a list of all -processed- hosts within a given
        # folder. Any update with set_all_processed hosts invalidates this cache, because
        # the scope of relevant hosts has changed. This is -good-, since the values in this
        # lookup are iterated one by one later on in all_matching_hosts
        self._folder_host_lookup = {}

        self._adjust_processed_hosts_similarity()

    def _adjust_processed_hosts_similarity(self):
        """ This function computes the tag similarities between of the processed hosts
        The result is a similarity factor, which helps finding the most perfomant operation
        for the current hostset """
        used_groups = set()
        for hostname in self._all_processed_hosts:
            used_groups.add(self._host_grouped_ref[hostname])

        if not used_groups:
            self._all_processed_hosts_similarity = 1
            return

        self._all_processed_hosts_similarity = (1.0 * len(self._all_processed_hosts) /
                                                len(used_groups))

    def get_host_ruleset(self, ruleset, with_foreign_hosts, is_binary):
        cache_id = id(ruleset), with_foreign_hosts

        if cache_id in self._host_ruleset_cache:
            return self._host_ruleset_cache[cache_id]

        ruleset = self._convert_host_ruleset(ruleset, with_foreign_hosts, is_binary)
        self._host_ruleset_cache[cache_id] = ruleset
        return ruleset

    def _convert_host_ruleset(self, ruleset, with_foreign_hosts, is_binary):
        """Precompute host lookup map

        Instead of a ruleset like list structure with precomputed host lists we compute a
        direct map for hostname based lookups for the matching rule values
        """
        host_values = {}
        for rule in ruleset:
            if "options" in rule and "disabled" in rule["options"]:
                continue

            for hostname in self._all_matching_hosts(rule["condition"], with_foreign_hosts):
                host_values.setdefault(hostname, []).append(rule["value"])

        return host_values

    def get_service_ruleset(self, ruleset, with_foreign_hosts, is_binary):
        cache_id = id(ruleset), with_foreign_hosts

        if cache_id in self._service_ruleset_cache:
            return self._service_ruleset_cache[cache_id]

        cached_ruleset = self._convert_service_ruleset(ruleset,
                                                       with_foreign_hosts=with_foreign_hosts,
                                                       is_binary=is_binary)
        self._service_ruleset_cache[cache_id] = cached_ruleset
        return cached_ruleset

    def _convert_service_ruleset(self, ruleset, with_foreign_hosts, is_binary):
        new_rules = []
        for rule in ruleset:
            if "options" in rule and "disabled" in rule["options"]:
                continue

            # Directly compute set of all matching hosts here, this will avoid
            # recomputation later
            hosts = self._all_matching_hosts(rule["condition"], with_foreign_hosts)

            # And now preprocess the configured patterns in the servlist
            new_rules.append(
                (rule["value"], hosts,
                 self._convert_pattern_list(rule["condition"].get("service_description"))))

        return new_rules

    def _convert_pattern_list(self, patterns):
        # type: (List[Text]) -> Tuple[bool, Pattern[Text]]
        """Compiles a list of service match patterns to a to a single regex

        Reducing the number of individual regex matches improves the performance dramatically.
        This function assumes either all or no pattern is negated (like WATO creates the rules).
        """
        if not patterns:
            return False, regex(u"")  # Match everything

        negate, patterns = parse_negated_condition_list(patterns)

        pattern_parts = []
        for p in patterns:
            if isinstance(p, dict):
                pattern_parts.append(p["$regex"])
            else:
                pattern_parts.append(p)

        return negate, regex("(?:%s)" % "|".join("(?:%s)" % p for p in pattern_parts))

    def _all_matching_hosts(self, condition, with_foreign_hosts):
        # type: (Dict[str, Any], bool) -> Set[str]
        """Returns a set containing the names of hosts that match the given
        tags and hostlist conditions."""
        hostlist = condition.get("host_name")
        tags = condition.get("host_tags", {})
        labels = condition.get("host_labels", {})
        rule_path = condition.get("host_folder", "/")

        cache_id = self._condition_cache_id(hostlist, tags, labels, rule_path), with_foreign_hosts

        try:
            return self._all_matching_hosts_match_cache[cache_id]
        except KeyError:
            pass

        if with_foreign_hosts:
            valid_hosts = self._all_configured_hosts
        else:
            valid_hosts = self._all_processed_hosts

        # Thin out the valid hosts further. If the rule is located in a folder
        # we only need the intersection of the folders hosts and the previously determined valid_hosts
        valid_hosts = self.get_hosts_within_folder(rule_path,
                                                   with_foreign_hosts).intersection(valid_hosts)

        if tags and hostlist is None and not labels:
            # TODO: Labels could also be optimized like the tags
            matched_by_tags = self._match_hosts_by_tags(cache_id, valid_hosts, tags)
            if matched_by_tags is not None:
                return matched_by_tags

        matching = set()  # type: Set[str]
        only_specific_hosts = hostlist is not None \
            and not isinstance(hostlist, dict) \
            and all(not isinstance(x, dict) for x in hostlist)

        if hostlist == []:
            pass  # Empty host list -> Nothing matches
        elif not tags and not labels and not hostlist:
            # If no tags are specified and the hostlist only include @all (all hosts)
            matching = valid_hosts
        elif not tags and not labels and only_specific_hosts:
            # If no tags are specified and there are only specific hosts we already have the matches
            matching = valid_hosts.intersection(hostlist)
        else:
            # If the rule has only exact host restrictions, we can thin out the list of hosts to check
            if only_specific_hosts:
                hosts_to_check = valid_hosts.intersection(hostlist)
            else:
                hosts_to_check = valid_hosts

            for hostname in hosts_to_check:
                # When no tag matching is requested, do not filter by tags. Accept all hosts
                # and filter only by hostlist
                if tags and not self.matches_host_tags(self._host_tag_lists[hostname], tags):
                    continue

                if labels:
                    host_labels = self._labels.labels_of_host(self._ruleset_matcher, hostname)
                    if not _matches_labels(host_labels, labels):
                        continue

                if not self.matches_host_name(hostlist, hostname):
                    continue

                matching.add(hostname)

        self._all_matching_hosts_match_cache[cache_id] = matching
        return matching

    def matches_host_name(self, host_entries, hostname):
        if not host_entries:
            return True

        negate, host_entries = parse_negated_condition_list(host_entries)

        for entry in host_entries:
            use_regex = isinstance(entry, dict)

            if hostname is True:  # -> generic agent host
                continue

            if not use_regex and hostname == entry:
                return not negate

            if use_regex and regex(entry["$regex"]).match(hostname) is not None:
                return not negate

        return negate

    def matches_host_tags(self, hosttags, required_tags):
        for tag_spec in required_tags.values():
            if self._matches_tag_spec(tag_spec, hosttags) is False:
                return False

        return True

    def _matches_tag_spec(self, tag_spec, hosttags):
        is_not = False
        if isinstance(tag_spec, dict):
            if "$ne" in tag_spec:
                is_not = True
                tag_spec = tag_spec["$ne"]

            elif "$or" in tag_spec:
                return any(
                    self._matches_tag_spec(sub_tag_spec, hosttags)
                    for sub_tag_spec in tag_spec["$or"])

            elif "$nor" in tag_spec:
                return not any(
                    self._matches_tag_spec(sub_tag_spec, hosttags)
                    for sub_tag_spec in tag_spec["$nor"])

            else:
                raise NotImplementedError()

        matches = tag_spec in hosttags
        if matches == is_not:
            return False

        return True

    def _condition_cache_id(self, hostlist, tags, labels, rule_path):
        host_parts = []

        if hostlist is None:
            host_parts.append(None)
        else:
            negate, hostlist = parse_negated_condition_list(hostlist)
            if negate:
                host_parts.append("!")

            for h in hostlist:
                if isinstance(h, dict):
                    if "$regex" not in h:
                        raise NotImplementedError()
                    host_parts.append("~%s" % h["$regex"])
                    continue

                host_parts.append(h)

        return (
            tuple(sorted(host_parts)),
            tuple((tag_id, _tags_or_labels_cache_id(tag_spec))
                  for tag_id, tag_spec in tags.iteritems()),
            tuple((label_id, _tags_or_labels_cache_id(label_spec))
                  for label_id, label_spec in labels.iteritems()),
            rule_path,
        )

    # TODO: Generalize this optimization: Build some kind of key out of the tag conditions
    # (positive, negative, ...). Make it work with the new tag group based "$or" handling.
    def _match_hosts_by_tags(self, cache_id, valid_hosts, tags):
        matching = set()
        negative_match_tags = set()
        positive_match_tags = set()
        for tag in tags.values():
            if isinstance(tag, dict):
                if "$ne" in tag:
                    negative_match_tags.add(tag["$ne"])
                    continue

                if "$or" in tag:
                    return None  # Can not be optimized, makes _all_matching_hosts proceed

                if "$nor" in tag:
                    return None  # Can not be optimized, makes _all_matching_hosts proceed

                raise NotImplementedError()

            positive_match_tags.add(tag)

        # TODO:
        #if has_specific_folder_tag or self._all_processed_hosts_similarity < 3:
        if self._all_processed_hosts_similarity < 3:
            # Without shared folders
            for hostname in valid_hosts:
                host_tags = self._host_tag_lists[hostname]
                if not positive_match_tags - host_tags:
                    if not negative_match_tags.intersection(host_tags):
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

            tags = self._host_tag_lists[hostname]
            if not positive_match_tags - tags:
                if not negative_match_tags.intersection(tags):
                    matching.update(hosts_with_same_tag)

        self._all_matching_hosts_match_cache[cache_id] = matching
        return matching

    def _filter_hosts_with_same_tags_as_host(self, hostname, hosts):
        return self._hosts_grouped_by_tags[self._host_grouped_ref[hostname]].intersection(hosts)

    def get_hosts_within_folder(self, folder_path, with_foreign_hosts):
        # type: (str, bool) -> Set[str]
        cache_id = with_foreign_hosts, folder_path
        if cache_id not in self._folder_host_lookup:
            hosts_in_folder = set()
            relevant_hosts = self._all_configured_hosts if with_foreign_hosts else self._all_processed_hosts

            for hostname in relevant_hosts:
                host_path = self._host_paths.get(hostname, "/")
                if host_path.startswith(folder_path):
                    hosts_in_folder.add(hostname)

            self._folder_host_lookup[cache_id] = hosts_in_folder
            return hosts_in_folder

        return self._folder_host_lookup[cache_id]

    def _initialize_host_lookup(self):
        # Determine hosttags without folder tag
        for hostname in self._all_configured_hosts:
            tags_without_folder = set(self._host_tag_lists[hostname])
            try:
                tags_without_folder.remove(self._host_paths.get(hostname, "/"))
            except (KeyError, ValueError):
                pass

            self._hosttags_without_folder[hostname] = tags_without_folder

        # Determine hosts with same tag setup (ignoring folder tag)
        for hostname in self._all_configured_hosts:
            group_ref = tuple(sorted(self._hosttags_without_folder[hostname]))
            self._hosts_grouped_by_tags.setdefault(group_ref, set()).add(hostname)
            self._host_grouped_ref[hostname] = group_ref


def _tags_or_labels_cache_id(tag_or_label_spec):
    if isinstance(tag_or_label_spec, dict):
        if "$ne" in tag_or_label_spec:
            return "!%s" % tag_or_label_spec["$ne"]

        if "$or" in tag_or_label_spec:
            return ("$or",
                    tuple(
                        _tags_or_labels_cache_id(sub_tag_or_label_spec)
                        for sub_tag_or_label_spec in tag_or_label_spec["$or"]))

        if "$nor" in tag_or_label_spec:
            return ("$nor",
                    tuple(
                        _tags_or_labels_cache_id(sub_tag_or_label_spec)
                        for sub_tag_or_label_spec in tag_or_label_spec["$nor"]))

        raise NotImplementedError("Invalid tag / label spec: %r" % tag_or_label_spec)

    return tag_or_label_spec


def _matches_labels(object_labels, required_labels):
    for label_group_id, label_spec in required_labels.iteritems():
        is_not = isinstance(label_spec, dict)
        if is_not:
            label_spec = label_spec["$ne"]

        if (object_labels.get(label_group_id) == label_spec) is is_not:
            return False

    return True


def parse_negated_condition_list(entries):
    negate = False
    if isinstance(entries, dict) and "$nor" in entries:
        negate = True
        entries = entries["$nor"]
    return negate, entries


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

        rule["condition"].update(service_condition)
        rule["condition"].update(host_condition)

        return rule

    def _transform_item_list(self, item_list):
        if item_list == ALL_SERVICES:
            return {}

        if not item_list:
            return {"service_description": []}

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
            if negate:
                if check_item[0] == '!':  # strip negate character
                    check_item = check_item[1:]
                else:
                    raise NotImplementedError(
                        "Mixed negate / not negated rule found but not supported")
            elif check_item[0] == '!':
                raise NotImplementedError("Mixed negate / not negated rule found but not supported")

            sub_conditions.append({"$regex": check_item})

        if negate:
            return {"service_description": {"$nor": sub_conditions}}
        return {"service_description": sub_conditions}

    def _transform_host_conditions(self, tuple_rule):
        if len(tuple_rule) == 1:
            host_tags = []
            host_list = tuple_rule[0]
        else:
            host_tags = tuple_rule[0]
            host_list = tuple_rule[1]

        condition = {}
        condition.update(self.transform_host_tags(host_tags))
        condition.update(self._transform_host_list(host_list))
        return condition

    def _transform_host_list(self, host_list):
        if host_list == ALL_HOSTS:
            return {}

        if not host_list:
            return {"host_name": []}

        sub_conditions = []

        # Assume WATO conforming rule where either *all* or *none* of the
        # host expressions are negated.
        # TODO: This is WATO specific. Should we handle this like base did before?
        negate = host_list[0].startswith("!")

        # Remove ALL_HOSTS from end of negated lists
        if negate and host_list[-1] == ALL_HOSTS[0]:
            host_list = host_list[:-1]

        # Construct list of all host item conditions
        for check_item in host_list:
            if check_item[0] == '!':  # strip negate character
                check_item = check_item[1:]

            if check_item[0] == '~':
                sub_conditions.append({"$regex": check_item[1:]})
                continue

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

            sub_conditions.append(check_item)

        if negate:
            return {"host_name": {"$nor": sub_conditions}}
        return {"host_name": sub_conditions}

    def transform_host_tags(self, host_tags):
        if not host_tags:
            return {}

        conditions = {}
        tag_conditions = {}
        for tag_id in host_tags:
            # Folder is either not present (main folder) or in this format
            # "/abc/+" which matches on folder "abc" and all subfolders.
            if tag_id.startswith("/"):
                conditions["host_folder"] = tag_id.rstrip("+")
                continue

            negate = False
            if tag_id[0] == '!':
                tag_id = tag_id[1:]
                negate = True

            # Assume it's an aux tag in case there is a tag configured without known group
            tag_group_id = self._tag_groups.get(tag_id, tag_id)

            tag_conditions[tag_group_id] = {"$ne": tag_id} if negate else tag_id

        if tag_conditions:
            conditions["host_tags"] = tag_conditions

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
