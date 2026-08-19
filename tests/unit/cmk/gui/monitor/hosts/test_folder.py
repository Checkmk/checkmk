#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import re
from collections.abc import Sequence
from typing import cast

import pytest

from cmk.gui.logged_in import LoggedInUser
from cmk.gui.monitor.hosts._folder import (
    folder_contains_filters,
    folder_from_filename,
    MonitorFolders,
    TitledFolder,
)


class _AnyUser:
    """Stands in for the asking user, whom the source below never consults."""


class _SetupFolders:
    """Stands in for Setup's folder tree, which is injected, not copied."""

    def __init__(self, folders: list[TitledFolder]) -> None:
        self._folders = folders

    def add(self, folder: TitledFolder) -> None:
        self._folders.append(folder)

    def folder_choices_fulltitle(self, acting_user: LoggedInUser) -> Sequence[TitledFolder]:
        return self._folders


@pytest.mark.parametrize(
    "filename, expected",
    [
        ("/wato/hosts.mk", "/"),
        ("/wato/network/switches/hosts.mk", "/network/switches"),
        ("/wato/network/hosts.mk", "/network"),
        ("/omd/sites/heute/etc/nagios/conf.d/hosts.mk", ""),
        ("/wato/network/switches/other.mk", ""),
    ],
)
def test_folder_from_filename(filename: str, expected: str) -> None:
    assert folder_from_filename(filename) == expected


@pytest.mark.parametrize(
    "value, expected",
    [
        pytest.param(
            "network",
            [r"Filter: filename ~~ ^/wato/.*network.*/hosts\.mk$"],
            id="folder name",
        ),
        pytest.param(
            "/network",
            [
                r"Filter: filename ~~ ^/wato/.*/network.*/hosts\.mk$",
                r"Filter: filename ~~ ^/wato/network.*/hosts\.mk$",
                "Or: 2",
            ],
            id="folder path, which may also be a prefix of the whole path",
        ),
        pytest.param(
            "/",
            [
                r"Filter: filename ~~ ^/wato/.*/.*/hosts\.mk$",
                r"Filter: filename ~~ ^/wato/.*/hosts\.mk$",
                "Filter: filename = /wato/hosts.mk",
                "Or: 3",
            ],
            id="every Setup folder, the root folder included",
        ),
        pytest.param(
            "",
            [
                r"Filter: filename ~~ ^/wato/.*.*/hosts\.mk$",
                "Filter: filename = /wato/hosts.mk",
                r"Filter: filename ~~ ^/wato/(.*/)?hosts\.mk$",
                "Negate:",
                "Or: 3",
            ],
            id="every host, those without a folder included",
        ),
        pytest.param(
            "net.*",
            [r"Filter: filename ~~ ^/wato/.*net\.\*.*/hosts\.mk$"],
            id="value is a literal, not a pattern",
        ),
    ],
)
def test_folder_contains_filters(value: str, expected: list[str]) -> None:
    assert folder_contains_filters(value) == expected


def test_folder_contains_filters_matches_the_title_setup_shows() -> None:
    """A title needs a file of its own: it may resemble the path in no way at all."""
    assert folder_contains_filters("Munich", folders=[("dc_muc", "Data center Munich")]) == [
        r"Filter: filename ~~ ^/wato/.*Munich.*/hosts\.mk$",
        "Filter: filename = /wato/dc_muc/hosts.mk",
        "Or: 2",
    ]


def test_folder_contains_filters_matches_the_root_folder_by_its_title() -> None:
    assert folder_contains_filters("Main", folders=[("", "Main"), ("network", "Netzwerk")]) == [
        r"Filter: filename ~~ ^/wato/.*Main.*/hosts\.mk$",
        "Filter: filename = /wato/hosts.mk",
        "Or: 2",
    ]


def test_folder_contains_filters_leaves_out_folders_the_path_already_matches() -> None:
    """Every folder path carries a slash, so titles would only repeat what the paths select."""
    folders: list[TitledFolder] = [("", "Main"), ("network", "Netzwerk"), ("muc", "Netzwerk/Muc")]

    assert folder_contains_filters("/", folders=folders) == folder_contains_filters("/")


def test_folders_stay_unknown_until_a_setup_source_is_wired() -> None:
    assert MonitorFolders().visible_to(cast(LoggedInUser, _AnyUser())) == ()


