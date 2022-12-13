#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging

import pytest

from cmk.ec.defaults import default_config
from cmk.ec.main import (
    Event,
    EventServer,
    make_config,
    MatchFailure,
    MatchGroups,
    MatchPriority,
    MatchResult,
    MatchSuccess,
    Rule,
    RuleMatcher,
    TextMatchResult,
)


@pytest.fixture(name="m")
def fixture_m() -> RuleMatcher:
    logger = logging.getLogger("cmk.mkeventd")
    config = default_config()
    config["debug_rules"] = True
    return RuleMatcher(logger, make_config(config))


@pytest.mark.parametrize(
    "message,result,match_message,cancel_message,match_groups,cancel_groups",
    [
        # No pattern, match
        ("bla CRIT", MatchSuccess(cancelling=False, match_groups={}), "", None, (), None),
        # Non regex, no match
        (
            "bla CRIT",
            MatchFailure("did not match, message text does not match"),
            "blub",
            None,
            False,
            None,
        ),
        # Regex, no match
        (
            "bla CRIT",
            MatchFailure("did not match, message text does not match"),
            "blub$",
            None,
            False,
            None,
        ),
        # None regex, no match, cancel match
        (
            "bla CRIT",
            MatchSuccess(cancelling=False, match_groups={}),
            "blub",
            "bla CRIT",
            False,
            (),
        ),
        # regex, no match, cancel match
        (
            "bla CRIT",
            MatchSuccess(cancelling=False, match_groups={}),
            "blub$",
            "bla CRIT$",
            False,
            (),
        ),
        # Non regex -> no match group
        (
            "bla CRIT",
            MatchSuccess(cancelling=False, match_groups={}),
            "bla CRIT",
            "bla OK",
            (),
            False,
        ),
        (
            "bla OK",
            MatchSuccess(cancelling=False, match_groups={}),
            "bla CRIT",
            "bla OK",
            False,
            (),
        ),
        # Regex without match group
        (
            "bla CRIT",
            MatchSuccess(cancelling=False, match_groups={}),
            "bla CRIT$",
            "bla OK$",
            (),
            False,
        ),
        (
            "bla OK",
            MatchSuccess(cancelling=False, match_groups={}),
            "bla CRIT$",
            "bla OK$",
            False,
            (),
        ),
        # Regex With match group
        (
            "bla CRIT",
            MatchSuccess(cancelling=False, match_groups={}),
            "(bla) CRIT$",
            "(bla) OK$",
            ("bla",),
            False,
        ),
        (
            "bla OK",
            MatchSuccess(cancelling=False, match_groups={}),
            "(bla) CRIT$",
            "(bla) OK$",
            False,
            ("bla",),
        ),
        # regex, both match
        ("bla OK", MatchSuccess(cancelling=False, match_groups={}), "bla .*", "bla OK", (), ()),
    ],
)
def test_match_message(
    m: RuleMatcher,
    message: str,
    result: MatchResult,
    match_message: str,
    cancel_message: str | None,
    match_groups: TextMatchResult,
    cancel_groups: bool | None,
) -> None:
    rule: Rule = {
        "match": EventServer._compile_matching_value("match", match_message),
    }

    if cancel_message is not None:
        rule["match_ok"] = EventServer._compile_matching_value("match_ok", cancel_message)

    event: Event = {"text": message}

    matched_groups: MatchGroups = {}
    assert m.event_rule_matches_message(rule, event, matched_groups) == result
    assert matched_groups["match_groups_message"] == match_groups

    if cancel_message is not None:
        assert matched_groups["match_groups_message_ok"] == cancel_groups
    else:
        assert "match_groups_message_ok" not in matched_groups


