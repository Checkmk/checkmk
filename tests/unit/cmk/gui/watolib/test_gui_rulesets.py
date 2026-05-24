#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="comparison-overlap"
# mypy: disable-error-code="misc"
# mypy: disable-error-code="no-any-return"
# mypy: disable-error-code="type-arg"
# mypy: disable-error-code="unreachable"
# mypy: disable-error-code="no-untyped-def"

import sys
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from io import StringIO
from unittest.mock import patch

import pytest

from livestatus import SiteConfigurations

from cmk.automations.results import ABCAutomationResult
from cmk.base.automations.check_mk import (
    automation_analyze_host_rule_effectiveness,
    automation_analyze_host_rule_matches,
)
from cmk.base.community_app import make_app
from cmk.base.config import LoadingResult
from cmk.ccc.hostaddress import HostName
from cmk.ccc.site import SiteId
from cmk.ccc.user import UserId
from cmk.gui.watolib import password_store, rulesets
from cmk.gui.watolib import rulesets as gui_rulesets_module
from cmk.gui.watolib.hosts_and_folders import Folder, folder_tree
from cmk.gui.watolib.pending_changes import NoopPendingChangesStore, PendingChanges
from cmk.gui.watolib.rulesets import Rule, Ruleset
from cmk.utils.global_ident_type import PROGRAM_ID_QUICK_SETUP
from cmk.utils.redis import disable_redis
from cmk.utils.rulesets.definition import RuleGroup
from cmk.utils.rulesets.ruleset_matcher import RulesetName, RuleSpec
from tests.testlib.unit.base_configuration_scenario import Scenario


def _noop_pending_changes() -> PendingChanges:
    return PendingChanges(
        activation_sites=SiteConfigurations({}),
        local_site=SiteId("NO_SITE"),
        acting_user=None,
        store=NoopPendingChangesStore(),
        hooks=(),
    )


def _ruleset(ruleset_name: RulesetName) -> rulesets.Ruleset:
    return rulesets.Ruleset(ruleset_name)


GEN_ID_COUNT = {"c": 0}


@pytest.fixture(autouse=True)
def fixture_gen_id(monkeypatch: pytest.MonkeyPatch, request_context: None) -> None:
    GEN_ID_COUNT["c"] = 0

    def _gen_id():
        GEN_ID_COUNT["c"] += 1
        return str(GEN_ID_COUNT["c"])

    monkeypatch.setattr(gui_rulesets_module, "gen_id", _gen_id)


def test_rule_clone() -> None:
    rule = rulesets.Rule.from_config(
        folder_tree().root_folder(),
        _ruleset("clustered_services"),
        {
            "id": "10",
            "value": True,
            "condition": {
                "host_name": ["HOSTLIST"],
                "service_description": [{"$regex": "SVC"}, {"$regex": "LIST"}],
            },
        },
    )

    cloned_rule = rule.clone()

    rule_config = dict(rule.to_config())
    del rule_config["id"]
    cloned_config = dict(cloned_rule.to_config())
    del cloned_config["id"]
    assert rule_config == cloned_config

    assert rule.folder == cloned_rule.folder
    assert rule.ruleset == cloned_rule.ruleset
    assert rule.id != cloned_rule.id


def test_rule_clone_locked() -> None:
    rule = rulesets.Rule.from_config(
        folder_tree().root_folder(),
        _ruleset("clustered_services"),
        {
            "id": "10",
            "value": True,
            "condition": {
                "host_name": ["HOSTLIST"],
                "service_description": [{"$regex": "SVC"}, {"$regex": "LIST"}],
            },
            "locked_by": {
                "site_id": "heute",
                "program_id": PROGRAM_ID_QUICK_SETUP,
                "instance_id": "...",
            },
        },
    )
    assert rule.locked_by is not None

    cloned_rule = rule.clone(preserve_id=True)
    assert rule.locked_by == cloned_rule.locked_by

    cloned_rule = rule.clone(preserve_id=False)
    assert cloned_rule.locked_by is None


