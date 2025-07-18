#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from dataclasses import dataclass
from typing import Literal, Self

from cmk.gui.openapi.framework.model import api_field, ApiOmitted
from cmk.gui.utils.autocompleter_config import AutocompleterConfig, DynamicParamsCallbackName

from ..components import (
    Checkbox,
    CheckboxGroup,
    Dropdown,
    DualList,
    DynamicDropdown,
    FilterComponent,
    Hidden,
    HorizontalGroup,
    LabelGroupFilterComponent,
    RadioButton,
    Slider,
    StaticText,
    TagFilterComponent,
    TextInput,
)


@dataclass(kw_only=True, slots=True)
class AutocompleterConfigModel:
    ident: str = api_field(description="Identifier for the autocompleter.")
    params: dict[str, object] = api_field(description="Parameters for the autocompleter.")
    dynamic_params_callback_name: DynamicParamsCallbackName | ApiOmitted = api_field(
        description="Name of the callback for dynamic parameters.",
        default_factory=ApiOmitted,
    )

    @classmethod
    def from_autocompleter(cls, autocompleter: AutocompleterConfig) -> Self:
        return cls(
            ident=autocompleter.ident,
            params=dict(autocompleter.params),
            dynamic_params_callback_name=ApiOmitted.from_optional(
                autocompleter._dynamic_params_callback_name
            ),
        )


@dataclass(kw_only=True, slots=True)
class HorizontalGroupComponentModel:
    component_type: Literal["horizontal_group"] = api_field(
        description="A horizontal group of components."
    )
    components: list["FilterComponentModel"] = api_field(
        description="The components within this horizontal group."
    )


@dataclass(kw_only=True, slots=True)
class DropdownComponentModel:
    component_type: Literal["dropdown"] = api_field(description="A static dropdown component.")
    id: str = api_field(description="The identifier for the dropdown component.")
    choices: dict[str, str] = api_field(
        description="Choices for the dropdown, internal value -> display label."
    )
    default_value: str = api_field(description="The default value that should be selected.")
    label: str | ApiOmitted = api_field(
        description="The label for the dropdown.",
        default_factory=ApiOmitted,
    )


@dataclass(kw_only=True, slots=True)
class DynamicDropdownComponentModel:
    component_type: Literal["dynamic_dropdown"] = api_field(
        description="Filter on a dropdown, with options loaded dynamically."
    )
    id: str = api_field(description="The identifier for the dropdown component.")
    autocompleter: AutocompleterConfigModel = api_field(
        description="Configuration for the autocompleter."
    )
    has_validation: bool = api_field(
        description="Whether this dropdown has validation logic.",
    )


@dataclass(kw_only=True, slots=True)
class CheckboxComponentModel:
    component_type: Literal["checkbox"] = api_field(description="A checkbox component.")
    id: str = api_field(description="The identifier for the checkbox component.")
    label: str = api_field(description="The label for the checkbox.")
    default_value: bool = api_field(description="The default value of the checkbox.")


@dataclass(kw_only=True, slots=True)
class CheckboxGroupComponentModel:
    component_type: Literal["checkbox_group"] = api_field(description="A group of checkboxes.")
    choices: dict[str, str] = api_field(
        description="""All checkboxes, variable id -> display label.
The default value for each checkbox is `true`, unless some checkboxes are explicitly set in the
current filter values (in which case the default is `false`)."""
    )
    label: str | ApiOmitted = api_field(
        description="The label for the checkbox group.",
        default_factory=ApiOmitted,
    )


@dataclass(kw_only=True, slots=True)
class TextInputComponentModel:
    component_type: Literal["text_input"] = api_field(description="A text input component.")
    id: str = api_field(description="The identifier for the text input component.")
    label: str | ApiOmitted = api_field(
        description="The label for the text input.",
        default_factory=ApiOmitted,
    )
    suffix: str | ApiOmitted = api_field(
        description="An optional suffix to be placed after the input field, mostly for units.",
        default_factory=ApiOmitted,
    )


@dataclass(kw_only=True, slots=True)
class RadioButtonComponentModel:
    component_type: Literal["radio_button"] = api_field(description="A radio button component.")
    id: str = api_field(description="The identifier for the radio button component.")
    choices: dict[str, str] = api_field(
        description="Options for the radio buttons, internal value -> display label."
    )
    default_value: str = api_field(description="The default value that should be selected.")


@dataclass(kw_only=True, slots=True)
class SliderComponentModel:
    component_type: Literal["slider"] = api_field(description="A slider component.")
    id: str = api_field(description="The identifier for the slider component.")
    min_value: int = api_field(description="The minimum value of the slider.")
    max_value: int = api_field(description="The maximum value of the slider.")
    step: int = api_field(description="The step size for the slider.")
    default_value: int = api_field(description="The default value of the slider.")


