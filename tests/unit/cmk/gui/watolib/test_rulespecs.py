#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Sequence

import pytest
from pytest import MonkeyPatch

import cmk.ccc.version as cmk_version
from cmk.ccc.exceptions import MKGeneralException

from cmk.utils import paths
from cmk.utils.rulesets.definition import RuleGroup

import cmk.gui.watolib.rulespecs
from cmk.gui.exceptions import MKUserError
from cmk.gui.plugins.wato.utils import TimeperiodValuespec
from cmk.gui.utils.rule_specs.legacy_converter import GENERATED_GROUP_PREFIX
from cmk.gui.valuespec import Dictionary, FixedValue, TextInput, Tuple, ValueSpec
from cmk.gui.wato import register_check_parameters
from cmk.gui.watolib.main_menu import main_module_registry
from cmk.gui.watolib.rulespecs import (
    CheckTypeGroupSelection,
    get_rulegroup,
    HostRulespec,
    main_module_from_rulespec_group_name,
    ManualCheckParameterRulespec,
    MatchItemGeneratorRules,
    register_rule,
    register_rulegroup,
    Rulespec,
    rulespec_group_registry,
    rulespec_registry,
    RulespecGroup,
    RulespecGroupEnforcedServices,
    RulespecGroupRegistry,
    RulespecRegistry,
    RulespecSubGroup,
)
from cmk.gui.watolib.search import MatchItem


def test_rulespec_sub_group() -> None:
    class TestGroup(RulespecGroup):
        @property
        def name(self) -> str:
            return "main_group"

        @property
        def title(self) -> str:
            return "Title"

        @property
        def help(self):
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


