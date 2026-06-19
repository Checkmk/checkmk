#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"
# mypy: disable-error-code="no-untyped-def"
# ruff: noqa: ARG002
# ruff: noqa: SLF001


import dataclasses
import logging
from collections.abc import Sequence
from functools import partial
from pathlib import Path
from typing import NoReturn

import pytest

import cmk.checkengine.snmplib._table as _snmp_table
from cmk.ccc.hostaddress import HostAddress, HostName
from cmk.checkengine.snmplib import (
    BackendOIDSpec,
    BackendSNMPTree,
    ensure_str,
    get_snmp_table,
    SNMPBackend,
    SNMPBackendEnum,
    SNMPContext,
    SNMPContextConfig,
    SNMPHostConfig,
    SNMPSectionName,
    SNMPTable,
    SNMPTimeout,
    SNMPVersion,
    SpecialColumn,
)
from cmk.utils.log import logger

SNMPConfig = SNMPHostConfig(
    is_ipv6_primary=False,
    hostname=HostName("testhost"),
    ipaddress=HostAddress("1.2.3.4"),
    credentials="",
    port=42,
    bulkwalk_enabled=True,
    snmp_version=SNMPVersion.V1,
    bulk_walk_size_of=0,
    timing={},
    oid_range_limits={},
    snmpv3_contexts=[],
    character_encoding="ascii",
    snmp_backend=SNMPBackendEnum.CLASSIC,
    stored_walk_path=Path("/tmp/foo"),
)


class SNMPTestBackend(SNMPBackend):
    @staticmethod
    def get_type() -> SNMPBackendEnum:
        return SNMPBackendEnum.CLASSIC

    def get(self, /, oid, *, context):
        pass

    def walk(self, /, oid, *, context, **kw):
        return [(f"{oid}.{r}", b"C0FEFE") for r in (1, 2, 3)]


@pytest.mark.parametrize(
    "snmp_info, expected_values",
    [
        (
            BackendSNMPTree(
                base=".1.3.6.1.4.1.13595.2.2.3.1",
                oids=[
                    BackendOIDSpec(SpecialColumn.END, "string", False),
                    BackendOIDSpec("16", "binary", False),
                ],
            ),
            [
                ["1", [67, 48, 70, 69, 70, 69]],
                ["2", [67, 48, 70, 69, 70, 69]],
                ["3", [67, 48, 70, 69, 70, 69]],
            ],
        ),
    ],
)
def test_get_snmp_table(
    snmp_info: BackendSNMPTree, expected_values: list[Sequence[SNMPTable]]
) -> None:
    def get_all_snmp_tables(info):
        backend = SNMPTestBackend(SNMPConfig, logger)
        if not isinstance(info, list):
            return get_snmp_table(
                section_name=SNMPSectionName("unit_test"),
                tree=info,
                walk_cache={},
                backend=backend,
                log=logger.debug,
            )
        return [
            get_snmp_table(
                section_name=SNMPSectionName("unit_test"),
                tree=i,
                walk_cache={},
                backend=backend,
                log=logger.debug,
            )
            for i in info
        ]

    assert get_all_snmp_tables(snmp_info) == expected_values


@pytest.mark.parametrize(
    "encoding, columns, expected",
    [
        (None, [([b"\xc3\xbc"], "string")], [["ü"]]),  # utf-8
        (None, [([b"\xc3\xbc"], "binary")], [[[195, 188]]]),  # utf-8
        (None, [([b"\xfc"], "string")], [["ü"]]),  # latin-1
        (None, [([b"\xfc"], "binary")], [[[252]]]),  # latin-1
        ("utf-8", [([b"\xc3\xbc"], "string")], [["ü"]]),
        ("latin1", [([b"\xfc"], "string")], [["ü"]]),
        ("cp437", [([b"\x81"], "string")], [["ü"]]),
    ],
)
def test_sanitize_snmp_encoding(
    encoding: str | None,
    columns: _snmp_table._ResultColumnsSanitized,
    expected: Sequence[Sequence[_snmp_table.SNMPDecodedValues]],
) -> None:
    assert [
        _snmp_table._decode_column(c, v, partial(ensure_str, encoding=encoding)) for c, v in columns
    ] == expected


def test_walk_passes_on_timeout_with_snmpv3_context_continue_on_timeout() -> None:
    class Backend(SNMPBackend):
        @staticmethod
        def get_type() -> SNMPBackendEnum:
            return SNMPBackendEnum.CLASSIC

        def get(self, /, *args: object, **kw: object) -> NoReturn:
            assert False

        def walk(
            self,
            /,
            oid: object,
            *,
            context: SNMPContext,
            **kw: object,
        ) -> NoReturn:
            # return timeout on first context, error on second context.
            # we do expect to reach the second context here.
            raise SNMPTimeout() if context != "two" else RuntimeError()

    section_name = SNMPSectionName("section")
    with pytest.raises(RuntimeError):
        _snmp_table.get_snmpwalk(
            section_name,
            ".1.2.3",
            ".4.5.6",
            walk_cache={},
            save_walk_cache=False,
            backend=Backend(
                dataclasses.replace(
                    SNMPConfig,
                    snmp_version=SNMPVersion.V3,
                    snmpv3_contexts=[
                        SNMPContextConfig(
                            section=section_name,
                            contexts=["one", "two"],
                            timeout_policy="continue",
                        )
                    ],
                ),
                logging.getLogger("test"),
            ),
            log=logger.debug,
        )


def test_walk_raises_on_timeout_without_snmpv3_context_stop_on_timeout() -> None:
    class Backend(SNMPBackend):
        @staticmethod
        def get_type() -> SNMPBackendEnum:
            return SNMPBackendEnum.CLASSIC

        def get(self, /, *args: object, **kw: object) -> NoReturn:
            assert False

        def walk(
            self,
            /,
            oid: object,
            *,
            context: SNMPContext,
            **kw: object,
        ) -> NoReturn:
            # return timeout on first context, error on second context
            # We expect to never reach the second context here.
            raise SNMPTimeout() if context != "two" else RuntimeError()

    section_name = SNMPSectionName("section")
    with pytest.raises(SNMPTimeout):
        _snmp_table.get_snmpwalk(
            section_name,
            ".1.2.3",
            ".4.5.6",
            walk_cache={},
            save_walk_cache=False,
            backend=Backend(
                dataclasses.replace(
                    SNMPConfig,
                    snmpv3_contexts=[
                        SNMPContextConfig(
                            section=section_name,
                            contexts=["one", "two"],
                            timeout_policy="stop",
                        )
                    ],
                ),
                logging.getLogger("test"),
            ),
            log=logger.debug,
        )
