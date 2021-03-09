#!/usr/bin/env python
# TODO: This should be realized as unit tests

import pytest
from testlib import web

import cmk_base.config as config


@pytest.fixture(scope="function")
def clear_config_caches(monkeypatch):
    import cmk_base
    import cmk_base.caching
    monkeypatch.setattr(cmk_base, "config_cache", cmk_base.caching.CacheManager())
    monkeypatch.setattr(cmk_base, "runtime_cache", cmk_base.caching.CacheManager())


def reload_config():
    # Needs to be done together, even when the checks are not directly needed
    import cmk_base.check_api as check_api
    config.load_all_checks(check_api.get_check_api_context)
    config.load()

    config_cache = config.get_config_cache()
    config_cache.initialize()
    return config_cache


@pytest.fixture(scope="function")
def enable_debug():
    import cmk.utils.debug
    cmk.utils.debug.enable()
    yield
    cmk.utils.debug.disable()


@pytest.fixture(autouse=True)
def test_cfg(web, clear_config_caches, enable_debug):
    reload_config()
    yield

    #
    # Cleanup code
    #
    print "Cleaning up test config"

    if web.host_exists("mgmt-host"):
        web.delete_host("mgmt-host")

    if web.folder_exists("folder1"):
        web.delete_folder("folder1")

    web.set_ruleset(
        "management_board_config",
        {
            "ruleset": {
                "": [],  # -> folder
            }
        })

    web.activate_changes()


@pytest.mark.parametrize("protocol,cred_attribute,credentials", [
    ("snmp", "management_snmp_community", "HOST"),
    ("ipmi", "management_ipmi_credentials", {
        "username": "USER",
        "password": "PASS",
    }),
])
def test_mgmt_explicit_settings(web, protocol, cred_attribute, credentials):
    web.add_host("mgmt-host",
                 attributes={
                     "ipaddress": "127.0.0.1",
                     "management_protocol": protocol,
                     cred_attribute: credentials,
                 })

    config_cache = reload_config()
    host_config = config_cache.get_host_config("mgmt-host")
    assert host_config.has_management_board
    assert host_config.management_protocol == protocol
    assert host_config.management_address == "127.0.0.1"
    assert host_config.management_credentials == credentials


def test_mgmt_explicit_address(web):
    web.add_host("mgmt-host",
                 attributes={
                     "ipaddress": "127.0.0.1",
                     "management_protocol": "snmp",
                     "management_address": "127.0.0.2",
                 })

    config_cache = reload_config()
    host_config = config_cache.get_host_config("mgmt-host")
    assert host_config.has_management_board
    assert host_config.management_protocol == "snmp"
    assert host_config.management_address == "127.0.0.2"
    assert host_config.management_credentials == "public"


def test_mgmt_disabled(web):
    web.add_host("mgmt-host",
                 attributes={
                     "ipaddress": "127.0.0.1",
                     "management_protocol": None,
                     "management_address": "127.0.0.1",
                     "management_snmp_community": "HOST",
                 })

    config_cache = reload_config()
    host_config = config_cache.get_host_config("mgmt-host")
    assert host_config.has_management_board is False
    assert host_config.management_protocol is None
    assert host_config.management_address == "127.0.0.1"
    assert host_config.management_credentials is None


@pytest.mark.parametrize("protocol,cred_attribute,credentials,folder_credentials", [
    ("snmp", "management_snmp_community", "HOST", "FOLDER"),
    ("ipmi", "management_ipmi_credentials", {
        "username": "USER",
        "password": "PASS",
    }, {
        "username": "FOLDERUSER",
        "password": "FOLDERPASS",
    }),
])
def test_mgmt_inherit_credentials_explicit_host(web, protocol, cred_attribute, credentials,
                                                folder_credentials):
    web.add_folder("folder1", attributes={
        cred_attribute: folder_credentials,
    })

    web.add_host("mgmt-host",
                 folder="folder1",
                 attributes={
                     "ipaddress": "127.0.0.1",
                     "management_protocol": protocol,
                     cred_attribute: credentials,
                 })

    config_cache = reload_config()
    host_config = config_cache.get_host_config("mgmt-host")
    assert host_config.has_management_board
    assert host_config.management_protocol == protocol
    assert host_config.management_address == "127.0.0.1"
    assert host_config.management_credentials == credentials


@pytest.mark.parametrize("protocol,cred_attribute,credentials,folder_credentials", [
    ("snmp", "management_snmp_community", "HOST", "FOLDER"),
    ("ipmi", "management_ipmi_credentials", {
        "username": "USER",
        "password": "PASS",
    }, {
        "username": "FOLDERUSER",
        "password": "FOLDERPASS",
    }),
])
def test_mgmt_inherit_credentials(web, protocol, cred_attribute, credentials, folder_credentials):
    web.add_folder("folder1", attributes={
        cred_attribute: folder_credentials,
    })

    web.add_host("mgmt-host",
                 folder="folder1",
                 attributes={
                     "ipaddress": "127.0.0.1",
                     "management_protocol": protocol,
                 })

    config_cache = reload_config()
    host_config = config_cache.get_host_config("mgmt-host")
    assert host_config.has_management_board
    assert host_config.management_protocol == protocol
    assert host_config.management_address == "127.0.0.1"
    assert host_config.management_credentials == folder_credentials


