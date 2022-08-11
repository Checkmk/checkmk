#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# pylint: disable=redefined-outer-name
import argparse
import io
import sys
from pathlib import Path
from typing import Any, Mapping, MutableMapping, Tuple

import pytest
from pytest_mock import MockerFixture

from tests.testlib.base import Scenario

# This GUI specific fixture is also needed in this context
from tests.unit.cmk.gui.conftest import load_plugins  # noqa: F401 # pylint: disable=unused-import

import cmk.utils.log
import cmk.utils.paths
from cmk.utils import version
from cmk.utils.type_defs import CheckPluginName, ContactgroupName, RulesetName, RuleValue
from cmk.utils.version import is_raw_edition

import cmk.gui.config
import cmk.gui.watolib.timeperiods as timeperiods
from cmk.gui.watolib.audit_log import AuditLogStore
from cmk.gui.watolib.hosts_and_folders import Folder
from cmk.gui.watolib.rulesets import Rule, Ruleset, RulesetCollection

import cmk.update_config as update_config


@pytest.fixture(name="uc")
def fixture_uc() -> update_config.UpdateConfig:
    return update_config.UpdateConfig(cmk.utils.log.logger, argparse.Namespace())


def test_parse_arguments_defaults() -> None:
    assert update_config.parse_arguments([]).__dict__ == {
        "debug": False,
        "verbose": 0,
    }


def test_parse_arguments_verbose() -> None:
    assert update_config.parse_arguments(["-v"]).verbose == 1
    assert update_config.parse_arguments(["-v"] * 2).verbose == 2
    assert update_config.parse_arguments(["-v"] * 3).verbose == 3


def test_parse_arguments_debug() -> None:
    assert update_config.parse_arguments(["--debug"]).debug is True


def test_update_config_init() -> None:
    update_config.UpdateConfig(cmk.utils.log.logger, argparse.Namespace())


def mock_run() -> int:
    sys.stdout.write("XYZ\n")
    return 0


def test_main(monkeypatch: pytest.MonkeyPatch) -> None:
    buf = io.StringIO()
    monkeypatch.setattr(sys, "stdout", buf)
    monkeypatch.setattr(update_config.UpdateConfig, "run", lambda self: mock_run())
    assert update_config.main([]) == 0
    assert "XYZ" in buf.getvalue()


def test_cleanup_version_specific_caches_missing_directory(uc: update_config.UpdateConfig) -> None:
    uc._cleanup_version_specific_caches()


def test_cleanup_version_specific_caches(uc: update_config.UpdateConfig) -> None:
    paths = [
        Path(cmk.utils.paths.include_cache_dir, "builtin"),
        Path(cmk.utils.paths.include_cache_dir, "local"),
        Path(cmk.utils.paths.precompiled_checks_dir, "builtin"),
        Path(cmk.utils.paths.precompiled_checks_dir, "local"),
    ]
    for base_dir in paths:
        base_dir.mkdir(parents=True, exist_ok=True)
        cached_file = base_dir / "if"
        with cached_file.open("w", encoding="utf-8") as f:
            f.write("\n")
        uc._cleanup_version_specific_caches()
        assert not cached_file.exists()
        assert base_dir.exists()


@pytest.mark.parametrize(
    "ruleset_name, param_value, transformed_param_value",
    [
        (
            "diskstat_inventory",
            ["summary", "lvm"],
            {"summary": True, "lvm": True},
        ),
    ],
)
@pytest.mark.usefixtures("request_context")
def test__transform_wato_rulesets_params(
    uc: update_config.UpdateConfig,
    ruleset_name: RulesetName,
    param_value: RuleValue,
    transformed_param_value: RuleValue,
) -> None:
    ruleset = _instantiate_ruleset(ruleset_name, param_value)
    rulesets = RulesetCollection()
    rulesets.set_rulesets({ruleset_name: ruleset})

    uc._transform_wato_rulesets_params(rulesets)

    assert len(ruleset.get_rules()[0]) == 3
    assert ruleset.get_rules()[0][2].value == transformed_param_value


