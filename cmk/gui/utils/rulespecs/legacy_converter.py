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
from cmk.gui.utils.rulespecs.loader import RuleSpec as APIV1RuleSpec
from cmk.gui.watolib import rulespec_groups as legacy_rulespec_groups
from cmk.gui.watolib import rulespecs as legacy_rulespecs
from cmk.gui.watolib.rulespecs import (
    CheckParameterRulespecWithItem,
    ManualCheckParameterRulespec,
    rulespec_group_registry,
)

from cmk.rulesets import v1 as ruleset_api_v1


def _localize_optional(
    to_localize: ruleset_api_v1.Localizable | None, localizer: Callable[[str], str]
) -> str | None:
    return None if to_localize is None else to_localize.localize(localizer)


def convert_to_legacy_rulespec(
    to_convert: APIV1RuleSpec, localizer: Callable[[str], str]
) -> legacy_rulespecs.Rulespec:
    match to_convert:
        case ruleset_api_v1.CheckParameterRuleSpecWithItem():
            return _convert_to_legacy_check_parameter_with_item_rulespec(to_convert, localizer)
        case ruleset_api_v1.EnforcedServiceRuleSpecWithItem():
            item_spec = partial(_convert_to_legacy_item_spec, to_convert.item, localizer)
            return _convert_to_legacy_manual_check_parameter_rulespec(
                to_convert, localizer, item_spec
            )
        case ruleset_api_v1.EnforcedServiceRuleSpecWithoutItem():
            return _convert_to_legacy_manual_check_parameter_rulespec(to_convert, localizer)
        case ruleset_api_v1.CheckParameterRuleSpecWithoutItem() | ruleset_api_v1.HostRuleSpec() | ruleset_api_v1.ServiceRuleSpec() | ruleset_api_v1.InventoryParameterRuleSpec() | ruleset_api_v1.ActiveChecksRuleSpec() | ruleset_api_v1.AgentConfigRuleSpec() | ruleset_api_v1.SpecialAgentRuleSpec() | ruleset_api_v1.ExtraHostConfRuleSpec() | ruleset_api_v1.ExtraServiceConfRuleSpec():
            raise NotImplementedError(to_convert)
        case other:
            assert_never(other)


def _convert_to_legacy_check_parameter_with_item_rulespec(
    to_convert: ruleset_api_v1.CheckParameterRuleSpecWithItem, localizer: Callable[[str], str]
) -> CheckParameterRulespecWithItem:
    return CheckParameterRulespecWithItem(
        check_group_name=to_convert.name,
        title=None if to_convert.title is None else partial(to_convert.title.localize, localizer),
        group=_convert_to_legacy_rulespec_group(
            to_convert.functionality, to_convert.topic, localizer
        ),
        item_spec=partial(_convert_to_legacy_item_spec, to_convert.item, localizer),
        match_type="dict",
        parameter_valuespec=partial(
            _convert_to_legacy_valuespec, to_convert.value_spec(), localizer
        ),
        is_deprecated=to_convert.is_deprecated,
        create_manual_check=False,
    )


def _convert_to_legacy_manual_check_parameter_rulespec(
    to_convert: ruleset_api_v1.EnforcedServiceRuleSpecWithItem
    | ruleset_api_v1.EnforcedServiceRuleSpecWithoutItem,
    localizer: Callable[[str], str],
    item_spec: Callable[[], legacy_valuespecs.ValueSpec] | None = None,
) -> ManualCheckParameterRulespec:
    return ManualCheckParameterRulespec(
        group=_convert_to_legacy_rulespec_group(
            to_convert.functionality, to_convert.topic, localizer
        ),
        check_group_name=to_convert.name,
        parameter_valuespec=partial(
            _convert_to_legacy_valuespec, to_convert.value_spec(), localizer
        ),
        title=None if to_convert.title is None else partial(to_convert.title.localize, localizer),
        is_deprecated=False,
        match_type="dict",
        item_spec=item_spec,
    )


