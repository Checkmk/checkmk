#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""This module provides generic Check_MK ruleset processing functionality"""

from typing import Any, cast, Dict, Generator, List, Optional, Pattern, Set, Tuple, TYPE_CHECKING

from cmk.utils.exceptions import MKGeneralException
from cmk.utils.parameters import boil_down_parameters
from cmk.utils.regex import regex
from cmk.utils.rulesets.tuple_rulesets import (
    ALL_HOSTS,
    ALL_SERVICES,
    CLUSTER_HOSTS,
    NEGATE,
    PHYSICAL_HOSTS,
)
from cmk.utils.tags import TagConfig
from cmk.utils.type_defs import (
    HostName,
    HostOrServiceConditions,
    HostOrServiceConditionsSimple,
    Labels,
    RuleConditionsSpec,
    Ruleset,
    RuleSpec,
    RuleValue,
    ServiceName,
    TagCondition,
    TagConditionNE,
    TagConditionNOR,
    TagConditionOR,
    TaggroupID,
    TaggroupIDToTagCondition,
    TagID,
    TagIDToTaggroupID,
    TagsOfHosts,
)

if TYPE_CHECKING:
    from cmk.utils.labels import LabelManager

LabelConditions = Dict  # TODO: Optimize this
PreprocessedHostRuleset = Dict[HostName, List[RuleValue]]
PreprocessedPattern = Tuple[bool, Pattern[str]]
PreprocessedServiceRuleset = List[
    Tuple[RuleValue, Set[HostName], LabelConditions, Tuple, PreprocessedPattern]
]


class RulesetMatchObject:
    """Wrapper around dict to ensure the ruleset match objects are correctly created"""

    __slots__ = ["host_name", "service_description", "service_labels", "service_cache_id"]

    def __init__(
        self,
        host_name: Optional[HostName] = None,
        service_description: Optional[ServiceName] = None,
        service_labels: Optional[Labels] = None,
    ) -> None:
        super().__init__()
        self.host_name = host_name
        self.service_description = service_description
        self.service_labels = service_labels
        self.service_cache_id = (
            self.service_description,
            self._generate_service_labels_hash(self.service_labels),
        )

    def _generate_service_labels_hash(self, service_labels: Optional[Labels]) -> int:
        return hash(None if service_labels is None else frozenset(service_labels.items()))

    def to_dict(self) -> Dict:
        # TODO: Two getattr()?
        return {k: getattr(self, k) for k in self.__slots__ if getattr(self, k) is not None}

    def copy(self) -> "RulesetMatchObject":
        return RulesetMatchObject(**self.to_dict())

    def __repr__(self) -> str:
        kwargs = ", ".join("%s=%r" % e for e in self.to_dict().items())
        return "RulesetMatchObject(%s)" % kwargs


