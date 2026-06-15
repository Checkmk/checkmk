#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="type-arg"


# Golden Tests for the LDAP connector
# trying to capture the current behavior of the connector to facilitate refactoring

import copy
import datetime
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from time import time
from unittest import mock
from unittest.mock import ANY, MagicMock

import ldap  # type: ignore[import-untyped,unused-ignore]
import ldap.ldapobject  # type: ignore[import-untyped,unused-ignore]
import pytest
from pytest_mock import MockerFixture

from cmk.ccc.user import UserId
from cmk.crypto.password import Password
from cmk.gui.ldap_integration.ldap_connector import (
    _sync_ldap_user,
    FetchedLDAPUser,
    LDAPUserConnector,
    LdapUsername,
    SyncUsersResult,
)
from cmk.gui.type_defs import Users, UserSpec
from cmk.gui.user_connection_config_types import (
    ActivePlugins,
    Fixed,
    LDAPConnectionConfigFixed,
    LDAPUserConnectionConfig,
    SyncAttribute,
    UserConnectionConfig,
)
from cmk.gui.userdb import get_user_attributes, UserAttribute
from cmk.gui.userdb.user_attributes import StartURLUserAttribute, TemperatureUnitUserAttribute
from cmk.gui.utils.security_log_events import UserManagementEvent


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
            ),
        ),
    ),
    user_dn="ou=People,dc=ldap_golden,dc=unit_tests,dc=local",
    user_scope="sub",
    user_id_umlauts="keep",
    group_dn="ou=Groups,dc=ldap_golden,dc=unit_tests,dc=local",
    group_scope="sub",
    active_plugins=ActivePlugins(
        start_url=SyncAttribute(attr="ldap_start_url"),
        temperature_unit=SyncAttribute(attr="ldap_temp_unit"),
    ),
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

    with mock.patch("cmk.utils.password_store.extract", return_value=None):
        connector.connect()

    assert connector._ldap_obj == mock_ldap.return_value, "Connector connects to mock"
    assert connector._ldap_obj_config == cfg, "Connector sets config for mock"

    assert len(mock_ldap.call_args_list) == 2, "Connected to main and failover server"
    mock_ldap.assert_called_with("ldap://internet")  # most recent

    # assumes "ldap_golden_unknown_password" is not in the password store, hence the 'None'.
    connector._ldap_obj.simple_bind_s.assert_called_with(  # type: ignore[union-attr]
        cfg["bind"][0], None
    )
    assert connector._ldap_obj.protocol_version == cfg["version"]  # type: ignore[union-attr]
    assert connector._ldap_obj.network_timeout == cfg["connect_timeout"]  # type: ignore[union-attr]


def _mock_result3(
    mocker: MockerFixture,
    connector: LDAPUserConnector,
    ldap_result: Sequence,
) -> None:
    """Make 'connector._ldap_object' return 'ldap_result' (plus some values that aren't used)."""
    mocker.patch.object(
        connector._ldap_obj,
        "result3",
        return_value=(
            0,
            ldap_result,
            0,
            [ldap.controls.SimplePagedResultsControl()],  # type: ignore[no-untyped-call]
        ),
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
            ldap.INVALID_CREDENTIALS(  # type: ignore[attr-defined,unused-ignore]
                {"desc": "Invalid credentials"}
            ),
            None,  # don't fail on the second call, which comes from _default_bind()
        ],
    )


def test_get_users(mocker: MockerFixture, mock_ldap: MagicMock) -> None:
    ldap_result = [
        ("user1", {"uid": [b"USER1_ID"]}),
        ("user2", {"uid": [b"USER2_ID#"]}),  # user with invalid user ID
    ]
    # note that the key is lower-cased due to 'lower_user_ids'
    expected_result = {
        "user1_id": FetchedLDAPUser(
            dn="user1",
            ldap_user_name="user1_id",
            ldap_user_spec={"dn": ["user1"], "uid": ["USER1_ID"]},
        ),
    }

    add_filter = "my(*)filter"
    expected_filter = f"(&(objectclass=person){add_filter})"

    cfg = _test_config
    connector = LDAPUserConnector(cfg)
    with mock.patch("cmk.utils.password_store.extract", return_value=None):
        connector.connect()
    assert connector._ldap_obj

    _mock_needed_attributes(mocker, connector)
    _mock_result3(mocker, connector, ldap_result)
    result = connector.get_users(get_user_attributes([]), add_filter=add_filter)

    assert expected_result == result
    connector._ldap_obj.search_ext.assert_called_once_with(  # type: ignore[attr-defined,unused-ignore]
        cfg["user_dn"],
        ldap.SCOPE_SUBTREE,  # type: ignore[attr-defined,unused-ignore]
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

    def assert_expected_users(
        users_to_save: Users,
        user_attributes: Sequence[tuple[str, UserAttribute]],
        user_connections: Sequence[UserConnectionConfig],
        _now: datetime.datetime,
        _pprint_value: bool,
        _call_users_saved_hook: bool,
    ) -> None:
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
        user_attributes=get_user_attributes([]),
        load_users_func=lambda _: loaded_users,
        save_users_func=assert_expected_users,
        default_user_profile={},
    )


