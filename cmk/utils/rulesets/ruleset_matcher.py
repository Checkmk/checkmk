#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""This module provides generic Check_MK ruleset processing functionality"""

import contextlib
from collections.abc import Callable, Iterable, Iterator, Mapping, Sequence
from re import Pattern
from typing import (
    Any,
    cast,
    Generic,
    NotRequired,
    TypeAlias,
    TypedDict,
    TypeGuard,
    TypeVar,
)

from cmk.ccc.hostaddress import HostAddress, HostName

from cmk.utils.global_ident_type import GlobalIdent
from cmk.utils.labels import (
    AndOrNotLiteral,
    LabelGroups,
    Labels,
)
from cmk.utils.parameters import merge_parameters
from cmk.utils.regex import combine_patterns, regex
from cmk.utils.servicename import Item, ServiceName
from cmk.utils.tags import TagGroupID, TagID

from cmk import trace

from .conditions import HostOrServiceConditions, HostOrServiceConditionsSimple

tracer = trace.get_tracer()

RulesetName = str  # Could move to a less cluttered module as it is often used on its own.
TRuleValue = TypeVar("TRuleValue")

# The Tag* types below are *not* used in `cmk.utils.tags`
# but they are used here.  Therefore, they do *not* belong
# in `cmk.utils.tags`.  This is _not a bug_!

TagConditionNE = TypedDict(
    "TagConditionNE",
    {
        "$ne": TagID | None,
    },
)
TagConditionOR = TypedDict(
    "TagConditionOR",
    {
        "$or": Sequence[TagID | None],
    },
)
TagConditionNOR = TypedDict(
    "TagConditionNOR",
    {
        "$nor": Sequence[TagID | None],
    },
)
TagCondition = TagID | None | TagConditionNE | TagConditionOR | TagConditionNOR


def is_tag_condition_or(condition: TagCondition) -> TypeGuard[TagConditionOR]:
    return isinstance(condition, dict) and "$or" in condition


def is_tag_condition_nor(condition: TagCondition) -> TypeGuard[TagConditionNOR]:
    return isinstance(condition, dict) and "$nor" in condition


def is_tag_condition_ne(condition: TagCondition) -> TypeGuard[TagConditionNE]:
    return isinstance(condition, dict) and "$ne" in condition


def is_tag_condition_tag_id(condition: TagCondition) -> TypeGuard[TagID]:
    return isinstance(condition, str)


# Here, we have data structures such as
# {'ip-v4': {'$ne': 'ip-v4'}, 'snmp_ds': {'$nor': ['no-snmp', 'snmp-v1']}, 'taggroup_02': None, 'aux_tag_01': 'aux_tag_01', 'address_family': 'ip-v4-only'}
type TagsOfHosts = Mapping[HostName | HostAddress, Mapping[TagGroupID, TagID]]

LabelGroupsCacheId = tuple[tuple[AndOrNotLiteral, tuple[tuple[AndOrNotLiteral, str], ...]], ...]

PreprocessedPattern: TypeAlias = tuple[bool, Pattern[str]]

type _PreprocessedServiceRule[TRuleValue] = tuple[
    TRuleValue,
    set[HostName],
    LabelGroups,
    LabelGroupsCacheId,
    PreprocessedPattern,
]

# FIXME: A lot of signatures regarding rules and rule sets are simply lying:
# They claim to expect a RuleConditionsSpec or Ruleset, but
# they are silently handling a very chaotic tuple-based structure, too. We
# really, really need to fix all those signatures! Some test cases for tuples are in
# test_tuple_rulesets.py. They contain horrible hand-made types...


# TODO: Improve this type
class RuleOptionsSpec(TypedDict, total=True):
    disabled: NotRequired[bool]
    description: NotRequired[str]
    comment: NotRequired[str]
    docu_url: NotRequired[str]
    predefined_condition_id: NotRequired[str]