def test_legacy_register_rulegroup(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr(
        cmk.gui.watolib.rulespecs, "rulespec_group_registry", RulespecGroupRegistry()
    )
    register_rulegroup("abc", "A B C", "abc 123")

    group = get_rulegroup("abc")
    assert isinstance(group, RulespecGroup)
    assert group.name == "abc"
    assert group.title == "A B C"
    assert group.help == "abc 123"


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


def _expected_rulespec_group_choices():
    expected = [
        ("activechecks", "HTTP, TCP, Email, ..."),
        ("agent", "Access to agents"),
        ("agent/check_mk_agent", "&nbsp;&nbsp;\u2319 Checkmk agent"),
        ("agent/general_settings", "&nbsp;&nbsp;\u2319 General Settings"),
        ("agents", "Agent rules"),
        ("agents/generic_options", "&nbsp;&nbsp;\u2319 Generic agent options"),
        ("checkparams", "Service discovery rules"),
        ("checkparams/discovery", "&nbsp;&nbsp;\u2319 Discovery of individual services"),
        (
            "checkparams/inventory_and_check_mk_settings",
            "&nbsp;&nbsp;\u2319 Discovery and Checkmk settings",
        ),
        ("datasource_programs", "Other integrations"),
        ("eventconsole", "Event Console rules"),
        ("inventory", "HW/SW Inventory"),
        ("host_monconf", "Host monitoring rules"),
        ("host_monconf/host_checks", "&nbsp;&nbsp;\u2319 Host checks"),
        ("host_monconf/host_notifications", "&nbsp;&nbsp;\u2319 Notifications"),
        ("host_monconf/host_various", "&nbsp;&nbsp;\u2319 Various"),
        ("monconf", "Service monitoring rules"),
        ("monconf/applications", "&nbsp;&nbsp;\u2319 Applications, Processes & Services"),
        ("monconf/networking", "&nbsp;&nbsp;\u2319 Networking"),
        ("monconf/os", "&nbsp;&nbsp;\u2319 Operating System Resources"),
        ("monconf/printers", "&nbsp;&nbsp;\u2319 Printers"),
        ("monconf/storage", "&nbsp;&nbsp;\u2319 Storage, Filesystems and Files"),
        (
            "monconf/environment",
            "&nbsp;&nbsp;\u2319 Temperature, Humidity, Electrical Parameters, etc.",
        ),
        ("monconf/hardware", "&nbsp;&nbsp;\u2319 Hardware, BIOS"),
        ("monconf/virtualization", "&nbsp;&nbsp;\u2319 Virtualization"),
        ("monconf/notifications", "&nbsp;&nbsp;\u2319 Notifications"),
        ("monconf/service_checks", "&nbsp;&nbsp;\u2319 Service Checks"),
        ("monconf/various", "&nbsp;&nbsp;\u2319 Various"),
        ("custom_checks", "Other services"),
        ("datasource_programs/apps", "&nbsp;&nbsp;⌙ Applications"),
        ("datasource_programs/cloud", "&nbsp;&nbsp;⌙ Cloud based environments"),
        ("datasource_programs/custom", "&nbsp;&nbsp;⌙ Custom integrations"),
        ("datasource_programs/hw", "&nbsp;&nbsp;⌙ Hardware"),
        ("datasource_programs/os", "&nbsp;&nbsp;⌙ Operating systems"),
        ("datasource_programs/testing", "&nbsp;&nbsp;⌙ Testing"),
        ("snmp", "SNMP rules"),
        ("static", "Enforced services"),
        ("static/applications", "&nbsp;&nbsp;⌙ Applications, Processes & Services"),
        ("static/environment", "&nbsp;&nbsp;⌙ Temperature, Humidity, Electrical Parameters, etc."),
        ("static/hardware", "&nbsp;&nbsp;⌙ Hardware, BIOS"),
        ("static/networking", "&nbsp;&nbsp;⌙ Networking"),
        ("static/os", "&nbsp;&nbsp;⌙ Operating System Resources"),
        ("static/printers", "&nbsp;&nbsp;⌙ Printers"),
        ("static/storage", "&nbsp;&nbsp;⌙ Storage, Filesystems and Files"),
        ("static/virtualization", "&nbsp;&nbsp;⌙ Virtualization"),
        ("vm_cloud_container", "VM, cloud, container"),
    ]

    if cmk_version.edition(paths.omd_root) is not cmk_version.Edition.CRE:
        expected += [
            ("agents/agent_plugins", "&nbsp;&nbsp;\u2319 Agent plug-ins"),
            ("agents/automatic_updates", "&nbsp;&nbsp;\u2319 Automatic Updates"),
            ("agents/linux_agent", "&nbsp;&nbsp;\u2319 Linux/UNIX agent options"),
            ("agents/windows_agent", "&nbsp;&nbsp;\u2319 Windows agent options"),
            ("agents/windows_modules", "&nbsp;&nbsp;\u2319 Windows Modules"),
        ]

    return expected


def test_rulespec_group_choices() -> None:
    actual_choices = [
        g
        for g in rulespec_group_registry.get_group_choices()
        if not _is_dynamically_generated_group(g[0])
    ]
    assert sorted(actual_choices) == sorted(_expected_rulespec_group_choices())


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


def test_rulespec_get_all_groups() -> None:
    expected_rulespec_groups = [
        "activechecks",
        "host_monconf/host_checks",
        "host_monconf/host_notifications",
        "host_monconf/host_various",
        "monconf/applications",
        "monconf/environment",
        "monconf/hardware",
        "monconf/service_checks",
        "monconf/networking",
        "monconf/notifications",
        "monconf/os",
        "monconf/printers",
        "monconf/storage",
        "monconf/various",
        "monconf/virtualization",
        "agent/general_settings",
        "agent/check_mk_agent",
        "agents/generic_options",
        "custom_checks",
        "snmp",
        "vm_cloud_container",
        "checkparams/inventory_and_check_mk_settings",
        "static/networking",
        "static/applications",
        "checkparams/discovery",
        "static/environment",
        "static/storage",
        "static/printers",
        "static/os",
        "static/virtualization",
        "static/hardware",
        "datasource_programs/apps",
        "datasource_programs/custom",
        "datasource_programs/hw",
        "datasource_programs/os",
        "inventory",
        "eventconsole",
    ]

    if cmk_version.edition(paths.omd_root) is not cmk_version.Edition.CRE:
        expected_rulespec_groups += [
            "agents/automatic_updates",
            "agents/linux_agent",
            "agents/windows_agent",
            "agents/windows_modules",
            "agents/agent_plugins",
        ]

    actual_rulespec_groups = [
        g for g in rulespec_registry.get_all_groups() if not _is_dynamically_generated_group(g)
    ]
    assert sorted(actual_rulespec_groups) == sorted(expected_rulespec_groups)


def _is_dynamically_generated_group(group_name: str) -> bool:
    # generated for the RulesetAPI v1
    return group_name.split("/")[-1].startswith(GENERATED_GROUP_PREFIX)


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

    if cmk_version.edition(paths.omd_root) is not cmk_version.Edition.CRE:
        expected_rulespec_host_groups += [
            "agents/agent_plugins",
            "agents/automatic_updates",
            "agents/linux_agent",
            "agents/windows_agent",
            "agents/windows_modules",
        ]

    group_names = [
        g
        for g in rulespec_group_registry.get_host_rulespec_group_names(True)
        if not _is_dynamically_generated_group(g)
    ]
    assert sorted(group_names) == sorted(expected_rulespec_host_groups)


def test_legacy_register_rule(monkeypatch: MonkeyPatch) -> None:
    group_registry = RulespecGroupRegistry()
    monkeypatch.setattr(cmk.gui.watolib.rulespecs, "rulespec_group_registry", group_registry)
    monkeypatch.setattr(
        cmk.gui.watolib.rulespecs, "rulespec_registry", RulespecRegistry(group_registry)
    )

    register_rule(
        "grouping",
        "dingdong_group",
        Dictionary(
            title="DING",
            help="s-o-s",
            elements=[],
        ),
    )

    group = get_rulegroup("grouping")
    assert group.name == "grouping"
    assert group.title == "grouping"

    rulespec_names = [
        r.name for r in cmk.gui.watolib.rulespecs.rulespec_registry.get_by_group("grouping")
    ]
    assert "dingdong_group" in rulespec_names
    assert len(rulespec_names) == 1

    # Check some default values
    spec = cmk.gui.watolib.rulespecs.rulespec_registry["dingdong_group"]

    assert spec.name == "dingdong_group"
    assert spec.group_name == "grouping"
    assert isinstance(spec.valuespec, Dictionary)
    assert spec.match_type == "first"
    assert spec.title == "DING"
    assert spec.help == "s-o-s"
    assert spec.item_spec is None
    assert spec.item_type is None
    assert spec.item_name is None
    assert spec.item_help is None
    assert spec.item_enum is None
    assert spec.is_optional is False
    assert spec.is_deprecated is False
    assert spec.factory_default == Rulespec.NO_FACTORY_DEFAULT


def test_legacy_register_rule_attributes(monkeypatch: MonkeyPatch) -> None:
    group_registry = RulespecGroupRegistry()
    monkeypatch.setattr(cmk.gui.watolib.rulespecs, "rulespec_group_registry", group_registry)
    monkeypatch.setattr(
        cmk.gui.watolib.rulespecs, "rulespec_registry", RulespecRegistry(group_registry)
    )

    register_rule(
        "dingdong_group",
        "rule_name",
        Dictionary(
            title="DING",
            elements=[],
        ),
        title="title",
        help="help me!",
        itemspec=TextInput(title="blub"),
        itemtype="service",
        itemname="Blub",
        itemhelp="Item help",
        match="dict",
        optional=True,
        deprecated=True,
        factory_default="humpf",
    )

    spec = cmk.gui.watolib.rulespecs.rulespec_registry["rule_name"]
    assert spec.name == "rule_name"
    assert spec.group_name == "dingdong_group"
    assert isinstance(spec.valuespec, Dictionary)
    assert spec.match_type == "dict"
    assert spec.title == "Deprecated: title"
    assert spec.help == "help me!"
    assert isinstance(spec.item_spec, TextInput)
    assert spec.item_type == "service"
    assert spec.item_name == "Blub"
    assert spec.item_help == "Item help"
    assert spec.is_optional is True
    assert spec.is_deprecated is True
    assert spec.factory_default == "humpf"


@pytest.fixture(name="patch_rulespec_registries")
def fixture_patch_rulespec_registries(monkeypatch: MonkeyPatch) -> None:
    group_registry = RulespecGroupRegistry()
    group_registry.register(RulespecGroupEnforcedServices)
    test_rulespec_registry = RulespecRegistry(group_registry)
    monkeypatch.setattr(cmk.gui.watolib.rulespecs, "rulespec_group_registry", group_registry)
    monkeypatch.setattr(cmk.gui.watolib.rulespecs, "rulespec_registry", test_rulespec_registry)
    monkeypatch.setattr(cmk.gui.plugins.wato.utils, "rulespec_registry", test_rulespec_registry)


def test_register_check_parameters(patch_rulespec_registries: None) -> None:
    register_check_parameters(
        "netblabla",
        "bla_params",
        "Title of bla",
        Dictionary(
            elements=[],
        ),
        TextInput(title="The object name"),
        "dict",
    )

    # Check either registration as discovery check ruleset
    group = get_rulegroup("checkparams/netblabla")
    assert group.name == "checkparams/netblabla"
    assert group.title == "netblabla"

    rulespec_names = [
        r.name
        for r in cmk.gui.watolib.rulespecs.rulespec_registry.get_by_group("checkparams/netblabla")
    ]
    assert RuleGroup.CheckgroupParameters("bla_params") in rulespec_names
    assert len(rulespec_names) == 1
    rulespec = cmk.gui.watolib.rulespecs.rulespec_registry[
        RuleGroup.CheckgroupParameters("bla_params")
    ]

    assert rulespec.title == "Title of bla"
    assert isinstance(rulespec.valuespec, TimeperiodValuespec)
    assert rulespec.is_for_services is True
    assert rulespec.item_type == "item"
    assert rulespec.item_name == "The object name"
    assert rulespec.item_help is None
    assert isinstance(rulespec.item_spec, TextInput)
    assert rulespec.match_type == "dict"
    assert rulespec.is_deprecated is False
    assert rulespec.is_optional is False

    # and also as static ruleset
    group = get_rulegroup("static/netblabla")
    assert group.name == "static/netblabla"
    assert group.title == "netblabla"

    rulespec_names = [
        r.name for r in cmk.gui.watolib.rulespecs.rulespec_registry.get_by_group("static/netblabla")
    ]
    assert RuleGroup.StaticChecks("bla_params") in rulespec_names
    assert len(rulespec_names) == 1
    rulespec = cmk.gui.watolib.rulespecs.rulespec_registry[RuleGroup.StaticChecks("bla_params")]
    assert isinstance(rulespec, ManualCheckParameterRulespec)

    # Static checks rulespecs are always
    # a) host rulespecs
    # b) match_type == "all"
    assert rulespec.is_for_services is False
    assert rulespec.match_type == "all"

    assert rulespec.title == "Title of bla"
    assert rulespec.item_type is None
    assert rulespec.item_name is None
    assert rulespec.item_help is None
    # The item_spec of the ManualCheckParameterRulespec fetched differently,
    # since it is no actual item spec
    assert isinstance(rulespec._get_item_valuespec(), TextInput)
    assert rulespec.is_deprecated is False
    assert rulespec.is_optional is False

    # Static checks wrap the valuespec into a 3-element tuple
    # - check type selection
    # - item spec for the service name
    # - original valuespec (TimeperiodSelection)
    assert isinstance(rulespec.valuespec, Tuple)
    assert len(rulespec.valuespec._elements) == 3
    assert isinstance(rulespec.valuespec._elements[0], CheckTypeGroupSelection)
    assert isinstance(rulespec.valuespec._elements[1], ValueSpec)
    assert isinstance(rulespec.valuespec._elements[2], TimeperiodValuespec)


def test_register_host_check_parameters(patch_rulespec_registries: None) -> None:
    register_check_parameters(
        "netblabla",
        "bla_params",
        "Title of bla",
        Dictionary(
            elements=[],
        ),
        None,
        "dict",
    )

    # Check either registration as discovery check ruleset
    rulespec = cmk.gui.watolib.rulespecs.rulespec_registry[
        RuleGroup.CheckgroupParameters("bla_params")
    ]
    assert rulespec.is_for_services is False

    rulespec = cmk.gui.watolib.rulespecs.rulespec_registry[RuleGroup.StaticChecks("bla_params")]
    assert rulespec.is_for_services is False
    assert isinstance(rulespec.valuespec, Tuple)
    assert len(rulespec.valuespec._elements) == 3
    assert isinstance(rulespec.valuespec._elements[0], CheckTypeGroupSelection)
    assert isinstance(rulespec.valuespec._elements[1], ValueSpec)
    assert isinstance(rulespec.valuespec._elements[2], TimeperiodValuespec)


def test_register_without_discovery(patch_rulespec_registries: None) -> None:
    with pytest.raises(MKGeneralException, match="registering manual check"):
        register_check_parameters(
            "netblabla",
            "bla_params",
            "Title of bla",
            Dictionary(
                elements=[],
            ),
            None,
            "dict",
            has_inventory=False,
        )


def test_register_without_static(patch_rulespec_registries: None) -> None:
    register_check_parameters(
        "netblabla",
        "bla_params",
        "Title of bla",
        Dictionary(
            elements=[],
        ),
        None,
        "dict",
        has_inventory=True,
        register_static_check=False,
    )

    # Check either registration as discovery check ruleset
    rulespec = cmk.gui.watolib.rulespecs.rulespec_registry[
        RuleGroup.CheckgroupParameters("bla_params")
    ]
    assert rulespec.is_for_services is False

    assert RuleGroup.StaticChecks("bla_params") not in cmk.gui.watolib.rulespecs.rulespec_registry


class DummyGroup(RulespecGroup):
    @property
    def name(self) -> str:
        return "group"

    @property
    def title(self) -> str:
        return "Group title"

    @property
    def help(self):
        return "help text"


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
        def help(self):
            return ""

    rulespec_group_reg = RulespecGroupRegistry()
    rulespec_group_reg.register(SomeRulespecGroup)

    rulespec_reg = RulespecRegistry(rulespec_group_reg)
    rulespec_reg.register(
        HostRulespec(
            name="some_host_rulespec",
            group=SomeRulespecGroup,
            valuespec=lambda: TextInput(),
            title=lambda: "Title",
        )
    )
    rulespec_reg.register(
        HostRulespec(
            name="some_deprecated_host_rulespec",
            group=SomeRulespecGroup,
            valuespec=lambda: TextInput(),
            title=lambda: "Title",
            is_deprecated=True,
        )
    )

    match_item_generator = MatchItemGeneratorRules(
        "rules",
        rulespec_group_reg,
        rulespec_reg,
    )
    assert list(match_item_generator.generate_match_items()) == [
        MatchItem(
            title="Title",
            topic="Rulespec Group",
            url="wato.py?mode=edit_ruleset&varname=some_host_rulespec",
            match_texts=["title", "some_host_rulespec"],
        ),
        MatchItem(
            title="Deprecated: Title",
            topic="Deprecated rulesets",
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
    # The title is e.g. shown in the mega menu search. With duplicate entries a user could not
    # distinguish where a rule is located in the menu hierarchy.
    main_group_titles = [e().title for e in rulespec_group_registry.get_main_groups()]
    assert len(main_group_titles) == len(set(main_group_titles)), "Main group titles are not unique"


def test_validate_datatype_timeperiod_valuespec_inner() -> None:
    # make sure TimeperiodValuespec does propagate validate_datatype to its child
    value_spec = TimeperiodValuespec(Dictionary(elements=[]))
    with pytest.raises(MKUserError):
        value_spec.validate_datatype(["not", "a", "string"], "")  # type: ignore[arg-type]
