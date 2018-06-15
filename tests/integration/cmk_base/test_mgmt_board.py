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
    import cmk_base.check_api as check_api
    config.load_all_checks(check_api.get_check_api_context)
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


@pytest.mark.parametrize("protocol,cred_attribute,credentials", [
    ("snmp", "management_snmp_community", "HOST"),
    ("ipmi", "management_ipmi_credentials", {
        "username"      : "USER",
        "password"      : "PASS",
    }),
])
def test_mgmt_explicit_settings(web, protocol, cred_attribute, credentials):
    web.add_host("mgmt-host", attributes={
        "ipaddress": "127.0.0.1",
        "management_protocol": protocol,
        cred_attribute: credentials,
    })

    reload_config()
    assert config.has_management_board("mgmt-host")
    assert config.management_address_of("mgmt-host") == "127.0.0.1"
    assert config.management_protocol_of("mgmt-host") == protocol
    assert config.management_credentials_of("mgmt-host") == credentials


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
    assert config.management_credentials_of("mgmt-host") == None


@pytest.mark.parametrize("protocol,cred_attribute,credentials,folder_credentials", [
    ("snmp", "management_snmp_community", "HOST", "FOLDER"),
    ("ipmi", "management_ipmi_credentials", {
        "username"      : "USER",
        "password"      : "PASS",
    }, {
        "username"      : "FOLDERUSER",
        "password"      : "FOLDERPASS",
    }),
])
def test_mgmt_inherit_credentials_explicit_host(web, protocol, cred_attribute, credentials, folder_credentials):
    web.add_folder("folder1", attributes={
        cred_attribute: folder_credentials,
    })

    web.add_host("mgmt-host", folder="folder1", attributes={
        "ipaddress": "127.0.0.1",
        "management_protocol": protocol,
        cred_attribute: credentials,
    })

    reload_config()
    assert config.has_management_board("mgmt-host")
    assert config.management_address_of("mgmt-host") == "127.0.0.1"
    assert config.management_protocol_of("mgmt-host") == protocol
    assert config.management_credentials_of("mgmt-host") == credentials



@pytest.mark.parametrize("protocol,cred_attribute,credentials,folder_credentials", [
    ("snmp", "management_snmp_community", "HOST", "FOLDER"),
    ("ipmi", "management_ipmi_credentials", {
        "username"      : "USER",
        "password"      : "PASS",
    }, {
        "username"      : "FOLDERUSER",
        "password"      : "FOLDERPASS",
    }),
])
def test_mgmt_inherit_credentials(web, protocol, cred_attribute, credentials, folder_credentials):
    web.add_folder("folder1", attributes={
        cred_attribute: folder_credentials,
    })

    web.add_host("mgmt-host", folder="folder1", attributes={
        "ipaddress": "127.0.0.1",
        "management_protocol": protocol,
    })

    reload_config()
    assert config.has_management_board("mgmt-host")
    assert config.management_address_of("mgmt-host") == "127.0.0.1"
    assert config.management_protocol_of("mgmt-host") == protocol
    assert config.management_credentials_of("mgmt-host") == folder_credentials


@pytest.mark.parametrize("protocol,cred_attribute,credentials,folder_credentials", [
    ("snmp", "management_snmp_community", "HOST", "FOLDER"),
    ("ipmi", "management_ipmi_credentials", {
        "username"      : "USER",
        "password"      : "PASS",
    }, {
        "username"      : "FOLDERUSER",
        "password"      : "FOLDERPASS",
    }),
])
def test_mgmt_inherit_protocol_explicit_host(web, protocol, cred_attribute, credentials, folder_credentials):
    web.add_folder("folder1", attributes={
        "management_protocol": None,
        cred_attribute: folder_credentials,
    })

    web.add_host("mgmt-host", folder="folder1", attributes={
        "ipaddress": "127.0.0.1",
        "management_protocol": protocol,
        cred_attribute: credentials,
    })

    reload_config()
    assert config.has_management_board("mgmt-host")
    assert config.management_address_of("mgmt-host") == "127.0.0.1"
    assert config.management_protocol_of("mgmt-host") == protocol
    assert config.management_credentials_of("mgmt-host") == credentials



