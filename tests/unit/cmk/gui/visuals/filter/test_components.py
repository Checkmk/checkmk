#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import pytest

from cmk.gui.visuals.filter.components import (
    Checkbox,
    CheckboxGroup,
    Dropdown,
    DualList,
    HorizontalGroup,
    RadioButton,
    Slider,
    TagFilterComponent,
)


def test_horizontal_group_valid() -> None:
    HorizontalGroup(
        components=[
            Checkbox(id="...", label="Checkbox 1"),
        ],
    )


def test_horizontal_group_empty() -> None:
    with pytest.raises(ValueError, match="Must contain at least one component"):
        HorizontalGroup(
            components=[],
        )


def test_dropdown_valid_default() -> None:
    # default is in choices
    Dropdown(
        id="...",
        choices={"option1": "Option 1", "option2": "Option 2"},
        default_value="option1",
    )

    # default is empty string
    Dropdown(
        id="...",
        choices={"": "Option 1", "other": "Option 2"},
    )


def test_dropdown_invalid_default() -> None:
    with pytest.raises(ValueError, match="Default value .* is not in the choices"):
        Dropdown(
            id="...",
            choices={"option1": "Option 1", "option2": "Option 2"},
        )

    with pytest.raises(ValueError, match="Default value .* is not in the choices"):
        Dropdown(
            id="...",
            choices={"": "Option 1", "other": "Option 2"},
            default_value="unrelated",
        )


def test_dropdown_empty_choices() -> None:
    with pytest.raises(ValueError, match="Choices must not be empty"):
        Dropdown(
            id="...",
            choices={},
        )


def test_checkbox_group_valid() -> None:
    CheckboxGroup(
        label="Checkboxes",
        choices={"option1": "Option 1", "option2": "Option 2"},
    )


def test_checkbox_group_empty_choices() -> None:
    with pytest.raises(ValueError, match="Choices must not be empty"):
        CheckboxGroup(
            label="Checkboxes",
            choices={},
        )


def test_radio_button_valid() -> None:
    RadioButton(
        id="...",
        choices={"option1": "Option 1", "option2": "Option 2"},
        default_value="option1",
    )


def test_radio_button_empty_choices() -> None:
    with pytest.raises(ValueError, match="Choices must not be empty"):
        RadioButton(
            id="...",
            choices={},
            default_value="",
        )


def test_radio_button_invalid_default() -> None:
    with pytest.raises(ValueError, match="Default value .* is not in the choices"):
        RadioButton(
            id="...",
            choices={"option1": "Option 1", "option2": "Option 2"},
            default_value="unrelated",
        )


def test_slider_valid() -> None:
    Slider(
        id="...",
        min_value=0,
        max_value=100,
        step=1,
        default_value=50,
    )


def test_slider_min_max() -> None:
    with pytest.raises(ValueError, match="Minimum value must be less than maximum value"):
        Slider(
            id="...",
            min_value=100,
            max_value=0,
            step=1,
            default_value=50,
        )


def test_slider_step() -> None:
    with pytest.raises(ValueError, match="Step must be a positive integer"):
        Slider(
            id="...",
            min_value=0,
            max_value=100,
            step=0,
            default_value=50,
        )


def test_slider_covers_all_values() -> None:
    with pytest.raises(ValueError, match="Max value .* must be divisible by step"):
        Slider(
            id="...",
            min_value=0,
            max_value=10,
            step=3,
            default_value=3,
        )

    with pytest.raises(ValueError, match="Min value .* must be divisible by step"):
        Slider(
            id="...",
            min_value=1,
            max_value=10,
            step=3,
            default_value=3,
        )

    with pytest.raises(ValueError, match="Default value .* must be divisible by step"):
        Slider(
            id="...",
            min_value=0,
            max_value=10,
            step=2,
            default_value=5,
        )


def test_slider_default_in_range() -> None:
    with pytest.raises(ValueError, match="Default value .* must be between .* and .*"):
        Slider(
            id="...",
            min_value=0,
            max_value=100,
            step=1,
            default_value=150,
        )

    with pytest.raises(ValueError, match="Default value .* must be between .* and .*"):
        Slider(
            id="...",
            min_value=0,
            max_value=100,
            step=1,
            default_value=-10,
        )


def test_dual_list_valid() -> None:
    DualList(
        id="...",
        choices={"option1": "Option 1", "option2": "Option 2"},
    )


def test_dual_list_empty_choices() -> None:
    with pytest.raises(ValueError, match="Choices must not be empty"):
        DualList(
            id="...",
            choices={},
        )


def test_tag_filter_valid() -> None:
    TagFilterComponent(
        display_rows=1,
        variable_prefix="x",
    )


def test_tag_filter_invalid_display_rows() -> None:
    with pytest.raises(ValueError, match="Display rows must be a positive integer"):
        TagFilterComponent(
            display_rows=0,
            variable_prefix="x",
        )


def test_tag_filter_empty_variable_prefix() -> None:
    with pytest.raises(ValueError, match="Variable prefix must not be empty"):
        TagFilterComponent(
            display_rows=1,
            variable_prefix="",
        )
