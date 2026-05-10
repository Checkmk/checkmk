#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="comparison-overlap"

from collections.abc import Sequence

import pytest
from pytest import MonkeyPatch

import cmk.gui.watolib.rulespecs
from cmk.gui.exceptions import MKUserError
from cmk.gui.plugins.wato.utils import TimeperiodValuespec
from cmk.gui.rule_specs.legacy_converter import GENERATED_GROUP_PREFIX
from cmk.gui.search import MatchItem
from cmk.gui.utils.roles import UserPermissions
from cmk.gui.valuespec import Dictionary, FixedValue, TextInput
from cmk.gui.watolib.main_menu import main_module_registry
from cmk.gui.watolib.rule_match_item_generator import MatchItemGeneratorRules
from cmk.gui.watolib.rulespecs import (
    get_rulegroup,
    HostRulespec,
    main_module_from_rulespec_group_name,
    rulespec_group_registry,
    RulespecGroup,
    RulespecGroupRegistry,
    RulespecRegistry,
    RulespecSubGroup,
)


def test_rulespec_sub_group() -> None:
    class TestGroup(RulespecGroup):
        @property
        def name(self) -> str:
            return "main_group"

        @property
        def title(self) -> str:
            return "Title"

        @property
        def help(self) -> str:
            return "help text"

    class TestSubGroup(RulespecSubGroup):
        @property
        def main_group(self) -> type[RulespecGroup]:
            return TestGroup

        @property
        def sub_group_name(self) -> str:
            return "sub_group"

        @property
        def title(self) -> str:
            return "Sub"

    test_sub_group = TestSubGroup()
    assert test_sub_group.name == "main_group/sub_group"
    assert test_sub_group.title == "Sub"