@pytest.mark.parametrize(
    "ruleset_name, param_value, new_ruleset_name, transformed_param_value",
    [
        ("non_inline_snmp_hosts", True, "snmp_backend_hosts", "classic"),
        ("non_inline_snmp_hosts", False, "snmp_backend_hosts", "inline"),
    ],
)
@pytest.mark.usefixtures("request_context")
def test__transform_replaced_wato_rulesets_and_params(
    uc: update_config.UpdateConfig,
    ruleset_name: RulesetName,
    param_value: RuleValue,
    new_ruleset_name: RulesetName,
    transformed_param_value: RuleValue,
) -> None:
    all_rulesets = RulesetCollection()
    # checkmk: all_rulesets are loaded via
    # all_rulesets = cmk.gui.watolib.rulesets.AllRulesets()
    all_rulesets.set_rulesets(
        {
            ruleset_name: _instantiate_ruleset(ruleset_name, param_value),
            new_ruleset_name: Ruleset(new_ruleset_name, {}),
        }
    )

    uc._transform_replaced_wato_rulesets(
        all_rulesets,
        {ruleset_name: new_ruleset_name},
    )
    uc._transform_wato_rulesets_params(all_rulesets)

    assert not all_rulesets.exists(ruleset_name)

    rules = all_rulesets.get(new_ruleset_name).get_rules()
    assert len(rules) == 1

    rule = rules[0]
    assert len(rule) == 3
    assert rule[2].value == transformed_param_value


def _instantiate_ruleset(ruleset_name, param_value) -> Ruleset:  # type:ignore[no-untyped-def]
    ruleset = Ruleset(ruleset_name, {})
    rule = Rule.from_ruleset_defaults(Folder(""), ruleset)
    rule.value = param_value
    ruleset.append_rule(Folder(""), rule)
    assert ruleset.get_rules()
    return ruleset


@pytest.mark.usefixtures("request_context")
def test_remove_removed_check_plugins_from_ignored_checks(uc: update_config.UpdateConfig) -> None:
    ruleset = Ruleset("ignored_checks", {})
    ruleset.from_config(
        Folder(""),
        [
            {
                "id": "1",
                "condition": {},
                "options": {"disabled": False},
                "value": ["a", "b", "mgmt_c"],
            },
            {
                "id": "2",
                "condition": {},
                "options": {"disabled": False},
                "value": ["d", "e"],
            },
            {
                "id": "3",
                "condition": {},
                "options": {"disabled": False},
                "value": ["mgmt_f"],
            },
            {
                "id": "4",
                "condition": {},
                "options": {"disabled": False},
                "value": ["a", "g"],
            },
        ],
    )
    rulesets = RulesetCollection()
    rulesets.set_rulesets({"ignored_checks": ruleset})
    uc._remove_removed_check_plugins_from_ignored_checks(
        rulesets,
        {
            CheckPluginName("b"),
            CheckPluginName("d"),
            CheckPluginName("e"),
            CheckPluginName("f"),
        },
    )
    leftover_rules = [rule for (_folder, idx, rule) in rulesets.get("ignored_checks").get_rules()]
    assert len(leftover_rules) == 2
    assert leftover_rules[0].id == "1"
    assert leftover_rules[1].id == "4"
    assert leftover_rules[0].value == ["a", "mgmt_c"]
    assert leftover_rules[1].value == ["a", "g"]


@pytest.mark.parametrize(
    ["rulesets", "n_expected_warnings"],
    [
        pytest.param(
            {
                "logwatch_rules": {
                    "reclassify_patterns": [
                        ("C", "\\\\x\\\\y\\\\z", "some comment"),
                        ("W", "\\H", "invalid_regex"),
                    ]
                },
                "checkgroup_parameters:ntp_time": {
                    "ntp_levels": (10, 200.0, 500.0),
                },
            },
            2,
            id="invalid configuration",
        ),
        pytest.param(
            {
                "logwatch_rules": {
                    "reclassify_patterns": [
                        ("C", "\\\\x\\\\y\\\\z", "some comment"),
                    ]
                },
                "checkgroup_parameters:ntp_time": {
                    "ntp_levels": (10, 200.0, 500.0),
                },
                **({} if is_raw_edition() else {"extra_service_conf:_sla_config": "i am skipped"}),
            },
            0,
            id="valid configuration",
        ),
    ],
)
@pytest.mark.usefixtures("request_context")
def test_validate_rule_values(
    mocker: MockerFixture,
    uc: update_config.UpdateConfig,
    rulesets: Mapping[RulesetName, RuleValue],
    n_expected_warnings: int,
) -> None:
    all_rulesets = RulesetCollection()
    all_rulesets.set_rulesets(
        {
            ruleset_name: _instantiate_ruleset(
                ruleset_name,
                rule_value,
            )
            for ruleset_name, rule_value in rulesets.items()
        }
    )
    mock_warner = mocker.patch.object(
        uc._logger,
        "warning",
    )
    uc._validate_rule_values(all_rulesets)
    assert mock_warner.call_count == n_expected_warnings