@pytest.mark.parametrize(
    "priority,match_priority,cancel_priority,expected",
    [
        # No condition at all
        (2, None, None, MatchPriority(has_match=True, has_canceling_match=False)),
        # positive
        (2, (0, 10), None, MatchPriority(has_match=True, has_canceling_match=False)),
        (2, (2, 2), None, MatchPriority(has_match=True, has_canceling_match=False)),
        (2, (1, 1), None, None),
        (2, (3, 5), None, None),
        (2, (10, 0), None, MatchPriority(has_match=True, has_canceling_match=False)),
        (2, (5, 3), None, None),
        # cancel
        (2, None, (2, 2), MatchPriority(has_match=True, has_canceling_match=True)),
        (2, (3, 5), (2, 2), MatchPriority(has_match=False, has_canceling_match=True)),
        (2, None, (0, 10), MatchPriority(has_match=True, has_canceling_match=True)),
        (2, None, (1, 1), MatchPriority(has_match=True, has_canceling_match=False)),
        (2, None, (3, 5), MatchPriority(has_match=True, has_canceling_match=False)),
        (2, (3, 5), (3, 5), None),
        (2, (5, 3), (2, 2), MatchPriority(has_match=False, has_canceling_match=True)),
        (2, None, (10, 0), MatchPriority(has_match=True, has_canceling_match=True)),
        (2, None, (5, 3), MatchPriority(has_match=True, has_canceling_match=False)),
        (2, (5, 3), (5, 3), None),
        # positive + cancel
        (2, (2, 2), (2, 2), MatchPriority(has_match=True, has_canceling_match=True)),
    ],
)
def test_match_priority(
    m: RuleMatcher,
    priority: int,
    match_priority: MatchPriority | None,
    cancel_priority: MatchPriority | None,
    expected: MatchPriority | None,
) -> None:
    rule: Rule = {}
    if match_priority is not None:
        rule["match_priority"] = match_priority
    if cancel_priority is not None:
        rule["cancel_priority"] = cancel_priority
    event: Event = {"priority": priority}
    assert m.event_rule_determine_match_priority(rule, event) == expected


@pytest.mark.parametrize(
    "rule,match_groups,match_priority,expected",
    [
        # No canceling
        (
            {"match": ""},
            {"match_groups_message": ()},
            MatchPriority(has_match=True, has_canceling_match=False),
            MatchSuccess(cancelling=False, match_groups={"match_groups_message": ()}),
        ),
        # Both configured but positive matches
        (
            {"match": "abc A abc", "match_ok": "abc X abc"},
            {"match_groups_message": ()},
            MatchPriority(has_match=True, has_canceling_match=False),
            MatchSuccess(cancelling=False, match_groups={"match_groups_message": ()}),
        ),
        # Both configured but  negative matches
        (
            {"match": "abc A abc", "match_ok": "abc X abc"},
            {"match_groups_message": False, "match_groups_message_ok": ()},
            MatchPriority(has_match=True, has_canceling_match=False),
            MatchSuccess(
                cancelling=True,
                match_groups={
                    "match_groups_message": False,
                    "match_groups_message_ok": (),
                },
            ),
        ),
        # Both match
        (
            {"match": "abc . abc", "match_ok": "abc X abc"},
            {"match_groups_message": (), "match_groups_message_ok": ()},
            MatchPriority(has_match=True, has_canceling_match=False),
            MatchSuccess(
                cancelling=True,
                match_groups={
                    "match_groups_message": (),
                    "match_groups_message_ok": (),
                },
            ),
        ),
    ],
)
def test_match_outcome(
    m: RuleMatcher,
    rule: Rule,
    match_groups: MatchGroups,
    match_priority: MatchPriority,
    expected: MatchResult,
) -> None:
    assert m._check_match_outcome(rule, match_groups, match_priority) == expected


@pytest.mark.parametrize(
    "result,rule",
    [
        (MatchSuccess(cancelling=False, match_groups={}), {}),
        (MatchFailure(reason="The site does not match."), {"match_site": []}),
        (MatchSuccess(cancelling=False, match_groups={}), {"match_site": ["NO_SITE"]}),
        (MatchFailure(reason="The site does not match."), {"match_site": ["dong"]}),
    ],
)
def test_match_site(m: RuleMatcher, rule: Rule, result: MatchResult) -> None:
    assert m.event_rule_matches_site(rule, {}) == result


