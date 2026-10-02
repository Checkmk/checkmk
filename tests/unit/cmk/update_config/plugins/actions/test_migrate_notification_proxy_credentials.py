#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
from datetime import datetime
from logging import getLogger

import pytest

from cmk.ccc.user import UserId
from cmk.gui import userdb
from cmk.gui.config import active_config
from cmk.gui.userdb.store import load_users_uncached
from cmk.gui.watolib.hosts_and_folders import FolderTree
from cmk.gui.watolib.notifications import NotificationParameterConfigFile
from cmk.gui.watolib.password_store import PasswordStore
from cmk.gui.watolib.rulesets import Rule, Ruleset, RulesetCollection
from cmk.gui.watolib.rulespecs import rulespec_registry
from cmk.ruleset_matcher.definition import RuleGroup
from cmk.update_config.plugins.actions.migrate_notification_proxy_credentials import (
    migrate_notification_parameter_rules,
    migrate_notification_parameters,
    migrate_proxy_credentials,
    migrate_user_notification_rules,
    proxy_methods,
    ProxyCredentialsMigration,
    save_new_passwords,
)
from cmk.update_config.plugins.lib.rulesets import transform_wato_rulesets_params
from cmk.update_config.registry import update_action_registry
from cmk.utils import password_store
from cmk.utils.http_proxy_config import http_proxy_config_from_user_setting
from cmk.utils.password_store import PasswordConfig

_METHODS = frozenset({"slack", "pushover"})
_URL_WITH_CREDENTIALS = "http://user:s3crit@proxy.lan:3128"


def _parameters(
    *proxy_urls: object, method: str = "slack"
) -> dict[str, dict[str, dict[str, object]]]:
    return {
        method: {
            f"param_{nr}": {
                "general": {"description": f"Parameter {nr}", "comment": "", "docu_url": ""},
                "parameter_properties": {
                    "webhook_url": ("webhook_url", "https://hooks.slack.com/services/x"),
                    "proxy_url": proxy_url,
                },
            }
            for nr, proxy_url in enumerate(proxy_urls, start=1)
        }
    }


def _proxy(
    parameters: dict[str, dict[str, dict[str, object]]],
    parameter_id: str = "param_1",
    method: str = "slack",
) -> object:
    properties = parameters[method][parameter_id]["parameter_properties"]
    assert isinstance(properties, dict)
    return properties["proxy_url"]


def _explicit(url: str) -> tuple[str, str, str]:
    return ("cmk_postprocessed", "explicit_proxy", url)


def test_credentials_are_moved_into_an_administrator_password_store_entry() -> None:
    parameters = _parameters(_explicit(_URL_WITH_CREDENTIALS))
    migration = ProxyCredentialsMigration(set(), getLogger())

    assert migrate_notification_parameters(parameters, _METHODS, migration)

    assert _proxy(parameters) == (
        "cmk_postprocessed",
        "explicit_proxy",
        {
            "scheme": "http",
            "proxy_server_name": "proxy.lan",
            "port": 3128,
            "auth": {
                "user": "user",
                "password": (
                    "cmk_postprocessed",
                    "stored_password",
                    ("notification_proxy_user_at_proxy_lan_3128_1", ""),
                ),
            },
        },
    )
    entry = migration.new_passwords["notification_proxy_user_at_proxy_lan_3128_1"]
    assert (entry["title"], entry["password"], entry["owned_by"], entry["shared_with"]) == (
        "Proxy credentials of user@proxy.lan:3128",
        "s3crit",
        None,
        [],
    )


def test_same_credentials_share_one_entry() -> None:
    parameters = _parameters(_explicit(_URL_WITH_CREDENTIALS), ("url", _URL_WITH_CREDENTIALS))
    migration = ProxyCredentialsMigration(set(), getLogger())

    migrate_notification_parameters(parameters, _METHODS, migration)

    assert list(migration.new_passwords) == ["notification_proxy_user_at_proxy_lan_3128_1"]
    assert (
        "'param_1', notification parameter 'param_2'"
        in (migration.new_passwords["notification_proxy_user_at_proxy_lan_3128_1"]["comment"])
    )


def test_different_credentials_get_entries_of_their_own() -> None:
    parameters = _parameters(
        _explicit(_URL_WITH_CREDENTIALS), _explicit("http://user:other@proxy.lan:3128")
    )
    migration = ProxyCredentialsMigration(set(), getLogger())

    migrate_notification_parameters(parameters, _METHODS, migration)

    assert sorted(migration.new_passwords) == [
        "notification_proxy_user_at_proxy_lan_3128_1",
        "notification_proxy_user_at_proxy_lan_3128_2",
    ]


def test_password_id_does_not_overwrite_existing_entries() -> None:
    parameters = _parameters(_explicit(_URL_WITH_CREDENTIALS))
    migration = ProxyCredentialsMigration(
        {"notification_proxy_user_at_proxy_lan_3128_1"}, getLogger()
    )

    migrate_notification_parameters(parameters, _METHODS, migration)

    assert list(migration.new_passwords) == ["notification_proxy_user_at_proxy_lan_3128_2"]


