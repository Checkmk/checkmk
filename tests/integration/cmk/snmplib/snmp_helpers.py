#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import ast
from collections.abc import MutableMapping, Sequence
from pathlib import Path

from tests.testlib.site import Site

from cmk.ccc.hostaddress import HostAddress, HostName

from cmk.snmplib import (
    BackendSNMPTree,
    OID,
    SNMPBackendEnum,
    SNMPDecodedString,
    SNMPHostConfig,
    SNMPTable,
    SNMPVersion,
)


def default_config(backend_type: SNMPBackendEnum) -> SNMPHostConfig:
    return SNMPHostConfig(
        is_ipv6_primary=False,
        ipaddress=HostAddress("127.0.0.1"),
        hostname=HostName("localhost"),
        credentials="public",
        port=1337,
        # TODO: Use SNMPv2 over v1 for the moment
        bulkwalk_enabled=False,
        snmp_version=SNMPVersion.V2C,
        bulk_walk_size_of=10,
        timing={},
        oid_range_limits={},
        snmpv3_contexts=[],
        character_encoding=None,
        snmp_backend=backend_type,
    )


def get_snmp_table(
    site: Site, tree: BackendSNMPTree, backend_type: SNMPBackendEnum, config: SNMPHostConfig
) -> tuple[Sequence[SNMPTable], MutableMapping[tuple[str, str, bool], list[tuple[str, bytes]]]]:
    return ast.literal_eval(
        site.python_helper("helper_get_snmp_table.py").check_output(
            input_=repr(
                (
                    tree.to_json(),
                    backend_type.serialize(),
                    config.serialize(),
                    str(Path(__file__).parent.resolve() / "snmp_data" / "cmk-walk"),
                )
            )
        )
    )


def get_single_oid(
    site: Site, oid: OID, backend_type: SNMPBackendEnum, config: SNMPHostConfig
) -> tuple[SNMPDecodedString | None, MutableMapping[OID, SNMPDecodedString | None]]:
    with site.copy_file(
        str(Path(__file__).parent.resolve() / "snmp_data" / "cmk-walk" / "localhost"),
        site.path("cmk-walk/localhost"),
    ):
        return ast.literal_eval(
            site.python_helper("helper_get_single_oid.py").check_output(
                input_=repr(
                    (
                        oid,
                        backend_type.serialize(),
                        config.serialize(),
                        site.path("cmk-walk").as_posix(),
                    )
                )
            )
        )
