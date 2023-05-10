#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""This module provides generic Check_MK ruleset processing functionality"""

from collections.abc import Callable, Iterable, Iterator, Mapping, Sequence
from re import Pattern
from typing import cast, Generic, Literal, NamedTuple, Required, TypeAlias, TypedDict, TypeVar

from cmk.utils.caching import instance_method_lru_cache
from cmk.utils.exceptions import MKGeneralException
from cmk.utils.labels import BuiltinHostLabelsStore, DiscoveredHostLabelsStore, HostLabel, Labels
from cmk.utils.parameters import boil_down_parameters
from cmk.utils.regex import regex
from cmk.utils.rulesets.tuple_rulesets import (
    ALL_HOSTS,
    ALL_SERVICES,
    CLUSTER_HOSTS,
    NEGATE,
    PHYSICAL_HOSTS,
)
from cmk.utils.tags import TagConfig, TagGroupID, TagID
from cmk.utils.type_defs import (
    HostAddress,
    HostName,
    HostOrServiceConditions,
    HostOrServiceConditionsSimple,
    ServiceName,
)

RulesetName = str  # Could move to a less cluttered module as it is often used on its own.
TRuleValue = TypeVar("TRuleValue")

# The value of `LabelConditions` may actually be something like TagCondition.
LabelConditions = Mapping[str, str | Mapping[Literal["$ne"], str]]
LabelSources = dict[str, str]

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
# Here, we have data structures such as
# {'ip-v4': {'$ne': 'ip-v4'}, 'snmp_ds': {'$nor': ['no-snmp', 'snmp-v1']}, 'taggroup_02': None, 'aux_tag_01': 'aux_tag_01', 'address_family': 'ip-v4-only'}
TagsOfHosts: TypeAlias = dict[HostName | HostAddress, Mapping[TagGroupID, TagID]]


PreprocessedHostRuleset: TypeAlias = dict[HostName | HostAddress, list[TRuleValue]]
PreprocessedPattern: TypeAlias = tuple[bool, Pattern[str]]
PreprocessedServiceRuleset: TypeAlias = list[
    tuple[
        object, set[HostName], LabelConditions, tuple[tuple[str, object], ...], PreprocessedPattern
    ]
]

# FIXME: A lot of signatures regarding rules and rule sets are simply lying:
# They claim to expect a RuleConditionsSpec or Ruleset, but
# they are silently handling a very chaotic tuple-based structure, too. We
# really, really need to fix all those signatures! Some test cases for tuples are in
# test_tuple_rulesets.py. They contain horrible hand-made types...


class RuleOptionsSpec(TypedDict, total=False):
    disabled: bool
    description: str
    comment: str
    docu_url: str
    predefined_condition_id: str


# TODO: Improve this type
class RuleConditionsSpec(TypedDict, total=False):
    host_tags: Mapping[TagGroupID, TagCondition]
    host_labels: Mapping[str, str | Mapping[Literal["$ne"], str]]
    host_name: HostOrServiceConditions | None
    service_description: HostOrServiceConditions | None
    service_labels: Mapping[str, str | Mapping[Literal["$ne"], str]]
    host_folder: str


class RuleSpec(Generic[TRuleValue], TypedDict, total=False):
    value: Required[TRuleValue]
    condition: Required[RuleConditionsSpec]
    id: str  # Should not be optional but nearly not test has that attribute set!
    options: RuleOptionsSpec


class LabelManager(NamedTuple):
    """Helper class to manage access to the host and service labels"""

    explicit_host_labels: dict[HostName, Labels]
    host_label_rules: Sequence[RuleSpec[dict[str, str]]]
    service_label_rules: Sequence[RuleSpec[dict[str, str]]]
    discovered_labels_of_service: Callable[[HostName, ServiceName], Labels]


