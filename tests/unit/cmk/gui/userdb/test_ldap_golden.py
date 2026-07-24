#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# pylint: disable=protected-access

# Golden Tests for the LDAP connector
# trying to capture the current behavior of the connector to facilitate refactoring

import datetime
from collections.abc import Sequence
from contextlib import contextmanager
from unittest.mock import ANY, MagicMock

import ldap  # type: ignore[import-untyped]
import ldap.ldapobject  # type: ignore[import-untyped]
import pytest
from pytest_mock import MockerFixture

from cmk.utils.user import UserId

from cmk.gui.type_defs import Users
from cmk.gui.userdb._connections import (
    Fixed,
    GroupsToAttributes,
    GroupsToRoles,
    GroupsToSync,
    LDAPConnectionConfigFixed,
    LDAPUserConnectionConfig,
)
from cmk.gui.userdb.ldap_connector import (
    LDAPAttributePluginGroupAttributes,
    LDAPAttributePluginGroupsToRoles,
    LDAPUserConnector,
    LDAPUserSpec,
)

from cmk.crypto.password import Password


@pytest.fixture(name="mock_ldap")
def fixture_mock_ldap_object(mocker: MockerFixture) -> MagicMock:
    """Mock the ReconnectLDAPObject and return the mock object.
    The actual instance of the mock, that can be used to check method calls, is
    `mock_ldap.return_value`.
    """
    return mocker.patch("ldap.ldapobject.ReconnectLDAPObject", autospec=True)


_test_config = LDAPUserConnectionConfig(
    id="test-golden-ldap-connector",
    description="LDAP connector for unit tests",
    comment="Hi!",
    docu_url="",
    disabled=False,
    directory_type=(
        "openldap",
        LDAPConnectionConfigFixed(
            connect_to=(
                "fixed_list",
                Fixed(
                    server="lolcathorst",
                    failover_servers=["internet"],
                ),
            )
        ),
    ),
    user_dn="ou=People,dc=ldap_golden,dc=unit_tests,dc=local",
    user_scope="sub",
    user_id_umlauts="keep",
    group_dn="ou=Groups,dc=ldap_golden,dc=unit_tests,dc=local",
    group_scope="sub",
    active_plugins={"email": {}},
    cache_livetime=300,
    type="ldap",
    bind=("bind_dn", ("store", "ldap_golden_unknown_password")),  # not in password_store
    version=2,
    connect_timeout=0.1,
    lower_user_ids=True,
    suffix="LDAP_SUFFIX",
)


@pytest.mark.parametrize(
    "config",
    [
        {
            "id": "test-golden-ldap-connector",
            "directory_type": ("ad", {"connect_to": ("discover", {"domain": "corp.de"})}),
        },
        {
            "id": "test-golden-ldap-connector",
            "directory_type": (
                "fixed_list",
                {"server": "localhorst", "failover_servers": ["internet"]},
            ),
        },
    ],
)
def test_init_connector(config: LDAPUserConnectionConfig) -> None:
    """Test initializing the connector with a given config"""
    LDAPUserConnector(config)


def test_connect(mock_ldap: MagicMock) -> None:
    cfg = _test_config
    connector = LDAPUserConnector(cfg)
    connector.connect()

    assert connector._ldap_obj == mock_ldap.return_value, "Connector connects to mock"
    assert connector._ldap_obj_config == cfg, "Connector sets config for mock"

    assert len(mock_ldap.call_args_list) == 2, "Connected to main and failover server"
    mock_ldap.assert_called_with("ldap://internet")  # most recent

    # assumes "ldap_golden_unknown_password" is not in the password store, hence the 'None'.
    connector._ldap_obj.simple_bind_s.assert_called_with(cfg["bind"][0], None)
    assert connector._ldap_obj.protocol_version == cfg["version"]
    assert connector._ldap_obj.network_timeout == cfg["connect_timeout"]


def _mock_result3(
    mocker: MockerFixture, connector: LDAPUserConnector, ldap_result: Sequence
) -> None:
    """Make 'connector._ldap_object' return 'ldap_result' (plus some values that aren't used)."""
    mocker.patch.object(
        connector._ldap_obj,
        "result3",
        return_value=(0, ldap_result, 0, [ldap.controls.SimplePagedResultsControl()]),
    )