@pytest.mark.parametrize("protocol,cred_attribute,credentials,folder_credentials", [
    ("snmp", "management_snmp_community", "HOST", "FOLDER"),
    ("ipmi", "management_ipmi_credentials", {
        "username"      : "USER",
        "password"      : "PASS",
    }, {
        "username"      : "FOLDERUSER",
        "password"      : "FOLDERPASS",
    }),
])
def test_mgmt_inherit_protocol(web, protocol, cred_attribute, credentials, folder_credentials):
    web.add_folder("folder1", attributes={
        "management_protocol": protocol,
        cred_attribute: folder_credentials,
    })

    web.add_host("mgmt-host", folder="folder1", attributes={
        "ipaddress": "127.0.0.1",
    })

    reload_config()
    assert config.has_management_board("mgmt-host")
    assert config.management_address_of("mgmt-host") == "127.0.0.1"
    assert config.management_protocol_of("mgmt-host") == protocol
    assert config.management_credentials_of("mgmt-host") == folder_credentials


@pytest.mark.parametrize("protocol,cred_attribute,credentials,ruleset_credentials", [
    ("snmp", "management_snmp_community", "HOST", "RULESET"),
    ("ipmi", "management_ipmi_credentials", {
        "username"      : "USER",
        "password"      : "PASS",
    }, {
        "username"      : "RULESETUSER",
        "password"      : "RULESETPASS",
    }),
])
def test_mgmt_config_ruleset(web, protocol, cred_attribute, credentials, ruleset_credentials):
    web.set_ruleset("management_board_config", {
        "ruleset": {
            "": [ # "" -> folder
                {
                    'conditions': {
                        'host_specs': ['@all'],
                        'host_tags': []
                    },
                    'options': {},
                    'value': (protocol, ruleset_credentials),
                },
            ],
        }
    })

    web.add_folder("folder1")

    web.add_host("mgmt-host", folder="folder1", attributes={
        "ipaddress": "127.0.0.1",
        "management_protocol": protocol,
    })

    reload_config()
    assert config.has_management_board("mgmt-host")
    assert config.management_address_of("mgmt-host") == "127.0.0.1"
    assert config.management_protocol_of("mgmt-host") == protocol
    assert config.management_credentials_of("mgmt-host") == ruleset_credentials


@pytest.mark.parametrize("protocol,cred_attribute,folder_credentials,ruleset_credentials", [
    ("snmp", "management_snmp_community", "FOLDER", "RULESET"),
    ("ipmi", "management_ipmi_credentials", {
        "username"      : "FOLDERUSER",
        "password"      : "FOLDERPASS",
    }, {
        "username"      : "RULESETUSER",
        "password"      : "RULESETPASS",
    }),
])
def test_mgmt_config_ruleset_overidden_by_explicit_setting(web, protocol, cred_attribute, folder_credentials, ruleset_credentials):
    web.set_ruleset("management_board_config", {
        "ruleset": {
            "": [ # "" -> folder
                {
                    'conditions': {
                        'host_specs': ['@all'],
                        'host_tags': []
                    },
                    'options': {},
                    'value': (protocol, ruleset_credentials),
                },
            ],
        }
    })

    web.add_folder("folder1", attributes={
        cred_attribute: folder_credentials,
    })

    web.add_host("mgmt-host", folder="folder1", attributes={
        "ipaddress": "127.0.0.1",
        "management_protocol": protocol,
    })

    reload_config()
    assert config.has_management_board("mgmt-host")
    assert config.management_address_of("mgmt-host") == "127.0.0.1"
    assert config.management_protocol_of("mgmt-host") == protocol
    assert config.management_credentials_of("mgmt-host") == folder_credentials


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