class RulesetMatchObject:
    """Wrapper around dict to ensure the ruleset match objects are correctly created"""

    __slots__ = ["host_name", "service_description", "service_labels", "service_cache_id"]

    def __init__(
        self,
        host_name: HostName | HostAddress | None = None,
        service_description: ServiceName | None = None,
        service_labels: Labels | None = None,
    ) -> None:
        super().__init__()
        self.host_name = host_name
        self.service_description = service_description
        self.service_labels = service_labels
        self.service_cache_id = (
            self.service_description,
            hash(None if service_labels is None else frozenset(service_labels.items())),
        )

    def copy(self) -> "RulesetMatchObject":
        return RulesetMatchObject(
            host_name=self.host_name,
            service_description=self.service_description,
            service_labels=self.service_labels,
        )

    def __repr__(self) -> str:
        return (
            "RulesetMatchObject("
            f"host_name={self.host_name!r}, "
            f"service_description={self.service_description!r}, "
            f"service_labels={self.service_labels!r})"
        )

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, RulesetMatchObject):
            return False
        return (
            self.host_name == other.host_name
            and self.service_description == other.service_description
            and self.service_labels == other.service_labels
        )


def merge_cluster_labels(all_node_labels: Iterable[Iterable[HostLabel]]) -> Sequence[HostLabel]:
    """A cluster has all its nodes labels. Last node wins."""
    return list({l.name: l for node_labels in all_node_labels for l in node_labels}.values())


