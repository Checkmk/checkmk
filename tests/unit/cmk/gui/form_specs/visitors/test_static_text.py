#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Tests for the ``StaticText`` form spec / visitor.

``StaticText`` renders read-only text injected at render time. There is no
input field, no validation, and the parsed value round-trips through
``to_disk`` unchanged. ``style`` selects a mutually-exclusive presentation
mode (plain text, preformatted ``<pre>`` block, or an alert box) that is
propagated to the frontend via the shared-typing payload.
"""

from cmk.gui.form_specs import (
    DefaultValue,
    RawDiskData,
    VisitorOptions,
)
from cmk.gui.form_specs.unstable.static_text import StaticText, StaticTextStyle
from cmk.gui.form_specs.visitors.static_text import StaticTextVisitor
from cmk.rulesets.v1 import Help, Title
from cmk.shared_typing import vue_formspec_components as shared_type_defs


def _visitor(*, style: StaticTextStyle = "text") -> StaticTextVisitor:
    return StaticTextVisitor(
        StaticText(
            title=Title("X"),
            help_text=Help("Y"),
            style=style,
        ),
        VisitorOptions(migrate_values=False, mask_values=False),
    )


def test_to_vue_passes_through_injected_string() -> None:
    spec, value = _visitor().to_vue(RawDiskData("hello"))
    assert value == "hello"
    assert spec.value == "hello"  # type: ignore[attr-defined]


def test_to_vue_style_defaults_to_text() -> None:
    spec, _ = _visitor().to_vue(RawDiskData("hello"))
    assert spec.style == shared_type_defs.StaticTextStyle.text  # type: ignore[attr-defined]


def test_to_vue_preformatted_style_propagates() -> None:
    spec, _ = _visitor(style="preformatted").to_vue(RawDiskData("first\n    second"))
    assert spec.style == shared_type_defs.StaticTextStyle.preformatted  # type: ignore[attr-defined]
    assert spec.value == "first\n    second"  # type: ignore[attr-defined]


def test_to_vue_alert_style_propagates() -> None:
    spec, _ = _visitor(style="alert_info").to_vue(RawDiskData("generated on save"))
    assert spec.style == shared_type_defs.StaticTextStyle.alert_info  # type: ignore[attr-defined]


def test_default_value_renders_empty_string() -> None:
    spec, value = _visitor().to_vue(DefaultValue())
    assert value == ""
    assert spec.value == ""  # type: ignore[attr-defined]


def test_non_string_input_falls_back_to_empty() -> None:
    """A render-time injection that is not a string (e.g. ``None``) must not
    crash the form; the widget falls back to an empty display."""
    spec, value = _visitor().to_vue(RawDiskData(None))
    assert value == ""
    assert spec.value == ""  # type: ignore[attr-defined]


def test_to_disk_round_trips_value() -> None:
    assert _visitor().to_disk(RawDiskData("computed-url")) == "computed-url"


def test_validate_returns_no_errors() -> None:
    """StaticText is read-only; nothing about it should ever fail validation."""
    assert _visitor().validate(RawDiskData("anything goes")) == []