# TODO: Improve this type
class RuleConditionsSpec(TypedDict, total=True):
    host_tags: NotRequired[Mapping[TagGroupID, TagCondition]]
    host_label_groups: NotRequired[LabelGroups]
    host_name: NotRequired[HostOrServiceConditions | None]
    service_description: NotRequired[HostOrServiceConditions | None]
    service_label_groups: NotRequired[LabelGroups]
    host_folder: NotRequired[str]


class RuleSpec(Generic[TRuleValue], TypedDict):
    value: TRuleValue
    condition: RuleConditionsSpec
    id: str  # a UUID if provided by either the GUI or the REST API
    options: NotRequired[RuleOptionsSpec]
    locked_by: NotRequired[GlobalIdent]


def is_disabled(rule: RuleSpec[TRuleValue]) -> bool:
    # TODO consolidate with cmk.gui.watolib.rulesets.py::Rule::is_disabled
    return "options" in rule and bool(rule["options"].get("disabled", False))


class RulesetMatcher:
    """Performing matching on host / service rulesets

    There is some duplicate logic for host / service rulesets. This has been
    kept for performance reasons. Especially the service rulset matching is
    done very often in large setups. Be careful when working here.
    """

    def __init__(
        self,
        host_tags: TagsOfHosts,
        host_paths: Mapping[HostName, str],
        all_configured_hosts: frozenset[HostName],
        clusters_of: Mapping[HostName, Sequence[HostName]],
        nodes_of: Mapping[HostName, Sequence[HostName]],
    ) -> None:
        super().__init__()

        self.ruleset_optimizer = RulesetOptimizer(
            self,
            host_tags,
            host_paths,
            all_configured_hosts,
            clusters_of,
            nodes_of,
        )

        self._service_match_cache: dict[
            tuple[
                tuple[ServiceName | None, int], PreprocessedPattern, tuple[tuple[str, object], ...]
            ],
            object,
        ] = {}

    def clear_caches(self) -> None:
        # clear caches that don't work properly (the ruleset optimizer ignores host labels).
        # self._service_match_cache works also in the case of changed labels, so we DON'T need to clear it.
        self.ruleset_optimizer.clear_caches()

    def get_host_bool_value(
        self,
        hostname: HostName,
        ruleset: Sequence[RuleSpec[bool]],
        labels_of_host: Callable[[HostName], Labels],
    ) -> bool:
        """Compute outcome of a ruleset set that just says yes/no

        The binary match only cares about the first matching rule of an object.
        Depending on the value the outcome is negated or not.

        """
        for value in self.get_host_values(hostname, ruleset, labels_of_host):
            # Next line may be controlled by `is_binary` in which case we
            # should overload the function instead of asserting to check
            # during typing instead of runtime.
            assert isinstance(value, bool)
            return value
        return False  # no match. Do not ignore

    def get_host_merged_dict(
        self,
        hostname: HostName,
        ruleset: Sequence[RuleSpec[Mapping[str, TRuleValue]]],
        labels_of_host: Callable[[HostName], Labels],
    ) -> Mapping[str, TRuleValue]:
        """Returns a dictionary of the merged dict values of the matched rules
        The first dict setting a key defines the final value.

        """
        return merge_parameters(self.get_host_values(hostname, ruleset, labels_of_host), default={})

    def get_host_values(
        self,
        hostname: HostName | HostAddress,
        ruleset: Sequence[RuleSpec[TRuleValue]],
        labels_of_host: Callable[[HostName], Labels],
    ) -> Sequence[TRuleValue]:
        """Returns a generator of the values of the matched rules."""

        return self.ruleset_optimizer.get_host_ruleset(hostname, ruleset, labels_of_host)

    def get_service_bool_value(
        self,
        hostname: HostName,
        service_name: ServiceName,
        service_labels: Labels,
        ruleset: Sequence[RuleSpec[TRuleValue]],
        labels_of_host: Callable[[HostName], Labels],
    ) -> bool:
        """Compute outcome of a ruleset set that just says yes/no

        The binary match only cares about the first matching rule of an object.
        Depending on the value the outcome is negated or not.

        """
        for value in self._get_service_ruleset_values(
            hostname, service_name, service_labels, ruleset, labels_of_host
        ):
            # See `get_host_bool_value()`.
            assert isinstance(value, bool)
            return value
        return False

    def get_service_merged_dict(
        self,
        hostname: HostName,
        service_name: ServiceName,
        service_labels: Labels,
        ruleset: Sequence[RuleSpec[Mapping[str, TRuleValue]]],
        labels_of_host: Callable[[HostName], Labels],
    ) -> Mapping[str, TRuleValue]:
        """Returns a dictionary of the merged dict values of the matched rules
        The first dict setting a key defines the final value.

        """
        return merge_parameters(
            list(
                self._get_service_ruleset_values(
                    hostname, service_name, service_labels, ruleset, labels_of_host
                )
            ),
            default={},
        )

    def service_extra_conf(
        self,
        hostname: HostName,
        service_name: ServiceName,
        service_labels: Labels,
        ruleset: Sequence[RuleSpec[TRuleValue]],
        labels_of_host: Callable[[HostName], Labels],
    ) -> list[TRuleValue]:
        """Compute outcome of a service rule set that has an item."""
        return list(
            self._get_service_ruleset_values(
                hostname, service_name, service_labels, ruleset, labels_of_host
            )
        )

    def get_checkgroup_ruleset_values(
        self,
        hostname: HostName,
        item: Item,
        service_labels: Labels,
        ruleset: Sequence[RuleSpec[TRuleValue]],
        labels_of_host: Callable[[HostName], Labels],
    ) -> list[TRuleValue]:
        with tracer.span(
            "RulesetMatcher_get_checkgroup_ruleset_values",
            attributes={
                "cmk.host_name": hostname,
                "cmk.item": repr(item),
                "cmk.ruleset": repr(ruleset),
            },
        ):
            return list(
                self._get_service_ruleset_values(
                    hostname,
                    item,
                    service_labels,
                    ruleset,
                    labels_of_host,
                )
            )

    def _get_service_ruleset_values(
        self,
        host_name: HostName,
        match_text: ServiceName | Item,
        service_labels: Labels,
        ruleset: Sequence[RuleSpec[TRuleValue]],
        labels_of_host: Callable[[HostName], Labels],
    ) -> Iterator[TRuleValue]:
        """Returns a generator of the values of the matched rules"""
        optimized_ruleset = self.ruleset_optimizer.get_service_ruleset(
            host_name, ruleset, labels_of_host
        )

        for (
            value,
            hosts,
            service_label_groups,
            service_label_groups_cache_id,
            service_description_condition,
        ) in optimized_ruleset:
            if match_text is None:
                continue

            if host_name not in hosts:
                continue

            service_cache_id = (
                (
                    match_text,
                    hash(None if service_labels is None else frozenset(service_labels.items())),
                ),
                service_description_condition,
                service_label_groups_cache_id,
            )

            if service_cache_id in self._service_match_cache:
                match = self._service_match_cache[service_cache_id]
            else:
                match = _matches_service_conditions(
                    service_description_condition,
                    service_label_groups,
                    match_text,
                    service_labels,
                )
                self._service_match_cache[service_cache_id] = match

            if match:
                yield value


