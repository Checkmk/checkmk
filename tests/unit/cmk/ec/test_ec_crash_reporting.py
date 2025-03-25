#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

from cmk.ccc.crash_reporting import crash_report_registry, VersionInfo

from cmk.ec.crash_reporting import CrashReportStore, ECCrashReport


def test_ec_crash_report_registry() -> None:
    assert crash_report_registry["ec"] == ECCrashReport


def test_ec_crash_report_from_exception(tmp_path: Path) -> None:
    crashdir = tmp_path / "crash"
    try:
        raise ValueError("DING")
    except Exception:
        crash = ECCrashReport(
            crashdir,
            ECCrashReport.make_crash_info(
                VersionInfo(
                    core="test",
                    python_version="test",
                    edition="test",
                    python_paths=["foo", "bar"],
                    version="3.99",
                    time=0.0,
                    os="Foobuntu",
                )
            ),
        )
        CrashReportStore().save(crash)

    assert crash.type() == "ec"
    assert crash.crash_info["exc_value"] == "DING"
