#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# pylint: disable=protected-access
import inspect
import sys
from collections.abc import Callable, Mapping, Sequence
from typing import Final, get_args, Literal, NoReturn, Union

from cmk.utils.check_utils import ParametersTypeAlias
from cmk.utils.rulesets import RuleSetName

from cmk.checkengine.checking import CheckPluginName
from cmk.checkengine.inventory import InventoryPluginName
from cmk.checkengine.sectionparser import ParsedSectionName

from cmk.base.api.agent_based.plugin_classes import CheckPlugin

from cmk.agent_based.v1.register import RuleSetType
from cmk.ccc.version import Edition
from cmk.discover_plugins import PluginLocation

TypeLabel = Literal["check", "cluster_check", "discovery", "host_label", "inventory"]

ITEM_VARIABLE: Final = "%s"

_ALLOWED_EDITION_FOLDERS: Final = {e.short for e in Edition}


def get_validated_plugin_location() -> PluginLocation:
    """Find out which module registered the plug-in and make sure its in the right place"""
    # We used this before, but it was a performance killer. The method below is a lot faster.
    # calling_from = inspect.stack()[2].filename
    full_module_name = str(sys._getframe(2).f_globals["__name__"])

    match full_module_name.split("."):
        case ("cmk", "base", "plugins", "agent_based", _module):
            return PluginLocation(full_module_name)
        case (
            "cmk",
            "base",
            "plugins",
            "agent_based",
            edition,
            _module,
        ) if edition in _ALLOWED_EDITION_FOLDERS:
            return PluginLocation(full_module_name)

    raise ImportError(f"do not register from {full_module_name!r}")


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
    default_params: ParametersTypeAlias | None,
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


def _value_type(annotation: inspect.Parameter) -> bytes:
    return get_args(annotation)[1]


def validate_ruleset_type(ruleset_type: RuleSetType) -> None:
    if not isinstance(ruleset_type, RuleSetType):
        allowed = ", ".join(str(c) for c in RuleSetType)
        raise ValueError(f"invalid ruleset type {ruleset_type!r}. Allowed are {allowed}")


def validate_default_parameters(
    params_type: Literal["check", "discovery", "host_label", "inventory"],
    ruleset_name: str | None,
    default_parameters: ParametersTypeAlias | None,
) -> None:
    if default_parameters is None:
        if ruleset_name is None:
            return
        raise TypeError(f"missing default {params_type} parameters for ruleset {ruleset_name}")

    if not isinstance(default_parameters, dict):
        raise TypeError(f"default {params_type} parameters must be dict")

    if ruleset_name is None and params_type != "check":
        raise TypeError(f"missing ruleset name for default {params_type} parameters")


def validate_check_ruleset_item_consistency(
    check_plugin: CheckPlugin,
    check_plugins_by_ruleset_name: dict[RuleSetName | None, list[CheckPlugin]],
) -> None:
    """Validate check plug-ins sharing a check_ruleset_name have either all or none an item.

    Mixed checkgroups lead to strange exceptions when processing the check parameters.
    So it is much better to catch these errors in a central place with a clear error message.
    """
    if check_plugin.check_ruleset_name is None:
        return

    present_check_plugins = check_plugins_by_ruleset_name[check_plugin.check_ruleset_name]
    if not present_check_plugins:
        return

    # Try to detect whether the check has an item. But this mechanism is not
    # 100% reliable since Checkmk appends an item to the service_description when "%s"
    # is not in the checks service_description template.
    # Maybe we need to define a new rule which enforces the developer to use the %s in
    # the service_description. At least for grouped checks.
    item_present = ITEM_VARIABLE in check_plugin.service_name
    item_expected = ITEM_VARIABLE in present_check_plugins[0].service_name

    if item_present is not item_expected:
        present_plugins = ", ".join(str(p.name) for p in present_check_plugins)
        raise ValueError(
            f"Check ruleset {check_plugin.check_ruleset_name} has checks with and without item! "
            "At least one of the checks in this group needs to be changed "
            f"(offending plug-in: {check_plugin.name}, present plug-ins: {present_plugins})."
        )
