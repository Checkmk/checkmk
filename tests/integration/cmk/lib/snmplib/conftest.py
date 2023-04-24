#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

import logging
import os
import shutil
import subprocess
from collections.abc import Iterator
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import assert_never, NamedTuple

import psutil
import pytest
from pysnmp.hlapi import (  # type: ignore[import]
    CommunityData,
    ContextData,
    getCmd,
    ObjectIdentity,
    ObjectType,
    SnmpEngine,
    UdpTransportTarget,
)

from tests.testlib import is_enterprise_repo, repo_path, wait_until
from tests.testlib.site import Site

import cmk.utils.debug as debug
import cmk.utils.log as log
import cmk.utils.paths
from cmk.utils.type_defs import HostName

import cmk.snmplib.snmp_cache as snmp_cache
from cmk.snmplib.type_defs import SNMPBackend, SNMPBackendEnum, SNMPHostConfig

from cmk.fetchers.snmp_backend import ClassicSNMPBackend, StoredWalkSNMPBackend

if is_enterprise_repo():
    from cmk.fetchers.cee.snmp_backend.inline import InlineSNMPBackend  # type: ignore[import]
else:
    InlineSNMPBackend = None  # type: ignore[assignment, misc]

logger = logging.getLogger(__name__)


class ProcessDef(NamedTuple):
    with_sudo: bool
    port: int
    process: subprocess.Popen


@pytest.fixture(name="snmp_data_dir", scope="session")
def snmp_data_dir_fixture() -> Path:
    return Path(__file__).parent / "snmp_data"


@pytest.fixture(name="snmpsim", scope="session")
def snmpsim_fixture(site: Site, snmp_data_dir: Path) -> Iterator[None]:
    log.logger.setLevel(logging.DEBUG)
    debug.enable()

    with_sudo = os.geteuid() == 0

    # In the CI the tests are started as root and snmpsimd needs to be started as
    # "jenkins" user. We need to provide a tmp path which is writable by that user.
    with TemporaryDirectory(prefix="snmpsim_") as d:
        if with_sudo:
            shutil.chown(d, "jenkins", "jenkins")

        process_definitions = [
            _define_process(idx, auth, Path(d), snmp_data_dir, with_sudo)
            for idx, auth in enumerate(_create_auth_list())
        ]

        try:
            for process_def in process_definitions:
                wait_until(_create_listening_condition(process_def), timeout=20)

            yield
        finally:
            log.logger.setLevel(logging.INFO)
            debug.disable()

            logger.debug("Stopping snmpsimd...")
            for process_def in process_definitions:
                p = _snmpsimd_process(process_def)
                if p:
                    p.terminate()
                process_def.process.wait()
            logger.debug("Stopped snmpsimd.")


def _define_process(index, auth, tmp_path, snmp_data_dir, with_sudo):
    port = 1337 + index

    # The tests are executed as root user in the containerized environmen, which snmpsimd does not
    # like. Switch the user context to the jenkins user to execute the daemon.
    # When executed on a dev system, we run as lower privileged user and don't have to switch the
    # context.
    sudo = ["sudo", "-u", "jenkins"] if with_sudo else []

    proc_tmp_path = tmp_path / f"snmpsim{index}"
    proc_tmp_path.mkdir(parents=True, exist_ok=True)
    if with_sudo:
        shutil.chown(proc_tmp_path, "jenkins", "jenkins")

    return ProcessDef(
        with_sudo=with_sudo,
        port=port,
        process=subprocess.Popen(
            sudo
            + [
                f"{repo_path()}/.venv/bin/snmpsimd.py",
                "--log-level=error",
                "--cache-dir",
                # Each snmpsim instance needs an own cache directory otherwise
                # some instances occasionally crash
                str(proc_tmp_path),
                # Explicitly set engine ID to make data-dir override builtin dirs
                # See https://snmplabs.thola.io/snmpsim/documentation/simulating-agents.html
                "--v3-engine-id=010203040505060809",
                # TODO: Fix port allocation to prevent problems with parallel tests
                # "--agent-unix-endpoint="
                "--agent-udpv4-endpoint=127.0.0.1:%s" % port,
                "--agent-udpv6-endpoint=[::1]:%s" % port,
                "--data-dir",
                snmp_data_dir,
            ]
            + auth,
            close_fds=True,
            # Capture output to return the error message for debugging purposes
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        ),
    )