@pytest.fixture(name="old_path")
def fixture_old_path() -> Path:
    return Path(cmk.utils.paths.var_dir, "wato", "log", "audit.log")


@pytest.fixture(name="new_path")
def fixture_new_path() -> Path:
    return Path(cmk.utils.paths.var_dir, "wato", "log", "wato_audit.log")


@pytest.fixture(name="old_audit_log")
def fixture_old_audit_log(old_path: Path) -> Path:
    old_path.parent.mkdir(exist_ok=True, parents=True)
    with old_path.open("w") as f:
        f.write(
            """
1604991356 - cmkadmin liveproxyd-activate Activating changes of Livestatus Proxy configuration
1604991356 - cmkadmin liveproxyd-activate Activating changes of Livestatus Proxy configuration
1604992040 :heute2 cmkadmin create-host Created new host heute2.
1604992159 :heute2 cmkadmin delete-host Deleted host heute2
1604992163 :heute1 cmkadmin create-host Created new host heute1.
1604992166 :heute12 cmkadmin create-host Created new host heute12.
"""
        )
    return old_path


def test__rename_discovered_host_label_files_fix_wrong_name(
    monkeypatch: pytest.MonkeyPatch,
    uc: update_config.UpdateConfig,
) -> None:
    ts = Scenario()
    ts.add_host("abc.d")
    ts.apply(monkeypatch)

    host_name = "abc.d"
    old_path = (cmk.utils.paths.discovered_host_labels_dir / host_name).with_suffix(".mk")
    new_path = cmk.utils.paths.discovered_host_labels_dir / (host_name + ".mk")

    old_path.parent.mkdir(exist_ok=True, parents=True)
    with old_path.open("w") as f:
        f.write("{}\n")
    assert old_path.exists()
    assert not new_path.exists()

    uc._rename_discovered_host_label_files()

    assert not old_path.exists()
    assert new_path.exists()


def test__rename_discovered_host_label_files_do_not_overwrite(
    monkeypatch: pytest.MonkeyPatch,
    uc: update_config.UpdateConfig,
) -> None:
    ts = Scenario()
    ts.add_host("abc.d")
    ts.apply(monkeypatch)

    host_name = "abc.d"
    old_path = (cmk.utils.paths.discovered_host_labels_dir / host_name).with_suffix(".mk")
    new_path = cmk.utils.paths.discovered_host_labels_dir / (host_name + ".mk")

    old_path.parent.mkdir(exist_ok=True, parents=True)
    with old_path.open("w") as f:
        f.write("{}\n")
    assert old_path.exists()

    with new_path.open("w") as f:
        f.write("{}\n")
    assert new_path.exists()

    uc._rename_discovered_host_label_files()

    assert old_path.exists()
    assert new_path.exists()


@pytest.mark.parametrize(
    "contact_groups, expected_contact_groups",
    [
        ({}, {}),
        (
            {"group_name": {"alias": "Everything", "a": "setting"}},
            {"group_name": {"alias": "Everything", "a": "setting"}},
        ),
        (
            {
                "group_name_0": {"alias": "Everything 0", "inventory_paths": "allow_all"},
                "group_name_1": {"alias": "Everything 1", "inventory_paths": "forbid_all"},
                "group_name_2": {
                    "alias": "Everything 2",
                    "inventory_paths": (
                        "paths",
                        [
                            {
                                "path": "path.to.node_0",
                            },
                            {
                                "path": "path.to.node_1",
                                "attributes": [],
                            },
                            {
                                "path": "path.to.node_2",
                                "attributes": ["some", "keys"],
                            },
                        ],
                    ),
                },
            },
            {
                "group_name_0": {"alias": "Everything 0", "inventory_paths": "allow_all"},
                "group_name_1": {"alias": "Everything 1", "inventory_paths": "forbid_all"},
                "group_name_2": {
                    "alias": "Everything 2",
                    "inventory_paths": (
                        "paths",
                        [
                            {
                                "visible_raw_path": "path.to.node_0",
                            },
                            {
                                "visible_raw_path": "path.to.node_1",
                                "nodes": "nothing",
                            },
                            {
                                "visible_raw_path": "path.to.node_2",
                                "attributes": ("choices", ["some", "keys"]),
                                "columns": ("choices", ["some", "keys"]),
                                "nodes": "nothing",
                            },
                        ],
                    ),
                },
            },
        ),
    ],
)
def test__transform_contact_groups(
    uc: update_config.UpdateConfig,
    contact_groups: Mapping[ContactgroupName, MutableMapping[str, Any]],
    expected_contact_groups: Mapping[ContactgroupName, MutableMapping[str, Any]],
) -> None:
    uc._transform_contact_groups(contact_groups)
    assert contact_groups == expected_contact_groups


