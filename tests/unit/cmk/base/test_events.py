#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from typing import Final

import pytest
from pytest import MonkeyPatch

import cmk.base.events
from cmk.base.events import (
    _update_enriched_context_from_notify_host_file,
    add_to_event_context,
    apply_matchers,
    CoreTimeperiodsActive,
    event_match_checktype,
    event_match_contactgroups,
    event_match_contacts,
    event_match_exclude_hosts,
    event_match_exclude_servicegroups_fixed,
    event_match_exclude_servicegroups_regex,
    event_match_exclude_services,
    event_match_folder,
    event_match_hostgroups,
    event_match_hostlabels,
    event_match_hosts,
    event_match_hosttags,
    event_match_plugin_output,
    event_match_servicegroups_fixed,
    event_match_servicegroups_regex,
    event_match_servicelabels,
    event_match_servicelevel,
    event_match_services,
    event_match_site,
    event_match_timeperiod,
    raw_context_from_string,
)
from cmk.ccc.hostaddress import HostAddress
from cmk.events.event_context import EnrichedEventContext, EventContext, HostName
from cmk.utils.http_proxy_config import (
    EnvironmentProxyConfig,
    HTTPProxySpec,
    make_http_proxy_getter,
    ProxyConfigSpec,
)
from cmk.utils.notify import NotificationHostConfig
from cmk.utils.notify_types import (
    EventRule,
    NotificationParameterID,
    NotificationRuleID,
    NotifyPluginParamsDict,
)
from cmk.utils.rulesets.ruleset_matcher import TagConditionNE
from cmk.utils.tags import TagGroupID, TagID
from cmk.utils.timeperiod import builtin_timeperiods

HTTP_PROXY: Final = EnvironmentProxyConfig()


@pytest.mark.parametrize(
    "context,expected",
    [
        ("", {}),
        ("TEST=test", {"TEST": "test"}),
        (
            "SERVICEOUTPUT=with_light_vertical_bar_\u2758",
            {"SERVICEOUTPUT": "with_light_vertical_bar_|"},
        ),
        (
            "LONGSERVICEOUTPUT=with_light_vertical_bar_\u2758",
            {"LONGSERVICEOUTPUT": "with_light_vertical_bar_|"},
        ),
        (
            "NOT_INFOTEXT=with_light_vertical_bar_\u2758",
            {"NOT_INFOTEXT": "with_light_vertical_bar_\u2758"},
        ),
    ],
)
def test_raw_context_from_string(context: str, expected: EventContext) -> None:
    assert raw_context_from_string(context) == expected


def test_add_to_event_context_param_overrides_context() -> None:
    context = {"FOO": "bar", "BAZ": "old"}
    add_to_event_context(context, "BAZ", "new", lambda *args, **kw: HTTP_PROXY)
    assert context == {"FOO": "bar", "BAZ": "new"}


def test_add_to_event_context_prefix_is_prepended() -> None:
    context: EventContext = {}
    add_to_event_context(context, "FOO", "bar", lambda *args, **kw: HTTP_PROXY)
    add_to_event_context(context, "BAZ", "boo", lambda *args, **kw: HTTP_PROXY)
    add_to_event_context(context, "AAA", {"BBB": "CCC"}, lambda *args, **kw: HTTP_PROXY)
    assert context == {"FOO": "bar", "BAZ": "boo", "AAA_BBB": "CCC"}


