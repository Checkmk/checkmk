#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

#########################################################################################
#                                                                                       #
#                                 !!   W A T C H   O U T   !!                           #
#                                                                                       #
#   The logwatch plug-in is notorious for being an exception to just about every rule   #
#   or best practice that applies to check plug-in development.                         #
#   It is highly discouraged to use this a an example!                                  #
#                                                                                       #
#########################################################################################

import re
from collections.abc import Callable, Container, Iterable, Mapping, MutableMapping, Sequence
from dataclasses import dataclass
from re import Pattern
from typing import Any, Literal, NamedTuple, Never, NotRequired, TypedDict

from cmk.ccc.hostaddress import HostName  # pylint: disable=cmk-module-layer-violation

from cmk.checkengine.plugins import CheckPluginName  # pylint: disable=cmk-module-layer-violation

# from cmk.base.config import logwatch_rule will NOT work!
import cmk.base.config  # pylint: disable=cmk-module-layer-violation

from cmk.agent_based.v2 import CheckPlugin, CheckResult, Result, State

# Watch out! Matching the 'logwatch_rules' ruleset against labels will not
# work as expected, if logfiles are grouped!
NEVER_DISCOVER_SERVICE_LABELS: Sequence[Never] = ()


class ItemData(TypedDict):
    attr: str
    lines: dict[str, list[str]]


class Section(NamedTuple):
    errors: Sequence[str]
    logfiles: Mapping[str, ItemData]


SyslogConfig = tuple[Literal["tcp"], dict] | tuple[Literal["udp"], dict]


class CommonLogwatchEc(TypedDict):
    activation: NotRequired[bool]
    method: NotRequired[Literal["", "spool:"] | str | SyslogConfig]
    facility: NotRequired[int]
    restrict_logfiles: NotRequired[list[str]]
    monitor_logfilelist: NotRequired[bool]
    expected_logfiles: NotRequired[list[str]]
    logwatch_reclassify: NotRequired[bool]
    monitor_logfile_access_state: NotRequired[Literal[0, 1, 2, 3]]
    separate_checks: NotRequired[bool]


class PreDictLogwatchEc(CommonLogwatchEc):
    service_level: tuple[Literal["cmk_postprocessed"], Literal["service_level"], None]
    host_name: tuple[Literal["cmk_postprocessed"], Literal["host_name"], None]


class ParameterLogwatchEc(CommonLogwatchEc):
    """Parameters as created by the 'logwatch_ec' ruleset"""

    service_level: int
    host_name: str


_StateMap = Mapping[Literal["c_to", "w_to", "o_to", "._to"], Literal["C", "W", "O", "I", "."]]


class ParameterLogwatchRules(TypedDict):
    reclassify_patterns: list[tuple[Literal["C", "W", "O", "I"], str, str]]
    reclassify_states: NotRequired[_StateMap]


class ParameterLogwatchGroups(TypedDict):
    grouping_patterns: list[tuple[str, tuple[str, str]]]
    host_name: str


ClusterSection = dict[str | None, Section]


