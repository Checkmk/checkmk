#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence
from typing import Literal, NamedTuple

import pytest

from cmk.utils.tags import TagID

import cmk.gui.mkeventd.icon as mkeventd_icon
from cmk.gui.type_defs import Row
from cmk.gui.views.icon import icon_and_action_registry


class IconRenderArgs(NamedTuple):
    what: Literal["service", "host"]
    row: Row
    tags: Sequence[TagID]
    custom_vars: Mapping[str, str]


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
        pytest.param(
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
            id="Match host with host name, IP address, Alias",
        ),
        # Host specification:
        #     Specify host explicitly
        pytest.param(
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
            id="Specify host explicitly",
        ),
        # Host specification:
        #   Specify host explicitly
        # Application (regular expression)
        pytest.param(
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
            id="Specify host explicitly and application by regular expression",
        ),
        # Host specification:
        #     Match host with
        #         Hostname
        #         IP address
        #         Alias
        # Ignore Acknowledged events
        pytest.param(
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
            id="Match host with host name, IP address, Alias and ignore Acknowledged events",
        ),
        # Host specification:
        #     Match host with
        #         Alias
        # Application (regular expression)
        # Ignore Acknowledged events
        pytest.param(
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
            id="Match host with Alias, application by regular expression ignore ack events",
        ),
        # Host specification:
        #        Match host with
        #            IP address
        # Application (regular expression)
        # Ignore Acknowledged events
        pytest.param(
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
            id="Match host with IP address, application by regular expression ignore ack events",
        ),
        # Check how the parser handles the -L parameter in service_check_command
        pytest.param(
            IconRenderArgs(
                what="service",
                row={
                    "site": "heute",
                    "host_name": "heute",
                    "service_check_command": "check_mk_active-mkevents!'-L' '$HOSTNAME$/$HOSTADDRESS$/$HOSTALIAS$'",
                },
                tags=[],
                custom_vars={},
            ),
            IconRenderResult(
                name="mkeventd",
                title="Events of Host heute",
                url="view.py?host=heute&site=heute&view_name=ec_events_of_monhost",
            ),
            id="-L parameter handling",
        ),
        # Check how the parser handles two single parameters in service_check_command
        pytest.param(
            IconRenderArgs(
                what="service",
                row={
                    "site": "heute",
                    "host_name": "heute",
                    "service_check_command": "check_mk_active-mkevents!'-a' '-l' '$HOSTNAME$/$HOSTADDRESS$/$HOSTALIAS$'",
                },
                tags=[],
                custom_vars={},
            ),
            IconRenderResult(
                name="mkeventd",
                title="Events of Host heute",
                url="view.py?host=heute&site=heute&view_name=ec_events_of_monhost",
            ),
            id="Handling of multiple parameters without arguments",
        ),
        # Check how the parser handles -H parameter in service_check_command
        pytest.param(
            IconRenderArgs(
                what="service",
                row={
                    "site": "heute",
                    "host_name": "heute",
                    "service_check_command": "check_mk_active-mkevents!'-H' '127.0.0.1:12345' '$HOSTNAME$/$HOSTADDRESS$/$HOSTALIAS$'",
                },
                tags=[],
                custom_vars={},
            ),
            IconRenderResult(
                name="mkeventd",
                title="Events of Host heute",
                url="view.py?host=heute&site=heute&view_name=ec_events_of_monhost",
            ),
            id="Handling of parameter with argument",
        ),
        # Check how the parser handles -H parameter in service_check_command
        pytest.param(
            IconRenderArgs(
                what="service",
                row={
                    "site": "heute",
                    "host_name": "heute",
                    "service_check_command": "check_mk_active-mkevents!'-H' '127.0.0.1:12345' '-L' '-a' '$HOSTNAME$/$HOSTADDRESS$/$HOSTALIAS$'",
                },
                tags=[],
                custom_vars={},
            ),
            IconRenderResult(
                name="mkeventd",
                title="Events of Host heute",
                url="view.py?host=heute&site=heute&view_name=ec_events_of_monhost",
            ),
            id="Handling of multiple parameters with and without argument",
        ),
    ],
)
def test_icon_options(
    args: IconRenderArgs,
    result: IconRenderResult,
    monkeypatch: pytest.MonkeyPatch,
    request_context: None,
) -> None:
    """Creation of title and url for links to event console entries of host"""
    icon = icon_and_action_registry["mkeventd"]

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
