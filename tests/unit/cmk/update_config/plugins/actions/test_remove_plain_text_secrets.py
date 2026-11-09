#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

import pytest

from cmk.server_side_programs.v1 import Storage
from cmk.update_config.plugins.actions.remove_plain_text_secrets import RemovePlainTextSecrets

_HOST = "my host"


@pytest.fixture(name="base_path")
def fixture_base_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("SERVER_SIDE_PROGRAM_STORAGE_PATH", str(tmp_path))
    return tmp_path


@pytest.mark.parametrize(
    ("ident", "key"),
    [
        pytest.param("veeam", "token", id="veeam"),
    ],
)
def test_plain_text_secret_is_removed(base_path: Path, ident: str, key: str) -> None:
    Storage(ident, _HOST).write(key, "plain secret")

    RemovePlainTextSecrets.remove(base_path)

    assert Storage(ident, _HOST).read(key, None) is None


def test_other_values_are_kept(base_path: Path) -> None:
    Storage("veeam", _HOST).write("not_a_secret", "value")
    Storage("other_program", _HOST).write("token", "value")

    RemovePlainTextSecrets.remove(base_path)

    assert (
        Storage("veeam", _HOST).read("not_a_secret", None),
        Storage("other_program", _HOST).read("token", None),
    ) == ("value", "value")
