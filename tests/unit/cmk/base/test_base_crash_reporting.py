#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Mapping
from pathlib import Path

import pytest

from cmk.base.errorhandling import (
    CheckCrashReport,
    CheckDetails,
    create_check_crash_dump,
    create_section_crash_dump,
)
from cmk.ccc.hostaddress import HostName
from cmk.checkengine.helper_interface import AgentRawData
from cmk.checkengine.plugins import SectionName
from cmk.checkengine.snmplib import SNMPBackendEnum
from cmk.crash import make_crash_report_base_path, VersionInfo
from cmk.utils import paths
from tests.testlib.unit.fake_site import pop_crash_report_file


def _check_generic_crash_info(crash: CheckCrashReport) -> None:
    crash_info: Mapping[str, object] = crash.crash_info
    assert "details" in crash_info

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
        assert key in crash_info
        assert isinstance(crash_info[key], ty), (
            f"Key {key!r} has an invalid type {type(crash_info[key])!r}"
        )


def test_check_crash_report_from_exception(tmp_path: Path) -> None:
    # Tautological test...
    hostname = HostName("testhost")
    crash = None
    try:
        raise Exception("DING")
    except Exception:
        crash = CheckCrashReport(
            crash_report_base_path=make_crash_report_base_path(tmp_path),
            crash_info=CheckCrashReport.make_crash_info(
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


@pytest.mark.usefixtures("patch_omd_site")
def test_check_crash_dump_contains_the_given_agent_output() -> None:
    try:
        raise Exception("DING")
    except Exception:
        create_check_crash_dump(
            HostName("testhost"),
            "Uptime",
            plugin_name="uptime",
            plugin_kwargs={},
            is_cluster=False,
            is_enforced=False,
            snmp_backend=SNMPBackendEnum.CLASSIC,
            get_agent_output=lambda: AgentRawData(b"<<<uptime>>>\n123\n"),
        )

    assert pop_crash_report_file("check", "agent_output") == b"<<<uptime>>>\n123\n"


@pytest.mark.usefixtures("patch_omd_site")
def test_section_crash_dump_contains_the_given_agent_output() -> None:
    try:
        raise Exception("DING")
    except Exception:
        create_section_crash_dump(
            operation="parsing",
            section_name=SectionName("uptime"),
            section_content=[["123"]],
            host_name=HostName("testhost"),
            get_agent_output=lambda: AgentRawData(b"<<<uptime>>>\n123\n"),
        )

    assert pop_crash_report_file("section", "agent_output") == b"<<<uptime>>>\n123\n"


@pytest.mark.usefixtures("patch_omd_site")
def test_section_crash_dump_without_agent_output_attaches_none_even_if_a_cache_file_exists() -> (
    None
):
    paths.tcp_cache_dir.mkdir(parents=True, exist_ok=True)
    (paths.tcp_cache_dir / "testhost").write_bytes(b"<<<stale>>>\n")
    try:
        raise Exception("DING")
    except Exception:
        create_section_crash_dump(
            operation="parsing",
            section_name=SectionName("uptime"),
            section_content=[["123"]],
            host_name=HostName("testhost"),
            get_agent_output=lambda: None,
        )

    assert pop_crash_report_file("section", "agent_output") is None