@pytest.fixture(name="mock_analyze_host_rule_matches_automation")
def fixture_mock_analyze_host_rule_matches_automation(monkeypatch: pytest.MonkeyPatch) -> None:
    """Replace rule matching via automation call, which does not work in unit test context,
    with a direct call to the automation"""

    def analyze_with_matcher(
        h: HostName, r: Sequence[Sequence[RuleSpec]], *, debug: bool
    ) -> ABCAutomationResult:
        ts = Scenario()
        ts.add_host(HostName("foobar123"), host_path="/wato/regex_check/hosts.mk")
        ts.add_host(HostName("foobar456"), host_path="/wato/regex_check/hosts.mk")
        config_cache = ts.apply(monkeypatch)
        loading_result = LoadingResult(
            loaded_config=config_cache._loaded_config,
            config_cache=config_cache,
        )

        with monkeypatch.context() as m:
            m.setattr(sys, "stdin", StringIO(repr(r)))
            return automation_analyze_host_rule_matches.handler(
                make_app(), [h], None, loading_result
            )

    monkeypatch.setattr(rulesets, "analyze_host_rule_matches", analyze_with_matcher)


@pytest.mark.parametrize(
    "search_options, rule_config, folder_name, expected_result",
    [
        (
            {"rule_host_list": "foobar123"},
            {
                "id": "2a983a0a-7fab-4403-ab9d-5922fd8be529",
                "value": "all",
                "condition": {
                    "host_name": [{"$regex": ".*foo.*"}],
                },
                "options": {"disabled": False, "description": "foo"},
            },
            "regex_check",
            True,
        ),
        (
            {"rule_host_list": "foobar123"},
            {
                "id": "efd67dab-68f8-4d3c-a417-9f7e29ab48d5",
                "value": "all",
                "condition": {},
                "options": {"description": 'Put all hosts into the contact group "all"'},
            },
            "",
            True,
        ),
        (
            {"rule_host_list": "foobar123"},
            {
                "id": "59d84cde-ee3a-4f8d-8bec-fce35a2b0d15",
                "value": "all",
                "condition": {
                    "host_name": ["foobar123"],
                },
                "options": {"description": "foo"},
            },
            "regex_check",
            True,
        ),
        (
            {"rule_host_list": "foobar123"},
            {
                "id": "e10843c55-11ea-4eb2-bfbc-bce65cd2ae22",
                "value": "all",
                "condition": {
                    "host_name": [{"$regex": ".*foo123.*"}],
                },
                "options": {"description": "foo"},
            },
            "regex_check",
            False,
        ),
        (
            {"rule_host_list": "foobar123"},
            {
                "id": "e10843c55-11ea-4eb2-bfbc-bce65cd2ae22",
                "value": "all",
                "condition": {
                    "host_name": ["foobar123"],
                },
                "options": {"description": "foo"},
            },
            "wrong_folder",
            False,
        ),
        (
            {"rule_host_list": "foobar123 foobar456"},
            {
                "id": "e10843c55-11ea-4eb2-bfbc-bce65cd2ae22",
                "value": "all",
                "condition": {
                    "host_name": ["foobar123", "foobar456"],
                },
                "options": {"description": "foo"},
            },
            "",
            True,
        ),
        (
            {"rule_host_list": "foobar456"},
            {
                "id": "e10843c55-11ea-4eb2-bfbc-bce65cd2ae22",
                "value": "all",
                "condition": {
                    "host_name": ["foobar123", "foobar456"],
                },
                "options": {"description": "foo"},
            },
            "",
            True,
        ),
        (
            {"rule_host_list": "foobar123 foobar456"},
            {
                "id": "e10843c55-11ea-4eb2-bfbc-bce65cd2ae22",
                "value": "all",
                "condition": {
                    "host_name": ["foobar456"],
                },
                "options": {"description": "foo"},
            },
            "",
            False,
        ),
    ],
)
@pytest.mark.usefixtures("mock_analyze_host_rule_matches_automation")
def test_matches_search_with_rules(
    with_admin_login: UserId,
    search_options: rulesets.SearchOptions,
    rule_config: RuleSpec,
    folder_name: str,
    expected_result: bool,
) -> None:
    folder_tree().create_missing_folders(
        folder_name, pprint_value=False, pending_changes=_noop_pending_changes()
    )
    folder = folder_tree().folder(folder_name)
    ruleset = _ruleset("host_contactgroups")
    rule = rulesets.Rule.from_config(folder, ruleset, rule_config)
    ruleset.append_rule(folder, rule)

    assert ruleset.matches_search_with_rules(search_options, debug=False) == expected_result


