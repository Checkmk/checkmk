#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import enum
import inspect
import pathlib
import sys
from typing import (
    Callable,
    Dict,
    get_args,
    List,
    Literal,
    Mapping,
    NoReturn,
    Optional,
    Sequence,
    Union,
)

from cmk.utils.paths import agent_based_plugins_dir
from cmk.utils.type_defs import CheckPluginName, InventoryPluginName, ParsedSectionName, RuleSetName

from cmk.base.api.agent_based.checking_classes import CheckPlugin
from cmk.base.api.agent_based.type_defs import ParametersTypeAlias

TypeLabel = Literal["check", "cluster_check", "discovery", "host_label", "inventory"]

ITEM_VARIABLE = "%s"

_NONE_TYPE = type(None)


def get_validated_plugin_module_name() -> Optional[str]:
    """Find out which module registered the plugin and make sure its in the right place"""
    # We used this before, but it was a performance killer. The method below is a lot faster.
    # calling_from = inspect.stack()[2].filename
    frame = sys._getframe(2)
    if not frame:
        return None
    calling_from = frame.f_code.co_filename

    path = pathlib.Path(calling_from)
    if not path.parent.parts[-3:] == agent_based_plugins_dir.parts[-3:]:
        raise ImportError("do not register from %r" % path)

    return path.stem


def create_subscribed_sections(
    sections: Optional[List[str]],
    plugin_name: Union[InventoryPluginName, CheckPluginName],
) -> List[ParsedSectionName]:
    if sections is None:
        return [ParsedSectionName(str(plugin_name))]
    if not isinstance(sections, list):
        raise TypeError("'sections' must be a list of str, got %r" % (sections,))
    if not sections:
        raise ValueError("'sections' must not be empty")
    return [ParsedSectionName(n) for n in sections]


def validate_function_arguments(
    *,
    type_label: TypeLabel,
    function: Callable,
    has_item: bool,
    default_params: Optional[ParametersTypeAlias],
    sections: List[ParsedSectionName],
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
        expected_params.extend("section_%s" % s for s in sections)

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
    # We know we must raise. Dispatch for a better error message:

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


def _validate_optional_section_annotation(
    *,
    parameters: Mapping[str, inspect.Parameter],
    type_label: TypeLabel,
) -> None:
    """Validate that the section annotation is correct, if present.

    We know almost nothing about the type of the section argument(s). Check the few things we know:

        * If we have more than one section, all of them must be `Optional`.

    """
    section_args = [p for n, p in parameters.items() if n.startswith("section")]
    if all(p.annotation == p.empty for p in section_args):
        return  # no typing used in plugin

    if type_label == "cluster_check":
        desired = " cluster sections must be of type `Mapping[str, Optional[<NodeSection>]]`"
        if not all(
            str(p.annotation).startswith("typing.Mapping[str, ")
            and _NONE_TYPE in get_args(get_args(p.annotation)[1])
            for p in section_args
        ):
            raise TypeError(f"Wrong type annotation: {desired}")
        return

    if len(section_args) <= 1:
        return  # we know nothing in this case

    if any(_NONE_TYPE not in get_args(p.annotation) for p in section_args):
        raise TypeError("Wrong type annotation: multiple sections must be `Optional`")

    return


def _value_type(annotation: inspect.Parameter) -> bytes:
    return get_args(annotation)[1]


class RuleSetType(enum.Enum):
    """Indicate the type of the rule set

    Discovery and host label functions may either use all rules of a rule set matching
    the current host, or the merged rules.
    """

    MERGED = enum.auto()
    ALL = enum.auto()


def validate_ruleset_type(ruleset_type: RuleSetType) -> None:
    if not isinstance(ruleset_type, RuleSetType):
        allowed = ", ".join(str(c) for c in RuleSetType)
        raise ValueError(f"invalid ruleset type {ruleset_type!r}. Allowed are {allowed}")


def validate_default_parameters(
    params_type: Literal["check", "discovery", "host_label", "inventory"],
    ruleset_name: Optional[str],
    default_parameters: Optional[ParametersTypeAlias],
) -> None:
    if default_parameters is None:
        if ruleset_name is None:
            return
        raise TypeError(
            "missing default %s parameters for ruleset %s" % (params_type, ruleset_name)
        )

    if not isinstance(default_parameters, dict):
        raise TypeError("default %s parameters must be dict" % (params_type,))

    if ruleset_name is None and params_type != "check":
        raise TypeError("missing ruleset name for default %s parameters" % (params_type))


def validate_check_ruleset_item_consistency(
    check_plugin: CheckPlugin,
    check_plugins_by_ruleset_name: Dict[Optional[RuleSetName], List[CheckPlugin]],
) -> None:
    """Validate check plugins sharing a check_ruleset_name have either all or none an item.

    Mixed checkgroups lead to strange exceptions when processing the check parameters.
    So it is much better to catch these errors in a central place with a clear error message.
    """
    if check_plugin.check_ruleset_name is None:
        return

    present_check_plugins = check_plugins_by_ruleset_name[check_plugin.check_ruleset_name]
    if not present_check_plugins:
        return

    # Trying to detect whether or not the check has an item. But this mechanism is not
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
            f"(offending plugin: {check_plugin.name}, present_plugins: {present_plugins})."
        )
