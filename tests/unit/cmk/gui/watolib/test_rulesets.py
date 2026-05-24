#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="type-arg"

import sys
from collections.abc import Sequence
from io import StringIO

import pytest

from livestatus import SiteConfigurations

from cmk.automations.results import ABCAutomationResult
from cmk.base.automations.check_mk import (
    automation_analyze_host_rule_matches,
    automation_analyze_service_rule_matches,
)
from cmk.base.community_app import make_app
from cmk.ccc.hostaddress import HostName
from cmk.ccc.site import SiteId
from cmk.gui.config import active_config
from cmk.gui.watolib import rulesets
from cmk.gui.watolib.hosts_and_folders import Folder, FolderTree, HostsAndFoldersConfig
from cmk.gui.watolib.pending_changes import NoopPendingChangesStore, PendingChanges
from cmk.gui.watolib.rulesets import FolderRulesets, Rule, RuleConditions, RuleOptions, Ruleset
from cmk.utils.labels import Labels
from cmk.utils.paths import default_config_dir
from cmk.utils.rulesets.ruleset_matcher import RuleSpec
from tests.testlib.unit.base_configuration_scenario import Scenario


def _noop_pending_changes() -> PendingChanges:
    return PendingChanges(
        activation_sites=SiteConfigurations({}),
        local_site=SiteId("NO_SITE"),
        acting_user=None,
        store=NoopPendingChangesStore(),
        hooks=(),
    )


@pytest.fixture(name="mock_analyze_host_rule_matches_automation")
def fixture_mock_analyze_host_rule_matches_automation(monkeypatch: pytest.MonkeyPatch) -> None:
    """Replace rule matching via automation call, which does not work in unit test context,
    with a direct call to the automation"""

    def analyze_with_matcher(
        h: HostName, r: Sequence[Sequence[RuleSpec]], *, debug: bool
    ) -> ABCAutomationResult:
        ts = Scenario()
        ts.add_host(HostName("ding"))
        ts.add_host(HostName("dong"))
        ts.apply(monkeypatch)

        with monkeypatch.context() as m:
            m.setattr(sys, "stdin", StringIO(repr(r)))
            return automation_analyze_host_rule_matches.handler(make_app(), [h], None, None)

    monkeypatch.setattr(rulesets, "analyze_host_rule_matches", analyze_with_matcher)


@pytest.mark.usefixtures(
    "request_context", "with_admin_login", "mock_analyze_host_rule_matches_automation"
)
def test_analyse_host_ruleset() -> None:
    ruleset = _test_host_ruleset(
        folder := FolderTree(config=HostsAndFoldersConfig.from_config(active_config)).root_folder()
    )
    _test_hosts(folder)
    (default_config_dir / "main.mk").touch()
    FolderRulesets({ruleset.name: ruleset}, folder=folder).save_folder(
        pprint_value=False, debug=False
    )

    result = ruleset.analyse_ruleset(HostName("ding"), None, None, {}, debug=False)
    assert isinstance(result, tuple)
    assert len(result) == 2

    assert result[0] is False

    assert len(result[1]) == 1
    entry = result[1][0]
    assert entry[0] == folder
    assert entry[1] == 1  # index of rule in folder
    assert isinstance(entry[2], Rule)

    result = ruleset.analyse_ruleset(HostName("dong"), None, None, {}, debug=False)
    assert isinstance(result, tuple)
    assert len(result) == 2

    assert result[0] is True

    assert len(result[1]) == 1
    entry = result[1][0]
    assert entry[0] == folder
    assert entry[1] == 0  # index of rule in folder
    assert isinstance(entry[2], Rule)


def _test_hosts(folder: Folder) -> None:
    folder.create_hosts(
        [
            (HostName("ding"), {}, None),
            (HostName("dong"), {}, None),
        ],
        pprint_value=False,
        pending_changes=_noop_pending_changes(),
    )


def _test_host_ruleset(folder: Folder) -> Ruleset:
    ruleset = Ruleset("only_hosts")
    ruleset.append_rule(
        folder,
        Rule(
            id_="1",
            folder=folder,
            ruleset=ruleset,
            conditions=RuleConditions(
                host_folder=folder.path(),
                host_tags=None,
                host_label_groups=None,
                host_name=["dong"],
                service_description=None,
                service_label_groups=None,
            ),
            options=RuleOptions(
                disabled=None,
                description="",
                comment="",
                docu_url="",
            ),
            value=True,
        ),
    )
    ruleset.append_rule(
        folder,
        Rule(
            id_="2",
            folder=folder,
            ruleset=ruleset,
            conditions=RuleConditions(
                host_folder=folder.path(),
                host_tags=None,
                host_label_groups=None,
                host_name=["ding"],
                service_description=None,
                service_label_groups=None,
            ),
            options=RuleOptions(
                disabled=None,
                description="",
                comment="",
                docu_url="",
            ),
            value=False,
        ),
    )
    return ruleset