# TODO: improve and cleanup types
_ConditionCacheID: TypeAlias = tuple[
    tuple[str, ...],
    tuple[tuple[TagGroupID, object], ...],
    LabelGroupsCacheId,
    str,
]


class RulesetOptimizer:
    """Performs some precalculations on the configured rulesets to improve the
    processing performance"""

    def __init__(
        self,
        ruleset_matcher: RulesetMatcher,
        host_tags: TagsOfHosts,
        host_paths: Mapping[HostName, str],
        all_configured_hosts: frozenset[HostName],
        clusters_of: Mapping[HostName, Sequence[HostName]],
        nodes_of: Mapping[HostName, Sequence[HostName]],
    ) -> None:
        super().__init__()
        self._ruleset_matcher = ruleset_matcher
        self._host_tags = {hn: set(tags_of_host.items()) for hn, tags_of_host in host_tags.items()}
        self._host_paths = host_paths
        self._clusters_of = clusters_of
        self._nodes_of = nodes_of

        self._all_configured_hosts = all_configured_hosts

        # Contains all hostnames which are currently relevant for this cache.
        # Every active host or a subset of the active hosts when multiprocessing
        # is enabled.
        self._all_processed_hosts = self._all_configured_hosts

        # A factor which indicates how much hosts share the same host tag configuration (excluding folders).
        # len(all_processed_hosts) / len(different tag combinations)
        # It is used to determine the best rule evualation method
        self._all_processed_hosts_similarity = 1.0

        self.__service_ruleset_cache: dict[
            tuple[int, bool], Sequence[_PreprocessedServiceRule[Any]]
        ] = {}
        self.__host_ruleset_cache: dict[tuple[int, bool], Mapping[HostAddress, Sequence[Any]]] = {}
        self._all_matching_hosts_match_cache: dict[
            tuple[_ConditionCacheID, bool], set[HostName]
        ] = {}

        # Reference dirname -> hosts in this dir including subfolders
        self._folder_host_lookup: dict[tuple[bool, str], set[HostName]] = {}

        # Provides a list of hosts with the same hosttags, excluding the folder
        self._hosts_grouped_by_tags: dict[tuple[tuple[TagGroupID, TagID], ...], set[HostName]] = {}
        # Reference hostname -> tag group reference
        self._host_grouped_ref: dict[HostName, tuple[tuple[TagGroupID, TagID], ...]] = {}

        # TODO: Clean this one up?
        self._initialize_host_lookup()

    def clear_ruleset_caches(self) -> None:
        self.__host_ruleset_cache.clear()
        self.__service_ruleset_cache.clear()

    def clear_caches(self) -> None:
        self.__host_ruleset_cache.clear()
        self._all_matching_hosts_match_cache.clear()

    def set_all_processed_hosts(self, all_processed_hosts: set[HostName]) -> None:
        involved_clusters: set[HostName] = set()
        involved_nodes: set[HostName] = set()
        for hostname in self._all_processed_hosts:
            involved_nodes.update(self._nodes_of.get(hostname, []))
            involved_clusters.update(self._clusters_of.get(hostname, []))

        # Also add all nodes of used clusters
        for hostname in involved_clusters:
            involved_nodes.update(self._nodes_of.get(hostname, []))

        nodes_and_clusters = involved_clusters | involved_nodes | all_processed_hosts

        # Only add references to configured hosts
        nodes_and_clusters.intersection_update(self._all_configured_hosts)
        self._all_processed_hosts = frozenset(nodes_and_clusters)

        # The folder host lookup includes a list of all -processed- hosts within a given
        # folder. Any update with set_all_processed hosts invalidates this cache, because
        # the scope of relevant hosts has changed. This is -good-, since the values in this
        # lookup are iterated one by one later on in all_matching_hosts
        self._folder_host_lookup = {}

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
        self,
        host_name: HostName,
        ruleset: Sequence[RuleSpec[TRuleValue]],
        labels_of_host: Callable[[HostName], Labels],
    ) -> Sequence[TRuleValue]:
        def _impl(
            ruleset: Iterable[RuleSpec[TRuleValue]], with_foreign_hosts: bool
        ) -> Mapping[HostAddress, Sequence[TRuleValue]]:
            host_values: dict[HostAddress, list[TRuleValue]] = {}
            for rule in ruleset:
                if is_disabled(rule):
                    continue

                for hostname in self._all_matching_hosts(
                    rule["condition"], with_foreign_hosts, labels_of_host
                ):
                    host_values.setdefault(hostname, []).append(rule["value"])

            return host_values

        # When the requested host is part of the local sites configuration,
        # then use only the sites hosts for processing the rules
        with_foreign_hosts = host_name not in self._all_processed_hosts

        cache_id = id(ruleset), with_foreign_hosts
        try:
            optimized_ruleset = self.__host_ruleset_cache[cache_id]
        except KeyError:
            optimized_ruleset = self.__host_ruleset_cache.setdefault(
                cache_id, _impl(ruleset, with_foreign_hosts)
            )
        return optimized_ruleset.get(host_name, [])

    def get_service_ruleset(
        self,
        host_name: HostName,
        ruleset: Sequence[RuleSpec[TRuleValue]],
        labels_of_host: Callable[[HostName], Labels],
    ) -> Sequence[_PreprocessedServiceRule[TRuleValue]]:
        def _impl(
            ruleset: Iterable[RuleSpec[TRuleValue]], with_foreign_hosts: bool
        ) -> Sequence[_PreprocessedServiceRule[TRuleValue]]:
            new_rules: list[_PreprocessedServiceRule[TRuleValue]] = []
            for rule in ruleset:
                if is_disabled(rule):
                    continue

                # Directly compute set of all matching hosts here, this will avoid
                # recomputation later
                hosts = self._all_matching_hosts(
                    rule["condition"], with_foreign_hosts, labels_of_host
                )

                # Prepare cache id
                service_label_groups: LabelGroups = rule["condition"].get(
                    "service_label_groups", []
                )
                # cast lists in label groups to tuples
                service_label_groups_cache_id = tuple(
                    (operator, tuple(label_group)) for operator, label_group in service_label_groups
                )

                # And now preprocess the configured patterns in the servlist
                new_rules.append(
                    (
                        rule["value"],
                        hosts,
                        service_label_groups,
                        service_label_groups_cache_id,
                        RulesetOptimizer._convert_pattern_list(
                            rule["condition"].get("service_description")
                        ),
                    )
                )
            return new_rules

        with_foreign_hosts = host_name not in self._all_processed_hosts

        cache_id = id(ruleset), with_foreign_hosts
        with contextlib.suppress(KeyError):
            return self.__service_ruleset_cache[cache_id]

        return self.__service_ruleset_cache.setdefault(cache_id, _impl(ruleset, with_foreign_hosts))

    @staticmethod
    def _convert_pattern_list(patterns: HostOrServiceConditions | None) -> PreprocessedPattern:
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

        return negate, regex(combine_patterns(pattern_parts))

    def _all_matching_hosts(
        self,
        condition: RuleConditionsSpec,
        with_foreign_hosts: bool,
        labels_of_host: Callable[[HostName], Labels],
    ) -> set[HostName]:
        """Returns a set containing the names of hosts that match the given
        tags and hostlist conditions."""
        host_conditions = condition.get("host_name")
        tag_conditions: Mapping[TagGroupID, TagCondition] = condition.get("host_tags", {})
        label_conditions: LabelGroups = condition.get("host_label_groups", [])
        rule_path = condition.get("host_folder", "/")

        cache_id = (
            RulesetOptimizer._condition_cache_id(
                host_conditions,
                tag_conditions,
                label_conditions,
                rule_path,
            ),
            with_foreign_hosts,
        )

        try:
            return self._all_matching_hosts_match_cache[cache_id]
        except KeyError:
            pass

        return self._all_matching_hosts_match_cache.setdefault(
            cache_id,
            self._all_matching_hosts_computation(
                # Determine match candidates.
                # If the rule is located in a folder we only need the hosts in that folder.
                self._get_hosts_within_folder(rule_path, with_foreign_hosts),
                host_conditions,
                tag_conditions,
                label_conditions,
                labels_of_host,
            ),
        )

    def _all_matching_hosts_computation(
        self,
        hosts_in_rule_scope: set[HostName],
        host_conditions: HostOrServiceConditions | None,
        tag_conditions: Mapping[TagGroupID, TagCondition],
        label_conditions: LabelGroups,
        labels_of_host: Callable[[HostName], Labels],
    ) -> set[HostName]:
        if tag_conditions and host_conditions is None and not label_conditions:
            # TODO: Labels could also be optimized like the tags
            matched_by_tags = self._match_hosts_by_tags(hosts_in_rule_scope, tag_conditions)
            if matched_by_tags is not None:
                return matched_by_tags

        only_specific_hosts = (
            host_conditions is not None
            and not isinstance(host_conditions, dict)
            and all(not isinstance(x, dict) for x in host_conditions)
        )

        if host_conditions == []:
            return set()  # Empty host list -> Nothing matches

        if not tag_conditions and not label_conditions and not host_conditions:
            # If no tags are specified and the hostlist only include @all (all hosts)
            return hosts_in_rule_scope

        if (
            not tag_conditions
            and not label_conditions
            and only_specific_hosts
            and host_conditions is not None
        ):
            # If no tags are specified and there are only specific hosts we already have the matches
            return hosts_in_rule_scope.intersection(host_conditions)

        # If the rule has only exact host restrictions, we can thin out the list of hosts to check
        if only_specific_hosts and host_conditions is not None:
            hosts_to_check = hosts_in_rule_scope.intersection(host_conditions)
        else:
            hosts_to_check = hosts_in_rule_scope

        matching: set[HostName] = set()
        for hostname in hosts_to_check:
            # When no tag matching is requested, do not filter by tags. Accept all hosts
            # and filter only by hostlist
            if tag_conditions and not matches_host_tags(
                self._host_tags[hostname],
                tag_conditions,
            ):
                continue

            if label_conditions:
                host_labels = labels_of_host(hostname)
                if not matches_labels(host_labels, label_conditions):
                    continue

            if not matches_host_name(host_conditions, hostname):
                continue

            matching.add(hostname)

        return matching

    @staticmethod
    def _condition_cache_id(
        hostlist: HostOrServiceConditions | None,
        tag_conditions: Mapping[TagGroupID, TagCondition],
        label_groups: LabelGroups,
        rule_path: str,
    ) -> _ConditionCacheID:
        host_parts: list[str] = []

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
                (taggroup_id, _tags_cache_id(tag_condition))
                for taggroup_id, tag_condition in tag_conditions.items()
            ),
            # cast lists in label groups to tuples
            tuple((operator, tuple(label_group)) for operator, label_group in label_groups),
            rule_path,
        )

    # TODO: Generalize this optimization: Build some kind of key out of the tag conditions
    # (positive, negative, ...). Make it work with the new tag group based "$or" handling.
    def _match_hosts_by_tags(
        self,
        valid_hosts: set[HostName],
        tag_conditions: Mapping[TagGroupID, TagCondition],
    ) -> set[HostName] | None:
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

            return matching

        # With shared folders
        checked_hosts: set[str] = set()
        for hostname in valid_hosts:
            if hostname in checked_hosts:
                continue

            hosts_with_same_tag = self._filter_hosts_with_same_tags_as_host(hostname, valid_hosts)
            checked_hosts.update(hosts_with_same_tag)

            if positive_match_tags <= self._host_tags[
                hostname
            ] and not negative_match_tags.intersection(self._host_tags[hostname]):
                matching.update(hosts_with_same_tag)

        return matching

    def _filter_hosts_with_same_tags_as_host(
        self,
        hostname: HostName,
        hosts: set[HostName],
    ) -> set[HostName]:
        return self._hosts_grouped_by_tags[self._host_grouped_ref[hostname]].intersection(hosts)

    def _get_hosts_within_folder(self, folder_path: str, with_foreign_hosts: bool) -> set[HostName]:
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

    def _initialize_host_lookup(self) -> None:
        for hostname in self._all_configured_hosts:
            group_ref = tuple(sorted(self._host_tags[hostname]))
            self._hosts_grouped_by_tags.setdefault(group_ref, set()).add(hostname)
            self._host_grouped_ref[hostname] = group_ref


