#!/usr/bin/env python

import pytest
from testlib import web

import cmk_base.config as config

@pytest.fixture(autouse=True)
def test_cfg(web):
    import cmk.debug
    cmk.debug.enable()

    yield

    #
    # Cleanup code
    #
    print "Cleaning up test config"

    cmk.debug.disable()

    if web.host_exists("mgmt-host"):
        web.delete_host("mgmt-host")

    if web.folder_exists("folder1"):
        web.delete_folder("folder1")

    web.activate_changes()

    config.load()


def test_mgmt_explicit_settings(web):
    web.add_host("mgmt-host", attributes={
        "ipaddress": "127.0.0.1",
        "management_protocol": "snmp",
        "management_snmp_community": "HOST",
    })

    config.load()
    assert config.has_management_board("mgmt-host")
    assert config.management_address_of("mgmt-host") == "127.0.0.1"
    assert config.management_protocol_of("mgmt-host") == "snmp"
    assert config.management_credentials_of("mgmt-host") == "HOST"


def test_mgmt_explicit_address(web):
    web.add_host("mgmt-host", attributes={
        "ipaddress": "127.0.0.1",
        "management_protocol": "snmp",
        "management_address": "127.0.0.2",
    })

    config.load()
    assert config.has_management_board("mgmt-host")
    assert config.management_address_of("mgmt-host") == "127.0.0.2"
    assert config.management_protocol_of("mgmt-host") == "snmp"
    assert config.management_credentials_of("mgmt-host") == "public"


def test_mgmt_disabled(web):
    web.add_host("mgmt-host", attributes={
        "ipaddress": "127.0.0.1",
        "management_protocol": None,
        "management_address": "127.0.0.1",
        "management_snmp_community": "HOST",
    })

    config.load()
    assert config.has_management_board("mgmt-host") == False
    assert config.management_address_of("mgmt-host") == "127.0.0.1"
    assert config.management_protocol_of("mgmt-host") == None
    assert config.management_credentials_of("mgmt-host") == "HOST"


def test_mgmt_inherit_credentials_explicit_host(web):
    web.add_folder("folder1", attributes={
        "management_snmp_community": "FOLDER",
    })

    web.add_host("mgmt-host", folder="folder1", attributes={
        "ipaddress": "127.0.0.1",
        "management_protocol": "snmp",
        "management_snmp_community": "HOST",
    })

    config.load()
    assert config.has_management_board("mgmt-host")
    assert config.management_address_of("mgmt-host") == "127.0.0.1"
    assert config.management_protocol_of("mgmt-host") == "snmp"
    assert config.management_credentials_of("mgmt-host") == "HOST"



def test_mgmt_inherit_credentials(web):
    web.add_folder("folder1", attributes={
        "management_snmp_community": "FOLDER",
    })

    web.add_host("mgmt-host", folder="folder1", attributes={
        "ipaddress": "127.0.0.1",
        "management_protocol": "snmp",
    })

    config.load()
    assert config.has_management_board("mgmt-host")
    assert config.management_address_of("mgmt-host") == "127.0.0.1"
    assert config.management_protocol_of("mgmt-host") == "snmp"
    assert config.management_credentials_of("mgmt-host") == "FOLDER"


def test_mgmt_inherit_protocol_explicit_host(web):
    web.add_folder("folder1", attributes={
        "management_protocol": None,
        "management_snmp_community": "FOLDER",
    })

    web.add_host("mgmt-host", folder="folder1", attributes={
        "ipaddress": "127.0.0.1",
        "management_protocol": "snmp",
        "management_snmp_community": "HOST",
    })

    config.load()
    assert config.has_management_board("mgmt-host")
    assert config.management_address_of("mgmt-host") == "127.0.0.1"
    assert config.management_protocol_of("mgmt-host") == "snmp"
    assert config.management_credentials_of("mgmt-host") == "HOST"



def test_mgmt_inherit_protocol(web):
    web.add_folder("folder1", attributes={
        "management_protocol": "snmp",
        "management_snmp_community": "FOLDER",
    })

    web.add_host("mgmt-host", folder="folder1", attributes={
        "ipaddress": "127.0.0.1",
    })

    config.load()
    assert config.has_management_board("mgmt-host")
    assert config.management_address_of("mgmt-host") == "127.0.0.1"
    assert config.management_protocol_of("mgmt-host") == "snmp"
    assert config.management_credentials_of("mgmt-host") == "FOLDER"
