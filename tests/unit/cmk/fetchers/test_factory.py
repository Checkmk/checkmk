#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import dataclasses
import logging
from pathlib import Path

import pytest

from tests.testlib.common.repo import is_enterprise_repo

from cmk.ccc.hostaddress import HostAddress, HostName

from cmk.snmplib import SNMPBackendEnum, SNMPHostConfig, SNMPVersion

from cmk.fetchers.snmp import make_backend
from cmk.fetchers.snmp_backend import ClassicSNMPBackend

if is_enterprise_repo():
    from cmk.fetchers.cee.snmp_backend.inline import (  # type: ignore[import,unused-ignore]
        InlineSNMPBackend,
    )
else:
    InlineSNMPBackend = None  # type: ignore[assignment, misc, unused-ignore]


@pytest.fixture(name="snmp_config")
def fixture_snmp_config() -> SNMPHostConfig:
    return SNMPHostConfig(
        is_ipv6_primary=False,
        hostname=HostName("bob"),
        ipaddress=HostAddress("1.2.3.4"),
        credentials="public",
        port=42,
        bulkwalk_enabled=True,
        snmp_version=SNMPVersion.V2C,
        bulk_walk_size_of=0,
        timing={},
        oid_range_limits={},
        snmpv3_contexts=[],
        character_encoding=None,
        snmp_backend=SNMPBackendEnum.CLASSIC,
    )


def test_factory_snmp_backend_classic(snmp_config: SNMPHostConfig, tmp_path: Path) -> None:
    assert isinstance(
        make_backend(snmp_config, logging.getLogger(), stored_walk_path=tmp_path),
        ClassicSNMPBackend,
    )


def test_factory_snmp_backend_inline(snmp_config: SNMPHostConfig, tmp_path: Path) -> None:
    snmp_config = dataclasses.replace(snmp_config, snmp_backend=SNMPBackendEnum.INLINE)
    if InlineSNMPBackend is not None:
        assert isinstance(
            make_backend(snmp_config, logging.getLogger(), stored_walk_path=tmp_path),
            InlineSNMPBackend,
        )


def test_factory_snmp_backend_unknown_backend(snmp_config: SNMPHostConfig, tmp_path: Path) -> None:
    with pytest.raises(NotImplementedError, match="Unknown SNMP backend"):
        snmp_config = dataclasses.replace(snmp_config, snmp_backend="bla")  # type: ignore[arg-type]
        if InlineSNMPBackend is not None:
            assert isinstance(
                make_backend(snmp_config, logging.getLogger(), stored_walk_path=tmp_path),
                InlineSNMPBackend,
            )
        else:
            assert isinstance(
                make_backend(snmp_config, logging.getLogger(), stored_walk_path=tmp_path),
                ClassicSNMPBackend,
            )
