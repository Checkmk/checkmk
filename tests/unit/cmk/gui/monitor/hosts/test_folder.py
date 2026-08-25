#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Sequence

import pytest

from cmk.gui.monitor.hosts._folder import (
    folder_matching_filters,
    folder_path_from_filename,
    folder_title,
    MonitorFolders,
    SetupFolders,
)


def _wired_to(titles: dict[str, str]) -> MonitorFolders:
    """A `MonitorFolders` reading these titles, the way Setup's functions are wired in."""
    folders = MonitorFolders()
    folders.use_setup_source(
        SetupFolders(title_of=titles.get, all_titles=lambda: titles),
    )
    return folders


# How Setup titles the folders of the filenames below: the root, a title that shares nothing with
# its path, and a child whose title path carries its parent's. Folders the filenames name but Setup
# does not know are left out on purpose - a monitoring core reports files Setup never wrote.
_TITLES = {
    "": "Main",
    "network": "Netzwerk",
    "network/dc1": "Netzwerk / Rechenzentrum 1",
    "dc_muc": "Data center Munich",
}


@pytest.mark.parametrize(
    "filename, expected",
    [
        ("/wato/hosts.mk", ""),
        ("/wato/network/hosts.mk", "network"),
        ("/wato/network/switches/hosts.mk", "network/switches"),
        ("/omd/sites/heute/etc/nagios/conf.d/hosts.mk", None),
        ("/wato/network/switches/other.mk", None),
        ("/watoo/network/hosts.mk", None),
    ],
)
def test_folder_path_from_filename(filename: str, expected: str | None) -> None:
    assert folder_path_from_filename(filename) == expected


@pytest.mark.parametrize(
    "filename, expected",
    [
        pytest.param("/wato/hosts.mk", "Main", id="the root folder is titled Main"),
        pytest.param("/wato/dc_muc/hosts.mk", "Data center Munich", id="a title unlike its path"),
        pytest.param(
            "/wato/network/dc1/hosts.mk",
            "Netzwerk / Rechenzentrum 1",
            id="the titles down to the folder",
        ),
        pytest.param("/wato/nowhere/hosts.mk", "", id="a folder Setup does not know"),
        pytest.param("/omd/sites/heute/hosts.mk", "", id="not managed via Setup"),
    ],
)
def test_folder_title(filename: str, expected: str) -> None:
    assert folder_title(filename, _TITLES.get) == expected


def test_folder_title_is_empty_while_no_setup_source_is_wired() -> None:
    assert folder_title("/wato/dc_muc/hosts.mk", MonitorFolders().title_of) == ""


@pytest.mark.parametrize(
    "value, expected",
    [
        pytest.param(
            "Munich",
            ["Filter: filename = /wato/dc_muc/hosts.mk"],
            id="one folder carries the title",
        ),
        pytest.param(
            "Netzwerk",
            [
                "Filter: filename = /wato/network/hosts.mk",
                "Filter: filename = /wato/network/dc1/hosts.mk",
                "Or: 2",
            ],
            id="a parent's title reaches its subfolders",
        ),
        pytest.param(
            "Main",
            ["Filter: filename = /wato/hosts.mk"],
            id="the root folder by its title",
        ),
        pytest.param(
            "dc_muc",
            ["Filter: state >= 0", "Negate:"],
            id="the path is no longer a name to filter by",
        ),
        pytest.param(
            "no such folder",
            ["Filter: state >= 0", "Negate:"],
            id="no folder carries it, so no host does",
        ),
    ],
)
def test_folder_matching_filters(value: str, expected: list[str]) -> None:
    assert folder_matching_filters(value, _TITLES) == expected


def test_folder_matching_filters_selects_nothing_while_no_titles_are_known() -> None:
    """The one failure mode that would pass unseen: no lines at all selects every host."""
    assert folder_matching_filters("Munich", {}) == ["Filter: state >= 0", "Negate:"]


def test_folders_stay_unknown_until_a_setup_source_is_wired() -> None:
    folders = MonitorFolders()

    assert folders.titles() == {}
    assert folders.title_of("dc_muc") is None


def test_the_setup_source_is_asked_per_call_so_a_new_folder_is_seen() -> None:
    titles = {"network": "Netzwerk"}
    folders = _wired_to(titles)

    titles["dc_muc"] = "Data center Munich"

    assert folders.title_of("dc_muc") == "Data center Munich"
    assert dict(folders.titles()) == {"network": "Netzwerk", "dc_muc": "Data center Munich"}


# Filenames as a monitoring core reports them: files Setup wrote, files it did not, and files that
# only look like its own. The first three are the fixtures the endpoint tests use, see
# tests/openapi/test_openapi_monitor_all_hosts.py.
_FILENAMES = (
    "/wato/hosts.mk",
    "/wato/network/hosts.mk",
    "/omd/sites/heute/etc/nagios/conf.d/hosts.mk",
    "/wato/network/dc1/hosts.mk",
    "/wato/dc_muc/hosts.mk",
    "/wato/nowhere/hosts.mk",
    "/wato/network/hosts.mk.bak",
    "/watoo/network/hosts.mk",
    "/omd/sites/heute/etc/check_mk/conf.d/wato/hosts.mk",
)
_VALUES = (
    "",
    "Netzwerk",
    "netzwerk",
    "Rechenzentrum",
    "Netzwerk / Rechenzentrum 1",
    "Munich",
    "Data center",
    "Main",
    # Names that are not titles: the folder paths, and the fixed parts of a filename.
    "dc_muc",
    "network",
    "/network",
    "wato",
    "hosts.mk",
)


@pytest.mark.parametrize("filename", _FILENAMES)
@pytest.mark.parametrize("value", _VALUES)
def test_folder_filters_select_exactly_the_folders_shown(value: str, filename: str) -> None:
    """Filtering by folder has to select the hosts whose shown folder carries the value.

    Both directions are exercised at once: the folder is titled from a filename the way the API
    returns it, and the filters produced for a value are evaluated against that same filename the
    way Livestatus would. A host whose folder Setup does not know shows no title, and is therefore
    never selected - not even by the empty value.
    """
    shown_title = folder_title(filename, _TITLES.get)
    carries_value = bool(shown_title) and value.lower() in shown_title.lower()

    assert _matches(folder_matching_filters(value, _TITLES), filename) == carries_value


def _matches(filter_lines: Sequence[str], filename: str) -> bool:
    """Evaluate filter lines on a single `filename` the way Livestatus' filter stack does."""
    stack: list[bool] = []
    for line in filter_lines:
        match line.split(" ", 3):
            case ["Filter:", "filename", "=", value]:
                stack.append(filename == value)
            case ["Filter:", "state", ">=", "0"]:
                # Every host has a state, so this holds for the host at hand, whichever it is.
                stack.append(True)
            case ["Negate:"]:
                stack.append(not stack.pop())
            case ["Or:", count]:
                alternatives = [stack.pop() for _ in range(int(count))]
                stack.append(any(alternatives))
            case _:
                raise NotImplementedError(line)

    assert len(stack) == 1, f"{filter_lines} does not leave a single filter on the stack"
    return stack[0]
