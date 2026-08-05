#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.agent_based.v2 import Result, Service, State, StringTable
from cmk.plugins.vbox.agent_based import vbox_guest

# The agent pipes "VBoxControl guestproperty enumerate" through "cut -d, -f1,2", so each
# line is the whitespace split of e.g.
#   Name: /VirtualBox/GuestAdd/Version, value: 6.1.38
MATCHING: StringTable = [
    ["Name:", "/VirtualBox/GuestAdd/Version,", "value:", "6.1.38"],
    ["Name:", "/VirtualBox/GuestAdd/Revision,", "value:", "153438"],
    ["Name:", "/VirtualBox/HostInfo/VBoxVer,", "value:", "6.1.38"],
    ["Name:", "/VirtualBox/HostInfo/VBoxRev,", "value:", "153438"],
    ["Name:", "/VirtualBox/GuestInfo/OS/Product,", "value:", "Linux"],
]


def _with(overrides: dict[str, str]) -> StringTable:
    section = [list(line) for line in MATCHING]
    for path, value in overrides.items():
        for line in section:
            if line[1] == f"/VirtualBox/{path},":
                line[3] = value
    return section


def test_parse_keeps_the_string_table() -> None:
    assert vbox_guest.parse_vbox_guest(MATCHING) == MATCHING


def test_make_dict_strips_the_property_prefix() -> None:
    assert vbox_guest.vbox_guest_make_dict(MATCHING) == {
        "GuestAdd/Version": "6.1.38",
        "GuestAdd/Revision": "153438",
        "HostInfo/VBoxVer": "6.1.38",
        "HostInfo/VBoxRev": "153438",
        "GuestInfo/OS/Product": "Linux",
    }


def test_make_dict_accepts_a_property_without_a_value() -> None:
    """VirtualBox 6.x reports an empty value for OS/ServicePack, which leaves the line one
    field short. That used to make the whole section unparsable (werk 7410)."""
    section: StringTable = [["Name:", "/VirtualBox/GuestInfo/OS/ServicePack,", "value:"]]

    assert vbox_guest.vbox_guest_make_dict(section) == {"GuestInfo/OS/ServicePack": ""}


def test_discover_when_the_agent_reported_anything() -> None:
    assert list(vbox_guest.discover_vbox_guest(MATCHING)) == [Service()]


def test_discover_without_any_output() -> None:
    """The section is always sent, empty when no guest additions are installed - and then
    there is nothing to monitor."""
    assert list(vbox_guest.discover_vbox_guest([])) == []


def test_check_reports_a_failing_vboxcontrol() -> None:
    assert list(vbox_guest.check_vbox_guest({}, [["ERROR"]])) == [
        Result(state=State.UNKNOWN, summary="Error running VBoxControl guestproperty enumerate")
    ]


@pytest.mark.parametrize(
    "section",
    [
        pytest.param([], id="empty_section"),
        pytest.param([["unparsable"]], id="unparsable_line"),
        pytest.param([["Name:", "no-slashes,", "value:", "x"]], id="path_without_slashes"),
    ],
)
def test_check_reports_missing_guest_additions(section: StringTable) -> None:
    """Anything the property parser cannot turn into properties means the guest additions
    are not answering, which is what this check exists to detect."""
    assert list(vbox_guest.check_vbox_guest({}, section)) == [
        Result(state=State.CRIT, summary="No guest additions installed")
    ]


@pytest.mark.parametrize(
    "version",
    [
        pytest.param("", id="empty_version"),
        pytest.param("unknown", id="non_numeric_version"),
    ],
)
def test_check_reports_an_unusable_version(version: str) -> None:
    assert list(vbox_guest.check_vbox_guest({}, _with({"GuestAdd/Version": version}))) == [
        Result(state=State.UNKNOWN, summary="No guest addition version available")
    ]


def test_check_is_ok_when_guest_and_host_match() -> None:
    assert list(vbox_guest.check_vbox_guest({}, MATCHING)) == [
        Result(state=State.OK, summary="version: 6.1.38, revision: 153438")
    ]


def test_check_warns_about_an_outdated_version() -> None:
    """Guest additions older than the host are the usual cause of misbehaving integration,
    so the host's version is reported alongside."""
    assert list(vbox_guest.check_vbox_guest({}, _with({"HostInfo/VBoxVer": "7.0.10"}))) == [
        Result(
            state=State.WARN, summary="version: 6.1.38, revision: 153438, Host has 7.0.10/153438"
        )
    ]


def test_check_warns_about_a_differing_revision() -> None:
    assert list(vbox_guest.check_vbox_guest({}, _with({"HostInfo/VBoxRev": "999999"}))) == [
        Result(
            state=State.WARN, summary="version: 6.1.38, revision: 153438, Host has 6.1.38/999999"
        )
    ]


def test_check_crashes_without_the_host_properties() -> None:
    """Documents a gap: the host version is read with [] rather than .get(), so a guest that
    reports its own version but no HostInfo takes the check down instead of reporting UNKNOWN."""
    section = [line for line in MATCHING if not line[1].startswith("/VirtualBox/HostInfo")]

    with pytest.raises(KeyError):
        list(vbox_guest.check_vbox_guest({}, section))
