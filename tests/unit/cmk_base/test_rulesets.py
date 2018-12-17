import pytest

import cmk_base.config as config
from cmk.utils.exceptions import MKGeneralException

import cmk

@pytest.fixture(autouse=True)
def fake_version(monkeypatch):
    monkeypatch.setattr(cmk, "omd_version", lambda: "1.4.0i1.cee")


# Automatically refresh caches for each test
@pytest.fixture(autouse=True, scope="function")
def clear_config_caches(monkeypatch):
    import cmk_base
    import cmk_base.caching
    monkeypatch.setattr(cmk_base, "config_cache", cmk_base.caching.CacheManager())
    monkeypatch.setattr(cmk_base, "runtime_cache", cmk_base.caching.CacheManager())


# TODO: Test the negations
def test_service_extra_conf(monkeypatch):
    import cmk_base.config as config
    monkeypatch.setattr(config, "all_hosts", ["host1|tag1|tag2", "host2|tag1"])
    monkeypatch.setattr(config, "clusters", {})
    config.collect_hosttags()

    ruleset = [
        ("1", [], config.ALL_HOSTS, config.ALL_SERVICES, {}),
        ("2", [], config.ALL_HOSTS, config.ALL_SERVICES, {}),
        ("3", ["tag1"], config.ALL_HOSTS, config.ALL_SERVICES, {}),
        ("4", ["tag2"], config.ALL_HOSTS, config.ALL_SERVICES, {}),
        ("5", ["tag3"], config.ALL_HOSTS, config.ALL_SERVICES, {}),
        ("6", ["tag3"], ["host1"], config.ALL_SERVICES, {}),
        ("7", [], ["host1"], config.ALL_SERVICES, {}),
        ("8", [], ["host1"], ["service1$"], {}),
        ("9", [], ["host1"], ["ser$"], {}),
        ("10", [], ["host1"], ["^serv$"], {}),
        ("11", [], ["~host"], config.ALL_SERVICES, {}),
        # TODO: Is it really OK that this does not match "host1" below? Maybe a bug?!
        ("12", [], ["!host2"], config.ALL_SERVICES, {}),
    ]

    assert config.service_extra_conf("host1", "service1", ruleset) == \
            [ "1", "2", "3", "4", "7", "8", "11" ]

    assert config.service_extra_conf("host1", "serv", ruleset) == \
            [ "1", "2", "3", "4", "7", "10", "11" ]

    assert config.service_extra_conf("host2", "service1", ruleset) == \
            [ "1", "2", "3", "11" ]


# TODO: _convert_service_ruleset
# TODO: in_boolean_serviceconf_list
# TODO: _convert_boolean_service_ruleset
# TODO: host_extra_conf
# TODO: _convert_host_ruleset
# TODO: host_extra_conf_merged


def test_all_matching_hosts(monkeypatch):
    import cmk_base.config as config

    monkeypatch.setattr(config, "distributed_wato_site", "site1")
    monkeypatch.setattr(config, "all_hosts",
        ["host1|tag1|tag2", "host2|tag1", "host3|tag1|site:site2"])
    monkeypatch.setattr(config, "clusters", {})
    config.collect_hosttags()

    assert config.all_matching_hosts(["tag1"], config.ALL_HOSTS, with_foreign_hosts=False) == \
            set(["host1", "host2"])

    assert config.all_matching_hosts(["tag2"], config.ALL_HOSTS, with_foreign_hosts=False) == \
            set(["host1"])

    assert config.all_matching_hosts(["!tag2"], config.ALL_HOSTS, with_foreign_hosts=False) == \
            set(["host2"])

    assert config.all_matching_hosts(["!tag2"], config.ALL_HOSTS, with_foreign_hosts=True) == \
            set(["host2", "host3"])

    assert config.all_matching_hosts(["tag1"], [], with_foreign_hosts=True) == \
            set([])

    assert config.all_matching_hosts(["tag1"], ["host1"], with_foreign_hosts=True) == \
            set(["host1"])

    assert config.all_matching_hosts(["!tag1"], ["host1"], with_foreign_hosts=False) == \
            set([])

    assert config.all_matching_hosts(["tag1"], ["~h"], with_foreign_hosts=False) == \
            set(["host1", "host2"])

    assert config.all_matching_hosts(["tag1"], ["~.*2"], with_foreign_hosts=False) == \
            set(["host2"])

    assert config.all_matching_hosts(["tag1"], ["~.*2$"], with_foreign_hosts=False) == \
            set(["host2"])

    assert config.all_matching_hosts(["tag1"], ["~2"], with_foreign_hosts=False) == \
            set([])


