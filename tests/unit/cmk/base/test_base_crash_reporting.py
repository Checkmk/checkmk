#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.utils.hostaddress import HostName

from cmk.base.errorhandling import CheckCrashReport


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
        assert isinstance(crash.crash_info[key], ty), "Key {!r} has an invalid type {!r}".format(
            key,
            type(crash.crash_info[key]),
        )


@pytest.mark.usefixtures("patch_omd_site")
def test_check_crash_report_from_exception() -> None:
    hostname = HostName("testhost")
    crash = None
    try:
        raise Exception("DING")
    except Exception:
        crash = CheckCrashReport.from_exception(
            details={
                "check_output": "Output",
                "host": hostname,
                "is_cluster": False,
                "description": "Uptime",
                "check_type": "uptime",
                "inline_snmp": False,
                "enforced_service": False,
            },
            type_specific_attributes={},
        )

    _check_generic_crash_info(crash)
    assert crash.type() == "check"
    assert crash.crash_info["exc_type"] == "Exception"
    assert crash.crash_info["exc_value"] == "DING"