@pytest.mark.parametrize("protocol,cred_attribute,credentials,folder_credentials", [
    ("snmp", "management_snmp_community", "HOST", "FOLDER"),
    ("ipmi", "management_ipmi_credentials", {
        "username": "USER",
        "password": "PASS",
    }, {
        "username": "FOLDERUSER",
        "password": "FOLDERPASS",
    }),
])
def test_mgmt_inherit_protocol_explicit_host(web, protocol, cred_attribute, credentials,
                                             folder_credentials):
    web.add_folder("folder1",
                   attributes={
                       "management_protocol": None,
                       cred_attribute: folder_credentials,
                   })

    web.add_host("mgmt-host",
                 folder="folder1",
                 attributes={
                     "ipaddress": "127.0.0.1",
                     "management_protocol": protocol,
                     cred_attribute: credentials,
                 })

    config_cache = reload_config()
    host_config = config_cache.get_host_config("mgmt-host")
    assert host_config.has_management_board
    assert host_config.management_protocol == protocol
    assert host_config.management_address == "127.0.0.1"
    assert host_config.management_credentials == credentials


@pytest.mark.parametrize("protocol,cred_attribute,credentials,folder_credentials", [
    ("snmp", "management_snmp_community", "HOST", "FOLDER"),
    ("ipmi", "management_ipmi_credentials", {
        "username": "USER",
        "password": "PASS",
    }, {
        "username": "FOLDERUSER",
        "password": "FOLDERPASS",
    }),
])
def test_mgmt_inherit_protocol(web, protocol, cred_attribute, credentials, folder_credentials):
    web.add_folder("folder1",
                   attributes={
                       "management_protocol": protocol,
                       cred_attribute: folder_credentials,
                   })

    web.add_host("mgmt-host", folder="folder1", attributes={
        "ipaddress": "127.0.0.1",
    })

    config_cache = reload_config()
    host_config = config_cache.get_host_config("mgmt-host")
    assert host_config.has_management_board
    assert host_config.management_protocol == protocol
    assert host_config.management_address == "127.0.0.1"
    assert host_config.management_credentials == folder_credentials


@pytest.mark.parametrize("protocol,cred_attribute,credentials,ruleset_credentials", [
    ("snmp", "management_snmp_community", "HOST", "RULESET"),
    ("ipmi", "management_ipmi_credentials", {
        "username": "USER",
        "password": "PASS",
    }, {
        "username": "RULESETUSER",
        "password": "RULESETPASS",
    }),
])
def test_mgmt_config_ruleset(web, protocol, cred_attribute, credentials, ruleset_credentials):
    web.set_ruleset(
        "management_board_config",
        {
            "ruleset": {
                "": [  # "" -> folder
                    {
                        'condition': {},
                        'options': {},
                        'value': (protocol, ruleset_credentials),
                    },
                ],
            }
        })

    web.add_folder("folder1")

    web.add_host("mgmt-host",
                 folder="folder1",
                 attributes={
                     "ipaddress": "127.0.0.1",
                     "management_protocol": protocol,
                 })

    config_cache = reload_config()
    host_config = config_cache.get_host_config("mgmt-host")
    assert host_config.has_management_board
    assert host_config.management_protocol == protocol
    assert host_config.management_address == "127.0.0.1"
    assert host_config.management_credentials == ruleset_credentials


@pytest.mark.parametrize("protocol,cred_attribute,folder_credentials,ruleset_credentials", [
    ("snmp", "management_snmp_community", "FOLDER", "RULESET"),
    ("ipmi", "management_ipmi_credentials", {
        "username": "FOLDERUSER",
        "password": "FOLDERPASS",
    }, {
        "username": "RULESETUSER",
        "password": "RULESETPASS",
    }),
])
def test_mgmt_config_ruleset_overidden_by_explicit_setting(web, protocol, cred_attribute,
                                                           folder_credentials, ruleset_credentials):
    web.set_ruleset(
        "management_board_config",
        {
            "ruleset": {
                "": [  # "" -> folder
                    {
                        'condition': {},
                        'options': {},
                        'value': (protocol, ruleset_credentials),
                    },
                ],
            }
        })

    web.add_folder("folder1", attributes={
        cred_attribute: folder_credentials,
    })

    web.add_host("mgmt-host",
                 folder="folder1",
                 attributes={
                     "ipaddress": "127.0.0.1",
                     "management_protocol": protocol,
                 })

    config_cache = reload_config()
    host_config = config_cache.get_host_config("mgmt-host")
    assert host_config.has_management_board
    assert host_config.management_protocol == protocol
    assert host_config.management_address == "127.0.0.1"
    assert host_config.management_credentials == folder_credentials


def test_mgmt_config_ruleset_order(web):
    web.set_ruleset(
        "management_board_config",
        {
            "ruleset": {
                "": [  # "" -> folder
                    {
                        'condition': {},
                        'options': {},
                        'value': ("snmp", "RULESET1"),
                    },
                    {
                        'condition': {},
                        'options': {},
                        'value': ("snmp", "RULESET2"),
                    },
                ],
            }
        })

    web.add_folder("folder1")

    web.add_host("mgmt-host",
                 folder="folder1",
                 attributes={
                     "ipaddress": "127.0.0.1",
                     "management_protocol": "snmp",
                 })

    config_cache = reload_config()
    host_config = config_cache.get_host_config("mgmt-host")
    assert host_config.has_management_board
    assert host_config.management_protocol == "snmp"
    assert host_config.management_address == "127.0.0.1"
    assert host_config.management_credentials == "RULESET1"
