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

from testlib import wait_until

import cmk.utils.debug as debug
import cmk.utils.log as log
import cmk.utils.paths
import cmk.utils.snmp_cache as snmp_cache
import cmk.utils.snmp_table as snmp_table
from cmk.utils.exceptions import MKSNMPError
from cmk.utils.type_defs import (
    OID_BIN,
    OID_END,
    OID_END_BIN,
    OID_STRING,
    OIDWithColumns,
    SNMPHostConfig,
)

import cmk.base.snmp as snmp
from cmk.fetchers.snmp_backend import ClassicSNMPBackend, StoredWalkSNMPBackend

try:
    from cmk.fetchers.cee.snmp_backend.inline import InlineSNMPBackend
except ImportError:
    InlineSNMPBackend = None  # type: ignore[assignment, misc]

logger = logging.getLogger(__name__)


# Found no other way to achieve this
# https://github.com/pytest-dev/pytest/issues/363
@pytest.fixture(scope="module")
def monkeymodule(request):
    from _pytest.monkeypatch import MonkeyPatch  # type: ignore[import] # pylint: disable=import-outside-toplevel
    mpatch = MonkeyPatch()
    yield mpatch
    mpatch.undo()


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

    # Ensure that snmpsim is ready for clients before starting with the tests
    def is_listening():
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

        # Correct module is only available in the site
        import netsnmp  # type: ignore[import] # pylint: disable=import-error,import-outside-toplevel
        var = netsnmp.Varbind("sysDescr.0")
        result = netsnmp.snmpget(var, Version=2, DestHost="127.0.0.1:1337", Community="public")
        if result is None or result[0] is None:
            return False
        return True

    wait_until(is_listening, timeout=20)

    yield

    log.logger.setLevel(logging.INFO)
    debug.disable()

    logger.debug("Stopping snmpsimd...")
    p.terminate()
    p.wait()
    logger.debug("Stopped snmpsimd.")


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

    yield backend(config)

    # Restore global variable.
    cmk.utils.paths.snmpwalks_dir = snmpwalks_dir


@pytest.fixture(autouse=True)
def clear_cache(monkeypatch):
    monkeypatch.setattr(snmp_cache, "_g_single_oid_hostname", None)
    monkeypatch.setattr(snmp_cache, "_g_single_oid_ipaddress", None)
    monkeypatch.setattr(snmp_cache, "_g_single_oid_cache", {})


# Missing in currently used dump:
# 5 NULL
#68 - Opaque
@pytest.mark.parametrize("type_name,oid,expected_response", [
    ("Counter64", ".1.3.6.1.2.1.4.31.1.1.21.1", "15833452"),
    ("OCTET STRING", ".1.3.6.1.2.1.1.4.0", "SNMP Laboratories, info@snmplabs.com"),
    ("OBJECT IDENTIFIER", ".1.3.6.1.2.1.1.9.1.2.1", ".1.3.6.1.6.3.10.3.1.1"),
    ("IpAddress", ".1.3.6.1.2.1.3.1.1.3.2.1.195.218.254.97", "195.218.254.97"),
    ("Integer32", ".1.3.6.1.2.1.1.7.0", "72"),
    ("Counter32", ".1.3.6.1.2.1.5.1.0", "324"),
    ("Gauge32", ".1.3.6.1.2.1.6.9.0", "9"),
    ("TimeTicks", ".1.3.6.1.2.1.1.3.0", "449613886"),
])
def test_get_data_types(backend, type_name, oid, expected_response):
    response = snmp.get_single_oid(oid, backend=backend)
    assert response == expected_response
    assert isinstance(response, str)

    oid_start, oid_end = oid.rsplit(".", 1)
    table = snmp_table.get_snmp_table(
        check_plugin_name="",
        oid_info=(oid_start, [oid_end]),
        backend=backend,
    )

    assert table[0][0] == expected_response
    assert isinstance(table[0][0], str)


def test_get_simple_snmp_table_not_resolvable(backend):
    if backend.config.is_usewalk_host:
        pytest.skip("Not relevant")

    backend.config = backend.config.update(ipaddress="bla.local")
    oid_info = (
        ".1.3.6.1.2.1.1",
        ["1.0", "2.0", "5.0"],
    )  # type: OIDWithColumns

    # TODO: Unify different error messages
    if backend.config.is_inline_snmp_host:
        exc_match = "Failed to initiate SNMP"
    else:
        exc_match = "Unknown host"

    with pytest.raises(MKSNMPError, match=exc_match):
        snmp_table.get_snmp_table(
            check_plugin_name="",
            oid_info=oid_info,
            backend=backend,
        )


