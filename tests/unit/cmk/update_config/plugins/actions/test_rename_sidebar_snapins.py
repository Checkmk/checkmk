#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
from pathlib import Path

import pytest

from cmk.ccc import store
from cmk.update_config.plugins.actions.rename_sidebar_snapins import RenameSidebarSnapins

LOGGER = logging.getLogger()


def test_rename_snapins_rewrites_renamed_ids_only(tmp_path: Path) -> None:
    path = tmp_path / "alice" / "sidebar.mk"
    path.parent.mkdir()
    store.save_object_to_file(
        path,
        {
            "fold": False,
            "snapins": [
                {"snapin_type_id": "metric_backend", "visibility": "open"},
                {"snapin_type_id": "tactical_overview", "visibility": "open"},
            ],
        },
    )

    RenameSidebarSnapins.rename_snapins(tmp_path, LOGGER)

    assert store.load_object_from_file(path, default=None) == {
        "fold": False,
        "snapins": [
            {"snapin_type_id": "telemetry_metrics", "visibility": "open"},
            {"snapin_type_id": "tactical_overview", "visibility": "open"},
        ],
    }


def test_rename_snapins_without_renamed_ids_is_a_noop(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    path = tmp_path / "bob" / "sidebar.mk"
    path.parent.mkdir()
    config = {"fold": True, "snapins": [{"snapin_type_id": "tactical_overview"}]}
    store.save_object_to_file(path, config)

    with caplog.at_level(logging.INFO):
        RenameSidebarSnapins.rename_snapins(tmp_path, LOGGER)

    assert store.load_object_from_file(path, default=None) == config
    assert caplog.messages == []