def _mock_needed_attributes(mocker: MockerFixture, connector: LDAPUserConnector) -> None:
    # LDAPUserConnector._needed_attributes uses a set to collect the attributes so we could not
    # rely on the order in our assertion. Fix one.
    mocker.patch.object(connector, "_needed_attributes", return_value=["mail", "cn"])


def _mock_simple_bind_s(mocker: MockerFixture, connector: LDAPUserConnector) -> None:
    mocker.patch.object(
        connector._ldap_obj,
        "simple_bind_s",
        side_effect=[
            ldap.INVALID_CREDENTIALS({"desc": "Invalid credentials"}),
            None,  # don't fail on the second call, which comes from _default_bind()
        ],
    )


def test_get_users(mocker: MockerFixture, mock_ldap: MagicMock) -> None:
    ldap_result = [
        ("user1", {"uid": [b"USER1_ID"]}),
        ("user2", {"uid": [b"USER2_ID#"]}),  # user with invalid user ID
    ]
    # note that the key is lower-cased due to 'lower_user_ids'
    expected_result = {"user1_id": {"dn": ["user1"], "uid": ["USER1_ID"]}}
    add_filter = "my(*)filter"
    expected_filter = f"(&(objectclass=person){add_filter})"

    cfg = _test_config
    connector = LDAPUserConnector(cfg)
    connector.connect()
    assert connector._ldap_obj

    _mock_needed_attributes(mocker, connector)
    _mock_result3(mocker, connector, ldap_result)
    result = connector.get_users(add_filter=add_filter)

    assert expected_result == result
    connector._ldap_obj.search_ext.assert_called_once_with(
        cfg["user_dn"],
        ldap.SCOPE_SUBTREE,
        expected_filter,
        AnyOrderMatcher(["uid", "mail", "cn"]),
        serverctrls=ANY,
    )


class AnyOrderMatcher:
    def __init__(self, args: Sequence):
        self.args = args

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, list):
            raise ValueError(f"Invalid value: {other!r}")
        return set(other) == set(self.args)

    def __repr__(self) -> str:
        return f"AnyOrderMatcher({self.args})"


def test_do_sync(mocker: MockerFixture, request_context: None) -> None:
    connector = LDAPUserConnector(_test_config)
    loaded_users: Users = {
        UserId("alice"): {"connector": "htpasswd"},
        UserId("bob"): {"connector": connector.id},
        UserId("david"): {"connector": connector.id, "alias": "dave"},
    }
    ldap_users = {
        "carol": {"connector": connector.id},
        "david": {"connector": connector.id},
        "alice": {"connector": connector.id},
    }

    def assert_expected_users(users_to_save: Users, _now: datetime.datetime) -> None:
        assert UserId("alice") in users_to_save
        assert users_to_save[UserId("alice")]["connector"] == "htpasswd"
        assert UserId("bob") not in users_to_save
        assert UserId("carol") in users_to_save
        assert users_to_save[UserId("carol")]["connector"] == connector.id
        assert users_to_save[UserId("carol")]["alias"] == "carol"
        assert UserId("david") in users_to_save
        assert users_to_save[UserId("david")]["alias"] == "dave"
        assert UserId("alice@LDAP_SUFFIX") in users_to_save
        assert users_to_save[UserId("alice@LDAP_SUFFIX")]["connector"] == connector.id

    mocker.patch.object(connector, "get_users", return_value=ldap_users)
    connector.do_sync(
        add_to_changelog=True,
        only_username=None,
        load_users_func=lambda _: loaded_users,
        save_users_func=assert_expected_users,
    )


def test_check_credentials_valid(
    mocker: MockerFixture, mock_ldap: MagicMock, request_context: None
) -> None:
    connector = LDAPUserConnector(_test_config)
    connector.connect()
    assert connector._ldap_obj

    _mock_result3(mocker, connector, [("carol", {"uid": [b"CAROL_ID"]})])
    result = connector.check_credentials(UserId("carol"), Password("hunter2"))

    connector._ldap_obj.simple_bind_s.assert_any_call("carol", "hunter2")
    assert result == UserId("carol_id")


def test_check_credentials_invalid(
    mocker: MockerFixture, mock_ldap: MagicMock, request_context: None
) -> None:
    connector = LDAPUserConnector(_test_config)
    connector.connect()
    assert connector._ldap_obj

    _mock_result3(mocker, connector, [("carol", {"uid": [b"CAROL_ID"]})])
    _mock_simple_bind_s(mocker, connector)
    assert connector.check_credentials(UserId("carol"), Password("hunter2")) is False