@pytest.mark.parametrize(
    "param, expected",
    [
        # basic types ----------------------------------------------------------
        pytest.param(
            "blah",
            {"PARAMETER": "blah"},
            id="string",
        ),
        pytest.param(
            12345,
            {"PARAMETER": "12345"},
            id="int",
        ),
        pytest.param(
            1234.5,
            {"PARAMETER": "1234.5"},
            id="float",
        ),
        pytest.param(
            None,
            {"PARAMETER": ""},
            id="None",
        ),
        pytest.param(
            True,
            {"PARAMETER": "True"},
            id="True",
        ),
        pytest.param(
            False,
            {"PARAMETER": "False"},
            id="False",
        ),
        # lists ----------------------------------------------------------------
        pytest.param(
            [],
            {"PARAMETERS": ""},
            id="empty list",
        ),
        pytest.param(
            ["blah"],
            {
                "PARAMETERS": "blah",
                "PARAMETER_1": "blah",
            },
            id="singleton list with string",
        ),
        pytest.param(
            ["foo", "bar", "baz"],
            {
                "PARAMETERS": "foo bar baz",
                "PARAMETER_1": "foo",
                "PARAMETER_2": "bar",
                "PARAMETER_3": "baz",
            },
            id="general list with strings",
        ),
        pytest.param(
            [42, {"caller": "admin", "urgency": "low"}],
            {
                "PARAMETER_1": "42",
                "PARAMETER_2_CALLER": "admin",
                "PARAMETER_2_URGENCY": "low",
            },
            id="list with non-string elements",
        ),
        # tuples ---------------------------------------------------------------
        pytest.param(
            (),
            {"PARAMETER": ""},
            id="empty tuple",
        ),
        pytest.param(
            ("blah",),
            {
                "PARAMETER": "blah",
                "PARAMETER_1": "blah",
            },
            id="singleton tuple with string",
        ),
        pytest.param(
            ("foo", "bar", "baz"),
            {
                "PARAMETER": "foo\tbar\tbaz",
                "PARAMETER_1": "foo",
                "PARAMETER_2": "bar",
                "PARAMETER_3": "baz",
            },
            id="general tuple with strings",
        ),
        pytest.param(
            (42, {"caller": "admin", "urgency": "low"}),
            {
                "PARAMETER_1": "42",
                "PARAMETER_2_CALLER": "admin",
                "PARAMETER_2_URGENCY": "low",
            },
            id="tuple with non-string elements",
        ),
        # dicts ----------------------------------------------------------------
        pytest.param(
            {},
            {},
            id="empty dict",
        ),
        pytest.param(
            {"key": "value"},
            {"PARAMETER_KEY": "value"},
            id="dict with a single string/string entry",
        ),
        pytest.param(
            {
                "key": 42,
                "foo": True,
                "ernie": "Bert",
                "bar": {
                    "baz": {
                        "blubb": 2.5,
                        "smarthosts": ["127.0.0.1", "127.0.0.2", "127.0.0.3"],
                        "nephews": ("Huey", "Dewey", "Louie"),
                    },
                    "ding": "dong",
                },
            },
            {
                "PARAMETER_KEY": "42",
                "PARAMETER_FOO": "True",
                "PARAMETER_ERNIE": "Bert",
                "PARAMETER_BAR_BAZ_BLUBB": "2.5",
                "PARAMETER_BAR_BAZ_SMARTHOSTSS": "127.0.0.1 127.0.0.2 127.0.0.3",
                "PARAMETER_BAR_BAZ_SMARTHOSTS_1": "127.0.0.1",
                "PARAMETER_BAR_BAZ_SMARTHOSTS_2": "127.0.0.2",
                "PARAMETER_BAR_BAZ_SMARTHOSTS_3": "127.0.0.3",
                "PARAMETER_BAR_BAZ_NEPHEWS": "Huey\tDewey\tLouie",
                "PARAMETER_BAR_BAZ_NEPHEWS_1": "Huey",
                "PARAMETER_BAR_BAZ_NEPHEWS_2": "Dewey",
                "PARAMETER_BAR_BAZ_NEPHEWS_3": "Louie",
                "PARAMETER_BAR_DING": "dong",
            },
            id="dict with multiple string/mixed entries",
        ),
    ],
)
def test_add_to_event_context(param: object, expected: EventContext) -> None:
    context: EventContext = {}
    add_to_event_context(context, "PARAMETER", param, make_http_proxy_getter({}))
    assert context == expected


@pytest.mark.parametrize(
    "enriched_context, config, expected",
    [
        pytest.param(
            {
                "CONTACTS": "cmkadmin",
                "NOTIFICATIONTYPE": "PROBLEM",
                "HOSTNAME": "heute",
                "SERVICEDESC": "Interface 1",
                "WHAT": "SERVICE",
            },
            NotificationHostConfig(
                host_labels={
                    "cmk/check_mk_server": "yes",
                    "cmk/docker_object": "node",
                    "cmk/os_family": "linux",
                    "rule": "label",
                    "explicit": "label",
                    "cmk/site": "heute",
                },
                service_labels={"Interface 1": {"dicovered": "label", "rule": "label"}},
                tags={
                    TagGroupID("criticality"): TagID("prod"),
                },
            ),
            {
                "CONTACTS": "cmkadmin",
                "NOTIFICATIONTYPE": "PROBLEM",
                "HOSTNAME": "heute",
                "WHAT": "SERVICE",
                "SERVICEDESC": "Interface 1",
                "HOSTLABEL_cmk/check_mk_server": "yes",
                "HOSTLABEL_cmk/docker_object": "node",
                "HOSTLABEL_cmk/os_family": "linux",
                "HOSTLABEL_rule": "label",
                "HOSTLABEL_explicit": "label",
                "HOSTLABEL_cmk/site": "heute",
                "HOSTTAG_criticality": "prod",
                "SERVICELABEL_dicovered": "label",
                "SERVICELABEL_rule": "label",
            },
            id="service notification",
        ),
        pytest.param(
            {
                "CONTACTS": "cmkadmin",
                "NOTIFICATIONTYPE": "PROBLEM",
                "HOSTNAME": "heute",
                "WHAT": "HOST",
            },
            NotificationHostConfig(
                host_labels={
                    "cmk/check_mk_server": "yes",
                    "cmk/docker_object": "node",
                    "cmk/os_family": "linux",
                    "rule": "label",
                    "explicit": "label",
                    "cmk/site": "heute",
                },
                service_labels={"Interface 1": {"dicovered": "label", "rule": "label"}},
                tags={
                    TagGroupID("networking"): TagID("wan"),
                    TagGroupID("criticality"): TagID("critical"),
                },
            ),
            {
                "CONTACTS": "cmkadmin",
                "NOTIFICATIONTYPE": "PROBLEM",
                "HOSTNAME": "heute",
                "WHAT": "HOST",
                "HOSTCHILDREN": "",
                "HOSTLABEL_cmk/check_mk_server": "yes",
                "HOSTLABEL_cmk/docker_object": "node",
                "HOSTLABEL_cmk/os_family": "linux",
                "HOSTLABEL_rule": "label",
                "HOSTLABEL_explicit": "label",
                "HOSTLABEL_cmk/site": "heute",
                "HOSTTAG_networking": "wan",
                "HOSTTAG_criticality": "critical",
            },
            id="host notification",
        ),
        pytest.param(
            {
                "CONTACTS": "cmkadmin",
                "NOTIFICATIONTYPE": "PROBLEM",
                "HOSTNAME": "switch1",
                "WHAT": "HOST",
            },
            NotificationHostConfig(
                host_labels={},
                service_labels={},
                tags={},
                descendants=(
                    HostAddress("srv1"),
                    HostAddress("srv2"),
                    HostAddress("srv1.db"),
                ),
            ),
            {
                "CONTACTS": "cmkadmin",
                "NOTIFICATIONTYPE": "PROBLEM",
                "HOSTNAME": "switch1",
                "WHAT": "HOST",
                "HOSTCHILDREN": "srv1,srv2,srv1.db",
            },
            id="host notification with descendants",
        ),
    ],
)
def test_update_enriched_context_from_host_file(
    enriched_context: EnrichedEventContext,
    config: NotificationHostConfig,
    expected: EventContext,
    monkeypatch: MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        cmk.base.events,
        "read_notify_host_file",
        lambda *args, **kw: config,
    )
    _update_enriched_context_from_notify_host_file(enriched_context)
    assert enriched_context == expected


