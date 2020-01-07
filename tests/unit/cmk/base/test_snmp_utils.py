# pylint: disable=protected-access
from cmk.base import snmp_utils


def oid_kea(_arg):
    """OID function of a Kea"""
    return "Kea"


def scan_kea(oid):
    """Scan function scanning for Keas"""
    return oid(".O.I.D") == "Kea"


def test_mutex_scan_registry_register():
    scan_registry = snmp_utils.MutexScanRegistry()

    assert not scan_registry._is_specific(oid_kea)
    assert scan_kea is scan_registry.register(scan_kea)
    assert scan_registry._is_specific(oid_kea)


def test_mutex_scan_registry_as_fallback():
    scan_registry = snmp_utils.MutexScanRegistry()

    @scan_registry.as_fallback
    def scan_parrot(oid):
        return bool(oid(".O.I.D"))

    assert scan_parrot(oid_kea)

    scan_registry.register(scan_kea)
    assert not scan_parrot(oid_kea)
