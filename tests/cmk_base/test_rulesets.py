import pytest

import cmk_base.rulesets as rulesets
from cmk.exceptions import MKGeneralException

import cmk

@pytest.fixture(autouse=True)
def fake_version(monkeypatch):
    monkeypatch.setattr(cmk, "omd_version", lambda: "1.4.0i1.cee")

# TODO: Test the negations
def test_service_extra_conf():
    import cmk_base.config as config

    config.all_hosts = ["host1|tag1|tag2", "host2|tag1"]
    config.collect_hosttags()
    ruleset = [
        ("1", [], rulesets.ALL_HOSTS, rulesets.ALL_SERVICES, {}),
        ("2", [], rulesets.ALL_HOSTS, rulesets.ALL_SERVICES, {}),
        ("3", ["tag1"], rulesets.ALL_HOSTS, rulesets.ALL_SERVICES, {}),
        ("4", ["tag2"], rulesets.ALL_HOSTS, rulesets.ALL_SERVICES, {}),
        ("5", ["tag3"], rulesets.ALL_HOSTS, rulesets.ALL_SERVICES, {}),
        ("6", ["tag3"], ["host1"], rulesets.ALL_SERVICES, {}),
        ("7", [], ["host1"], rulesets.ALL_SERVICES, {}),
        ("8", [], ["host1"], ["service1$"], {}),
        ("9", [], ["host1"], ["ser$"], {}),
        ("10", [], ["host1"], ["^serv$"], {}),
        ("11", [], ["~host"], rulesets.ALL_SERVICES, {}),
        # TODO: Is it really OK that this does not match "host1" below? Maybe a bug?!
        ("12", [], ["!host2"], rulesets.ALL_SERVICES, {}),
    ]

    assert rulesets.service_extra_conf("host1", "service1", ruleset) == \
            [ "1", "2", "3", "4", "7", "8", "11" ]

    assert rulesets.service_extra_conf("host1", "serv", ruleset) == \
            [ "1", "2", "3", "4", "7", "10", "11" ]

    assert rulesets.service_extra_conf("host2", "service1", ruleset) == \
            [ "1", "2", "3", "11" ]


# TODO: _convert_service_ruleset
# TODO: in_boolean_serviceconf_list
# TODO: _convert_boolean_service_ruleset
# TODO: host_extra_conf
# TODO: _convert_host_ruleset
# TODO: host_extra_conf_merged
# TODO: all_matching_hosts
# TODO: in_extraconf_hostlist
# TODO: in_binary_hostlist


def test_parse_host_rule():
    options = {'description': u'Put all hosts into the contact group "all"'}
    entry = ( 'all', [], rulesets.ALL_HOSTS, options)
    assert rulesets.parse_host_rule(entry) == ('all', [], rulesets.ALL_HOSTS, options)


def test_parse_host_rule_without_tags():
    options = {'description': u'Put all hosts into the contact group "all"'}
    entry = ( 'all', rulesets.ALL_HOSTS, options)
    assert rulesets.parse_host_rule(entry) == ('all', [], rulesets.ALL_HOSTS, options)


def test_parse_host_rule_invalid_length():
    options = {'description': u'Put all hosts into the contact group "all"'}
    entry = (None, None, 'all', rulesets.ALL_HOSTS, options)
    with pytest.raises(MKGeneralException):
        assert rulesets.parse_host_rule(entry)


def test_get_rule_options_regular_rule():
    options = {'description': u'Put all hosts into the contact group "all"'}
    entry = ( 'all', [], rulesets.ALL_HOSTS, options)
    assert rulesets.get_rule_options(entry) == (entry[:-1], options)


def test_get_rule_options_empty_options():
    options = {}
    entry = ( 'all', [], rulesets.ALL_HOSTS, options)
    assert rulesets.get_rule_options(entry) == (entry[:-1], options)


def test_get_rule_options_missing_options():
    entry = ( 'all', [], rulesets.ALL_HOSTS)
    assert rulesets.get_rule_options(entry) == (entry, {})


def test_hosttags_match_taglist():
    assert rulesets.hosttags_match_taglist(["tag1"], ["tag1"])
    assert rulesets.hosttags_match_taglist(["tag1", "tag2"], ["tag1"])
    assert rulesets.hosttags_match_taglist(["tag1", "tag2"], ["tag1", "tag2"])


def test_hosttags_match_taglist_not_matching():
    assert not rulesets.hosttags_match_taglist(["tag1"], ["tag2"])
    assert not rulesets.hosttags_match_taglist(["tag", "tag1", "tag22"], ["tag2"])
    assert not rulesets.hosttags_match_taglist(["tag1", "tag2"], ["tag2", "tag3"])


def test_hosttags_match_taglist_negate():
    assert not rulesets.hosttags_match_taglist(["tag1", "tag2"], ["tag1", "!tag2"])
    assert rulesets.hosttags_match_taglist(["tag1"], ["tag1", "!tag2"])

    assert not rulesets.hosttags_match_taglist(["tag1", "tag2"], ["!tag2+"])


def test_hosttags_match_taglist_prefix():
    assert rulesets.hosttags_match_taglist(["tag1", "tag2"], ["tag2+"])
    assert rulesets.hosttags_match_taglist(["tag1", "tax2"], ["tag+"])
    assert not rulesets.hosttags_match_taglist(["tag1", "tag2"], ["tag3+"])


def test_parse_negated():
    assert rulesets._parse_negated("") == (False, "")
    assert rulesets._parse_negated("!aaa") == (True, "aaa")
    assert rulesets._parse_negated("aaa") == (False, "aaa")


# TODO: convert_pattern
# TODO: convert_pattern_list
# TODO: in_extraconf_servicelist
# TODO: in_servicematcher_list