def test_check_credentials_valid(
    mocker: MockerFixture,
    mock_ldap: MagicMock,
    request_context: None,
) -> None:
    connector = LDAPUserConnector(_test_config)
    with mock.patch("cmk.utils.password_store.extract", return_value="hunter2"):
        connector.connect()
        assert connector._ldap_obj

        _mock_result3(mocker, connector, [("carol", {"uid": [b"CAROL_ID"]})])

        result = connector.check_credentials(
            UserId("carol"),
            Password("hunter2"),
            get_user_attributes([]),
            [_test_config],
            default_user_profile={},
        )

        connector._ldap_obj.simple_bind_s.assert_any_call(  # type: ignore[attr-defined,unused-ignore]
            "carol", "hunter2"
        )
        assert result == UserId("carol_id")


def test_check_credentials_invalid(mocker: MockerFixture, mock_ldap: MagicMock) -> None:
    connector = LDAPUserConnector(_test_config)
    with mock.patch("cmk.utils.password_store.extract", return_value="hunter2"):
        connector.connect()
        assert connector._ldap_obj

        _mock_result3(mocker, connector, [("carol", {"uid": [b"CAROL_ID"]})])
        _mock_simple_bind_s(mocker, connector)
        assert (
            connector.check_credentials(
                UserId("carol"),
                Password("hunter2"),
                get_user_attributes([]),
                [_test_config],
                default_user_profile={},
            )
            is False
        )


def test_check_credentials_not_found(mocker: MockerFixture, mock_ldap: MagicMock) -> None:
    connector = LDAPUserConnector(_test_config)
    with mock.patch("cmk.utils.password_store.extract", return_value=None):
        connector.connect()
    assert connector._ldap_obj

    mocker.patch.object(connector, "_connection_id_of_user", return_value="htpasswd")
    _mock_result3(mocker, connector, [])
    assert (
        connector.check_credentials(
            UserId("alice"),
            Password("hunter2"),
            get_user_attributes([]),
            [_test_config],
            default_user_profile={},
        )
        is None
    )


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
                ),
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
    with mock.patch("cmk.utils.password_store.extract", return_value=None):
        connector.connect()

    mock_ldap.assert_called_with("ldap://lolcathorst")


@contextmanager
def with_crl_check() -> Iterator[None]:
    old_crl_check = ldap.get_option(ldap.OPT_X_TLS_CRLCHECK)  # type: ignore[attr-defined,no-untyped-call,unused-ignore]
    try:
        ldap.set_option(ldap.OPT_X_TLS_CRLCHECK, ldap.OPT_X_TLS_CRL_ALL)  # type: ignore[attr-defined,no-untyped-call,unused-ignore]
        yield
    finally:
        ldap.set_option(ldap.OPT_X_TLS_CRLCHECK, old_crl_check)  # type: ignore[attr-defined,no-untyped-call,unused-ignore]


def test_set_tls_options_overrides_global_crlcheck() -> None:
    """Regression test for SUP-28719.

    On OpenSSL-linked libldap, a new handle inherits the global OPT_X_TLS_CRLCHECK from ldap.conf.
    A globally configured 'TLS_CRLCHECK all' (e.g. via /etc/ldap/ldap.conf) would then enforce CRL
    checks on our handle, which fail in our environment because no CRL is loaded.

    _set_tls_options must override that inherited global to OPT_X_TLS_CRL_NONE on the handle.
    """
    if (backend := ldap.get_option(ldap.OPT_X_TLS_PACKAGE)) != "OpenSSL":  # type: ignore[attr-defined,no-untyped-call,unused-ignore]
        assert backend == "GnuTLS", f"Unexpected TLS backend: {backend}"
        pytest.skip("OPT_X_TLS_CRLCHECK is only relevant on OpenSSL backend, GnuTLS would raise")

    with with_crl_check():
        conn = ldap.ldapobject.ReconnectLDAPObject("ldaps://foobar.test")  # type: ignore[no-untyped-call,unused-ignore]
        # Precondition: new handle inherits the global setting for TLS_CRLCHECK
        assert conn.get_option(ldap.OPT_X_TLS_CRLCHECK) == ldap.OPT_X_TLS_CRL_ALL  # type: ignore[attr-defined,no-untyped-call,unused-ignore]

        LDAPUserConnector(
            {
                **_test_config,
                "use_ssl": True,
            },
        )._set_tls_options(conn)

        assert conn.get_option(ldap.OPT_X_TLS_CRLCHECK) == ldap.OPT_X_TLS_CRL_NONE  # type: ignore[attr-defined,no-untyped-call,unused-ignore]