def _convert_to_legacy_rulespec_group(
    functionality_to_convert: ruleset_api_v1.Functionality | ruleset_api_v1.CustomFunctionality,
    topic_to_convert: ruleset_api_v1.Topic | ruleset_api_v1.CustomTopic,
    localizer: Callable[[str], str],
) -> type[legacy_rulespecs.RulespecBaseGroup]:
    if isinstance(functionality_to_convert, ruleset_api_v1.Functionality) and isinstance(
        topic_to_convert, ruleset_api_v1.Topic
    ):
        return _get_builtin_legacy_sub_group_with_main_group(
            functionality_to_convert, topic_to_convert
        )
    if isinstance(functionality_to_convert, ruleset_api_v1.Functionality) and isinstance(
        topic_to_convert, ruleset_api_v1.CustomTopic
    ):
        identifier = f"{hash(topic_to_convert.title.localize(lambda x: x))}"
        return _convert_to_custom_group(
            identifier,
            legacy_rulespecs.RulespecSubGroup,
            {
                "title": topic_to_convert.title.localize(localizer),
                "main_group": _get_builtin_legacy_main_group(functionality_to_convert),
                "sub_group_name": identifier,
            },
        )
    if isinstance(functionality_to_convert, ruleset_api_v1.CustomFunctionality):
        raise NotImplementedError

    raise ValueError((functionality_to_convert, topic_to_convert))


def _get_builtin_legacy_main_group(
    functionality_to_convert: ruleset_api_v1.Functionality,
) -> type[legacy_rulespecs.RulespecGroup]:
    match functionality_to_convert:
        case ruleset_api_v1.Functionality.MONITORING_CONFIGURATION:
            return wato._rulespec_groups.RulespecGroupMonitoringConfiguration  # type: ignore[attr-defined]
        case ruleset_api_v1.Functionality.ENFORCED_SERVICES:
            return legacy_rulespecs.RulespecGroupEnforcedServices
    assert_never(functionality_to_convert)


def _get_builtin_legacy_sub_group_with_main_group(
    functionality_to_convert: ruleset_api_v1.Functionality,
    topic_to_convert: ruleset_api_v1.Topic,
) -> type[legacy_rulespecs.RulespecSubGroup]:
    match functionality_to_convert:
        case ruleset_api_v1.Functionality.MONITORING_CONFIGURATION:
            match topic_to_convert:
                case ruleset_api_v1.Topic.APPLICATIONS:
                    return wato.RulespecGroupCheckParametersApplications
                case ruleset_api_v1.Topic.VIRTUALIZATION:
                    return wato.RulespecGroupCheckParametersVirtualization

            assert_never(topic_to_convert)

        case ruleset_api_v1.Functionality.ENFORCED_SERVICES:
            match topic_to_convert:
                case ruleset_api_v1.Topic.APPLICATIONS:
                    return legacy_rulespec_groups.RulespecGroupEnforcedServicesApplications
                case ruleset_api_v1.Topic.VIRTUALIZATION:
                    return legacy_rulespec_groups.RulespecGroupEnforcedServicesVirtualization

            assert_never(topic_to_convert)

    assert_never(functionality_to_convert)


def _convert_to_custom_group(
    identifier: str,
    base: type,
    args: dict[str, str | type[legacy_rulespecs.RulespecGroup]],
) -> type[legacy_rulespecs.RulespecBaseGroup]:
    if identifier in rulespec_group_registry:
        return rulespec_group_registry[identifier]

    group_class = type(identifier, (base,), args)
    rulespec_group_registry.register(group_class)
    return group_class


@dataclass(frozen=True)
class _LegacyDictKeyProps:
    required: list[str]
    hidden: list[str]
    show_more: list[str]


def _extract_dictionary_key_props(
    dic_elements: Mapping[str, ruleset_api_v1.DictElement]
) -> _LegacyDictKeyProps:
    key_props = _LegacyDictKeyProps(required=[], hidden=[], show_more=[])

    for key, dic_elem in dic_elements.items():
        if dic_elem.required:
            key_props.required.append(key)
        if dic_elem.read_only:
            key_props.hidden.append(key)
        if dic_elem.show_more:
            key_props.show_more.append(key)

    return key_props


