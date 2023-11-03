#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import enum
from collections.abc import Mapping, MutableMapping
from dataclasses import dataclass
from functools import partial
from typing import Any, assert_never, Callable, TypeVar

from cmk.gui import valuespec as legacy_valuespecs
from cmk.gui import wato
from cmk.gui.exceptions import MKUserError
from cmk.gui.watolib import rulespecs as legacy_rulespecs
from cmk.gui.watolib.rulespecs import CheckParameterRulespecWithItem

from cmk.rulesets import v1 as ruleset_api_v1
from cmk.rulesets.v1 import RuleSpecSubGroup

_RULESPEC_SUB_GROUP_LEGACY_MAPPING = {
    RuleSpecSubGroup.CHECK_PARAMETERS_APPLICATIONS: wato.RulespecGroupCheckParametersApplications,
    RuleSpecSubGroup.CHECK_PARAMETERS_VIRTUALIZATION: wato.RulespecGroupCheckParametersVirtualization,
}


def _localize_optional(
    to_localize: ruleset_api_v1.Localizable | None, localizer: Callable[[str], str]
) -> str | None:
    return None if to_localize is None else to_localize.localize(localizer)


def convert_to_legacy_rulespec(
    to_convert: ruleset_api_v1.RuleSpec, localizer: Callable[[str], str]
) -> legacy_rulespecs.Rulespec:
    if isinstance(to_convert, ruleset_api_v1.CheckParameterRuleSpecWithItem):
        return CheckParameterRulespecWithItem(
            check_group_name=to_convert.name,
            title=None
            if to_convert.title is None
            else partial(to_convert.title.localize, localizer),
            group=_convert_to_legacy_rulespec_group(to_convert.group),
            item_spec=partial(_convert_to_legacy_item_spec, to_convert.item, localizer),
            match_type="dict",
            parameter_valuespec=partial(
                _convert_to_legacy_valuespec, to_convert.value_spec(), localizer
            ),
            create_manual_check=False,  # TODO create EnforcedService explicitly and convert
        )

    raise NotImplementedError(to_convert)


def _convert_to_legacy_rulespec_group(
    to_convert: ruleset_api_v1.RuleSpecCustomSubGroup | ruleset_api_v1.RuleSpecSubGroup,
) -> type[legacy_rulespecs.RulespecSubGroup]:
    if isinstance(to_convert, ruleset_api_v1.RuleSpecSubGroup):
        return _RULESPEC_SUB_GROUP_LEGACY_MAPPING[to_convert]
    raise ValueError(to_convert)


@dataclass(frozen=True)
class _LegacyDictKeyProps:
    required: list[str]
    ignored: list[str]
    show_more: list[str]


def _extract_key_props(
    dic_elements: Mapping[str, ruleset_api_v1.DictElement]
) -> _LegacyDictKeyProps:
    key_props = _LegacyDictKeyProps(required=[], ignored=[], show_more=[])

    for key, dic_elem in dic_elements.items():
        if dic_elem.required:
            key_props.required.append(key)
        if dic_elem.ignored:
            key_props.ignored.append(key)
        if dic_elem.show_more:
            key_props.show_more.append(key)

    return key_props


def _convert_to_legacy_valuespec(
    to_convert: ruleset_api_v1.ValueSpec, localizer: Callable[[str], str]
) -> legacy_valuespecs.ValueSpec:
    if isinstance(to_convert, ruleset_api_v1.Integer):
        return _convert_to_legacy_integer(to_convert, localizer)

    if isinstance(to_convert, ruleset_api_v1.Percentage):
        return _convert_to_legacy_percentage(to_convert, localizer)

    if isinstance(to_convert, ruleset_api_v1.Dictionary):
        elements = [
            (key, _convert_to_legacy_valuespec(elem.spec, localizer))
            for key, elem in to_convert.elements.items()
        ]

        legacy_key_props = _extract_key_props(to_convert.elements)

        return legacy_valuespecs.Dictionary(
            elements=elements,
            title=_localize_optional(to_convert.title, localizer),
            help=_localize_optional(to_convert.help_text, localizer),
            empty_text=_localize_optional(to_convert.no_elements_text, localizer),
            required_keys=legacy_key_props.required,
            ignored_keys=legacy_key_props.ignored,
            show_more_keys=legacy_key_props.show_more,
            validate=_convert_to_legacy_validation(to_convert.custom_validate, localizer)
            if to_convert.custom_validate is not None
            else None,
        )
    if isinstance(to_convert, ruleset_api_v1.TextInput):
        return _convert_to_legacy_text_input(to_convert, localizer)

    if isinstance(to_convert, ruleset_api_v1.DropdownChoice):
        return _convert_to_legacy_dropdown_choice(to_convert, localizer)

    if isinstance(to_convert, ruleset_api_v1.MonitoringState):
        return _convert_to_legacy_monitoring_state(to_convert, localizer)

    raise NotImplementedError(to_convert)


def _convert_to_legacy_integer(
    to_convert: ruleset_api_v1.Integer, localizer: Callable[[str], str]
) -> legacy_valuespecs.Integer:
    converted_kwargs: MutableMapping[str, Any] = {
        "title": _localize_optional(to_convert.title, localizer),
        "help": _localize_optional(to_convert.help_text, localizer),
        "label": _localize_optional(to_convert.label, localizer),
    }
    converted_kwargs["unit"] = ""
    if to_convert.unit is not None:
        converted_kwargs["unit"] = to_convert.unit.localize(localizer)

    if to_convert.default_value is not None:
        converted_kwargs["default_value"] = to_convert.default_value

    if to_convert.custom_validate is not None:
        converted_kwargs["validate"] = _convert_to_legacy_validation(
            to_convert.custom_validate, localizer
        )

    if to_convert.custom_validate is not None:
        converted_kwargs["validate"] = _convert_to_legacy_validation(
            to_convert.custom_validate, localizer
        )

    return legacy_valuespecs.Integer(**converted_kwargs)