@pytest.mark.parametrize(
    "enriched_context, host_config, event_rule, expected",
    [
        pytest.param(
            {
                "HOSTNAME": "heute",
                "HOSTTAG_criticality": "prod",
            },
            NotificationHostConfig(
                host_labels={},
                service_labels={},
                tags={
                    TagGroupID("criticality"): TagID("prod"),
                },
            ),
            EventRule(
                rule_id=NotificationRuleID("1"),
                allow_disable=False,
                contact_all=False,
                contact_all_with_email=False,
                contact_object=False,
                description="Test rule",
                disabled=False,
                notify_plugin=("mail", NotificationParameterID("parameter_id")),
                match_hosttags={TagGroupID("bla"): TagID("bli")},
            ),
            "The host's tags {'criticality': 'prod'} do not match the required tags {'bla': 'bli'}",
            id="Does not match",
        ),
        pytest.param(
            {
                "HOSTNAME": "heute",
                "HOSTTAG_criticality": "prod",
                "HOSTTAG_hurz": "blub",
                "HOSTTAG_hans": "wurst",
            },
            NotificationHostConfig(
                host_labels={},
                service_labels={},
                tags={
                    TagGroupID("criticality"): TagID("prod"),
                    TagGroupID("hurz"): TagID("blub"),
                    TagGroupID("hans"): TagID("wurst"),
                },
            ),
            EventRule(
                rule_id=NotificationRuleID("2"),
                allow_disable=False,
                contact_all=False,
                contact_all_with_email=False,
                contact_object=False,
                description="Test rule",
                disabled=False,
                notify_plugin=("mail", NotificationParameterID("parameter_id")),
                match_hosttags={
                    TagGroupID("criticality"): TagID("prod"),
                    TagGroupID("hurz"): TagID("blub"),
                    TagGroupID("hans"): TagID("wurst"),
                },
            ),
            None,
            id="Matches",
        ),
        pytest.param(
            {
                "HOSTNAME": "heute",
                "HOSTTAG_criticality": "prod",
                "HOSTTAG_hurz": "blub",
                "HOSTTAG_hans": "wurst",
            },
            NotificationHostConfig(
                host_labels={},
                service_labels={},
                tags={
                    TagGroupID("criticality"): TagID("prod"),
                    TagGroupID("hurz"): TagID("blub"),
                    TagGroupID("hans"): TagID("wurst"),
                },
            ),
            EventRule(
                rule_id=NotificationRuleID("2"),
                allow_disable=False,
                contact_all=False,
                contact_all_with_email=False,
                contact_object=False,
                description="Test rule",
                disabled=False,
                notify_plugin=("mail", NotificationParameterID("parameter_id")),
                match_hosttags={
                    TagGroupID("criticality"): TagConditionNE({"$ne": TagID("prod")}),
                    TagGroupID("hurz"): TagID("blub"),
                    TagGroupID("hans"): TagID("wurst"),
                },
            ),
            "The host's tags {'criticality': 'prod', 'hurz': 'blub', 'hans': "
            "'wurst'} do not match the required tags {'criticality': {'$ne': "
            "'prod'}, 'hurz': 'blub', 'hans': 'wurst'}",
            id="Does not match because of negate",
        ),
    ],
)
def test_match_host_tags(
    enriched_context: EnrichedEventContext,
    host_config: NotificationHostConfig,
    event_rule: EventRule,
    expected: str | None,
    monkeypatch: MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        cmk.base.events,
        "read_notify_host_file",
        lambda *args, **kw: host_config,
    )
    assert (
        event_match_hosttags(
            rule=event_rule,
            context=enriched_context,
            _analyse=False,
            _all_timeperiods={},
        )
        == expected
    )


@pytest.mark.parametrize(
    "params, expected",
    [
        pytest.param(
            {"proxy_url": ("cmk_postprocessed", "no_proxy", "")},
            {
                "PARAMETER_PROXY_URL": "NO_PROXY",
            },
            id="No proxy",
        ),
        pytest.param(
            {"proxy_url": ("cmk_postprocessed", "stored_proxy", "proxy_id")},
            {
                "PARAMETER_PROXY_URL": "http://stored_url:8080",
            },
            id="Stored proxy",
        ),
        pytest.param(
            {"proxy_url": ("cmk_postprocessed", "environment_proxy", "")},
            {
                "PARAMETER_PROXY_URL": "FROM_ENVIRONMENT",
            },
            id="Environment proxy",
        ),
        pytest.param(
            {"proxy_url": ("cmk_postprocessed", "explicit_proxy", "http://www.myproxy.com")},
            {
                "PARAMETER_PROXY_URL": "http://www.myproxy.com",
            },
            id="Explicit proxy",
        ),
    ],
)
def test_add_to_event_context_proxy(
    params: NotifyPluginParamsDict,
    expected: Mapping[str, str],
) -> None:
    context = dict[str, str]()
    add_to_event_context(
        context,
        "PARAMETER",
        params,
        make_http_proxy_getter(
            {
                "proxy_id": HTTPProxySpec(
                    ident="proxy_id",
                    title="proxy_id",
                    proxy_config=ProxyConfigSpec(
                        scheme="http",
                        proxy_server_name="stored_url",
                        port=8080,
                    ),
                )
            },
        ),
    )
    assert context == expected


