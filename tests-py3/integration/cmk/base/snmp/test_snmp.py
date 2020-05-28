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
import six

from testlib import wait_until

import cmk.utils.debug as debug
import cmk.utils.log as log
import cmk.utils.paths
import cmk.utils.snmp_cache as snmp_cache
from cmk.utils.exceptions import MKGeneralException
from cmk.utils.type_defs import SNMPHostConfig

import cmk.base.snmp as snmp

logger = logging.getLogger(__name__)

# "netsnmp" python module (used for inline SNMP) and snmp commands (used for
# classic SNMP) are not available in the git environment. For the moment it
# does not make sense to build these tests as unit tests because we want to
# tests the whole chain from single SNMP actions in our modules to the faked
# SNMP device and back.


# Found no other way to achieve this
# https://github.com/pytest-dev/pytest/issues/363
@pytest.fixture(scope="module")
def monkeymodule(request):
    from _pytest.monkeypatch import MonkeyPatch  # type: ignore[import] # pylint: disable=import-outside-toplevel
    mpatch = MonkeyPatch()
    yield mpatch
    mpatch.undo()


@pytest.fixture(name="snmpsim", scope="module", autouse=True)
def snmpsim_fixture(site, request, tmp_path_factory):
    tmp_path = tmp_path_factory.getbasetemp()
    source_data_dir = Path(request.fspath.dirname) / "snmp_data"

    log.logger.setLevel(logging.DEBUG)
    debug.enable()
    cmd = [
        "snmpsimd.py",
        #"--log-level=error",
        "--cache-dir",
        str(tmp_path / "snmpsim"),
        "--data-dir",
        str(source_data_dir),
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
        if p.poll() is not None:
            raise Exception("snmpsimd died. Exit code: %d" % p.poll())

        num_sockets = 0
        try:
            for e in os.listdir("/proc/%d/fd" % p.pid):
                try:
                    if os.readlink("/proc/%d/fd/%s" % (p.pid, e)).startswith("socket:"):
                        num_sockets += 1
                except OSError:
                    pass
        except OSError:
            if p.poll() is None:
                raise
            raise Exception("snmpsimd died. Exit code: %d" % p.poll())

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


# Execute all tests for all SNMP backends
@pytest.fixture(name="snmp_config", params=["inline_snmp", "classic_snmp", "stored_snmp"])
def snmp_config_fixture(request, snmpsim, monkeypatch):
    backend_name = request.param

    if backend_name == "stored_snmp":
        source_data_dir = Path(request.fspath.dirname) / "snmp_data" / "cmk-walk"
        monkeypatch.setattr(cmk.utils.paths, "snmpwalks_dir", str(source_data_dir))

    return SNMPHostConfig(
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
        is_usewalk_host=backend_name == "stored_snmp",
        is_inline_snmp_host=backend_name == "inline_snmp",
        record_stats=False,
    )


@pytest.fixture(autouse=True)
def clear_cache(monkeypatch):
    monkeypatch.setattr(snmp_cache, "_g_single_oid_hostname", None)
    monkeypatch.setattr(snmp_cache, "_g_single_oid_ipaddress", None)
    monkeypatch.setattr(snmp_cache, "_g_single_oid_cache", {})


def test_get_single_oid_ipv6(snmp_config):
    if snmp_config.is_usewalk_host:
        pytest.skip("Not relevant")

    snmp_config = snmp_config.update(
        is_ipv6_primary=True,
        ipaddress="::1",
    )

    result = snmp.get_single_oid(snmp_config, ".1.3.6.1.2.1.1.1.0")
    assert result == "Linux zeus 4.8.6.5-smp #2 SMP Sun Nov 13 14:58:11 CDT 2016 i686"


def test_get_single_oid_snmpv3(snmp_config):
    if snmp_config.is_usewalk_host:
        pytest.skip("Not relevant")

    snmp_config = snmp_config.update(credentials=(
        'authNoPriv',
        'md5',
        'authOnlyUser',
        'authOnlyUser',
    ))

    result = snmp.get_single_oid(snmp_config, ".1.3.6.1.2.1.1.1.0")
    assert result == "Linux zeus 4.8.6.5-smp #2 SMP Sun Nov 13 14:58:11 CDT 2016 i686"


def test_get_single_oid_wrong_credentials(snmp_config):
    if snmp_config.is_usewalk_host:
        pytest.skip("Not relevant")

    snmp_config = snmp_config.update(credentials="dingdong")
    result = snmp.get_single_oid(snmp_config, ".1.3.6.1.2.1.1.1.0")
    assert result is None


def test_get_single_oid(snmp_config):
    result = snmp.get_single_oid(snmp_config, ".1.3.6.1.2.1.1.1.0")
    assert result == "Linux zeus 4.8.6.5-smp #2 SMP Sun Nov 13 14:58:11 CDT 2016 i686"
    assert isinstance(result, six.text_type)


def test_get_single_oid_cache(snmp_config):
    oid = ".1.3.6.1.2.1.1.1.0"
    expected_value = "Linux zeus 4.8.6.5-smp #2 SMP Sun Nov 13 14:58:11 CDT 2016 i686"

    assert snmp.get_single_oid(snmp_config, oid) == expected_value
    assert snmp_cache.is_in_single_oid_cache(oid)
    cached_oid = snmp_cache.get_oid_from_single_oid_cache(oid)
    assert cached_oid == expected_value
    assert isinstance(cached_oid, six.text_type)


def test_get_single_non_prefixed_oid(snmp_config):
    with pytest.raises(MKGeneralException, match="does not begin with"):
        snmp.get_single_oid(snmp_config, "1.3.6.1.2.1.1.1.0")


def test_get_single_oid_next(snmp_config):
    assert snmp.get_single_oid(snmp_config, ".1.3.6.1.2.1.1.9.1.*") == ".1.3.6.1.6.3.10.3.1.1"


# The get_single_oid function currently does not support OID_BIN handling
#def test_get_single_oid_hex(snmp_config):
#    assert snmp.get_single_oid(snmp_config, ".1.3.6.1.2.1.2.2.1.6.2") == b"\x00\x12yb\xf9@"


def test_get_single_oid_value(snmp_config):
    assert snmp.get_single_oid(snmp_config, ".1.3.6.1.2.1.1.9.1.2.1") == '.1.3.6.1.6.3.10.3.1.1'


def test_get_single_oid_not_existing(snmp_config):
    assert snmp.get_single_oid(snmp_config, ".1.3.100.200.300.400") is None


def test_get_single_oid_not_resolvable(snmp_config):
    if snmp_config.is_usewalk_host:
        pytest.skip("Not relevant")

    snmp_config = snmp_config.update(ipaddress="bla.local")
    assert snmp.get_single_oid(snmp_config, ".1.3.6.1.2.1.1.7.0") is None


@pytest.mark.parametrize("oid,expected_table", [
    (".1.3.6.1.2.1.11", [
        ('.1.3.6.1.2.1.11.1.0', '4294967295'),
        ('.1.3.6.1.2.1.11.2.0', '4294967295'),
        ('.1.3.6.1.2.1.11.3.0', '877474094'),
        ('.1.3.6.1.2.1.11.4.0', '292513791'),
        ('.1.3.6.1.2.1.11.5.0', '584997545'),
        ('.1.3.6.1.2.1.11.6.0', '292504432'),
        ('.1.3.6.1.2.1.11.8.0', '877498609'),
        ('.1.3.6.1.2.1.11.9.0', '585006643'),
        ('.1.3.6.1.2.1.11.10.0', '585006444'),
        ('.1.3.6.1.2.1.11.11.0', '292505902'),
        ('.1.3.6.1.2.1.11.12.0', '315362353'),
        ('.1.3.6.1.2.1.11.13.0', '4294967295'),
    ]),
    (".1.3.6.1.2.1.1.9.1.3", [
        ('.1.3.6.1.2.1.1.9.1.3.1', 'The SNMP Management Architecture MIB.'),
        ('.1.3.6.1.2.1.1.9.1.3.2', 'The MIB for Message Processing and Dispatching.'),
        ('.1.3.6.1.2.1.1.9.1.3.3',
         'The management information definitions for the SNMP User-based Security Model.'),
        ('.1.3.6.1.2.1.1.9.1.3.4', 'The MIB module for SNMPv2 entities'),
        ('.1.3.6.1.2.1.1.9.1.3.5', 'The MIB module for managing TCP implementations'),
        ('.1.3.6.1.2.1.1.9.1.3.6', 'The MIB module for managing IP and ICMP implementations'),
        ('.1.3.6.1.2.1.1.9.1.3.7', 'The MIB module for managing UDP implementations'),
        ('.1.3.6.1.2.1.1.9.1.3.8', 'View-based Access Control Model for SNMP.'),
    ]),
    (".1.3.6.1.2.1.4.21.1.1", [
        ('.1.3.6.1.2.1.4.21.1.1.0.0.0.0', '0.0.0.0'),
        ('.1.3.6.1.2.1.4.21.1.1.127.0.0.0', '127.0.0.0'),
        ('.1.3.6.1.2.1.4.21.1.1.195.218.254.0', '195.218.254.0'),
    ]),
    (".1.3.6.1.2.1.2.2.1.6", [
        ('.1.3.6.1.2.1.2.2.1.6.1', ''),
        ('.1.3.6.1.2.1.2.2.1.6.2', '"00 12 79 62 F9 40 "'),
    ]),
])
def test_walk_for_export(snmp_config, oid, expected_table):
    if snmp_config.is_usewalk_host:
        pytest.skip("Not relevant")

    table = snmp.walk_for_export(snmp_config, oid)
    assert table == expected_table
