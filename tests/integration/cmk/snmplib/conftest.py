#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
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
from typing import NamedTuple

import psutil
import pytest
from pysnmp.hlapi import (  # type: ignore[import-untyped]
    CommunityData,
    ContextData,
    getCmd,
    ObjectIdentity,
    ObjectType,
    SnmpEngine,
    UdpTransportTarget,
)

from cmk.ccc import debug
from cmk.snmplib import SNMPBackendEnum
from cmk.utils import log

from tests.testlib.common.repo import repo_path
from tests.testlib.common.utils import wait_until
from tests.testlib.site import Site

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
    # "testuser" user. We need to provide a tmp path which is writable by that user.
    with TemporaryDirectory(prefix="snmpsim_") as d:
        if with_sudo:
            shutil.chown(d, "testuser", "testuser")

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
                process_def.process.wait(36)
            logger.debug("Stopped snmpsimd.")


def _define_process(index, auth, tmp_path, snmp_data_dir, with_sudo):
    port = 1337 + index

    # The tests are executed as root user in the containerized environment, which snmpsimd does not
    # like. Switch the user context to 'testuser' to execute the daemon.
    # When executed on a dev system, we run as lower privileged user and don't have to switch the
    # context.
    sudo = ["sudo", "-u", "testuser"] if with_sudo else []

    proc_tmp_path = tmp_path / f"snmpsim{index}"
    proc_tmp_path.mkdir(parents=True, exist_ok=True)
    if with_sudo:
        shutil.chown(proc_tmp_path, "testuser", "testuser")

    return ProcessDef(
        with_sudo=with_sudo,
        port=port,
        process=subprocess.Popen(
            sudo
            + [
                f"{repo_path()}/.venv/bin/snmpsim-command-responder",
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
        [
            "--v3-user=authPrivUser",
            "--v3-auth-key=A_long_authKey",
            "--v3-auth-proto=SHA512",
            "--v3-priv-key=A_long_privKey",
            "--v3-priv-proto=AES256",
        ],
        [
            "--v3-user=authPrivUser",
            "--v3-auth-key=A_long_authKey",
            "--v3-auth-proto=SHA512",
            "--v3-priv-key=A_long_privKey",
            "--v3-priv-proto=AES192",
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
    if snmpsimd_died:
        logger.error(
            "=============================================snmpsimd dead from the beginning"
        )
    process = _snmpsimd_process(process_def)
    snmpsimd_proc_found = process is not None

    if not snmpsimd_proc_found:
        logger.error("Did not detect actual snmpsim-command process")
        return False

    num_sockets = 0

    if not snmpsimd_died:
        pid = process.pid  # type: ignore[union-attr]
        # Wait for snmpsimd to initialize the UDP sockets
        try:
            logger.debug("============================================= %d", pid)
            os.system("ls -al /proc/%d/fd" % pid)
            os.system("ps -ef | grep %d" % pid)
            for e in os.listdir("/proc/%d/fd" % pid):
                try:
                    if os.readlink("/proc/%d/fd/%s" % (pid, e)).startswith("socket:"):
                        num_sockets += 1
                except OSError:
                    pass
        except OSError as e:
            exitcode = p.poll()
            if exitcode is None:
                raise
            snmpsimd_died = True
            logger.error(
                "====================================snmpsimd dead OSError try-except %s", e
            )

    if snmpsimd_died:
        # assert p.stdout is not None
        # output = p.stdout.read()
        output = "foobar"
        raise Exception(f"snmpsimd died. Exit code: {exitcode}; output: {output}")

    logger.debug("snmpsimd is running")

    if num_sockets < 2:
        return False

    logger.debug("snmpsimd has opened it's sockets")

    # We got the expected number of listen sockets. One for IPv4 and one for IPv6. Now test
    # whether or not snmpsimd is already answering.
    g = getCmd(
        SnmpEngine(),
        CommunityData("public"),
        UdpTransportTarget(("127.0.0.1", port)),
        ContextData(),
        ObjectType(ObjectIdentity("SNMPv2-MIB", "sysDescr", 0)),
    )
    _error_indication, _error_status, _error_index, var_binds = g
    logger.debug("SNMP get response")
    logger.debug(repr((_error_indication, _error_status, _error_index, var_binds)))
    assert len(var_binds) == 1
    logger.debug(var_binds[0][1].prettyPrint())
    assert (
        var_binds[0][1].prettyPrint()
        == "Linux zeus 4.8.6.5-smp #2 SMP Sun Nov 13 14:58:11 CDT 2016 i686"
    )
    return True


def _snmpsimd_process(process_def: ProcessDef) -> psutil.Process | None:
    try:
        if process_def.with_sudo:
            proc = psutil.Process(process_def.process.pid)
            for child in (children := proc.children(recursive=True)):
                if child.name().startswith("snmpsim-command"):
                    return child
            logger.debug("Did not find snmpsim-command in children %r", children)
            return None
        return psutil.Process(process_def.process.pid)
    except psutil.NoSuchProcess:
        logger.exception("No such process", exc_info=True)
        return None


@pytest.fixture(name="backend_type", params=SNMPBackendEnum)
def backend_type_fixture(site: Site, request: pytest.FixtureRequest) -> SNMPBackendEnum:
    backend_type: SNMPBackendEnum = request.param
    if site.edition.is_raw_edition() and backend_type is SNMPBackendEnum.INLINE:
        return pytest.skip("CEE feature only")
    return backend_type
