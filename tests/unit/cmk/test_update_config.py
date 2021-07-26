#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# pylint: disable=redefined-outer-name
import argparse
import sys
import io
from pathlib import Path
import pytest

from tests.testlib.base import Scenario

import cmk.utils.log
import cmk.update_config as update_config
import cmk.gui.config
import cmk.utils.paths
from cmk.gui.utils.script_helpers import application_and_request_context
from cmk.gui.watolib.hosts_and_folders import Folder
from cmk.gui.watolib.rulesets import Rule, Ruleset, RulesetCollection
from cmk.gui.watolib.changes import AuditLogStore, ObjectRef, ObjectRefType


@pytest.fixture()
def request_context():
    with application_and_request_context():
        yield


@pytest.fixture()
def uc():
    return update_config.UpdateConfig(cmk.utils.log.logger, argparse.Namespace())


def test_parse_arguments_defaults():
    assert update_config.parse_arguments([]).__dict__ == {
        "debug": False,
        "verbose": 0,
    }


def test_parse_arguments_verbose():
    assert update_config.parse_arguments(["-v"]).verbose == 1
    assert update_config.parse_arguments(["-v"] * 2).verbose == 2
    assert update_config.parse_arguments(["-v"] * 3).verbose == 3


def test_parse_arguments_debug():
    assert update_config.parse_arguments(["--debug"]).debug is True


def test_update_config_init():
    update_config.UpdateConfig(cmk.utils.log.logger, argparse.Namespace())


def mock_run():
    sys.stdout.write("XYZ\n")
    return 0


def test_main(monkeypatch):
    buf = io.StringIO()
    monkeypatch.setattr(sys, "stdout", buf)
    monkeypatch.setattr(update_config.UpdateConfig, "run", lambda self: mock_run())
    assert update_config.main([]) == 0
    assert "XYZ" in buf.getvalue()


def test_cleanup_version_specific_caches_missing_directory(uc):
    uc._cleanup_version_specific_caches()


def test_cleanup_version_specific_caches(uc):
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
@pytest.mark.usefixtures("request_context")
def test__transform_wato_rulesets_params(
    ruleset_name,
    param_value,
    transformed_param_value,
):
    ruleset = _instantiate_ruleset(ruleset_name, param_value)
    rulesets = RulesetCollection()
    rulesets.set_rulesets({ruleset_name: ruleset})

    uc = update_config.UpdateConfig(cmk.utils.log.logger, argparse.Namespace())

    uc._transform_wato_rulesets_params(rulesets)

    assert len(ruleset.get_rules()[0]) == 3
    assert ruleset.get_rules()[0][2].value == transformed_param_value


@pytest.mark.parametrize('ruleset_name, param_value, new_ruleset_name, transformed_param_value', [
    ('non_inline_snmp_hosts', True, 'snmp_backend_hosts', 'classic'),
    ('non_inline_snmp_hosts', False, 'snmp_backend_hosts', 'inline'),
])
@pytest.mark.usefixtures("request_context")
def test__transform_replaced_wato_rulesets_and_params(
    ruleset_name,
    param_value,
    new_ruleset_name,
    transformed_param_value,
):
    all_rulesets = RulesetCollection()
    # checkmk: all_rulesets are loaded via
    # all_rulesets = cmk.gui.watolib.rulesets.AllRulesets()
    all_rulesets.set_rulesets({
        ruleset_name: _instantiate_ruleset(ruleset_name, param_value),
        new_ruleset_name: Ruleset(new_ruleset_name, {}),
    })

    uc = update_config.UpdateConfig(cmk.utils.log.logger, argparse.Namespace())

    uc._transform_replaced_wato_rulesets(all_rulesets)
    uc._transform_wato_rulesets_params(all_rulesets)

    assert not all_rulesets.exists(ruleset_name)

    rules = all_rulesets.get(new_ruleset_name).get_rules()
    assert len(rules) == 1

    rule = rules[0]
    assert len(rule) == 3
    assert rule[2].value == transformed_param_value


def _instantiate_ruleset(ruleset_name, param_value):
    ruleset = Ruleset(ruleset_name, {})
    rule = Rule(Folder(''), ruleset)
    rule.value = param_value
    ruleset.append_rule(Folder(''), rule)
    assert ruleset.get_rules()
    return ruleset


