#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import subprocess
from collections.abc import Callable, Mapping, Sequence
from typing import Final

import pytest

from cmk.notification_plugins.spectrum import main
from cmk.testlib.notification_plugins import exit_code, explicit_password

BASE_OID: Final = "1.3.6.1.4.1.1234"

SERVICE_CONTEXT: Final = {
    "WHAT": "SERVICE",
    "NOTIFICATIONTYPE": "PROBLEM",
    "MONITORING_HOST": "monitoring.lan",
    "OMD_SITE": "mysite",
    "HOSTNAME": "myhost",
    "HOSTADDRESS": "10.0.0.1",
    "HOSTGROUPNAMES": "linux",
    "HOSTURL": "/view?host=myhost",
    "SERVICEDESC": "CPU load",
    "SERVICESTATE": "CRITICAL",
    "SERVICEOUTPUT": 'Load "very" high',
    "SERVICEGROUPNAMES": "cpu",
    "SERVICEURL": "/view?service=cpu",
    "PARAMETER_DESTINATION": "spectrum.lan",
    **explicit_password("PARAMETER_COMMUNITY", "public"),
}

HOST_CONTEXT: Final = {
    **{k: v for k, v in SERVICE_CONTEXT.items() if not k.startswith("SERVICE")},
    "WHAT": "HOST",
    "HOSTSTATE": "DOWN",
    "HOSTOUTPUT": "Host unreachable",
}


class FakeSnmptrap:
    def __init__(self) -> None:
        self.returncode = 0
        self.commands: list[Sequence[str]] = []

    def run(self, cmd: Sequence[str], **_kwargs: object) -> subprocess.CompletedProcess[bytes]:
        self.commands.append(cmd)
        return subprocess.CompletedProcess(args=cmd, returncode=self.returncode)


@pytest.fixture(name="snmptrap")
def fixture_snmptrap(monkeypatch: pytest.MonkeyPatch) -> FakeSnmptrap:
    fake = FakeSnmptrap()
    monkeypatch.setattr(subprocess, "run", fake.run)
    return fake


def _varbinds(cmd: Sequence[str]) -> dict[str, tuple[str, str]]:
    # Everything after the fixed 11 trap header arguments are (oid, type, value) triples.
    tail = cmd[11:]
    return {tail[i]: (tail[i + 1], tail[i + 2]) for i in range(0, len(tail), 3)}


def test_service_trap_command(
    snmptrap: FakeSnmptrap, notify_context: Callable[[Mapping[str, str]], None]
) -> None:
    notify_context(SERVICE_CONTEXT)

    exit_code(main)

    assert snmptrap.commands == [
        [
            "/usr/bin/snmptrap",
            "-v",
            "1",
            "-c",
            "public",
            "spectrum.lan",
            "1.3.6.1.4.1.100.1.2.3",
            "172.25.221.23",
            "6",
            "1",
            '""',
            f"{BASE_OID}.1",
            "s",
            '"monitoring.lan"',
            f"{BASE_OID}.2",
            "s",
            '"myhost"',
            f"{BASE_OID}.3",
            "s",
            '"10.0.0.1"',
            f"{BASE_OID}.4",
            "s",
            '"linux"',
            f"{BASE_OID}.5",
            "s",
            '"CPU load"',
            f"{BASE_OID}.6",
            "s",
            '"CRITICAL"',
            f"{BASE_OID}.7",
            "s",
            '"Load  very  high"',
            f"{BASE_OID}.8",
            "s",
            '"HARD"',
            f"{BASE_OID}.9",
            "s",
            '"CPU load"',
            f"{BASE_OID}.10",
            "i",
            "3",
            f"{BASE_OID}.11",
            "s",
            '"Call number 123456"',
            f"{BASE_OID}.12",
            "s",
            '"https://monitoring.lan/mysite/view?service=cpu"',
            f"{BASE_OID}.13",
            "s",
            '"CPU load alarm on host myhost"',
            f"{BASE_OID}.14",
            "s",
            '"cpu"',
        ]
    ]


def test_host_trap_falls_back_to_host_values(
    snmptrap: FakeSnmptrap, notify_context: Callable[[Mapping[str, str]], None]
) -> None:
    notify_context(HOST_CONTEXT)

    exit_code(main)

    varbinds = _varbinds(snmptrap.commands[0])
    assert {suffix: varbinds[f"{BASE_OID}.{suffix}"][1] for suffix in (5, 6, 7, 12, 13, 14)} == {
        5: '"Connectivity"',
        6: '"DOWN"',
        7: '"Host unreachable"',
        12: '"https://monitoring.lan/mysite/view?host=myhost"',
        13: '"Connectivity alarm on host myhost"',
        14: '""',
    }


def test_url_without_site(
    snmptrap: FakeSnmptrap, notify_context: Callable[[Mapping[str, str]], None]
) -> None:
    notify_context({k: v for k, v in HOST_CONTEXT.items() if k != "OMD_SITE"})

    exit_code(main)

    assert _varbinds(snmptrap.commands[0])[f"{BASE_OID}.12"] == (
        "s",
        '"https://monitoring.lan/view?host=myhost"',
    )


def test_configured_base_oid(
    snmptrap: FakeSnmptrap, notify_context: Callable[[Mapping[str, str]], None]
) -> None:
    notify_context({**SERVICE_CONTEXT, "PARAMETER_BASEOID": "1.2.3"})

    exit_code(main)

    assert list(_varbinds(snmptrap.commands[0])) == [f"1.2.3.{n}" for n in range(1, 15)]


@pytest.mark.parametrize("returncode", [0, 1])
def test_exit_code_is_snmptrap_exit_code(
    snmptrap: FakeSnmptrap,
    notify_context: Callable[[Mapping[str, str]], None],
    returncode: int,
) -> None:
    snmptrap.returncode = returncode
    notify_context(SERVICE_CONTEXT)

    assert exit_code(main) == returncode


def test_command_is_logged(
    snmptrap: FakeSnmptrap,
    notify_context: Callable[[Mapping[str, str]], None],
    capsys: pytest.CaptureFixture[str],
) -> None:
    notify_context(SERVICE_CONTEXT)

    exit_code(main)

    assert capsys.readouterr().err == repr(snmptrap.commands[0])
