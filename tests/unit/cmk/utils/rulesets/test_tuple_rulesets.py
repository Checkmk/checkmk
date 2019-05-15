# pylint: disable=redefined-outer-name
import pytest  # type: ignore
from testlib.base import Scenario

import cmk_base.config as config
import cmk.utils.rulesets.tuple_rulesets as tuple_rulesets
from cmk.utils.exceptions import MKGeneralException

import cmk


@pytest.fixture(autouse=True)
def fake_version(monkeypatch):
    monkeypatch.setattr(cmk, "omd_version", lambda: "1.4.0i1.cee")


@pytest.fixture()
def ts(monkeypatch):
    ts = Scenario(site_id="site1")
    ts.add_host("host1", tags={"agent": "no-agent", "criticality": "test"})
    ts.add_host("host2", tags={"agent": "no-agent"})
    ts.add_host("host3", tags={"agent": "no-agent", "site": "site2"})
    ts.apply(monkeypatch)
    return ts


def test_service_extra_conf(ts):
    ruleset = [
        ("1", [], tuple_rulesets.ALL_HOSTS, tuple_rulesets.ALL_SERVICES, {}),
        ("2", [], tuple_rulesets.ALL_HOSTS, tuple_rulesets.ALL_SERVICES,
         {}),  # Duplicate test to detect caching issues
        ("3", ["no-agent"], tuple_rulesets.ALL_HOSTS, tuple_rulesets.ALL_SERVICES, {}),
        ("4", ["test"], tuple_rulesets.ALL_HOSTS, tuple_rulesets.ALL_SERVICES, {}),
        ("5", ["tag3"], tuple_rulesets.ALL_HOSTS, tuple_rulesets.ALL_SERVICES, {}),
        ("6", ["tag3"], ["host1"], tuple_rulesets.ALL_SERVICES, {}),
        ("7", [], ["host1"], tuple_rulesets.ALL_SERVICES, {}),
        ("8", [], ["host1"], ["service1$"], {}),
        ("9", [], ["host1"], ["ser$"], {}),
        ("10", [], ["host1"], ["^serv$"], {}),
        ("11", [], ["~host"] + tuple_rulesets.ALL_HOSTS, tuple_rulesets.ALL_SERVICES, {}),
        ("12", [], ["!host2"] + tuple_rulesets.ALL_HOSTS, tuple_rulesets.ALL_SERVICES, {}),
    ]

    assert ts.config_cache.service_extra_conf("host1", "service1", ruleset) == \
            [ "1", "2", "3", "4", "7", "8", "11", "12" ]

    assert ts.config_cache.service_extra_conf("host1", "serv", ruleset) == \
            [ "1", "2", "3", "4", "7", "10", "11", "12" ]

    assert ts.config_cache.service_extra_conf("host2", "service1", ruleset) == \
            [ "1", "2", "3", "11" ]


@pytest.fixture(scope="function")
def host_ruleset():
    return [
        ({
            "1": True
        }, [], tuple_rulesets.ALL_HOSTS, {}),
        ({
            "2": True
        }, ["no-agent"], tuple_rulesets.ALL_HOSTS, {}),
        ({
            "3": True
        }, ["test"], tuple_rulesets.ALL_HOSTS, {}),
        ({
            "4": True
        }, ["tag3"], tuple_rulesets.ALL_HOSTS, {}),
        ({
            "5": True
        }, ["no-agent"], ["host1"], {}),
        ({
            "6": True
        }, ["tag3"], ["host1"], {}),
        ({
            "7": True
        }, [], ["host1"], {}),
        ({
            "8": True
        }, [], ["~host"] + tuple_rulesets.ALL_HOSTS, {}),
        ({
            "9": True
        }, [], ["!host2"] + tuple_rulesets.ALL_HOSTS, {}),
    ]


def test_host_extra_conf(ts, host_ruleset):
    assert ts.config_cache.host_extra_conf("host1", host_ruleset) == \
            [{"1": True},
             {"2": True},
             {"3": True},
             {"5": True},
             {"7": True},
             {"8": True},
             {"9": True}]


    assert ts.config_cache.host_extra_conf("host2", host_ruleset) == \
            [{"1": True},
             {"2": True},
             {"8": True}]


def test_host_extra_conf_merged(ts, host_ruleset):
    assert ts.config_cache.host_extra_conf_merged("host1", host_ruleset) == \
            {"1": True,
             "2": True,
             "3": True,
             "5": True,
             "7": True,
             "8": True,
             "9": True}


    assert ts.config_cache.host_extra_conf_merged("host2", host_ruleset) == \
            {"1": True,
             "2": True,
             "8": True}


