#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Literal

from cmk.gui.htmllib.html import html
from cmk.gui.query_filters import AllLabelGroupsQuery
from cmk.gui.type_defs import ChoiceMapping, Choices, FilterHTTPVariables
from cmk.gui.utils.autocompleter_config import AutocompleterConfig
from cmk.gui.valuespec import DualListChoice, LabelGroups


@dataclass(kw_only=True, slots=True)
class BaseComponent(ABC):
    @property
    @abstractmethod
    def component_type(self) -> str:
        pass

    @abstractmethod
    def render_html(self, filter_id: str, current_values: FilterHTTPVariables) -> None:
        pass


@dataclass(kw_only=True, slots=True)
class HorizontalGroup(BaseComponent):
    component_type: Literal["horizontal_group"] = "horizontal_group"
    components: list["FilterComponent"]

    def __post_init__(self) -> None:
        if not self.components:
            raise ValueError("Must contain at least one component")

    def render_html(self, filter_id: str, current_values: FilterHTTPVariables) -> None:
        self.components[0].render_html(filter_id, current_values)
        for component in self.components[1:]:
            html.open_nobr()
            component.render_html(filter_id, current_values)
            html.close_nobr()


@dataclass(kw_only=True, slots=True)
class Dropdown(BaseComponent):
    component_type: Literal["dropdown"] = "dropdown"
    id: str
    choices: ChoiceMapping
    """Choices for the dropdown, internal value -> display label"""
    default_value: str = ""
    label: str | None = None

    def __post_init__(self) -> None:
        if not self.choices:
            raise ValueError("Choices must not be empty")
        if self.default_value not in self.choices:
            raise ValueError(
                f"Default value {self.default_value!r} is not in the choices: {self.choices!r}"
            )

    def render_html(self, filter_id: str, current_values: FilterHTTPVariables) -> None:
        if self.label:
            html.write_text_permissive(self.label)
            html.open_nobr()
        html.dropdown(
            self.id,
            self.choices.items(),
            deflt=current_values.get(self.id, self.default_value),
        )
        if self.label:
            html.close_nobr()


@dataclass(kw_only=True, slots=True)
class DynamicDropdown(BaseComponent):
    component_type: Literal["dynamic_dropdown"] = "dynamic_dropdown"
    id: str
    autocompleter: AutocompleterConfig
    has_validation: bool = False

    def render_html(self, filter_id: str, current_values: FilterHTTPVariables) -> None:
        current_value = current_values.get(self.id, "")
        choices = [(current_value, current_value)] if current_value else []

        html.dropdown(
            self.id,
            choices,
            current_value,
            style="width: 250px;",
            class_=["ajax-vals"],
            data_autocompleter=json.dumps(self.autocompleter.config),
        )

        if self.has_validation:
            html.javascript(
                f"cmk.valuespecs.init_on_change_validation('{self.id}', '{filter_id}');"
            )


@dataclass(kw_only=True, slots=True)
class Checkbox(BaseComponent):
    component_type: Literal["checkbox"] = "checkbox"
    id: str
    label: str
    default_value: bool = False

    def render_html(self, filter_id: str, current_values: FilterHTTPVariables) -> None:
        current_value = bool(current_values.get(self.id, self.default_value))
        html.checkbox(self.id, deflt=current_value, label=self.label)


@dataclass(kw_only=True, slots=True)
class CheckboxGroup(BaseComponent):
    """Groups multiple checkboxes under a common label, allowing for multiple selections.

    The default value for each checkbox is `True`, unless some checkboxes are explicitly set in the
    current filter values (in which case the default is `False`).
    """

    component_type: Literal["checkbox_group"] = "checkbox_group"
    choices: ChoiceMapping
    """All checkboxes in this group, variable id -> display label"""
    label: str | None = None
    """Label for the entire group"""

    def __post_init__(self) -> None:
        if not self.choices:
            raise ValueError("Choices must not be empty")

    def render_html(self, filter_id: str, current_values: FilterHTTPVariables) -> None:
        html.begin_checkbox_group()
        if self.label:
            html.write_text_permissive(self.label)
        checkbox_default = not any(current_values.values())
        for var, text in self.choices.items():
            html.checkbox(var, bool(current_values.get(var, checkbox_default)), label=text)
        html.end_checkbox_group()


