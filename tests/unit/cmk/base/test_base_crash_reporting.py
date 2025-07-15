#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

from cmk.ccc.crash_reporting import VersionInfo
from cmk.ccc.hostaddress import HostName

from cmk.base.errorhandling import CheckCrashReport, CheckDetails


def _check_generic_crash_info(crash):
    assert "details" in crash.crash_info

    for key, ty in {
        "crash_type": str,
        "time": float,
        "os": str,
        "version": str,
        "python_version": str,
        "python_paths": list,
        "exc_type": str,
        "exc_value": str,
        "exc_traceback": list,
        "local_vars": str,
    }.items():
        assert key in crash.crash_info
        assert isinstance(crash.crash_info[key], ty), (
            f"Key {key!r} has an invalid type {type(crash.crash_info[key])!r}"
        )


def test_check_crash_report_from_exception(tmp_path: Path) -> None:
    # Tautological test...
    crashdir = tmp_path / "crash"
    hostname = HostName("testhost")
    crash = None
    try:
        raise Exception("DING")
    except Exception:
        crash = CheckCrashReport(
            crashdir,
            CheckCrashReport.make_crash_info(
                VersionInfo(
                    time=0.0,
                    os="",
                    version="",
                    edition="",
                    core="",
                    python_version="",
                    python_paths=[],
                ),
                CheckDetails(
                    item="foo",
                    params={},
                    check_output="Output",
                    host=hostname,
                    is_cluster=False,
                    description="Uptime",
                    check_type="uptime",
                    manual_check=False,
                    uses_snmp=False,
                    inline_snmp=False,
                    enforced_service=False,
                ),
            ),
        )

    _check_generic_crash_info(crash)
    assert crash.type() == "check"
    assert crash.crash_info["exc_type"] == "Exception"
    assert crash.crash_info["exc_value"] == "DING"
