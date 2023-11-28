#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import enum
from collections.abc import Mapping, MutableMapping
from dataclasses import dataclass
from functools import partial
from typing import Any, assert_never, Callable, TypeVar

from cmk.utils.version import Edition

from cmk.gui import valuespec as legacy_valuespecs
from cmk.gui import wato
from cmk.gui.exceptions import MKUserError
from cmk.gui.utils.rule_specs.loader import RuleSpec as APIV1RuleSpec
from cmk.gui.watolib import rulespec_groups as legacy_rulespec_groups
from cmk.gui.watolib import rulespecs as legacy_rulespecs
from cmk.gui.watolib.rulespecs import (
    CheckParameterRulespecWithItem,
    CheckParameterRulespecWithoutItem,
    ManualCheckParameterRulespec,
    rulespec_group_registry,
)

from cmk.rulesets import v1 as ruleset_api_v1


def _localize_optional(
    to_localize: ruleset_api_v1.Localizable | None, localizer: Callable[[str], str]
) -> str | None:
    return None if to_localize is None else to_localize.localize(localizer)


def convert_to_legacy_rulespec(
    to_convert: APIV1RuleSpec, edition_only: Edition, localizer: Callable[[str], str]
) -> legacy_rulespecs.Rulespec:
    match to_convert:
        case ruleset_api_v1.CheckParameterRuleSpecWithItem():
            return _convert_to_legacy_check_parameter_with_item_rulespec(
                to_convert, edition_only, localizer
            )
        case ruleset_api_v1.CheckParameterRuleSpecWithoutItem():
            return _convert_to_legacy_check_parameter_without_item_rulespec(
                to_convert, edition_only, localizer
            )
        case ruleset_api_v1.EnforcedServiceRuleSpecWithItem():
            item_spec = partial(_convert_to_legacy_item_spec, to_convert.item_form, localizer)
            return _convert_to_legacy_manual_check_parameter_rulespec(
                to_convert, edition_only, localizer, item_spec
            )
        case ruleset_api_v1.EnforcedServiceRuleSpecWithoutItem():
            return _convert_to_legacy_manual_check_parameter_rulespec(
                to_convert, edition_only, localizer
            )
        case ruleset_api_v1.HostRuleSpec():
            return _convert_to_legacy_host_rule_spec_rulespec(to_convert, localizer)
        case ruleset_api_v1.ServiceRuleSpec() | ruleset_api_v1.InventoryParameterRuleSpec() | ruleset_api_v1.ActiveChecksRuleSpec() | ruleset_api_v1.AgentConfigRuleSpec() | ruleset_api_v1.SpecialAgentRuleSpec() | ruleset_api_v1.ExtraHostConfRuleSpec() | ruleset_api_v1.ExtraServiceConfRuleSpec():
            raise NotImplementedError(to_convert)
        case other:
            assert_never(other)


def _convert_to_legacy_check_parameter_with_item_rulespec(
    to_convert: ruleset_api_v1.CheckParameterRuleSpecWithItem,
    edition_only: Edition,
    localizer: Callable[[str], str],
) -> CheckParameterRulespecWithItem:
    return CheckParameterRulespecWithItem(
        check_group_name=to_convert.name,
        title=None if to_convert.title is None else partial(to_convert.title.localize, localizer),
        group=_convert_to_legacy_rulespec_group(
            to_convert.functionality, to_convert.topic, localizer
        ),
        item_spec=partial(_convert_to_legacy_item_spec, to_convert.item_form, localizer),
        match_type="dict",
        parameter_valuespec=partial(
            _convert_to_legacy_valuespec, to_convert.parameter_form(), localizer
        ),
        is_deprecated=to_convert.is_deprecated,
        create_manual_check=False,
        # weird field since the CME, as well as the CSE is based on a CCE, but we currently only
        # want to mark rulespecs that are available in both the CCE and CME as such
        is_cloud_and_managed_edition_only=edition_only is Edition.CCE,
    )


def _convert_to_legacy_check_parameter_without_item_rulespec(
    to_convert: ruleset_api_v1.CheckParameterRuleSpecWithoutItem,
    edition_only: Edition,
    localizer: Callable[[str], str],
) -> CheckParameterRulespecWithoutItem:
    return CheckParameterRulespecWithoutItem(
        check_group_name=to_convert.name,
        title=partial(to_convert.title.localize, localizer),
        group=_convert_to_legacy_rulespec_group(
            to_convert.functionality, to_convert.topic, localizer
        ),
        match_type="dict",
        parameter_valuespec=partial(
            _convert_to_legacy_valuespec, to_convert.parameter_form(), localizer
        ),
        create_manual_check=False,
        is_cloud_and_managed_edition_only=edition_only is Edition.CCE,
    )


