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


@pytest.mark.parametrize(
    "program_ident,host",
    [
        pytest.param("pid.log.cache.json", "pid.log.cache.json"),
        pytest.param("pid.log_cache.json", "pid.log_cache.json"),
        pytest.param("pid.log-cache.json", "pid.log-cache.json"),
        pytest.param("pid.log123-7412cache.json", "pid.log123-7412cache.json"),
        pytest.param(
            "7d160171-a52a-43d0-b43c-644540aad7ec", "7d160171-a52a-43d0-b43c-644540aad7ec"
        ),
        pytest.param("pid.log.-sad?/&fjaads", "pid.log.-sad?/&fjaads"),
        pytest.param("pid.lo__-sadöfjaads", "pid.lo__-sadöfjaads"),
        pytest.param("__pid”~n.log.-sadöfjaads", "__pid”~n.log.-sadöfjaads"),
        pytest.param("!?=pid.log.-sadöfjaads", "!?=pid.log.-sadöfjaads"),
        pytest.param("!?=pid.ñlog.-sadöfjaads", "!?=pid.ñlog.-sadöfjaads"),
        pytest.param("!?=pid.ñlo/g.-sadöfjaads", "!?=pid.ñlo/g.-sadöfjaads"),
        pytest.param("!?=pid.ñlog.-sadöfjaads", "!?=pid.ñlog.-sadöfjaads"),
    ],
)
def test_agent_storage_init(
    monkeypatch: MonkeyPatch, tmp_path: Path, program_ident: str, host: str
) -> None:
    with monkeypatch.context() as m:
        m.setenv("OMD_ROOT", str(tmp_path))
        Storage(program_ident, host)
        assert True


@pytest.mark.parametrize(
    "key_name",
    [
        pytest.param("pid.log.cache.json"),
        pytest.param("pid.log_cache.json"),
        pytest.param("pid.log-cache.json"),
        pytest.param("pid.log123-7412cache.json"),
        pytest.param("7d160171-a52a-43d0-b43c-644540aad7ec"),
        pytest.param("pid.log.-sad?/&fjaads"),
        pytest.param("pid.lo__-sadöfjaads"),
        pytest.param("__pid”~n.log.-sadöfjaads"),
        pytest.param("!?=pid.log.-sadöfjaads"),
        pytest.param("!?=pid.ñlog.-sadöfjaads"),
        pytest.param("!?=pid.ñlo/g.-sadöfjaads"),
        pytest.param("!?=pid.ñlog.-sadöfjaads"),
    ],
)
def test_write_and_read_text_persistent(agent_storage, key_name):
    value = "hello, persistent world"
    agent_storage.write(key_name, value)
    result = agent_storage.read(key_name, DEFAULT_VALUE)
    assert result == value
    assert result != DEFAULT_VALUE


def test_read_nonexistent_returns_default(agent_storage):
    result = agent_storage.read("does_not_exist", DEFAULT_VALUE)
    assert result == DEFAULT_VALUE


@pytest.mark.parametrize(
    "key, expected_safe_key",
    [
        pytest.param("pid.log.cache.json", "pid.log.cache.json"),
        pytest.param("pid.log_cache.json", "pid.log_cache.json"),
        pytest.param("pid.log-cache.json", "pid.log-cache.json"),
        pytest.param("pid.log123-7412cache.json", "pid.log123-7412cache.json"),
        pytest.param(
            "7d160171-a52a-43d0-b43c-644540aad7ec", "7d160171-a52a-43d0-b43c-644540aad7ec"
        ),
        pytest.param("pid.log.-sad?/&fjaads", "pid.log.-sad%3F%2F%26fjaads"),
        pytest.param("pid.lo__-sadöfjaads", "pid.lo__-sad%C3%B6fjaads"),
        pytest.param("__pid”~n.log.-sadöfjaads", "__pid%E2%80%9D~n.log.-sad%C3%B6fjaads"),
        pytest.param("!?=pid.log.-sadöfjaads", "%21%3F%3Dpid.log.-sad%C3%B6fjaads"),
        pytest.param("!?=pid.ñlog.-sadöfjaads", "%21%3F%3Dpid.%C3%B1log.-sad%C3%B6fjaads"),
        pytest.param("!?=pid.ñlo/g.-sadöfjaads", "%21%3F%3Dpid.%C3%B1lo%2Fg.-sad%C3%B6fjaads"),
        pytest.param("!?=pid.ñlog.-sadöfjaads", "%21%3F%3Dpid.%C3%B1log.-sad%C3%B6fjaads"),
    ],
)
def test_key_sanitation(agent_storage, key, expected_safe_key):
    assert agent_storage._sanitize_key(key) == expected_safe_key


@pytest.mark.parametrize(
    "key_name",
    [
        pytest.param("pid.log.-sad?/&fjaads" * 11, id="key name too long"),
    ],
)
def test_invalid_key_name(agent_storage, key_name):
    value = "slash test"
    with pytest.raises(ValueError):
        agent_storage.write(key_name, value)
