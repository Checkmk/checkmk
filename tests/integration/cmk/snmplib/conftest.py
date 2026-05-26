#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"
# mypy: disable-error-code="no-untyped-def"
# mypy: disable-error-code="type-arg"

from __future__ import annotations

import asyncio
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
from pysnmp.hlapi.asyncio import (  # type: ignore[attr-defined]
    CommunityData,
    ContextData,
    get_cmd,
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
from tests.testlib.common.utils2 import is_containerized
from tests.testlib.site import Site

TIMEOUT_AFTER = 120  # seconds
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

    # Run the SNMP simulator as site user.
    # Don't run it as this user when running inside Kubernetes.
    as_user = None if is_containerized() else site.id

    # In the CI the tests are started as root and snmpsimd needs to be started as
    # "testuser" user. We need to provide a tmp path which is writable by that user.
    with TemporaryDirectory(prefix="snmpsim_") as d:
        if as_user:
            shutil.chown(d, as_user, as_user)

        process_definitions = [
            _define_process(idx, auth, Path(d), snmp_data_dir, as_user)
            for idx, auth in enumerate(_create_auth_list())
        ]

        try:
            for process_def in process_definitions:
                wait_until(lambda: _is_listening(process_def), timeout=TIMEOUT_AFTER, interval=1)

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


def _define_process(index, auth, tmp_path, snmp_data_dir, as_user: None | str) -> ProcessDef:
    port = 1337 + index

    proc_tmp_path = tmp_path / f"snmpsim{index}"
    proc_tmp_path.mkdir(parents=True, exist_ok=True)

    command_prefix = []
    if as_user:
        command_prefix = ["sudo", "-u", as_user]
        shutil.chown(proc_tmp_path, as_user, as_user)

    env_override = None
    if os.geteuid() == 0:
        # As a root user we have to pass a special flag to snmpsim in order to be able to run it as root.
        # Hint: the SNMP Simulator changelog mentions the flag SNMP_ALLOW_ROOT, but the code actually checks for SNMPSIM_ALLOW_ROOT
        env_override = {"SNMPSIM_ALLOW_ROOT": "true"}
        # Extend the environment with variables required by snmpsim
        env_override.update({key: os.environ[key] for key in ("HOME",)})
        logger.debug(f"overriding snmpsim-command-responder process env with: {env_override!r}")

    return ProcessDef(
        with_sudo=bool(as_user),
        port=port,
        process=subprocess.Popen(
            command_prefix
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
            env=env_override,
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


def _is_listening(process_def: ProcessDef) -> bool:
    p = process_def.process
    port = process_def.port
    exitcode = p.poll()
    snmpsimd_died = exitcode is not None
    if snmpsimd_died:
        logger.error(
            "============================================="
            " snmpsimd dead from the beginning (exit code %d)",
            exitcode,
        )

        # stderr is piped to stdout, so we can rely on only showing stdout
        for line in p.stdout or []:
            logger.error(line)

    process = _snmpsimd_process(process_def)
    snmpsimd_proc_found = process is not None

    if not snmpsimd_proc_found:
        logger.error("Did not detect actual snmpsim-command process")
        return False

    num_sockets = 0

    if not snmpsimd_died:
        pid = process.pid  # type: ignore[union-attr]
        logger.debug("============================================= %d", pid)
        # Wait for snmpsimd to initialize the UDP sockets
        try:
            os.system("ls -al /proc/%d/fd" % pid)
            os.system("ps -ef | grep %d" % pid)
            socket_dir = Path("/proc/%d/fd" % pid)
            for filename in os.listdir(socket_dir):
                filepath = socket_dir / filename
                try:
                    if os.readlink(filepath).startswith("socket:"):
                        num_sockets += 1
                except OSError as socket_read_error:
                    logger.debug("Failed to read %s: %s", filepath, socket_read_error)
        except OSError as oserr:
            exitcode = p.poll()
            if exitcode is None:
                raise
            snmpsimd_died = True
            logger.error(
                "====================================snmpsimd dead OSError try-except %s", oserr
            )

    if snmpsimd_died:
        # assert p.stdout is not None
        # output = p.stdout.read()
        output = "foobar"
        raise RuntimeError(f"snmpsimd died. Exit code: {exitcode}; output: {output}")

    logger.debug("snmpsimd is running")

    if (not is_containerized()) and num_sockets < 2:
        # For Kubernetes the socket check might fail due to missing permissions.
        # We assume the responder is up and running with the correct amount of sockets there.
        logger.debug("not enough open sockets")
        return False

    logger.debug("snmpsimd has opened it's sockets")

    def _snmp_response_is_available() -> bool:
        # We got the expected number of listen sockets. One for IPv4 and one for IPv6. Now test
        # whether or not snmpsimd is already answering.
        transport_target = wait_sync(UdpTransportTarget.create(("127.0.0.1", port)))
        g = wait_sync(
            get_cmd(
                SnmpEngine(),
                CommunityData("public"),
                transport_target,
                ContextData(),
                ObjectType(ObjectIdentity("SNMPv2-MIB", "sysDescr", 0)),
            )
        )
        _error_indication, _error_status, _error_index, var_binds = g
        try:
            logger.debug("SNMP get response")
            logger.debug(repr((_error_indication, _error_status, _error_index, var_binds)))
            assert len(var_binds) == 1
            logger.debug(var_binds[0][1].prettyPrint())
            assert (
                var_binds[0][1].prettyPrint()
                == "Linux zeus 4.8.6.5-smp #2 SMP Sun Nov 13 14:58:11 CDT 2016 i686"
            )
        except (AssertionError, IndexError):
            return False
        return True

    try:
        wait_until(_snmp_response_is_available, timeout=TIMEOUT_AFTER // 2, interval=1)
    except TimeoutError:
        return False
    return True


# To help with async APIs from pysnmp.
def wait_sync(coro):
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    else:
        return loop.run_until_complete(coro)


def _snmpsimd_process(process_def: ProcessDef) -> psutil.Process | None:
    try:
        if process_def.with_sudo:
            proc = psutil.Process(process_def.process.pid)
            for child in (children := proc.children(recursive=True)):
                if "snmpsim-command" in child.name():
                    return child

                for cmdline_part in child.cmdline():
                    if "snmpsim-command" in cmdline_part:
                        return child

            logger.debug("Did not find snmpsim-command in children %r", children)
            return None
        return psutil.Process(process_def.process.pid)
    except psutil.NoSuchProcess:
        logger.exception("No such process", exc_info=True)
        return None


@pytest.fixture(name="backend_type", params=SNMPBackendEnum)
def backend_type_fixture(
    site: Site, request: pytest.FixtureRequest, snmpsim: None
) -> SNMPBackendEnum:
    backend_type: SNMPBackendEnum = request.param
    if site.edition.is_community_edition() and backend_type is SNMPBackendEnum.INLINE:
        return pytest.skip("Commercial editions only")
    return backend_type


@pytest.fixture(name="backend_type_dockerized")
def backend_type_dockerized_fixture(backend_type: SNMPBackendEnum) -> SNMPBackendEnum:
    if backend_type is SNMPBackendEnum.STORED_WALK and not is_containerized():
        pytest.skip("Allow only dockerized runs!")
    return backend_type
