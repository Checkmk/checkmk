#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
import logging
from pathlib import Path

import pytest

from cmk.flags import CONFIG_FILENAME
from cmk.gui.release_flags import global_config
from cmk.update_config.plugins.actions import release_flags  # noqa: F401
from cmk.update_config.registry import update_action_registry

LOGGER = logging.getLogger("test")


@pytest.fixture(autouse=True)
def _release_flags_config_dir(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(global_config, "RELEASE_FLAGS_CONFIG_DIR", tmp_path)


@pytest.mark.usefixtures("request_context")
def test_removes_flags_that_no_longer_exist(tmp_path: Path) -> None:
    config_file = tmp_path / CONFIG_FILENAME
    config_file.write_text('{"already_removed_flag": true}')

    update_action_registry["release_flags"](LOGGER)

    assert "already_removed_flag" not in json.loads(config_file.read_text())


@pytest.mark.usefixtures("request_context")
def test_does_not_create_config_file_when_missing(tmp_path: Path) -> None:
    config_file = tmp_path / CONFIG_FILENAME

    update_action_registry["release_flags"](LOGGER)

    assert not config_file.exists()