class RulesetMatcher:
    """Performing matching on host / service rulesets

    There is some duplicate logic for host / service rulesets. This has been
    kept for performance reasons. Especially the service rulset matching is
    done very often in large setups. Be careful when working here.
    """

    def __init__(
        self,
        tag_to_group_map: Mapping[TagID, TagGroupID],
        host_tags: TagsOfHosts,
        host_paths: dict[HostName, str],
        labels: LabelManager,
        all_configured_hosts: set[HostName],
        clusters_of: dict[HostName, list[HostName]],
        nodes_of: dict[HostName, list[HostName]],
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
        self.labels_of_host = self.ruleset_optimizer.labels_of_host
        self.labels_of_service = self.ruleset_optimizer.labels_of_service
        self.label_sources_of_host = self.ruleset_optimizer.label_sources_of_host
        self.label_sources_of_service = self.ruleset_optimizer.label_sources_of_service
        self.clear_caches = self.ruleset_optimizer.clear_caches

        self._service_match_cache: dict[
            tuple[
                tuple[ServiceName | None, int], PreprocessedPattern, tuple[tuple[str, object], ...]
            ],
            object,
        ] = {}

    def is_matching_host_ruleset(
        self, match_object: RulesetMatchObject, ruleset: Iterable[RuleSpec[bool]]
    ) -> bool:
        """Compute outcome of a ruleset set that just says yes/no

        The binary match only cares about the first matching rule of an object.
        Depending on the value the outcome is negated or not.

        Replaces in_binary_hostlist / in_boolean_serviceconf_list"""
        for value in self.get_host_ruleset_values(match_object, ruleset, is_binary=True):
            # Next line may be controlled by `is_binary` in which case we
            # should overload the function instead of asserting to check
            # during typing instead of runtime.
            assert isinstance(value, bool)
            return value
        return False  # no match. Do not ignore

    def get_host_ruleset_merged_dict(
        self, match_object: RulesetMatchObject, ruleset: Iterable[RuleSpec[dict[str, TRuleValue]]]
    ) -> Mapping[str, TRuleValue]:
        """Returns a dictionary of the merged dict values of the matched rules
        The first dict setting a key defines the final value.

        Replaces host_extra_conf_merged / service_extra_conf_merged"""
        default: dict[str, dict[str, TRuleValue]] = {}
        merged = boil_down_parameters(
            self.get_host_ruleset_values(match_object, ruleset, is_binary=False), default
        )
        assert isinstance(merged, dict)  # remove along with LegacyCheckParameters
        return merged

    def get_host_ruleset_values(
        self,
        match_object: RulesetMatchObject,
        ruleset: Iterable[RuleSpec[TRuleValue]],
        is_binary: bool,
    ) -> Iterator[TRuleValue]:
        """Returns a generator of the values of the matched rules
        Replaces host_extra_conf"""
        self.tuple_transformer.transform_in_place(ruleset, is_service=False, is_binary=is_binary)

        # When the requested host is part of the local sites configuration,
        # then use only the sites hosts for processing the rules
        with_foreign_hosts = (
            match_object.host_name not in self.ruleset_optimizer.all_processed_hosts()
        )

        optimized_ruleset: PreprocessedHostRuleset[
            TRuleValue
        ] = self.ruleset_optimizer.get_host_ruleset(
            ruleset, with_foreign_hosts, is_binary=is_binary
        )

        assert match_object.host_name is not None
        yield from optimized_ruleset.get(match_object.host_name, ())

    def is_matching_service_ruleset(
        self, match_object: RulesetMatchObject, ruleset: Iterable[RuleSpec[TRuleValue]]
    ) -> bool:
        """Compute outcome of a ruleset set that just says yes/no

        The binary match only cares about the first matching rule of an object.
        Depending on the value the outcome is negated or not.

        Replaces in_binary_hostlist / in_boolean_serviceconf_list"""
        for value in self.get_service_ruleset_values(match_object, ruleset, is_binary=True):
            # See `is_matching_host_ruleset()`.
            assert isinstance(value, bool)
            return value
        return False  # no match. Do not ignore

    def get_service_ruleset_merged_dict(
        self, match_object: RulesetMatchObject, ruleset: Iterable[RuleSpec[dict[str, TRuleValue]]]
    ) -> Mapping[str, TRuleValue]:
        """Returns a dictionary of the merged dict values of the matched rules
        The first dict setting a key defines the final value.

        Replaces host_extra_conf_merged / service_extra_conf_merged"""
        merged = boil_down_parameters(
            self.get_service_ruleset_values(match_object, ruleset, is_binary=False), {}
        )
        assert isinstance(merged, dict)  # remove along with LegacyCheckParameters
        return merged

    def get_service_ruleset_values(
        self,
        match_object: RulesetMatchObject,
        ruleset: Iterable[RuleSpec[TRuleValue]],
        is_binary: bool,
    ) -> Iterator[object]:
        """Returns a generator of the values of the matched rules
        Replaces service_extra_conf"""
        self.tuple_transformer.transform_in_place(ruleset, is_service=True, is_binary=is_binary)

        with_foreign_hosts = (
            match_object.host_name not in self.ruleset_optimizer.all_processed_hosts()
        )
        optimized_ruleset = self.ruleset_optimizer.get_service_ruleset(ruleset, with_foreign_hosts)

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
        service_description_condition: tuple[bool, Pattern[str]],
        service_labels_condition: Mapping[str, object],
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
        service_description_condition: tuple[bool, Pattern[str]],
        match_object: RulesetMatchObject,
    ) -> bool:
        negate, pattern = service_description_condition

        if (
            match_object.service_description is not None
            and pattern.match(match_object.service_description) is not None
        ):
            return not negate
        return negate

    def get_values_for_generic_agent(
        self, ruleset: Iterable[RuleSpec[object]], path_for_rule_matching: str
    ) -> list[object]:
        """Compute rulesets for "generic" hosts

        This fictious host has no name and no tags.
        It matches all rules that do not require specific hosts or tags.
        It matches rules that e.g. except specific hosts or tags (is not, has not set).
        """
        self.tuple_transformer.transform_in_place(ruleset, is_service=False, is_binary=False)

        entries: list[object] = []
        for rule in ruleset:
            if _is_disabled(rule):
                continue

            rule_path = (cond := rule["condition"]).get("host_folder")
            if rule_path is not None and not path_for_rule_matching.startswith(rule_path):
                continue

            if (tags := cond.get("host_tags", {})) and not self.ruleset_optimizer.matches_host_tags(
                set(), tags
            ):
                continue

            if (labels := cond.get("host_labels", {})) and not matches_labels({}, labels):
                continue

            if not self.ruleset_optimizer.matches_host_name(cond.get("host_name"), HostName("")):
                continue

            entries.append(rule["value"])

        return entries


