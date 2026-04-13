#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="comparison-overlap"
# mypy: disable-error-code="unreachable"

import dataclasses
import logging
from pathlib import Path

import pytest

from cmk.ccc.hostaddress import HostAddress, HostName
from cmk.fetchers.snmp_backend import ClassicSNMPBackend, make_backend
from cmk.snmplib import SNMPBackend, SNMPBackendEnum, SNMPHostConfig, SNMPVersion

InlineSNMPBackend: type[SNMPBackend] | None = None
try:
    from cmk.inline_snmp.inline import (  # type: ignore[import,unused-ignore,no-redef]
        InlineSNMPBackend,
    )
except ImportError:
    pass


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


@pytest.mark.skipif(InlineSNMPBackend is None, reason="Inline SNMP backend not available")
def test_factory_snmp_backend_inline(snmp_config: SNMPHostConfig, tmp_path: Path) -> None:
    snmp_config = dataclasses.replace(snmp_config, snmp_backend=SNMPBackendEnum.INLINE)
    assert InlineSNMPBackend is not None  # Just for the benefit of type checking
    assert isinstance(
        make_backend(snmp_config, logging.getLogger(), stored_walk_path=tmp_path), InlineSNMPBackend
    )


def test_factory_snmp_backend_inline_unavailable(
    snmp_config: SNMPHostConfig, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import cmk.fetchers.snmp_backend as snmp_backend_module

    monkeypatch.setattr(snmp_backend_module, "inline", None)
    snmp_config = dataclasses.replace(snmp_config, snmp_backend=SNMPBackendEnum.INLINE)
    with pytest.raises(NotImplementedError, match="Unknown SNMP backend"):
        make_backend(snmp_config, logging.getLogger(), stored_walk_path=tmp_path)


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
