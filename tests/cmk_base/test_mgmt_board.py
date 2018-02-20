#!/usr/bin/env python

import pytest
from testlib import web

import cmk_base.config as config


@pytest.fixture(scope="function")
def clear_config_caches(monkeypatch):
    import cmk_base
    import cmk_base.caching
    monkeypatch.setattr(cmk_base, "config_cache", cmk_base.caching.CacheManager())
    monkeypatch.setattr(cmk_base, "runtime_cache", cmk_base.caching.CacheManager())


@pytest.fixture(scope="function")
def reload_config():
    # Needs to be done together, even when the checks are not directly needed
    import cmk_base.checks as checks
    checks.load()
    config.load()


@pytest.fixture(scope="function")
def enable_debug():
    import cmk.debug
    cmk.debug.enable()
    yield
    cmk.debug.disable()


@pytest.fixture(autouse=True)
def test_cfg(web, clear_config_caches, reload_config, enable_debug):
    yield

    #
    # Cleanup code
    #
    print "Cleaning up test config"

    if web.host_exists("mgmt-host"):
        web.delete_host("mgmt-host")

    if web.folder_exists("folder1"):
        web.delete_folder("folder1")

    web.set_ruleset("management_board_config", {
        "ruleset": {
            "": [], # -> folder
        }
    })

    web.activate_changes()


def test_mgmt_explicit_settings(web):
    web.add_host("mgmt-host", attributes={
        "ipaddress": "127.0.0.1",
        "management_protocol": "snmp",
        "management_snmp_community": "HOST",
    })

    reload_config()
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

    reload_config()
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

    reload_config()
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

    reload_config()
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

    reload_config()
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

    reload_config()
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

    reload_config()
    assert config.has_management_board("mgmt-host")
    assert config.management_address_of("mgmt-host") == "127.0.0.1"
    assert config.management_protocol_of("mgmt-host") == "snmp"
    assert config.management_credentials_of("mgmt-host") == "FOLDER"


def test_mgmt_config_ruleset(web):
    web.set_ruleset("management_board_config", {
        "ruleset": {
            "": [ # "" -> folder
                {
                    'conditions': {
                        'host_specs': ['@all'],
                        'host_tags': []
                    },
                    'options': {},
                    'value': ("snmp", "RULESET"),
                },
            ],
        }
    })

    web.add_folder("folder1")

    web.add_host("mgmt-host", folder="folder1", attributes={
        "ipaddress": "127.0.0.1",
        "management_protocol": "snmp",
    })

    reload_config()
    assert config.has_management_board("mgmt-host")
    assert config.management_address_of("mgmt-host") == "127.0.0.1"
    assert config.management_protocol_of("mgmt-host") == "snmp"
    assert config.management_credentials_of("mgmt-host") == "RULESET"


def test_mgmt_config_ruleset_overidden_by_explicit_setting(web):
    web.set_ruleset("management_board_config", {
        "ruleset": {
            "": [ # "" -> folder
                {
                    'conditions': {
                        'host_specs': ['@all'],
                        'host_tags': []
                    },
                    'options': {},
                    'value': ("snmp", "RULESET"),
                },
            ],
        }
    })

    web.add_folder("folder1", attributes={
        "management_snmp_community": "FOLDER",
    })

    web.add_host("mgmt-host", folder="folder1", attributes={
        "ipaddress": "127.0.0.1",
        "management_protocol": "snmp",
    })

    reload_config()
    assert config.has_management_board("mgmt-host")
    assert config.management_address_of("mgmt-host") == "127.0.0.1"
    assert config.management_protocol_of("mgmt-host") == "snmp"
    assert config.management_credentials_of("mgmt-host") == "FOLDER"


def test_mgmt_config_ruleset_order(web):
    web.set_ruleset("management_board_config", {
        "ruleset": {
            "": [ # "" -> folder
                {
                    'conditions': {
                        'host_specs': ['@all'],
                        'host_tags': []
                    },
                    'options': {},
                    'value': ("snmp", "RULESET1"),
                },
                {
                    'conditions': {
                        'host_specs': ['@all'],
                        'host_tags': []
                    },
                    'options': {},
                    'value': ("snmp", "RULESET2"),
                },
            ],
        }
    })

    web.add_folder("folder1")

    web.add_host("mgmt-host", folder="folder1", attributes={
        "ipaddress": "127.0.0.1",
        "management_protocol": "snmp",
    })

    reload_config()
    assert config.has_management_board("mgmt-host")
    assert config.management_address_of("mgmt-host") == "127.0.0.1"
    assert config.management_protocol_of("mgmt-host") == "snmp"
    assert config.management_credentials_of("mgmt-host") == "RULESET1"
