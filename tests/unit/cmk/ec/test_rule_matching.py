import logging
import pytest

import cmk
from cmk.ec.main import RuleMatcher, SyslogPriority, EventServer


@pytest.fixture()
def m():
    logger = logging.getLogger("cmk.mkeventd")
    return RuleMatcher(logger, {"debug_rules": True})


@pytest.mark.parametrize(
    "message,result,match_message,cancel_message,match_groups,cancel_groups",
    [
        # No pattern, match
        ("bla CRIT", True, "", None, (), None),
        # Non regex, no match
        ("bla CRIT", False, "blub", None, False, None),
        # Regex, no match
        ("bla CRIT", False, "blub$", None, False, None),
        # None regex, no match, cancel match
        ("bla CRIT", True, "blub", "bla CRIT", False, ()),
        # regex, no match, cancel match
        ("bla CRIT", True, "blub$", "bla CRIT$", False, ()),
        # Non regex -> no match group
        ("bla CRIT", True, "bla CRIT", "bla OK", (), False),
        ("bla OK", True, "bla CRIT", "bla OK", False, ()),
        # Regex without match group
        ("bla CRIT", True, "bla CRIT$", "bla OK$", (), False),
        ("bla OK", True, "bla CRIT$", "bla OK$", False, ()),
        # Regex With match group
        ("bla CRIT", True, "(bla) CRIT$", "(bla) OK$", ("bla",), False),
        ("bla OK", True, "(bla) CRIT$", "(bla) OK$", False, ("bla",)),
        # regex, both match
        ("bla OK", True, "bla .*", "bla OK", (), ()),
    ])
def test_match_message(m, message, result, match_message, cancel_message, match_groups,
                       cancel_groups):
    rule = {
        "match": EventServer._compile_matching_value("match", match_message),
    }

    if cancel_message is not None:
        rule["match_ok"] = EventServer._compile_matching_value("match_ok", cancel_message)

    event = {"text": message}

    matched_groups = {}
    assert m.event_rule_matches_message(rule, event, matched_groups) == result
    assert matched_groups["match_groups_message"] == match_groups

    if cancel_message is not None:
        assert matched_groups["match_groups_message_ok"] == cancel_groups
    else:
        assert "match_groups_message_ok" not in matched_groups


@pytest.mark.parametrize(
    "priority,match_priority,cancel_priority,has_match,has_canceling_match,result",
    [
        # No condition at all
        (2, None, None, True, False, True),
        # positive
        (2, (0, 10), None, True, False, True),
        (2, (2, 2), None, True, False, True),
        (2, (1, 1), None, False, False, False),
        (2, (3, 5), None, False, False, False),
        (2, (10, 0), None, True, False, True),
        (2, (2, 2), None, True, False, True),
        (2, (1, 1), None, False, False, False),
        (2, (5, 3), None, False, False, False),
        # cancel
        (2, None, (2, 2), True, True, True),
        (2, (3, 5), (2, 2), False, True, True),
        (2, None, (0, 10), True, True, True),
        (2, None, (1, 1), True, False, True),
        (2, None, (3, 5), True, False, True),
        (2, (3, 5), (3, 5), False, False, False),
        (2, None, (2, 2), True, True, True),
        (2, (5, 3), (2, 2), False, True, True),
        (2, None, (10, 0), True, True, True),
        (2, None, (1, 1), True, False, True),
        (2, None, (5, 3), True, False, True),
        (2, (5, 3), (5, 3), False, False, False),
        # positive + cancel
        (2, (2, 2), (2, 2), True, True, True),
    ])
def test_match_priority(m, priority, match_priority, cancel_priority, has_match,
                        has_canceling_match, result):
    rule = {}
    if match_priority is not None:
        rule["match_priority"] = match_priority
    if cancel_priority is not None:
        rule["cancel_priority"] = cancel_priority

    event = {"priority": priority}

    matched_match_priority = {}
    assert m.event_rule_determine_match_priority(rule, event, matched_match_priority) == result
    assert matched_match_priority["has_match"] == has_match
    assert matched_match_priority["has_canceling_match"] == has_canceling_match