@pytest.mark.parametrize(
    "parameters",
    [
        # ruleset, outcome host1, outcome host2
        [[], False, False],
        [[(config.NEGATE, [], tuple_rulesets.ALL_HOSTS, tuple_rulesets.ALL_SERVICES, {})], False,
         False],
        [[([], tuple_rulesets.ALL_HOSTS, tuple_rulesets.ALL_SERVICES, {})], True, True],
        [[([], ["!host1"] + tuple_rulesets.ALL_HOSTS, tuple_rulesets.ALL_SERVICES, {})], False, True
        ],
        [[([], ["!host1", "!host2"] + tuple_rulesets.ALL_HOSTS, tuple_rulesets.ALL_SERVICES, {})],
         False, False],
        [[(["test"], tuple_rulesets.ALL_HOSTS, tuple_rulesets.ALL_SERVICES, {})], True, False],
        [[(["test"], ["!host1"] + tuple_rulesets.ALL_HOSTS, tuple_rulesets.ALL_SERVICES, {})],
         False, False],
        [[([], ["!host1"] + tuple_rulesets.ALL_HOSTS, tuple_rulesets.ALL_SERVICES, {})], False, True
        ],
        [[(config.NEGATE, [], ["!host1"] + tuple_rulesets.ALL_HOSTS, tuple_rulesets.ALL_SERVICES,
           {})], False, False],
        [[(config.NEGATE, ["test"], ["!host1"] + tuple_rulesets.ALL_HOSTS,
           tuple_rulesets.ALL_SERVICES, {})], False, False],
        [[([], tuple_rulesets.ALL_HOSTS, ["serv"], {})], True, True],
        [[(config.NEGATE, [], tuple_rulesets.ALL_HOSTS, ["serv"], {})], False, False],
        [[(config.NEGATE, [], tuple_rulesets.ALL_HOSTS, ["service1"], {})], False, False],
        # Dual rule test, first rule matches host1 - negates -> False
        #                 second rule matches host2 -> True
        [[(config.NEGATE, [], tuple_rulesets.ALL_HOSTS, ["service1"], {}),
          ([], tuple_rulesets.ALL_HOSTS, tuple_rulesets.ALL_SERVICES, {})], False, True]
    ])
def test_in_boolean_serviceconf_list(ts, parameters):
    ruleset, outcome_host1, outcome_host2 = parameters

    assert ts.config_cache.in_boolean_serviceconf_list("host1", "service1",
                                                       ruleset) == outcome_host1
    assert ts.config_cache.in_boolean_serviceconf_list("host2", "service2",
                                                       ruleset) == outcome_host2


def test_all_matching_hosts(ts):
    config_cache = ts.config_cache
    assert config_cache.ruleset_matcher.ruleset_optimizer._all_matching_hosts(["no-agent"], tuple_rulesets.ALL_HOSTS, with_foreign_hosts=False) == \
            set(["host1", "host2"])

    assert config_cache.ruleset_matcher.ruleset_optimizer._all_matching_hosts(["test"], tuple_rulesets.ALL_HOSTS, with_foreign_hosts=False) == \
            set(["host1"])

    assert config_cache.ruleset_matcher.ruleset_optimizer._all_matching_hosts(["!test"], tuple_rulesets.ALL_HOSTS, with_foreign_hosts=False) == \
            set(["host2"])

    assert config_cache.ruleset_matcher.ruleset_optimizer._all_matching_hosts(["!test"], tuple_rulesets.ALL_HOSTS, with_foreign_hosts=True) == \
            set(["host2", "host3"])

    assert config_cache.ruleset_matcher.ruleset_optimizer._all_matching_hosts(["no-agent"], [], with_foreign_hosts=True) == \
            set([])

    assert config_cache.ruleset_matcher.ruleset_optimizer._all_matching_hosts(["no-agent"], ["host1"], with_foreign_hosts=True) == \
            set(["host1"])

    assert config_cache.ruleset_matcher.ruleset_optimizer._all_matching_hosts(["!no-agent"], ["host1"], with_foreign_hosts=False) == \
            set([])

    assert config_cache.ruleset_matcher.ruleset_optimizer._all_matching_hosts(["no-agent"], ["~h"], with_foreign_hosts=False) == \
            set(["host1", "host2"])

    assert config_cache.ruleset_matcher.ruleset_optimizer._all_matching_hosts(["no-agent"], ["~.*2"], with_foreign_hosts=False) == \
            set(["host2"])

    assert config_cache.ruleset_matcher.ruleset_optimizer._all_matching_hosts(["no-agent"], ["~.*2$"], with_foreign_hosts=False) == \
            set(["host2"])

    assert config_cache.ruleset_matcher.ruleset_optimizer._all_matching_hosts(["no-agent"], ["~2"], with_foreign_hosts=False) == \
            set([])


