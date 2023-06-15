#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging

import pytest

from tests.testlib import is_enterprise_repo

from cmk.utils.hostaddress import HostAddress, HostName

from cmk.snmplib.type_defs import SNMPBackendEnum, SNMPHostConfig

from cmk.fetchers.snmp import make_backend
from cmk.fetchers.snmp_backend import ClassicSNMPBackend

if is_enterprise_repo():
    from cmk.fetchers.cee.snmp_backend.inline import (  # type: ignore[import] # pylint: disable=import-error,no-name-in-module
        InlineSNMPBackend,
    )
else:
    InlineSNMPBackend = None  # type: ignore[assignment, misc]


@pytest.fixture(name="snmp_config")
def fixture_snmp_config() -> SNMPHostConfig:
    return SNMPHostConfig(
        is_ipv6_primary=False,
        hostname=HostName("bob"),
        ipaddress=HostAddress("1.2.3.4"),
        credentials="public",
        port=42,
        is_bulkwalk_host=False,
        is_snmpv2or3_without_bulkwalk_host=False,
        bulk_walk_size_of=0,
        timing={},
        oid_range_limits={},
        snmpv3_contexts=[],
        character_encoding=None,
        snmp_backend=SNMPBackendEnum.CLASSIC,
    )


def test_factory_snmp_backend_classic(snmp_config: SNMPHostConfig) -> None:
    assert isinstance(make_backend(snmp_config, logging.getLogger()), ClassicSNMPBackend)


def test_factory_snmp_backend_inline(snmp_config: SNMPHostConfig) -> None:
    snmp_config = snmp_config._replace(snmp_backend=SNMPBackendEnum.INLINE)
    if InlineSNMPBackend is not None:
        assert isinstance(make_backend(snmp_config, logging.getLogger()), InlineSNMPBackend)


def test_factory_snmp_backend_unknown_backend(snmp_config: SNMPHostConfig) -> None:
    with pytest.raises(NotImplementedError, match="Unknown SNMP backend"):
        snmp_config = snmp_config._replace(snmp_backend="bla")  # type: ignore[arg-type]
        if InlineSNMPBackend is not None:
            assert isinstance(make_backend(snmp_config, logging.getLogger()), InlineSNMPBackend)
        else:
            assert isinstance(
                make_backend(snmp_config, logging.getLogger()),
                ClassicSNMPBackend,
            )