def test_set_tls_options_gnutls_no_crlcheck_support() -> None:
    """Test that we didn't break the GnuTLS path with the fix for SUP-28719.

    I.e. with GnuTLS we must still be able to set use_ssl without crashing, even though
    OPT_X_TLS_CRLCHECK is not supported by the backend at all.
    """
    if ldap.get_option(ldap.OPT_X_TLS_PACKAGE) != "GnuTLS":  # type: ignore[attr-defined,no-untyped-call,unused-ignore]
        pytest.skip("CRLCHECK-unsupported path only meaningful on GnuTLS backend")

    conn = ldap.ldapobject.ReconnectLDAPObject("ldaps://foobar.test")  # type: ignore[no-untyped-call,unused-ignore]
    LDAPUserConnector(
        {
            **_test_config,
            "use_ssl": True,
        },
    )._set_tls_options(conn)  # must not raise


@dataclass
class SyncLdapData:
    fetched_ldap_user: FetchedLDAPUser
    existing_users: Users
    change_str: str
    expected_user_after_sync: dict[UserId, UserSpec]
    security_event: UserManagementEvent


sync_data: list[SyncLdapData] = [
    SyncLdapData(
        fetched_ldap_user=FetchedLDAPUser(
            dn="carol",
            ldap_user_name=LdapUsername("carol"),
            ldap_user_spec={
                "dn": ["carol"],
                "uid": ["CAROL_ID"],
                "ldap_start_url": ["mr_bojangles.py"],
                "ldap_temp_unit": ["celsius"],
            },
        ),
        existing_users=Users(
            {
                UserId("carol"): UserSpec(
                    alias="carol",
                    connector="test-golden-ldap-connector",
                    contactgroups=[],
                    customer="provider",
                    force_authuser=False,
                    locked=False,
                    roles=["user"],
                    serial=0,
                    start_url="welcome.py",
                    user_scheme_serial=1,
                ),
            },
        ),
        change_str="Changed start_url from welcome.py to mr_bojangles.py, Added: temperature_unit",
        expected_user_after_sync={
            UserId("carol"): UserSpec(
                alias="carol",
                connector="test-golden-ldap-connector",
                contactgroups=[],
                customer="provider",
                force_authuser=False,
                locked=False,
                roles=["user"],
                serial=0,
                user_scheme_serial=1,
                start_url="mr_bojangles.py",
                temperature_unit="celsius",
            ),
        },
        security_event=UserManagementEvent(
            event="user modified",
            affected_user=UserId("carol"),
            acting_user=UserId("admin_gav"),
            connector="ldap",
            connection_id="test-golden-ldap-connector",
        ),
    ),
    SyncLdapData(
        fetched_ldap_user=FetchedLDAPUser(
            dn="carol",
            ldap_user_name=LdapUsername("carol"),
            ldap_user_spec={
                "dn": ["carol"],
                "uid": ["CAROL_ID"],
                "ldap_start_url": ["mr_bojangles.py"],
                "ldap_temp_unit": ["celsius"],
            },
        ),
        existing_users=Users({}),
        change_str="Created user",
        expected_user_after_sync={
            UserId("carol"): UserSpec(
                alias="carol",
                connector="test-golden-ldap-connector",
                contactgroups=[],
                customer="provider",
                force_authuser=False,
                locked=False,
                roles=["user"],
                serial=0,
                user_scheme_serial=1,
                start_url="mr_bojangles.py",
                temperature_unit="celsius",
            ),
        },
        security_event=UserManagementEvent(
            event="user created",
            affected_user=UserId("carol"),
            acting_user=UserId("admin_gav"),
            connector="ldap",
            connection_id="test-golden-ldap-connector",
        ),
    ),
]


@pytest.mark.parametrize("sync_ldap_data", sync_data)
def test_ldap_sync(
    mocker: MockerFixture, sync_ldap_data: SyncLdapData, request_context: None
) -> None:
    mocker.patch("cmk.gui.ldap_integration.ldap_connector.logged_in_user_id", lambda: "admin_gav")
    # The connector is treated as an authentication connection so the "user
    # created" parametrization still creates users (creation is gated on
    # authentication_connections membership).
    mocker.patch.object(LDAPUserConnector, "is_authentication_connection", return_value=True)
    sync_user_result = SyncUsersResult(
        sync_start_time=time(),
        fetched_users={
            sync_ldap_data.fetched_ldap_user.ldap_user_name: sync_ldap_data.fetched_ldap_user
        },
    )

    user_id = _sync_ldap_user(
        fetched_ldap_user=sync_ldap_data.fetched_ldap_user,
        ldap_user_connector=LDAPUserConnector(_test_config),
        users=sync_ldap_data.existing_users,
        sync_users_result=sync_user_result,
        user_attributes=[
            ("start_url", StartURLUserAttribute()),
            ("temperature_unit", TemperatureUnitUserAttribute()),
        ],
        default_user_profile=UserSpec(
            contactgroups=[],
            roles=["user"],
            force_authuser=False,
        ),
    )

    assert user_id == UserId(sync_ldap_data.fetched_ldap_user.ldap_user_name)
    assert len(sync_user_result.changes) == 1
    assert sync_ldap_data.change_str in sync_user_result.changes[0]
    assert len(sync_user_result.security_events) == 1
    assert sync_user_result.security_events[0] == sync_ldap_data.security_event