def test_in_extraconf_hostlist():
    assert config.in_extraconf_hostlist(tuple_rulesets.ALL_HOSTS, "host1") is True
    assert config.in_extraconf_hostlist([], "host1") is False

    assert config.in_extraconf_hostlist(["host2", "host1"], "host1") is True
    assert config.in_extraconf_hostlist(["host1", "host2"], "host1") is True

    assert config.in_extraconf_hostlist(["host1"], "host1") is True
    assert config.in_extraconf_hostlist(["!host1", "host1", "!host1"], "host1") is False
    assert config.in_extraconf_hostlist(["!host1"], "host1") is False
    assert config.in_extraconf_hostlist(["!host2"], "host1") is False
    assert config.in_extraconf_hostlist(["host1", "!host2"], "host1") is True
    assert config.in_extraconf_hostlist(["!host2", "host1"], "host1") is True
    assert config.in_extraconf_hostlist(["~h"], "host1") is True
    assert config.in_extraconf_hostlist(["~h"], "host1") is True
    assert config.in_extraconf_hostlist(["~h$"], "host1") is False
    assert config.in_extraconf_hostlist(["~1"], "host1") is False
    assert config.in_extraconf_hostlist(["~.*1"], "host1") is True
    assert config.in_extraconf_hostlist(["~.*1$"], "host1") is True


# TODO: in_binary_hostlist


def test_parse_host_rule():
    config_cache = config.get_config_cache()
    config_cache.initialize()
    entry = ('all', [], tuple_rulesets.ALL_HOSTS)
    assert config_cache.ruleset_matcher.ruleset_optimizer.parse_host_rule(
        entry, is_binary=False) == ('all', [], tuple_rulesets.ALL_HOSTS)


def test_parse_host_rule_without_tags():
    config_cache = config.get_config_cache()
    config_cache.initialize()
    entry = ('all', tuple_rulesets.ALL_HOSTS)
    assert config_cache.ruleset_matcher.ruleset_optimizer.parse_host_rule(
        entry, is_binary=False) == ('all', [], tuple_rulesets.ALL_HOSTS)


def test_parse_host_rule_invalid_length():
    config_cache = config.get_config_cache()
    config_cache.initialize()
    entry = (None, None, 'all', tuple_rulesets.ALL_HOSTS)
    with pytest.raises(MKGeneralException):
        assert config_cache.ruleset_matcher.ruleset_optimizer.parse_host_rule(
            entry, is_binary=False)


def test_get_rule_options_regular_rule():
    options = {'description': u'Put all hosts into the contact group "all"'}
    entry = ('all', [], tuple_rulesets.ALL_HOSTS, options)
    assert tuple_rulesets.get_rule_options(entry) == (entry[:-1], options)


def test_get_rule_options_empty_options():
    options = {}
    entry = ('all', [], tuple_rulesets.ALL_HOSTS, options)
    assert tuple_rulesets.get_rule_options(entry) == (entry[:-1], options)


def test_get_rule_options_missing_options():
    entry = ('all', [], tuple_rulesets.ALL_HOSTS)
    assert tuple_rulesets.get_rule_options(entry) == (entry, {})


def test_hosttags_match_taglist():
    assert tuple_rulesets.hosttags_match_taglist(["no-agent"], ["no-agent"])
    assert tuple_rulesets.hosttags_match_taglist(["no-agent", "test"], ["no-agent"])
    assert tuple_rulesets.hosttags_match_taglist(["no-agent", "test"], ["no-agent", "test"])


def test_hosttags_match_taglist_not_matching():
    assert not tuple_rulesets.hosttags_match_taglist(["no-agent"], ["test"])
    assert not tuple_rulesets.hosttags_match_taglist(["tag", "no-agent", "test2"], ["test"])
    assert not tuple_rulesets.hosttags_match_taglist(["no-agent", "test"], ["test", "tag3"])


def test_hosttags_match_taglist_negate():
    assert not tuple_rulesets.hosttags_match_taglist(["no-agent", "test"], ["no-agent", "!test"])
    assert tuple_rulesets.hosttags_match_taglist(["no-agent"], ["no-agent", "!test"])


# TODO: convert_pattern
# TODO: convert_pattern_list
# TODO: in_extraconf_servicelist
# TODO: in_servicematcher_list