def test_in_extraconf_hostlist():
    assert config.in_extraconf_hostlist(config.ALL_HOSTS, "host1") == True
    assert config.in_extraconf_hostlist([], "host1") == False

    assert config.in_extraconf_hostlist(["host2", "host1"], "host1") == True
    assert config.in_extraconf_hostlist(["host1", "host2"], "host1") == True

    assert config.in_extraconf_hostlist(["host1"], "host1") == True
    assert config.in_extraconf_hostlist(["!host1", "host1", "!host1"], "host1") == False
    assert config.in_extraconf_hostlist(["!host1"], "host1") == False
    assert config.in_extraconf_hostlist(["!host2"], "host1") == False
    assert config.in_extraconf_hostlist(["host1", "!host2"], "host1") == True
    assert config.in_extraconf_hostlist(["!host2", "host1"], "host1") == True
    assert config.in_extraconf_hostlist(["~h"], "host1") == True
    assert config.in_extraconf_hostlist(["~h"], "host1") == True
    assert config.in_extraconf_hostlist(["~h$"], "host1") == False
    assert config.in_extraconf_hostlist(["~1"], "host1") == False
    assert config.in_extraconf_hostlist(["~.*1"], "host1") == True
    assert config.in_extraconf_hostlist(["~.*1$"], "host1") == True


# TODO: in_binary_hostlist


def test_parse_host_rule():
    options = {'description': u'Put all hosts into the contact group "all"'}
    entry = ( 'all', [], config.ALL_HOSTS, options)
    assert config.parse_host_rule(entry) == ('all', [], config.ALL_HOSTS, options)


def test_parse_host_rule_without_tags():
    options = {'description': u'Put all hosts into the contact group "all"'}
    entry = ( 'all', config.ALL_HOSTS, options)
    assert config.parse_host_rule(entry) == ('all', [], config.ALL_HOSTS, options)


def test_parse_host_rule_invalid_length():
    options = {'description': u'Put all hosts into the contact group "all"'}
    entry = (None, None, 'all', config.ALL_HOSTS, options)
    with pytest.raises(MKGeneralException):
        assert config.parse_host_rule(entry)


def test_get_rule_options_regular_rule():
    options = {'description': u'Put all hosts into the contact group "all"'}
    entry = ( 'all', [], config.ALL_HOSTS, options)
    assert config.get_rule_options(entry) == (entry[:-1], options)


def test_get_rule_options_empty_options():
    options = {}
    entry = ( 'all', [], config.ALL_HOSTS, options)
    assert config.get_rule_options(entry) == (entry[:-1], options)


def test_get_rule_options_missing_options():
    entry = ( 'all', [], config.ALL_HOSTS)
    assert config.get_rule_options(entry) == (entry, {})


def test_hosttags_match_taglist():
    assert config.hosttags_match_taglist(["tag1"], ["tag1"])
    assert config.hosttags_match_taglist(["tag1", "tag2"], ["tag1"])
    assert config.hosttags_match_taglist(["tag1", "tag2"], ["tag1", "tag2"])


def test_hosttags_match_taglist_not_matching():
    assert not config.hosttags_match_taglist(["tag1"], ["tag2"])
    assert not config.hosttags_match_taglist(["tag", "tag1", "tag22"], ["tag2"])
    assert not config.hosttags_match_taglist(["tag1", "tag2"], ["tag2", "tag3"])


def test_hosttags_match_taglist_negate():
    assert not config.hosttags_match_taglist(["tag1", "tag2"], ["tag1", "!tag2"])
    assert config.hosttags_match_taglist(["tag1"], ["tag1", "!tag2"])

    assert not config.hosttags_match_taglist(["tag1", "tag2"], ["!tag2+"])


def test_hosttags_match_taglist_prefix():
    assert config.hosttags_match_taglist(["tag1", "tag2"], ["tag2+"])
    assert config.hosttags_match_taglist(["tag1", "tax2"], ["tag+"])
    assert not config.hosttags_match_taglist(["tag1", "tag2"], ["tag3+"])


def test_parse_negated():
    assert config._parse_negated("") == (False, "")
    assert config._parse_negated("!aaa") == (True, "aaa")
    assert config._parse_negated("aaa") == (False, "aaa")


# TODO: convert_pattern
# TODO: convert_pattern_list
# TODO: in_extraconf_servicelist
# TODO: in_servicematcher_list