class RulesetMatcher:
    """Performing matching on host / service rulesets

    There is some duplicate logic for host / service rulesets. This has been
    kept for performance reasons. Especially the service rulset matching is
    done very often in large setups. Be careful when working here.
    """

    def __init__(
        self,
        tag_to_group_map: TagIDToTaggroupID,
        host_tags: TagsOfHosts,
        host_paths: Dict[HostName, str],
        labels: "LabelManager",
        all_configured_hosts: Set[HostName],
        clusters_of: Dict[HostName, List[HostName]],
        nodes_of: Dict[HostName, List[HostName]],
    ) -> None:
        super().__init__()

        self.tuple_transformer = RulesetToDictTransformer(tag_to_group_map=tag_to_group_map)

        self.ruleset_optimizer = RulesetOptimizer(
            self,
            host_tags,
            host_paths,
            labels,
            all_configured_hosts,
            clusters_of,
            nodes_of,
        )

        self._service_match_cache: Dict = {}

    def is_matching_host_ruleset(self, match_object: RulesetMatchObject, ruleset: Ruleset) -> bool:
        """Compute outcome of a ruleset set that just says yes/no

        The binary match only cares about the first matching rule of an object.
        Depending on the value the outcome is negated or not.

        Replaces in_binary_hostlist / in_boolean_serviceconf_list"""
        for value in self.get_host_ruleset_values(match_object, ruleset, is_binary=True):
            return value
        return False  # no match. Do not ignore

    def get_host_ruleset_merged_dict(
        self, match_object: RulesetMatchObject, ruleset: Ruleset
    ) -> Dict[str, Any]:
        """Returns a dictionary of the merged dict values of the matched rules
        The first dict setting a key defines the final value.

        Replaces host_extra_conf_merged / service_extra_conf_merged"""
        merged = boil_down_parameters(
            self.get_host_ruleset_values(match_object, ruleset, is_binary=False), {}
        )
        assert isinstance(merged, dict)  # remove along with LegacyCheckParameters
        return merged

    def get_host_ruleset_values(
        self, match_object: RulesetMatchObject, ruleset: List, is_binary: bool
    ) -> Generator:
        """Returns a generator of the values of the matched rules
        Replaces host_extra_conf"""
        self.tuple_transformer.transform_in_place(ruleset, is_service=False, is_binary=is_binary)

        # When the requested host is part of the local sites configuration,
        # then use only the sites hosts for processing the rules
        with_foreign_hosts = (
            match_object.host_name not in self.ruleset_optimizer.all_processed_hosts()
        )

        optimized_ruleset = self.ruleset_optimizer.get_host_ruleset(
            ruleset, with_foreign_hosts, is_binary=is_binary
        )

        assert match_object.host_name is not None
        for value in optimized_ruleset.get(match_object.host_name, []):
            yield value

    def is_matching_service_ruleset(
        self, match_object: RulesetMatchObject, ruleset: Ruleset
    ) -> bool:
        """Compute outcome of a ruleset set that just says yes/no

        The binary match only cares about the first matching rule of an object.
        Depending on the value the outcome is negated or not.

        Replaces in_binary_hostlist / in_boolean_serviceconf_list"""
        for value in self.get_service_ruleset_values(match_object, ruleset, is_binary=True):
            return value
        return False  # no match. Do not ignore

    def get_service_ruleset_merged_dict(
        self, match_object: RulesetMatchObject, ruleset: Ruleset
    ) -> Dict[str, Any]:
        """Returns a dictionary of the merged dict values of the matched rules
        The first dict setting a key defines the final value.

        Replaces host_extra_conf_merged / service_extra_conf_merged"""
        merged = boil_down_parameters(
            self.get_service_ruleset_values(match_object, ruleset, is_binary=False), {}
        )
        assert isinstance(merged, dict)  # remove along with LegacyCheckParameters
        return merged

    def get_service_ruleset_values(
        self, match_object: RulesetMatchObject, ruleset: List, is_binary: bool
    ) -> Generator:
        """Returns a generator of the values of the matched rules
        Replaces service_extra_conf"""
        self.tuple_transformer.transform_in_place(ruleset, is_service=True, is_binary=is_binary)

        with_foreign_hosts = (
            match_object.host_name not in self.ruleset_optimizer.all_processed_hosts()
        )
        optimized_ruleset = self.ruleset_optimizer.get_service_ruleset(
            ruleset, with_foreign_hosts, is_binary=is_binary
        )

        for (
            value,
            hosts,
            service_labels_condition,
            service_labels_condition_cache_id,
            service_description_condition,
        ) in optimized_ruleset:
            if match_object.service_description is None:
                continue

            if match_object.host_name not in hosts:
                continue

            service_cache_id = (
                match_object.service_cache_id,
                service_description_condition,
                service_labels_condition_cache_id,
            )

            if service_cache_id in self._service_match_cache:
                match = self._service_match_cache[service_cache_id]
            else:
                match = self._matches_service_conditions(
                    service_description_condition, service_labels_condition, match_object
                )
                self._service_match_cache[service_cache_id] = match

            if match:
                yield value

    def _matches_service_conditions(
        self,
        service_description_condition: Tuple[bool, Pattern[str]],
        service_labels_condition: Dict[str, str],
        match_object: RulesetMatchObject,
    ) -> bool:
        if not self._matches_service_description_condition(
            service_description_condition, match_object
        ):
            return False

        if service_labels_condition and not matches_labels(
            match_object.service_labels, service_labels_condition
        ):
            return False

        return True

    def _matches_service_description_condition(
        self,
        service_description_condition: Tuple[bool, Pattern[str]],
        match_object: RulesetMatchObject,
    ) -> bool:
        negate, pattern = service_description_condition

        if (
            match_object.service_description is not None
            and pattern.match(match_object.service_description) is not None
        ):
            return not negate
        return negate

    # TODO: Find a way to use the generic get_host_ruleset_values
    def get_values_for_generic_agent_host(self, ruleset: Ruleset) -> List[RuleValue]:
        """Compute ruleset for "generic" host

        This fictious host has no name and no tags. It matches all rules that
        do not require specific hosts or tags. But it matches rules that e.g.
        except specific hosts or tags (is not, has not set)
        """
        self.tuple_transformer.transform_in_place(ruleset, is_service=False, is_binary=False)
        entries = []
        for rule in ruleset:
            if _is_disabled(rule):
                continue

            hostlist = rule["condition"].get("host_name")
            tags = rule["condition"].get("host_tags", {})
            labels = rule["condition"].get("host_labels", {})
            rule_path = rule["condition"].get("host_folder", "/")

            if rule_path != "/":
                continue

            if tags and not self.ruleset_optimizer.matches_host_tags(set(), tags):
                continue

            if labels and not matches_labels({}, labels):
                continue

            if not self.ruleset_optimizer.matches_host_name(hostlist, ""):
                continue

            entries.append(rule["value"])
        return entries


