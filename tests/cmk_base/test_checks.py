import cmk_base.checks as checks

def test_load_checks():
    assert checks.check_info == {}
    checks.load()
    assert len(checks.check_info) > 1000


def test_is_tcp_check():
    checks.load()
    assert checks.is_tcp_check("xxx") == False
    assert checks.is_tcp_check("uptime") == True
    assert checks.is_tcp_check("uptime") == True
    assert checks.is_tcp_check("snmp_uptime") == False
    assert checks.is_tcp_check("mem") == True
    assert checks.is_tcp_check("mem.linux") == True
    assert checks.is_tcp_check("mem.ding") == True
    assert checks.is_tcp_check("apc_humidity") == False


def test_is_snmp_check():
    checks.load()
    assert checks.is_snmp_check("xxx") == False
    assert checks.is_snmp_check("uptime") == False
    assert checks.is_snmp_check("uptime") == False
    assert checks.is_snmp_check("snmp_uptime") == True
    assert checks.is_snmp_check("mem") == False
    assert checks.is_snmp_check("mem.linux") == False
    assert checks.is_snmp_check("mem.ding") == False
    assert checks.is_snmp_check("apc_humidity") == True
    assert checks.is_snmp_check("brocade.power") == True
    assert checks.is_snmp_check("brocade.fan") == True
    assert checks.is_snmp_check("brocade.xy") == True
    assert checks.is_snmp_check("brocade") == True


def test_discoverable_tcp_checks():
    checks.load()
    assert "uptime" in checks.discoverable_tcp_checks()
    assert "snmp_uptime" not in checks.discoverable_tcp_checks()
    assert "logwatch" in checks.discoverable_tcp_checks()