def _edit_rule(key: str) -> Tuple[str, str]:
    # note that values ending with [1 are missing a closing "
    return (
        'Value of "%s changed from "mysecret" to "verysecret".' % key,
        'Value of "%s changed from "hash:652c7dc687" to "hash:36dd292533".' % key,
    )


def mock_audit_log_entry(action: str, diff_text: str) -> AuditLogStore.Entry:
    return AuditLogStore.Entry(
        time=0, object_ref=None, user_id="", action=action, text="", diff_text=diff_text
    )


@pytest.mark.parametrize(
    "diff, expected",
    [
        _edit_rule("value/proxy/auth/[1][1"),
        _edit_rule("value/imap_parameters/auth/[1][1"),
        _edit_rule("value/fetch/[1]auth/[1][1"),
        _edit_rule("value/token/[1"),
        _edit_rule("value/login/[1"),
        _edit_rule("value/smtp_auth/[1][1"),
        _edit_rule('value/password"'),
        _edit_rule("value/password/[1"),
        _edit_rule("value/mode/[1]auth/[1][1"),
        _edit_rule("value/[0]credentials/[1][1"),
        _edit_rule("value/credentials/[1"),
        _edit_rule("value/credentials/[1][1"),
        _edit_rule("value/credentials/[1][1][1"),
        _edit_rule("value/auth_basic/password/[1"),
        _edit_rule('value/secret"'),
        _edit_rule("value/secret/[1"),
        _edit_rule("value/secret_access_key/[1"),
        _edit_rule("value/proxy_details/proxy_password/[1"),
        _edit_rule("value/credentials_sap_connect/[1][1"),
        _edit_rule("value/credentials/[0][3][1][1"),
        _edit_rule("value/credentials/[1][3][1][1"),
        _edit_rule('value/passphrase"'),
        _edit_rule("value/auth/[1"),
        _edit_rule("value/[1]auth/[1"),
        _edit_rule("value/[2]authentication/[1"),
        _edit_rule("value/proxy/proxy_protocol/[1]credentials/[1"),
        _edit_rule('value/[1]password"'),
        _edit_rule("value/basicauth/[1"),
        _edit_rule("value/basicauth/[1][1"),
        _edit_rule('value/api_token"'),
        _edit_rule('value/client_secret"'),
        _edit_rule('value/instances/[0]passwd"'),
        _edit_rule("value/login/auth/[1][1"),
        _edit_rule("value/login_asm/auth/[1][1"),
        _edit_rule("value/login_exceptions/[0][1]auth/[1][1"),
        (
            # If a double quote is present, it is not escaped in the diff text
            'Value of "value/token/[1 changed from "$oo" to "sec"ret".',
            'Value of "value/token/[1 changed from "hash:d3d9561ead" to "hash:34d1ada6a1".',
        ),
    ],
)
def test_password_sanitizer_edit_rule(diff: str, expected: str) -> None:
    sanitizer = update_config.PasswordSanitizer()
    entry = sanitizer.replace_password(mock_audit_log_entry("edit-rule", diff))
    assert entry.diff_text == expected


