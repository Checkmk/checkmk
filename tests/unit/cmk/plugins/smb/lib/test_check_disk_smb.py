#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Final

import pytest

from cmk.plugins.smb.lib.check_disk_smb import ErrorResult, main, SMBShare


class _SMBShareDiskUsageOK:
    def __init__(self, mountpoint: str, available_bytes: int, total_bytes: int) -> None:
        self.mountpoint: Final = mountpoint
        self.available_bytes: Final = available_bytes
        self.total_bytes: Final = total_bytes

    def __call__(
        self,
        *args: object,
        **kwargs: object,
    ) -> SMBShare:
        return SMBShare(
            mountpoint=self.mountpoint,
            available_bytes=self.available_bytes,
            total_bytes=self.total_bytes,
        )


class _SMBShareDiskUsageError:
    def __init__(self, state: int, summary: str) -> None:
        self.state: Final = state
        self.summary: Final = summary

    def __call__(
        self,
        *args: object,
        **kwargs: object,
    ) -> ErrorResult:
        return ErrorResult(
            state=self.state,
            summary=self.summary,
        )


def test_main_no_levels(capsys: pytest.CaptureFixture[str]) -> None:
    assert (
        main(
            ["share", "-u", "cratus", "--password", "some-pw", "-H", "hostname"],
            _SMBShareDiskUsageOK("\\\\hostname\\share", 1, 102400),
        )
        == 0
    )
    out, err = capsys.readouterr()
    assert out == "1 B (<0.01%) free on \\\\hostname\\share | 'share'=102399B;;;0;102400\n"
    assert not err


def test_main_ok_state(capsys: pytest.CaptureFixture[str]) -> None:
    assert (
        main(
            [
                "share",
                "--levels",
                "80",
                "90",
                "-u",
                "cratus",
                "--password",
                "some-pw",
                "-H",
                "hostname",
            ],
            _SMBShareDiskUsageOK("\\\\hostname\\share", 51200, 102400),
        )
        == 0
    )
    out, err = capsys.readouterr()
    assert (
        out
        == "50.0 KiB (50.00%) free on \\\\hostname\\share | 'share'=51200B;81920.0;92160.0;0;102400\n"
    )
    assert not err


def test_main_warn_state(capsys: pytest.CaptureFixture[str]) -> None:
    assert (
        main(
            [
                "share",
                "--levels",
                "80",
                "90",
                "-u",
                "cratus",
                "--password",
                "some-pw",
                "-H",
                "hostname",
            ],
            _SMBShareDiskUsageOK("\\\\hostname\\share", 20000, 102400),
        )
        == 1
    )
    out, err = capsys.readouterr()
    assert (
        out
        == "19.5 KiB (19.53%) free on \\\\hostname\\share | 'share'=82400B;81920.0;92160.0;0;102400\n"
    )
    assert not err


def test_main_crit_state(capsys: pytest.CaptureFixture[str]) -> None:
    assert (
        main(
            [
                "share",
                "--levels",
                "80",
                "90",
                "-u",
                "cratus",
                "--password",
                "some-pw",
                "-H",
                "hostname",
            ],
            _SMBShareDiskUsageOK("\\\\hostname\\share", 5600, 102400),
        )
        == 2
    )
    out, err = capsys.readouterr()
    assert (
        out
        == "5.47 KiB (5.47%) free on \\\\hostname\\share | 'share'=96800B;81920.0;92160.0;0;102400\n"
    )
    assert not err


def test_main_access_denied(capsys: pytest.CaptureFixture[str]) -> None:
    assert (
        main(
            [
                "share",
                "--levels",
                "80",
                "90",
                "-u",
                "cratus",
                "--password",
                "some-pw",
                "-H",
                "hostname",
            ],
            _SMBShareDiskUsageError(2, "Access denied"),
        )
        == 2
    )
    out, err = capsys.readouterr()
    assert out == "Access denied\n"
    assert not err


def test_main_unknown_error(capsys: pytest.CaptureFixture[str]) -> None:
    assert (
        main(
            [
                "sha",
                "--levels",
                "80",
                "90",
                "-u",
                "cratus",
                "--password",
                "some-pw",
                "-H",
                "hostname",
            ],
            _SMBShareDiskUsageError(3, "Result from smbclient not suitable"),
        )
        == 3
    )
    out, err = capsys.readouterr()
    assert out == "Result from smbclient not suitable\n"
    assert not err
