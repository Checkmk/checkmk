#!/usr/bin/env python

import pytest
from testlib import web

import cmk_base.config as config

@pytest.fixture(scope="module")
def test_cfg(web, site):
    print "Applying default config"
    web.add_host("mgmt-host1", attributes={
        "ipaddress": "127.0.0.1",
        "management_protocol": "snmp",
        "management_snmp_community": "HOST",
    })
    web.add_host("mgmt-host2", attributes={
        "ipaddress": "127.0.0.1",
        "management_protocol": "snmp",
        "management_address": "127.0.0.2",
    })
    web.add_host("mgmt-host3", attributes={
        "ipaddress": "127.0.0.1",
        "management_protocol": None,
        "management_address": "127.0.0.1",
        "management_snmp_community": "HOST",
    })

    web.activate_changes()

    import cmk.debug
    cmk.debug.enable()

    import cmk_base.checks as checks
    checks.load()
    config.load()

    yield None

    #
    # Cleanup code
    #
    print "Cleaning up test config"

    cmk.debug.disable()

    web.delete_host("mgmt-host1")
    web.delete_host("mgmt-host2")
    web.delete_host("mgmt-host3")
    web.activate_changes()


def test_management_board_configc(test_cfg):
    assert config.has_management_board("mgmt-host1")
    assert config.management_address_of("mgmt-host1") == "127.0.0.1"
    assert config.management_protocol_of("mgmt-host1") == "snmp"
    assert config.management_credentials_of("mgmt-host1") == "HOST"

    assert config.has_management_board("mgmt-host2")
    assert config.management_address_of("mgmt-host2") == "127.0.0.2"
    assert config.management_protocol_of("mgmt-host2") == "snmp"
    assert config.management_credentials_of("mgmt-host2") == "public"

    assert config.has_management_board("mgmt-host3") == False
    assert config.management_address_of("mgmt-host3") == "127.0.0.1"
    assert config.management_protocol_of("mgmt-host3") == None
    assert config.management_credentials_of("mgmt-host3") == "HOST"
