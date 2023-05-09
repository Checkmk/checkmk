#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# pylint: disable=redefined-outer-name
import argparse
import io
import sys
from pathlib import Path
from typing import Sequence, Tuple

import pytest  # type: ignore[import]
from _pytest.monkeypatch import MonkeyPatch

from testlib.base import Scenario

import cmk.utils.log
import cmk.utils.paths
from cmk.utils.type_defs import RulesetName, RuleSpec, RuleValue

import cmk.gui.config
import cmk.update_config as update_config
from cmk.gui.watolib.changes import AuditLogStore, ObjectRef, ObjectRefType
from cmk.gui.watolib.hosts_and_folders import Folder
from cmk.gui.watolib.rulesets import Rule, Ruleset, RulesetCollection


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


def test_main(monkeypatch: MonkeyPatch) -> None:
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
            f.write(u"\n")
        uc._cleanup_version_specific_caches()
        assert not cached_file.exists()
        assert base_dir.exists()


@pytest.mark.parametrize('ruleset_name, param_value, transformed_param_value', [
    (
        'diskstat_inventory',
        ['summary', 'lvm'],
        {
            'summary': True,
            'lvm': True
        },
    ),
])
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


@pytest.mark.parametrize('ruleset_name, param_value, new_ruleset_name, transformed_param_value', [
    ('non_inline_snmp_hosts', True, 'snmp_backend_hosts', 'classic'),
    ('non_inline_snmp_hosts', False, 'snmp_backend_hosts', 'inline'),
])
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
    all_rulesets.set_rulesets({
        ruleset_name: _instantiate_ruleset(ruleset_name, param_value),
        new_ruleset_name: Ruleset(new_ruleset_name, {}),
    })

    uc._transform_replaced_wato_rulesets(all_rulesets)
    uc._transform_wato_rulesets_params(all_rulesets)

    assert not all_rulesets.exists(ruleset_name)

    rules = all_rulesets.get(new_ruleset_name).get_rules()
    assert len(rules) == 1

    rule = rules[0]
    assert len(rule) == 3
    assert rule[2].value == transformed_param_value


def test__transform_enforced_services(uc: update_config.UpdateConfig,) -> None:
    ruleset_spec = [
        {
            "condition": {},
            "value": ("nvidia.temp", "", {})
        },
    ]
    ruleset = Ruleset("static_checks:temperature", {})
    ruleset.from_config(Folder(""), ruleset_spec)
    rulesets = RulesetCollection()
    rulesets.set_rulesets({"static_checks:temperature": ruleset})

    uc._transform_wato_rulesets_params(rulesets)

    _folder, _idx, nvidia_rule = rulesets.get("static_checks:temperature").get_rules()[0]
    assert nvidia_rule.value == ("nvidia_temp", "", {})


def _instantiate_ruleset(ruleset_name, param_value) -> Ruleset:
    ruleset = Ruleset(ruleset_name, {})
    rule = Rule(Folder(''), ruleset)
    rule.value = param_value
    ruleset.append_rule(Folder(''), rule)
    assert ruleset.get_rules()
    return ruleset


def _2_0_ignored_services() -> Sequence[RuleSpec]:
    return [
        {
            'id': '1',
            'value': True,
            'condition': {
                'host_name': ['heute'],
                'service_description': [{
                    '$regex': 'Filesystem /opt/omd/sites/heute/tmp$'
                },]
            }
        },
        {
            'id': '1',
            'value': True,
            'condition': {
                'host_name': ['heute'],
                'service_description': {
                    '$nor': [{
                        '$regex': 'Filesystem /opt/omd/sites/heute/tmp$'
                    }]
                }
            }
        },
    ]


def _non_discovery_ignored_services_ruleset() -> Sequence[RuleSpec]:
    return [
        # Skip rule with multiple hostnames
        {
            'id': '1',
            'value': True,
            'condition': {
                'service_description': [{
                    '$regex': 'abc\\ xyz$'
                }, {
                    '$regex': 'dd\\ ggg$'
                }],
                'host_name': ['stable', 'xyz']
            }
        },
        # Skip rule service condition without $ at end
        {
            'id': '1',
            'value': True,
            'condition': {
                'service_description': [{
                    '$regex': 'abc\\ xyz'
                }, {
                    '$regex': 'dd\\ ggg$'
                }]
            }
        },
    ]


@pytest.mark.parametrize(
    'ruleset_spec,expected_ruleset',
    [
        # Transform pre 2.0 to 2.0 service_description regex
        ([
            {
                'id': '1',
                'condition': {
                    'service_description': [
                        {
                            '$regex': u'Filesystem\\ \\/boot\\/efi$'
                        },
                        {
                            '$regex': u'\\(a\\)\\ b\\?\\ c\\!$'
                        },
                    ],
                    'host_name': ['stable']
                },
                'value': True
            },
        ], [
            {
                'id': '1',
                'condition': {
                    'service_description': [
                        {
                            '$regex': u'Filesystem /boot/efi$'
                        },
                        {
                            '$regex': u'\\(a\\) b\\? c!$'
                        },
                    ],
                    'host_name': ['stable']
                },
                'value': True
            },
        ]),
        # Do not touch rules saved with 2.0
        (
            _2_0_ignored_services(),
            _2_0_ignored_services(),
        ),
        # Do not touch rules that have not been created by discovery page
        (
            _non_discovery_ignored_services_ruleset(),
            _non_discovery_ignored_services_ruleset(),
        ),
    ])