class RulesetOptimizer:
    """Performs some precalculations on the configured rulesets to improve the
    processing performance"""

    def __init__(
        self,
        ruleset_matcher: RulesetMatcher,
        host_tags: TagsOfHosts,
        host_paths: Dict[HostName, str],
        labels: "LabelManager",
        all_configured_hosts: Set[HostName],
        clusters_of: Dict[HostName, List[HostName]],
        nodes_of: Dict[HostName, List[HostName]],
    ) -> None:
        super().__init__()
        self._ruleset_matcher = ruleset_matcher
        self._labels = labels
        self._host_tags = {hn: set(tags_of_host.items()) for hn, tags_of_host in host_tags.items()}
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
        self._all_processed_hosts_similarity = 1.0

        self._service_ruleset_cache: Dict = {}
        self._host_ruleset_cache: Dict = {}
        self._all_matching_hosts_match_cache: Dict = {}

        # Reference dirname -> hosts in this dir including subfolders
        self._folder_host_lookup: Dict[Tuple[bool, str], Set[HostName]] = {}

        # Provides a list of hosts with the same hosttags, excluding the folder
        self._hosts_grouped_by_tags: Dict[Tuple[Tuple[TaggroupID, TagID], ...], Set[HostName]] = {}
        # Reference hostname -> tag group reference
        self._host_grouped_ref: Dict[HostName, Tuple[Tuple[TaggroupID, TagID], ...]] = {}

        # TODO: Clean this one up?
        self._initialize_host_lookup()

    def clear_ruleset_caches(self) -> None:
        self._host_ruleset_cache.clear()
        self._service_ruleset_cache.clear()

    def clear_caches(self) -> None:
        self._host_ruleset_cache.clear()
        self._all_matching_hosts_match_cache.clear()

    def all_processed_hosts(self) -> Set[HostName]:
        """Returns a set of all processed hosts"""
        return self._all_processed_hosts

    def set_all_processed_hosts(self, all_processed_hosts: Set[HostName]) -> None:
        self._all_processed_hosts = set(all_processed_hosts)

        nodes_and_clusters: Set[HostName] = set()
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

    def _adjust_processed_hosts_similarity(self) -> None:
        """This function computes the tag similarities between of the processed hosts
        The result is a similarity factor, which helps finding the most perfomant operation
        for the current hostset"""
        used_groups = {
            self._host_grouped_ref.get(hostname, ()) for hostname in self._all_processed_hosts
        }

        if not used_groups:
            self._all_processed_hosts_similarity = 1.0
            return

        self._all_processed_hosts_similarity = (
            1.0 * len(self._all_processed_hosts) / len(used_groups)
        )

    def get_host_ruleset(
        self, ruleset: Ruleset, with_foreign_hosts: bool, is_binary: bool
    ) -> PreprocessedHostRuleset:
        cache_id = id(ruleset), with_foreign_hosts

        if cache_id in self._host_ruleset_cache:
            return self._host_ruleset_cache[cache_id]

        host_ruleset = self._convert_host_ruleset(ruleset, with_foreign_hosts, is_binary)
        self._host_ruleset_cache[cache_id] = host_ruleset
        return host_ruleset

    def _convert_host_ruleset(
        self, ruleset: Ruleset, with_foreign_hosts: bool, is_binary: bool
    ) -> PreprocessedHostRuleset:
        """Precompute host lookup map

        Instead of a ruleset like list structure with precomputed host lists we compute a
        direct map for hostname based lookups for the matching rule values
        """
        host_values: PreprocessedHostRuleset = {}
        for rule in ruleset:
            if _is_disabled(rule):
                continue

            for hostname in self._all_matching_hosts(rule["condition"], with_foreign_hosts):
                host_values.setdefault(hostname, []).append(rule["value"])

        return host_values

    def get_service_ruleset(
        self, ruleset: Ruleset, with_foreign_hosts: bool, is_binary: bool
    ) -> PreprocessedServiceRuleset:
        cache_id = id(ruleset), with_foreign_hosts

        if cache_id in self._service_ruleset_cache:
            return self._service_ruleset_cache[cache_id]

        cached_ruleset = self._convert_service_ruleset(
            ruleset, with_foreign_hosts=with_foreign_hosts, is_binary=is_binary
        )
        self._service_ruleset_cache[cache_id] = cached_ruleset
        return cached_ruleset

    def _convert_service_ruleset(
        self, ruleset: Ruleset, with_foreign_hosts: bool, is_binary: bool
    ) -> PreprocessedServiceRuleset:
        new_rules: PreprocessedServiceRuleset = []
        for rule in ruleset:
            if _is_disabled(rule):
                continue

            # Directly compute set of all matching hosts here, this will avoid
            # recomputation later
            hosts = self._all_matching_hosts(rule["condition"], with_foreign_hosts)

            # Prepare cache id
            service_labels_condition = rule["condition"].get("service_labels", {})
            service_labels_condition_cache_id = tuple(
                (label_id, _tags_or_labels_cache_id(label_spec))
                for label_id, label_spec in service_labels_condition.items()
            )

            # And now preprocess the configured patterns in the servlist
            new_rules.append(
                (
                    rule["value"],
                    hosts,
                    service_labels_condition,
                    service_labels_condition_cache_id,
                    self._convert_pattern_list(rule["condition"].get("service_description")),
                )
            )
        return new_rules

    def _convert_pattern_list(
        self, patterns: Optional[HostOrServiceConditions]
    ) -> PreprocessedPattern:
        """Compiles a list of service match patterns to a to a single regex

        Reducing the number of individual regex matches improves the performance dramatically.
        This function assumes either all or no pattern is negated (like WATO creates the rules).
        """
        if not patterns:
            return False, regex("")  # Match everything

        negate, parsed_patterns = parse_negated_condition_list(patterns)

        pattern_parts = []
        for p in parsed_patterns:
            if isinstance(p, dict):
                pattern_parts.append(p["$regex"])
            else:
                pattern_parts.append(p)

        return negate, regex("(?:%s)" % "|".join("(?:%s)" % p for p in pattern_parts))

    def _all_matching_hosts(
        self, condition: RuleConditionsSpec, with_foreign_hosts: bool
    ) -> Set[HostName]:
        """Returns a set containing the names of hosts that match the given
        tags and hostlist conditions."""
        hostlist = condition.get("host_name")
        tag_conditions: TaggroupIDToTagCondition = condition.get("host_tags", {})
        labels = condition.get("host_labels", {})
        rule_path = condition.get("host_folder", "/")

        cache_id = (
            self._condition_cache_id(
                hostlist,
                tag_conditions,
                labels,
                rule_path,
            ),
            with_foreign_hosts,
        )

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
        valid_hosts = self.get_hosts_within_folder(rule_path, with_foreign_hosts).intersection(
            valid_hosts
        )

        if tag_conditions and hostlist is None and not labels:
            # TODO: Labels could also be optimized like the tags
            matched_by_tags = self._match_hosts_by_tags(cache_id, valid_hosts, tag_conditions)
            if matched_by_tags is not None:
                return matched_by_tags

        matching: Set[HostName] = set()
        only_specific_hosts = (
            hostlist is not None
            and not isinstance(hostlist, dict)
            and all(not isinstance(x, dict) for x in hostlist)
        )

        if hostlist == []:
            pass  # Empty host list -> Nothing matches

        elif not tag_conditions and not labels and not hostlist:
            # If no tags are specified and the hostlist only include @all (all hosts)
            matching = valid_hosts

        elif not tag_conditions and not labels and only_specific_hosts and hostlist is not None:
            # If no tags are specified and there are only specific hosts we already have the matches
            matching = valid_hosts.intersection(hostlist)

        else:
            # If the rule has only exact host restrictions, we can thin out the list of hosts to check
            if only_specific_hosts and hostlist is not None:
                hosts_to_check = valid_hosts.intersection(hostlist)
            else:
                hosts_to_check = valid_hosts

            for hostname in hosts_to_check:
                # When no tag matching is requested, do not filter by tags. Accept all hosts
                # and filter only by hostlist
                if tag_conditions and not self.matches_host_tags(
                    self._host_tags[hostname],
                    tag_conditions,
                ):
                    continue

                if labels:
                    host_labels = self._labels.labels_of_host(self._ruleset_matcher, hostname)
                    if not matches_labels(host_labels, labels):
                        continue

                if not self.matches_host_name(hostlist, hostname):
                    continue

                matching.add(hostname)

        self._all_matching_hosts_match_cache[cache_id] = matching
        return matching

    def matches_host_name(
        self, host_entries: Optional[HostOrServiceConditions], hostname: HostName
    ) -> bool:
        if not host_entries:
            return True

        negate, host_entries = parse_negated_condition_list(host_entries)
        if hostname == "":  # -> generic agent host
            return negate

        for entry in host_entries:
            if not isinstance(entry, dict) and hostname == entry:
                return not negate

            if isinstance(entry, dict) and regex(entry["$regex"]).match(hostname) is not None:
                return not negate

        return negate

    def matches_host_tags(
        self,
        hosttags: Set[Tuple[TaggroupID, TagID]],
        required_tags: TaggroupIDToTagCondition,
    ) -> bool:
        return all(
            matches_tag_condition(taggroup_id, tag_condition, hosttags)
            for taggroup_id, tag_condition in required_tags.items()
        )

    # TODO: improve and cleanup types
    def _condition_cache_id(
        self,
        hostlist: Optional[HostOrServiceConditions],
        tag_conditions: TaggroupIDToTagCondition,
        labels: Any,
        rule_path: Any,
    ) -> Tuple[Tuple[str, ...], Tuple[Tuple[str, Any], ...], Tuple[Tuple[Any, Any], ...], Any]:
        host_parts: List[str] = []

        if hostlist is not None:
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
            tuple(
                (taggroup_id, _tags_or_labels_cache_id(tag_condition))
                for taggroup_id, tag_condition in tag_conditions.items()
            ),
            tuple(
                (label_id, _tags_or_labels_cache_id(label_spec))
                for label_id, label_spec in labels.items()
            ),
            rule_path,
        )

    # TODO: Generalize this optimization: Build some kind of key out of the tag conditions
    # (positive, negative, ...). Make it work with the new tag group based "$or" handling.
    def _match_hosts_by_tags(
        self,
        cache_id,
        valid_hosts: Set[HostName],
        tag_conditions: TaggroupIDToTagCondition,
    ):
        matching = set()
        negative_match_tags = set()
        positive_match_tags = set()
        for taggroup_id, tag_condition in tag_conditions.items():
            if isinstance(tag_condition, dict):
                if "$ne" in tag_condition:
                    negative_match_tags.add(
                        (
                            taggroup_id,
                            cast(TagConditionNE, tag_condition)["$ne"],
                        )
                    )
                    continue

                if "$or" in tag_condition:
                    return None  # Can not be optimized, makes _all_matching_hosts proceed

                if "$nor" in tag_condition:
                    return None  # Can not be optimized, makes _all_matching_hosts proceed

                raise NotImplementedError()

            positive_match_tags.add((taggroup_id, tag_condition))

        # TODO:
        # if has_specific_folder_tag or self._all_processed_hosts_similarity < 3.0:
        if self._all_processed_hosts_similarity < 3.0:
            # Without shared folders
            for hostname in valid_hosts:
                if positive_match_tags <= self._host_tags[
                    hostname
                ] and not negative_match_tags.intersection(self._host_tags[hostname]):
                    matching.add(hostname)

            self._all_matching_hosts_match_cache[cache_id] = matching
            return matching

        # With shared folders
        checked_hosts: Set[str] = set()
        for hostname in valid_hosts:
            if hostname in checked_hosts:
                continue

            hosts_with_same_tag = self._filter_hosts_with_same_tags_as_host(hostname, valid_hosts)
            checked_hosts.update(hosts_with_same_tag)

            if positive_match_tags <= self._host_tags[
                hostname
            ] and not negative_match_tags.intersection(self._host_tags[hostname]):
                matching.update(hosts_with_same_tag)

        self._all_matching_hosts_match_cache[cache_id] = matching
        return matching

    def _filter_hosts_with_same_tags_as_host(
        self,
        hostname: HostName,
        hosts: Set[HostName],
    ):
        return self._hosts_grouped_by_tags[self._host_grouped_ref[hostname]].intersection(hosts)

    def get_hosts_within_folder(self, folder_path: str, with_foreign_hosts: bool) -> Set[HostName]:
        cache_id = with_foreign_hosts, folder_path
        if cache_id not in self._folder_host_lookup:
            hosts_in_folder = set()
            relevant_hosts = (
                self._all_configured_hosts if with_foreign_hosts else self._all_processed_hosts
            )

            for hostname in relevant_hosts:
                host_path = self._host_paths.get(hostname, "/")
                if host_path.startswith(folder_path):
                    hosts_in_folder.add(hostname)

            self._folder_host_lookup[cache_id] = hosts_in_folder
            return hosts_in_folder

        return self._folder_host_lookup[cache_id]

    def _initialize_host_lookup(self):
        for hostname in self._all_configured_hosts:
            group_ref = tuple(sorted(self._host_tags[hostname]))
            self._hosts_grouped_by_tags.setdefault(group_ref, set()).add(hostname)
            self._host_grouped_ref[hostname] = group_ref


