#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import dataclasses
from pathlib import Path
from subprocess import CalledProcessError

import pytest

from tests.testlib.site import Site

from cmk.ccc.hostaddress import HostAddress

from cmk.snmplib import BackendOIDSpec, BackendSNMPTree, SNMPBackendEnum, SpecialColumn

from .snmp_helpers import default_config, get_single_oid, get_snmp_table

INFO_TREE = BackendSNMPTree(
    base=".1.3.6.1.2.1.1",
    oids=[
        BackendOIDSpec("1.0", "string", False),
        BackendOIDSpec("2.0", "string", False),
        BackendOIDSpec("5.0", "string", False),
    ],
)


# Missing in currently used dump:
# 5 NULL
# 68 - Opaque
@pytest.mark.parametrize(
    "type_name,oid,expected_response",
    [
        ("Counter64", ".1.3.6.1.2.1.4.31.1.1.21.1", "15833452"),
        ("OCTET STRING", ".1.3.6.1.2.1.1.4.0", "SNMP Laboratories, info@snmplabs.com"),
        ("OBJECT IDENTIFIER", ".1.3.6.1.2.1.1.9.1.2.1", ".1.3.6.1.6.3.10.3.1.1"),
        ("IpAddress", ".1.3.6.1.2.1.3.1.1.3.2.1.195.218.254.97", "195.218.254.97"),
        ("Integer32", ".1.3.6.1.2.1.1.7.0", "72"),
        ("Counter32", ".1.3.6.1.2.1.5.1.0", "324"),
        ("Gauge32", ".1.3.6.1.2.1.6.9.0", "9"),
        ("TimeTicks", ".1.3.6.1.2.1.1.3.0", "449613886"),
    ],
)
@pytest.mark.usefixtures("snmpsim")
def test_get_data_types(
    site: Site, backend_type: SNMPBackendEnum, type_name: str, oid: str, expected_response: str
) -> None:
    response = get_single_oid(site, oid, backend_type, default_config(backend_type))[0]
    assert response == expected_response
    assert isinstance(response, str)

    oid_start, oid_end = oid.rsplit(".", 1)
    table, _ = get_snmp_table(
        site,
        tree=BackendSNMPTree(base=oid_start, oids=[BackendOIDSpec(oid_end, "string", False)]),
        backend_type=backend_type,
        config=default_config(backend_type),
    )

    assert table[0][0] == expected_response
    assert isinstance(table[0][0], str)


@pytest.mark.usefixtures("snmpsim")
def test_get_simple_snmp_table_not_resolvable(site: Site, backend_type: SNMPBackendEnum) -> None:
    if backend_type is SNMPBackendEnum.STORED_WALK:
        pytest.skip("Not relevant")

    config = dataclasses.replace(
        default_config(backend_type), ipaddress=HostAddress("unknown_host.internal.")
    )

    # TODO: Unify different error messages
    if config.snmp_backend is SNMPBackendEnum.INLINE:
        exc_match = "Failed to initiate SNMP"
    else:
        exc_match = "Unknown host"

    with pytest.raises(CalledProcessError) as e:
        site.python_helper("helper_get_snmp_table.py").check_output(
            input_=repr(
                (
                    INFO_TREE.to_json(),
                    backend_type.serialize(),
                    config.serialize(),
                    str(Path(__file__).parent.resolve() / "snmp_data" / "cmk-walk"),
                )
            )
        )
    assert exc_match in e.value.stderr


@pytest.mark.usefixtures("snmpsim")
def test_get_simple_snmp_table_wrong_credentials(site: Site, backend_type: SNMPBackendEnum) -> None:
    if backend_type is SNMPBackendEnum.STORED_WALK:
        pytest.skip("Not relevant")

    config = dataclasses.replace(default_config(backend_type), credentials="dingdong")

    # TODO: Unify different error messages
    if config.snmp_backend is SNMPBackendEnum.INLINE:
        exc_match = "SNMP query timed out"
    else:
        exc_match = "Timeout: No Response from"

    with pytest.raises(CalledProcessError) as e:
        site.python_helper("helper_get_snmp_table.py").check_output(
            input_=repr(
                (
                    INFO_TREE.to_json(),
                    backend_type.serialize(),
                    config.serialize(),
                    str(Path(__file__).parent.resolve() / "snmp_data" / "cmk-walk"),
                )
            )
        )
    assert exc_match in e.value.stderr


@pytest.mark.parametrize("bulk", [True, False])
def test_get_simple_snmp_table_bulkwalk(
    site: Site, backend_type: SNMPBackendEnum, bulk: bool
) -> None:
    config = dataclasses.replace(default_config(backend_type), bulkwalk_enabled=bulk)
    table, _ = get_snmp_table(site, INFO_TREE, backend_type, config)

    assert table == [
        [
            "Linux zeus 4.8.6.5-smp #2 SMP Sun Nov 13 14:58:11 CDT 2016 i686",
            ".1.3.6.1.4.1.8072.3.2.10",
            "new system name",
        ],
    ]
    assert isinstance(table[0][0], str)