def _password(secret: str) -> PasswordConfig:
    return PasswordConfig(
        title="title", comment="", docu_url="", password=secret, owned_by=None, shared_with=[]
    )


def test_new_passwords_keep_existing_entries() -> None:
    PasswordStore().save(
        {"existing": _password("secret")}, pprint_value=False, update_merged_file=False
    )

    save_new_passwords({"new": _password("s3crit")}, pprint_value=False)

    stored = PasswordStore().load_for_reading()
    assert {password_id: spec["password"] for password_id, spec in stored.items()} == {
        "existing": "secret",
        "new": "s3crit",
    }


def test_proxy_without_credentials_creates_no_password() -> None:
    parameters = _parameters(_explicit("http://proxy.lan:3128"))
    migration = ProxyCredentialsMigration(set(), getLogger())

    assert migrate_notification_parameters(parameters, _METHODS, migration)

    assert _proxy(parameters) == (
        "cmk_postprocessed",
        "explicit_proxy",
        {"scheme": "http", "proxy_server_name": "proxy.lan", "port": 3128},
    )
    assert not migration.new_passwords


@pytest.mark.parametrize(
    "proxy_url",
    [
        pytest.param(("cmk_postprocessed", "environment_proxy", ""), id="environment"),
        pytest.param(("cmk_postprocessed", "stored_proxy", "global_proxy"), id="global proxy"),
        pytest.param(
            (
                "cmk_postprocessed",
                "explicit_proxy",
                {"scheme": "http", "proxy_server_name": "proxy.lan", "port": 3128},
            ),
            id="already structured",
        ),
    ],
)
def test_other_proxy_settings_are_left_alone(proxy_url: object) -> None:
    parameters = _parameters(proxy_url)
    migration = ProxyCredentialsMigration(set(), getLogger())

    assert not migrate_notification_parameters(parameters, _METHODS, migration)
    assert _proxy(parameters) == proxy_url


def test_plugins_without_the_structured_proxy_are_left_alone() -> None:
    """Notification plug-ins of extension packages still use the plain proxy URL"""
    proxy_url = _explicit(_URL_WITH_CREDENTIALS)
    parameters = _parameters(proxy_url, method="my_mkp_plugin")
    migration = ProxyCredentialsMigration(set(), getLogger())

    assert not migrate_notification_parameters(parameters, _METHODS, migration)
    assert _proxy(parameters, method="my_mkp_plugin") == proxy_url


def test_unconvertible_url_moves_its_credentials_and_is_reported(
    caplog: pytest.LogCaptureFixture,
) -> None:
    parameters = _parameters(_explicit("http://user:s3crit@proxy.lan:port"))
    migration = ProxyCredentialsMigration(set(), getLogger())

    with caplog.at_level(logging.INFO):
        assert migrate_notification_parameters(parameters, _METHODS, migration)

    match _proxy(parameters):
        case (
            "cmk_postprocessed",
            "explicit_proxy",
            {"port": 0, "auth": {"password": (_, "stored_password", (password_id, ""))}},
        ):
            assert migration.new_passwords[password_id]["password"] == "s3crit"
        case other:
            pytest.fail(f"Unexpected proxy: {other!r}")
    assert "cannot be fully converted" in caplog.text
    assert "s3crit" not in caplog.text


def test_moved_credentials_are_not_logged(caplog: pytest.LogCaptureFixture) -> None:
    parameters = _parameters(_explicit(_URL_WITH_CREDENTIALS))

    with caplog.at_level(logging.DEBUG):
        migrate_notification_parameters(
            parameters, _METHODS, ProxyCredentialsMigration(set(), getLogger())
        )

    assert "notification_proxy_user_at_proxy_lan_3128_1" in caplog.text
    assert "s3crit" not in caplog.text


def _user_with_proxy_rule(url: str) -> dict[str, object]:
    return {
        "contactgroups": ["team"],
        "notification_rules": [
            {"rule_id": "rule_1", "notify_plugin": ("pushover", {"proxy_url": ("url", url)})},
            {"rule_id": "rule_2", "notify_plugin": ("mail", None)},
        ],
    }


def test_personal_rules_get_unshared_entries_of_their_own() -> None:
    users: dict[UserId, dict[str, object]] = {
        UserId("harry"): _user_with_proxy_rule(_URL_WITH_CREDENTIALS),
        UserId("sally"): {"notification_rules": []},
    }
    parameters = _parameters(_explicit(_URL_WITH_CREDENTIALS))
    migration = ProxyCredentialsMigration(set(), getLogger())

    migrate_notification_parameters(parameters, _METHODS, migration)
    assert migrate_user_notification_rules(users, _METHODS, migration) == [UserId("harry")]

    entry = migration.new_passwords["notification_proxy_harry_user_at_proxy_lan_3128_1"]
    assert (entry["owned_by"], entry["shared_with"]) == (None, [])
    assert "notification_proxy_user_at_proxy_lan_3128_1" in migration.new_passwords


