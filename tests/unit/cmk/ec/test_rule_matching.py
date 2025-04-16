#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import re

import pytest

from cmk.ccc.site import SiteId

import cmk.ec.export as ec
from cmk.ec.config import MatchGroups, TextMatchResult
from cmk.ec.rule_matcher import compile_matching_value, MatchPriority


@pytest.mark.parametrize(
    "message,result,match_message,cancel_message,match_result,cancel_groups",
    [
        # No pattern, match
        (
            "bla CRIT",
            ec.MatchSuccess(cancelling=False, match_groups=MatchGroups()),
            "",
            None,
            (),
            None,
        ),
        # Non regex, no match
        (
            "bla CRIT",
            ec.MatchFailure(reason="did not match, message text does not match"),
            "blub",
            None,
            False,
            None,
        ),
        # Regex, no match
        (
            "bla CRIT",
            ec.MatchFailure(reason="did not match, message text does not match"),
            "blub$",
            None,
            False,
            None,
        ),
        # None regex, no match, cancel match
        (
            "bla CRIT",
            ec.MatchSuccess(cancelling=False, match_groups=MatchGroups()),
            "blub",
            "bla CRIT",
            False,
            (),
        ),
        # regex, no match, cancel match
        (
            "bla CRIT",
            ec.MatchSuccess(cancelling=False, match_groups=MatchGroups()),
            "blub$",
            "bla CRIT$",
            False,
            (),
        ),
        # Non regex -> no match group
        (
            "bla CRIT",
            ec.MatchSuccess(cancelling=False, match_groups=MatchGroups()),
            "bla CRIT",
            "bla OK",
            (),
            False,
        ),
        (
            "bla OK",
            ec.MatchSuccess(cancelling=False, match_groups=MatchGroups()),
            "bla CRIT",
            "bla OK",
            False,
            (),
        ),
        # Regex without match group
        (
            "bla CRIT",
            ec.MatchSuccess(cancelling=False, match_groups=MatchGroups()),
            "bla CRIT$",
            "bla OK$",
            (),
            False,
        ),
        (
            "bla OK",
            ec.MatchSuccess(cancelling=False, match_groups=MatchGroups()),
            "bla CRIT$",
            "bla OK$",
            False,
            (),
        ),
        # Regex With match group
        (
            "bla CRIT",
            ec.MatchSuccess(cancelling=False, match_groups=MatchGroups()),
            "(bla) CRIT$",
            "(bla) OK$",
            ("bla",),
            False,
        ),
        (
            "bla OK",
            ec.MatchSuccess(cancelling=False, match_groups=MatchGroups()),
            "(bla) CRIT$",
            "(bla) OK$",
            False,
            ("bla",),
        ),
        # regex, both match
        (
            "bla OK",
            ec.MatchSuccess(cancelling=False, match_groups=MatchGroups()),
            "bla .*",
            "bla OK",
            (),
            (),
        ),
        # regex, dot star
        (
            "test ODBC test",
            ec.MatchSuccess(cancelling=False, match_groups=MatchGroups()),
            ".*ODBC",
            "test ODBC",
            (),
            (),
        ),
        # regex, dot star also at the end
        (
            "test ODBC test",
            ec.MatchSuccess(cancelling=False, match_groups=MatchGroups()),
            ".*ODBC.*",
            "test ODBC test",
            (),
            (),
        ),
    ],
)
def test_match_message(
    message: str,
    result: ec.MatchResult,
    match_message: str,
    cancel_message: str | None,
    match_result: TextMatchResult,
    cancel_groups: bool | None,
) -> None:
    m = ec.RuleMatcher(None, SiteId("test_site"), lambda time_period_name: True)
    rule = (
        ec.Rule(match=match_message)
        if cancel_message is None
        else ec.Rule(match=match_message, match_ok=cancel_message)
    )
    ec.compile_rule(rule)
    event = ec.Event(text=message)
    match_groups = MatchGroups()

    assert m.event_rule_matches_message(rule, event, match_groups) == result
    assert match_groups["match_groups_message"] == match_result
    assert match_groups.get("match_groups_message_ok") == (
        None if cancel_message is None else cancel_groups
    )


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
    priority: int,
    match_priority: MatchPriority | None,
    cancel_priority: MatchPriority | None,
    expected: MatchPriority | None,
) -> None:
    m = ec.RuleMatcher(None, SiteId("test_site"), lambda time_period_name: True)
    rule = ec.Rule()
    if match_priority is not None:
        rule["match_priority"] = match_priority
    if cancel_priority is not None:
        rule["cancel_priority"] = cancel_priority
    event = ec.Event(priority=priority)
    assert m.event_rule_determine_match_priority(rule, event) == expected


