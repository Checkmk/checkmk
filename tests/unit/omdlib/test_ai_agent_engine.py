#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

import pytest

from omdlib.ai_agent_engine import AI_AGENT_ENGINE, ai_agent_engine_has_error
from omdlib.config_hooks import get_hook

from cmk.ccc.version import Edition
from cmk.flags import CONFIG_FILENAME


@pytest.mark.parametrize("edition", list(Edition), ids=lambda e: e.name.lower())
def test_ai_agent_engine_ships_disabled(edition: Edition) -> None:
    assert AI_AGENT_ENGINE.default(edition) == "off"


def test_ai_agent_engine_hook_is_registered() -> None:
    assert get_hook(AI_AGENT_ENGINE.name) is AI_AGENT_ENGINE


def test_ai_agent_engine_has_error_rejects_invalid_value(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    assert ai_agent_engine_has_error("maybe") is not None


def test_ai_agent_engine_has_error_blocks_on_when_release_flag_off(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    assert ai_agent_engine_has_error("off") is None
    assert ai_agent_engine_has_error("on") is not None


def test_ai_agent_engine_has_error_allows_on_when_release_flag_on(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "etc/check_mk").mkdir(parents=True)
    (tmp_path / "etc/check_mk" / CONFIG_FILENAME).write_text('{"exp_ai_assistant": true}')

    assert ai_agent_engine_has_error("on") is None