def test_get_simple_snmp_table_wrong_credentials(backend):
    if backend.config.is_usewalk_host:
        pytest.skip("Not relevant")

    backend.config = backend.config.update(credentials="dingdong")
    oid_info = (
        ".1.3.6.1.2.1.1",
        ["1.0", "2.0", "5.0"],
    )  # type: OIDWithColumns

    # TODO: Unify different error messages
    if backend.config.is_inline_snmp_host:
        exc_match = "SNMP query timed out"
    else:
        exc_match = "Timeout: No Response from"

    with pytest.raises(MKSNMPError, match=exc_match):
        snmp_table.get_snmp_table(
            check_plugin_name="",
            oid_info=oid_info,
            backend=backend,
        )


@pytest.mark.parametrize("bulk", [True, False])
def test_get_simple_snmp_table_bulkwalk(backend, bulk):
    backend.config = backend.config.update(is_bulkwalk_host=bulk)
    oid_info = (
        ".1.3.6.1.2.1.1",
        ["1.0", "2.0", "5.0"],
    )  # type: OIDWithColumns
    table = snmp_table.get_snmp_table(
        check_plugin_name="",
        oid_info=oid_info,
        backend=backend,
    )

    assert table == [
        [
            u'Linux zeus 4.8.6.5-smp #2 SMP Sun Nov 13 14:58:11 CDT 2016 i686',
            u'.1.3.6.1.4.1.8072.3.2.10',
            u'new system name',
        ],
    ]
    assert isinstance(table[0][0], str)


def test_get_simple_snmp_table(backend):
    oid_info = (
        ".1.3.6.1.2.1.1",
        ["1.0", "2.0", "5.0"],
    )  # type: OIDWithColumns
    table = snmp_table.get_snmp_table(
        check_plugin_name="",
        oid_info=oid_info,
        backend=backend,
    )

    assert table == [
        [
            u'Linux zeus 4.8.6.5-smp #2 SMP Sun Nov 13 14:58:11 CDT 2016 i686',
            u'.1.3.6.1.4.1.8072.3.2.10',
            u'new system name',
        ],
    ]
    assert isinstance(table[0][0], str)


def test_get_simple_snmp_table_oid_end(backend):
    oid_info = (
        ".1.3.6.1.2.1.2.2.1",
        ["1", "2", "3", OID_END],
    )  # type: OIDWithColumns
    table = snmp_table.get_snmp_table(
        check_plugin_name="",
        oid_info=oid_info,
        backend=backend,
    )

    assert table == [
        [u'1', u'lo', u'24', u'1'],
        [u'2', u'eth0', u'6', u'2'],
    ]


def test_get_simple_snmp_table_oid_string(backend):
    oid_info = (
        ".1.3.6.1.2.1.2.2.1",
        ["1", "2", "3", OID_STRING],
    )  # type: OIDWithColumns
    table = snmp_table.get_snmp_table(
        check_plugin_name="",
        oid_info=oid_info,
        backend=backend,
    )

    assert table == [
        [u'1', u'lo', u'24', u'.1.3.6.1.2.1.2.2.1.1.1'],
        [u'2', u'eth0', u'6', u'.1.3.6.1.2.1.2.2.1.1.2'],
    ]


def test_get_simple_snmp_table_oid_bin(backend):
    oid_info = (
        ".1.3.6.1.2.1.2.2.1",
        ["1", "2", "3", OID_BIN],
    )  # type: OIDWithColumns
    table = snmp_table.get_snmp_table(
        check_plugin_name="",
        oid_info=oid_info,
        backend=backend,
    )

    assert table == [
        [u'1', u'lo', u'24', u'\x01\x03\x06\x01\x02\x01\x02\x02\x01\x01\x01'],
        [u'2', u'eth0', u'6', u'\x01\x03\x06\x01\x02\x01\x02\x02\x01\x01\x02'],
    ]


def test_get_simple_snmp_table_oid_end_bin(backend):
    oid_info = (
        ".1.3.6.1.2.1.2.2.1",
        ["1", "2", "3", OID_END_BIN],
    )  # type: OIDWithColumns
    table = snmp_table.get_snmp_table(
        check_plugin_name="",
        oid_info=oid_info,
        backend=backend,
    )

    assert table == [
        [u'1', u'lo', u'24', u'\x01'],
        [u'2', u'eth0', u'6', u'\x02'],
    ]


def test_get_simple_snmp_table_with_hex_str(backend):
    oid_info = (
        ".1.3.6.1.2.1.2.2.1",
        [
            "6",
        ],
    )  # type: OIDWithColumns

    table = snmp_table.get_snmp_table(
        check_plugin_name="",
        oid_info=oid_info,
        backend=backend,
    )

    assert table == [
        [u''],
        [
            u'\x00\x12yb\xf9@',
        ],
    ]