@pytest.mark.parametrize(
    "rule,match_groups,match_priority,expected",
    [
        # No canceling
        (
            {"match": ""},
            {"match_groups_message": ()},
            MatchPriority(has_match=True, has_canceling_match=False),
            ec.MatchSuccess(cancelling=False, match_groups=MatchGroups(match_groups_message=())),
        ),
        # Both configured but positive matches
        (
            {"match": "abc A abc", "match_ok": "abc X abc"},
            {"match_groups_message": ()},
            MatchPriority(has_match=True, has_canceling_match=False),
            ec.MatchSuccess(cancelling=False, match_groups=MatchGroups(match_groups_message=())),
        ),
        # Both configured but  negative matches
        (
            {"match": "abc A abc", "match_ok": "abc X abc"},
            {"match_groups_message": False, "match_groups_message_ok": ()},
            MatchPriority(has_match=True, has_canceling_match=False),
            ec.MatchSuccess(
                cancelling=True,
                match_groups=MatchGroups(
                    match_groups_message=False,
                    match_groups_message_ok=(),
                ),
            ),
        ),
        # Both match
        (
            {"match": "abc . abc", "match_ok": "abc X abc"},
            {"match_groups_message": (), "match_groups_message_ok": ()},
            MatchPriority(has_match=True, has_canceling_match=False),
            ec.MatchSuccess(
                cancelling=True,
                match_groups=MatchGroups(
                    match_groups_message=(),
                    match_groups_message_ok=(),
                ),
            ),
        ),
    ],
)
def test_match_outcome(
    rule: ec.Rule,
    match_groups: MatchGroups,
    match_priority: MatchPriority,
    expected: ec.MatchResult,
) -> None:
    m = ec.RuleMatcher(None, SiteId("test_site"), lambda time_period_name: True)
    assert m._check_match_outcome(rule, match_groups, match_priority) == expected


@pytest.mark.parametrize(
    "result,rule",
    [
        (ec.MatchSuccess(cancelling=False, match_groups=MatchGroups()), {}),
        (ec.MatchFailure(reason="The site does not match."), {"match_site": []}),
        (
            ec.MatchSuccess(cancelling=False, match_groups=MatchGroups()),
            {"match_site": ["NO_SITE"]},
        ),
        (ec.MatchFailure(reason="The site does not match."), {"match_site": ["dong"]}),
    ],
)
def test_match_site(rule: ec.Rule, result: ec.MatchResult) -> None:
    # TODO why is "NO_SITE" necessary here. Random string as SiteId fails
    m = ec.RuleMatcher(None, SiteId("NO_SITE"), lambda time_period_name: True)
    assert m.event_rule_matches_site(rule, {}) == result


@pytest.mark.parametrize(
    "result,rule,event",
    [
        (ec.MatchSuccess(cancelling=False, match_groups=MatchGroups()), {}, {"host": "abc"}),
        # TODO weird the empty string in the rule seems to be interpreted as 'no match_host specified', which is clearly incorrect.
        (
            ec.MatchSuccess(cancelling=False, match_groups=MatchGroups()),
            {"match_host": ""},
            {"host": "abc"},
        ),
        (
            ec.MatchSuccess(cancelling=False, match_groups=MatchGroups()),
            {"match_host": ""},
            {"host": ""},
        ),
        (
            ec.MatchFailure(reason="Did not match because of wrong host 'aaaabc' (need 'abc')"),
            {"match_host": "abc"},
            {"host": "aaaabc"},
        ),
        (
            ec.MatchSuccess(cancelling=False, match_groups=MatchGroups()),
            {"match_host": ".bc"},
            {"host": "xbc"},
        ),
        (
            ec.MatchFailure(reason="Did not match because of wrong host 'abcc' (need 'abc')"),
            {"match_host": "abc"},
            {"host": "abcc"},
        ),
        (
            ec.MatchSuccess(cancelling=False, match_groups=MatchGroups()),
            {"match_host": "abc.*"},
            {"host": "abcc"},
        ),
        (
            ec.MatchSuccess(cancelling=False, match_groups=MatchGroups()),
            {"match_host": ".*abc.*"},
            {"host": "ccabcc"},
        ),
        (
            ec.MatchSuccess(cancelling=False, match_groups=MatchGroups()),
            {"match_host": "^abc$"},
            {"host": "abc"},
        ),
        (
            ec.MatchFailure(reason="Did not match because of wrong host 'abx' (need '^abc$')"),
            {"match_host": "^abc$"},
            {"host": "abx"},
        ),
    ],
)
def test_match_host(result: ec.MatchResult, rule: ec.Rule, event: ec.Event) -> None:
    m = ec.RuleMatcher(None, SiteId("test_site"), lambda time_period_name: True)
    rule = rule.copy()
    ec.compile_rule(rule)
    assert m.event_rule_matches_host(rule, event) == result


