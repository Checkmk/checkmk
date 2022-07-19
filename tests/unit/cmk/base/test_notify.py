#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os
from typing import Mapping

import pytest
from _pytest.monkeypatch import MonkeyPatch

from tests.testlib.base import Scenario

from cmk.utils.type_defs import ContactgroupName, ContactName

from cmk.base import notify


def test_os_environment_does_not_override_notification_script_env(monkeypatch: MonkeyPatch) -> None:
    """Regression test for Werk #7339"""
    monkeypatch.setattr(os, "environ", {"NOTIFY_CONTACTEMAIL": ""})
    script_env = notify.notification_script_env({"CONTACTEMAIL": "ab@test.de"})
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
def test_raw_context_from_env_pipe_decoding(environ, expected):
    assert notify.raw_context_from_env(environ) == expected


@pytest.mark.parametrize(
    "raw_context,params,expected",
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
def test_create_plugin_context(raw_context, params, expected):
    assert notify.create_plugin_context(raw_context, params) == expected


@pytest.fixture(name="user_groups")
def fixture_user_groups() -> Mapping[ContactName, list[ContactgroupName]]:
    return {
        "ding": ["foo"],
        "dong": ["bar", "all"],
        "harry": ["foo"],
    }


def test_rbn_groups_contacts(
    monkeypatch: MonkeyPatch, user_groups: Mapping[ContactName, list[ContactgroupName]]
) -> None:
    ts = Scenario()
    ts.set_option(
        "contacts", {name: {"contactgroups": groups} for name, groups in user_groups.items()}
    )
    ts.apply(monkeypatch)
    assert notify.rbn_groups_contacts([]) == set()
    assert notify.rbn_groups_contacts(["nono"]) == set()
    assert notify.rbn_groups_contacts(["all"]) == set(["dong"])
    assert notify.rbn_groups_contacts(["foo"]) == set(["ding", "harry"])
    assert notify.rbn_groups_contacts(["foo", "all"]) == set(["ding", "dong", "harry"])
