#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Mapping

import pytest

from cmk.gui.plugins.wato import active_checks
from cmk.gui.plugins.wato.active_checks_mailbox import transform_check_mail_loop_params


@pytest.mark.parametrize(
    ["deprecated_params", "transformed_params"],
    [
        pytest.param(
            (
                "name",
                {
                    "ssl": True,
                    "expect_regex": ".*some_form.*",
                    "num_succeeded": (
                        3,
                        2,
                    ),
                },
            ),
            (
                "name",
                {
                    "tls_configuration": "tls_standard",
                    "expect_regex": ".*some_form.*",
                    "num_succeeded": (
                        3,
                        2,
                    ),
                },
            ),
            id="old format",
        ),
        pytest.param(
            (
                "name",
                {
                    "tls_configuration": "no_tls",
                    "timeout": 13,
                },
            ),
            (
                "name",
                {
                    "tls_configuration": "no_tls",
                    "timeout": 13,
                },
            ),
            id="current format without tls",
        ),
        pytest.param(
            (
                "name",
                {
                    "tls_configuration": "tls_standard",
                },
            ),
            (
                "name",
                {
                    "tls_configuration": "tls_standard",
                },
            ),
            id="current format with standard tls",
        ),
        pytest.param(
            (
                "name",
                {
                    "tls_configuration": "tls_no_cert_valid",
                },
            ),
            (
                "name",
                {
                    "tls_configuration": "tls_no_cert_valid",
                },
            ),
            id="current format with tls, server certificate validation disabled",
        ),
    ],
)
def test_transform_form_submit(
    deprecated_params: tuple[str, Mapping[str, object]],
    transformed_params: tuple[str, Mapping[str, object]],
) -> None:
    assert active_checks._transform_form_submit(deprecated_params) == transformed_params


@pytest.mark.parametrize(
    "old_rule,expected",
    [
        pytest.param(
            {
                "item": "service_name",
                "fetch": (
                    "IMAP",
                    {
                        "server": "imap.gmx.net",
                        "connection": {"disable_tls": False},
                        "auth": ("usr_imap", ("password", "pw_imap")),
                    },
                ),
                "smtp_server": "smtp.gmx.de",
                "smtp_tls": True,
                "mail_from": "me_from@gmx.de",
                "mail_to": "me_to@gmx.de",
            },
            {
                "fetch": (
                    "IMAP",
                    {
                        "auth": ("basic", ("usr_imap", ("password", "pw_imap"))),
                        "connection": {"disable_tls": False},
                        "server": "imap.gmx.net",
                    },
                ),
                "item": "service_name",
                "mail_from": "me_from@gmx.de",
                "mail_to": "me_to@gmx.de",
                "smtp_server": "smtp.gmx.de",
                "smtp_tls": True,
            },
            id="v2.0.0 rule with basic auth only and ssl as tuple",
        ),
        pytest.param(
            {
                "item": "service_name",
                "subject": "Some subject",
                "connect_timeout": 23,
                "mail_from": "me_from@gmx.de",
                "mail_to": "me_to@gmx.de",
                "smtp_server": "smtp.gmx.de",
                "smtp_tls": True,
                "imap_tls": True,
                "smtp_port": 25,
                "smtp_auth": ("usr_smtp", ("password", "pw_smtp")),
                "duration": (93780, 183840),
                "fetch": (
                    "IMAP",
                    {
                        "server": "imap.gmx.net",
                        "ssl": (False, 143),
                        "auth": ("usr_imap", ("password", "pw_imap")),
                    },
                ),
            },
            {
                "item": "service_name",
                "subject": "Some subject",
                "mail_from": "me_from@gmx.de",
                "mail_to": "me_to@gmx.de",
                "connect_timeout": 23,
                "smtp_auth": ("usr_smtp", ("password", "pw_smtp")),
                "duration": (93780, 183840),
                "fetch": (
                    "IMAP",
                    {
                        "auth": ("basic", ("usr_imap", ("password", "pw_imap"))),
                        "connection": {"disable_tls": False, "tcp_port": 143},
                        "server": "imap.gmx.net",
                    },
                ),
                "smtp_port": 25,
                "smtp_server": "smtp.gmx.de",
                "smtp_tls": True,
            },
            id="v2.0.0 with basic auth only and ssl as tuple",
        ),
        pytest.param(
            {
                "item": "service_name",
                "subject": "Some subject",
                "connect_timeout": 23,
                "mail_from": "me_from@gmx.de",
                "mail_to": "me_to@gmx.de",
                "fetch": (
                    "IMAP",
                    {
                        "auth": ("foobar", ("password", "password")),
                        "connection": {},
                    },
                ),
            },
            {
                "item": "service_name",
                "subject": "Some subject",
                "connect_timeout": 23,
                "mail_from": "me_from@gmx.de",
                "mail_to": "me_to@gmx.de",
                "fetch": (
                    "IMAP",
                    {
                        "auth": ("basic", ("foobar", ("password", "password"))),
                        "connection": {},
                        "server": None,
                    },
                ),
            },
            id="v2.1.0 rule with already migrated fetch/connection dict but still "
            "old basic auth only format",
        ),
    ],
)
def test_transform_check_mail_loop_params(old_rule, expected):
    assert transform_check_mail_loop_params(old_rule) == expected
