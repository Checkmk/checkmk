#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="explicit-any"

# ruff: noqa: ARG001
# ruff: noqa: ARG005
# ruff: noqa: SLF001

from collections.abc import Callable, Iterator

import pytest

from cmk.agent_based.v2 import (
    AgentSection,
    HostLabelGenerator,
    matches,
    OIDEnd,
    SimpleSNMPSection,
    SNMPSection,
    SNMPTree,
    StringByteTable,
    StringTable,
)
from cmk.agent_based.v3_unstable import (
    AggregatedInstantGauge,
    CustomMetricMeta,
    MetricSelector,
    MetricsRecord,
    MetricsSection,
    MetricType,
)
from cmk.checkengine.plugin_backend import section_plugins
from cmk.checkengine.plugins import (
    AgentSectionPlugin,
    ParsedSectionName,
    SectionName,
    SNMPSectionPlugin,
)
from cmk.discover_plugins import PluginLocation
from cmk.ruleset_matcher.ruleset_name import RuleSetName


def _generator_function() -> Iterator[None]:
    yield None


def parse_dummy(string_table: object) -> None:
    return None


@pytest.mark.parametrize(
    "parse_function",
    [
        _generator_function,
        "bar",
        b"foo",
        None,
        ("foo", "bar"),
        42,
    ],
)
def test_validate_parse_function_type(parse_function: object) -> None:
    with pytest.raises(TypeError):
        section_plugins.validate_parse_function(
            parse_function,  # type: ignore[arg-type]
            expected_annotations={(str, "str")},  # irrelevant for test
        )


@pytest.mark.parametrize(
    "parse_function",
    [
        # argument name must be string_table, and string_table only.
        lambda foo: None,
        lambda string_table, foo: None,
        lambda foo, string_table: None,
    ],
)
def test_validate_parse_function_value(parse_function: Callable[..., None]) -> None:  # type: ignore[misc]
    with pytest.raises(ValueError):
        section_plugins.validate_parse_function(
            parse_function,
            expected_annotations={(str, "str")},  # ignored
        )


def test_validate_parse_function_annotation_string_table() -> None:
    def _parse_function(string_table: list[StringTable]) -> list[StringTable]:
        return string_table

    with pytest.raises(TypeError):
        section_plugins.validate_parse_function(
            _parse_function,
            expected_annotations={(StringByteTable, "StringByteTable")},
        )

    section_plugins.validate_parse_function(
        _parse_function,
        expected_annotations={(list[StringTable], "List[StringTable]")},
    )


def test_validate_supersedings_raise_duplicate() -> None:
    supersedes = [
        SectionName("foo"),
        SectionName("bar"),
        SectionName("foo"),
    ]

    with pytest.raises(ValueError, match="duplicate"):
        section_plugins._validate_supersedings(SectionName("jim"), supersedes)


def test_validate_supersedings_raise_self_superseding() -> None:
    with pytest.raises(ValueError, match="cannot supersede myself"):
        section_plugins._validate_supersedings(SectionName("foo"), [SectionName("foo")])


def test_create_agent_section_plugin() -> None:
    plugin = section_plugins.create_agent_section_plugin(
        AgentSection(
            name="norris",
            parsed_section_name="chuck",
            parse_function=parse_dummy,
            supersedes=["foo", "bar"],
        ),
        location=PluginLocation(module="norris", name="check_plugin_norris"),
        validate=True,
    )

    assert isinstance(plugin, AgentSectionPlugin)
    assert len(plugin) == 9
    assert plugin.name == SectionName("norris")
    assert plugin.parsed_section_name == ParsedSectionName("chuck")
    assert plugin.parse_function is parse_dummy
    assert plugin.host_label_function is section_plugins._noop_host_label_function
    assert plugin.host_label_default_parameters is None
    assert plugin.host_label_ruleset_name is None
    assert plugin.host_label_ruleset_type == "merged"
    assert plugin.supersedes == {SectionName("bar"), SectionName("foo")}


def test_create_metrics_section_plugin() -> None:
    plugin = section_plugins.create_metrics_section_plugin(
        MetricsSection(
            name="norris",
            selectors=[MetricSelector(metric_name="cpu.load")],
            parsed_section_name="chuck",
            parse_function=parse_dummy,
            supersedes=["foo", "bar"],
        ),
        location=PluginLocation(module="norris", name="metrics_section_norris"),
        validate=True,
    )

    assert isinstance(plugin, AgentSectionPlugin)
    assert len(plugin) == 9
    assert plugin.name == SectionName("norris")
    assert plugin.parsed_section_name == ParsedSectionName("chuck")
    assert plugin.host_label_function is section_plugins._noop_host_label_function
    assert plugin.host_label_default_parameters is None
    assert plugin.host_label_ruleset_name is None
    assert plugin.host_label_ruleset_type == "merged"
    assert plugin.supersedes == {SectionName("bar"), SectionName("foo")}


def test_create_metrics_section_plugin_defaults() -> None:
    plugin = section_plugins.create_metrics_section_plugin(
        MetricsSection(
            name="norris",
            selectors=[MetricSelector(metric_name="cpu.load")],
            parse_function=parse_dummy,
        ),
        location=PluginLocation(module="norris", name="metrics_section_norris"),
        validate=True,
    )

    assert plugin.parsed_section_name == ParsedSectionName("norris")
    assert plugin.supersedes == set()


