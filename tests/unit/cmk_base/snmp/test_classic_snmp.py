import collections
import pytest
import cmk_base.classic_snmp as classic_snmp
import cmk_base.snmp_utils as snmp_utils


@pytest.mark.parametrize("port,expected", [
    (161, ""),
    (1234, ":1234"),
])
def test_snmp_port_spec(port, expected):
    host_config = snmp_utils.SNMPHostConfig(
        is_ipv6_primary=False,
        hostname="localhost",
        ipaddress="127.0.0.1",
        credentials="public",
        port=port,
        is_bulkwalk_host=False,
        is_snmpv2c_host=False,
        bulk_walk_size_of=10,
        timing={},
    )
    assert classic_snmp._snmp_port_spec(host_config) == expected


@pytest.mark.parametrize("is_ipv6,expected", [
    (True, "udp6:"),
    (False, ""),
])
def test_snmp_proto_spec(monkeypatch, is_ipv6, expected):
    host_config = snmp_utils.SNMPHostConfig(
        is_ipv6_primary=is_ipv6,
        hostname="localhost",
        ipaddress="127.0.0.1",
        credentials="public",
        port=161,
        is_bulkwalk_host=False,
        is_snmpv2c_host=False,
        bulk_walk_size_of=10,
        timing={},
    )
    assert classic_snmp._snmp_proto_spec(host_config) == expected


SNMPSettings = collections.namedtuple("SNMPSettings", [
    "host_config",
    "context_name",
])


@pytest.mark.parametrize("settings,expected", [
    (SNMPSettings(
        host_config=snmp_utils.SNMPHostConfig(
            is_ipv6_primary=False,
            hostname="localhost",
            ipaddress="127.0.0.1",
            credentials="public",
            port=161,
            is_bulkwalk_host=True,
            is_snmpv2c_host=True,
            bulk_walk_size_of=10,
            timing={
                "timeout": 2,
                "retries": 3
            },
        ),
        context_name=None,
    ), [
        'snmpbulkwalk', '-Cr10', '-v2c', '-c', 'public', '-m', '', '-M', '', '-t', '2.00', '-r',
        '3', '-Cc'
    ]),
    (SNMPSettings(
        host_config=snmp_utils.SNMPHostConfig(
            is_ipv6_primary=False,
            hostname="lohost",
            ipaddress="127.0.0.1",
            credentials="public",
            port=161,
            is_bulkwalk_host=False,
            is_snmpv2c_host=False,
            bulk_walk_size_of=5,
            timing={
                "timeout": 5,
                "retries": 1
            },
        ),
        context_name="blabla",
    ), [
        'snmpwalk', '-v1', '-c', 'public', '-m', '', '-M', '', '-t', '5.00', '-r', '1', '-n',
        'blabla', '-Cc'
    ]),
    (SNMPSettings(
        host_config=snmp_utils.SNMPHostConfig(
            is_ipv6_primary=False,
            hostname="lohost",
            ipaddress="public",
            credentials=("authNoPriv", "abc", "md5", "abc"),
            port=161,
            is_bulkwalk_host=False,
            is_snmpv2c_host=False,
            bulk_walk_size_of=5,
            timing={
                "timeout": 5,
                "retries": 1
            },
        ),
        context_name="blabla",
    ), [
        'snmpwalk', '-v3', '-l', 'authNoPriv', '-a', 'abc', '-u', 'md5', '-A', 'abc', '-m', '',
        '-M', '', '-t', '5.00', '-r', '1', '-n', 'blabla', '-Cc'
    ]),
    (SNMPSettings(
        host_config=snmp_utils.SNMPHostConfig(
            is_ipv6_primary=False,
            hostname="lohost",
            ipaddress="public",
            credentials=('noAuthNoPriv', 'secname'),
            port=161,
            is_bulkwalk_host=False,
            is_snmpv2c_host=False,
            bulk_walk_size_of=5,
            timing={
                "timeout": 5,
                "retries": 1
            },
        ),
        context_name=None,
    ), [
        'snmpwalk', '-v3', '-l', 'noAuthNoPriv', '-u', 'secname', '-m', '', '-M', '', '-t', '5.00',
        '-r', '1', '-Cc'
    ]),
    (SNMPSettings(
        host_config=snmp_utils.SNMPHostConfig(
            is_ipv6_primary=False,
            hostname="lohost",
            ipaddress="127.0.0.1",
            credentials=('authPriv', 'md5', 'secname', 'auhtpassword', 'DES', 'privacybla'),
            port=161,
            is_bulkwalk_host=False,
            is_snmpv2c_host=False,
            bulk_walk_size_of=5,
            timing={
                "timeout": 5,
                "retries": 1
            },
        ),
        context_name=None,
    ), [
        'snmpwalk', '-v3', '-l', 'authPriv', '-a', 'md5', '-u', 'secname', '-A', 'auhtpassword',
        '-x', 'DES', '-X', 'privacybla', '-m', '', '-M', '', '-t', '5.00', '-r', '1', '-Cc'
    ]),
])
def test_snmp_walk_command(monkeypatch, settings, expected):
    assert classic_snmp._snmp_walk_command(settings.host_config, settings.context_name) == expected