@dataclass(kw_only=True, slots=True)
class TextInput(BaseComponent):
    component_type: Literal["text_input"] = "text_input"
    id: str
    label: str | None = None
    suffix: str | None = None
    """Suffix to be placed directly after the input field, e.g. a unit like 'ms' or '%'"""

    def render_html(self, filter_id: str, current_values: FilterHTTPVariables) -> None:
        if self.label:
            html.write_text_permissive(self.label)
        html.text_input(self.id, default_value=current_values.get(self.id, ""))
        if self.suffix:
            html.write_text_permissive(self.suffix)


@dataclass(kw_only=True, slots=True)
class RadioButton(BaseComponent):
    component_type: Literal["radio_button"] = "radio_button"
    id: str
    choices: ChoiceMapping
    """All available options, internal value -> display label"""
    default_value: str

    def __post_init__(self) -> None:
        if not self.choices:
            raise ValueError("Choices must not be empty")
        if self.default_value not in self.choices:
            raise ValueError(
                f"Default value {self.default_value!r} is not in the choices: {self.choices!r}"
            )

    def render_html(self, filter_id: str, current_values: FilterHTTPVariables) -> None:
        pick = current_values.get(self.id, self.default_value)
        html.begin_radio_group(horizontal=True)
        for state, text in self.choices.items():
            html.radiobutton(self.id, state, pick == state, text + " &nbsp; ")
        html.end_radio_group()


@dataclass(kw_only=True, slots=True)
class Slider(BaseComponent):
    component_type: Literal["slider"] = "slider"
    id: str
    min_value: int
    max_value: int
    step: int
    default_value: int

    def __post_init__(self) -> None:
        if self.min_value >= self.max_value:
            raise ValueError("Minimum value must be less than maximum value")
        if not (self.min_value <= self.default_value <= self.max_value):
            raise ValueError(
                f"Default value {self.default_value} must be between {self.min_value} and {self.max_value}"
            )
        if self.step <= 0:
            raise ValueError("Step must be a positive integer")
        for name, value in (
            ("Min", self.min_value),
            ("Max", self.max_value),
            ("Default", self.default_value),
        ):
            if value % self.step != 0:
                raise ValueError(f"{name} value {value} must be divisible by step {self.step}")

    def render_html(self, filter_id: str, current_values: FilterHTTPVariables) -> None:
        filter_value = str(current_values.get(self.id))
        actual_value = filter_value if filter_value.isnumeric() else self.default_value
        html.add_form_var(self.id)
        html.open_table()
        html.tr("", id_=self.id, css=["range_input"])
        html.close_table()
        html.javascript(
            "cmk.nodevis.utils.render_input_range(cmk.d3.select(%s), %s, %s)"
            % (
                json.dumps(f"#{self.id}"),
                json.dumps(
                    {
                        "id": self.id,
                        "title": "",
                        "step": self.step,
                        "min": self.min_value,
                        "max": self.max_value,
                        "default_value": self.default_value,
                    },
                ),
                json.dumps(actual_value),
            ),
            data_cmk_execute_after_replace="",
        )


@dataclass(kw_only=True, slots=True)
class StaticText(BaseComponent):
    """A static text component that does not require any interaction."""

    component_type: Literal["static_text"] = "static_text"
    text: str

    def render_html(self, filter_id: str, current_values: FilterHTTPVariables) -> None:
        html.write_text_permissive(self.text)


@dataclass(kw_only=True, slots=True)
class Hidden(BaseComponent):
    component_type: Literal["hidden"] = "hidden"
    id: str
    value: str

    def render_html(self, filter_id: str, current_values: FilterHTTPVariables) -> None:
        html.hidden_field(self.id, self.value, add_var=True)