@pytest.mark.parametrize(
    "result,rule,event",
    [
        (
            ec.MatchSuccess(cancelling=False, match_groups=MatchGroups()),
            {},
            {"ipaddress": "10.3.3.4"},
        ),
        (
            ec.MatchSuccess(cancelling=False, match_groups=MatchGroups()),
            {"match_ipaddress": "10.3.3.4"},
            {"ipaddress": "10.3.3.4"},
        ),
        (
            ec.MatchSuccess(cancelling=False, match_groups=MatchGroups()),
            {"match_ipaddress": "10.3.3.0/24"},
            {"ipaddress": "10.3.3.4"},
        ),
        (
            ec.MatchSuccess(cancelling=False, match_groups=MatchGroups()),
            {"match_ipaddress": "2001:db00::0/24"},
            {"ipaddress": "2001:db00::1"},
        ),
        (
            ec.MatchSuccess(cancelling=False, match_groups=MatchGroups()),
            {"match_ipaddress": "10.0.0.0/8"},
            {"ipaddress": "10.3.3.4"},
        ),
        (
            ec.MatchFailure(
                reason="Did not match because of wrong source IP address '10.3.3.4' (need '11.0.0.0/8')"
            ),
            {"match_ipaddress": "11.0.0.0/8"},
            {"ipaddress": "10.3.3.4"},
        ),
        (
            ec.MatchFailure(
                reason="Did not match because of wrong source IP address '2002:db00::1' (need '2001:db00::0/24')"
            ),
            {"match_ipaddress": "2001:db00::0/24"},
            {"ipaddress": "2002:db00::1"},
        ),
        (
            ec.MatchFailure(
                reason="Did not match because of wrong source IP address '10.3.3.4' (need '10.3.3.5')"
            ),
            {"match_ipaddress": "10.3.3.5"},
            {"ipaddress": "10.3.3.4"},
        ),
        (
            ec.MatchFailure(
                reason="Did not match because of wrong source IP address '10.3.3.4' (need '10.3.3.0')"
            ),
            {"match_ipaddress": "10.3.3.0"},
            {"ipaddress": "10.3.3.4"},
        ),
    ],
)
def test_match_ipaddress(result: ec.MatchResult, rule: ec.Rule, event: ec.Event) -> None:
    m = ec.RuleMatcher(None, SiteId("test_site"), lambda time_period_name: True)
    assert m.event_rule_matches_ip(rule, event) == result


@pytest.mark.parametrize(
    "result,rule,event",
    [
        (ec.MatchSuccess(cancelling=False, match_groups=MatchGroups()), {}, {"facility": 1}),
        (
            ec.MatchSuccess(cancelling=False, match_groups=MatchGroups()),
            {"match_facility": 1},
            {"facility": 1},
        ),
        (
            ec.MatchFailure(reason="Did not match because of wrong syslog facility"),
            {"match_facility": 2},
            {"facility": 1},
        ),
        (
            ec.MatchFailure(reason="Did not match because of wrong syslog facility"),
            {"match_facility": 0},
            {"facility": 1},
        ),
    ],
)
def test_match_facility(result: ec.MatchResult, rule: ec.Rule, event: ec.Event) -> None:
    m = ec.RuleMatcher(None, SiteId("test_site"), lambda time_period_name: True)
    assert m.event_rule_matches_facility(rule, event) == result


@pytest.mark.parametrize(
    "original_value, expected_result",
    [
        ("simpleString", "simplestring"),
        ("  spaces  ", "spaces"),
        (".*regex", "regex"),
        ("", None),
        ("    ", None),
        (".*", None),
    ],
)
def test_compile_matching_value_non_regex(original_value: str, expected_result: str) -> None:
    assert compile_matching_value("match", original_value) == expected_result


@pytest.mark.parametrize(
    "original_value, expected_start",
    [("^regex$", "^regex$"), (".*regex.*", "regex.*"), (".*?lazy", ".*?lazy")],
)
def test_compile_matching_value_regex(original_value: str, expected_start: str) -> None:
    compiled_pattern = compile_matching_value("match", original_value)
    assert isinstance(compiled_pattern, re.Pattern)
    assert compiled_pattern.pattern.startswith(expected_start)


@pytest.mark.parametrize("key", ["non_match", "random_key"])
def test_compile_matching_value_different_key(key: str) -> None:
    original_value = ".*regex"
    compiled_pattern = compile_matching_value(key, original_value)
    assert isinstance(compiled_pattern, re.Pattern)
    # Expect the original pattern since the key is not in {"match", "match_ok"}
    assert compiled_pattern.pattern == original_value