def _tags_cache_id(tag_or_label_spec: object) -> object:
    if isinstance(tag_or_label_spec, dict):
        if "$ne" in tag_or_label_spec:
            return "!%s" % tag_or_label_spec["$ne"]

        if "$or" in tag_or_label_spec:
            return (
                "$or",
                tuple(
                    _tags_cache_id(sub_tag_or_label_spec)
                    for sub_tag_or_label_spec in tag_or_label_spec["$or"]
                ),
            )

        if "$nor" in tag_or_label_spec:
            return (
                "$nor",
                tuple(
                    _tags_cache_id(sub_tag_or_label_spec)
                    for sub_tag_or_label_spec in tag_or_label_spec["$nor"]
                ),
            )

        raise NotImplementedError("Invalid tag / label spec: %r" % tag_or_label_spec)

    return tag_or_label_spec


def parse_negated_condition_list(
    entries: HostOrServiceConditions,
) -> tuple[bool, HostOrServiceConditionsSimple]:
    if isinstance(entries, dict) and "$nor" in entries:
        return True, entries["$nor"]
    if isinstance(entries, list):
        return False, entries
    raise ValueError("unsupported conditions")


def matches_host_tags(
    hosttags: set[tuple[TagGroupID, TagID]],
    required_tags: Mapping[TagGroupID, TagCondition],
) -> bool:
    return all(
        matches_tag_condition(taggroup_id, tag_condition, hosttags)
        for taggroup_id, tag_condition in required_tags.items()
    )