def _tags_or_labels_cache_id(tag_or_label_spec):
    if isinstance(tag_or_label_spec, dict):
        if "$ne" in tag_or_label_spec:
            return "!%s" % tag_or_label_spec["$ne"]

        if "$or" in tag_or_label_spec:
            return (
                "$or",
                tuple(
                    _tags_or_labels_cache_id(sub_tag_or_label_spec)
                    for sub_tag_or_label_spec in tag_or_label_spec["$or"]
                ),
            )

        if "$nor" in tag_or_label_spec:
            return (
                "$nor",
                tuple(
                    _tags_or_labels_cache_id(sub_tag_or_label_spec)
                    for sub_tag_or_label_spec in tag_or_label_spec["$nor"]
                ),
            )

        raise NotImplementedError("Invalid tag / label spec: %r" % tag_or_label_spec)

    return tag_or_label_spec


def matches_tag_condition(
    taggroup_id: TaggroupID,
    tag_condition: TagCondition,
    hosttags: Set[Tuple[TaggroupID, TagID]],
) -> bool:
    if isinstance(tag_condition, dict):
        if "$ne" in tag_condition:
            return (
                taggroup_id,
                cast(TagConditionNE, tag_condition)["$ne"],
            ) not in hosttags

        if "$or" in tag_condition:
            return any(
                (
                    taggroup_id,
                    opt_tag_id,
                )
                in hosttags
                for opt_tag_id in cast(
                    TagConditionOR,
                    tag_condition,
                )["$or"]
            )

        if "$nor" in tag_condition:
            return not hosttags.intersection(
                {
                    (
                        taggroup_id,
                        opt_tag_id,
                    )
                    for opt_tag_id in cast(
                        TagConditionNOR,
                        tag_condition,
                    )["$nor"]
                }
            )

        raise NotImplementedError()

    return (
        taggroup_id,
        tag_condition,
    ) in hosttags


