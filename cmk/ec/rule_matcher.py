#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

import ipaddress
import re
from collections.abc import Callable
from dataclasses import dataclass
from logging import Logger
from typing import Literal, NamedTuple

import cmk.utils.regex
from cmk.ccc.site import SiteId
from cmk.utils.timeperiod import TimeperiodName

from .config import MatchGroups, Rule, StatePatterns, TextMatchResult, TextPattern
from .event import Event


class MatchPriority(NamedTuple):
    has_match: bool
    has_canceling_match: bool


@dataclass(frozen=True)
class MatchFailure:
    reason: str


@dataclass(frozen=True)
class MatchSuccess:
    cancelling: bool
    match_groups: MatchGroups


MatchResult = MatchFailure | MatchSuccess


def compile_matching_value(key: str, original_value: str) -> TextPattern | None:
    """Tries to convert a string to a compiled regex pattern.

    If the value is empty, it returns None.
    Or returns the value.lower() if it is not a regex.

    The leading '.*' is removed from the regex since it has a performance impact.
    See the benchmarks last 4 lines on a longer string here:

    Testing pattern         'ODBC' on test_string:  0.00043 seconds
    Testing pattern         '.*ODBC' on test_string:        0.00049 seconds
    Testing pattern         '.*ODBC.*' on test_string:      0.00049 seconds
    Testing pattern         'ODBC.*' on test_string:        0.00050 seconds
    Testing pattern         'ODBC' on test_string:  0.00076 seconds
    Testing pattern         '.*ODBC' on test_string:        0.09972 seconds
    Testing pattern         '.*ODBC.*' on test_string:      0.10019 seconds
    Testing pattern         'ODBC.*' on test_string:        0.00056 seconds

    Especially the search is dramatically slower on a NON-MATCHING long(100 characters) string.

    """

    value = original_value.strip()
    # Remove leading .* from regex. This is redundant and
    # dramatically destroys performance when doing an infix search.
    if key in {"match", "match_ok"}:
        while value.startswith(".*") and not value.startswith(".*?"):
            value = value[2:]
    if not value:
        return None
    if cmk.utils.regex.is_regex(value):
        return re.compile(value, re.IGNORECASE)
    return value.lower()


def compile_rule_attribute(
    rule: Rule,
    key: Literal["match", "match_ok", "match_host", "match_application", "cancel_application"],
) -> None:
    if key not in rule:
        return
    value = rule[key]
    if not isinstance(value, str):  # TODO: Remove when we have CompiledRule
        raise ValueError(f"attribute {key} of rule {rule['id']} already compiled")
    compiled_value = compile_matching_value(key, value)
    if compiled_value is None:
        del rule[key]
    else:
        rule[key] = compiled_value


def compile_state_pattern(state_patterns: StatePatterns, key: Literal["0", "1", "2"]) -> None:
    if key not in state_patterns:
        return
    value = state_patterns[key]
    if not isinstance(value, str):  # TODO: Remove when we have CompiledRule
        raise ValueError(f"state pattern {key} already compiled")
    compiled_value = compile_matching_value("state", value)
    if compiled_value is None:
        del state_patterns[key]
    else:
        state_patterns[key] = compiled_value


def compile_rule(rule: Rule) -> None:
    """Tries to convert strings to compiled regex patterns."""
    compile_rule_attribute(rule, "match")
    compile_rule_attribute(rule, "match_ok")
    compile_rule_attribute(rule, "match_host")
    compile_rule_attribute(rule, "match_application")
    compile_rule_attribute(rule, "cancel_application")
    if "state" in rule and isinstance(rule["state"], tuple) and rule["state"][0] == "text_pattern":
        state_patterns: StatePatterns = rule["state"][1]
        compile_state_pattern(state_patterns, "2")
        compile_state_pattern(state_patterns, "1")
        compile_state_pattern(state_patterns, "0")