def matches_host_name(host_entries: HostOrServiceConditions | None, hostname: HostName) -> bool:
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


def matches_labels(object_labels: Labels, required_label_groups: LabelGroups) -> bool:
    overall_match: bool = True

    for group_operator, label_group in required_label_groups:
        group_match: bool = True
        for label_operator, label in label_group:
            if not label:
                continue

            if not object_labels:
                # The first label operator in a group is always "and" or "not", it cannot be "or"
                # -> a label group matches a host without labels only if it has no "and" operators
                if label_operator == "and":
                    group_match = False
                    break
                continue

            try:
                key, value = label.split(":")
            except Exception:
                raise NotImplementedError(f"HALLO DORT: wird hier zu wenig entpackt?  --  {label}")
            label_match: bool = value == object_labels.get(key)
            group_match = _and_or_not_group_match(group_match, label_match, label_operator)

        overall_match = _and_or_not_group_match(overall_match, group_match, group_operator)

    return overall_match


def _and_or_not_group_match(
    given_group_match: bool, new_single_match: bool, operator: AndOrNotLiteral
) -> bool:
    match operator:
        case "and":
            return given_group_match and new_single_match
        case "or":
            return given_group_match or new_single_match
        case "not":
            return given_group_match and not new_single_match


def _matches_service_conditions(
    service_description_condition: tuple[bool, Pattern[str]],
    service_labels_condition: LabelGroups,
    match_text: ServiceName | Item,
    service_labels: Labels,
) -> bool:
    if not _matches_service_description_condition(service_description_condition, match_text):
        return False

    if service_labels_condition and not matches_labels(service_labels, service_labels_condition):
        return False

    return True


def _matches_service_description_condition(
    service_description_condition: tuple[bool, Pattern[str]],
    match_text: ServiceName | Item,
) -> bool:
    negate, pattern = service_description_condition

    if match_text is not None and pattern.match(match_text) is not None:
        return not negate
    return negate


def matches_tag_condition(
    taggroup_id: TagGroupID,
    tag_condition: TagCondition,
    hosttags: set[tuple[TagGroupID, TagID]],
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
                {(taggroup_id, opt_tag_id) for opt_tag_id in tag_condition["$nor"]}
            )

        raise NotImplementedError()

    return (
        taggroup_id,
        tag_condition,
    ) in hosttags
