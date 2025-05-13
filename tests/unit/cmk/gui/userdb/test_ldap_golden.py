#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


# Golden Tests for the LDAP connector
# trying to capture the current behavior of the connector to facilitate refactoring

import datetime
from collections.abc import Sequence
from unittest import mock
from unittest.mock import ANY, MagicMock

import ldap  # type: ignore[import-untyped]
import pytest
from pytest_mock import MockerFixture

from cmk.ccc.user import UserId

from cmk.gui.type_defs import Users
from cmk.gui.userdb._connections import Fixed, LDAPConnectionConfigFixed, LDAPUserConnectionConfig
from cmk.gui.userdb.ldap_connector import LDAPUserConnector

from cmk.crypto.password import Password


@pytest.fixture(name="mock_ldap", autouse=True)
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

    with mock.patch("cmk.utils.password_store.extract", return_value=None):
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
    with mock.patch("cmk.utils.password_store.extract", return_value=None):
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


def test_check_credentials_valid(mocker: MockerFixture, request_context: None) -> None:
    connector = LDAPUserConnector(_test_config)
    with mock.patch("cmk.utils.password_store.extract", return_value="hunter2"):
        connector.connect()
        assert connector._ldap_obj

        _mock_result3(mocker, connector, [("carol", {"uid": [b"CAROL_ID"]})])

        result = connector.check_credentials(UserId("carol"), Password("hunter2"))

        connector._ldap_obj.simple_bind_s.assert_any_call("carol", "hunter2")
        assert result == UserId("carol_id")


def test_check_credentials_invalid(mocker: MockerFixture, request_context: None) -> None:
    connector = LDAPUserConnector(_test_config)
    with mock.patch("cmk.utils.password_store.extract", return_value="hunter2"):
        connector.connect()
        assert connector._ldap_obj

        _mock_result3(mocker, connector, [("carol", {"uid": [b"CAROL_ID"]})])
        _mock_simple_bind_s(mocker, connector)
        assert connector.check_credentials(UserId("carol"), Password("hunter2")) is False


def test_check_credentials_not_found(mocker: MockerFixture) -> None:
    connector = LDAPUserConnector(_test_config)
    with mock.patch("cmk.utils.password_store.extract", return_value=None):
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
    with mock.patch("cmk.utils.password_store.extract", return_value=None):
        connector.connect()

    mock_ldap.assert_called_with("ldap://lolcathorst")
