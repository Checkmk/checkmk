#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Unit tests for :meth:`tests.testlib.system.site.Site.activate_changes_and_wait_for_core_reload`.

One activation covers every site that has changes, so which cores are waited for
afterwards is a decision the caller cannot see on a live site until a check result
lands on a core that was still reloading.
"""

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from tests.testlib.system.site import Site


class FakeCore:
    """The `GET status` answer of one site's core."""

    def __init__(self, program_start: int) -> None:
        self.program_start = program_start

    def query_value(self, _query: str) -> object:
        return self.program_start


def _sites(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, *site_ids: str, activated: bool
) -> tuple[list[Site], list[tuple[str, object]]]:
    """Build sites whose cores answer, and record which of them are waited for.

    `activated` is what the activation reports back: whether there were changes.
    """
    cores: dict[str, FakeCore] = {}
    waited: list[tuple[str, object]] = []

    monkeypatch.setattr(Site, "live", property(lambda site: cores[site.id]))
    monkeypatch.setattr(Site, "ensure_running", lambda _site: None)
    monkeypatch.setattr(Site, "path", lambda _site, rel_path: tmp_path / rel_path)
    monkeypatch.setattr(
        Site, "wait_for_core_reloaded", lambda site, after: waited.append((site.id, after))
    )

    sites = []
    for program_start, site_id in enumerate(site_ids, start=1):
        site = Site.__new__(Site)  # a real site cannot be built without an installed Checkmk
        site.id = site_id
        openapi = MagicMock()
        openapi.changes.activate_and_wait_for_completion.return_value = activated
        site.openapi = openapi
        cores[site_id] = FakeCore(program_start)
        sites.append(site)
    return sites, waited


def test_every_named_site_is_waited_for(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    (central, remote), waited = _sites(monkeypatch, tmp_path, "central", "remote", activated=True)

    central.activate_changes_and_wait_for_core_reload(reload_core_on_sites=(central, remote))

    assert waited == [("central", 1), ("remote", 2)]


def test_the_activating_site_is_waited_for_when_no_site_is_named(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    (central, _remote), waited = _sites(monkeypatch, tmp_path, "central", "remote", activated=True)

    central.activate_changes_and_wait_for_core_reload()

    assert waited == [("central", 1)]


def test_nothing_is_waited_for_when_there_was_nothing_to_activate(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    (central, remote), waited = _sites(monkeypatch, tmp_path, "central", "remote", activated=False)

    central.activate_changes_and_wait_for_core_reload(reload_core_on_sites=(central, remote))

    assert waited == []


def test_an_activation_that_is_still_running_is_refused(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Activating on top of a running activation would make the wait meaningless."""
    (central,), _waited = _sites(monkeypatch, tmp_path, "central", activated=True)
    monkeypatch.setattr(Site, "read_file", lambda _site, path: Path(path).read_text())
    wato_dir = tmp_path / "var" / "check_mk" / "wato"
    wato_dir.mkdir(parents=True)
    (wato_dir / "replication_status_remote").write_text("{'current_activation': 'a1'}")

    with pytest.raises(RuntimeError, match="previous activation"):
        central.activate_changes_and_wait_for_core_reload()