@pytest.mark.parametrize(
    "result,rule,event",
    [
        (MatchSuccess(cancelling=False, match_groups={}), {}, {"host": "abc"}),
        (MatchSuccess(cancelling=False, match_groups={}), {"match_host": ""}, {"host": "abc"}),
        (MatchSuccess(cancelling=False, match_groups={}), {"match_host": ""}, {"host": ""}),
        (
            MatchFailure(reason="Did not match because of wrong host 'aaaabc' (need 'abc')"),
            {"match_host": "abc"},
            {"host": "aaaabc"},
        ),
        (MatchSuccess(cancelling=False, match_groups={}), {"match_host": ".bc"}, {"host": "xbc"}),
        (
            MatchFailure(reason="Did not match because of wrong host 'abcc' (need 'abc')"),
            {"match_host": "abc"},
            {"host": "abcc"},
        ),
        (
            MatchSuccess(cancelling=False, match_groups={}),
            {"match_host": "abc.*"},
            {"host": "abcc"},
        ),
        (
            MatchSuccess(cancelling=False, match_groups={}),
            {"match_host": ".*abc.*"},
            {"host": "ccabcc"},
        ),
        (MatchSuccess(cancelling=False, match_groups={}), {"match_host": "^abc$"}, {"host": "abc"}),
        (
            MatchFailure(reason="Did not match because of wrong host 'abx' (need '^abc$')"),
            {"match_host": "^abc$"},
            {"host": "abx"},
        ),
    ],
)
def test_match_host(m: RuleMatcher, result: MatchResult, rule: Rule, event: Event) -> None:

    if "match_host" in rule:
        rule = {
            **rule,  # type: ignore[misc] # mypy bug https://github.com/python/mypy/issues/4122
            "match_host": EventServer._compile_matching_value("match_host", rule["match_host"]),
        }

    assert m.event_rule_matches_host(rule, event) == result


@pytest.mark.parametrize(
    "result,rule,event",
    [
        (MatchSuccess(cancelling=False, match_groups={}), {}, {"ipaddress": "10.3.3.4"}),
        (
            MatchSuccess(cancelling=False, match_groups={}),
            {"match_ipaddress": "10.3.3.4"},
            {"ipaddress": "10.3.3.4"},
        ),
        (
            MatchSuccess(cancelling=False, match_groups={}),
            {"match_ipaddress": "10.3.3.0/24"},
            {"ipaddress": "10.3.3.4"},
        ),
        (
            MatchSuccess(cancelling=False, match_groups={}),
            {"match_ipaddress": "10.0.0.0/8"},
            {"ipaddress": "10.3.3.4"},
        ),
        (
            MatchFailure(
                reason="Did not match because of wrong source IP address '10.3.3.4' (need '11.0.0.0/8')"
            ),
            {"match_ipaddress": "11.0.0.0/8"},
            {"ipaddress": "10.3.3.4"},
        ),
        (
            MatchFailure(
                reason="Did not match because of wrong source IP address '10.3.3.4' (need '10.3.3.5')"
            ),
            {"match_ipaddress": "10.3.3.5"},
            {"ipaddress": "10.3.3.4"},
        ),
        (
            MatchFailure(
                reason="Did not match because of wrong source IP address '10.3.3.4' (need '10.3.3.0')"
            ),
            {"match_ipaddress": "10.3.3.0"},
            {"ipaddress": "10.3.3.4"},
        ),
    ],
)
def test_match_ipaddress(m: RuleMatcher, result: MatchResult, rule: Rule, event: Event) -> None:
    assert m.event_rule_matches_ip(rule, event) == result


@pytest.mark.parametrize(
    "result,rule,event",
    [
        (MatchSuccess(cancelling=False, match_groups={}), {}, {"facility": 1}),
        (MatchSuccess(cancelling=False, match_groups={}), {"match_facility": 1}, {"facility": 1}),
        (
            MatchFailure(reason="Did not match because of wrong syslog facility"),
            {"match_facility": 2},
            {"facility": 1},
        ),
        (
            MatchFailure(reason="Did not match because of wrong syslog facility"),
            {"match_facility": 0},
            {"facility": 1},
        ),
    ],
)
def test_match_facility(m: RuleMatcher, result: MatchResult, rule: Rule, event: Event) -> None:
    assert m.event_rule_matches_facility(rule, event) == result