def matches_labels(object_labels, required_labels) -> bool:
    for label_group_id, label_spec in required_labels.items():
        is_not = isinstance(label_spec, dict)
        if is_not:
            label_spec = label_spec["$ne"]

        if (object_labels.get(label_group_id) == label_spec) is is_not:
            return False

    return True


def parse_negated_condition_list(
    entries: HostOrServiceConditions,
) -> Tuple[bool, HostOrServiceConditionsSimple]:
    if isinstance(entries, dict) and "$nor" in entries:
        return True, entries["$nor"]
    if isinstance(entries, list):
        return False, entries
    raise ValueError("unsupported conditions")


class RulesetToDictTransformer:
    """Transforms all rules in the given ruleset from the pre 1.6 tuple format to the dict format
    This is done in place to keep the references to the ruleset working.
    """

    def __init__(self, tag_to_group_map: TagIDToTaggroupID) -> None:
        super().__init__()
        self._tag_groups = tag_to_group_map
        self._transformed_ids: Set[int] = set()

    def transform_in_place(self, ruleset, is_service, is_binary, use_ruleset_id_cache=True):
        if use_ruleset_id_cache:
            ruleset_id = id(ruleset)
            if ruleset_id in self._transformed_ids:
                return

        for index, rule in enumerate(ruleset):
            if not isinstance(rule, dict):
                ruleset[index] = self._transform_rule(rule, is_service, is_binary)

        if use_ruleset_id_cache:
            self._transformed_ids.add(ruleset_id)

    def _transform_rule(self, tuple_rule, is_service, is_binary):
        rule: Dict[str, Any] = {
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
                if check_item[0] == "!":  # strip negate character
                    check_item = check_item[1:]
                else:
                    raise NotImplementedError(
                        "Mixed negate / not negated rule found but not supported"
                    )
            elif check_item[0] == "!":
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

        condition: Dict[str, str] = {}
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
            if check_item[0] == "!":  # strip negate character
                check_item = check_item[1:]

            if check_item[0] == "~":
                sub_conditions.append({"$regex": check_item[1:]})
                continue

            if check_item == CLUSTER_HOSTS[0]:
                raise MKGeneralException(
                    "Found a ruleset using CLUSTER_HOSTS as host condition. "
                    "This is not supported anymore. These rules can not be transformed "
                    "automatically to the new format. Please check out your configuration and "
                    "replace the rules in question."
                )
            if check_item == PHYSICAL_HOSTS[0]:
                raise MKGeneralException(
                    "Found a ruleset using PHYSICAL_HOSTS as host condition. "
                    "This is not supported anymore. These rules can not be transformed "
                    "automatically to the new format. Please check out your configuration and "
                    "replace the rules in question."
                )

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
            if tag_id[0] == "!":
                tag_id = tag_id[1:]
                negate = True

            # Assume it's an aux tag in case there is a tag configured without known group
            tag_group_id = self._tag_groups.get(tag_id, tag_id)

            tag_conditions[tag_group_id] = {"$ne": tag_id} if negate else tag_id

        if tag_conditions:
            conditions["host_tags"] = tag_conditions

        return conditions


def get_tag_to_group_map(tag_config: TagConfig) -> TagIDToTaggroupID:
    """The old rules only have a list of tags and don't know anything about the
    tag groups they are coming from. Create a map based on the current tag config
    """
    tag_id_to_tag_group_id_map = {}

    for aux_tag in tag_config.aux_tag_list.get_tags():
        tag_id_to_tag_group_id_map[aux_tag.id] = aux_tag.id

    for tag_group in tag_config.tag_groups:
        for grouped_tag in tag_group.tags:
            # Do not care for the choices with a None value here. They are not relevant for this map
            if grouped_tag.id is not None:
                tag_id_to_tag_group_id_map[grouped_tag.id] = tag_group.id
    return tag_id_to_tag_group_id_map


def _is_disabled(rule: RuleSpec) -> bool:
    # TODO consolidate with cmk.gui.watolib.rulesets.py::Rule::is_disabled
    return "options" in rule and bool(rule["options"].get("disabled", False))