@pytest.mark.parametrize(
    "diff, expected",
    [
        (
            "Attribute \"value/credentials_sap_connect\" with value ('foo', ('password', 'secret')) added.",
            "Attribute \"value/credentials_sap_connect\" with value ('foo', ('password', 'hash:2bb80d537b')) added.",
        ),
        (
            "Attribute \"value\" with value ('test', 'test', {'authentication': ('foo', 'secret')}) added.",
            "Attribute \"value\" with value ('test', 'test', {'authentication': ('foo', 'hash:2bb80d537b')}) added.",
        ),
        (
            "Attribute \"value\" with value {'login': ('monitoring', 'secret', 'basic')} added.",
            "Attribute \"value\" with value {'login': ('monitoring', 'hash:2bb80d537b', 'basic')} added.",
        ),
        (
            "Attribute \"value\" with value {'login': (\"mon'itoring\", 'secret', 'basic')} added.",
            "Attribute \"value\" with value {'login': (\"mon'itoring\", 'hash:2bb80d537b', 'basic')} added.",
        ),
        (
            "Attribute \"value\" with value {'passphrase': 'secret', 'use_regular': 'disable', 'use_realtime': 'enforce'} added.",
            "Attribute \"value\" with value {'passphrase': 'hash:2bb80d537b', 'use_regular': 'disable', 'use_realtime': 'enforce'} added.",
        ),
        (
            "Attribute \"value\" with value {'passphrase': \"$ecr'et\", 'use_regular': 'disable', 'use_realtime': 'enforce'} added.",
            "Attribute \"value\" with value {'passphrase': 'hash:f65f232a52', 'use_regular': 'disable', 'use_realtime': 'enforce'} added.",
        ),
        (
            "Attribute \"value\" with value ('test', {'auth': ('foo', 'secret')}) added.",
            "Attribute \"value\" with value ('test', {'auth': ('foo', 'hash:2bb80d537b')}) added.",
        ),
        (
            "Attribute \"value\" with value {'share': 'test', 'levels': (85.0, 95.0), 'auth': ('foo', 'secret')} added.",
            "Attribute \"value\" with value {'share': 'test', 'levels': (85.0, 95.0), 'auth': ('foo', 'hash:2bb80d537b')} added.",
        ),
        (
            "Attribute \"value\" with value {'proxy': {'server': 'localhost', 'port': 80, 'proxy_protocol': ('http', {'credentials': ('foo', 'secret')})}} added.",
            "Attribute \"value\" with value {'proxy': {'server': 'localhost', 'port': 80, 'proxy_protocol': ('http', {'credentials': ('foo', 'hash:2bb80d537b')})}} added.",
        ),
        (
            "Attribute \"value\" with value {'username': 'foo', 'password': 'secret'} added.",
            "Attribute \"value\" with value {'username': 'foo', 'password': 'hash:2bb80d537b'} added.",
        ),
        (
            "Attribute \"value\" with value ('freeipmi', {'username': 'foo', 'password': 'secret\\'\"quotes', 'privilege_lvl': 'test', 'ipmi_driver': 'ha'}) added.",
            "Attribute \"value\" with value ('freeipmi', {'username': 'foo', 'password': 'hash:8f89822355', 'privilege_lvl': 'test', 'ipmi_driver': 'ha'}) added.",
        ),
        (
            "Attribute \"value\" with value {'servername': 'test', 'port': 8161, 'protocol': 'http', 'use_piggyback': False, 'basicauth': ('test', 'secret')} added.",
            "Attribute \"value\" with value {'servername': 'test', 'port': 8161, 'protocol': 'http', 'use_piggyback': False, 'basicauth': ('test', 'hash:2bb80d537b')} added.",
        ),
        (
            "Attribute \"value\" with value {'url': 'http://abc', 'vhm_id': '123', 'api_token': 'secret', 'client_id': 'clien', 'client_secret': 'secret', 'redirect_url': 'http://red'} added.",
            "Attribute \"value\" with value {'url': 'http://abc', 'vhm_id': '123', 'api_token': 'hash:2bb80d537b', 'client_id': 'clien', 'client_secret': 'hash:2bb80d537b', 'redirect_url': 'http://red'} added.",
        ),
        (
            "Attribute \"value\" with value {'subscription': 'id', 'tenant': 'tenant', 'client': 'client', 'secret': 'secret', 'config': {'explicit': [{'group_name': 'foo'}]}} added.",
            "Attribute \"value\" with value {'subscription': 'id', 'tenant': 'tenant', 'client': 'client', 'secret': 'hash:2bb80d537b', 'config': {'explicit': [{'group_name': 'foo'}]}} added.",
        ),
        (
            # In the ruleset "BI Aggregations" the string 'automation' refers to the automation user and should NOT be replaced!
            "Attribute \"value\" with value [{'site': 'local', 'credentials': 'automation'}] added.",
            "Attribute \"value\" with value [{'site': 'local', 'credentials': 'automation'}] added.",
        ),
        (
            "Attribute \"value\" with value [{'site': 'local', 'credentials': ('configured', ('test', 'secret'))}] added.",
            "Attribute \"value\" with value [{'site': 'local', 'credentials': ('configured', ('test', 'hash:2bb80d537b'))}] added.",
        ),
        (
            "Attribute \"value\" with value {'instances': [{'ashost': 'localhost', 'sysnr': '00', 'client': '100', 'user': 'cmk-user', 'passwd': 'secret', 'trace': '3', 'lang': 'EN'}], 'paths': ['SAP BI Monitors/BI Monitor', 'SAP BI Monitors/BI Monitor/*/Oracle/Performance']} added.",
            "Attribute \"value\" with value {'instances': [{'ashost': 'localhost', 'sysnr': '00', 'client': '100', 'user': 'cmk-user', 'passwd': 'hash:2bb80d537b', 'trace': '3', 'lang': 'EN'}], 'paths': ['SAP BI Monitors/BI Monitor', 'SAP BI Monitors/BI Monitor/*/Oracle/Performance']} added.",
        ),
        (
            "Attribute \"value\" with value {'login': {'auth': ('explicit', ('test', 'secret'))}, 'login_exceptions': [('foo', {'auth': ('explicit', ('test2', 'secret'))})], 'login_asm': {'auth': ('explicit', ('test3', 'secret'))}} added.",
            "Attribute \"value\" with value {'login': {'auth': ('explicit', ('test', 'hash:2bb80d537b'))}, 'login_exceptions': [('foo', {'auth': ('explicit', ('test2', 'hash:2bb80d537b'))})], 'login_asm': {'auth': ('explicit', ('test3', 'hash:2bb80d537b'))}} added.",
        ),
    ],
)
def test_password_sanitizer_new_rule(diff: str, expected: str) -> None:
    sanitizer = update_config.PasswordSanitizer()
    entry = sanitizer.replace_password(mock_audit_log_entry("new-rule", diff))
    assert entry.diff_text == expected