@pytest.mark.usefixtures("snmpsim")
def test_get_simple_snmp_table_fills_cache(site: Site, backend_type: SNMPBackendEnum) -> None:
    _, walk_cache = get_snmp_table(site, INFO_TREE, backend_type, default_config(backend_type))
    assert sorted(walk_cache) == [
        (".1.3.6.1.2.1.1.1.0", "f3a8901547f4c88fd9947f9e401ce2", False),
        (".1.3.6.1.2.1.1.2.0", "f3a8901547f4c88fd9947f9e401ce2", False),
        (".1.3.6.1.2.1.1.5.0", "f3a8901547f4c88fd9947f9e401ce2", False),
    ]


@pytest.mark.usefixtures("snmpsim")
def test_get_simple_snmp_table(site: Site, backend_type: SNMPBackendEnum) -> None:
    table, _ = get_snmp_table(site, INFO_TREE, backend_type, default_config(backend_type))

    assert table == [
        [
            "Linux zeus 4.8.6.5-smp #2 SMP Sun Nov 13 14:58:11 CDT 2016 i686",
            ".1.3.6.1.4.1.8072.3.2.10",
            "new system name",
        ],
    ]
    assert isinstance(table[0][0], str)


@pytest.mark.usefixtures("snmpsim")
def test_get_simple_snmp_table_oid_end(site: Site, backend_type: SNMPBackendEnum) -> None:
    oid_info = BackendSNMPTree(
        base=".1.3.6.1.2.1.2.2.1",
        oids=[
            BackendOIDSpec("1", "string", False),
            BackendOIDSpec("2", "string", False),
            BackendOIDSpec("3", "string", False),
            BackendOIDSpec(SpecialColumn.END, "string", False),
        ],
    )
    table, _ = get_snmp_table(site, oid_info, backend_type, default_config(backend_type))

    assert table == [
        ["1", "lo", "24", "1"],
        ["2", "eth0", "6", "2"],
    ]


@pytest.mark.usefixtures("snmpsim")
def test_get_simple_snmp_table_oid_string(site: Site, backend_type: SNMPBackendEnum) -> None:
    oid_info = BackendSNMPTree(
        base=".1.3.6.1.2.1.2.2.1",
        # deprecated with checkmk version 2.0
        oids=[
            BackendOIDSpec("1", "string", False),
            BackendOIDSpec("2", "string", False),
            BackendOIDSpec("3", "string", False),
            BackendOIDSpec(SpecialColumn.STRING, "string", False),
        ],
    )
    table, _ = get_snmp_table(site, oid_info, backend_type, default_config(backend_type))

    assert table == [
        ["1", "lo", "24", ".1.3.6.1.2.1.2.2.1.1.1"],
        ["2", "eth0", "6", ".1.3.6.1.2.1.2.2.1.1.2"],
    ]


@pytest.mark.usefixtures("snmpsim")
def test_get_simple_snmp_table_oid_bin(site: Site, backend_type: SNMPBackendEnum) -> None:
    oid_info = BackendSNMPTree(
        base=".1.3.6.1.2.1.2.2.1",
        # deprecated with checkmk version 2.0
        oids=[
            BackendOIDSpec("1", "string", False),
            BackendOIDSpec("2", "string", False),
            BackendOIDSpec("3", "string", False),
            BackendOIDSpec(SpecialColumn.BIN, "string", False),
        ],
    )
    table, _ = get_snmp_table(site, oid_info, backend_type, default_config(backend_type))

    assert table == [
        ["1", "lo", "24", "\x01\x03\x06\x01\x02\x01\x02\x02\x01\x01\x01"],
        ["2", "eth0", "6", "\x01\x03\x06\x01\x02\x01\x02\x02\x01\x01\x02"],
    ]


@pytest.mark.usefixtures("snmpsim")
def test_get_simple_snmp_table_oid_end_bin(site: Site, backend_type: SNMPBackendEnum) -> None:
    oid_info = BackendSNMPTree(
        base=".1.3.6.1.2.1.2.2.1",
        # deprecated with checkmk version 2.0
        oids=[
            BackendOIDSpec("1", "string", False),
            BackendOIDSpec("2", "string", False),
            BackendOIDSpec("3", "string", False),
            BackendOIDSpec(SpecialColumn.END_BIN, "string", False),
        ],
    )
    table, _ = get_snmp_table(site, oid_info, backend_type, default_config(backend_type))

    assert table == [
        ["1", "lo", "24", "\x01"],
        ["2", "eth0", "6", "\x02"],
    ]


@pytest.mark.usefixtures("snmpsim")
def test_get_simple_snmp_table_with_hex_str(site: Site, backend_type: SNMPBackendEnum) -> None:
    oid_info = BackendSNMPTree(
        base=".1.3.6.1.2.1.2.2.1",
        oids=[BackendOIDSpec("6", "string", False)],
    )

    table, _ = get_snmp_table(site, oid_info, backend_type, default_config(backend_type))

    assert table == [
        [""],
        [
            "\x00\x12yb\xf9@",
        ],
    ]
