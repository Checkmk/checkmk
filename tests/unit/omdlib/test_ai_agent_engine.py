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


def test_ai_agent_engine_conf_proxies_the_route_to_the_daemon_socket_when_enabled(
    tmp_path: Path,
) -> None:
    site_home = tmp_path
    (site_home / "etc" / "apache" / "conf.d").mkdir(parents=True)

    AI_AGENT_ENGINE.activation("unit", site_home, {"AI_AGENT_ENGINE": "on"})

    conf = (site_home / "etc" / "apache" / "conf.d" / "ai-agent-engine.conf").read_text()
    sock = site_home / "tmp" / "run" / "ai-agent-engine.sock"
    assert f'ProxyPass "/unit/check_mk/ai-agent-engine" "unix://{sock}|http://localhost:2" ' in conf
    assert 'ProxyPassReverse "/unit/check_mk/ai-agent-engine" "http://localhost:2"\n' in conf


def test_ai_agent_engine_conf_is_removed_when_disabled(tmp_path: Path) -> None:
    site_home = tmp_path
    conf_dir = site_home / "etc" / "apache" / "conf.d"
    conf_dir.mkdir(parents=True)
    (conf_dir / "ai-agent-engine.conf").write_text("stale")

    AI_AGENT_ENGINE.activation("unit", site_home, {"AI_AGENT_ENGINE": "off"})

    assert not (conf_dir / "ai-agent-engine.conf").exists()