def test_password_sanitizer_multiline() -> None:
    diff_fst, expected_fst = _edit_rule("value/instance/api_key/[1")
    diff_snd, expected_snd = _edit_rule("value/instance/app_key/[1")
    diff = "\n".join([diff_fst, diff_snd])
    expected = "\n".join([expected_fst, expected_snd])

    sanitizer = update_config.PasswordSanitizer()
    entry = sanitizer.replace_password(mock_audit_log_entry("edit-rule", diff))
    assert entry.diff_text == expected


def test_update_global_config(
    mocker: MockerFixture,
    uc: update_config.UpdateConfig,
) -> None:
    mocker.patch.object(
        update_config,
        "REMOVED_GLOBALS_MAP",
        [
            ("global_a", "new_global_a", {True: 1, False: 0}),
            ("global_b", "new_global_b", {}),
            ("missing", "new_missing", {}),
        ],
    )
    mocker.patch.object(
        update_config,
        "filter_unknown_settings",
        lambda global_config: {k: v for k, v in global_config.items() if k != "unknown"},
    )
    mocker.patch.object(
        update_config.UpdateConfig,
        "_transform_global_config_value",
        lambda _self, config_var, config_val: {
            "new_global_a": config_val,
            "new_global_b": 15,
            "global_c": ["x", "y", "z"],
            "unchanged": config_val,
        }[config_var],
    )
    assert uc._update_global_config(
        {
            "global_a": True,
            "global_b": 14,
            "global_c": None,
            "unchanged": "please leave me alone",
            "unknown": "How did this get here?",
        }
    ) == {
        "global_c": ["x", "y", "z"],
        "unchanged": "please leave me alone",
        "new_global_a": 1,
        "new_global_b": 15,
    }


