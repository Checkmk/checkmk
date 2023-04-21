#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

import logging
import os
import subprocess
from collections.abc import Iterator
from pathlib import Path
from typing import assert_never, NamedTuple

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

from tests.testlib import is_enterprise_repo, wait_until
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
    port: int
    process: subprocess.Popen


@pytest.fixture(name="snmp_data_dir", scope="module")
def snmp_data_dir_fixture(request) -> Path:  # type:ignore[no-untyped-def]
    return Path(request.fspath.dirname) / "snmp_data"


@pytest.fixture(name="snmpsim", scope="module", autouse=True)
def snmpsim_fixture(
    site: Site, snmp_data_dir: Path, tmp_path_factory: pytest.TempPathFactory
) -> Iterator[None]:
    tmp_path = tmp_path_factory.getbasetemp()
    log.logger.setLevel(logging.DEBUG)
    debug.enable()

    process_definitions = [
        _define_process(idx, auth, tmp_path, snmp_data_dir)
        for idx, auth in enumerate(_create_auth_list())
    ]

    for process_def in process_definitions:
        wait_until(_create_listening_condition(process_def), timeout=20)

    yield

    log.logger.setLevel(logging.INFO)
    debug.disable()

    logger.debug("Stopping snmpsimd...")
    for process_def in process_definitions:
        process_def.process.terminate()
        process_def.process.wait()
    logger.debug("Stopped snmpsimd.")


def _define_process(index, auth, tmp_path, snmp_data_dir):
    port = 1337 + index
    return ProcessDef(
        port=port,
        process=subprocess.Popen(
            [
                "snmpsimd.py",
                "--log-level=error",
                "--cache-dir",
                # Each snmpsim instance needs an own cache directory otherwise
                # some instances occasionally crash
                str(tmp_path / "snmpsim%s") % index,
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

    if not snmpsimd_died:
        # Wait for snmpsimd to initialize the UDP sockets
        num_sockets = 0
        try:
            for e in os.listdir("/proc/%d/fd" % p.pid):
                try:
                    if os.readlink("/proc/%d/fd/%s" % (p.pid, e)).startswith("socket:"):
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
    assert len(list(g)) == 1
    return True


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
