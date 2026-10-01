#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import override

from cmk.ccc.hostaddress import HostAddress, HostName
from cmk.checkengine.snmplib import (
    OID,
    SNMPBackend,
    SNMPBackendEnum,
    SNMPContext,
    SNMPContextConfig,
    SNMPHostConfig,
    SNMPRawValue,
    SNMPRowInfo,
    SNMPVersion,
    walk_all_contexts_for_export,
)


def _snmp_config(contexts: Sequence[SNMPContext]) -> SNMPHostConfig:
    return SNMPHostConfig(
        is_ipv6_primary=False,
        hostname=HostName("testhost"),
        ipaddress=HostAddress("1.2.3.4"),
        credentials="",
        port=161,
        bulkwalk_enabled=True,
        snmp_version=SNMPVersion.V3,
        bulk_walk_size_of=0,
        timing={},
        oid_range_limits={},
        snmpv3_contexts=[SNMPContextConfig(section=None, contexts=contexts, timeout_policy="stop")],
        character_encoding="ascii",
        snmp_backend=SNMPBackendEnum.CLASSIC,
        stored_walk_path=Path("/tmp/foo"),
    )


class _ContextBackend(SNMPBackend):
    """Answers every walk with the rows of the context; contexts without rows fail"""

    def __init__(
        self,
        contexts: Sequence[SNMPContext],
        rows_by_context: Mapping[SNMPContext, SNMPRowInfo],
    ) -> None:
        super().__init__(_snmp_config(contexts))
        self._rows_by_context = rows_by_context

    @staticmethod
    @override
    def get_type() -> SNMPBackendEnum:
        return SNMPBackendEnum.CLASSIC

    @override
    def get(self, /, oid: OID, *, context: SNMPContext) -> SNMPRawValue | None:
        return None

    @override
    def walk(self, /, oid: OID, *, context: SNMPContext, **kw: object) -> SNMPRowInfo:
        if context not in self._rows_by_context:
            raise RuntimeError(f"timeout in {context}")
        return self._rows_by_context[context]


def _ignore_error(_oid: OID, _context: SNMPContext, _e: Exception) -> None:
    pass


def test_rows_of_all_configured_contexts_are_returned() -> None:
    backend = _ContextBackend(
        ["", "vrf1"],
        {"": [(".1.3.6.1.2.1.1.0", b"default")], "vrf1": [(".1.3.6.1.2.1.2.0", b"vrf")]},
    )

    rows = walk_all_contexts_for_export(".1.3.6.1.2.1", backend=backend, on_error=_ignore_error)

    assert rows == [(".1.3.6.1.2.1.1.0", "default"), (".1.3.6.1.2.1.2.0", "vrf")]


def test_oid_returned_by_several_contexts_is_kept_once_with_the_first_value() -> None:
    backend = _ContextBackend(
        ["", "vrf1"],
        {"": [(".1.3.6.1.2.1.1.0", b"default")], "vrf1": [(".1.3.6.1.2.1.1.0", b"vrf")]},
    )

    rows = walk_all_contexts_for_export(".1.3.6.1.2.1", backend=backend, on_error=_ignore_error)

    assert rows == [(".1.3.6.1.2.1.1.0", "default")]


def test_failing_context_is_reported_and_the_remaining_contexts_are_walked() -> None:
    backend = _ContextBackend(["broken", ""], {"": [(".1.3.6.1.2.1.1.0", b"default")]})
    errors: list[tuple[OID, SNMPContext, str]] = []

    rows = walk_all_contexts_for_export(
        ".1.3.6.1.2.1",
        backend=backend,
        on_error=lambda oid, context, e: errors.append((oid, context, str(e))),
    )

    assert (rows, errors) == (
        [(".1.3.6.1.2.1.1.0", "default")],
        [(".1.3.6.1.2.1", "broken", "timeout in broken")],
    )