@pytest.fixture
def basic_event_rule() -> EventRule:
    return EventRule(
        rule_id=NotificationRuleID("1"),
        allow_disable=False,
        contact_all=False,
        contact_all_with_email=False,
        contact_object=False,
        description="Test rule",
        disabled=False,
        notify_plugin=("mail", NotificationParameterID("parameter_id")),
    )


def test_apply_matchers_returns_none_on_empty_matchers(basic_event_rule: EventRule) -> None:
    assert (
        apply_matchers([], basic_event_rule, context={}, analyse=False, all_timeperiods={}) is None
    )


def test_apply_matchers_returns_none_when_all_pass(basic_event_rule: EventRule) -> None:
    assert (
        apply_matchers(
            [lambda *args, **kw: None, lambda *args, **kw: None],
            basic_event_rule,
            context={},
            analyse=False,
            all_timeperiods={},
        )
        is None
    )


def test_apply_matchers_returns_first_non_none_result(basic_event_rule: EventRule) -> None:
    result = apply_matchers(
        [
            lambda *args, **kw: None,
            lambda *args, **kw: "reason one",
            lambda *args, **kw: "reason two",
        ],
        basic_event_rule,
        context={},
        analyse=False,
        all_timeperiods={},
    )
    assert result == "reason one"


def test_apply_matchers_stops_at_first_failure(basic_event_rule: EventRule) -> None:
    called: list[str] = []

    def first_matcher(
        rule: EventRule, context: EventContext, analyse: bool, all_timeperiods: object
    ) -> str:
        called.append("first")
        return "failed"

    def second_matcher(
        rule: EventRule, context: EventContext, analyse: bool, all_timeperiods: object
    ) -> None:
        called.append("second")

    apply_matchers(
        [first_matcher, second_matcher],
        basic_event_rule,
        context={},
        analyse=False,
        all_timeperiods={},
    )
    assert called == ["first"]


def test_apply_matchers_passes_arguments_to_matchers(basic_event_rule: EventRule) -> None:
    received: list[object] = []
    ctx: EventContext = {"HOSTNAME": HostName("myhost")}
    periods = builtin_timeperiods()

    def capturing_matcher(
        rule: EventRule, context: EventContext, analyse: bool, all_timeperiods: object
    ) -> None:
        received.extend([rule, context, analyse, all_timeperiods])

    apply_matchers(
        [capturing_matcher],
        basic_event_rule,
        context=ctx,
        analyse=True,
        all_timeperiods=periods,
    )
    assert received == [basic_event_rule, ctx, True, periods]


def test_apply_matchers_catches_errors(basic_event_rule: EventRule) -> None:
    def raise_error() -> None:
        raise ValueError("This is a test")

    why_not = apply_matchers(
        [
            lambda *args, **kw: raise_error(),
        ],
        basic_event_rule,
        context={},
        analyse=False,
        all_timeperiods={},
    )

    assert isinstance(why_not, str)
    assert "ValueError: This is a test" in why_not


# =============================================================================
# Individual event_match_* function tests
# =============================================================================


def _make_rule() -> EventRule:
    return {
        "rule_id": NotificationRuleID("1"),
        "allow_disable": False,
        "contact_all": False,
        "contact_all_with_email": False,
        "contact_object": False,
        "description": "Test rule",
        "disabled": False,
        "notify_plugin": ("mail", NotificationParameterID("parameter_id")),
    }


# -- event_match_site ----------------------------------------------------------


@pytest.mark.parametrize(
    "rule, context, expected_none",
    [
        pytest.param(_make_rule(), {"OMD_SITE": "site_a"}, True, id="no condition"),
        pytest.param(
            _make_rule() | {"match_site": ["site_a", "site_b"]},
            {"OMD_SITE": "site_a"},
            True,
            id="site in allowed list",
        ),
        pytest.param(
            _make_rule() | {"match_site": ["site_a"]},
            {"OMD_SITE": "site_b"},
            False,
            id="site not in allowed list",
        ),
    ],
)
def test_event_match_site(rule: EventRule, context: EventContext, expected_none: bool) -> None:
    result = event_match_site(rule, context, False, {})
    assert (result is None) == expected_none


# -- event_match_folder --------------------------------------------------------