class RulesetAccess:
    """Namespace to get an overview of logwatch rulesets / configuration

    Logwatch uses more configuration parameters that just its rulesets.
    It also uses the current host name, and the "effective service level".

    We consider 8 cases here: EC/¬EC, grouped/single, cluster/node.

    There are three logwatch rulesets:

    logwatch_rules:
        These contain the reclassification-patterns and -states.
        They are used:
            * In all 8 check functions
              ** match type "ALL"
              ** in logwatch_ec (gouped) they don't match on the item (the group),
                 but on the individual logfiles _in_ the group (bug or feature?).

    logwatch_ec:
        These contain forwarding parameters (which files + how) and a few flags.
        They are used:
            * As the 'official' check parameters in logwatch_ec (_not_ logwatch_ec_single)
              This implies match type "MERGED".
            * In all discovery functions, where in a "merged" style only the "restrict_logfiles"
              parameters is used to filter the logfiles (forwardig VS no forwarding).
            * In the EC case, they are "forwarded" to the check functions as discovered parameters.

    logwatch_groups:
        These contain grouping patterns for the ¬EC case.
        They are used:
            * As regular 'ALL' style discovery parameters for the ¬EC plugins.

    PROPOSAL:
    Way out: Change to one common discovery and two dedicated check paramater rulesets:

        Discovery ruleset (ONE for all plugins).
         * Match type: ALL.
         * Grouping patterns: List of tripples:
            ** <Group matches to one item 'group name'> | <matched logfiles are single items>
            ** <patterns (include/exclude?)>
            ** <forward these to EC or not>

        ¬EC check ruleset
         * Match type: MERGE
         * Reclassify-patterns and -states
         * matching regularly, i.e. on items or groups

        EC check ruleset
         * Match type: MERGE
         * Reclassify-patterns and -states
         * Forwarding parameters
         * matching regularly, i.e. on items or groups

    * Current configurations could be embedded in an update config step.
    * In the future, reclassification parameters would *always* be matched against the *item*.
    * Proposal: Grouping should work the same regardless of EC/¬EC
      (currently the options in EC are only 'group everything' or 'group nothing').
    """

    # This is only wishful typing -- but lets assume this is what we get.
    @staticmethod
    def logwatch_rules_all(
        *, host_name: str, plugin: CheckPlugin, logfile: str
    ) -> Sequence[ParameterLogwatchRules]:
        host_name = HostName(host_name)
        cc = cmk.base.config.access_globally_cached_config_cache()
        # We're using the logfile to match the ruleset, not necessarily the "item"
        # (which might be the group). However: the ruleset matcher expects this to be the item.
        # As a result, the following will all fail (hidden in `service_extra_conf`):
        #
        # Fail #1: Look up the discovered labels
        # Mitigate this by never discovering any labels.
        discovered_labels: Mapping[str, str] = dict(NEVER_DISCOVER_SERVICE_LABELS)

        # Fail #2: Compute the correct service description
        # This will be wrong if the logfile is grouped.
        service_description = cc.make_passive_service_name_config().make_name(
            cc.label_manager.labels_of_host,
            host_name,
            CheckPluginName(plugin.name),
            service_name_template=plugin.service_name,
            item=logfile,
        )

        # Fail #3: Retrieve the configured labels for this service.
        # This might be wrong as a result of #2.
        service_labels = cc.label_manager.labels_of_service(
            host_name, service_description, discovered_labels
        )
        # => Matching this rule agains service labels will most likely fail.
        return cc.ruleset_matcher.get_checkgroup_ruleset_values(
            host_name,
            logfile,
            service_labels,
            cmk.base.config.logwatch_rules,  # type: ignore[arg-type]
            cc.label_manager.labels_of_host,
        )

    # This is only wishful typing -- but lets assume this is what we get.
    @staticmethod
    def logwatch_ec_all(host_name: str) -> Sequence[ParameterLogwatchEc]:
        """Isolate the remaining API violation w.r.t. parameters"""
        cc = cmk.base.config.access_globally_cached_config_cache()
        return cc.ruleset_matcher.get_host_values(
            HostName(host_name),
            cmk.base.config.checkgroup_parameters.get("logwatch_ec", []),  # type: ignore[arg-type]
            cc.label_manager.labels_of_host,
        )


def update_seen_batches(
    value_store: MutableMapping[str, Any],
    cluster_section: ClusterSection,
    logfiles: Iterable[str],
) -> Container[str]:
    # Watch out: we cannot write an empty set to the value_store :-(
    seen_batches = value_store.get("seen_batches", ())
    value_store["seen_batches"] = tuple(
        batch_id
        for node_section in cluster_section.values()
        for logfile in logfiles
        if (logfile_data := node_section.logfiles.get(logfile)) is not None
        for batch_id in logfile_data["lines"]
    )
    return seen_batches


def extract_unseen_lines(
    batches_of_lines: Mapping[str, list[str]],
    seen_batches: Container[str],
) -> list[str]:
    return [
        line
        for batch, lines in sorted(batches_of_lines.items())
        if batch not in seen_batches
        for line in lines
    ]


def discoverable_items(*sections: Section) -> list[str]:
    """only consider files which are 'ok' on at least one node or 'cannotopen' to notify about
    unreadable files"""
    return sorted(
        {
            item
            for node_data in sections
            for item, item_data in node_data.logfiles.items()
            if item_data["attr"] == "ok" or item_data["attr"] == "cannotopen"
        }
    )


class LogFileFilter:
    @staticmethod
    def _match_all(_logfile: str) -> Literal[True]:
        return True

    @staticmethod
    def _match_nothing(_logfile: str) -> Literal[False]:
        return False

    def __init__(self, rules: Sequence[ParameterLogwatchEc]) -> None:
        self._expressions: tuple[Pattern[str], ...] = ()
        self.is_forwarded: Callable[[str], bool]
        if not rules:
            # forwarding disabled
            self.is_forwarded = self._match_nothing
            return

        if not next((p["activation"] for p in rules if "activation" in p), True):
            # forwarding disabled
            self.is_forwarded = self._match_nothing
            return

        params = rules[0]
        if "restrict_logfiles" not in params:
            # matches all logs on this host
            self.is_forwarded = self._match_all
            return

        self._expressions = tuple(re.compile(pattern) for pattern in params["restrict_logfiles"])
        self.is_forwarded = self._match_patterns

    def _match_patterns(self, logfile: str) -> bool:
        return any(rgx.match(logfile) for rgx in self._expressions)


