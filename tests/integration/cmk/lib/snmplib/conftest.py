#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
import os
import subprocess
from pathlib import Path

import pytest  # type: ignore[import]

from testlib import wait_until  # type: ignore[import]

import cmk.utils.debug as debug
import cmk.utils.log as log
import cmk.utils.paths

import cmk.snmplib.snmp_cache as snmp_cache
from cmk.snmplib.type_defs import SNMPHostConfig

from cmk.fetchers.snmp_backend import ClassicSNMPBackend, StoredWalkSNMPBackend

try:
    from cmk.fetchers.cee.snmp_backend.inline import InlineSNMPBackend
except ImportError:
    InlineSNMPBackend = None  # type: ignore[assignment, misc]

logger = logging.getLogger(__name__)


@pytest.fixture(name="snmp_data_dir", scope="module")
def snmp_data_dir_fixture(request):
    return Path(request.fspath.dirname) / "snmp_data"


@pytest.fixture(name="snmpsim", scope="module", autouse=True)
def snmpsim_fixture(site, snmp_data_dir, tmp_path_factory):
    tmp_path = tmp_path_factory.getbasetemp()
    log.logger.setLevel(logging.DEBUG)
    debug.enable()
    cmd = [
        "snmpsimd.py",
        #"--log-level=error",
        "--cache-dir",
        str(tmp_path / "snmpsim"),
        "--data-dir",
        str(snmp_data_dir),
        # TODO: Fix port allocation to prevent problems with parallel tests
        #"--agent-unix-endpoint="
        "--agent-udpv4-endpoint=127.0.0.1:1337",
        "--agent-udpv6-endpoint=[::1]:1337",
        "--v3-user=authOnlyUser",
        "--v3-auth-key=authOnlyUser",
        "--v3-auth-proto=MD5",
    ]

    p = subprocess.Popen(
        cmd,
        close_fds=True,
        # Silence the very noisy output. May be useful to enable this for debugging tests
        #stdout=open(os.devnull, "w"),
        #stderr=subprocess.STDOUT,
    )

    wait_until(lambda: _is_listening(p, 1337), timeout=20)

    yield

    log.logger.setLevel(logging.INFO)
    debug.disable()

    logger.debug("Stopping snmpsimd...")
    p.terminate()
    p.wait()
    logger.debug("Stopped snmpsimd.")


def _is_listening(p, port):
    exitcode = p.poll()
    if exitcode is not None:
        raise Exception("snmpsimd died. Exit code: %d" % exitcode)
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
        raise Exception("snmpsimd died. Exit code: %d" % exitcode)
    if num_sockets < 2:
        return False
    num_sockets = 0
    # Correct module is only available in the site
    import netsnmp  # type: ignore[import] # pylint: disable=import-error,import-outside-toplevel
    var = netsnmp.Varbind("sysDescr.0")
    result = netsnmp.snmpget(var, Version=2, DestHost="127.0.0.1:%s" % port, Community="public")
    if result is None or result[0] is None:
        return False
    return True


@pytest.fixture(name="backend",
                params=[ClassicSNMPBackend, StoredWalkSNMPBackend, InlineSNMPBackend])
def backend_fixture(request, snmp_data_dir):
    backend = request.param
    if backend is None:
        return pytest.skip("CEE feature only")

    config = SNMPHostConfig(
        is_ipv6_primary=False,
        ipaddress="127.0.0.1",
        hostname="localhost",
        credentials="public",
        port=1337,
        # TODO: Use SNMPv2 over v1 for the moment
        is_bulkwalk_host=False,
        is_snmpv2or3_without_bulkwalk_host=True,
        bulk_walk_size_of=10,
        timing={},
        oid_range_limits=[],
        snmpv3_contexts=[],
        character_encoding=None,
        is_usewalk_host=backend is StoredWalkSNMPBackend,
        is_inline_snmp_host=backend is InlineSNMPBackend,
        record_stats=False,
    )

    snmpwalks_dir = cmk.utils.paths.snmpwalks_dir
    # Point the backend to the test walks shipped with the test file in git
    cmk.utils.paths.snmpwalks_dir = str(snmp_data_dir / "cmk-walk")

    assert snmp_data_dir.exists()
    assert (snmp_data_dir / "cmk-walk").exists()

    yield backend(config, logger)

    # Restore global variable.
    cmk.utils.paths.snmpwalks_dir = snmpwalks_dir


@pytest.fixture(autouse=True)
def clear_cache(monkeypatch):
    monkeypatch.setattr(snmp_cache, "_g_single_oid_hostname", None)
    monkeypatch.setattr(snmp_cache, "_g_single_oid_ipaddress", None)
    monkeypatch.setattr(snmp_cache, "_g_single_oid_cache", {})