@pytest.mark.parametrize(
    "rule, context, expected_none",
    [
        pytest.param(_make_rule(), {"HOSTTAGS": "/wato/subfolder"}, True, id="no condition"),
        pytest.param(
            _make_rule() | {"match_folder": ""},
            {"HOSTTAGS": "/wato/subfolder"},
            True,
            id="root folder always matches",
        ),
        pytest.param(
            _make_rule() | {"match_folder": "subfolder"},
            {"HOSTTAGS": "/wato/subfolder"},
            True,
            id="host in exact folder",
        ),
        pytest.param(
            _make_rule() | {"match_folder": "subfolder"},
            {"HOSTTAGS": "/wato/subfolder/nested"},
            True,
            id="host in nested subfolder matches parent",
        ),
        pytest.param(
            _make_rule() | {"match_folder": "subfolder"},
            {"HOSTTAGS": "/wato/other"},
            False,
            id="host in different folder",
        ),
        pytest.param(
            _make_rule() | {"match_folder": "subfolder"},
            {"HOSTTAGS": "some_tag"},
            False,
            id="host not managed in Setup",
        ),
    ],
)
def test_event_match_folder(rule: EventRule, context: EventContext, expected_none: bool) -> None:
    result = event_match_folder(rule, context, False, {})
    assert (result is None) == expected_none


# -- event_match_hostgroups ----------------------------------------------------


@pytest.mark.parametrize(
    "rule, context, expected_none",
    [
        pytest.param(_make_rule(), {"HOSTGROUPNAMES": "web,db"}, True, id="no condition"),
        pytest.param(
            _make_rule() | {"match_hostgroups": ["web"]},
            {"HOSTGROUPNAMES": "web,db"},
            True,
            id="host in required group",
        ),
        pytest.param(
            _make_rule() | {"match_hostgroups": ["ops"]},
            {"HOSTGROUPNAMES": "web,db"},
            False,
            id="host not in required group",
        ),
        pytest.param(
            _make_rule() | {"match_hostgroups": ["web"]},
            {},
            False,
            id="no group info in context",
        ),
        pytest.param(
            _make_rule() | {"match_hostgroups": ["web"]},
            {"HOSTGROUPNAMES": ""},
            False,
            id="host in no group",
        ),
    ],
)
def test_event_match_hostgroups(
    rule: EventRule, context: EventContext, expected_none: bool
) -> None:
    result = event_match_hostgroups(rule, context, False, {})
    assert (result is None) == expected_none


# -- event_match_contacts ------------------------------------------------------


@pytest.mark.parametrize(
    "rule, context, expected_none",
    [
        pytest.param(_make_rule(), {"CONTACTS": "alice,bob"}, True, id="no condition"),
        pytest.param(
            _make_rule() | {"match_contacts": ["alice"]},
            {"CONTACTS": "alice,bob"},
            True,
            id="required contact present",
        ),
        pytest.param(
            _make_rule() | {"match_contacts": ["alice"]},
            {"CONTACTS": ""},
            False,
            id="object has no contacts",
        ),
        pytest.param(
            _make_rule() | {"match_contacts": ["charlie"]},
            {"CONTACTS": "alice,bob"},
            False,
            id="required contact absent",
        ),
    ],
)
def test_event_match_contacts(rule: EventRule, context: EventContext, expected_none: bool) -> None:
    result = event_match_contacts(rule, context, False, {})
    assert (result is None) == expected_none


# -- event_match_contactgroups -------------------------------------------------


@pytest.mark.parametrize(
    "rule, context, expected_none",
    [
        pytest.param(
            _make_rule(),
            {"WHAT": "HOST", "HOSTCONTACTGROUPNAMES": "ops"},
            True,
            id="no condition",
        ),
        pytest.param(
            _make_rule() | {"match_contactgroups": ["ops"]},
            {"WHAT": "HOST", "HOSTCONTACTGROUPNAMES": "ops,web"},
            True,
            id="host in required contact group",
        ),
        pytest.param(
            _make_rule() | {"match_contactgroups": ["ops"]},
            {"WHAT": "SERVICE", "SERVICECONTACTGROUPNAMES": "ops,web"},
            True,
            id="service in required contact group",
        ),
        pytest.param(
            _make_rule() | {"match_contactgroups": ["ops"]},
            {"WHAT": "HOST"},
            True,
            id="no group info returns None, not an error",
        ),
        pytest.param(
            _make_rule() | {"match_contactgroups": ["ops"]},
            {"WHAT": "HOST", "HOSTCONTACTGROUPNAMES": ""},
            False,
            id="host in no group",
        ),
        pytest.param(
            _make_rule() | {"match_contactgroups": ["ops"]},
            {"WHAT": "HOST", "HOSTCONTACTGROUPNAMES": "web,db"},
            False,
            id="host not in required contact group",
        ),
    ],
)
def test_event_match_contactgroups(
    rule: EventRule, context: EventContext, expected_none: bool
) -> None:
    result = event_match_contactgroups(rule, context, False, {})
    assert (result is None) == expected_none


# -- event_match_hosts ---------------------------------------------------------


@pytest.mark.parametrize(
    "rule, context, expected_none",
    [
        pytest.param(_make_rule(), {"HOSTNAME": "myhost"}, True, id="no condition"),
        pytest.param(
            _make_rule() | {"match_hosts": ["myhost", "otherhost"]},
            {"HOSTNAME": "myhost"},
            True,
            id="host in allowed list",
        ),
        pytest.param(
            _make_rule() | {"match_hosts": ["otherhost"]},
            {"HOSTNAME": "myhost"},
            False,
            id="host not in allowed list",
        ),
    ],
)
def test_event_match_hosts(rule: EventRule, context: EventContext, expected_none: bool) -> None:
    result = event_match_hosts(rule, context, False, {})
    assert (result is None) == expected_none


# -- event_match_exclude_hosts -------------------------------------------------


