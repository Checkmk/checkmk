#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os
from collections.abc import Mapping
from typing import Final

import pytest
from pytest import MonkeyPatch

from cmk.utils.notify_types import Contact, ContactName, NotificationContext, NotifyPluginParamsDict

from cmk.events.event_context import EnrichedEventContext, EventContext

from cmk.base import notify


class HTTPPRoxyConfig:
    def to_requests_proxies(self) -> None:
        return None

    def serialize(self) -> str:
        return ""

    def __eq__(self, o: object) -> bool:
        return NotImplemented


HTTP_PROXY: Final = HTTPPRoxyConfig()


def test_os_environment_does_not_override_notification_script_env(monkeypatch: MonkeyPatch) -> None:
    """Regression test for Werk #7339"""
    monkeypatch.setattr(os, "environ", {"NOTIFY_CONTACTEMAIL": ""})
    notification_context = NotificationContext({"CONTACTEMAIL": "ab@test.de"})
    script_env = notify.notification_script_env(notification_context)
    assert script_env == {"NOTIFY_CONTACTEMAIL": "ab@test.de"}


@pytest.mark.parametrize(
    "environ,expected",
    [
        ({}, {}),
        (
            {"TEST": "test"},
            {},
        ),
        (
            {"NOTIFY_TEST": "test"},
            {"TEST": "test"},
        ),
        (
            {"NOTIFY_SERVICEOUTPUT": "LONGSERVICEOUTPUT=with_light_vertical_bar_\u2758"},
            {"SERVICEOUTPUT": "LONGSERVICEOUTPUT=with_light_vertical_bar_|"},
        ),
        (
            {"NOTIFY_LONGSERVICEOUTPUT": "LONGSERVICEOUTPUT=with_light_vertical_bar_\u2758"},
            {"LONGSERVICEOUTPUT": "LONGSERVICEOUTPUT=with_light_vertical_bar_|"},
        ),
    ],
)
def test_raw_context_from_env_pipe_decoding(
    environ: Mapping[str, str], expected: EventContext
) -> None:
    assert notify.raw_context_from_env(environ) == expected


@pytest.mark.parametrize(
    "enriched_context,params,expected",
    [
        (
            {},
            {
                "from": {"address": "from@lala.com", "display_name": "from_display_name"},
                "reply_to": {"address": "reply@lala.com", "display_name": "reply_display_name"},
                "host_subject": "Check_MK: $HOSTNAME$ - $EVENT_TXT$",
                "service_subject": "Check_MK: $HOSTNAME$/$SERVICEDESC$ $EVENT_TXT$",
            },
            {
                "PARAMETER_FROM_ADDRESS": "from@lala.com",
                "PARAMETER_FROM_DISPLAY_NAME": "from_display_name",
                "PARAMETER_REPLY_TO_ADDRESS": "reply@lala.com",
                "PARAMETER_REPLY_TO_DISPLAY_NAME": "reply_display_name",
                "PARAMETER_HOST_SUBJECT": "Check_MK: $HOSTNAME$ - $EVENT_TXT$",
                "PARAMETER_SERVICE_SUBJECT": "Check_MK: $HOSTNAME$/$SERVICEDESC$ $EVENT_TXT$",
            },
        ),
    ],
)
def test_create_plugin_context(
    enriched_context: EnrichedEventContext,
    params: NotifyPluginParamsDict,
    expected: NotificationContext,
) -> None:
    assert (
        notify.create_plugin_context(
            enriched_context,
            params,
            lambda *args, **kw: HTTP_PROXY,
        )
        == expected
    )


@pytest.fixture(name="user_groups")
def fixture_user_groups() -> Mapping[ContactName, list[str]]:
    return {
        "ding": ["foo"],
        "dong": ["bar", "all"],
        "harry": ["foo"],
    }


def test_rbn_groups_contacts(user_groups: Mapping[ContactName, list[str]]) -> None:
    contacts = {name: Contact({"contactgroups": groups}) for name, groups in user_groups.items()}
    assert notify.rbn_groups_contacts([], config_contacts=contacts) == set()
    assert notify.rbn_groups_contacts(["nono"], config_contacts=contacts) == set()
    assert notify.rbn_groups_contacts(["all"], config_contacts=contacts) == {"dong"}
    assert notify.rbn_groups_contacts(["foo"], config_contacts=contacts) == {"ding", "harry"}
    assert notify.rbn_groups_contacts(["foo", "all"], config_contacts=contacts) == {
        "ding",
        "dong",
        "harry",
    }