@dataclass(kw_only=True, slots=True)
class DualList(BaseComponent):
    component_type: Literal["dual_list"] = "dual_list"
    id: str
    choices: ChoiceMapping
    """Choices for the dual list, internal value -> display label"""

    def __post_init__(self) -> None:
        if not self.choices:
            raise ValueError("Choices must not be empty")

    def render_html(self, filter_id: str, current_values: FilterHTTPVariables) -> None:
        choices = [(name, folder) for name, folder in self.choices.items()]
        selected = current_values.get(self.id, "").split("|")
        DualListChoice(choices=choices, rows=4, enlarge_active=True).render_input(self.id, selected)


@dataclass(kw_only=True, slots=True)
class LabelGroupFilterComponent(BaseComponent):
    """A special component just for filtering labels."""

    component_type: Literal["label_group"] = "label_group"
    id: str
    object_type: Literal["host", "service"]

    def render_html(self, filter_id: str, current_values: FilterHTTPVariables) -> None:
        LabelGroups().render_input(
            self.id,
            AllLabelGroupsQuery(object_type=self.object_type).parse_value(current_values),
        )


@dataclass(kw_only=True, slots=True)
class TagFilterComponent(BaseComponent):
    """A special component just for filtering tags."""

    component_type: Literal["tag_filter"] = "tag_filter"
    display_rows: int
    variable_prefix: str

    def __post_init__(self) -> None:
        if self.display_rows < 1:
            raise ValueError("Display rows must be a positive integer")
        if not self.variable_prefix:
            raise ValueError("Variable prefix must not be empty")

    def render_html(self, filter_id: str, current_values: FilterHTTPVariables) -> None:
        operators: Choices = [
            ("is", "="),
            ("isnot", "≠"),
        ]

        html.open_table()
        # Show at least three rows of tag filters (hard coded self.query_filter.count) and add more
        # rows if respective values are given via the URL.
        # E.g. links from the virtual host tree snap-in may contain multiple tag filter values
        num = 0
        while num < self.display_rows or current_values.get(
            "%s_%d_grp" % (self.variable_prefix, num)
        ):
            prefix = "%s_%d" % (self.variable_prefix, num)
            num += 1
            html.open_tr()
            html.open_td()
            grp_value = current_values.get(prefix + "_grp", "")
            grp_choices = [(grp_value, grp_value)] if grp_value else []
            html.dropdown(
                prefix + "_grp",
                grp_choices,
                grp_value,
                style="width: 129px;",
                class_=["ajax-vals"],
                data_autocompleter=json.dumps(
                    AutocompleterConfig(
                        ident="tag_groups",
                        strict=True,
                    ).config
                ),
            )

            html.close_td()
            html.open_td()
            html.dropdown(
                prefix + "_op",
                operators,
                deflt=current_values.get(prefix + "_op", "is"),
                style="width:36px",
                ordered=True,
                class_=["op"],
            )
            html.close_td()
            html.open_td()

            current_value = current_values.get(prefix + "_val", "")
            choices = [(current_value, current_value)] if current_value else []
            html.dropdown(
                prefix + "_val",
                choices,
                current_value,
                style="width: 129px;",
                class_=["ajax-vals"],
                data_autocompleter=json.dumps(
                    AutocompleterConfig(
                        ident="tag_groups_opt",
                        strict=True,
                        dynamic_params_callback_name="tag_group_options_autocompleter",
                    ).config
                ),
            )

            html.close_td()
            html.close_tr()
        html.close_table()


type FilterComponent = (
    HorizontalGroup
    | Dropdown
    | DynamicDropdown
    | Checkbox
    | CheckboxGroup
    | TextInput
    | RadioButton
    | Slider
    | StaticText
    | Hidden
    | DualList
    | LabelGroupFilterComponent
    | TagFilterComponent
)
