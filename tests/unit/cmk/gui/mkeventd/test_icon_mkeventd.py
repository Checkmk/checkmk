#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import shlex
from typing import NamedTuple

import pytest

from cmk.ccc.site import omd_site
from cmk.gui import sites
from cmk.gui.utils.roles import UserPermissions
from cmk.gui.views.icon import icon_and_action_registry, IconConfig
from cmk.livestatus_client.testing import MockLiveStatusConnection


class IconRenderResult(NamedTuple):
    name: str
    title: str
    url: str


@pytest.mark.parametrize(
    "check_command, title, url",
    [
        pytest.param(
            "check_mk_active-mkevents!'$HOSTNAME$/$HOSTADDRESS$/$HOSTALIAS$'",
            "Events of host heute",
            "view.py?host=heute&site=heute&view_name=ec_events_of_monhost",
            id="Match host with host name, IP address, Alias",
        ),
        pytest.param(
            "check_mk_active-mkevents!'heute'",
            "Events of host heute",
            "view.py?host=heute&site=heute&view_name=ec_events_of_monhost",
            id="Specify host explicitly",
        ),
        pytest.param(
            "check_mk_active-mkevents!'heute' '^my_apps*'",
            'Events of application "^my_apps*" on host heute',
            "view.py?event_application=%5Emy_apps%2A&host=heute&site=heute&view_name=ec_events_of_monhost",
            id="Specify host explicitly and application by regular expression",
        ),
        pytest.param(
            "check_mk_active-mkevents!'hostB' 'myapp'",
            'Events of application "myapp" on host hostB',
            "view.py?event_application=myapp&event_host=hostB&host=hostB&site=heute&view_name=ec_events_of_host",
            id="Explicit host differs from monitored host",
        ),
        pytest.param(
            "check_mk_active-mkevents!'HEUTE'",
            "Events of host heute",
            "view.py?host=heute&site=heute&view_name=ec_events_of_monhost",
            id="Explicit host differs only in case from monitored host",
        ),
        pytest.param(
            "check_mk_active-mkevents!'heute/127.0.0.1/my_alias' 'myapp'",
            'Events of application "myapp" on host heute',
            "view.py?event_application=myapp&host=heute&site=heute&view_name=ec_events_of_monhost",
            id="Resolved host name, IP address and alias",
        ),
        pytest.param(
            "check_mk_active-mkevents!'-a' '$HOSTNAME$/$HOSTADDRESS$/$HOSTALIAS$'",
            "Events of host heute",
            "view.py?host=heute&site=heute&view_name=ec_events_of_monhost",
            id="Match host with host name, IP address, Alias and ignore Acknowledged events",
        ),
        pytest.param(
            "check_mk_active-mkevents!'-a' '$HOSTALIAS$' '^my_apps*'",
            'Events of application "^my_apps*" on host heute',
            "view.py?event_application=%5Emy_apps%2A&host=heute&site=heute&view_name=ec_events_of_monhost",
            id="Match host with Alias, application by regular expression ignore ack events",
        ),
        pytest.param(
            "check_mk_active-mkevents!'-a' '$HOSTADDRESS$' '^my_apps*'",
            'Events of application "^my_apps*" on host heute',
            "view.py?event_application=%5Emy_apps%2A&host=heute&site=heute&view_name=ec_events_of_monhost",
            id="Match host with IP address, application by regular expression ignore ack events",
        ),
        pytest.param(
            "check_mk_active-mkevents!'-L' '$HOSTNAME$/$HOSTADDRESS$/$HOSTALIAS$'",
            "Events of host heute",
            "view.py?host=heute&site=heute&view_name=ec_events_of_monhost",
            id="-L parameter handling",
        ),
        pytest.param(
            "check_mk_active-mkevents!'-a' '-l' '$HOSTNAME$/$HOSTADDRESS$/$HOSTALIAS$'",
            "Events of host heute",
            "view.py?host=heute&site=heute&view_name=ec_events_of_monhost",
            id="Handling of multiple parameters without arguments",
        ),
        pytest.param(
            "check_mk_active-mkevents!'-H' '127.0.0.1:12345' '$HOSTNAME$/$HOSTADDRESS$/$HOSTALIAS$'",
            "Events of host heute",
            "view.py?host=heute&site=heute&view_name=ec_events_of_monhost",
            id="Handling of parameter with argument",
        ),
        pytest.param(
            "check_mk_active-mkevents!'-H' '127.0.0.1:12345' '-L' '-a' '$HOSTNAME$/$HOSTADDRESS$/$HOSTALIAS$'",
            "Events of host heute",
            "view.py?host=heute&site=heute&view_name=ec_events_of_monhost",
            id="Handling of multiple parameters with and without argument",
        ),
        pytest.param(
            "check_mk_active-mkevents!'-a' '--' '$HOSTALIAS$' '-my_app'",
            'Events of application "-my_app" on host heute',
            "view.py?event_application=-my_app&host=heute&site=heute&view_name=ec_events_of_monhost",
            id="Handling of the end of the options",
        ),
    ],
)
@pytest.mark.usefixtures("request_context")
def test_icon_links_to_the_events_the_check_looks_at(
    check_command: str, title: str, url: str
) -> None:
    rendered = _render_icon("heute", check_command)

    assert rendered == IconRenderResult(name="mkeventd", title=title, url=url)


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