@pytest.mark.parametrize(
    "rule, context, expected_none",
    [
        pytest.param(_make_rule(), {"HOSTNAME": "myhost"}, True, id="no condition"),
        pytest.param(
            _make_rule() | {"match_exclude_hosts": ["otherhost"]},
            {"HOSTNAME": "myhost"},
            True,
            id="host not in excluded list",
        ),
        pytest.param(
            _make_rule() | {"match_exclude_hosts": ["myhost"]},
            {"HOSTNAME": "myhost"},
            False,
            id="host in excluded list",
        ),
    ],
)
def test_event_match_exclude_hosts(
    rule: EventRule, context: EventContext, expected_none: bool
) -> None:
    result = event_match_exclude_hosts(rule, context, False, {})
    assert (result is None) == expected_none


# -- event_match_services ------------------------------------------------------


@pytest.mark.parametrize(
    "rule, context, expected_none",
    [
        pytest.param(
            _make_rule(),
            {"WHAT": "SERVICE", "SERVICEDESC": "CPU load"},
            True,
            id="no condition",
        ),
        pytest.param(
            _make_rule() | {"match_services": ["CPU load"]},
            {"WHAT": "SERVICE", "SERVICEDESC": "CPU load"},
            True,
            id="service matches",
        ),
        pytest.param(
            _make_rule() | {"match_services": ["Memory"]},
            {"WHAT": "SERVICE", "SERVICEDESC": "CPU load"},
            False,
            id="service does not match",
        ),
        pytest.param(
            _make_rule() | {"match_services": ["CPU load"]},
            {"WHAT": "HOST", "SERVICEDESC": ""},
            False,
            id="host notification with service rule",
        ),
    ],
)
def test_event_match_services(rule: EventRule, context: EventContext, expected_none: bool) -> None:
    result = event_match_services(rule, context, False, {})
    assert (result is None) == expected_none


# -- event_match_exclude_services ----------------------------------------------


@pytest.mark.parametrize(
    "rule, context, expected_none",
    [
        pytest.param(
            _make_rule(),
            {"WHAT": "SERVICE", "SERVICEDESC": "CPU load"},
            True,
            id="no condition",
        ),
        pytest.param(
            _make_rule(),
            {"WHAT": "HOST"},
            True,
            id="host notification always passes",
        ),
        pytest.param(
            _make_rule() | {"match_exclude_services": ["CPU load"]},
            {"WHAT": "SERVICE", "SERVICEDESC": "CPU load"},
            False,
            id="service in excluded list",
        ),
        pytest.param(
            _make_rule() | {"match_exclude_services": ["Memory"]},
            {"WHAT": "SERVICE", "SERVICEDESC": "CPU load"},
            True,
            id="service not in excluded list",
        ),
    ],
)
def test_event_match_exclude_services(
    rule: EventRule, context: EventContext, expected_none: bool
) -> None:
    result = event_match_exclude_services(rule, context, False, {})
    assert (result is None) == expected_none


# -- event_match_plugin_output -------------------------------------------------


@pytest.mark.parametrize(
    "rule, context, expected_none",
    [
        pytest.param(
            _make_rule(),
            {"WHAT": "SERVICE", "SERVICEOUTPUT": "CRIT - high load"},
            True,
            id="no condition",
        ),
        pytest.param(
            _make_rule() | {"match_plugin_output": "high load"},
            {"WHAT": "SERVICE", "SERVICEOUTPUT": "CRIT - high load"},
            True,
            id="pattern matches service output",
        ),
        pytest.param(
            _make_rule() | {"match_plugin_output": "high load"},
            {"WHAT": "HOST", "HOSTOUTPUT": "CRIT - high load"},
            True,
            id="pattern matches host output",
        ),
        pytest.param(
            _make_rule() | {"match_plugin_output": "memory"},
            {"WHAT": "SERVICE", "SERVICEOUTPUT": "CRIT - high load"},
            False,
            id="pattern does not match",
        ),
    ],
)
def test_event_match_plugin_output(
    rule: EventRule, context: EventContext, expected_none: bool
) -> None:
    result = event_match_plugin_output(rule, context, False, {})
    assert (result is None) == expected_none


# -- event_match_checktype -----------------------------------------------------


@pytest.mark.parametrize(
    "rule, context, expected_none",
    [
        pytest.param(
            _make_rule(),
            {"WHAT": "SERVICE", "SERVICECHECKCOMMAND": "check_mk-cpu_loads"},
            True,
            id="no condition",
        ),
        pytest.param(
            _make_rule() | {"match_checktype": ["cpu_loads"]},
            {"WHAT": "HOST", "SERVICECHECKCOMMAND": ""},
            False,
            id="host notification with check type rule",
        ),
        pytest.param(
            _make_rule() | {"match_checktype": ["cpu_loads"]},
            {"WHAT": "SERVICE", "SERVICECHECKCOMMAND": "active_check-http"},
            False,
            id="not a check_mk service",
        ),
        pytest.param(
            _make_rule() | {"match_checktype": ["cpu_loads"]},
            {"WHAT": "SERVICE", "SERVICECHECKCOMMAND": "check_mk-cpu_loads"},
            True,
            id="plugin in allowed list",
        ),
        pytest.param(
            _make_rule() | {"match_checktype": ["memory"]},
            {"WHAT": "SERVICE", "SERVICECHECKCOMMAND": "check_mk-cpu_loads"},
            False,
            id="plugin not in allowed list",
        ),
    ],
)
def test_event_match_checktype(rule: EventRule, context: EventContext, expected_none: bool) -> None:
    result = event_match_checktype(rule, context, False, {})
    assert (result is None) == expected_none


