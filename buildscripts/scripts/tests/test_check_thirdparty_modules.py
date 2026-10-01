#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import base64
import hashlib
import json
from pathlib import Path

import pytest

from buildscripts.scripts.check_thirdparty_modules import main


def _sri(content: bytes) -> str:
    return "sha256-" + base64.b64encode(hashlib.sha256(content).digest()).decode()


def _make_module(registry: Path, name: str = "foo") -> Path:
    """A module whose source.json matches its overlay file and patch."""
    module_dir = registry / "modules" / name / "1.0.cmk.1"
    (module_dir / "overlay").mkdir(parents=True)
    (module_dir / "patches").mkdir()
    (module_dir / "overlay" / "BUILD.bazel").write_bytes(b"exports_files([])\n")
    (module_dir / "patches" / "0001-fix.patch").write_bytes(b"diff --git a/x b/x\n \n")
    (module_dir / "source.json").write_text(
        json.dumps(
            {
                "url": "https://example.com/foo.tar.gz",
                "overlay": {"BUILD.bazel": _sri(b"exports_files([])\n")},
                "patches": {"0001-fix.patch": _sri(b"diff --git a/x b/x\n \n")},
            }
        )
    )
    return module_dir


def test_matching_hashes_pass(tmp_path: Path) -> None:
    _make_module(tmp_path)

    assert main(["--registry", str(tmp_path)]) == 0


@pytest.mark.parametrize(
    "pinned_file",
    [
        pytest.param("overlay/BUILD.bazel", id="overlay file"),
        pytest.param("patches/0001-fix.patch", id="patch"),
    ],
)
def test_file_edited_after_hashing_is_reported(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], pinned_file: str
) -> None:
    module_dir = _make_module(tmp_path)
    (module_dir / pinned_file).write_bytes(b"edited\n")

    rc = main(["--registry", str(tmp_path)])

    assert rc == 1
    assert str(module_dir / pinned_file) in capsys.readouterr().out


def test_pinned_file_deleted_from_disk_is_reported(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    module_dir = _make_module(tmp_path)
    (module_dir / "patches" / "0001-fix.patch").unlink()

    rc = main(["--registry", str(tmp_path)])

    assert rc == 1
    assert f"{module_dir / 'patches' / '0001-fix.patch'}: listed in" in capsys.readouterr().out


@pytest.mark.parametrize(
    "unlisted_file",
    [
        pytest.param("overlay/defs.bzl", id="overlay file"),
        pytest.param("patches/0002-new.patch", id="patch"),
    ],
)
def test_file_missing_in_source_json_is_reported(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], unlisted_file: str
) -> None:
    module_dir = _make_module(tmp_path)
    (module_dir / unlisted_file).write_text("new\n")

    rc = main(["--registry", str(tmp_path)])

    assert rc == 1
    assert f"{module_dir / unlisted_file}: not listed" in capsys.readouterr().out
