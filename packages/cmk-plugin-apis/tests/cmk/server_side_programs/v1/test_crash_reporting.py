#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import base64
import json
from pathlib import Path

import pytest

from cmk.server_side_programs.v1_unstable import report_agent_crashes

TEST_AGENT = "test_agent"
TEST_HOST = "test_host"


@pytest.fixture
def fixed_path(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    monkeypatch.setenv("SERVER_SIDE_PROGRAM_CRASHES_PATH", str(tmp_path))
    return tmp_path


def test_crash_reported_for_exception(monkeypatch: pytest.MonkeyPatch, fixed_path: Path) -> None:
    monkeypatch.setattr("time.time", lambda: 10.0)

    # check sanity of setup
    assert not list(fixed_path.iterdir())

    @report_agent_crashes("smith", "3.14.15p92")
    def main() -> int:
        raise ValueError("test exception")

    _ = main()

    (crash_dir,) = (fixed_path / "agent").iterdir()

    match json.loads((crash_dir / "crash.info").read_text()):
        case {
            "crash_id": str(),
            "crash_type": "agent",
            "exc_type": "ValueError",
            "exc_value": "test exception",
            "exc_traceback": list(),
            "local_vars": str(),
            "details": {
                "program_type": "agent",
                "program_name": "smith",
            },
            "core": "N/A",
            "python_version": str(),
            "edition": "N/A",
            "python_paths": list(),
            "version": "3.14.15p92",
            "time": 10.0,
            "os": "N/A",
            **additional_values,
        }:
            assert not additional_values
        case _other:
            assert False, repr(_other)


def test_no_crash_reported_for_missing_env(
    monkeypatch: pytest.MonkeyPatch, fixed_path: Path
) -> None:
    monkeypatch.delenv("SERVER_SIDE_PROGRAM_CRASHES_PATH")

    @report_agent_crashes("smith", "3.14.15p92")
    def main() -> int:
        raise ValueError("test exception")

    with pytest.raises(ValueError):
        main()

    assert not list(fixed_path.iterdir())


@pytest.mark.parametrize("exitcode", (0, 1))
def test_no_crash_reported_return(fixed_path: Path, exitcode: int) -> None:
    @report_agent_crashes("smith", "3.14.15p92")
    def main() -> int:
        return exitcode

    _ = main()

    assert not list(fixed_path.iterdir())


def test_type_info_preserved() -> None:
    @report_agent_crashes("smith", "3.14.15p92")
    def main(_a: str) -> int:
        return 42

    # We test that we need suppressions here:
    _r1 = main(23)  # type: ignore[arg-type]
    _r2: str = main("hello")  # type: ignore[assignment]


def test_crash_report_masks_secrets(fixed_path: Path) -> None:
    @report_agent_crashes("smith", "3.14.15p92")
    def main() -> int:
        _moo = {"passphrase": "pedo mellon a minno.", "foo": "bar"}
        _secret = "s3cr37"
        raise ValueError("test exception")

    _ = main()
    (crash_dir,) = (fixed_path / "agent").iterdir()

    local_vars = base64.b64decode(json.loads((crash_dir / "crash.info").read_text())["local_vars"])
    assert (
        local_vars == b"{'_moo': {'foo': 'bar', 'passphrase': 'redacted'}, '_secret': 'redacted'}"
    )