@dataclass(frozen=True)
class ReclassifyParameters:
    patterns: Sequence[tuple[Literal["C", "W", "O", "I"], str, str]]
    states: _StateMap


def compile_reclassify_params(params: Sequence[ParameterLogwatchRules]) -> ReclassifyParameters:
    patterns: list[tuple[Literal["C", "W", "O", "I"], str, str]] = []
    states: _StateMap = {}

    for rule in params:
        if isinstance(rule, dict):
            patterns.extend(rule["reclassify_patterns"])
            if "reclassify_states" in rule:
                # (mo) wondering during migration: doesn't this mean the last one wins?
                states = rule["reclassify_states"]
        else:
            patterns.extend(rule)

    return ReclassifyParameters(patterns, states)


# the `str` is a hack to account for the poorly typed `old_level` below.
_STATE_CHANGE_MAP: Mapping[str, Literal["c_to", "w_to", "o_to", "._to"]] = {
    "C": "c_to",
    "W": "w_to",
    "O": "o_to",
    ".": "._to",
}


def reclassify(
    reclassify_parameters: ReclassifyParameters,
    text: str,
    old_level: str,
) -> str:
    # Reclassify state if a given regex pattern matches
    # A match overrules the previous state->state reclassification
    for level, pattern, _ in reclassify_parameters.patterns:
        # not necessary to validate regex: already done by GUI
        if re.search(pattern, text, flags=re.UNICODE):
            return level

    # Reclassify state to another state
    try:
        return reclassify_parameters.states[_STATE_CHANGE_MAP[old_level.upper()]]
    except KeyError:
        return old_level


def check_errors(cluster_section: Mapping[str | None, Section]) -> Iterable[Result]:
    """
    >>> cluster_section = {
    ...     None: Section(errors=["error w/o node info"], logfiles={}),
    ...     "node": Section(errors=["some error"], logfiles={}),
    ... }
    >>> for r in check_errors(cluster_section):
    ...     print((r.state, r.summary))
    (<State.UNKNOWN: 3>, 'error w/o node info')
    (<State.UNKNOWN: 3>, '[node] some error')
    """
    for node, node_data in cluster_section.items():
        for error_msg in node_data.errors:
            yield Result(
                state=State.UNKNOWN,
                summary=error_msg if node is None else f"[{node}] {error_msg}",
            )


def get_unreadable_logfiles(
    logfile: str, section: Mapping[str | None, Section]
) -> Sequence[tuple[str, str | None]]:
    """
    >>> section = Section(errors=[], logfiles={"log1": ItemData(attr="cannotopen", lines={})})
    >>> list(get_unreadable_logfiles("log1", {"node":section }))
    [('log1', 'node')]
    >>> section = Section(errors=[], logfiles={"log1": ItemData(attr="cannotopen", lines={})})
    >>> list(get_unreadable_logfiles("log1", {None:section }))
    [('log1', None)]
    >>> list(get_unreadable_logfiles("log1", {"node": Section(errors=[], logfiles={})}))
    []
    """
    unreadable_logfiles = [
        (logfile, node)
        for node, node_data in section.items()
        if (logfile_data := node_data.logfiles.get(logfile))
        and logfile_data["attr"] == "cannotopen"
    ]
    return unreadable_logfiles


def check_unreadable_files(
    unreadable_logfiles: Sequence[tuple[str, str | None]], monitoring_state: State
) -> CheckResult:
    """
    >>> list(check_unreadable_files([("log1", "node")], State.WARN))
    [Result(state=<State.WARN: 1>, summary="[node] Could not read log file 'log1'")]
    >>> list(check_unreadable_files([("log1", "node")], State.CRIT))
    [Result(state=<State.CRIT: 2>, summary="[node] Could not read log file 'log1'")]
    >>> list(check_unreadable_files([("log1", None)], State.CRIT))
    [Result(state=<State.CRIT: 2>, summary="Could not read log file 'log1'")]
    >>> list(check_unreadable_files([], State.CRIT))
    []
    """
    for logfile, node in unreadable_logfiles:
        error_msg = f"Could not read log file '{logfile}'"
        yield Result(
            state=monitoring_state,
            summary=error_msg if node is None else f"[{node}] {error_msg}",
        )