# TODO: improve and cleanup types
_ConditionCacheID: TypeAlias = tuple[
    tuple[str, ...], tuple[tuple[TagGroupID, object], ...], tuple[tuple[str, object], ...], str
]


class RulesetOptimizer:
    """Performs some precalculations on the configured rulesets to improve the
    processing performance"""

    def __init__(
        self,
        ruleset_matcher: RulesetMatcher,
        host_tags: TagsOfHosts,
        host_paths: dict[HostName, str],
        labels: LabelManager,
        all_configured_hosts: set[HostName],
        clusters_of: dict[HostName, list[HostName]],
        nodes_of: dict[HostName, list[HostName]],
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

        self._service_ruleset_cache: dict[tuple[int, bool], PreprocessedServiceRuleset] = {}
        self._host_ruleset_cache: dict[tuple[int, bool], PreprocessedHostRuleset[object]] = {}
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
        self._host_ruleset_cache.clear()
        self._service_ruleset_cache.clear()

    def clear_caches(self) -> None:
        self._host_ruleset_cache.clear()
        self._all_matching_hosts_match_cache.clear()

    def all_processed_hosts(self) -> set[HostName]:
        """Returns a set of all processed hosts"""
        return self._all_processed_hosts

    def set_all_processed_hosts(self, all_processed_hosts: Iterable[HostName]) -> None:
        self._all_processed_hosts = set(all_processed_hosts)

        involved_clusters: set[HostName] = set()
        involved_nodes: set[HostName] = set()
        for hostname in self._all_processed_hosts:
            involved_nodes.update(self._nodes_of.get(hostname, []))
            involved_clusters.update(self._clusters_of.get(hostname, []))

        # Also add all nodes of used clusters
        for hostname in involved_clusters:
            involved_nodes.update(self._nodes_of.get(hostname, []))

        nodes_and_clusters = involved_clusters | involved_nodes

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
        self, ruleset: Iterable[RuleSpec[TRuleValue]], with_foreign_hosts: bool, is_binary: bool
    ) -> PreprocessedHostRuleset[TRuleValue]:
        # Note on the `type: ignore` in this function.  The cache may store
        # any `RuleSpec[TRuleValue]`.  The consequence is that the actual
        # type for `TRuleValue` isn't conserved.
        cache_id = id(ruleset), with_foreign_hosts

        if cache_id in self._host_ruleset_cache:
            return self._host_ruleset_cache[cache_id]  # type: ignore[return-value]

        host_ruleset: PreprocessedHostRuleset[TRuleValue] = self._convert_host_ruleset(
            ruleset, with_foreign_hosts, is_binary
        )
        self._host_ruleset_cache[cache_id] = host_ruleset  # type: ignore[assignment]
        return host_ruleset

    def _convert_host_ruleset(
        self, ruleset: Iterable[RuleSpec[TRuleValue]], with_foreign_hosts: bool, is_binary: bool
    ) -> PreprocessedHostRuleset[TRuleValue]:
        """Precompute host lookup map

        Instead of a ruleset like list structure with precomputed host lists we compute a
        direct map for hostname based lookups for the matching rule values
        """
        host_values: PreprocessedHostRuleset[TRuleValue] = {}
        for rule in ruleset:
            if _is_disabled(rule):
                continue

            for hostname in self._all_matching_hosts(rule["condition"], with_foreign_hosts):
                host_values.setdefault(hostname, []).append(rule["value"])

        return host_values

    def get_service_ruleset(
        self, ruleset: Iterable[RuleSpec[TRuleValue]], with_foreign_hosts: bool
    ) -> PreprocessedServiceRuleset:
        cache_id = id(ruleset), with_foreign_hosts

        if cache_id in self._service_ruleset_cache:
            return self._service_ruleset_cache[cache_id]

        cached_ruleset = self._convert_service_ruleset(
            ruleset, with_foreign_hosts=with_foreign_hosts
        )
        self._service_ruleset_cache[cache_id] = cached_ruleset
        return cached_ruleset

    def _convert_service_ruleset(
        self, ruleset: Iterable[RuleSpec[TRuleValue]], with_foreign_hosts: bool
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
        self, patterns: HostOrServiceConditions | None
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

    def _all_matching_hosts(  # pylint: disable=too-many-branches
        self, condition: RuleConditionsSpec, with_foreign_hosts: bool
    ) -> set[HostName]:
        """Returns a set containing the names of hosts that match the given
        tags and hostlist conditions."""
        hostlist = condition.get("host_name")
        tag_conditions: Mapping[TagGroupID, TagCondition] = condition.get("host_tags", {})
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

        matching: set[HostName] = set()
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
                    host_labels = self.labels_of_host(hostname)
                    if not matches_labels(host_labels, labels):
                        continue

                if not self.matches_host_name(hostlist, hostname):
                    continue

                matching.add(hostname)

        self._all_matching_hosts_match_cache[cache_id] = matching
        return matching

    def matches_host_name(
        self, host_entries: HostOrServiceConditions | None, hostname: HostName
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
        hosttags: set[tuple[TagGroupID, TagID]],
        required_tags: Mapping[TagGroupID, TagCondition],
    ) -> bool:
        return all(
            matches_tag_condition(taggroup_id, tag_condition, hosttags)
            for taggroup_id, tag_condition in required_tags.items()
        )

    def _condition_cache_id(
        self,
        hostlist: HostOrServiceConditions | None,
        tag_conditions: Mapping[TagGroupID, TagCondition],
        labels: Mapping[str, str | Mapping[Literal["$ne"], str]],
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
        cache_id: tuple[_ConditionCacheID, bool],
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

            self._all_matching_hosts_match_cache[cache_id] = matching
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

        self._all_matching_hosts_match_cache[cache_id] = matching
        return matching

    def _filter_hosts_with_same_tags_as_host(
        self,
        hostname: HostName,
        hosts: set[HostName],
    ) -> set[HostName]:
        return self._hosts_grouped_by_tags[self._host_grouped_ref[hostname]].intersection(hosts)

    def get_hosts_within_folder(self, folder_path: str, with_foreign_hosts: bool) -> set[HostName]:
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

    @instance_method_lru_cache(maxsize=None)
    def labels_of_host(self, hostname: HostName) -> Labels:
        """Returns the effective set of host labels from all available sources

        1. Discovered labels
        2. Ruleset "Host labels"
        3. Explicit labels (via host/folder config)
        4. Builtin labels

        Last one wins.
        """
        labels: dict[str, str] = {}
        labels.update(self._discovered_labels_of_host(hostname))
        labels.update(self._ruleset_labels_of_host(hostname))
        labels.update(self._labels.explicit_host_labels.get(hostname, {}))
        labels.update(self._builtin_labels_of_host(hostname))
        return labels

    @instance_method_lru_cache(maxsize=None)
    def label_sources_of_host(self, hostname: HostName) -> LabelSources:
        """Returns the effective set of host label keys with their source
        identifier instead of the value Order and merging logic is equal to
        _get_host_labels()"""
        labels: LabelSources = {}
        labels.update({k: "discovered" for k in self._discovered_labels_of_host(hostname).keys()})
        labels.update({k: "discovered" for k in self._builtin_labels_of_host(hostname)})
        labels.update({k: "ruleset" for k in self._ruleset_labels_of_host(hostname)})
        labels.update(
            {k: "explicit" for k in self._labels.explicit_host_labels.get(hostname, {}).keys()}
        )
        return labels

    def _ruleset_labels_of_host(self, hostname: HostName) -> Labels:
        match_object = RulesetMatchObject(hostname, service_description=None)
        return self._ruleset_matcher.get_host_ruleset_merged_dict(
            match_object, self._labels.host_label_rules
        )

    def _discovered_labels_of_host(self, hostname: HostName) -> Labels:
        host_labels = (
            DiscoveredHostLabelsStore(hostname).load()
            if (nodes := self._nodes_of.get(hostname)) is None
            else merge_cluster_labels([DiscoveredHostLabelsStore(node).load() for node in nodes])
        )
        return {l.name: l.value for l in host_labels}

    @staticmethod
    def _builtin_labels_of_host(hostname: HostName) -> Labels:
        return {
            label_id: label["value"] for label_id, label in BuiltinHostLabelsStore().load().items()
        }

    def labels_of_service(self, hostname: HostName, service_desc: ServiceName) -> Labels:
        """Returns the effective set of service labels from all available sources

        1. Discovered labels
        2. Ruleset "Host labels"

        Last one wins.
        """
        labels: dict[str, str] = {}
        labels.update(self._labels.discovered_labels_of_service(hostname, service_desc))
        labels.update(self._ruleset_labels_of_service(hostname, service_desc))

        return labels

    def label_sources_of_service(
        self, hostname: HostName, service_desc: ServiceName
    ) -> LabelSources:
        """Returns the effective set of host label keys with their source
        identifier instead of the value Order and merging logic is equal to
        _get_host_labels()"""
        labels: LabelSources = {}
        labels.update(
            {
                k: "discovered"
                for k in self._labels.discovered_labels_of_service(hostname, service_desc)
            }
        )
        labels.update(
            {k: "ruleset" for k in self._ruleset_labels_of_service(hostname, service_desc)}
        )

        return labels

    def _ruleset_labels_of_service(self, hostname: HostName, service_desc: ServiceName) -> Labels:
        match_object = RulesetMatchObject(hostname, service_description=service_desc)
        return self._ruleset_matcher.get_service_ruleset_merged_dict(
            match_object, self._labels.service_label_rules
        )


def _tags_or_labels_cache_id(tag_or_label_spec: object) -> object:
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


def matches_labels(
    object_labels: Mapping[str, object] | None, required_labels: Mapping[str, object]
) -> bool:
    for label_group_id, label_spec in required_labels.items():
        is_not = isinstance(label_spec, dict)
        if isinstance(label_spec, dict):
            label_spec = label_spec["$ne"]

        if object_labels is None:
            return False

        if (object_labels.get(label_group_id) == label_spec) is is_not:
            return False

    return True


def parse_negated_condition_list(
    entries: HostOrServiceConditions,
) -> tuple[bool, HostOrServiceConditionsSimple]:
    if isinstance(entries, dict) and "$nor" in entries:
        return True, entries["$nor"]
    if isinstance(entries, list):
        return False, entries
    raise ValueError("unsupported conditions")


# Class to help transition to new dict ruleset format. Can be deleted in 2.3
class RulesetToDictTransformer:
    """Transforms all rules in the given ruleset from the pre 1.6 tuple format to the dict format
    This is done in place to keep the references to the ruleset working.
    """

    def __init__(self, tag_to_group_map: Mapping[TagID, TagGroupID]) -> None:
        super().__init__()
        self._tag_groups = tag_to_group_map
        self._transformed_ids: set[int] = set()

    def transform_in_place(
        self, ruleset: Iterable[RuleSpec[TRuleValue]], is_service: bool, is_binary: bool
    ) -> None:
        for rule in ruleset:
            if not isinstance(rule, dict):
                new_value = self._transform_rule(rule, is_service, is_binary)
                raise MKGeneralException(
                    "rule",
                    (
                        f"Found old style tuple ruleset ({rule}). "
                        "Checkmk now expects dict rules. "
                        "Please convert to new format, see werk 7352.\n "
                        "The new ruleset format is \n"
                        f"{new_value}"
                    ),
                )

    def _transform_rule(
        self,
        rule_spec: RuleSpec[object],
        is_service: bool,
        is_binary: bool,
    ) -> Mapping[str, object]:
        rule: dict[str, object] = {}
        tuple_rule = list(rule_spec)

        # Extract optional rule_options from the end of the tuple
        if isinstance(tuple_rule[-1], dict):
            rule["options"] = tuple_rule.pop()

        # Extract value from front, if rule has a value
        if not is_binary:
            rule["value"] = tuple_rule.pop(0)
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

        condition = {}
        condition.update(service_condition)
        condition.update(host_condition)
        rule["condition"] = condition

        return rule

    def _transform_item_list(self, item_list: Sequence[str]):  # type: ignore[no-untyped-def]
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

    def _transform_host_conditions(self, tuple_rule: Sequence[str]) -> Mapping[str, object]:
        host_tags: Sequence[str]
        host_list: Sequence[str]
        if len(tuple_rule) == 1:
            host_tags = []
            host_list = tuple_rule[0]
        else:
            host_tags = tuple_rule[0]
            host_list = tuple_rule[1]

        condition: dict[str, object] = {}
        condition.update(self.transform_host_tags(host_tags))
        condition.update(self._transform_host_list(host_list))
        return condition

    def _transform_host_list(self, host_list: Sequence[str]) -> Mapping[str, object]:
        if host_list == ALL_HOSTS:
            return {}

        if not host_list:
            return {"host_name": []}

        sub_conditions: list[object] = []

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

    def transform_host_tags(self, host_tags: Sequence[str]) -> Mapping[str, object]:
        if not host_tags:
            return {}

        conditions: dict[str, object] = {}
        tag_conditions: dict[TagGroupID, TagCondition] = {}
        for tag_id in host_tags:
            # Folder is either not present (main folder) or in this format
            # "/abc/+" which matches on folder "abc" and all subfolders.
            if tag_id.startswith("/"):
                conditions["host_folder"] = tag_id.rstrip("+")
                continue

            negate = False
            if tag_id[0] == "!":
                negate, tag_id = True, TagID(tag_id[1:])

            # Assume it's an aux tag in case there is a tag configured without known group
            tag_id = TagID(tag_id)
            tag_group_id = self._tag_groups.get(tag_id, TagGroupID(tag_id))

            tag_conditions[tag_group_id] = {"$ne": tag_id} if negate else tag_id

        if tag_conditions:
            conditions["host_tags"] = tag_conditions

        return conditions


def get_tag_to_group_map(tag_config: TagConfig) -> Mapping[TagID, TagGroupID]:
    """The old rules only have a list of tags and don't know anything about the
    tag groups they are coming from. Create a map based on the current tag config
    """
    tag_id_to_tag_group_id_map: dict[TagID, TagGroupID] = {}

    for aux_tag in tag_config.aux_tag_list.get_tags():
        tag_id_to_tag_group_id_map[aux_tag.id] = TagGroupID(aux_tag.id)

    for tag_group in tag_config.tag_groups:
        for grouped_tag in tag_group.tags:
            # Do not care for the choices with a None value here. They are not relevant for this map
            if grouped_tag.id is not None:
                tag_id_to_tag_group_id_map[grouped_tag.id] = tag_group.id
    return tag_id_to_tag_group_id_map


def _is_disabled(rule: RuleSpec[TRuleValue]) -> bool:
    # TODO consolidate with cmk.gui.watolib.rulesets.py::Rule::is_disabled
    return "options" in rule and bool(rule["options"].get("disabled", False))