# -- event_match_servicelevel --------------------------------------------------


@pytest.mark.parametrize(
    "rule, context, expected_none",
    [
        pytest.param(
            _make_rule(),
            {"WHAT": "SERVICE", "SVC_SL": "50"},
            True,
            id="no condition",
        ),
        pytest.param(
            _make_rule() | {"match_sl": (0, 100)},
            {"WHAT": "SERVICE", "SVC_SL": "50"},
            True,
            id="service level in range",
        ),
        pytest.param(
            _make_rule() | {"match_sl": (60, 100)},
            {"WHAT": "SERVICE", "SVC_SL": "50"},
            False,
            id="service level below range",
        ),
        pytest.param(
            _make_rule() | {"match_sl": (0, 40)},
            {"WHAT": "SERVICE", "SVC_SL": "50"},
            False,
            id="service level above range",
        ),
        pytest.param(
            _make_rule() | {"match_sl": (0, 100)},
            {"WHAT": "HOST", "HOST_SL": "75"},
            True,
            id="host service level in range",
        ),
    ],
)
def test_event_match_servicelevel(
    rule: EventRule, context: EventContext, expected_none: bool
) -> None:
    result = event_match_servicelevel(rule, context, False, {})
    assert (result is None) == expected_none


# -- event_match_hostlabels ----------------------------------------------------


@pytest.mark.parametrize(
    "rule, context, expected_none",
    [
        pytest.param(_make_rule(), {"HOSTLABEL_os": "linux"}, True, id="no condition"),
        pytest.param(
            _make_rule() | {"match_hostlabels": {"os": "linux"}},
            {"HOSTLABEL_os": "linux", "HOSTLABEL_env": "prod"},
            True,
            id="required label present",
        ),
        pytest.param(
            _make_rule() | {"match_hostlabels": {"os": "windows"}},
            {"HOSTLABEL_os": "linux"},
            False,
            id="label value does not match",
        ),
        pytest.param(
            _make_rule() | {"match_hostlabels": {"os": "linux"}},
            {},
            False,
            id="required label absent from context",
        ),
    ],
)
def test_event_match_hostlabels(
    rule: EventRule, context: EventContext, expected_none: bool
) -> None:
    result = event_match_hostlabels(rule, context, False, {})
    assert (result is None) == expected_none


# -- event_match_servicelabels -------------------------------------------------


@pytest.mark.parametrize(
    "rule, context, expected_none",
    [
        pytest.param(_make_rule(), {"SERVICELABEL_tier": "frontend"}, True, id="no condition"),
        pytest.param(
            _make_rule() | {"match_servicelabels": {"tier": "frontend"}},
            {"SERVICELABEL_tier": "frontend", "SERVICELABEL_env": "prod"},
            True,
            id="required label present",
        ),
        pytest.param(
            _make_rule() | {"match_servicelabels": {"tier": "backend"}},
            {"SERVICELABEL_tier": "frontend"},
            False,
            id="label value does not match",
        ),
        pytest.param(
            _make_rule() | {"match_servicelabels": {"tier": "frontend"}},
            {},
            False,
            id="required label absent from context",
        ),
    ],
)
def test_event_match_servicelabels(
    rule: EventRule, context: EventContext, expected_none: bool
) -> None:
    result = event_match_servicelabels(rule, context, False, {})
    assert (result is None) == expected_none


# -- event_match_servicegroups_fixed -------------------------------------------


@pytest.mark.parametrize(
    "rule, context, expected_none",
    [
        pytest.param(
            _make_rule(),
            {"WHAT": "SERVICE", "SERVICEGROUPNAMES": "web"},
            True,
            id="no condition",
        ),
        pytest.param(
            _make_rule(),
            {"WHAT": "HOST"},
            True,
            id="host notification without required groups",
        ),
        pytest.param(
            _make_rule() | {"match_servicegroups": ["web"]},
            {"WHAT": "HOST"},
            False,
            id="host notification with required groups",
        ),
        pytest.param(
            _make_rule() | {"match_servicegroups": ["web"]},
            {"WHAT": "SERVICE", "SERVICEGROUPNAMES": "web,db"},
            True,
            id="service in required group",
        ),
        pytest.param(
            _make_rule() | {"match_servicegroups": ["ops"]},
            {"WHAT": "SERVICE", "SERVICEGROUPNAMES": "web,db"},
            False,
            id="service not in required group",
        ),
        pytest.param(
            _make_rule() | {"match_servicegroups": ["web"]},
            {"WHAT": "SERVICE"},
            False,
            id="no service group info in context",
        ),
        pytest.param(
            _make_rule() | {"match_servicegroups": ["web"]},
            {"WHAT": "SERVICE", "SERVICEGROUPNAMES": ""},
            False,
            id="service in no group",
        ),
    ],
)
def test_event_match_servicegroups_fixed(
    rule: EventRule, context: EventContext, expected_none: bool
) -> None:
    result = event_match_servicegroups_fixed({})(rule, context, False, {})
    assert (result is None) == expected_none


# -- event_match_servicegroups_regex -------------------------------------------