@pytest.mark.usefixtures("request_context")
def test_transform_influxdb_connnections(uc: update_config.UpdateConfig) -> None:
    if version.is_raw_edition():
        return

    from cmk.gui.cee.plugins.wato import influxdb  # pylint: disable=no-name-in-module

    influx_db_connection_config = influxdb.InfluxDBConnectionConfig()
    influx_db_connection_config.save(
        {
            "InfluxDB_Connection_1": {
                "title": "influxdb",
                "comment": "",
                "docu_url": "",
                "disabled": False,
                "site": ["-all-sites"],
                "instance": {
                    "protocol": ("https", {"port": 8086, "no-cert-check": True}),
                    "instance_host": "influx.somwhere.com",
                    "instance_token": "to_be_transformed",
                },
            }
        }
    )

    uc._transform_influxdb_connnections()
    assert influx_db_connection_config.load_for_reading()["InfluxDB_Connection_1"]["instance"][
        "instance_token"
    ] == (
        "password",
        "to_be_transformed",
    )


def test__transform_time_range(uc: update_config.UpdateConfig) -> None:
    time_range = ((8, 0), (16, 0))
    assert uc._transform_time_range(time_range) == ("08:00", "16:00")


def test__get_timeperiod_name(uc: update_config.UpdateConfig) -> None:
    time_range = [((8, 0), (16, 0)), ((17, 0), (20, 0))]
    assert uc._get_timeperiod_name(time_range) == "timeofday_0800-1600_1700-2000"


@pytest.mark.usefixtures("request_context")
def test__create_timeperiod(uc: update_config.UpdateConfig) -> None:
    time_range = [((8, 0), (16, 0)), ((17, 0), (20, 0))]
    uc._create_timeperiod("timeofday_0800-1600_1700-2000", time_range)

    timeperiod = timeperiods.load_timeperiods()["timeofday_0800-1600_1700-2000"]
    assert timeperiod == {
        "alias": "Created by migration of timeofday parameter (08:00-16:00, 17:00-20:00)",
        "monday": [("08:00", "16:00"), ("17:00", "20:00")],
        "tuesday": [("08:00", "16:00"), ("17:00", "20:00")],
        "wednesday": [("08:00", "16:00"), ("17:00", "20:00")],
        "thursday": [("08:00", "16:00"), ("17:00", "20:00")],
        "friday": [("08:00", "16:00"), ("17:00", "20:00")],
        "saturday": [("08:00", "16:00"), ("17:00", "20:00")],
        "sunday": [("08:00", "16:00"), ("17:00", "20:00")],
    }


@pytest.mark.parametrize(
    "old_param_value, transformed_param_value",
    [
        pytest.param(
            {"timeofday": [((8, 0), (16, 0)), ((17, 0), (20, 0))], "minage": (2, 1)},
            {
                "tp_default_value": {},
                "tp_values": [("timeofday_0800-1600_1700-2000", {"minage": (2, 1)})],
            },
            id="without_timeperiods",
        ),
        pytest.param(
            {
                "tp_default_value": {"timeofday": [((8, 0), (16, 0))], "minage": (2, 1)},
                "tp_values": [("24x7", {"maxage": (200, 1000)})],
            },
            {
                "tp_default_value": {},
                "tp_values": [("timeofday_0800-1600", {"minage": (2, 1)})],
            },
            id="timeofday_in_default_timeperiod",
        ),
        pytest.param(
            {
                "tp_default_value": {"minage": (2, 1)},
                "tp_values": [("24x7", {"timeofday": [((8, 0), (16, 0))], "minage": (2, 1)})],
            },
            {
                "tp_default_value": {"minage": (2, 1)},
                "tp_values": [("24x7", {"minage": (2, 1)})],
            },
            id="timeofday_in_nondefault_timeperiod",
        ),
    ],
)
@pytest.mark.usefixtures("request_context")
def test__transform_fileinfo_timeofday_to_timeperiods(  # type:ignore[no-untyped-def]
    uc: update_config.UpdateConfig, old_param_value: RuleValue, transformed_param_value: RuleValue
):
    rulesets = RulesetCollection()
    ruleset = _instantiate_ruleset("checkgroup_parameters:fileinfo", old_param_value)
    rulesets.set_rulesets({"checkgroup_parameters:fileinfo": ruleset})

    uc._transform_fileinfo_timeofday_to_timeperiods(rulesets)

    ruleset = rulesets.get_rulesets()["checkgroup_parameters:fileinfo"]
    assert ruleset.get_rules()[0][2].value == transformed_param_value