def _2_0_ignored_services():
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
    ]


def _non_discovery_ignored_services_ruleset():
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
@pytest.mark.usefixtures("request_context")
def test__transform_discovery_disabled_services(
    ruleset_spec,
    expected_ruleset,
):
    ruleset = Ruleset("ignored_services", {})
    ruleset.from_config(Folder(''), ruleset_spec)
    assert ruleset.get_rules()

    rulesets = RulesetCollection()
    rulesets.set_rulesets({"ignored_services": ruleset})

    uc = update_config.UpdateConfig(cmk.utils.log.logger, argparse.Namespace())
    uc._transform_discovery_disabled_services(rulesets)

    folder_rules = ruleset.get_folder_rules(Folder(''))
    assert [r.to_config() for r in folder_rules] == expected_ruleset


@pytest.fixture(name="old_path")
def fixture_old_path():
    return Path(cmk.utils.paths.var_dir, "wato", "log", "audit.log")


@pytest.fixture(name="new_path")
def fixture_new_path():
    return Path(cmk.utils.paths.var_dir, "wato", "log", "wato_audit.log")


@pytest.fixture(name="old_audit_log")
def fixture_old_audit_log(old_path):
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


def test__migrate_pre_2_0_audit_log(tmp_path, old_audit_log, new_path):
    uc = update_config.UpdateConfig(cmk.utils.log.logger, argparse.Namespace())

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


def test__migrate_pre_2_0_audit_log_not_existing(tmp_path, old_path, new_path):
    uc = update_config.UpdateConfig(cmk.utils.log.logger, argparse.Namespace())

    assert not new_path.exists()
    assert not old_path.exists()
    uc._migrate_pre_2_0_audit_log()
    assert not new_path.exists()
    assert not old_path.exists()


def test__migrate_pre_2_0_audit_log_not_migrate_already_migrated(tmp_path, old_audit_log, new_path):
    uc = update_config.UpdateConfig(cmk.utils.log.logger, argparse.Namespace())

    assert not new_path.exists()
    assert old_audit_log.exists()

    new_path.parent.mkdir(exist_ok=True, parents=True)
    with new_path.open("w") as f:
        f.write("abc\n")
    assert new_path.exists()

    uc._migrate_pre_2_0_audit_log()

    assert new_path.open().read() == "abc\n"
    assert old_audit_log.exists()


def test__rename_discovered_host_label_files_fix_wrong_name(monkeypatch):
    Scenario().add_host("abc.d").apply(monkeypatch)

    uc = update_config.UpdateConfig(cmk.utils.log.logger, argparse.Namespace())

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


def test__rename_discovered_host_label_files_do_not_overwrite(monkeypatch):
    Scenario().add_host("abc.d").apply(monkeypatch)

    uc = update_config.UpdateConfig(cmk.utils.log.logger, argparse.Namespace())

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


@pytest.mark.parametrize("contact_groups, expected_contact_groups", [
    ({}, {}),
    ({
        "group_name": {
            "alias": "Everything",
            "a": "setting"
        }
    }, {
        "group_name": {
            "alias": "Everything",
            "a": "setting"
        }
    }),
    ({
        "group_name_0": {
            "alias": "Everything 0",
            "inventory_paths": "allow_all"
        },
        "group_name_1": {
            "alias": "Everything 1",
            "inventory_paths": "forbid_all"
        },
        "group_name_2": {
            "alias": "Everything 2",
            "inventory_paths": ("paths", [
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
            ])
        }
    }, {
        "group_name_0": {
            "alias": "Everything 0",
            "inventory_paths": "allow_all"
        },
        "group_name_1": {
            "alias": "Everything 1",
            "inventory_paths": "forbid_all"
        },
        "group_name_2": {
            "alias": "Everything 2",
            "inventory_paths": ("paths", [
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
            ])
        }
    }),
])
def test__transform_contact_groups(monkeypatch, contact_groups, expected_contact_groups):
    uc = update_config.UpdateConfig(cmk.utils.log.logger, argparse.Namespace())
    uc._transform_contact_groups(contact_groups)
    assert contact_groups == expected_contact_groups
