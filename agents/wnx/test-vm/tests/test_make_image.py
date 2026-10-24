# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable
from dataclasses import replace
from pathlib import Path

import pytest
from make_image import BuildError, check_paths, Config, fill, parse_args, parse_expiry

_TOOLS = [
    *("--qemu", "bin/qemu-system-x86_64", "--qemu-img", "bin/qemu-img"),
    *("--bios", "share/qemu/bios-256k.bin", "--media", "file/downloaded"),
    *("--virtio-win", "virtio/downloaded"),
    *("--sql-iso", "sql/downloaded", "--sql-cu", "cu/downloaded", "--odbc", "odbc/downloaded"),
    *("--answer", "answer/autounattend-core.xml", "--first-logon", "guest/first-logon.ps1"),
    *("--install-mssql", "guest/install-mssql.ps1", "--verify", "guest/verify-image.ps1"),
]


def config(tmp_path: Path) -> Config:
    return replace(
        parse_args([*_TOOLS, "--out", str(tmp_path / "image.qcow2")]),
        media=tmp_path / "media.iso",
        sql_iso=tmp_path / "sql.iso",
    )


def test_user_paths_are_relative_to_the_bazel_run_working_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("BUILD_WORKING_DIRECTORY", str(tmp_path))

    result = parse_args([*_TOOLS, "--", "--out", "out/image.qcow2", "--work", "scratch"])

    assert (result.out, result.work) == (
        tmp_path / "out/image.qcow2",
        tmp_path / "scratch/test-vm-build-core",
    )


def test_work_dir_defaults_to_the_output_directory(tmp_path: Path) -> None:
    result = parse_args([*_TOOLS, "--out", str(tmp_path / "image.qcow2")])

    assert result.work == tmp_path / "test-vm-build-core"


def test_usable_paths_pass_the_check(tmp_path: Path) -> None:
    check_paths(config(tmp_path))


def test_existing_output_is_not_overwritten(tmp_path: Path) -> None:
    (tmp_path / "image.qcow2").touch()

    with pytest.raises(BuildError, match="exists; remove it first"):
        check_paths(config(tmp_path))


def test_output_in_a_missing_directory_is_refused(tmp_path: Path) -> None:
    missing = replace(config(tmp_path), out=tmp_path / "missing/image.qcow2")

    with pytest.raises(BuildError, match="is not a writable directory"):
        check_paths(missing)


# fmt: off
@pytest.mark.parametrize(
    "unusable",
    [
        pytest.param(lambda c, d: replace(c, out=d / "image,1.qcow2"), id="comma in the output"),
        pytest.param(lambda c, d: replace(c, work=d / "work:1"), id="colon in the work dir"),
        pytest.param(lambda c, d: replace(c, media=d / "eval:iso"), id="colon in the media"),
        pytest.param(lambda c, d: replace(c, sql_iso=d / "sql,iso"), id="comma in the SQL media"),
    ],
)
# fmt: on
def test_paths_qemu_cannot_take_are_refused(
    tmp_path: Path, unusable: Callable[[Config, Path], Config]
) -> None:
    with pytest.raises(BuildError, match="QEMU cannot take a path"):
        check_paths(unusable(config(tmp_path), tmp_path))


def test_templates_get_the_password_and_values() -> None:
    template = "pw=@@PASSWORD@@ name=@@IMAGE_NAME@@\r\n"

    result = fill(template, IMAGE_NAME="Core")

    assert result == "pw=QemuRunner1! name=Core\r\n"


def test_expiry_is_read_from_the_verification_output() -> None:
    output = "OK licence activated\nEVAL_EXPIRY=2027-04-21\nOK done\n"

    assert parse_expiry(output) == "2027-04-21"


def test_verification_output_without_expiry_has_none() -> None:
    assert parse_expiry("OK done\n") is None
