import pytest

import cmk.log
from cmk.ec.main import RuleMatcher, SyslogPriority

@pytest.fixture()
def m():
    logger = cmk.log.get_logger("mkeventd")
    return RuleMatcher(logger, debug_rules=True)


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