def _convert_to_legacy_valuespec(
    to_convert: ruleset_api_v1.ValueSpec, localizer: Callable[[str], str]
) -> legacy_valuespecs.ValueSpec:
    match to_convert:
        case ruleset_api_v1.Integer():
            return _convert_to_legacy_integer(to_convert, localizer)

        case ruleset_api_v1.Percentage():
            return _convert_to_legacy_percentage(to_convert, localizer)

        case ruleset_api_v1.TextInput():
            return _convert_to_legacy_text_input(to_convert, localizer)

        case ruleset_api_v1.Tuple():
            return _convert_to_legacy_tuple(to_convert, localizer)

        case ruleset_api_v1.Dictionary():
            elements = [
                (key, _convert_to_legacy_valuespec(elem.value_spec, localizer))
                for key, elem in to_convert.elements.items()
            ]

            legacy_key_props = _extract_dictionary_key_props(to_convert.elements)

            return legacy_valuespecs.Dictionary(
                elements=elements,
                title=_localize_optional(to_convert.title, localizer),
                help=_localize_optional(to_convert.help_text, localizer),
                empty_text=_localize_optional(to_convert.no_elements_text, localizer),
                required_keys=legacy_key_props.required,
                ignored_keys=to_convert.deprecated_elements,
                hidden_keys=legacy_key_props.hidden,
                show_more_keys=legacy_key_props.show_more,
                validate=_convert_to_legacy_validation(to_convert.custom_validate, localizer)
                if to_convert.custom_validate is not None
                else None,
            )

        case ruleset_api_v1.DropdownChoice():
            return _convert_to_legacy_dropdown_choice(to_convert, localizer)

        case ruleset_api_v1.CascadingDropdown():
            return _convert_to_legacy_cascading_dropdown(to_convert, localizer)

        case ruleset_api_v1.MonitoringState():
            return _convert_to_legacy_monitoring_state(to_convert, localizer)

        case other:
            assert_never(other)


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

    if to_convert.prefill_value is not None:
        converted_kwargs["default_value"] = to_convert.prefill_value

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

    if to_convert.prefill_value is not None:
        converted_kwargs["default_value"] = to_convert.prefill_value

    if to_convert.custom_validate is not None:
        converted_kwargs["validate"] = _convert_to_legacy_validation(
            to_convert.custom_validate, localizer
        )

    return legacy_valuespecs.Percentage(**converted_kwargs)


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

    if to_convert.prefill_value is not None:
        converted_kwargs["default_value"] = to_convert.prefill_value

    if to_convert.custom_validate is not None:
        converted_kwargs["validate"] = _convert_to_legacy_validation(
            to_convert.custom_validate, localizer
        )

    return legacy_valuespecs.TextInput(**converted_kwargs)


def _convert_to_legacy_tuple(
    to_convert: ruleset_api_v1.Tuple, localizer: Callable[[str], str]
) -> legacy_valuespecs.Tuple:
    legacy_elements = [
        _convert_to_legacy_valuespec(element, localizer) for element in to_convert.elements
    ]
    converted_kwargs: MutableMapping[str, Any] = {
        "title": _localize_optional(to_convert.title, localizer),
        "help": _localize_optional(to_convert.help_text, localizer),
    }

    if to_convert.custom_validate is not None:
        converted_kwargs["validate"] = _convert_to_legacy_validation(
            to_convert.custom_validate, localizer
        )
    return legacy_valuespecs.Tuple(elements=legacy_elements, **converted_kwargs)


def _convert_to_legacy_monitoring_state(
    to_convert: ruleset_api_v1.MonitoringState, localizer: Callable[[str], str]
) -> legacy_valuespecs.DropdownChoice:
    converted_kwargs: MutableMapping[str, Any] = {
        "title": _localize_optional(to_convert.title, localizer),
        "label": _localize_optional(to_convert.label, localizer),
        "help": _localize_optional(to_convert.help_text, localizer),
    }
    if to_convert.prefill_value is not None:
        converted_kwargs["default_value"] = (
            to_convert.prefill_value.value
            if isinstance(to_convert.prefill_value, enum.Enum)
            else to_convert.prefill_value
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

    if to_convert.prefill_selection is not None:
        converted_kwargs["default_value"] = (
            to_convert.prefill_selection.value
            if isinstance(to_convert.prefill_selection, enum.Enum)
            else to_convert.prefill_selection
        )

    if to_convert.custom_validate is not None:
        converted_kwargs["validate"] = _convert_to_legacy_validation(
            to_convert.custom_validate, localizer
        )

    return legacy_valuespecs.DropdownChoice(choices, **converted_kwargs)


def _convert_to_legacy_cascading_dropdown(
    to_convert: ruleset_api_v1.CascadingDropdown, localizer: Callable[[str], str]
) -> legacy_valuespecs.CascadingDropdown:
    legacy_choices = [
        (
            element.ident.value if isinstance(element.ident, enum.StrEnum) else element.ident,
            element.value_spec.title.localize(localizer)
            if hasattr(element.value_spec, "title") and element.value_spec.title is not None
            else str(element.ident),
            _convert_to_legacy_valuespec(element.value_spec, localizer),
        )
        for element in to_convert.elements
    ]

    converted_kwargs: MutableMapping[str, Any] = {
        "title": _localize_optional(to_convert.title, localizer),
        "label": _localize_optional(to_convert.label, localizer),
        "help": _localize_optional(to_convert.help_text, localizer),
    }
    if to_convert.prefill_selection is None:
        converted_kwargs["no_preselect_title"] = ""
    else:
        converted_kwargs["default_value"] = to_convert.prefill_selection
    return legacy_valuespecs.CascadingDropdown(choices=legacy_choices, **converted_kwargs)


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
