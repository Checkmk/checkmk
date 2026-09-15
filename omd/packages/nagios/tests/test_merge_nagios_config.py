#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import runpy
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).parent.parent / "merge-nagios-config.py"


def _merge(
    files: list[Path], monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> str:
    monkeypatch.setattr(sys, "argv", [str(SCRIPT), *map(str, files)])
    runpy.run_path(str(SCRIPT), run_name="__main__")
    return capsys.readouterr().out


def test_merged_config_lists_sources_and_annotates_lines(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    first = tmp_path / "first.cfg"
    first.write_text("# a comment\n\ncfg_file=a.cfg\n")
    second = tmp_path / "second.cfg"
    second.write_text("log_file=/var/log/nagios.log\n")

    out = _merge([first, second], monkeypatch, capsys)

    assert f"# {first}\n# {second}\n" in out
    assert out.endswith(
        f"# {first}:2\ncfg_file=a.cfg\n# {second}:0\nlog_file=/var/log/nagios.log\n"
    )


def test_backup_files_are_skipped(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    config = tmp_path / "main.cfg"
    config.write_text("value=1\n")
    backup = tmp_path / "main.cfg~"
    backup.write_text("value=old\n")

    out = _merge([config, backup], monkeypatch, capsys)

    assert "value=old" not in out
    assert str(backup) not in out


def test_continuation_lines_are_joined(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    config = tmp_path / "main.cfg"
    config.write_text("define command {\\\n  command_name check\\\n  command_line /bin/true\n}\n")

    out = _merge([config], monkeypatch, capsys)

    assert out.endswith(
        f"# {config}:2\ndefine command {{ command_name check   command_line /bin/true\n# {config}:3\n}}\n"
    )