@pytest.mark.parametrize(
    "rule, context, expected_none",
    [
        pytest.param(
            _make_rule(),
            {"WHAT": "SERVICE", "SERVICEGROUPNAMES": "webservers"},
            True,
            id="no condition",
        ),
        pytest.param(
            _make_rule() | {"match_servicegroups_regex": (None, ["web.*"])},
            {"WHAT": "SERVICE", "SERVICEGROUPNAMES": "webservers,db"},
            True,
            id="group name matches regex",
        ),
        pytest.param(
            _make_rule() | {"match_servicegroups_regex": (None, ["ops.*"])},
            {"WHAT": "SERVICE", "SERVICEGROUPNAMES": "webservers,db"},
            False,
            id="group name does not match regex",
        ),
        pytest.param(
            _make_rule() | {"match_servicegroups_regex": (None, ["web.*"])},
            {"WHAT": "HOST"},
            False,
            id="host notification with required groups",
        ),
    ],
)
def test_event_match_servicegroups_regex(
    rule: EventRule, context: EventContext, expected_none: bool
) -> None:
    result = event_match_servicegroups_regex({})(rule, context, False, {})
    assert (result is None) == expected_none


# -- event_match_exclude_servicegroups_fixed -----------------------------------


@pytest.mark.parametrize(
    "rule, context, expected_none",
    [
        pytest.param(
            _make_rule(),
            {"WHAT": "SERVICE", "SERVICEGROUPNAMES": "web"},
            True,
            id="no condition",
        ),
        pytest.param(
            _make_rule() | {"match_exclude_servicegroups": ["web"]},
            {"WHAT": "HOST"},
            True,
            id="host notification always passes",
        ),
        pytest.param(
            _make_rule() | {"match_exclude_servicegroups": ["web"]},
            {"WHAT": "SERVICE", "SERVICEGROUPNAMES": "web,db"},
            False,
            id="service in excluded group",
        ),
        pytest.param(
            _make_rule() | {"match_exclude_servicegroups": ["ops"]},
            {"WHAT": "SERVICE", "SERVICEGROUPNAMES": "web,db"},
            True,
            id="service not in excluded group",
        ),
        pytest.param(
            _make_rule() | {"match_exclude_servicegroups": ["web"]},
            {"WHAT": "SERVICE", "SERVICEGROUPNAMES": ""},
            True,
            id="service in no group cannot be excluded",
        ),
    ],
)
def test_event_match_exclude_servicegroups_fixed(
    rule: EventRule, context: EventContext, expected_none: bool
) -> None:
    result = event_match_exclude_servicegroups_fixed({})(rule, context, False, {})
    assert (result is None) == expected_none


# -- event_match_exclude_servicegroups_regex -----------------------------------

# define_servicegroups aliases are required: the regex-exclude path evaluates
# define_servicegroups[sg] for every group in context to build the error message,
# even when the pattern does not match.
_SG_ALIASES: Mapping[str, str] = {"webservers": "Web Servers", "db": "Database Servers"}


@pytest.mark.parametrize(
    "rule, context, expected_none",
    [
        pytest.param(
            _make_rule(),
            {"WHAT": "SERVICE", "SERVICEGROUPNAMES": "webservers"},
            True,
            id="no condition",
        ),
        pytest.param(
            _make_rule() | {"match_exclude_servicegroups_regex": (None, ["web.*"])},
            {"WHAT": "HOST"},
            True,
            id="host notification always passes",
        ),
        pytest.param(
            _make_rule() | {"match_exclude_servicegroups_regex": (None, ["web.*"])},
            {"WHAT": "SERVICE", "SERVICEGROUPNAMES": "webservers,db"},
            False,
            id="group name matches exclusion regex",
        ),
        pytest.param(
            _make_rule() | {"match_exclude_servicegroups_regex": (None, ["ops.*"])},
            {"WHAT": "SERVICE", "SERVICEGROUPNAMES": "webservers,db"},
            True,
            id="group name does not match exclusion regex",
        ),
        pytest.param(
            _make_rule() | {"match_exclude_servicegroups_regex": (None, ["web.*"])},
            {"WHAT": "SERVICE", "SERVICEGROUPNAMES": ""},
            True,
            id="service in no group cannot be excluded",
        ),
    ],
)
def test_event_match_exclude_servicegroups_regex(
    rule: EventRule, context: EventContext, expected_none: bool
) -> None:
    result = event_match_exclude_servicegroups_regex(_SG_ALIASES)(rule, context, False, {})
    assert (result is None) == expected_none


# -- event_match_timeperiod ----------------------------------------------------


@pytest.mark.parametrize(
    "rule, timeperiods_active, analyse, expected_none",
    [
        pytest.param(_make_rule(), {}, False, True, id="no condition"),
        pytest.param(
            _make_rule() | {"match_timeperiod": "business_hours"},
            {},
            True,
            True,
            id="analyse=True skips check",
        ),
        pytest.param(
            _make_rule() | {"match_timeperiod": "24X7"},
            {},
            False,
            True,
            id="24X7 always active",
        ),
        pytest.param(
            _make_rule() | {"match_timeperiod": "business_hours"},
            {"business_hours": True},
            False,
            True,
            id="timeperiod is active",
        ),
        pytest.param(
            _make_rule() | {"match_timeperiod": "business_hours"},
            {"business_hours": False},
            False,
            False,
            id="timeperiod is not active",
        ),
        pytest.param(
            _make_rule() | {"match_timeperiod": "business_hours"},
            {},
            False,
            True,
            id="unknown timeperiod defaults to active",
        ),
    ],
)
def test_event_match_timeperiod(
    rule: EventRule,
    timeperiods_active: CoreTimeperiodsActive,
    analyse: bool,
    expected_none: bool,
) -> None:
    matcher = event_match_timeperiod(timeperiods_active)
    result = matcher(rule, {}, analyse, {})
    assert (result is None) == expected_none
