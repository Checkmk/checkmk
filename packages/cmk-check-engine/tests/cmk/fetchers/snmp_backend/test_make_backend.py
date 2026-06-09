#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import dataclasses
import logging
from pathlib import Path

import pytest

from cmk.ccc.hostaddress import HostAddress, HostName
from cmk.checkengine.snmp_backends.classic import ClassicSNMPBackend
from cmk.checkengine.snmplib import SNMPBackendEnum, SNMPHostConfig, SNMPVersion
from cmk.fetchers.snmp_backend import make_backend


@pytest.fixture(name="snmp_config")
def fixture_snmp_config(tmp_path: Path) -> SNMPHostConfig:
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
        stored_walk_path=tmp_path,
    )


def test_factory_snmp_backend_classic(snmp_config: SNMPHostConfig) -> None:
    assert isinstance(
        make_backend(snmp_config, logging.getLogger()),
        ClassicSNMPBackend,
    )


def test_factory_snmp_backend_inline_unavailable(
    snmp_config: SNMPHostConfig,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    import cmk.fetchers.snmp_backend as snmp_backend_module

    monkeypatch.setattr(
        snmp_backend_module,
        "_BACKENDS",
        {
            k: v
            for k, v in snmp_backend_module._BACKENDS.items()  # noqa: SLF001
            if k is not SNMPBackendEnum.INLINE
        },
    )
    snmp_config = dataclasses.replace(snmp_config, snmp_backend=SNMPBackendEnum.INLINE)
    logger = logging.getLogger()
    with caplog.at_level(logging.ERROR, logger=logger.name):
        backend = make_backend(snmp_config, logger)
    assert isinstance(backend, ClassicSNMPBackend)
    assert any(
        record.levelno == logging.ERROR and "Unknown SNMP backend" in record.getMessage()
        for record in caplog.records
    )


def test_factory_snmp_backend_unknown_backend(snmp_config: SNMPHostConfig) -> None:
    with pytest.raises(AssertionError, match="Unknown SNMP backend"):
        snmp_config = dataclasses.replace(snmp_config, snmp_backend="bla")  # type: ignore[arg-type]
        make_backend(snmp_config, logging.getLogger())
