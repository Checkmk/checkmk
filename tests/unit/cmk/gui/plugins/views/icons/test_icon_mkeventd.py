#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Dict, List, NamedTuple

import pytest

import cmk.gui.plugins.views.icons.mkeventd as mkeventd_icon
from cmk.gui.plugins.views.icons.utils import get_multisite_icons


class IconRenderArgs(NamedTuple):
    what: str
    row: Dict
    tags: List
    custom_vars: Dict


class IconRenderResult(NamedTuple):
    name: str
    title: str
    url: str


@pytest.mark.parametrize(
    "args, result",
    [
        # Rule 'Check event state in Event Console' options:
        # Host specification:
        #     Match host with
        #         Hostname
        #         IP address
        #         Alias
        (
            IconRenderArgs(
                what="service",
                row={
                    "site": "heute",
                    "host_name": "heute",
                    "service_check_command": "check_mk_active-mkevents!'$HOSTNAME$/$HOSTADDRESS$/$HOSTALIAS$'",
                },
                tags=[],
                custom_vars={},
            ),
            IconRenderResult(
                name="mkeventd",
                title="Events of Host heute",
                url="view.py?host=heute&site=heute&view_name=ec_events_of_monhost",
            ),
        ),
        # Host specification:
        #     Specify host explicitly
        (
            IconRenderArgs(
                what="service",
                row={
                    "site": "heute",
                    "host_name": "heute",
                    "service_check_command": "check_mk_active-mkevents!'heute'",
                },
                tags=[],
                custom_vars={},
            ),
            IconRenderResult(
                name="mkeventd",
                title="Events of Host heute",
                url="view.py?host=heute&site=heute&view_name=ec_events_of_monhost",
            ),
        ),
        # Host specification:
        #   Specify host explicitly
        # Application (regular expression)
        (
            IconRenderArgs(
                what="service",
                row={
                    "site": "heute",
                    "host_name": "heute",
                    "service_check_command": "check_mk_active-mkevents!'heute' '^my_apps*'",
                },
                tags=[],
                custom_vars={},
            ),
            IconRenderResult(
                name="mkeventd",
                title='Events of Application "^my_apps*" on Host heute',
                url="view.py?event_application=%5Emy_apps%2A&host=heute&site=heute&view_name=ec_events_of_monhost",
            ),
        ),
        # Host specification:
        #     Match host with
        #         Hostname
        #         IP address
        #         Alias
        # Ignore Acknowledged events
        (
            IconRenderArgs(
                what="service",
                row={
                    "site": "heute",
                    "host_name": "heute",
                    "service_check_command": "check_mk_active-mkevents!'-a' '$HOSTNAME$/$HOSTADDRESS$/$HOSTALIAS$'",
                },
                tags=[],
                custom_vars={},
            ),
            IconRenderResult(
                name="mkeventd",
                title="Events of Host heute",
                url="view.py?host=heute&site=heute&view_name=ec_events_of_monhost",
            ),
        ),
        # Host specification:
        #     Match host with
        #         Alias
        # Application (regular expression)
        # Ignore Acknowledged events
        (
            IconRenderArgs(
                what="service",
                row={
                    "site": "heute",
                    "host_name": "heute",
                    "service_check_command": "check_mk_active-mkevents!'-a' '$HOSTALIAS$' '^my_apps*'",
                },
                tags=[],
                custom_vars={},
            ),
            IconRenderResult(
                name="mkeventd",
                title='Events of Application "^my_apps*" on Host my_alias',
                url="view.py?event_application=%5Emy_apps%2A&host=heute&site=heute&view_name=ec_events_of_monhost",
            ),
        ),
        # Host specification:
        #        Match host with
        #            IP address
        # Application (regular expression)
        # Ignore Acknowledged events
        (
            IconRenderArgs(
                what="service",
                row={
                    "site": "heute",
                    "host_name": "heute",
                    "host_address": "127.0.0.1",
                    "service_check_command": "check_mk_active-mkevents!'-a' '$HOSTADDRESS$' '^my_apps*'",
                },
                tags=[],
                custom_vars={},
            ),
            IconRenderResult(
                name="mkeventd",
                title='Events of Application "^my_apps*" on Host 127.0.0.1',
                url="view.py?event_application=%5Emy_apps%2A&host=heute&site=heute&view_name=ec_events_of_monhost",
            ),
        ),
    ],
)
def test_icon_options(args, result, request_context, monkeypatch) -> None:
    """Creation of title and url for links to event console entries of host"""
    icon = get_multisite_icons()["mkeventd"]

    def _get_dummy_hostname(args, row):
        args_splitted = args[0].split("/")
        if args_splitted[0] == "$HOSTNAME$":
            return row["host_name"]
        if args_splitted[0] == "$HOSTADDRESS$":
            return row["host_address"]
        if args_splitted[0] == "$HOSTALIAS$":
            return "my_alias"
        return args[0]

    monkeypatch.setattr(
        mkeventd_icon,
        "_get_hostname",
        _get_dummy_hostname,
    )

    assert icon.render(args.what, args.row, args.tags, args.custom_vars) == result