def test_legacy_get_not_existing_rulegroup(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr(
        cmk.gui.watolib.rulespecs, "rulespec_group_registry", RulespecGroupRegistry()
    )

    group = get_rulegroup("xyz")
    assert isinstance(group, cmk.gui.watolib.rulespecs.RulespecGroup)
    assert group.name == "xyz"
    assert group.title == "xyz"
    assert group.help is None


def test_legacy_get_not_existing_rule_sub_group(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr(
        cmk.gui.watolib.rulespecs, "rulespec_group_registry", RulespecGroupRegistry()
    )

    group = get_rulegroup("xyz/Abc, xxx ding./aaa")
    assert isinstance(group, RulespecSubGroup)
    assert group.name == "xyz/abcxxxdingaaa"
    assert group.title == "Abc, xxx ding./aaa"
    assert group.help is None


@pytest.mark.parametrize(
    "term,result",
    [
        (
            "host_monconf",
            [
                "host_monconf",
                "host_monconf/host_checks",
                "host_monconf/host_notifications",
                "host_monconf/host_various",
            ],
        ),
        (
            "monconf",
            [
                "monconf",
                "monconf/applications",
                "monconf/environment",
                "monconf/hardware",
                "monconf/networking",
                "monconf/notifications",
                "monconf/os",
                "monconf/printers",
                "monconf/service_checks",
                "monconf/storage",
                "monconf/various",
                "monconf/virtualization",
            ],
        ),
        ("monconf/various", ["monconf/various"]),
        (
            "agent",
            [
                "agent",
                "agent/check_mk_agent",
                "agent/general_settings",
            ],
        ),
    ],
)
def test_rulespec_get_matching_group_names(term: str, result: Sequence[str]) -> None:
    actual_names = [
        g
        for g in rulespec_group_registry.get_matching_group_names(term)
        if not _is_dynamically_generated_group(g)
    ]
    assert sorted(actual_names) == sorted(result)


def test_rulespec_get_main_groups() -> None:
    main_group_names = [g_class().name for g_class in rulespec_group_registry.get_main_groups()]
    assert sorted(main_group_names) == sorted(
        [
            "activechecks",
            "monconf",
            "host_monconf",
            "agent",
            "agents",
            "checkparams",
            "static",
            "datasource_programs",
            "inventory",
            "eventconsole",
            "custom_checks",
            "snmp",
            "vm_cloud_container",
        ]
    )


def _is_dynamically_generated_group(group_name: str) -> bool:
    # generated for the RulesetAPI v1
    return group_name.rsplit("/", maxsplit=1)[-1].startswith(GENERATED_GROUP_PREFIX)


def test_rulespec_get_host_groups() -> None:
    expected_rulespec_host_groups = [
        "checkparams",
        "checkparams/discovery",
        "checkparams/inventory_and_check_mk_settings",
        "host_monconf/host_checks",
        "host_monconf/host_notifications",
        "host_monconf/host_various",
        "agent/general_settings",
        "agent/check_mk_agent",
        "agents/generic_options",
        "datasource_programs",
        "datasource_programs/apps",
        "datasource_programs/cloud",
        "datasource_programs/container",
        "datasource_programs/custom",
        "datasource_programs/hw",
        "datasource_programs/os",
        "datasource_programs/testing",
        "inventory",
        "eventconsole",
        "custom_checks",
        "snmp",
        "vm_cloud_container",
    ]

    group_names = [
        g
        for g in rulespec_group_registry.get_host_rulespec_group_names(True)
        if not _is_dynamically_generated_group(g)
    ]
    assert sorted(group_names) == sorted(expected_rulespec_host_groups)


class DummyGroup(RulespecGroup):
    @property
    def name(self) -> str:
        return "group"

    @property
    def title(self) -> str:
        return "Group title"

    @property
    def help(self) -> str:
        return "help text"


class DummySubGroup(RulespecSubGroup):
    @property
    def main_group(self) -> type[RulespecGroup]:
        return DummyGroup

    @property
    def sub_group_name(self) -> str:
        return "sub"

    @property
    def title(self) -> str:
        return "Sub title"


def test_main_group_registered_twice_appears_once_in_get_main_groups() -> None:
    registry = RulespecGroupRegistry()
    registry.register(DummyGroup)
    registry.register(DummyGroup)

    assert [g().name for g in registry.get_main_groups()] == ["group"]


def test_sub_group_registered_twice_appears_once_in_get_group_choices() -> None:
    registry = RulespecGroupRegistry()
    registry.register(DummyGroup)
    registry.register(DummySubGroup)
    registry.register(DummySubGroup)

    assert [name for name, _ in registry.get_group_choices() if "/" in name] == ["group/sub"]


def test_get_group_choices_no_duplicates_after_double_registration() -> None:
    registry = RulespecGroupRegistry()
    registry.register(DummyGroup)
    registry.register(DummySubGroup)
    registry.register(DummyGroup)
    registry.register(DummySubGroup)

    choice_names = [name for name, _ in registry.get_group_choices()]
    assert choice_names == ["group", "group/sub"]


def test_rulespecs_get_by_group() -> None:
    group_registry = RulespecGroupRegistry()
    registry = RulespecRegistry(group_registry)

    with pytest.raises(KeyError):
        registry.get_by_group("group")

    group_registry.register(DummyGroup)
    result = registry.get_by_group("group")
    assert len(result) == 0

    registry.register(
        HostRulespec(name="dummy_name", group=DummyGroup, valuespec=lambda: FixedValue(value=None))
    )
    result = registry.get_by_group("group")
    assert len(result) == 1
    assert isinstance(result[0], HostRulespec)


def test_match_item_generator_rules() -> None:
    class SomeRulespecGroup(RulespecGroup):
        @property
        def name(self) -> str:
            return "rulespec_group"

        @property
        def title(self) -> str:
            return "Rulespec Group"

        @property
        def help(self) -> str:
            return ""

    rulespec_group_reg = RulespecGroupRegistry()
    rulespec_group_reg.register(SomeRulespecGroup)

    rulespec_reg = RulespecRegistry(rulespec_group_reg)
    rulespec_reg.register(
        HostRulespec(
            name="some_host_rulespec",
            group=SomeRulespecGroup,
            valuespec=TextInput,
            title=lambda: "Title",
        )
    )
    rulespec_reg.register(
        HostRulespec(
            name="some_deprecated_host_rulespec",
            group=SomeRulespecGroup,
            valuespec=TextInput,
            title=lambda: "Title",
            is_deprecated=True,
        )
    )

    match_item_generator = MatchItemGeneratorRules(
        "rules",
        rulespec_group_reg,
        rulespec_reg,
    )
    assert list(match_item_generator.generate_match_items(UserPermissions({}, {}, {}, []))) == [
        MatchItem(
            title="Title",
            topic="Rulespec Group",
            url="wato.py?mode=edit_ruleset&varname=some_host_rulespec",
            match_texts=["title", "some_host_rulespec"],
        ),
        MatchItem(
            title="Deprecated: Title",
            topic="Deprecated rule sets",
            url="wato.py?mode=edit_ruleset&varname=some_deprecated_host_rulespec",
            match_texts=["deprecated: title", "some_deprecated_host_rulespec"],
        ),
    ]


def test_all_rulespec_groups_have_main_group() -> None:
    for rulespec_group_name, rulespec_group_cls in rulespec_group_registry.items():
        if issubclass(rulespec_group_cls, RulespecGroup):
            main_module_from_rulespec_group_name(
                rulespec_group_name,
                main_module_registry,
            )


def test_rulespec_groups_have_unique_names() -> None:
    # The title is e.g. shown in the main menu search. With duplicate entries a user could not
    # distinguish where a rule is located in the menu hierarchy.
    main_group_titles = [e().title for e in rulespec_group_registry.get_main_groups()]
    assert len(main_group_titles) == len(set(main_group_titles)), "Main group titles are not unique"


def test_validate_datatype_timeperiod_valuespec_inner() -> None:
    # make sure TimeperiodValuespec does propagate validate_datatype to its child
    value_spec = TimeperiodValuespec(Dictionary(elements=[]))
    with pytest.raises(MKUserError):
        value_spec.validate_datatype(["not", "a", "string"], "")  # type: ignore[arg-type]