def test_check_credentials_not_found(mocker: MockerFixture, mock_ldap: MagicMock) -> None:
    connector = LDAPUserConnector(_test_config)
    connector.connect()
    assert connector._ldap_obj

    mocker.patch.object(connector, "_connection_id_of_user", return_value="htpasswd")
    assert connector.check_credentials(UserId("alice"), Password("hunter2")) is None


def test_remove_trailing_dot_from_hostname(mock_ldap: MagicMock) -> None:
    cfg = LDAPUserConnectionConfig(
        id="test-trailing-dot-server",
        directory_type=(
            "openldap",
            LDAPConnectionConfigFixed(
                connect_to=(
                    "fixed_list",
                    Fixed(
                        server="lolcathorst.",
                    ),
                )
            ),
        ),
        user_dn="ou=People,dc=ldap_golden,dc=unit_tests,dc=local",
        user_scope="sub",
        user_id_umlauts="keep",
        group_dn="ou=Groups,dc=ldap_golden,dc=unit_tests,dc=local",
        group_scope="sub",
        active_plugins={"email": {}},
        cache_livetime=300,
        type="ldap",
        bind=("bind_dn", ("store", "ldap_golden_unknown_password")),  # not in password_store
        version=2,
        connect_timeout=0.1,
        lower_user_ids=True,
        suffix="TEST_TRAILING_DOT",
        disabled=False,
        description="",
        comment="",
        docu_url="",
    )

    connector = LDAPUserConnector(cfg)
    connector.connect()

    mock_ldap.assert_called_with("ldap://lolcathorst")


@contextmanager
def with_crl_check():
    old_crl_check = ldap.get_option(ldap.OPT_X_TLS_CRLCHECK)
    try:
        ldap.set_option(ldap.OPT_X_TLS_CRLCHECK, ldap.OPT_X_TLS_CRL_ALL)
        yield
    finally:
        ldap.set_option(ldap.OPT_X_TLS_CRLCHECK, old_crl_check)


def test_set_tls_options_overrides_global_crlcheck() -> None:
    """Regression test for SUP-28719.

    On OpenSSL-linked libldap, a new handle inherits the global OPT_X_TLS_CRLCHECK from ldap.conf.
    A globally configured 'TLS_CRLCHECK all' (e.g. via /etc/ldap/ldap.conf) would then enforce CRL
    checks on our handle, which fail in our environment because no CRL is loaded.

    _set_tls_options must override that inherited global to OPT_X_TLS_CRL_NONE on the handle.
    """
    if (backend := ldap.get_option(ldap.OPT_X_TLS_PACKAGE)) != "OpenSSL":
        assert backend == "GnuTLS", f"Unexpected TLS backend: {backend}"
        pytest.skip("OPT_X_TLS_CRLCHECK is only relevant on OpenSSL backend, GnuTLS would raise")

    with with_crl_check():
        conn = ldap.ldapobject.ReconnectLDAPObject("ldaps://foobar.test")
        # Precondition: new handle inherits the global setting for TLS_CRLCHECK
        assert conn.get_option(ldap.OPT_X_TLS_CRLCHECK) == ldap.OPT_X_TLS_CRL_ALL

        LDAPUserConnector(
            {
                **_test_config,
                "use_ssl": True,
            }
        )._set_tls_options(conn)

        assert conn.get_option(ldap.OPT_X_TLS_CRLCHECK) == ldap.OPT_X_TLS_CRL_NONE


def test_set_tls_options_gnutls_no_crlcheck_support() -> None:
    """Test that we didn't break the GnuTLS path with the fix for SUP-28719.

    I.e. with GnuTLS we must still be able to set use_ssl without crashing, even though
    OPT_X_TLS_CRLCHECK is not supported by the backend at all.
    """
    if ldap.get_option(ldap.OPT_X_TLS_PACKAGE) != "GnuTLS":
        pytest.skip("CRLCHECK-unsupported path only meaningful on GnuTLS backend")

    conn = ldap.ldapobject.ReconnectLDAPObject("ldaps://foobar.test")
    LDAPUserConnector(
        {
            **_test_config,
            "use_ssl": True,
        }
    )._set_tls_options(conn)  # must not raise