@dataclass(kw_only=True, slots=True)
class StaticTextComponentModel:
    component_type: Literal["static_text"] = api_field(
        description="A static text component, not interactive."
    )
    text: str = api_field(description="The static text to be displayed.")


@dataclass(kw_only=True, slots=True)
class HiddenComponentModel:
    component_type: Literal["hidden"] = api_field(
        description="A hidden component, not rendered in the UI but used to set static values."
    )
    id: str = api_field(description="The identifier for the hidden component.")
    value: str = api_field(description="The static value for this component.")


@dataclass(kw_only=True, slots=True)
class DualListComponentModel:
    component_type: Literal["dual_list"] = api_field(
        description="A dual list component for selecting multiple items."
    )
    id: str = api_field(description="The identifier for the dual list component.")
    choices: dict[str, str] = api_field(
        description="Choices for the dual list, internal value -> display label."
    )


@dataclass(kw_only=True, slots=True)
class LabelGroupFilterComponentModel:
    component_type: Literal["label_group"] = api_field(
        description="A filter component for selecting label groups."
    )
    id: str = api_field(description="The identifier for the label group filter component.")
    object_type: Literal["host", "service"] = api_field(
        description="The type of object this label group filter is applied to.",
    )


@dataclass(kw_only=True, slots=True)
class TagFilterComponentModel:
    component_type: Literal["tag_filter"] = api_field(
        description="A filter component for selecting tags."
    )
    display_rows: int = api_field(
        description="Number of rows to display in the tag filter dropdown."
    )
    variable_prefix: str = api_field(description="Prefix for the variables used in the filter.")


type FilterComponentModel = (
    HorizontalGroupComponentModel
    | DropdownComponentModel
    | DynamicDropdownComponentModel
    | CheckboxComponentModel
    | CheckboxGroupComponentModel
    | TextInputComponentModel
    | RadioButtonComponentModel
    | SliderComponentModel
    | StaticTextComponentModel
    | HiddenComponentModel
    | DualListComponentModel
    | LabelGroupFilterComponentModel
    | TagFilterComponentModel
)


def filter_component_from_internal(component: FilterComponent) -> FilterComponentModel:
    if isinstance(component, HorizontalGroup):
        return HorizontalGroupComponentModel(
            component_type=component.component_type,
            components=[filter_component_from_internal(c) for c in component.components],
        )
    if isinstance(component, Dropdown):
        return DropdownComponentModel(
            component_type=component.component_type,
            id=component.id,
            choices=dict(component.choices),
            default_value=component.default_value,
            label=ApiOmitted.from_optional(component.label),
        )
    if isinstance(component, DynamicDropdown):
        return DynamicDropdownComponentModel(
            component_type=component.component_type,
            id=component.id,
            autocompleter=AutocompleterConfigModel.from_autocompleter(component.autocompleter),
            has_validation=component.has_validation,
        )
    if isinstance(component, Checkbox):
        return CheckboxComponentModel(
            component_type=component.component_type,
            id=component.id,
            label=component.label,
            default_value=component.default_value,
        )
    if isinstance(component, CheckboxGroup):
        return CheckboxGroupComponentModel(
            component_type=component.component_type,
            choices=dict(component.choices),
            label=ApiOmitted.from_optional(component.label),
        )
    if isinstance(component, TextInput):
        return TextInputComponentModel(
            component_type=component.component_type,
            id=component.id,
            label=ApiOmitted.from_optional(component.label),
            suffix=ApiOmitted.from_optional(component.suffix),
        )
    if isinstance(component, RadioButton):
        return RadioButtonComponentModel(
            component_type=component.component_type,
            id=component.id,
            choices=dict(component.choices),
            default_value=component.default_value,
        )
    if isinstance(component, Slider):
        return SliderComponentModel(
            component_type=component.component_type,
            id=component.id,
            min_value=component.min_value,
            max_value=component.max_value,
            step=component.step,
            default_value=component.default_value,
        )
    if isinstance(component, StaticText):
        return StaticTextComponentModel(
            component_type=component.component_type,
            text=component.text,
        )
    if isinstance(component, Hidden):
        return HiddenComponentModel(
            component_type=component.component_type,
            id=component.id,
            value=component.value,
        )
    if isinstance(component, DualList):
        return DualListComponentModel(
            component_type=component.component_type,
            id=component.id,
            choices=dict(component.choices),
        )
    if isinstance(component, LabelGroupFilterComponent):
        return LabelGroupFilterComponentModel(
            component_type=component.component_type,
            id=component.id,
            object_type=component.object_type,
        )
    if isinstance(component, TagFilterComponent):
        return TagFilterComponentModel(
            component_type=component.component_type,
            display_rows=component.display_rows,
            variable_prefix=component.variable_prefix,
        )

    raise ValueError("Unknown component type")
