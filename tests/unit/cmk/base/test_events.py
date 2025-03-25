#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Final

import pytest
from pytest import MonkeyPatch

from cmk.utils.notify import NotificationHostConfig
from cmk.utils.notify_types import (
    EventRule,
    NotificationParameterID,
    NotificationRuleID,
    NotifyPluginParamsDict,
)
from cmk.utils.rulesets.ruleset_matcher import TagConditionNE
from cmk.utils.tags import TagGroupID, TagID

from cmk.events.event_context import EnrichedEventContext, EventContext

import cmk.base.events
from cmk.base.events import (
    _update_enriched_context_from_notify_host_file,
    add_to_event_context,
    apply_matchers,
    convert_proxy_params,
    event_match_hosttags,
    raw_context_from_string,
)


class HTTPPRoxyConfig:
    def to_requests_proxies(self) -> None:
        return None

    def serialize(self) -> str:
        return ""

    def __eq__(self, o: object) -> bool:
        return NotImplemented


HTTP_PROXY: Final = HTTPPRoxyConfig()


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
    add_to_event_context(context, "PARAMETER", param, lambda *args, **lw: HTTP_PROXY)
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
            ("no_proxy", None),
            id="No proxy",
        ),
        pytest.param(
            {"proxy_url": ("cmk_postprocessed", "stored_proxy", "proxy_id")},
            ("global", "proxy_id"),
            id="Stored proxy",
        ),
        pytest.param(
            {"proxy_url": ("cmk_postprocessed", "environment_proxy", "")},
            ("environment", "environment"),
            id="Environment proxy",
        ),
        pytest.param(
            {"proxy_url": ("cmk_postprocessed", "explicit_proxy", "http://www.myproxy.com")},
            ("url", "http://www.myproxy.com"),
            id="Explicit proxy",
        ),
    ],
)
def test_convert_proxy_params(
    params: NotifyPluginParamsDict,
    expected: tuple[str, str | None],
) -> None:
    params_dict = convert_proxy_params(params)
    assert params_dict["proxy_url"] == expected


def test_apply_matchers_catches_errors() -> None:
    rule = EventRule(
        rule_id=NotificationRuleID("1"),
        allow_disable=False,
        contact_all=False,
        contact_all_with_email=False,
        contact_object=False,
        description="Test rule",
        disabled=False,
        notify_plugin=("mail", NotificationParameterID("parameter_id")),
    )

    def raise_error() -> None:
        raise ValueError("This is a test")

    why_not = apply_matchers(
        [
            lambda *args, **kw: raise_error(),
        ],
        rule,
        context={},
        analyse=False,
        all_timeperiods={},
    )

    assert isinstance(why_not, str)
    assert "ValueError: This is a test" in why_not