def _patch_get_connection(
    mocker: MockerFixture, mapping: dict[str, MagicMock | LDAPUserConnector]
) -> None:
    mocker.patch(
        "cmk.gui.userdb.ldap_connector.get_connection",
        side_effect=mapping.get,
    )


@pytest.mark.parametrize(
    "group_spec, mocked_return, expected_ldap_groups",
    [
        (
            ("CN=cmk-admins,OU=groups,DC=example,DC=com", "ldap_with_groups"),
            {
                "cn=cmk-admins,ou=groups,dc=example,dc=com": {
                    "cn": "cmk-admins",
                    "members": ["alice"],
                }
            },
            {
                "cn=cmk-admins,ou=groups,dc=example,dc=com": {
                    "cn": "cmk-admins",
                    "members": ["alice"],
                }
            },
        ),
        (
            ("cmk-admins", "ldap_with_groups"),
            {
                "cn=cmk-admins,ou=groups,dc=example,dc=com": {
                    "cn": "cmk-admins",
                    "members": ["alice"],
                }
            },
            {"cmk-admins": {"cn": "cmk-admins", "members": ["alice"]}},
        ),
        (
            ("CN=cmk-admins,OU=groups,DC=example,DC=com", "ldap_with_groups"),
            {
                "CN=Cmk-Admins,OU=Groups,DC=Example,DC=Com": {
                    "cn": "Cmk-Admins",
                    "members": ["alice"],
                }
            },
            {
                "cn=cmk-admins,ou=groups,dc=example,dc=com": {
                    "cn": "Cmk-Admins",
                    "members": ["alice"],
                }
            },
        ),
        (
            ("cmk-admins", "ldap_with_groups"),
            {
                "cn=cmk-admins,ou=groups,dc=example,dc=com": {
                    "cn": "Cmk-Admins",
                    "members": ["alice"],
                }
            },
            {"cmk-admins": {"cn": "Cmk-Admins", "members": ["alice"]}},
        ),
    ],
    ids=["dn", "cn", "dn_case", "cn_case"],
)
def test_fetch_needed_groups_for_groups_to_roles_with_cn_or_dn(
    mocker: MockerFixture,
    group_spec: tuple[str, str],
    mocked_return: dict[str, dict[str, object]],
    expected_ldap_groups: dict[str, dict[str, object]],
) -> None:
    """Test a typical use case with DN OR CN"""
    connection = LDAPUserConnector(_test_config)
    mocker.patch.object(
        connection,
        "_get_group_memberships",
        return_value=mocked_return,
    )
    _patch_get_connection(mocker, {"ldap_with_groups": connection})

    params: GroupsToRoles = {"admin": [group_spec]}
    ldap_groups = LDAPAttributePluginGroupsToRoles().fetch_needed_groups_for_groups_to_roles(
        connection, params
    )

    assert ldap_groups == expected_ldap_groups


@pytest.mark.parametrize(
    "admin_value",
    [
        [("cmk-admins", None)],
        ["cmk-admins"],
        "cmk-admins",
    ],
    ids=["tuple", "list_str", "str"],
)
def test_fetch_needed_groups_for_groups_to_roles_outliers(
    mocker: MockerFixture, admin_value: object
) -> None:
    """Test outlier scenarios of tuple with none, list no connection id, just string"""
    connection = LDAPUserConnector(_test_config)
    mocker.patch.object(
        connection,
        "_get_group_memberships",
        return_value={
            "cn=cmk-admins,ou=groups,dc=example,dc=com": {
                "cn": "cmk-admins",
                "members": ["alice"],
            },
        },
    )
    _patch_get_connection(mocker, {connection.id: connection})

    params: GroupsToRoles = {"admin": admin_value}  # type: ignore[dict-item]
    ldap_groups = LDAPAttributePluginGroupsToRoles().fetch_needed_groups_for_groups_to_roles(
        connection, params
    )

    assert ldap_groups == {"cmk-admins": {"cn": "cmk-admins", "members": ["alice"]}}