def test__transform_discovery_disabled_services(
    uc: update_config.UpdateConfig,
    ruleset_spec: Sequence[RuleSpec],
    expected_ruleset: Sequence[RuleSpec],
) -> None:
    ruleset = Ruleset("ignored_services", {})
    ruleset.from_config(Folder(''), ruleset_spec)
    assert ruleset.get_rules()

    rulesets = RulesetCollection()
    rulesets.set_rulesets({"ignored_services": ruleset})

    uc._transform_discovery_disabled_services(rulesets)

    folder_rules = ruleset.get_folder_rules(Folder(''))
    assert [r.to_config() for r in folder_rules] == expected_ruleset


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
        f.write("""
1604991356 - cmkadmin liveproxyd-activate Activating changes of Livestatus Proxy configuration
1604991356 - cmkadmin liveproxyd-activate Activating changes of Livestatus Proxy configuration
1604992040 :heute2 cmkadmin create-host Created new host heute2.
1604992159 :heute2 cmkadmin delete-host Deleted host heute2
1604992163 :heute1 cmkadmin create-host Created new host heute1.
1604992166 :heute12 cmkadmin create-host Created new host heute12.
""")
    return old_path


def test__migrate_pre_2_0_audit_log(
    uc: update_config.UpdateConfig,
    old_audit_log: Path,
    new_path: Path,
) -> None:
    assert not new_path.exists()
    assert old_audit_log.exists()

    uc._migrate_pre_2_0_audit_log()

    assert new_path.exists()
    assert not old_audit_log.exists()

    # Now try to parse the migrated log with the new logic
    store = AuditLogStore(new_path)
    assert store.read() == [
        AuditLogStore.Entry(time=1604991356,
                            object_ref=None,
                            user_id='cmkadmin',
                            action='liveproxyd-activate',
                            text='Activating changes of Livestatus Proxy configuration',
                            diff_text=None),
        AuditLogStore.Entry(time=1604991356,
                            object_ref=None,
                            user_id='cmkadmin',
                            action='liveproxyd-activate',
                            text='Activating changes of Livestatus Proxy configuration',
                            diff_text=None),
        AuditLogStore.Entry(time=1604992040,
                            object_ref=ObjectRef(ObjectRefType.Host, "heute2"),
                            user_id='cmkadmin',
                            action='create-host',
                            text='Created new host heute2.',
                            diff_text=None),
        AuditLogStore.Entry(time=1604992159,
                            object_ref=ObjectRef(ObjectRefType.Host, "heute2"),
                            user_id='cmkadmin',
                            action='delete-host',
                            text='Deleted host heute2',
                            diff_text=None),
        AuditLogStore.Entry(time=1604992163,
                            object_ref=ObjectRef(ObjectRefType.Host, "heute1"),
                            user_id='cmkadmin',
                            action='create-host',
                            text='Created new host heute1.',
                            diff_text=None),
        AuditLogStore.Entry(time=1604992166,
                            object_ref=ObjectRef(ObjectRefType.Host, "heute12"),
                            user_id='cmkadmin',
                            action='create-host',
                            text='Created new host heute12.',
                            diff_text=None),
    ]


def test__migrate_pre_2_0_audit_log_not_existing(
    uc: update_config.UpdateConfig,
    old_path: Path,
    new_path: Path,
) -> None:
    assert not new_path.exists()
    assert not old_path.exists()
    uc._migrate_pre_2_0_audit_log()
    assert not new_path.exists()
    assert not old_path.exists()


def test__migrate_pre_2_0_audit_log_not_migrate_already_migrated(
    uc: update_config.UpdateConfig,
    old_audit_log: Path,
    new_path: Path,
) -> None:
    assert not new_path.exists()
    assert old_audit_log.exists()

    new_path.parent.mkdir(exist_ok=True, parents=True)
    with new_path.open("w") as f:
        f.write("abc\n")
    assert new_path.exists()

    uc._migrate_pre_2_0_audit_log()

    assert new_path.open().read() == "abc\n"
    assert old_audit_log.exists()


def test__rename_discovered_host_label_files_fix_wrong_name(
    monkeypatch: MonkeyPatch,
    uc: update_config.UpdateConfig,
) -> None:
    Scenario().add_host("abc.d").apply(monkeypatch)

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
    monkeypatch: MonkeyPatch,
    uc: update_config.UpdateConfig,
) -> None:
    Scenario().add_host("abc.d").apply(monkeypatch)

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


def _edit_rule(key: str) -> Tuple[str, str]:
    # note that values ending with [1 are missing a closing "
    return (
        'Value of "%s changed from "mysecret" to "verysecret".' % key,
        'Value of "%s changed from "hash:652c7dc687" to "hash:36dd292533".' % key,
    )


def mock_audit_log_entry(action: str, diff_text: str) -> AuditLogStore.Entry:
    return AuditLogStore.Entry(time=0,
                               object_ref=None,
                               user_id="",
                               action=action,
                               text="",
                               diff_text=diff_text)


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
