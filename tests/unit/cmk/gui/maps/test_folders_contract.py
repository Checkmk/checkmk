#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# ruff: noqa: ARG001  # Unused fixtures are needed for setup side effects

"""The GUI↔daemon folder-skeleton contract, pinned end to end.

The GUI (:mod:`cmk.maps.gui._folders`) resolves the SETUP-folder skeleton with
the real ``Folder.groups()`` on every activation and writes it to
``maps.d/wato/folder_perms.mk``; the daemon
(:mod:`cmk.maps.backend.integrations.checkmk_folders`) reads it back to scope its
folder-tree map. This test writes with the *real* GUI hook and reads with the
*real* daemon loader, so drift in the file location, variable name or entry shape
fails CI. The ``Folder.groups()`` resolution itself is watolib's own concern; here
the folder tree is faked so the test pins the wire shape, not watolib.
"""

from collections.abc import Iterator
from pathlib import Path

import pytest

from cmk.maps.backend.core.config import settings as daemon_settings
from cmk.maps.backend.integrations import checkmk_folders
from cmk.maps.gui import _folders


class _FakeFolder:
    def __init__(self, path: str, title: str, fid: str, permitted: list[str]) -> None:
        self._path, self._title, self._id, self._permitted = path, title, fid, permitted

    def path(self) -> str:
        return self._path

    def title(self) -> str:
        return self._title

    def id(self) -> str:
        return self._id

    def groups(self) -> tuple[set[str], set[str], bool]:
        # (permitted_groups, host_contact_groups, use_for_services) — the writer
        # takes only the first element.
        return set(self._permitted), set(), False


class _FakeTree:
    def __init__(self, folders: list[_FakeFolder]) -> None:
        self._folders = folders

    def all_folders(self) -> dict[str, _FakeFolder]:
        return {f.path(): f for f in self._folders}


@pytest.fixture(name="shared_omd_root")
def fixture_shared_omd_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    """Point the GUI writer and the daemon reader at the same folder-perms file."""
    perms = tmp_path / "etc" / "check_mk" / "maps.d" / "wato" / "folder_perms.mk"
    monkeypatch.setattr(_folders, "folder_perms_path", lambda: perms)
    monkeypatch.setattr(daemon_settings, "checkmk_omd_root", str(tmp_path))
    yield tmp_path


def _fake_tree(monkeypatch: pytest.MonkeyPatch, folders: list[_FakeFolder]) -> None:
    monkeypatch.setattr(_folders, "folder_tree", lambda: _FakeTree(folders))


def test_skeleton_round_trips(shared_omd_root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _fake_tree(
        monkeypatch,
        [
            _FakeFolder("", "Main", "root-id", []),
            _FakeFolder("dc", "Datacenters", "dc-id", ["ops"]),
            _FakeFolder("dc/muc", "Munich", "muc-id", ["ops", "muc-admins"]),
        ],
    )

    _folders._on_pre_activate_changes()  # noqa: SLF001
    loaded = checkmk_folders.load_folder_perms()

    by_path = {entry["path"]: entry for entry in loaded}
    assert set(by_path) == {"", "dc", "dc/muc"}
    assert by_path[""] == {
        "path": "",
        "title": "Main",
        "folder_id": "root-id",
        "permitted_groups": [],
    }
    # permitted_groups is the effective (inheritance-resolved) read permission the
    # GUI produced; the daemon stores it verbatim, sorted.
    assert by_path["dc/muc"]["permitted_groups"] == ["muc-admins", "ops"]
    assert by_path["dc"]["title"] == "Datacenters"


def test_missing_file_means_no_skeleton(shared_omd_root: Path) -> None:
    assert checkmk_folders.load_folder_perms() == []


def test_daemon_converts_loaded_entries_to_folder_infos(
    shared_omd_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # The reader's entries feed the daemon's FolderInfo conversion unchanged.
    from cmk.maps.backend.connections.livestatus import _folder_info_from_entry

    _fake_tree(monkeypatch, [_FakeFolder("dc", "Datacenters", "dc-id", ["ops"])])
    _folders._on_pre_activate_changes()  # noqa: SLF001

    (entry,) = checkmk_folders.load_folder_perms()
    assert _folder_info_from_entry(entry) == {
        "path": "dc",
        "title": "Datacenters",
        "folder_id": "dc-id",
        "permitted_groups": ["ops"],
    }