def match(pattern: TextPattern | None, text: str, complete: bool) -> TextMatchResult:
    """Performs an EC style matching test of pattern on text.

    Returns False in case of no match or a tuple with the match groups.
    In case no match group is produced, it returns an empty tuple.
    """
    if pattern is None:
        return ()
    if isinstance(pattern, str):
        found = pattern == text.lower() if complete else pattern in text.lower()
        return () if found else False
    m = pattern.search(text)
    return m.groups("") if m else False


def format_pattern(pattern: TextPattern | None) -> str:
    if pattern is None:
        return str(pattern)
    if isinstance(pattern, str):
        return pattern
    return pattern.pattern


def match_ip_network(pattern: str, ipaddress_text: str) -> bool:
    """
    Return True if ipaddress belongs to the network.
    Works for both ipv6 and ipv4 addresses.
    """
    try:
        # strict=False is for 0.0.0.0/0 to be evaluated
        network = ipaddress.ip_network(pattern, strict=False)
    except ValueError:
        return False

    if int(network.netmask) == 0:
        return True  # event if ipaddress is empty

    try:
        ipaddress_ = ipaddress.ip_address(ipaddress_text)
    except ValueError:
        return False  # invalid address never matches

    return ipaddress_ in network


class RuleMatcher:
    def __init__(
        self,
        logger: Logger | None,
        omd_site_id: SiteId,
        is_active_time_period: Callable[[TimeperiodName], bool],
    ) -> None:
        self._logger = logger
        self._omd_site = omd_site_id
        self._is_active_time_period = is_active_time_period

    def _log_rule_matching(self, message: str, *args: object, indent: bool = True) -> None:
        """Check if logger is present and log the message as info level."""
        if self._logger:
            self._logger.info(f"  {message}" if indent else message, *args)

    def event_rule_matches_non_inverted(self, rule: Rule, event: Event) -> MatchResult:
        self._log_rule_matching("Trying rule %s/%s...", rule["pack"], rule["id"], indent=False)
        self._log_rule_matching("  Text:   %s", event["text"])
        self._log_rule_matching("  Syslog: %d.%d", event["facility"], event["priority"])
        self._log_rule_matching("  Host:   %s", event["host"])

        # Generic conditions without positive/canceling matches
        generic_match_result = self.event_rule_matches_generic(rule, event)
        if isinstance(generic_match_result, MatchFailure):
            self._log_rule_matching(generic_match_result.reason)
            return generic_match_result

        # Determine syslog priority
        match_priority = self.event_rule_determine_match_priority(rule, event)
        if match_priority is None:
            # Abort on negative outcome, neither positive nor negative
            result = MatchFailure(reason="The syslog priority does not match")
            self._log_rule_matching(result.reason)
            return result

        # Determine and cleanup match_groups
        match_groups = MatchGroups()
        match_groups_result = self.event_rule_determine_match_groups(rule, event, match_groups)
        if isinstance(match_groups_result, MatchFailure):
            self._log_rule_matching(match_groups_result.reason)
            # Abort on negative outcome, neither positive nor negative
            return match_groups_result

        return self._check_match_outcome(rule, match_groups, match_priority)

    def event_rule_matches(self, rule: Rule, event: Event) -> MatchResult:
        """Matches the rule and inverts the match if invert_matching is true."""
        result = self.event_rule_matches_non_inverted(rule, event)
        if rule.get("invert_matching"):
            if isinstance(result, MatchFailure):
                result = MatchSuccess(cancelling=False, match_groups=MatchGroups())
                self._log_rule_matching("Rule would not match, but due to inverted matching does.")
            else:
                result = MatchFailure(
                    reason="Rule would match, but due to inverted matching does not."
                )
                self._log_rule_matching(result.reason)
        return result

    def _check_match_outcome(
        self, rule: Rule, match_groups: MatchGroups, match_priority: MatchPriority
    ) -> MatchResult:
        """Decide or not a event is created, canceled or nothing is done."""
        # Check canceling-event
        has_canceling_condition = bool(
            [x for x in ["match_ok", "cancel_application", "cancel_priority"] if x in rule]
        )
        if has_canceling_condition and (
            (
                "match_ok" not in rule
                or match_groups.get("match_groups_message_ok", False) is not False
            )
            and (
                "cancel_application" not in rule
                or match_groups.get("match_groups_syslog_application_ok", False) is not False
            )
            and ("cancel_priority" not in rule or match_priority.has_canceling_match)
        ):
            self._log_rule_matching("  found canceling event")
            return MatchSuccess(cancelling=True, match_groups=match_groups)

        # Check create-event
        if (
            match_groups["match_groups_message"] is not False
            and match_groups.get("match_groups_syslog_application", ()) is not False
            and match_priority.has_match
        ):
            self._log_rule_matching("  found new event")
            return MatchSuccess(cancelling=False, match_groups=match_groups)

        # Looks like there was no match, output some additional info
        # Reasons preventing create-event
        if match_groups["match_groups_message"] is False:
            self._log_rule_matching("did not create event, because of wrong message")
        if "match_application" in rule and match_groups["match_groups_syslog_application"] is False:
            self._log_rule_matching("did not create event, because of wrong syslog application")
        if "match_priority" in rule and not match_priority.has_match:
            self._log_rule_matching("did not create event, because of wrong syslog priority")

        if has_canceling_condition:
            # Reasons preventing cancel-event
            if "match_ok" in rule and match_groups.get("match_groups_message_ok", False) is False:
                self._log_rule_matching("did not cancel event, because of wrong message")
            if (
                "cancel_application" in rule
                and match_groups.get("match_groups_syslog_application_ok", False) is False
            ):
                self._log_rule_matching("did not cancel event, because of wrong syslog application")
            if "cancel_priority" in rule and not match_priority.has_canceling_match:
                self._log_rule_matching("did not cancel event, because of wrong cancel priority")

        # TODO: create a better reason
        return MatchFailure(reason="Unknown")

    def event_rule_matches_generic(self, rule: Rule, event: Event) -> MatchResult:
        """
        Return match result against a list of generic match functions.

        Such as site, host, ip, facility, service_level and timeperiod.
        """
        generic_match_functions = [
            self.event_rule_matches_site,
            self.event_rule_matches_host,
            self.event_rule_matches_ip,
            self.event_rule_matches_facility,
            self.event_rule_matches_service_level,
            self.event_rule_matches_timeperiod,
        ]

        for match_function in generic_match_functions:
            result = match_function(rule, event)
            if isinstance(result, MatchFailure):
                self._log_rule_matching(result.reason)
                return result

        return MatchSuccess(cancelling=False, match_groups=MatchGroups())

    def event_rule_determine_match_priority(self, rule: Rule, event: Event) -> MatchPriority | None:
        p = event["priority"]

        if "match_priority" in rule:
            prio_from, prio_to = sorted(rule["match_priority"])
            has_match = prio_from <= p <= prio_to
        else:
            has_match = True

        if "cancel_priority" in rule:
            cancel_from, cancel_to = sorted(rule["cancel_priority"])
            has_canceling_match = cancel_from <= p <= cancel_to
        else:
            has_canceling_match = False

        if has_match is False and has_canceling_match is False:
            return None
        return MatchPriority(has_match=has_match, has_canceling_match=has_canceling_match)

    def event_rule_matches_site(self, rule: Rule, event: Event) -> MatchResult:
        if "match_site" not in rule or self._omd_site in rule["match_site"]:
            return MatchSuccess(cancelling=False, match_groups=MatchGroups())
        return MatchFailure(reason="The site does not match.")

    def event_rule_matches_host(self, rule: Rule, event: Event) -> MatchResult:
        if match(rule.get("match_host"), event["host"], complete=True) is False:
            return MatchFailure(
                reason=f"Did not match because of wrong host {event['host']!r} (need {format_pattern(rule.get('match_host'))!r})"
            )

        return MatchSuccess(cancelling=False, match_groups=MatchGroups())

    def event_rule_matches_ip(self, rule: Rule, event: Event) -> MatchResult:
        if not match_ip_network(rule.get("match_ipaddress", "0.0.0.0/0"), event["ipaddress"]):
            return MatchFailure(
                reason=f"Did not match because of wrong source IP address {event['ipaddress']!r} (need {rule.get('match_ipaddress')!r})"
            )

        return MatchSuccess(cancelling=False, match_groups=MatchGroups())

    def event_rule_matches_facility(self, rule: Rule, event: Event) -> MatchResult:
        if "match_facility" in rule and event["facility"] != rule["match_facility"]:
            return MatchFailure(reason="Did not match because of wrong syslog facility")

        return MatchSuccess(cancelling=False, match_groups=MatchGroups())

    def event_rule_matches_service_level(self, rule: Rule, event: Event) -> MatchResult:
        if "match_sl" in rule:
            sl_from, sl_to = rule["match_sl"]
            if sl_from > sl_to:
                sl_to, sl_from = sl_from, sl_to
            p = event.get("sl", 0)
            if p < sl_from or p > sl_to:
                return MatchFailure(
                    reason=f"Did not match because of wrong service level {p} (need {sl_from}..{sl_to})"
                )

        return MatchSuccess(cancelling=False, match_groups=MatchGroups())

    def event_rule_matches_timeperiod(self, rule: Rule, event: Event) -> MatchResult:
        if "match_timeperiod" in rule and not self._is_active_time_period(rule["match_timeperiod"]):
            return MatchFailure(
                reason=f"The time period {rule['match_timeperiod']} is not is not known or is currently not active"
            )
        return MatchSuccess(cancelling=False, match_groups=MatchGroups())

    def event_rule_determine_match_groups(
        self, rule: Rule, event: Event, match_groups: MatchGroups
    ) -> MatchResult:
        match_group_functions = [
            self.event_rule_matches_syslog_application,
            self.event_rule_matches_message,
        ]

        for match_function in match_group_functions:
            result = match_function(rule, event, match_groups)
            if isinstance(result, MatchFailure):
                self._log_rule_matching(result.reason)
                return result

        return MatchSuccess(cancelling=False, match_groups=MatchGroups())

    def event_rule_matches_syslog_application(
        self, rule: Rule, event: Event, match_groups: MatchGroups
    ) -> MatchResult:
        if "match_application" not in rule and "cancel_application" not in rule:
            return MatchSuccess(cancelling=False, match_groups=MatchGroups())

        # Syslog application
        if "match_application" in rule:
            match_groups["match_groups_syslog_application"] = match(
                rule.get("match_application"), event["application"], complete=False
            )

        # Syslog application canceling, this option must be explicitly set
        if "cancel_application" in rule:
            match_groups["match_groups_syslog_application_ok"] = match(
                rule.get("cancel_application"), event["application"], complete=False
            )

        # Detect impossible match
        if (
            match_groups.get("match_groups_syslog_application", False) is False
            and match_groups.get("match_groups_syslog_application_ok", False) is False
        ):
            return MatchFailure(reason="did not match, syslog application does not match")

        return MatchSuccess(cancelling=False, match_groups=MatchGroups())

    def event_rule_matches_message(
        self, rule: Rule, event: Event, match_groups: MatchGroups
    ) -> MatchResult:
        # Message matching, this condition is always active
        match_groups["match_groups_message"] = match(
            rule.get("match"), event["text"], complete=False
        )

        # Message canceling, this option must be explicitly set
        if "match_ok" in rule:
            match_groups["match_groups_message_ok"] = match(
                rule.get("match_ok"), event["text"], complete=False
            )

        # Detect impossible match
        if (
            match_groups["match_groups_message"] is False
            and match_groups.get("match_groups_message_ok", False) is False
        ):
            return MatchFailure(reason="did not match, message text does not match")

        return MatchSuccess(cancelling=False, match_groups=MatchGroups())