_test_config_with_auth_expire = LDAPUserConnectionConfig(
    id="test-golden-ldap-connector",
    description="LDAP connector with auth_expire",
    comment="",
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
            ),
        ),
    ),
    user_dn="ou=People,dc=ldap_golden,dc=unit_tests,dc=local",
    user_scope="sub",
    user_id_umlauts="keep",
    group_dn="ou=Groups,dc=ldap_golden,dc=unit_tests,dc=local",
    group_scope="sub",
    active_plugins=ActivePlugins(
        auth_expire=SyncAttribute(),
    ),
    cache_livetime=300,
    type="ldap",
    bind=("bind_dn", ("store", "ldap_golden_unknown_password")),
    version=2,
    connect_timeout=0.1,
    lower_user_ids=True,
    suffix="LDAP_SUFFIX",
)


def test_check_credentials_with_auth_expire(
    mocker: MockerFixture,
    mock_ldap: MagicMock,
    request_context: None,
) -> None:
    """Login with auth_expire plugin enabled must request all needed LDAP attributes.

    Regression test: _get_user() used to fetch only the user-id attribute, so
    the auth_expire sync plugin could not find pwdchangedtime in the user spec.
    """
    connector = LDAPUserConnector(_test_config_with_auth_expire)
    with mock.patch("cmk.utils.password_store.extract", return_value="hunter2"):
        connector.connect()
        assert connector._ldap_obj

        _mock_result3(
            mocker,
            connector,
            [("carol", {"uid": [b"CAROL_ID"], "pwdchangedtime": [b"20250101000000Z"]})],
        )

        connector.check_credentials(
            UserId("carol"),
            Password("hunter2"),
            get_user_attributes([]),
            [_test_config_with_auth_expire],
            default_user_profile={},
        )

        search_ext_call = connector._ldap_obj.search_ext.call_args  # type: ignore[attr-defined,unused-ignore]
        requested_attrs = search_ext_call[1].get("attrlist") or search_ext_call[0][3]
        assert "pwdchangedtime" in requested_attrs, (
            f"auth_expire needs 'pwdchangedtime' but _get_user() only requested: {requested_attrs}"
        )


# --- CMK-33824: SAML→LDAP attribute-sync takeover ---------------------------
#
# When an LDAP background sync finds a directory entry that matches an existing
# SAML-owned user (by Checkmk UserId == LDAP username), the LDAP-wins rule
# (see doc/documentation/sec-auth-saml-ldap-attribute-sync.md) requires the
# LDAP connector to *take over* the user: flip ``connector`` to the LDAP id,
# overwrite LDAP-managed attributes, emit a security event + change entry, and
# log a clear TAKEOVER line. The tests below pin that behaviour.


def _stub_saml2_connection(
    connection_id: str,
    locked_attributes: list[str] | None = None,
) -> MagicMock:
    """Return a get_connection-compatible stub for a SAML2 connection.

    ``.type()`` and ``.id`` are read by the takeover gate; ``.locked_attributes()``
    is read when dropping the previous connection's attributes on takeover. The
    rest of the UserConnector surface is irrelevant here.
    """
    stub = MagicMock(spec=["type", "id", "locked_attributes"])
    stub.type.return_value = "saml2"
    stub.id = connection_id
    stub.locked_attributes.return_value = (
        ["password", "alias", "email", "contactgroups", "roles"]
        if locked_attributes is None
        else locked_attributes
    )
    return stub


def _stub_htpasswd_connection(connection_id: str) -> MagicMock:
    stub = MagicMock(spec=["type", "id"])
    stub.type.return_value = "htpasswd"
    stub.id = connection_id
    return stub


def _patch_get_connection(mocker: MockerFixture, mapping: dict[str, MagicMock]) -> None:
    mocker.patch(
        "cmk.gui.ldap_integration.ldap_connector.get_connection",
        side_effect=mapping.get,
    )


_carol_ldap_fetch = FetchedLDAPUser(
    dn="carol",
    ldap_user_name=LdapUsername("carol"),
    ldap_user_spec={
        "dn": ["carol"],
        "uid": ["CAROL_ID"],
        "ldap_start_url": ["mr_bojangles.py"],
        "ldap_temp_unit": ["celsius"],
    },
)


def _saml_owned_carol(connection_id: str = "saml2_corp") -> UserSpec:
    return UserSpec(
        alias="carol",
        connector=connection_id,
        contactgroups=[],
        customer="provider",
        force_authuser=False,
        locked=False,
        roles=["user"],
        serial=0,
        start_url="welcome.py",
        user_scheme_serial=1,
    )


def _ldap_default_user_profile() -> UserSpec:
    return UserSpec(
        contactgroups=[],
        roles=["user"],
        force_authuser=False,
    )