@pytest.mark.parametrize(
    "group_spec, mocked_return, is_assigned",
    [
        (
            "cmk-admins",
            {
                "cn=cmk-admins,ou=groups,dc=example,dc=com": {
                    "cn": "cmk-admins",
                    "members": ["alice"],
                }
            },
            True,
        ),
        (
            "CN=cmk-admins,OU=groups,DC=example,DC=com",
            {
                "cn=cmk-admins,ou=groups,dc=example,dc=com": {
                    "cn": "cmk-admins",
                    "members": ["alice"],
                }
            },
            True,
        ),
        (
            "cmk-admins",
            {
                "cn=cmk-admins,ou=groups,dc=example,dc=com": {
                    "cn": "Cmk-Admins",
                    "members": ["alice"],
                }
            },
            True,
        ),
        (
            "CN=cmk-admins,OU=groups,DC=example,DC=com",
            {
                "CN=Cmk-Admins,OU=Groups,DC=Example,DC=Com": {
                    "cn": "Cmk-Admins",
                    "members": ["alice"],
                }
            },
            True,
        ),
        (
            "cmk-admins",
            {
                "cn=cmk-admins,ou=groups,dc=example,dc=com": {
                    "cn": "cmk-admins",
                    "members": ["bob"],
                }
            },
            False,
        ),
        (
            "CN=cmk-admins,OU=groups,DC=example,DC=com",
            {
                "cn=cmk-admins,ou=groups,dc=example,dc=com": {
                    "cn": "cmk-admins",
                    "members": ["bob"],
                }
            },
            False,
        ),
    ],
    ids=["cn_match", "dn_match", "cn_case", "dn_case", "cn_wrong_user", "dn_wrong_user"],
)
def test_groups_to_roles_and_groups_to_attributes_work_with_dn_or_cn(
    mocker: MockerFixture,
    request_context: None,
    group_spec: str,
    mocked_return: dict[str, dict[str, object]],
    is_assigned: bool,
) -> None:
    """This test ensures that even with the group_dn and group_cn spec differences,that a user
    providing either a DN or CN will still produce the expected user assignment based on the group.
    Additionally, this change as better improved case insensitivity"""
    connection = LDAPUserConnector(_test_config)
    mocker.patch.object(connection, "_get_group_memberships", return_value=mocked_return)
    _patch_get_connection(mocker, {connection.id: connection})

    ldap_user: LDAPUserSpec = {"dn": ["alice"]}

    roles_result = LDAPAttributePluginGroupsToRoles().sync_func(
        connection,
        "",
        {"admin": [(group_spec, None)]},
        UserId("alice"),
        ldap_user,
        {},
    )
    attrs_result = LDAPAttributePluginGroupAttributes().sync_func(
        connection,
        "",
        dict(
            GroupsToAttributes(
                groups=[GroupsToSync(cn=group_spec, attribute=("ldap_temp_unit", "fahrenheit"))]
            ),
        ),
        UserId("alice"),
        ldap_user,
        {},
    )

    assert ("admin" in roles_result.get("roles", [])) == is_assigned
    assert (attrs_result.get("ldap_temp_unit") == "fahrenheit") == is_assigned


def test_fetch_needed_groups_for_groups_to_roles_multiple_groups_in_one_role(
    mocker: MockerFixture,
) -> None:
    """A role mapped to a list of several groups must fetch all of them, not just the last one."""
    connection = LDAPUserConnector(_test_config)

    def _memberships(
        names: list[str], filt_attr: str | None = None, nested: bool = False
    ) -> dict[str, dict[str, object]]:
        return {name: {"cn": name, "members": ["alice"]} for name in names}

    mocker.patch.object(connection, "_get_group_memberships", side_effect=_memberships)
    _patch_get_connection(mocker, {connection.id: connection})

    params: GroupsToRoles = {"admin": [("cmk-admins", None), ("cmk-superusers", None)]}
    ldap_groups = LDAPAttributePluginGroupsToRoles().fetch_needed_groups_for_groups_to_roles(
        connection, params
    )

    assert ldap_groups == {
        "cmk-admins": {"cn": "cmk-admins", "members": ["alice"]},
        "cmk-superusers": {"cn": "cmk-superusers", "members": ["alice"]},
    }


def test_fetch_needed_groups_for_groups_to_roles_empty_group_list(
    mocker: MockerFixture,
) -> None:
    """A role mapped to an empty group list must fetch nothing instead of crashing."""
    connection = LDAPUserConnector(_test_config)
    mocker.patch.object(connection, "_get_group_memberships", return_value={})
    _patch_get_connection(mocker, {connection.id: connection})

    params: GroupsToRoles = {"admin": []}
    ldap_groups = LDAPAttributePluginGroupsToRoles().fetch_needed_groups_for_groups_to_roles(
        connection, params
    )

    assert ldap_groups == {}