def _create_auth_list():
    return [
        [
            "--v3-user=authOnlyUser",
            "--v3-auth-key=authOnlyUser",
            "--v3-auth-proto=MD5",
        ],
        [
            "--v3-user=md5desuser",
            "--v3-auth-key=md5password",
            "--v3-auth-proto=MD5",
            "--v3-priv-key=desencryption",
            "--v3-priv-proto=DES",
        ],
        [
            "--v3-user=noAuthNoPrivUser",
        ],
        [
            "--v3-user=shaaesuser",
            "--v3-auth-key=shapassword",
            "--v3-auth-proto=SHA",
            "--v3-priv-key=aesencryption",
            "--v3-priv-proto=AES",
        ],
        [
            "--v3-user=authPrivUser",
            "--v3-auth-key=A_long_authKey",
            "--v3-auth-proto=SHA512",
            "--v3-priv-key=A_long_privKey",
            "--v3-priv-proto=DES",
        ],
    ]


# This function is needed because Pylint raises these two error if
# you create a function depending on a loop variable inside the loop:
# W0631 (undefined-loop-variable), W0640 (cell-var-from-loop)
def _create_listening_condition(process_def):
    return lambda: _is_listening(process_def)


def _is_listening(process_def: ProcessDef) -> bool:
    p = process_def.process
    port = process_def.port
    exitcode = p.poll()
    snmpsimd_died = exitcode is not None

    process = _snmpsimd_process(process_def)
    if process is None:
        return False
    pid = process.pid

    if not snmpsimd_died:
        # Wait for snmpsimd to initialize the UDP sockets
        num_sockets = 0
        try:
            for e in os.listdir("/proc/%d/fd" % pid):
                try:
                    if os.readlink("/proc/%d/fd/%s" % (pid, e)).startswith("socket:"):
                        num_sockets += 1
                except OSError:
                    pass
        except OSError:
            exitcode = p.poll()
            if exitcode is None:
                raise
            snmpsimd_died = True
    if snmpsimd_died:
        assert p.stdout is not None and exitcode is not None
        output = p.stdout.read()
        raise Exception("snmpsimd died. Exit code: %d; output: %s" % (exitcode, output))

    if num_sockets < 2:
        return False

    # We got the expected number of listen sockets. One for IPv4 and one for IPv6. Now test
    # whether or not snmpsimd is already answering.
    g = getCmd(
        SnmpEngine(),
        CommunityData("public"),
        UdpTransportTarget(("127.0.0.1", port)),
        ContextData(),
        ObjectType(ObjectIdentity("SNMPv2-MIB", "sysDescr", 0)),
    )
    _error_indication, _error_status, _error_index, var_binds = next(g)
    assert len(var_binds) == 1
    assert (
        var_binds[0][1].prettyPrint()
        == "Linux zeus 4.8.6.5-smp #2 SMP Sun Nov 13 14:58:11 CDT 2016 i686"
    )
    return True


def _snmpsimd_process(process_def: ProcessDef) -> psutil.Process | None:
    if process_def.with_sudo:
        proc = psutil.Process(process_def.process.pid)
        if not (children := proc.children()):
            return None
        if children[0].name() != "snmpsimd.py":
            raise RuntimeError(f"Unexpected child processes: {children}")
        return children[0]
    return psutil.Process(process_def.process.pid)


@pytest.fixture(name="backend", params=SNMPBackendEnum)
def backend_fixture(request, snmp_data_dir):
    backend_type: SNMPBackendEnum = request.param
    backend: type[SNMPBackend] | None
    match backend_type:
        case SNMPBackendEnum.INLINE:
            backend = InlineSNMPBackend
        case SNMPBackendEnum.CLASSIC:
            backend = ClassicSNMPBackend
        case SNMPBackendEnum.STORED_WALK:
            backend = StoredWalkSNMPBackend
        case _:
            assert_never(backend_type)

    if backend is None:
        return pytest.skip("CEE feature only")

    config = SNMPHostConfig(
        is_ipv6_primary=False,
        ipaddress="127.0.0.1",
        hostname=HostName("localhost"),
        credentials="public",
        port=1337,
        # TODO: Use SNMPv2 over v1 for the moment
        is_bulkwalk_host=False,
        is_snmpv2or3_without_bulkwalk_host=True,
        bulk_walk_size_of=10,
        timing={},
        oid_range_limits={},
        snmpv3_contexts=[],
        character_encoding=None,
        snmp_backend=backend_type,
    )

    snmpwalks_dir = cmk.utils.paths.snmpwalks_dir
    # Point the backend to the test walks shipped with the test file in git
    cmk.utils.paths.snmpwalks_dir = str(snmp_data_dir / "cmk-walk")

    assert snmp_data_dir.exists()
    assert (snmp_data_dir / "cmk-walk").exists()

    yield backend(config, logger)

    # Restore global variable.
    cmk.utils.paths.snmpwalks_dir = snmpwalks_dir
    return None


@pytest.fixture(autouse=True)
def clear_cache(monkeypatch):
    monkeypatch.setattr(snmp_cache, "_g_single_oid_hostname", None)
    monkeypatch.setattr(snmp_cache, "_g_single_oid_ipaddress", None)
    monkeypatch.setattr(snmp_cache, "_g_single_oid_cache", {})
