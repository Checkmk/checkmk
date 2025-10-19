#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from pathlib import Path

import pytest

from cmk.server_side_programs.v1_unstable import Storage

TEST_AGENT = "test_agent"
TEST_HOST = "test_host"


@pytest.fixture(autouse=True)
def patch_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("SERVER_SIDE_PROGRAM_STORAGE_PATH", str(tmp_path))


class TestStorage:
    @pytest.mark.parametrize(
        "program_ident,host",
        [
            pytest.param("pid.log.cache.json", "pid.log.cache.json"),
            pytest.param("pid.log_cache.json", "pid.log_cache.json"),
            pytest.param("pid.log-cache.json", "pid.log-cache.json"),
            pytest.param("pid.log123-7412cache.json", "pid.log123-7412cache.json"),
            pytest.param(
                "7d160171-a52a-43d0-b43c-644540aad7ec",
                "7d160171-a52a-43d0-b43c-644540aad7ec",
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
    def test_init(self, program_ident: str, host: str) -> None:
        _ = Storage(program_ident, host)

    def test_write_read(self) -> None:
        test_data = {
            "pid.log.cache.json": "1",
            "pid.log_cache.json": "2",
            "pid.log-cache.json": "3",
            "pid.log123-7412cache.json": "4",
            "7d160171-a52a-43d0-b43c-644540aad7ec": "5",
            "pid.log.-sad?/&fjaads": "6",
            "pid.lo__-sadöfjaads": "7",
            "__pid”~n.log.-sadöfjaads": "8",
            "!?=pid.log.-sadöfjaads": "9",
            "!?=pid.ñlog.-sadöfjaads": "10",
            "!?=pid.ñlo/g.-sadöfjaads": "11",
        }
        storage = Storage(TEST_AGENT, TEST_HOST)
        for key, value in test_data.items():
            storage.write(key, value)

        # new instance to make sure it is not just stored in the instance.
        storage = Storage(TEST_AGENT, TEST_HOST)
        expected = {**test_data, "non_existent_key": "default"}
        for key, expected_value in expected.items():
            assert storage.read(key, "default") == expected_value

    def test_unset(self) -> None:
        storage = Storage(TEST_AGENT, TEST_HOST)
        value = "hello, persistent world"
        storage.write("key", value)
        assert storage.read("key", None) == value
        storage.unset("key")
        assert storage.read("key", None) is None

    def test_read_nonexistent_returns_default(self) -> None:
        storage = Storage(TEST_AGENT, TEST_HOST)
        result = storage.read("does_not_exist", "default")
        assert result == "default"

    def test_key_too_long(self) -> None:
        storage = Storage(TEST_AGENT, TEST_HOST)
        with pytest.raises(ValueError):
            storage.write("X" * 256, "value")