def test_password_ids_are_ascii() -> None:
    users: dict[UserId, dict[str, object]] = {
        UserId("jörg"): _user_with_proxy_rule(_URL_WITH_CREDENTIALS)
    }
    migration = ProxyCredentialsMigration(set(), getLogger())

    migrate_user_notification_rules(users, _METHODS, migration)

    assert list(migration.new_passwords) == ["notification_proxy_j_rg_user_at_proxy_lan_3128_1"]


def _ruleset_holding(tree: FolderTree, proxy_url: object) -> Ruleset:
    ruleset_name = RuleGroup.NotificationParameters("slack")
    ruleset = Ruleset(ruleset_name, rulespec=rulespec_registry[ruleset_name])
    folder = tree.root_folder()
    ruleset.append_rule(
        folder,
        Rule.from_ruleset(
            folder,
            ruleset,
            {
                "webhook_url": ("webhook_url", "https://hooks.slack.com/services/x"),
                "proxy_url": proxy_url,
            },
        ),
    )
    return ruleset


def test_notification_parameter_rules_keep_the_stored_password_in_the_rulesets_action(
    request_context: None,  # noqa: ARG001  # Unused fixtures are needed for setup side effects
    tree: FolderTree,
) -> None:
    ruleset = _ruleset_holding(tree, _explicit(_URL_WITH_CREDENTIALS))
    all_rulesets = RulesetCollection({ruleset.name: ruleset})

    assert migrate_notification_parameter_rules(
        all_rulesets, _METHODS, ProxyCredentialsMigration(set(), getLogger())
    )
    transform_wato_rulesets_params(getLogger(), all_rulesets, raise_errors=True)

    assert ruleset.get_rules()[0][2].value["proxy_url"][2]["auth"]["password"] == (
        "cmk_postprocessed",
        "stored_password",
        ("notification_proxy_user_at_proxy_lan_3128_1", ""),
    )


def test_unconvertible_rules_keep_the_stored_password_in_the_rulesets_action(
    request_context: None,  # noqa: ARG001  # Unused fixtures are needed for setup side effects
    tree: FolderTree,
) -> None:
    ruleset = _ruleset_holding(tree, _explicit("http://user:s3crit@proxy.lan:port"))
    all_rulesets = RulesetCollection({ruleset.name: ruleset})

    migrate_notification_parameter_rules(
        all_rulesets, _METHODS, ProxyCredentialsMigration(set(), getLogger())
    )
    transform_wato_rulesets_params(getLogger(), all_rulesets, raise_errors=True)

    assert ruleset.get_rules()[0][2].value["proxy_url"][2]["auth"]["password"][1] == (
        "stored_password"
    )


@pytest.mark.usefixtures("request_context")
def test_proxy_methods_are_the_plugins_with_the_structured_proxy() -> None:
    methods = proxy_methods(getLogger())

    assert "slack" in methods
    assert "mail" not in methods


def _write_merged_passwords() -> None:
    """What the core config update ("cmk -U") does at the end of the update"""
    password_store.save(
        password_store.load(password_store.password_store_path()),
        password_store.pending_secrets_path_site(),
    )


@pytest.mark.usefixtures("request_context")
def test_the_update_moves_the_credentials_of_saved_notification_parameters() -> None:
    url = _URL_WITH_CREDENTIALS
    NotificationParameterConfigFile().save(
        _parameters(_explicit(url)),  # type: ignore[arg-type]
        pprint_value=False,
    )

    assert migrate_proxy_credentials(getLogger(), active_config, {}) == []
    _write_merged_passwords()

    saved: object = NotificationParameterConfigFile().load_for_reading()
    match saved:
        case {"slack": {"param_1": {"parameter_properties": {"proxy_url": saved_proxy}}}}:
            pass
        case _:
            pytest.fail(f"Unexpected notification parameters: {saved!r}")
    assert "notification_proxy_user_at_proxy_lan_3128_1" in PasswordStore().load_for_reading()
    assert http_proxy_config_from_user_setting(saved_proxy, {}).serialize() == url


def test_the_update_action_saves_the_migrated_personal_rules(
    with_user: tuple[UserId, str],
) -> None:
    user_id, _password_of_user = with_user
    users = load_users_uncached(lock=True)
    users[user_id]["notification_rules"] = [
        {  # type: ignore[typeddict-item]  # personal rules keep their parameters inline
            "rule_id": "rule_1",
            "notify_plugin": ("slack", {"proxy_url": ("url", _URL_WITH_CREDENTIALS)}),
        }
    ]
    userdb.save_users(
        users,
        userdb.get_user_attributes(active_config.wato_user_attrs),
        active_config.user_connections,
        now=datetime.now(),
        pprint_value=False,
        call_users_saved_hook=False,
    )

    update_action_registry["migrate_notification_proxy_credentials"](getLogger())

    match load_users_uncached()[user_id].get("notification_rules"):
        case [{"notify_plugin": ("slack", {"proxy_url": (_, "explicit_proxy", {"auth": auth})})}]:
            assert auth["password"] == (
                "cmk_postprocessed",
                "stored_password",
                (f"notification_proxy_{user_id}_user_at_proxy_lan_3128_1", ""),
            )
        case other:
            pytest.fail(f"Unexpected notification rules: {other!r}")
