#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
from collections.abc import Sequence

import pytest

from cmk.ccc.site import SiteId
from cmk.gui.valuespec import DropdownChoice
from cmk.gui.watolib.hosts_and_folders import folder_tree
from cmk.gui.watolib.rulesets import Rule, Ruleset, RulesetCollection
from cmk.gui.watolib.rulespec_groups import RulespecGroupMonitoringConfigurationVarious
from cmk.gui.watolib.rulespecs import HostRulespec
from cmk.livestatus_client import NetworkSocketDetails, SiteConfiguration, SiteConfigurations
from cmk.update_config.plugins.actions.migrate_snmp_backend_values import (
    migrate_global_setting,
    migrate_rules,
    migrate_site_globals,
    migrated_backend_value,
)

LOGGER = logging.getLogger("test")

_RULESET_NAME = "snmp_backend_hosts"


def _rulesets(rule_values: Sequence[object]) -> RulesetCollection:
    ruleset = Ruleset(
        _RULESET_NAME,
        rulespec=HostRulespec(
            name=_RULESET_NAME,
            group=RulespecGroupMonitoringConfigurationVarious,
            valuespec=lambda: DropdownChoice(
                choices=[("classic", "classic"), ("inline", "inline")]
            ),
        ),
    )
    folder = folder_tree().root_folder()
    for value in rule_values:
        rule = Rule.from_ruleset(folder, ruleset, ruleset.rulespec.valuespec.default_value())
        rule.value = value
        ruleset.append_rule(folder, rule)
    return RulesetCollection({_RULESET_NAME: ruleset})


@pytest.mark.parametrize(
    "value, expected",
    [
        (False, "inline"),
        ("inline_legacy", "inline"),
        (True, "classic"),
        ("pysnmp", "classic"),
        # nothing to do
        ("inline", None),
        ("classic", None),
        # not ours to guess
        ("some rubbish", None),
        (0, None),
        (1, None),
    ],
)
def test_migrated_backend_value(value: object, expected: str | None) -> None:
    assert migrated_backend_value(value) == expected


def test_migrate_global_setting() -> None:
    assert migrate_global_setting({"snmp_backend_default": "inline_legacy"}, "test", LOGGER) == {
        "snmp_backend_default": "inline"
    }


def test_migrate_global_setting_keeps_other_settings() -> None:
    assert migrate_global_setting(
        {"snmp_backend_default": False, "some_other_setting": 23}, "test", LOGGER
    ) == {"snmp_backend_default": "inline", "some_other_setting": 23}


@pytest.mark.parametrize(
    "settings",
    [
        {},
        {"snmp_backend_default": "inline"},
        {"snmp_backend_default": "some rubbish"},
    ],
)
def test_migrate_global_setting_nothing_to_do(settings: dict[str, object]) -> None:
    # returning the very same object is how the update action detects that it must not save
    assert migrate_global_setting(settings, "test", LOGGER) is settings


def _remote_site(site_globals: dict[str, object] | None) -> SiteConfiguration:
    """A replicating remote site, so that its site specific globals are editable"""
    site = SiteConfiguration(
        id=SiteId("remote"),
        alias="Remote",
        socket=(
            "tcp",
            NetworkSocketDetails(
                address=("127.0.0.1", 6557),
                tls=("encrypted", {"verify": True}),
            ),
        ),
        disable_wato=True,
        disabled=False,
        insecure=False,
        url_prefix="/remote/",
        multisiteurl="http://remote/check_mk/",
        persist=False,
        replicate_ec=False,
        replicate_mkps=False,
        replication="slave",
        timeout=5,
        user_login=True,
        proxy=None,
        user_attribute_sync_connections="all",
        status_host=None,
        message_broker_port=5672,
        is_trusted=False,
    )
    if site_globals is not None:
        site["globals"] = site_globals
    return site


def test_migrate_site_globals() -> None:
    sites = SiteConfigurations({SiteId("remote"): _remote_site({"snmp_backend_default": False})})

    assert migrate_site_globals(sites, LOGGER) is True

    assert sites[SiteId("remote")]["globals"] == {"snmp_backend_default": "inline"}


def test_migrate_site_globals_keeps_other_settings() -> None:
    sites = SiteConfigurations(
        {SiteId("remote"): _remote_site({"snmp_backend_default": "pysnmp", "some_other": 23})}
    )

    assert migrate_site_globals(sites, LOGGER) is True

    assert sites[SiteId("remote")]["globals"] == {
        "snmp_backend_default": "classic",
        "some_other": 23,
    }


@pytest.mark.parametrize(
    "site_globals",
    [
        None,
        {},
        {"snmp_backend_default": "inline"},
        {"snmp_backend_default": "some rubbish"},
    ],
)
def test_migrate_site_globals_nothing_to_do(site_globals: dict[str, object] | None) -> None:
    sites = SiteConfigurations({SiteId("remote"): _remote_site(site_globals)})

    assert migrate_site_globals(sites, LOGGER) is False

    # we must not create the key just to write nothing into it
    assert sites[SiteId("remote")].get("globals") == site_globals


@pytest.mark.usefixtures("request_context")
def test_migrate_rules() -> None:
    all_rulesets = _rulesets([False, "inline_legacy", True, "pysnmp", "inline", "some rubbish"])

    assert migrate_rules(all_rulesets, LOGGER) == 4

    assert [
        rule.value for _folder, _index, rule in all_rulesets.get(_RULESET_NAME).get_rules()
    ] == [
        "inline",
        "inline",
        "classic",
        "classic",
        "inline",
        "some rubbish",
    ]


@pytest.mark.usefixtures("request_context")
def test_migrate_rules_nothing_to_do() -> None:
    assert migrate_rules(_rulesets(["inline", "classic"]), LOGGER) == 0


@pytest.mark.usefixtures("request_context")
def test_migrate_rules_without_ruleset() -> None:
    assert migrate_rules(RulesetCollection({}), LOGGER) == 0