def _ldap_user_attributes() -> list[tuple[str, UserAttribute]]:
    return [
        ("start_url", StartURLUserAttribute()),
        ("temperature_unit", TemperatureUnitUserAttribute()),
    ]


_test_config_no_suffix = LDAPUserConnectionConfig(
    {**_test_config, "suffix": None},  # type: ignore[typeddict-item]
)


def test_sync_takes_over_saml_owned_user(mocker: MockerFixture, request_context: None) -> None:
    """A SAML-owned user with a matching LDAP entry is taken over by LDAP sync.

    Connector flips to the LDAP id and LDAP-managed attributes are written.
    """
    mocker.patch("cmk.gui.ldap_integration.ldap_connector.logged_in_user_id", lambda: "admin_gav")
    _patch_get_connection(mocker, {"saml2_corp": _stub_saml2_connection("saml2_corp")})

    existing_users: Users = {UserId("carol"): _saml_owned_carol()}
    sync_user_result = SyncUsersResult(
        sync_start_time=time(),
        fetched_users={_carol_ldap_fetch.ldap_user_name: _carol_ldap_fetch},
    )

    user_id = _sync_ldap_user(
        fetched_ldap_user=_carol_ldap_fetch,
        ldap_user_connector=LDAPUserConnector(_test_config),
        users=existing_users,
        sync_users_result=sync_user_result,
        user_attributes=_ldap_user_attributes(),
        default_user_profile=_ldap_default_user_profile(),
    )

    assert user_id == UserId("carol"), "takeover keeps the bare UserId"
    taken_over = existing_users[UserId("carol")]
    assert taken_over["connector"] == _test_config["id"], "connector flipped to LDAP"
    assert taken_over["start_url"] == "mr_bojangles.py", "LDAP attribute synced"
    assert taken_over["temperature_unit"] == "celsius", "LDAP attribute synced"


def test_takeover_drops_attributes_provided_by_saml(
    mocker: MockerFixture, request_context: None
) -> None:
    """On takeover, attributes the SAML connector managed are dropped.

    CMK-33824: stale SAML values must not linger when the LDAP connection does
    not re-provide them. Attributes present in the site default profile reset to
    that default; the rest are removed entirely. The LDAP connector in this test
    (`_test_config`) only syncs ``start_url`` and ``temperature_unit`` — it does
    NOT provide email/contactgroups/roles — so those SAML values must disappear.
    """
    mocker.patch("cmk.gui.ldap_integration.ldap_connector.logged_in_user_id", lambda: "admin_gav")
    _patch_get_connection(mocker, {"saml2_corp": _stub_saml2_connection("saml2_corp")})

    saml_user = UserSpec(
        alias="Carol from SAML",
        connector="saml2_corp",
        contactgroups=["saml-only-group"],
        customer="provider",
        email="carol@saml.example",
        force_authuser=False,
        locked=False,
        roles=["admin"],
        serial=0,
        start_url="welcome.py",
        user_scheme_serial=1,
    )
    existing_users: Users = {UserId("carol"): saml_user}
    sync_user_result = SyncUsersResult(
        sync_start_time=time(),
        fetched_users={_carol_ldap_fetch.ldap_user_name: _carol_ldap_fetch},
    )

    _sync_ldap_user(
        fetched_ldap_user=_carol_ldap_fetch,
        ldap_user_connector=LDAPUserConnector(_test_config),
        users=existing_users,
        sync_users_result=sync_user_result,
        user_attributes=_ldap_user_attributes(),
        default_user_profile=_ldap_default_user_profile(),
    )

    taken_over = existing_users[UserId("carol")]
    assert taken_over["connector"] == _test_config["id"]
    # `email` is not in the default profile -> removed outright.
    assert "email" not in taken_over, "stale SAML email must be dropped"
    # `contactgroups` and `roles` are in the default profile -> reset to default.
    assert taken_over["contactgroups"] == [], "SAML contact groups reset to default"
    assert taken_over["roles"] == ["user"], "SAML roles reset to default"
    # LDAP-provided attributes are still applied.
    assert taken_over["start_url"] == "mr_bojangles.py"
    assert taken_over["temperature_unit"] == "celsius"


def test_sync_does_not_touch_saml_only_user(mocker: MockerFixture, request_context: None) -> None:
    """A SAML-owned user with NO matching LDAP entry is left untouched.

    ``do_sync`` only iterates fetched LDAP users, so a SAML-only user is never reached by the takeover path.
    """
    connector = LDAPUserConnector(_test_config)
    saml_only_user = _saml_owned_carol("saml2_corp")
    saml_only_user["alias"] = "alice"
    loaded_users: Users = {UserId("alice"): copy.deepcopy(saml_only_user)}
    _patch_get_connection(mocker, {"saml2_corp": _stub_saml2_connection("saml2_corp")})

    # `_complete_sync` only calls `save_users_func` when there are changes;
    # this test asserts there are *no* changes, so we observe the in-place
    # mutated `loaded_users` directly.
    def fail_if_save_called(*_a: object, **_k: object) -> None:
        raise AssertionError("save_users_func must not be called when nothing changed")

    mocker.patch.object(connector, "get_users", return_value={})
    connector.do_sync(
        add_to_changelog=True,
        only_username=None,
        user_attributes=get_user_attributes([]),
        load_users_func=lambda _: loaded_users,
        save_users_func=fail_if_save_called,
        default_user_profile={},
    )

    assert loaded_users == {UserId("alice"): saml_only_user}, (
        "SAML-only user untouched and no other users created"
    )


