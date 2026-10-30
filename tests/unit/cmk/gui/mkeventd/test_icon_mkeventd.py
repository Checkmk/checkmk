#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import shlex
from collections.abc import Mapping, Sequence
from typing import Literal, NamedTuple

import pytest

import cmk.gui.mkeventd.icon as mkeventd_icon
from cmk.ccc.site import omd_site
from cmk.gui import sites
from cmk.gui.type_defs import Row
from cmk.gui.utils.roles import UserPermissions
from cmk.gui.views.icon import icon_and_action_registry, IconConfig
from cmk.livestatus_client.testing import MockLiveStatusConnection
from cmk.ruleset_matcher.tags import TagID


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
                    "host_address": "127.0.0.1",
                    "host_alias": "my_alias",
                    "service_check_command": "check_mk_active-mkevents!'$HOSTNAME$/$HOSTADDRESS$/$HOSTALIAS$'",
                },
                tags=[],
                custom_vars={},
            ),
            IconRenderResult(
                name="mkeventd",
                title="Events of host heute",
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
                    "host_address": "127.0.0.1",
                    "host_alias": "my_alias",
                    "service_check_command": "check_mk_active-mkevents!'heute'",
                },
                tags=[],
                custom_vars={},
            ),
            IconRenderResult(
                name="mkeventd",
                title="Events of host heute",
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
                    "host_address": "127.0.0.1",
                    "host_alias": "my_alias",
                    "service_check_command": "check_mk_active-mkevents!'heute' '^my_apps*'",
                },
                tags=[],
                custom_vars={},
            ),
            IconRenderResult(
                name="mkeventd",
                title='Events of application "^my_apps*" on host heute',
                url="view.py?event_application=%5Emy_apps%2A&host=heute&site=heute&view_name=ec_events_of_monhost",
            ),
            id="Specify host explicitly and application by regular expression",
        ),
        pytest.param(
            IconRenderArgs(
                what="service",
                row={
                    "site": "heute",
                    "host_name": "hostA",
                    "host_address": "127.0.0.1",
                    "host_alias": "my_alias",
                    "service_check_command": "check_mk_active-mkevents!'hostB' 'myapp'",
                },
                tags=[],
                custom_vars={},
            ),
            IconRenderResult(
                name="mkeventd",
                title='Events of application "myapp" on host hostB',
                url="view.py?event_application=myapp&event_host=hostB&host=hostB&site=heute&view_name=ec_events_of_host",
            ),
            id="Explicit host differs from monitored host",
        ),
        pytest.param(
            IconRenderArgs(
                what="service",
                row={
                    "site": "heute",
                    "host_name": "heute",
                    "host_address": "127.0.0.1",
                    "host_alias": "my_alias",
                    "service_check_command": "check_mk_active-mkevents!'HEUTE'",
                },
                tags=[],
                custom_vars={},
            ),
            IconRenderResult(
                name="mkeventd",
                title="Events of host heute",
                url="view.py?host=heute&site=heute&view_name=ec_events_of_monhost",
            ),
            id="Explicit host differs only in case from monitored host",
        ),
        # Macros are resolved when the command line is built
        pytest.param(
            IconRenderArgs(
                what="service",
                row={
                    "site": "heute",
                    "host_name": "hostA",
                    "host_address": "127.0.0.2",
                    "host_alias": "Host A",
                    "service_check_command": "check_mk_active-mkevents!'hostA/127.0.0.2/Host A' 'myapp'",
                },
                tags=[],
                custom_vars={},
            ),
            IconRenderResult(
                name="mkeventd",
                title='Events of application "myapp" on host hostA',
                url="view.py?event_application=myapp&host=hostA&site=heute&view_name=ec_events_of_monhost",
            ),
            id="Resolved host name, IP address and alias",
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
                    "host_address": "127.0.0.1",
                    "host_alias": "my_alias",
                    "service_check_command": "check_mk_active-mkevents!'-a' '$HOSTNAME$/$HOSTADDRESS$/$HOSTALIAS$'",
                },
                tags=[],
                custom_vars={},
            ),
            IconRenderResult(
                name="mkeventd",
                title="Events of host heute",
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
                    "host_address": "127.0.0.1",
                    "host_alias": "my_alias",
                    "service_check_command": "check_mk_active-mkevents!'-a' '$HOSTALIAS$' '^my_apps*'",
                },
                tags=[],
                custom_vars={},
            ),
            IconRenderResult(
                name="mkeventd",
                title='Events of application "^my_apps*" on host heute',
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
                    "host_alias": "my_alias",
                    "host_address": "127.0.0.1",
                    "service_check_command": "check_mk_active-mkevents!'-a' '$HOSTADDRESS$' '^my_apps*'",
                },
                tags=[],
                custom_vars={},
            ),
            IconRenderResult(
                name="mkeventd",
                title='Events of application "^my_apps*" on host heute',
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
                    "host_address": "127.0.0.1",
                    "host_alias": "my_alias",
                    "service_check_command": "check_mk_active-mkevents!'-L' '$HOSTNAME$/$HOSTADDRESS$/$HOSTALIAS$'",
                },
                tags=[],
                custom_vars={},
            ),
            IconRenderResult(
                name="mkeventd",
                title="Events of host heute",
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
                    "host_address": "127.0.0.1",
                    "host_alias": "my_alias",
                    "service_check_command": "check_mk_active-mkevents!'-a' '-l' '$HOSTNAME$/$HOSTADDRESS$/$HOSTALIAS$'",
                },
                tags=[],
                custom_vars={},
            ),
            IconRenderResult(
                name="mkeventd",
                title="Events of host heute",
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
                    "host_address": "127.0.0.1",
                    "host_alias": "my_alias",
                    "service_check_command": "check_mk_active-mkevents!'-H' '127.0.0.1:12345' '$HOSTNAME$/$HOSTADDRESS$/$HOSTALIAS$'",
                },
                tags=[],
                custom_vars={},
            ),
            IconRenderResult(
                name="mkeventd",
                title="Events of host heute",
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
                    "host_address": "127.0.0.1",
                    "host_alias": "my_alias",
                    "service_check_command": "check_mk_active-mkevents!'-H' '127.0.0.1:12345' '-L' '-a' '$HOSTNAME$/$HOSTADDRESS$/$HOSTALIAS$'",
                },
                tags=[],
                custom_vars={},
            ),
            IconRenderResult(
                name="mkeventd",
                title="Events of host heute",
                url="view.py?host=heute&site=heute&view_name=ec_events_of_monhost",
            ),
            id="Handling of multiple parameters with and without argument",
        ),
        # Check how the parser handles the end of the options in service_check_command
        pytest.param(
            IconRenderArgs(
                what="service",
                row={
                    "site": "heute",
                    "host_name": "heute",
                    "host_address": "127.0.0.1",
                    "host_alias": "my_alias",
                    "service_check_command": "check_mk_active-mkevents!'-a' '--' '$HOSTALIAS$' '-my_app'",
                },
                tags=[],
                custom_vars={},
            ),
            IconRenderResult(
                name="mkeventd",
                title='Events of application "-my_app" on host heute',
                url="view.py?event_application=-my_app&host=heute&site=heute&view_name=ec_events_of_monhost",
            ),
            id="Handling of the end of the options",
        ),
    ],
)
def test_icon_options(
    args: IconRenderArgs,
    result: IconRenderResult,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Creation of title and url for links to event console entries of host"""
    icon = icon_and_action_registry["mkeventd"]

    def _get_dummy_hostname(hosts: Sequence[str], row: Row) -> str:
        if hosts[0] == "$HOSTNAME$":
            return str(row["host_name"])
        if hosts[0] == "$HOSTADDRESS$":
            return str(row["host_address"])
        if hosts[0] == "$HOSTALIAS$":
            return "my_alias"
        return "/".join(hosts)

    monkeypatch.setattr(
        mkeventd_icon,
        "_get_hostname",
        _get_dummy_hostname,
    )

    assert (
        icon.render(
            args.what,
            args.row,
            args.tags,
            args.custom_vars,
            UserPermissions({}, {}, {}, []),
            IconConfig(
                wato_enabled=True,
                mkeventd_enabled=True,
                multisite_draw_ruleicon=True,
                staleness_threshold=1.5,
                debug=True,
            ),
        )
        == result
    )


_CMC_VERSION = "Check_MK 2.5.0"
_NAGIOS_VERSION = "3.5.0"


def _render_icon(site: str, check_command: str, alias: str = "my_alias") -> object:
    return icon_and_action_registry["mkeventd"].render(
        "service",
        {
            "site": site,
            "host_name": "heute",
            "host_address": "127.0.0.1",
            "host_alias": alias,
            "service_check_command": check_command,
        },
        [],
        {},
        UserPermissions({}, {}, {}, []),
        IconConfig(
            wato_enabled=True,
            mkeventd_enabled=True,
            multisite_draw_ruleicon=True,
            staleness_threshold=1.5,
            debug=True,
        ),
    )


@pytest.mark.parametrize(
    "program_version, check_command, alias",
    [
        pytest.param(
            _CMC_VERSION,
            r"check_mk_active-mkevents!'-q' '--' 'heute/Router A\/B' 'my_app'",
            "Router A/B",
            id="slash, cmc",
        ),
        pytest.param(
            _NAGIOS_VERSION,
            r"check_mk_active-mkevents!'-q' '--' 'heute/Router A\\/B' 'my_app'",
            "Router A/B",
            id="slash, nagios",
        ),
        # A command line from before check_mkevents knew "--"
        pytest.param(
            _CMC_VERSION,
            r"check_mk_active-mkevents!'-q' 'heute/Router A\/B' 'my_app'",
            "Router A/B",
            id="slash, cmc, without the end of the options",
        ),
        # Only Nagios doubles the backslashes of check_mkevents' quoting.
        pytest.param(
            _CMC_VERSION,
            r"check_mk_active-mkevents!'-q' '--' 'heute/\\\\fs1\\share' 'my_app'",
            r"\\fs1\share",
            id="backslashes, cmc",
        ),
        pytest.param(
            _NAGIOS_VERSION,
            r"check_mk_active-mkevents!'-q' '--' 'heute/\\\\\\\\fs1\\\\share' 'my_app'",
            r"\\fs1\share",
            id="backslashes, nagios",
        ),
    ],
)
@pytest.mark.usefixtures("request_context")
def test_quoted_host_list_with_the_alias_is_the_monitored_host(
    mock_livestatus: MockLiveStatusConnection, program_version: str, check_command: str, alias: str
) -> None:
    # The GUI connects to a remote site only if it knows the site's edition.
    site = omd_site()
    mock_livestatus.set_sites([site])
    mock_livestatus.tables["status"][site][0]["program_version"] = program_version

    with mock_livestatus(expect_status_query=True):
        sites.live()  # The view has fetched its rows before it renders the icons.
        rendered = _render_icon(site, check_command, alias)

    assert rendered == IconRenderResult(
        name="mkeventd",
        title='Events of application "my_app" on host heute',
        url=f"view.py?event_application=my_app&host=heute&site={site}&view_name=ec_events_of_monhost",
    )


@pytest.mark.usefixtures("request_context")
def test_title_shows_a_host_specification_without_quoting_as_it_is() -> None:
    rendered = _render_icon("heute", r"check_mk_active-mkevents!'--' 'Router A\/B' 'my_app'")

    assert rendered == IconRenderResult(
        name="mkeventd",
        title=r'Events of application "my_app" on host Router A\/B',
        url="view.py?event_application=my_app&event_host=Router+A%5C%2FB&host=Router+A%5C%2FB&site=heute&view_name=ec_events_of_host",
    )


@pytest.mark.usefixtures("request_context")
def test_whitespace_and_empty_hosts_in_a_host_list_dont_count_like_for_the_check() -> None:
    rendered = _render_icon(
        "heute", "check_mk_active-mkevents!'-q' '--' ' heute / 127.0.0.1 /' 'my_app'"
    )

    assert rendered == IconRenderResult(
        name="mkeventd",
        title='Events of application "my_app" on host heute',
        url="view.py?event_application=my_app&host=heute&site=heute&view_name=ec_events_of_monhost",
    )


@pytest.mark.parametrize(
    "program_version, check_command",
    [
        pytest.param(_CMC_VERSION, r"check_mk_active-mkevents!'--' 'heute' 'a\\b'", id="cmc"),
        # Only Nagios doubles the backslashes of the application.
        pytest.param(
            _NAGIOS_VERSION, r"check_mk_active-mkevents!'--' 'heute' 'a\\\\b'", id="nagios"
        ),
    ],
)
@pytest.mark.usefixtures("request_context")
def test_application_with_backslashes_is_the_regex_of_the_check(
    mock_livestatus: MockLiveStatusConnection, program_version: str, check_command: str
) -> None:
    site = omd_site()
    mock_livestatus.set_sites([site])
    mock_livestatus.tables["status"][site][0]["program_version"] = program_version

    with mock_livestatus(expect_status_query=True):
        sites.live()  # The view has fetched its rows before it renders the icons.
        rendered = _render_icon(site, check_command)

    assert rendered == IconRenderResult(
        name="mkeventd",
        title=r'Events of application "a\\b" on host heute',
        url=f"view.py?event_application=a%5C%5Cb&host=heute&site={site}&view_name=ec_events_of_monhost",
    )


@pytest.mark.usefixtures("request_context")
def test_application_with_apostrophes_is_the_regex_of_the_check() -> None:
    rendered = _render_icon(
        "heute", "check_mk_active-mkevents!'--' 'heute' " + shlex.quote("'my_app'")
    )

    assert rendered == IconRenderResult(
        name="mkeventd",
        title="Events of application \"'my_app'\" on host heute",
        url="view.py?event_application=%27my_app%27&host=heute&site=heute&view_name=ec_events_of_monhost",
    )
