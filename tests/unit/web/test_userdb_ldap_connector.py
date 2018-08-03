#!/usr/bin/env python

import pytest

import cmk.gui.plugins.userdb.ldap_connector as ldap
import cmk.gui.plugins.userdb.utils as userdb_utils

def test_connector_info():
    assert ldap.LDAPUserConnector.type() == "ldap"
    assert "LDAP" in ldap.LDAPUserConnector.title()
    assert ldap.LDAPUserConnector.short_title() == "LDAP"


def test_connector_registered():
    assert userdb_utils.user_connector_registry.get("ldap") == ldap.LDAPUserConnector