def test_sync_for_ldap_only_users_unchanged(mocker: MockerFixture, request_context: None) -> None:
    """A regular LDAP-owned user still receives the standard modify event.

    The new takeover branch must not affect users that were already owned by the LDAP connector.
    This pins today's modify path.
    """
    mocker.patch("cmk.gui.ldap_integration.ldap_connector.logged_in_user_id", lambda: "admin_gav")
    # No SAML connector registered — only the LDAP one matters here.
    _patch_get_connection(mocker, {})

    ldap_owned_carol = UserSpec(
        alias="carol",
        connector=_test_config["id"],
        contactgroups=[],
        customer="provider",
        force_authuser=False,
        locked=False,
        roles=["user"],
        serial=0,
        start_url="welcome.py",
        user_scheme_serial=1,
    )
    existing_users: Users = {UserId("carol"): ldap_owned_carol}
    sync_user_result = SyncUsersResult(
        sync_start_time=time(),
        fetched_users={_carol_ldap_fetch.ldap_user_name: _carol_ldap_fetch},
    )

    user_id = _sync_ldap_user(
        fetched_ldap_user=_carol_ldap_fetch,
        ldap_user_connector=LDAPUserConnector(_test_config),
        users=existing_users,
        sync_users_result=sync_user_result,
        user_attributes=_ldap_user_attributes(),
        default_user_profile=_ldap_default_user_profile(),
    )

    assert user_id == UserId("carol")
    assert existing_users[UserId("carol")]["connector"] == _test_config["id"]
    # Standard modify path: a single "user modified" event, no takeover entry
    # in the change log.
    assert sync_user_result.security_events == [
        UserManagementEvent(
            event="user modified",
            affected_user=UserId("carol"),
            acting_user=UserId("admin_gav"),
            connector="ldap",
            connection_id=_test_config["id"],
        )
    ]
    assert not any("ook over" in c for c in sync_user_result.changes), (
        "LDAP-only sync must not emit a takeover change entry"
    )


def test_sync_does_not_take_over_htpasswd_user(
    mocker: MockerFixture, request_context: None
) -> None:
    """Takeover is SAML-only — htpasswd-owned users fall through to today's
    name-conflict skip path.
    """
    mocker.patch("cmk.gui.ldap_integration.ldap_connector.logged_in_user_id", lambda: "admin_gav")
    _patch_get_connection(mocker, {"htpasswd": _stub_htpasswd_connection("htpasswd")})

    htpasswd_carol = UserSpec(
        alias="carol",
        connector="htpasswd",
        contactgroups=[],
        roles=["user"],
        serial=0,
        start_url="welcome.py",
        user_scheme_serial=1,
    )
    existing_users: Users = {UserId("carol"): copy.deepcopy(htpasswd_carol)}
    sync_user_result = SyncUsersResult(
        sync_start_time=time(),
        fetched_users={_carol_ldap_fetch.ldap_user_name: _carol_ldap_fetch},
    )

    user_id = _sync_ldap_user(
        fetched_ldap_user=_carol_ldap_fetch,
        ldap_user_connector=LDAPUserConnector(_test_config_no_suffix),
        users=existing_users,
        sync_users_result=sync_user_result,
        user_attributes=_ldap_user_attributes(),
        default_user_profile=_ldap_default_user_profile(),
    )

    assert user_id is None, "name-conflict skip path returns None"
    assert existing_users[UserId("carol")] == htpasswd_carol, "htpasswd user untouched"
    assert sync_user_result.security_events == [], "no audit event for skipped user"


def test_takeover_emits_security_event_and_change(
    mocker: MockerFixture, request_context: None
) -> None:
    """Takeover records a 'user modified' security event AND a change entry
    that explicitly names the ownership transfer.
    """
    mocker.patch("cmk.gui.ldap_integration.ldap_connector.logged_in_user_id", lambda: "admin_gav")
    _patch_get_connection(mocker, {"saml2_corp": _stub_saml2_connection("saml2_corp")})

    existing_users: Users = {UserId("carol"): _saml_owned_carol()}
    sync_user_result = SyncUsersResult(
        sync_start_time=time(),
        fetched_users={_carol_ldap_fetch.ldap_user_name: _carol_ldap_fetch},
    )

    _sync_ldap_user(
        fetched_ldap_user=_carol_ldap_fetch,
        ldap_user_connector=LDAPUserConnector(_test_config),
        users=existing_users,
        sync_users_result=sync_user_result,
        user_attributes=_ldap_user_attributes(),
        default_user_profile=_ldap_default_user_profile(),
    )

    # An explicit takeover entry appears in the change log alongside the
    # standard modify entry. Substring match keeps the test resilient to
    # i18n / minor wording tweaks.
    assert any("ook over" in c for c in sync_user_result.changes), (
        f"missing takeover entry; changes were: {sync_user_result.changes!r}"
    )
    # The audit event is a 'user modified' under the LDAP connector — no new
    # event type is needed; the connector + connection_id tell the full story.
    assert sync_user_result.security_events == [
        UserManagementEvent(
            event="user modified",
            affected_user=UserId("carol"),
            acting_user=UserId("admin_gav"),
            connector="ldap",
            connection_id=_test_config["id"],
        )
    ]


