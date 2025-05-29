#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from pathlib import Path

import pytest
from _pytest.monkeypatch import MonkeyPatch

from cmk.special_agents.v0_unstable.storage import Storage

TEST_AGENT = "test_agent"
TEST_HOST = "test_host"
DEFAULT_VALUE = "default_value"


@pytest.fixture
def agent_storage(monkeypatch: MonkeyPatch, tmp_path: Path) -> Storage:
    """Fixture to provide a SpecialAgentStorage instance with isolated directories."""
    with monkeypatch.context() as m:
        m.setenv("OMD_ROOT", str(tmp_path))
        return Storage(
            program_ident=TEST_AGENT,
            host=TEST_HOST,
        )


def test_write_and_read_text_persistent(agent_storage):
    key = "my_text"
    value = "hello, persistent world"
    agent_storage.write(key, value)
    result = agent_storage.read(key, DEFAULT_VALUE)
    assert result == value
    assert result != DEFAULT_VALUE


def test_read_nonexistent_returns_default(agent_storage):
    result = agent_storage.read("does_not_exist", DEFAULT_VALUE)
    assert result == DEFAULT_VALUE


def test_invalid_key_name(agent_storage):
    key = "foo/bar/baz*.!"
    value = "slash test"
    with pytest.raises(ValueError):
        agent_storage.write(key, value)