@pytest.fixture(name="mock_analyze_service_rule_matches_automation")
def fixture_mock_analyze_service_rule_matches_automation(monkeypatch: pytest.MonkeyPatch) -> None:
    """Replace rule matching via automation call, which does not work in unit test context,
    with a direct call to the automation"""

    def analyze_with_matcher(
        host_name: HostName,
        service_or_item: str,
        service_labels: Labels,
        rules: Sequence[Sequence[RuleSpec]],
        *,
        debug: bool,
    ) -> ABCAutomationResult:
        ts = Scenario()
        ts.add_host(HostName("ding"))
        ts.apply(monkeypatch)

        with monkeypatch.context() as m:
            m.setattr(sys, "stdin", StringIO(repr((rules, service_labels))))
            return automation_analyze_service_rule_matches.handler(
                make_app(), [host_name, service_or_item], None, None
            )

    monkeypatch.setattr(rulesets, "analyze_service_rule_matches", analyze_with_matcher)


@pytest.mark.usefixtures(
    "request_context", "with_admin_login", "mock_analyze_service_rule_matches_automation"
)
def test_analyse_service_ruleset() -> None:
    ruleset = _test_service_ruleset(
        folder := FolderTree(config=HostsAndFoldersConfig.from_config(active_config)).root_folder()
    )
    _test_hosts(folder)
    (default_config_dir / "main.mk").touch()
    FolderRulesets({ruleset.name: ruleset}, folder=folder).save_folder(
        pprint_value=False, debug=False
    )

    result = ruleset.analyse_ruleset(HostName("ding"), "Ding", "Ding", {}, debug=False)
    assert isinstance(result, tuple)
    assert len(result) == 2

    assert result[0] is True

    assert len(result[1]) == 1
    entry = result[1][0]
    assert entry[0] == folder
    assert entry[1] == 0  # index of rule in folder
    assert isinstance(entry[2], Rule)

    result = ruleset.analyse_ruleset(
        HostName("ding"), "Not matching", "Not matching", {}, debug=False
    )
    assert result == (None, [])


def _test_service_ruleset(folder: Folder) -> Ruleset:
    ruleset = Ruleset("ignored_services")
    ruleset.append_rule(
        folder,
        Rule(
            id_="1",
            folder=folder,
            ruleset=ruleset,
            conditions=RuleConditions(
                host_folder=folder.path(),
                host_tags=None,
                host_label_groups=None,
                host_name=["ding"],
                service_description=["Ding"],
                service_label_groups=None,
            ),
            options=RuleOptions(
                disabled=None,
                description="",
                comment="",
                docu_url="",
            ),
            value=True,
        ),
    )
    return ruleset


def test_get_rule_options_from_catalog_value_predefined() -> None:
    disk_value = {
        "properties": {"description": "", "comment": "", "docu_url": "", "disabled": False},
        "conditions": {"type": ("predefined", "my_predef_id")},
    }
    options = rulesets.get_rule_options_from_catalog_value(disk_value)
    assert options.predefined_condition_id == "my_predef_id"


def test_get_rule_options_from_catalog_value_explicit() -> None:
    disk_value = {
        "properties": {"description": "", "comment": "", "docu_url": "", "disabled": False},
        "conditions": {"type": ("explicit", {"folder_path": ""})},
    }
    options = rulesets.get_rule_options_from_catalog_value(disk_value)
    assert options.predefined_condition_id is None


def test_get_rule_options_from_catalog_value_not_a_dict() -> None:
    with pytest.raises(TypeError):
        rulesets.get_rule_options_from_catalog_value("not a dict")


def test_get_rule_options_from_catalog_value_malformed_type_tuple() -> None:
    disk_value = {
        "properties": {"description": "", "comment": "", "docu_url": "", "disabled": False},
        "conditions": {"type": "not-a-tuple"},
    }
    with pytest.raises(TypeError):
        rulesets.get_rule_options_from_catalog_value(disk_value)


def test_get_rule_options_from_catalog_value_unknown_type() -> None:
    disk_value = {
        "properties": {"description": "", "comment": "", "docu_url": "", "disabled": False},
        "conditions": {"type": ("bogus", None)},
    }
    with pytest.raises(TypeError):
        rulesets.get_rule_options_from_catalog_value(disk_value)