def _convert_to_legacy_percentage(
    to_convert: ruleset_api_v1.Percentage, localizer: Callable[[str], str]
) -> legacy_valuespecs.Percentage:
    converted_kwargs: MutableMapping[str, Any] = {
        "title": _localize_optional(to_convert.title, localizer),
        "help": _localize_optional(to_convert.help_text, localizer),
        "label": _localize_optional(to_convert.label, localizer),
    }

    if to_convert.display_precision is not None:
        converted_kwargs["display_format"] = f"%.{to_convert.display_precision}f"

    if to_convert.default_value is not None:
        converted_kwargs["default_value"] = to_convert.default_value

    if to_convert.custom_validate is not None:
        converted_kwargs["validate"] = _convert_to_legacy_validation(
            to_convert.custom_validate, localizer
        )

    return legacy_valuespecs.Percentage(**converted_kwargs)


def _convert_to_legacy_monitoring_state(
    to_convert: ruleset_api_v1.MonitoringState, localizer: Callable[[str], str]
) -> legacy_valuespecs.DropdownChoice:
    converted_kwargs: MutableMapping[str, Any] = {
        "title": _localize_optional(to_convert.title, localizer),
        "label": _localize_optional(to_convert.label, localizer),
        "help": _localize_optional(to_convert.help_text, localizer),
    }
    if to_convert.default_value is not None:
        converted_kwargs["default_value"] = (
            to_convert.default_value.value
            if isinstance(to_convert.default_value, enum.Enum)
            else to_convert.default_value
        )
    return legacy_valuespecs.MonitoringState(**converted_kwargs)


def _convert_to_legacy_dropdown_choice(
    to_convert: ruleset_api_v1.DropdownChoice, localizer: Callable[[str], str]
) -> legacy_valuespecs.DropdownChoice:
    choices = [
        (
            element.choice.value if isinstance(element.choice, enum.Enum) else element.choice,
            element.display.localize(localizer),
        )
        for element in to_convert.elements
    ]
    converted_kwargs: MutableMapping[str, Any] = {
        "title": _localize_optional(to_convert.title, localizer),
        "label": _localize_optional(to_convert.label, localizer),
        "help": _localize_optional(to_convert.help_text, localizer),
        "empty_text": _localize_optional(to_convert.no_elements_text, localizer),
        "read_only": to_convert.frozen,
    }
    if to_convert.invalid_element_validation is not None:
        match to_convert.invalid_element_validation.mode:
            case ruleset_api_v1.InvalidElementMode.COMPLAIN:
                converted_kwargs["invalid_choice"] = "complain"
            case ruleset_api_v1.InvalidElementMode.KEEP:
                converted_kwargs["invalid_choice"] = None
            case _:
                assert_never(to_convert.invalid_element_validation.mode)

        converted_kwargs["invalid_choice_title"] = _localize_optional(
            to_convert.invalid_element_validation.display, localizer
        )
        converted_kwargs["invalid_choice_error"] = _localize_optional(
            to_convert.invalid_element_validation.error_msg, localizer
        )
    if to_convert.deprecated_elements is not None:
        converted_kwargs["deprecated_choices"] = to_convert.deprecated_elements
    if to_convert.default_element is not None:
        converted_kwargs["default_value"] = (
            to_convert.default_element.value
            if isinstance(to_convert.default_element, enum.Enum)
            else to_convert.default_element
        )
    if to_convert.custom_validate is not None:
        converted_kwargs["validate"] = _convert_to_legacy_validation(
            to_convert.custom_validate, localizer
        )

    return legacy_valuespecs.DropdownChoice(choices, **converted_kwargs)


def _convert_to_legacy_text_input(
    to_convert: ruleset_api_v1.TextInput, localizer: Callable[[str], str]
) -> legacy_valuespecs.TextInput:
    converted_kwargs: MutableMapping[str, Any] = {
        "title": _localize_optional(to_convert.title, localizer),
        "label": _localize_optional(to_convert.label, localizer),
        "help": _localize_optional(to_convert.help_text, localizer),
    }

    if to_convert.input_hint is not None:
        converted_kwargs["placeholder"] = to_convert.input_hint

    if to_convert.default_value is not None:
        converted_kwargs["default_value"] = to_convert.default_value

    if to_convert.custom_validate is not None:
        converted_kwargs["validate"] = _convert_to_legacy_validation(
            to_convert.custom_validate, localizer
        )

    return legacy_valuespecs.TextInput(**converted_kwargs)


def _convert_to_legacy_item_spec(
    to_convert: ruleset_api_v1.ItemSpec, localizer: Callable[[str], str]
) -> legacy_valuespecs.TextInput | legacy_valuespecs.DropdownChoice:
    if isinstance(to_convert, ruleset_api_v1.TextInput):
        return _convert_to_legacy_text_input(to_convert, localizer)
    if isinstance(to_convert, ruleset_api_v1.DropdownChoice):
        return _convert_to_legacy_dropdown_choice(to_convert, localizer)

    raise ValueError(to_convert)


_ValidateFuncType = TypeVar("_ValidateFuncType")


def _convert_to_legacy_validation(
    v1_validate_func: Callable[[_ValidateFuncType], object],
    localizer: Callable[[str], str],
) -> Callable[[_ValidateFuncType, str], None]:
    def wrapper(value: _ValidateFuncType, var_prefix: str) -> None:
        try:
            v1_validate_func(value)
        except ruleset_api_v1.ValidationError as e:
            raise MKUserError(var_prefix, e.message.localize(localizer))

    return wrapper
