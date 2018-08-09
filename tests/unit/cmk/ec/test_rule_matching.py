import pytest

import cmk.log
from cmk.ec.main import RuleMatcher, SyslogPriority, EventServer

@pytest.fixture()
def m():
    logger = cmk.log.get_logger("mkeventd")
    return RuleMatcher(logger, {"debug_rules": True})

@pytest.mark.parametrize("message,result,match_message,cancel_message,match_groups,cancel_groups", [
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
    ("bla OK",   True, "bla CRIT", "bla OK", False, ()),
    # Regex without match group
    ("bla CRIT", True, "bla CRIT$", "bla OK$", (), False),
    ("bla OK",   True, "bla CRIT$", "bla OK$", False, ()),
    # Regex With match group
    ("bla CRIT", True, "(bla) CRIT$", "(bla) OK$", ("bla",), False),
    ("bla OK",   True, "(bla) CRIT$", "(bla) OK$", False, ("bla",)),
    # regex, both match
    ("bla OK",   True, "bla .*", "bla OK", (), ()),
])
def test_match_message(m, message, result, match_message, cancel_message, match_groups, cancel_groups):
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


@pytest.mark.parametrize("priority,match_priority,cancel_priority,has_match,has_canceling_match,result", [
    # No condition at all
    (2, None,    None,   True,  False, True),
    # positive
    (2, (0, 10), None,   True,  False, True),
    (2, (2, 2),  None,   True,  False, True),
    (2, (1, 1),  None,   False, False, False),
    (2, (3, 5),  None,   False, False, False),
    # cancel
    (2, None,    (2,2),  True,  True,  True),
    (2, (3, 5),  (2,2),  False, True,  True),
    (2, None,    (0,10), True,  True,  True),
    (2, None,    (1,1),  True,  False, True),
    (2, None,    (3,5),  True,  False, True),
    (2, (3, 5),  (3,5),  False, False, False),
    # positive + cancel
    (2, (2, 2),  (2,2),  True,  True,  True),
])
def test_match_priority(m, priority, match_priority, cancel_priority, has_match, has_canceling_match, result):
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


@pytest.mark.parametrize("rule,match_groups,match_priority,result", [
    # No canceling
    ({"match": ""}, {"match_groups_message": ()}, {"has_match": True}, (False, {"match_groups_message": ()})),
    # Both configured but positive matches
    ({"match": "abc A abc", "match_ok": "abc X abc"},
     {"match_groups_message": ()},
     {"has_match": True},
     (False, {"match_groups_message": ()})),
    # Both configured but  negative matches
    ({"match": "abc A abc", "match_ok": "abc X abc"},
     {"match_groups_message": False, "match_groups_message_ok": ()},
     {"has_match": True},
     (True, {"match_groups_message": False, "match_groups_message_ok": ()})),
    # Both match
    ({"match": "abc . abc", "match_ok": "abc X abc"},
     {"match_groups_message": (), "match_groups_message_ok": ()},
     {"has_match": True},
     (True, {"match_groups_message": (), "match_groups_message_ok": ()})),
])
def test_match_outcome(m, rule, match_groups, match_priority, result):
    assert m._check_match_outcome(rule, match_groups, match_priority) == result