def test_the_setup_source_is_read_per_call_so_a_new_folder_is_seen() -> None:
    setup = _SetupFolders([("network", "Netzwerk")])
    folders = MonitorFolders()
    folders.use_setup_source(lambda: setup)

    setup.add(("dc_muc", "Data center Munich"))

    assert list(folders.visible_to(cast(LoggedInUser, _AnyUser()))) == [
        ("network", "Netzwerk"),
        ("dc_muc", "Data center Munich"),
    ]


# Filenames as the monitoring core emits them, plus the ones that look Setup-managed without
# being it. The first three are the fixtures the endpoint tests use, see
# tests/openapi/test_openapi_monitor_all_hosts.py.
_FILENAMES = (
    "/wato/hosts.mk",
    "/wato/network/hosts.mk",
    "/omd/sites/heute/etc/nagios/conf.d/hosts.mk",
    "/wato/network/dc1/hosts.mk",
    "/wato/dc_muc/hosts.mk",
    "/wato/Network/hosts.mk",
    "/wato/wato/hosts.mk",
    "/wato/hosts.mk/hosts.mk",
    "/wato/network/hosts.mk.bak",
    "/watoo/network/hosts.mk",
    "/omd/sites/heute/etc/check_mk/conf.d/wato/hosts.mk",
)
_VALUES = (
    "",
    "/",
    "network",
    "NETWORK",
    "/network",
    "/network/dc1",
    "dc",
    "wato",
    "hosts.mk",
    ".",
    "a|b",
    "net.*",
    # Titles of the folders below, whole and in part, in either case, and one crossing the
    # separator of a title path.
    "Netzwerk",
    "netzwerk",
    "Munich",
    "Data center",
    "Main",
    "/Rechenzentrum",
)
# How Setup titles the folders above: a title that shares nothing with its path, a title path
# carrying its parent's, and the root. Folders the paths of `_FILENAMES` do not name are left out
# on purpose - Setup does not know every file a monitoring core reports.
_FOLDERS: tuple[TitledFolder, ...] = (
    ("", "Main"),
    ("network", "Netzwerk"),
    ("network/dc1", "Netzwerk/Rechenzentrum 1"),
    ("dc_muc", "Data center Munich"),
)


def _title_path_of(filename: str) -> str:
    """What Setup titles the folder of this file, empty when Setup knows no such folder."""
    shown_folder = folder_from_filename(filename)
    for path, title_path in _FOLDERS:
        if shown_folder == ("/" if not path else f"/{path}"):
            return title_path
    return ""


@pytest.mark.parametrize("filename", _FILENAMES)
@pytest.mark.parametrize("value", _VALUES)
def test_folder_filters_match_exactly_the_folders_shown(value: str, filename: str) -> None:
    """Filtering by folder has to select the hosts whose folder carries the value.

    A folder carries it under either of its names: the path shown in the Folder column, or the
    title Setup shows. Both directions of the `filename` mapping are exercised at once - the
    folder is read from a filename the way the API returns it, and the filters produced for a
    value are evaluated against that same filename the way Livestatus would.
    """
    carries_value = (
        value.lower() in folder_from_filename(filename).lower()
        or value.lower() in _title_path_of(filename).lower()
    )

    assert _matches(folder_contains_filters(value, folders=_FOLDERS), filename) == carries_value


def _matches(filter_lines: Sequence[str], filename: str) -> bool:
    """Evaluate filter lines on a single `filename` the way Livestatus' filter stack does.

    Only what `folder_contains_filters` produces is understood; `~~` is a case-insensitive
    regex match, as in Livestatus (whose mock in `cmk.livestatus_client.testing` treats it as a
    plain substring, so it cannot stand in here).
    """
    stack: list[bool] = []
    for line in filter_lines:
        match line.split(" ", 3):
            case ["Filter:", "filename", "~~", pattern]:
                stack.append(re.search(pattern, filename, re.IGNORECASE) is not None)
            case ["Filter:", "filename", "=", value]:
                stack.append(filename == value)
            case ["Negate:"]:
                stack.append(not stack.pop())
            case ["Or:", count]:
                alternatives = [stack.pop() for _ in range(int(count))]
                stack.append(any(alternatives))
            case _:
                raise NotImplementedError(line)

    assert len(stack) == 1, f"{filter_lines} does not leave a single filter on the stack"
    return stack[0]