def test_takeover_with_suffix_keeps_bare_userid(
    mocker: MockerFixture, request_context: None
) -> None:
    """Takeover reuses the bare UserId even when the LDAP connector has a
    suffix configured. Existing users are never renamed
    (see cmk/gui/ldap_integration/ldap_suffix_flow.md).
    """
    mocker.patch("cmk.gui.ldap_integration.ldap_connector.logged_in_user_id", lambda: "admin_gav")
    _patch_get_connection(mocker, {"saml2_corp": _stub_saml2_connection("saml2_corp")})

    assert _test_config.get("suffix"), "fixture must have a suffix for this test"
    existing_users: Users = {UserId("carol"): _saml_owned_carol()}
    sync_user_result = SyncUsersResult(
        sync_start_time=time(),
        fetched_users={_carol_ldap_fetch.ldap_user_name: _carol_ldap_fetch},
    )

    user_id = _sync_ldap_user(
        fetched_ldap_user=_carol_ldap_fetch,
        ldap_user_connector=LDAPUserConnector(_test_config),
        users=existing_users,
        sync_users_result=sync_user_result,
        user_attributes=_ldap_user_attributes(),
        default_user_profile=_ldap_default_user_profile(),
    )

    assert user_id == UserId("carol"), "no rename to <name>@<suffix>"
    suffixed = UserId(f"carol@{_test_config['suffix']}")
    assert suffixed not in existing_users, (
        f"takeover must not create a suffixed duplicate; found {suffixed!r}"
    )


# .--creation gating-----------------------------------------------------.
# |   User creation during the periodic sync is reserved for connectors  |
# |   listed in `authentication_connections`. Connectors that only       |
# |   appear in `user_attribute_sync_connections` update existing users  |
# |   (and delete users they own that left LDAP) but never create new    |
# |   ones. See doc/documentation/sec-auth-ldap-creation-gating.md.      |
# '----------------------------------------------------------------------'


def test_sync_skips_creation_for_attr_only_connector(
    mocker: MockerFixture, request_context: None
) -> None:
    """A connector absent from `authentication_connections` must not create a
    new user during the periodic background sync (`login_attempt=False`).
    """
    mocker.patch("cmk.gui.ldap_integration.ldap_connector.logged_in_user_id", lambda: "admin_gav")
    _patch_get_connection(mocker, {})
    connector = LDAPUserConnector(_test_config_no_suffix)
    mocker.patch.object(connector, "is_authentication_connection", return_value=False)

    existing_users: Users = {}
    sync_user_result = SyncUsersResult(
        sync_start_time=time(),
        fetched_users={_carol_ldap_fetch.ldap_user_name: _carol_ldap_fetch},
    )

    user_id = _sync_ldap_user(
        fetched_ldap_user=_carol_ldap_fetch,
        ldap_user_connector=connector,
        users=existing_users,
        sync_users_result=sync_user_result,
        user_attributes=_ldap_user_attributes(),
        default_user_profile=_ldap_default_user_profile(),
    )

    assert user_id is None, "no user created for an attribute-sync-only connector"
    assert existing_users == {}, "no user added to the site"
    assert sync_user_result.security_events == [], "no 'user created' event emitted"


def test_sync_creates_user_for_authentication_connector(
    mocker: MockerFixture, request_context: None
) -> None:
    """A connector listed in `authentication_connections` still creates new
    users during the periodic sync — the gate does not change this path.
    """
    mocker.patch("cmk.gui.ldap_integration.ldap_connector.logged_in_user_id", lambda: "admin_gav")
    _patch_get_connection(mocker, {})
    connector = LDAPUserConnector(_test_config_no_suffix)
    mocker.patch.object(connector, "is_authentication_connection", return_value=True)

    existing_users: Users = {}
    sync_user_result = SyncUsersResult(
        sync_start_time=time(),
        fetched_users={_carol_ldap_fetch.ldap_user_name: _carol_ldap_fetch},
    )

    user_id = _sync_ldap_user(
        fetched_ldap_user=_carol_ldap_fetch,
        ldap_user_connector=connector,
        users=existing_users,
        sync_users_result=sync_user_result,
        user_attributes=_ldap_user_attributes(),
        default_user_profile=_ldap_default_user_profile(),
    )

    assert user_id == UserId("carol"), "user created for an authentication connector"
    created = existing_users[UserId("carol")]
    assert created["connector"] == _test_config_no_suffix["id"]
    assert created["start_url"] == "mr_bojangles.py", "LDAP attributes applied on creation"
    assert created["temperature_unit"] == "celsius"
    assert any(event.summary == "user created" for event in sync_user_result.security_events)