def _convert_to_legacy_manual_check_parameter_rulespec(
    to_convert: ruleset_api_v1.EnforcedServiceRuleSpecWithItem
    | ruleset_api_v1.EnforcedServiceRuleSpecWithoutItem,
    edition_only: Edition,
    localizer: Callable[[str], str],
    item_spec: Callable[[], legacy_valuespecs.ValueSpec] | None = None,
) -> ManualCheckParameterRulespec:
    return ManualCheckParameterRulespec(
        group=_convert_to_legacy_rulespec_group(
            to_convert.functionality, to_convert.topic, localizer
        ),
        check_group_name=to_convert.name,
        parameter_valuespec=partial(
            _convert_to_legacy_valuespec, to_convert.parameter_form(), localizer
        )
        if to_convert.parameter_form is not None
        else None,
        title=None if to_convert.title is None else partial(to_convert.title.localize, localizer),
        is_deprecated=False,
        match_type="dict",
        item_spec=item_spec,
        is_cloud_and_managed_edition_only=edition_only is Edition.CCE,
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


def _convert_to_legacy_host_rule_spec_rulespec(
    to_convert: ruleset_api_v1.HostRuleSpec,
    localizer: Callable[[str], str],
) -> legacy_rulespecs.HostRulespec:
    return legacy_rulespecs.HostRulespec(
        group=_convert_to_legacy_rulespec_group(
            to_convert.functionality, to_convert.topic, localizer
        ),
        name=to_convert.name,
        valuespec=partial(_convert_to_legacy_valuespec, to_convert.parameter_form(), localizer),
        title=None if to_convert.title is None else partial(to_convert.title.localize, localizer),
        is_deprecated=to_convert.is_deprecated,
        match_type="dict" if to_convert.eval_type == ruleset_api_v1.RuleEvalType.MERGE else "all",
    )


def _get_builtin_legacy_main_group(
    functionality_to_convert: ruleset_api_v1.Functionality,
) -> type[legacy_rulespecs.RulespecGroup]:
    match functionality_to_convert:
        case ruleset_api_v1.Functionality.SERVICE_MONITORING_RULES:
            return wato._rulespec_groups.RulespecGroupMonitoringConfiguration  # type: ignore[attr-defined]
        case ruleset_api_v1.Functionality.ENFORCED_SERVICES:
            return legacy_rulespecs.RulespecGroupEnforcedServices
        case ruleset_api_v1.Functionality.SERVICE_DISCOVERY_RULES:
            return wato.RulespecGroupDiscoveryCheckParameters
    assert_never(functionality_to_convert)


def _get_builtin_legacy_sub_group_with_main_group(
    functionality_to_convert: ruleset_api_v1.Functionality,
    topic_to_convert: ruleset_api_v1.Topic,
) -> type[legacy_rulespecs.RulespecSubGroup]:
    match functionality_to_convert:
        case ruleset_api_v1.Functionality.SERVICE_MONITORING_RULES:
            match topic_to_convert:
                case ruleset_api_v1.Topic.APPLICATIONS:
                    return wato.RulespecGroupCheckParametersApplications
                case ruleset_api_v1.Topic.VIRTUALIZATION:
                    return wato.RulespecGroupCheckParametersVirtualization
                case ruleset_api_v1.Topic.OPERATING_SYSTEM:
                    return wato.RulespecGroupCheckParametersOperatingSystem
                case ruleset_api_v1.Topic.GENERAL:
                    raise NotImplementedError

            assert_never(topic_to_convert)

        case ruleset_api_v1.Functionality.ENFORCED_SERVICES:
            match topic_to_convert:
                case ruleset_api_v1.Topic.APPLICATIONS:
                    return legacy_rulespec_groups.RulespecGroupEnforcedServicesApplications
                case ruleset_api_v1.Topic.VIRTUALIZATION:
                    return legacy_rulespec_groups.RulespecGroupEnforcedServicesVirtualization
                case ruleset_api_v1.Topic.OPERATING_SYSTEM:
                    return legacy_rulespec_groups.RulespecGroupEnforcedServicesOperatingSystem
                case ruleset_api_v1.Topic.GENERAL:
                    raise NotImplementedError

            assert_never(topic_to_convert)

        case ruleset_api_v1.Functionality.SERVICE_DISCOVERY_RULES:
            match topic_to_convert:
                case ruleset_api_v1.Topic.GENERAL:
                    return wato.RulespecGroupCheckParametersDiscovery
                case ruleset_api_v1.Topic.APPLICATIONS | ruleset_api_v1.Topic.VIRTUALIZATION | ruleset_api_v1.Topic.OPERATING_SYSTEM:
                    raise NotImplementedError

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


def _extract_dictionary_key_props(
    dic_elements: Mapping[str, ruleset_api_v1.DictElement]
) -> _LegacyDictKeyProps:
    key_props = _LegacyDictKeyProps(required=[], hidden=[])

    for key, dic_elem in dic_elements.items():
        if dic_elem.required:
            key_props.required.append(key)
        if dic_elem.read_only:
            key_props.hidden.append(key)

    return key_props


def _convert_to_inner_legacy_valuespec(
    to_convert: ruleset_api_v1.FormSpec, localizer: Callable[[str], str]
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
                (key, _convert_to_legacy_valuespec(elem.parameter_form, localizer))
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

        case ruleset_api_v1.List():
            return _convert_to_legacy_list(to_convert, localizer)

        case ruleset_api_v1.FixedValue():
            return _convert_to_legacy_fixed_value(to_convert, localizer)

        case ruleset_api_v1.TimeSpan():
            return _convert_to_legacy_age(to_convert, localizer)

        case other:
            assert_never(other)


def _convert_to_legacy_valuespec(
    to_convert: ruleset_api_v1.FormSpec, localizer: Callable[[str], str]
) -> legacy_valuespecs.ValueSpec:
    if isinstance(to_convert.transform, ruleset_api_v1.Migrate):
        return legacy_valuespecs.Migrate(
            valuespec=_convert_to_inner_legacy_valuespec(to_convert, localizer),
            migrate=to_convert.transform.raw_to_form,
        )
    if isinstance(to_convert.transform, ruleset_api_v1.Transform):
        return legacy_valuespecs.Transform(
            valuespec=_convert_to_inner_legacy_valuespec(to_convert, localizer),
            to_valuespec=to_convert.transform.raw_to_form,
            from_valuespec=to_convert.transform.form_to_raw,
        )
    return _convert_to_inner_legacy_valuespec(to_convert, localizer)


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
            element.parameter_form.title.localize(localizer)
            if hasattr(element.parameter_form, "title") and element.parameter_form.title is not None
            else str(element.ident),
            _convert_to_legacy_valuespec(element.parameter_form, localizer),
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
    to_convert: ruleset_api_v1.ItemFormSpec, localizer: Callable[[str], str]
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


def _convert_to_legacy_list(
    to_convert: ruleset_api_v1.List, localizer: Callable[[str], str]
) -> legacy_valuespecs.ListOf | legacy_valuespecs.ListOfStrings:
    converted_kwargs: MutableMapping[str, Any] = {
        "valuespec": _convert_to_legacy_valuespec(to_convert.parameter_form, localizer),
        "title": _localize_optional(to_convert.title, localizer),
        "help": _localize_optional(to_convert.help_text, localizer),
        "movable": to_convert.order_editable,
    }

    if to_convert.custom_validate is not None:
        converted_kwargs["validate"] = _convert_to_legacy_validation(
            to_convert.custom_validate, localizer
        )

    if to_convert.prefill_value is not None:
        converted_kwargs["default_value"] = to_convert.prefill_value

    return legacy_valuespecs.ListOf(**converted_kwargs)


def _convert_to_legacy_fixed_value(
    to_convert: ruleset_api_v1.FixedValue, localizer: Callable[[str], str]
) -> legacy_valuespecs.FixedValue:
    return legacy_valuespecs.FixedValue(
        value=to_convert.value,
        totext=_localize_optional(to_convert.label, localizer)
        if to_convert.label is not None
        else "",
        title=_localize_optional(to_convert.title, localizer),
        help=_localize_optional(to_convert.help_text, localizer),
    )


def _convert_to_legacy_age(
    to_convert: ruleset_api_v1.TimeSpan, localizer: Callable[[str], str]
) -> legacy_valuespecs.Age:
    converted_kwargs: MutableMapping[str, Any] = {
        "title": _localize_optional(to_convert.title, localizer),
        "help": _localize_optional(to_convert.help_text, localizer),
        "label": _localize_optional(to_convert.label, localizer),
    }

    if to_convert.displayed_units is not None:
        converted_kwargs["display"] = [u.value for u in to_convert.displayed_units]

    if to_convert.prefill_value is not None:
        converted_kwargs["default_value"] = to_convert.prefill_value

    if to_convert.custom_validate is not None:
        converted_kwargs["validate"] = _convert_to_legacy_validation(
            to_convert.custom_validate, localizer
        )

    return legacy_valuespecs.Age(**converted_kwargs)
