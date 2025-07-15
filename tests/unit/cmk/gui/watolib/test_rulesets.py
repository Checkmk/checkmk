#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import sys
from collections.abc import Sequence
from io import StringIO

import pytest

from tests.testlib.unit.base_configuration_scenario import Scenario

from cmk.ccc.hostaddress import HostName

from cmk.utils.labels import Labels
from cmk.utils.paths import default_config_dir
from cmk.utils.rulesets.ruleset_matcher import RuleSpec

from cmk.automations.results import (
    AnalyzeHostRuleMatchesResult,
    AnalyzeServiceRuleMatchesResult,
)

from cmk.base.automations.check_mk import (
    AutomationAnalyzeHostRuleMatches,
    AutomationAnalyzeServiceRuleMatches,
)

from cmk.gui.watolib import rulesets
from cmk.gui.watolib.hosts_and_folders import Folder, FolderTree
from cmk.gui.watolib.rulesets import FolderRulesets, Rule, RuleConditions, RuleOptions, Ruleset


@pytest.fixture(name="mock_analyze_host_rule_matches_automation")
def fixture_mock_analyze_host_rule_matches_automation(monkeypatch: pytest.MonkeyPatch) -> None:
    """Replace rule matching via automation call, which does not work in unit test context,
    with a direct call to the automation"""

    def analyze_with_matcher(
        h: HostName, r: Sequence[Sequence[RuleSpec]], *, debug: bool
    ) -> AnalyzeHostRuleMatchesResult:
        ts = Scenario()
        ts.add_host(HostName("ding"))
        ts.add_host(HostName("dong"))
        ts.apply(monkeypatch)

        with monkeypatch.context() as m:
            m.setattr(sys, "stdin", StringIO(repr(r)))
            return AutomationAnalyzeHostRuleMatches().execute([h], None, None)

    monkeypatch.setattr(rulesets, "analyze_host_rule_matches", analyze_with_matcher)


@pytest.mark.usefixtures(
    "request_context", "with_admin_login", "mock_analyze_host_rule_matches_automation"
)
def test_analyse_host_ruleset() -> None:
    ruleset = _test_host_ruleset(folder := FolderTree().root_folder())
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
    )


def _test_host_ruleset(folder: Folder) -> Ruleset:
    ruleset = Ruleset("only_hosts", {})
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
    ) -> AnalyzeServiceRuleMatchesResult:
        ts = Scenario()
        ts.add_host(HostName("ding"))
        ts.apply(monkeypatch)

        with monkeypatch.context() as m:
            m.setattr(sys, "stdin", StringIO(repr((rules, service_labels))))
            return AutomationAnalyzeServiceRuleMatches().execute(
                [host_name, service_or_item], None, None
            )

    monkeypatch.setattr(rulesets, "analyze_service_rule_matches", analyze_with_matcher)


@pytest.mark.usefixtures(
    "request_context", "with_admin_login", "mock_analyze_service_rule_matches_automation"
)
def test_analyse_service_ruleset() -> None:
    ruleset = _test_service_ruleset(folder := FolderTree().root_folder())
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
    ruleset = Ruleset("ignored_services", {})
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
