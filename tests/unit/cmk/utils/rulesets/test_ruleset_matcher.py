# encoding: utf-8
# pylint: disable=redefined-outer-name
import pytest  # type: ignore
from cmk.utils.rulesets.ruleset_matcher import RulesetMatcher, RulesetMatchObject


def test_ruleset_match_object_invalid_attribute_in_init():
    with pytest.raises(TypeError, match="unexpected keyword"):
        RulesetMatchObject(x=1)  # pylint: disable=unexpected-keyword-arg


def test_ruleset_match_object_no_conditions():
    x = RulesetMatchObject()
    assert x.host_name is None
    assert x.host_tags is None
    assert x.host_folder is None
    assert x.service_description is None


def test_ruleset_match_object_set_invalid_attribute():
    x = RulesetMatchObject()
    with pytest.raises(AttributeError, match="object has no attribute"):
        x.xyz = 123  # pylint: disable=assigning-non-slot


def test_ruleset_match_object_host_name():
    obj = RulesetMatchObject(host_name="abc")
    assert obj.host_name == "abc"


def test_ruleset_match_object_host_tags():
    obj = RulesetMatchObject(host_tags={"tag_group1": "tag1"})
    assert obj.host_tags == {"tag_group1": "tag1"}


def test_ruleset_match_object_host_folder():
    obj = RulesetMatchObject(host_folder="/abc/")
    assert obj.host_folder == "/abc/"


def test_ruleset_match_object_service_description():
    obj = RulesetMatchObject(service_description=u"Ümlaut")
    assert obj.service_description == u"Ümlaut"


def test_ruleset_match_object_to_dict():
    obj = RulesetMatchObject(host_name="abc", host_folder="/abc/", service_description=u"Ümlaut")
    assert obj.to_dict() == {
        "host_name": "abc",
        "host_folder": "/abc/",
        "service_description": u"Ümlaut",
    }


def test_ruleset_match_object_copy():
    obj = RulesetMatchObject(host_name="abc", service_description=u"Ümlaut")
    copied_obj = obj.copy()
    assert obj is not copied_obj
    assert obj.to_dict() == copied_obj.to_dict()


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
    {
        "value": "BLA",
        "condition": {
            "host_name": "xyz",
        },
        "options": {
            "disabled": True,
        },
    },
    {
        "value": "LEVEL1",
        "condition": {
            "host_folder": {
                "$regex": "^/lvl1/"
            },
        },
    },
    {
        "value": "LEVEL2",
        "condition": {
            "host_folder": {
                "$regex": "^/lvl1/lvl2/"
            },
        },
    },
    {
        "value": "XYZ",
        "condition": {
            "host_name": {
                "$in": [],
            },
        },
        "options": {},
    },
]


def test_basic_host_ruleset_get_matching_rules():
    matcher = RulesetMatcher()
    assert matcher.get_matching_rules(RulesetMatchObject(host_name="abc"), ruleset=ruleset) == []
    assert matcher.get_matching_rules(RulesetMatchObject(host_name="xyz"), ruleset=ruleset) == []
    assert matcher.get_matching_rules(
        RulesetMatchObject(host_name="host1"), ruleset=ruleset) == ruleset[:2]
    assert matcher.get_matching_rules(
        RulesetMatchObject(host_name="host2"), ruleset=ruleset) == [ruleset[1]]


def test_basic_host_ruleset_get_values():
    matcher = RulesetMatcher()
    assert matcher.get_values(RulesetMatchObject(host_name="abc"), ruleset=ruleset) == []
    assert matcher.get_values(RulesetMatchObject(host_name="xyz"), ruleset=ruleset) == []
    assert matcher.get_values(
        RulesetMatchObject(host_name="host1"), ruleset=ruleset) == ["BLA", "BLUB"]
    assert matcher.get_values(RulesetMatchObject(host_name="host2"), ruleset=ruleset) == ["BLUB"]


def test_basic_host_ruleset_get_values_subfolders():
    matcher = RulesetMatcher()
    assert matcher.get_values(RulesetMatchObject(), ruleset=ruleset) == []
    assert matcher.get_values(RulesetMatchObject(host_folder="/level1/"), ruleset=ruleset) == []
    assert matcher.get_values(
        RulesetMatchObject(host_folder="/level1/level2/"), ruleset=ruleset) == []


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
    {
        "value": {
            "hu": "BLA"
        },
        "condition": {
            "host_name": "xyz",
        },
        "options": {
            "disabled": True,
        },
    },
]


def test_basic_host_ruleset_get_merged_dict_values():
    matcher = RulesetMatcher()
    assert matcher.get_merged_dict(RulesetMatchObject(host_name="abc"), ruleset=dict_ruleset) == {}
    assert matcher.get_merged_dict(RulesetMatchObject(host_name="xyz"), ruleset=dict_ruleset) == {}
    assert matcher.get_merged_dict(
        RulesetMatchObject(host_name="host1"), ruleset=dict_ruleset) == {
            "hu": "BLA",
            "ho": "BLA",
            "he": "BLUB",
        }
    assert matcher.get_merged_dict(
        RulesetMatchObject(host_name="host2"), ruleset=dict_ruleset) == {
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
    {
        "value": True,
        "condition": {
            "host_name": "xyz",
        },
        "options": {
            "disabled": True,
        },
    },
]


def test_basic_host_ruleset_is_matching():
    matcher = RulesetMatcher()
    assert matcher.is_matching(RulesetMatchObject(host_name="abc"), ruleset=binary_ruleset) is False
    assert matcher.is_matching(RulesetMatchObject(host_name="xyz"), ruleset=binary_ruleset) is False
    assert matcher.is_matching(
        RulesetMatchObject(host_name="host1"), ruleset=binary_ruleset) is True
    assert matcher.is_matching(
        RulesetMatchObject(host_name="host2"), ruleset=binary_ruleset) is False