def test_sync_updates_existing_user_for_attr_only_connector(
    mocker: MockerFixture, request_context: None
) -> None:
    """An attribute-sync-only connector still updates an existing user it owns.
    The creation gate sits on the new-user branch only.
    """
    mocker.patch("cmk.gui.ldap_integration.ldap_connector.logged_in_user_id", lambda: "admin_gav")
    _patch_get_connection(mocker, {})
    connector = LDAPUserConnector(_test_config_no_suffix)
    mocker.patch.object(connector, "is_authentication_connection", return_value=False)

    ldap_owned_carol = UserSpec(
        alias="carol",
        connector=_test_config_no_suffix["id"],
        contactgroups=[],
        force_authuser=False,
        locked=False,
        roles=["user"],
        serial=0,
        start_url="stale.py",
        temperature_unit="fahrenheit",
        user_scheme_serial=1,
    )
    existing_users: Users = {UserId("carol"): ldap_owned_carol}
    sync_user_result = SyncUsersResult(
        sync_start_time=time(),
        fetched_users={_carol_ldap_fetch.ldap_user_name: _carol_ldap_fetch},
    )

    user_id = _sync_ldap_user(
        fetched_ldap_user=_carol_ldap_fetch,
        ldap_user_connector=connector,
        users=existing_users,
        sync_users_result=sync_user_result,
        user_attributes=_ldap_user_attributes(),
        default_user_profile=_ldap_default_user_profile(),
    )

    assert user_id == UserId("carol")
    updated = existing_users[UserId("carol")]
    assert updated["connector"] == _test_config_no_suffix["id"], "ownership unchanged"
    assert updated["start_url"] == "mr_bojangles.py", "attributes refreshed from LDAP"
    assert updated["temperature_unit"] == "celsius"


def test_sync_takeover_still_works_for_attr_only_connector(
    mocker: MockerFixture, request_context: None
) -> None:
    """The CMK-33824 SAML->LDAP takeover still applies for a connector that is
    only in `user_attribute_sync_connections`: takeover acts on an
    already-existing user, so the creation gate does not affect it.
    """
    mocker.patch("cmk.gui.ldap_integration.ldap_connector.logged_in_user_id", lambda: "admin_gav")
    _patch_get_connection(mocker, {"saml2_corp": _stub_saml2_connection("saml2_corp")})
    connector = LDAPUserConnector(_test_config)
    mocker.patch.object(connector, "is_authentication_connection", return_value=False)

    existing_users: Users = {UserId("carol"): _saml_owned_carol()}
    sync_user_result = SyncUsersResult(
        sync_start_time=time(),
        fetched_users={_carol_ldap_fetch.ldap_user_name: _carol_ldap_fetch},
    )

    user_id = _sync_ldap_user(
        fetched_ldap_user=_carol_ldap_fetch,
        ldap_user_connector=connector,
        users=existing_users,
        sync_users_result=sync_user_result,
        user_attributes=_ldap_user_attributes(),
        default_user_profile=_ldap_default_user_profile(),
    )

    assert user_id == UserId("carol")
    taken_over = existing_users[UserId("carol")]
    assert taken_over["connector"] == _test_config["id"], "takeover still flips the connector"
    assert taken_over["start_url"] == "mr_bojangles.py", "LDAP attributes still synced"


def test_sync_attr_only_connector_deletes_owned_user_gone_from_ldap(
    mocker: MockerFixture, request_context: None
) -> None:
    """Deletion follows ownership, not auth membership: an attribute-sync-only
    connector still removes a user it owns once that user leaves the LDAP
    directory. The removal pass is unchanged.
    """
    mocker.patch("cmk.gui.ldap_integration.ldap_connector.logged_in_user_id", lambda: "admin_gav")
    log_security_event = mocker.patch("cmk.gui.ldap_integration.ldap_connector.log_security_event")
    connector = LDAPUserConnector(_test_config_no_suffix)
    mocker.patch.object(connector, "is_authentication_connection", return_value=False)

    users: Users = {
        UserId("bob"): UserSpec(alias="bob", connector=_test_config_no_suffix["id"]),
    }
    sync_user_result = SyncUsersResult(sync_start_time=time(), fetched_users={})

    connector._remove_checkmk_users_that_are_no_longer_in_the_ldap_instance(
        users=users,
        ldap_users={},
        sync_users_result=sync_user_result,
    )

    assert UserId("bob") not in users, "owned user absent from LDAP is removed"
    assert any("emoved" in change for change in sync_user_result.changes), (
        f"missing removal change entry; changes were: {sync_user_result.changes!r}"
    )
    assert log_security_event.call_args is not None
    assert log_security_event.call_args.args[0].summary == "user deleted"