@pytest.mark.parametrize(
    "rule,match_groups,match_priority,result",
    [
        # No canceling
        ({
            "match": ""
        }, {
            "match_groups_message": ()
        }, {
            "has_match": True
        }, (False, {
            "match_groups_message": ()
        })),
        # Both configured but positive matches
        ({
            "match": "abc A abc",
            "match_ok": "abc X abc"
        }, {
            "match_groups_message": ()
        }, {
            "has_match": True
        }, (False, {
            "match_groups_message": ()
        })),
        # Both configured but  negative matches
        ({
            "match": "abc A abc",
            "match_ok": "abc X abc"
        }, {
            "match_groups_message": False,
            "match_groups_message_ok": ()
        }, {
            "has_match": True
        }, (True, {
            "match_groups_message": False,
            "match_groups_message_ok": ()
        })),
        # Both match
        ({
            "match": "abc . abc",
            "match_ok": "abc X abc"
        }, {
            "match_groups_message": (),
            "match_groups_message_ok": ()
        }, {
            "has_match": True
        }, (True, {
            "match_groups_message": (),
            "match_groups_message_ok": ()
        })),
    ])
def test_match_outcome(m, rule, match_groups, match_priority, result):
    assert m._check_match_outcome(rule, match_groups, match_priority) == result


@pytest.mark.parametrize("result,rule", [
    (True, {}),
    (False, {
        "match_site": []
    }),
    (True, {
        "match_site": ["ding"]
    }),
    (False, {
        "match_site": ["dong"]
    }),
])
def test_match_site(m, rule, result, monkeypatch):
    monkeypatch.setattr(cmk, "omd_site", lambda: "ding")
    assert m.event_rule_matches_site(rule, {}) == result


@pytest.mark.parametrize("result,rule,event", [
    (True, {}, {
        "host": "abc"
    }),
    (True, {
        "match_host": ""
    }, {
        "host": "abc"
    }),
    (True, {
        "match_host": ""
    }, {
        "host": ""
    }),
    (False, {
        "match_host": "abc"
    }, {
        "host": "aaaabc"
    }),
    (True, {
        "match_host": ".bc"
    }, {
        "host": "xbc"
    }),
    (False, {
        "match_host": "abc"
    }, {
        "host": "abcc"
    }),
    (True, {
        "match_host": "abc.*"
    }, {
        "host": "abcc"
    }),
    (True, {
        "match_host": ".*abc.*"
    }, {
        "host": "ccabcc"
    }),
    (True, {
        "match_host": "^abc$"
    }, {
        "host": "abc"
    }),
    (False, {
        "match_host": "^abc$"
    }, {
        "host": "abx"
    }),
])
def test_match_host(m, result, rule, event):
    if "match_host" in rule:
        rule["match_host"] = EventServer._compile_matching_value("match_host", rule["match_host"])
    assert m.event_rule_matches_host(rule, event) == result


@pytest.mark.parametrize("result,rule,event", [
    (True, {}, {
        "ipaddress": "10.3.3.4"
    }),
    (True, {
        "match_ipaddress": "10.3.3.4"
    }, {
        "ipaddress": "10.3.3.4"
    }),
    (True, {
        "match_ipaddress": "10.3.3.0/24"
    }, {
        "ipaddress": "10.3.3.4"
    }),
    (True, {
        "match_ipaddress": "10.0.0.0/8"
    }, {
        "ipaddress": "10.3.3.4"
    }),
    (False, {
        "match_ipaddress": "11.0.0.0/8"
    }, {
        "ipaddress": "10.3.3.4"
    }),
    (False, {
        "match_ipaddress": "10.3.3.5"
    }, {
        "ipaddress": "10.3.3.4"
    }),
    (False, {
        "match_ipaddress": "10.3.3.0"
    }, {
        "ipaddress": "10.3.3.4"
    }),
])
def test_match_ipaddress(m, result, rule, event):
    assert m.event_rule_matches_ip(rule, event) == result


@pytest.mark.parametrize("result,rule,event", [
    (True, {}, {
        "facility": 1
    }),
    (True, {
        "match_facility": 1
    }, {
        "facility": 1
    }),
    (False, {
        "match_facility": 2
    }, {
        "facility": 1
    }),
    (False, {
        "match_facility": 0
    }, {
        "facility": 1
    }),
])
def test_match_facility(m, result, rule, event):
    assert m.event_rule_matches_facility(rule, event) == result
