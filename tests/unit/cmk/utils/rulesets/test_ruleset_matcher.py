# encoding: utf-8
# pylint: disable=redefined-outer-name
from cmk.utils.rulesets.ruleset_matcher import RulesetMatcher


def test_basic_matching():
    ruleset = [{"condition": {"a": "b"}}, {"condition": {"a": "c"}}]
    matcher = RulesetMatcher()
    assert matcher.get_matching_rules({"a": "b"}, ruleset=ruleset) == [ruleset[0]]


ruleset = [
    {
        "value": "BLA",
        "condition": {
            "host_name": "host1",
        },
        "options": {},
    },
    {
        "value": "BLUB",
        "condition": {
            "host_name": {
                "$in": ["host1", "host2"]
            },
        },
        "options": {},
    },
]


def test_basic_host_ruleset_get_matching_rules():
    matcher = RulesetMatcher()
    assert matcher.get_matching_rules({"host_name": "abc"}, ruleset=ruleset) == []
    assert matcher.get_matching_rules({"host_name": "host1"}, ruleset=ruleset) == ruleset
    assert matcher.get_matching_rules({"host_name": "host2"}, ruleset=ruleset) == [ruleset[1]]


def test_basic_host_ruleset_get_values():
    matcher = RulesetMatcher()
    assert matcher.get_values({"host_name": "abc"}, ruleset=ruleset) == []
    assert matcher.get_values({"host_name": "host1"}, ruleset=ruleset) == ["BLA", "BLUB"]
    assert matcher.get_values({"host_name": "host2"}, ruleset=ruleset) == ["BLUB"]


dict_ruleset = [
    {
        "value": {
            "hu": "BLA"
        },
        "condition": {
            "host_name": "host1",
        },
        "options": {},
    },
    {
        "value": {
            "ho": "BLA"
        },
        "condition": {
            "host_name": {
                "$in": ["host1", "host2"]
            },
        },
        "options": {},
    },
    {
        "value": {
            "hu": "BLUB",
            "he": "BLUB",
        },
        "condition": {
            "host_name": {
                "$in": ["host1", "host2"]
            },
        },
        "options": {},
    },
]


def test_basic_host_ruleset_get_merged_dict_values():
    matcher = RulesetMatcher()
    assert matcher.get_merged_dict({"host_name": "abc"}, ruleset=dict_ruleset) == {}
    assert matcher.get_merged_dict({"host_name": "host1"}, ruleset=dict_ruleset) == {
        "hu": "BLA",
        "ho": "BLA",
        "he": "BLUB",
    }
    assert matcher.get_merged_dict({"host_name": "host2"}, ruleset=dict_ruleset) == {
        "hu": "BLUB",
        "ho": "BLA",
        "he": "BLUB",
    }


binary_ruleset = [
    {
        "value": True,
        "condition": {
            "host_name": "host1",
        },
        "options": {},
    },
    {
        "value": False,
        "condition": {
            "host_name": {
                "$in": ["host1", "host2"]
            },
        },
        "options": {},
    },
    {
        "value": True,
        "condition": {
            "host_name": {
                "$in": ["host1", "host2"]
            },
        },
        "options": {},
    },
]


def test_basic_host_ruleset_is_matching():
    matcher = RulesetMatcher()
    assert matcher.is_matching({"host_name": "abc"}, ruleset=binary_ruleset) is False
    assert matcher.is_matching({"host_name": "host1"}, ruleset=binary_ruleset) is True
    assert matcher.is_matching({"host_name": "host2"}, ruleset=binary_ruleset) is False