def test_create_metrics_section_plugin_host_label_ruleset() -> None:
    def host_labels(params: object, section: object) -> HostLabelGenerator:
        yield from ()

    plugin = section_plugins.create_metrics_section_plugin(
        MetricsSection(
            name="norris",
            selectors=[MetricSelector(metric_name="cpu.load")],
            parse_function=parse_dummy,
            host_label_function=host_labels,
            host_label_default_parameters={"levels": ("fixed", (1, 2))},
            host_label_ruleset_name="norris_rules",
        ),
        location=PluginLocation(module="norris", name="metrics_section_norris"),
        validate=True,
    )

    assert plugin.host_label_default_parameters == {"levels": ("fixed", (1, 2))}
    assert plugin.host_label_ruleset_name == RuleSetName("norris_rules")
    assert plugin.host_label_ruleset_type == "merged"


def test_create_metrics_section_plugin_deserializes() -> None:
    """The engine deserializes the raw agent output before calling the plugin's parse function."""
    records = [
        MetricsRecord(
            filter_name="the_filter",
            metadata=CustomMetricMeta(
                series_id="series-1",
                metric_type=MetricType.GAUGE,
                name="the_metric",
                description="A metric",
                resource_attributes={},
                scope_name="scope",
                scope_version="1.0",
                scope_attributes={},
                attributes={},
                unit="{units}",
            ),
            data=AggregatedInstantGauge(series_id="series-1", value=42.0),
        ),
    ]

    plugin = section_plugins.create_metrics_section_plugin(
        MetricsSection(
            name="norris",
            selectors=[MetricSelector(metric_name="cpu.load")],
            parse_function=list,
        ),
        location=PluginLocation(module="norris", name="metrics_section_norris"),
        validate=True,
    )

    string_table = [[record.model_dump_json()] for record in records]
    assert plugin.parse_function(string_table) == records


def test_create_snmp_section_plugin() -> None:
    trees: list[SNMPTree] = [
        SNMPTree(
            base=".1.2.3",
            oids=[OIDEnd(), "2.3"],
        ),
    ]

    detect = matches(".1.2.3.4.5", "Foo.*")

    plugin = section_plugins.create_snmp_section_plugin(
        SNMPSection(
            name="norris",
            parsed_section_name="chuck",
            parse_function=parse_dummy,
            fetch=trees,
            detect=detect,
            supersedes=["foo", "bar"],
        ),
        location=PluginLocation(module="norris", name="check_plugin_norris"),
        validate=True,
    )

    assert isinstance(plugin, SNMPSectionPlugin)
    assert len(plugin) == 11
    assert plugin.name == SectionName("norris")
    assert plugin.parsed_section_name == ParsedSectionName("chuck")
    assert plugin.parse_function is parse_dummy
    assert plugin.host_label_function is section_plugins._noop_host_label_function
    assert plugin.host_label_default_parameters is None
    assert plugin.host_label_ruleset_name is None
    assert plugin.host_label_ruleset_type == "merged"
    assert plugin.detect_spec == detect
    assert plugin.trees == trees
    assert plugin.supersedes == {SectionName("bar"), SectionName("foo")}


def test_create_snmp_section_plugin_single_tree() -> None:
    single_tree = SNMPTree(base=".1.2.3", oids=[OIDEnd(), "2.3"])

    plugin = section_plugins.create_snmp_section_plugin(
        SimpleSNMPSection(
            name="norris",
            parse_function=lambda string_table: string_table,
            # just one, no list:
            fetch=single_tree,
            detect=matches(".1.2.3.4.5", "Foo.*"),
        ),
        location=PluginLocation(module="norris", name="check_plugin_norris"),
        validate=True,
    )

    assert plugin.trees == [single_tree]
    # the plug-in only specified a single tree (not a list),
    # so a wrapper should unpack the argument:
    assert plugin.parse_function([[["A", "B"]]]) == [["A", "B"]]


def test_validate_supersedings_raise_implicit() -> None:
    all_supersedes_invalid = {
        SectionName("foo"): {SectionName("bar")},
        SectionName("bar"): {SectionName("gee")},
    }

    with pytest.raises(
        ValueError,
        match="implicitly supersedes section.*You must add those to the supersedes keyword",
    ):
        section_plugins.validate_section_supersedes(all_supersedes_invalid)

    # add the implicit superseding, then it should be OK:
    all_supersedes_valid = all_supersedes_invalid.copy()
    all_supersedes_valid[SectionName("foo")].add(SectionName("gee"))

    section_plugins.validate_section_supersedes(all_supersedes_valid)


def test_validate_supersedings_raise_cyclic() -> None:
    all_supersedes_cyclic = {
        SectionName("foo"): {SectionName("bar")},
        SectionName("bar"): {SectionName("foo")},
    }

    with pytest.raises(
        ValueError,
        match="implicitly supersedes section.*This leads to a cyclic superseding",
    ):
        section_plugins.validate_section_supersedes(all_supersedes_cyclic)
