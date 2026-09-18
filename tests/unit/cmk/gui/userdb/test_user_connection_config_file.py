#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Unit tests for ``UserConnectionConfigFile`` validation of migrated connections.

After the ``user_sync`` / ``owned_by_site`` migrations run, the resulting LDAP
and SAML connection specs must still validate against the current schema when
they are loaded through ``UserConnectionConfigFile`` — no validation error.
"""

import pytest

from cmk.gui.user_connection_config_types import (
    ActivePlugins,
    Fixed,
    LDAPConnectionConfigFixed,
    LDAPUserConnectionConfig,
    SAMLUserConnectionConfig,
    SyncAttribute,
)
from cmk.gui.userdb import UserConnectionConfigFile
from cmk.gui.validation_utils import ConfigValidationError

# A SAML connection in the post-migration shape (no obsolete ``owned_by_site``).
_VALID_SAML = SAMLUserConnectionConfig(
    {
        "type": "saml2",
        "version": "1.0.0",
        "id": "my_lovely_saml",
        "name": "härbärt",
        "description": "",
        "comment": "",
        "docu_url": "",
        "disabled": False,
        "checkmk_entity_id": "http://localhost/heute/check_mk/saml_metadata.py",
        "checkmk_metadata_endpoint": "http://localhost/heute/check_mk/saml_metadata.py?RelayState=my_lovely_saml",
        "checkmk_assertion_consumer_service_endpoint": "http://localhost/heute/check_mk/saml_acs.py?acs",
        "connection_timeout": (12, 12),
        "checkmk_server_url": "https://localhost",
        "idp_metadata": ("url", "https://localhost:8080/simplesaml/saml2/idp/metadata.php"),
        "user_id_attribute_name": "username",
        "user_alias_attribute_name": "",
        "email_attribute_name": "",
        "contactgroups_mapping": "no_mapping",
        "role_membership_mapping": False,
        "signature_certificate": "builtin",
    }
)

# An LDAP connection spec in the current schema.
_VALID_LDAP = LDAPUserConnectionConfig(
    id="test-ldap-connector",
    description="LDAP connector for unit tests",
    comment="",
    docu_url="",
    disabled=False,
    directory_type=(
        "openldap",
        LDAPConnectionConfigFixed(
            connect_to=(
                "fixed_list",
                Fixed(server="localhorst", failover_servers=["internet"]),
            ),
        ),
    ),
    user_dn="ou=People,dc=corp,dc=local",
    user_scope="sub",
    user_id_umlauts="keep",
    group_dn="ou=Groups,dc=corp,dc=local",
    group_scope="sub",
    active_plugins=ActivePlugins(start_url=SyncAttribute(attr="ldap_start_url")),
    cache_livetime=300,
    type="ldap",
    bind=("bind_dn", ("store", "ldap_unknown_password")),
    version=2,
    connect_timeout=0.1,
    lower_user_ids=True,
    suffix="LDAP_SUFFIX",
)


def test_migrated_connections_validate() -> None:
    """Migrated SAML and LDAP connection specs pass the config-file
    schema validation with no error, and round-trip their ids."""
    validated = UserConnectionConfigFile().validate([_VALID_SAML, _VALID_LDAP])
    assert [conn["id"] for conn in validated] == [_VALID_SAML["id"], _VALID_LDAP["id"]]


def test_invalid_connection_is_rejected() -> None:
    """Negative: a connection missing required schema fields raises
    ``ConfigValidationError`` — proving the validation is actually enforced and
    the positive case above is meaningful."""
    broken = {"type": "saml2", "id": "broken"}
    with pytest.raises(ConfigValidationError):
        UserConnectionConfigFile().validate([broken])
