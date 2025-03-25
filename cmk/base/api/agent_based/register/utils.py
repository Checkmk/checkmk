#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import inspect
from collections import defaultdict
from collections.abc import Callable, Collection, Iterable, Mapping, Sequence
from typing import Final, get_args, Literal, NoReturn, Union

from cmk.utils.rulesets import RuleSetName
from cmk.utils.sectionname import SectionName

from cmk.checkengine.plugins import CheckPluginName, InventoryPlugin, InventoryPluginName
from cmk.checkengine.sectionparser import ParsedSectionName

from cmk.base.api.agent_based.plugin_classes import (
    AgentBasedPlugins,
    CheckPlugin,
    SectionPlugin,
    SNMPSectionPlugin,
)

from cmk.agent_based.v1.register import RuleSetType

TypeLabel = Literal["check", "cluster_check", "discovery", "host_label", "inventory"]

ITEM_VARIABLE: Final = "%s"


def create_subscribed_sections(
    sections: list[str] | None,
    plugin_name: InventoryPluginName | CheckPluginName,
) -> list[ParsedSectionName]:
    if sections is None:
        return [ParsedSectionName(str(plugin_name))]
    if not isinstance(sections, list):
        raise TypeError(f"'sections' must be a list of str, got {sections!r}")
    if not sections:
        raise ValueError("'sections' must not be empty")
    return [ParsedSectionName(n) for n in sections]


def validate_function_arguments(
    *,
    type_label: TypeLabel,
    function: Callable,
    has_item: bool,
    default_params: Mapping[str, object] | None,
    sections: list[ParsedSectionName],
) -> None:
    """Validate the functions signature and type"""
    if not inspect.isgeneratorfunction(function):
        raise TypeError(f"{type_label}_function must be a generator function")

    expected_params = []
    if has_item:
        expected_params.append("item")
    if default_params is not None:
        expected_params.append("params")
    if len(sections) == 1:
        expected_params.append("section")
    else:
        expected_params.extend(f"section_{s}" for s in sections)

    parameters = inspect.signature(function).parameters
    present_params = list(parameters)

    if expected_params == present_params:
        return _validate_optional_section_annotation(
            parameters=parameters,
            type_label=type_label,
        )
    _raise_appropriate_type_error(
        expected_params=expected_params,
        present_params=present_params,
        type_label=type_label,
        has_item=has_item,
    )


def _raise_appropriate_type_error(
    *,
    expected_params: Sequence[str],
    present_params: Sequence[str],
    type_label: TypeLabel,
    has_item: bool,
) -> NoReturn:
    """Raise with appropriate error message:"""

    if set(expected_params) == set(present_params):  # not len()!
        exp_str = ", ".join(expected_params)
        raise TypeError(f"{type_label}_function: wrong order of arguments. Expected: {exp_str}")

    symm_diff = set(expected_params).symmetric_difference(present_params)

    if "item" in symm_diff:
        missing_or_unexpected = "missing" if has_item else "unexpected"
        raise TypeError(f"{type_label}_function: {missing_or_unexpected} 'item' argument")

    if "params" in symm_diff:
        raise TypeError(
            f"{type_label}_function: 'params' argument expected if "
            "and only if default parameters are not None"
        )

    exp_str = ", ".join(expected_params)
    act_str = ", ".join(present_params)
    raise TypeError(
        f"{type_label}_function: expected arguments: '{exp_str}', actual arguments: '{act_str}'"
    )


# Note: The concrete union type parameters below don't matter, we are just interested in the type
# constructors of the new & old-skool unions.
_UNION_TYPES: Final = (type(int | str), type(Union[int, str]))


# Poor man's pattern matching on generic types ahead! Note that we see Optional as a union at
# runtime, so no special handling is needed for it.
def _is_optional(annotation: object) -> bool:
    return issubclass(type(annotation), _UNION_TYPES) and type(None) in get_args(annotation)


# Check if the given parameter has a type of the form 'Mapping[str, T | None]' for any T.
def _is_valid_cluster_section_parameter(p: inspect.Parameter) -> bool:
    return (
        any(map(str(p.annotation).startswith, ("collections.abc.Mapping[", "typing.Mapping[")))
        and (len(args := get_args(p.annotation)) == 2)
        and issubclass(args[0], str)
        and _is_optional(args[1])
    )


def _validate_optional_section_annotation(
    *,
    parameters: Mapping[str, inspect.Parameter],
    type_label: TypeLabel,
) -> None:
    section_parameters = [p for n, p in parameters.items() if n.startswith("section")]

    def validate_with(pred: Callable[[inspect.Parameter], bool], msg: str) -> None:
        if not all(p.annotation == p.empty or pred(p) for p in section_parameters):
            raise TypeError(f"Wrong type annotation: {msg}")

    if type_label == "cluster_check":
        validate_with(
            _is_valid_cluster_section_parameter,
            "cluster sections must be of type `Mapping[str, <NodeSection> | None]`",
        )
    elif len(section_parameters) > 1:
        validate_with(
            lambda p: _is_optional(p.annotation),
            "multiple sections must be of type `<NodeSection> | None`",
        )


def validate_ruleset_type(ruleset_type: RuleSetType) -> None:
    if not isinstance(ruleset_type, RuleSetType):
        allowed = ", ".join(str(c) for c in RuleSetType)
        raise ValueError(f"invalid ruleset type {ruleset_type!r}. Allowed are {allowed}")


def validate_default_parameters(
    params_type: Literal["check", "discovery", "host_label", "inventory"],
    ruleset_name: str | None,
    default_parameters: Mapping[str, object] | None,
) -> None:
    if default_parameters is None:
        if ruleset_name is None:
            return
        raise TypeError(f"missing default {params_type} parameters for ruleset {ruleset_name}")

    if not isinstance(default_parameters, dict):
        raise TypeError(f"default {params_type} parameters must be dict")

    if ruleset_name is None and params_type != "check":
        raise TypeError(f"missing ruleset name for default {params_type} parameters")


def filter_relevant_raw_sections(
    *,
    consumers: Iterable[CheckPlugin | InventoryPlugin],
    sections: Iterable[SectionPlugin],
) -> Mapping[SectionName, SectionPlugin]:
    """Return the raw sections potentially relevant for the given check or inventory plugins"""
    parsed_section_names = {
        section_name for plugin in consumers for section_name in plugin.sections
    }

    return {
        section.name: section
        for section in sections
        if section.parsed_section_name in parsed_section_names
    }


def sections_needing_redetection(
    sections: Iterable[SNMPSectionPlugin],
) -> set[SectionName]:
    """Return the names of sections that need to be redetected

    Sections that are not the only producers of their parsed
    sections need to be re-detected during checking.
    """
    sections_by_parsed_name = defaultdict(set)
    for section in sections:
        sections_by_parsed_name[section.parsed_section_name].add(section.name)
    return {
        section_name
        for section_names in sections_by_parsed_name.values()
        if len(section_names) > 1
        for section_name in section_names
    }


def extract_known_discovery_rulesets(plugins: AgentBasedPlugins) -> Collection[RuleSetName]:
    return {
        r
        for r in (
            *(p.discovery_ruleset_name for p in plugins.check_plugins.values()),
            *(p.host_label_ruleset_name for p in plugins.agent_sections.values()),
            *(p.host_label_ruleset_name for p in plugins.snmp_sections.values()),
        )
        if r is not None
    }