@pytest.fixture(name="inline_analyze_host_rule_effectiveness_automation")
def fixture_inline_analyze_host_rule_effectiveness_automation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Inline rule matching automation call"""

    def analyze_host_rule_effectiveness(
        r: Sequence[Sequence[RuleSpec]], *, debug: bool
    ) -> ABCAutomationResult:
        ts = Scenario()
        ts.add_host(HostName("ding"))
        config_cache = ts.apply(monkeypatch)
        loading_result = LoadingResult(
            loaded_config=config_cache._loaded_config,
            config_cache=config_cache,
        )

        with monkeypatch.context() as m:
            m.setattr(sys, "stdin", StringIO(repr(r)))
            return automation_analyze_host_rule_effectiveness.handler(
                make_app(), [], None, loading_result
            )

    monkeypatch.setattr(
        rulesets, "analyze_host_rule_effectiveness", analyze_host_rule_effectiveness
    )


@pytest.mark.usefixtures("inline_analyze_host_rule_effectiveness_automation")
def test_matches_search_with_rules_negate_is_ineffective_finds_matching(
    with_admin_login: UserId,
) -> None:
    (ruleset := _ruleset("host_contactgroups")).append_rule(
        (folder := folder_tree().root_folder()),
        rulesets.Rule.from_config(
            folder,
            ruleset,
            {
                "id": "2a983a0a-7fab-4403-ab9d-5922fd8be529",
                "value": "all",
                "condition": {
                    "host_name": ["ding"],
                },
                "options": {"disabled": False, "description": "foo"},
            },
        ),
    )

    assert ruleset.matches_search_with_rules({"rule_ineffective": False}, debug=False) is True


@pytest.mark.usefixtures("inline_analyze_host_rule_effectiveness_automation")
def test_matches_search_with_rules_is_ineffective_finds_matching(with_admin_login: UserId) -> None:
    (ruleset := _ruleset("host_contactgroups")).append_rule(
        (folder := folder_tree().root_folder()),
        rulesets.Rule.from_config(
            folder,
            ruleset,
            {
                "id": "2a983a0a-7fab-4403-ab9d-5922fd8be529",
                "value": "all",
                "condition": {
                    "host_name": ["ding"],
                },
                "options": {"disabled": False, "description": "foo"},
            },
        ),
    )

    assert ruleset.matches_search_with_rules({"rule_ineffective": True}, debug=False) is False


@pytest.mark.usefixtures("inline_analyze_host_rule_effectiveness_automation")
def test_matches_search_with_rules_is_ineffective_finds_not_matching(
    with_admin_login: UserId,
) -> None:
    (ruleset := _ruleset("host_contactgroups")).append_rule(
        (folder := folder_tree().root_folder()),
        rulesets.Rule.from_config(
            folder,
            ruleset,
            {
                "id": "2a983a0a-7fab-4403-ab9d-5922fd8be529",
                "value": "all",
                "condition": {
                    "host_name": ["dong"],
                },
                "options": {"disabled": False, "description": "foo"},
            },
        ),
    )

    assert ruleset.matches_search_with_rules({"rule_ineffective": True}, debug=False) is True


@dataclass
class _RuleHelper:
    """Helps making and accessing rules"""

    rule: Callable[[], rulesets.Rule]
    secret_attr: str
    new_secret: object
    other_attr: str

    @staticmethod
    def _make_rule(ruleset: str, value: dict) -> rulesets.Rule:
        return rulesets.Rule.from_config(
            folder_tree().root_folder(),
            _ruleset(ruleset),
            {"id": "1", "value": value, "condition": {"host_name": ["HOSTLIST"]}},
        )

    @staticmethod
    def gcp_rule() -> rulesets.Rule:
        return _RuleHelper._make_rule(
            RuleGroup.SpecialAgents("gcp"),
            {
                "project": "old_value",
                "credentials": ("explicit_password", "uuid", "hunter2"),
                "services": ["gcs", "gce"],
            },
        )


@pytest.fixture()
def rule_helper() -> _RuleHelper:
    return _RuleHelper(
        _RuleHelper.gcp_rule, "credentials", ("explicit_password", "uuid", "geheim"), "project"
    )


def test_to_log_masks_secrets() -> None:
    log = str(_RuleHelper.gcp_rule().to_log())
    assert "'explicit_password'" in log, "password tuple is present"
    assert "hunter2" not in log, "password is masked"


def test_diff_rules_new_rule(rule_helper: _RuleHelper) -> None:
    new = rule_helper.rule()
    diff = new.ruleset.diff_rules(None, new)
    assert rule_helper.secret_attr in diff, "Attribute is added in new rule"
    assert "******" in diff, "Attribute is masked"


def test_diff_to_no_changes(rule_helper: _RuleHelper) -> None:
    rule = rule_helper.rule()
    # An uuid is created every time a rule is created/edited, so mock it here for the comparison.
    # The actual password should stay the same
    with patch.object(password_store, "ad_hoc_password_id", return_value="test-uuid"):
        assert rule.diff_to(rule) == "Nothing was changed."


def test_diff_to_secret_changed(rule_helper: _RuleHelper) -> None:
    old, new = rule_helper.rule(), rule_helper.rule()
    new.value[rule_helper.secret_attr] = rule_helper.new_secret
    assert old.diff_to(new) == "Redacted secrets changed."


def test_diff_to_secret_unchanged(rule_helper: _RuleHelper) -> None:
    old, new = rule_helper.rule(), rule_helper.rule()
    new.value[rule_helper.other_attr] = "new_value"
    # An uuid is created every time a rule is created/edited, so mock it here for the comparison.
    # The actual password should stay the same
    with patch.object(password_store, "ad_hoc_password_id", return_value="test-uuid"):
        diff = old.diff_to(new)
    assert "Redacted secrets changed." not in diff
    assert 'changed from "old_value" to "new_value".' in diff


def test_diff_to_secret_and_other_attribute_changed(rule_helper: _RuleHelper) -> None:
    old, new = rule_helper.rule(), rule_helper.rule()
    new.value[rule_helper.secret_attr] = rule_helper.new_secret
    new.value[rule_helper.other_attr] = "new_value"
    diff = old.diff_to(new)
    assert "Redacted secrets changed." in diff
    assert 'changed from "old_value" to "new_value".' in diff


def test_rules_grouped_by_folder() -> None:
    """Test sort order of rules"""
    tree = folder_tree()
    expected_folder_order: list[str] = [
        "folder2/folder2/folder2",
        "folder2/folder2/folder1",
        "folder2/folder2",
        "folder2/folder1/folder2",
        "folder2/folder1/folder1",
        "folder2/folder1",
        "folder2",
        "folder1/folder2/folder2",
        "folder1/folder2/folder1",
        "folder1/folder2",
        "folder1/folder1/folder2",
        "folder1/folder1/folder1",
        "folder1/folder1",
        "folder1",
        "folder4",
        "",
    ]

    root: Folder = tree.root_folder()
    ruleset: Ruleset = Ruleset("only_hosts")
    rules: list[tuple[Folder, int, Rule]] = [
        (root, 0, Rule.from_ruleset(root, ruleset, ruleset.rulespec.valuespec.default_value()))
    ]

    for nr in range(1, 3):
        folder = Folder.new(tree=tree, name="folder%d" % nr, parent_folder=root)
        rules.append(
            (
                folder,
                0,
                Rule.from_ruleset(folder, ruleset, ruleset.rulespec.valuespec.default_value()),
            )
        )
        for x in range(1, 3):
            subfolder = Folder.new(tree=tree, name="folder%d" % x, parent_folder=folder)
            rules.append(
                (
                    subfolder,
                    0,
                    Rule.from_ruleset(folder, ruleset, ruleset.rulespec.valuespec.default_value()),
                )
            )
            for y in range(1, 3):
                sub_subfolder = Folder.new(tree=tree, name="folder%d" % y, parent_folder=subfolder)
                rules.append(
                    (
                        sub_subfolder,
                        0,
                        Rule.from_ruleset(
                            folder, ruleset, ruleset.rulespec.valuespec.default_value()
                        ),
                    )
                )

    # Also test renamed folder
    folder4 = Folder.new(tree=tree, name="folder4", parent_folder=root)
    folder4._title = "abc"
    rules.append(
        (
            folder4,
            0,
            Rule.from_ruleset(folder4, ruleset, ruleset.rulespec.valuespec.default_value()),
        )
    )

    sorted_rules = sorted(
        rules, key=lambda x: (x[0].path().split("/"), len(rules) - x[1]), reverse=True
    )
    with disable_redis():
        assert (
            list(rule[0].path() for rule in rulesets.rules_grouped_by_folder(sorted_rules, root))
            == expected_folder_order
        )
