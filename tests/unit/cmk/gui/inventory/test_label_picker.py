#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.gui.exceptions import MKUserError
from cmk.gui.inventory._label_picker import parameter_form


def _value(
    *,
    label_prefix: str = "cmk/inventory",
    label_name: str = "product",
    value_match: tuple[str, object] = ("use_value", None),
) -> dict[str, object]:
    return {
        "configs": [
            {
                "source": {
                    "path": "hardware.os",
                    "attributes": [
                        {
                            "key_match": "key",
                            "value_match": value_match,
                            "label_name": label_name,
                        }
                    ],
                    "columns": [],
                },
                "labeling": {
                    "label_prefix": label_prefix,
                    "case_conversion": {"label": "no_conversion", "value": "no_conversion"},
                },
            }
        ]
    }


@pytest.mark.parametrize(
    "label_prefix",
    [
        pytest.param("cmk/inventory", id="one-slash"),
        pytest.param("cmk", id="no-slash"),
        pytest.param("cmk/inventory/extra", id="multiple-slashes"),
        pytest.param("", id="empty"),
    ],
)
def test_parameter_form_accepts_any_prefix(label_prefix: str) -> None:
    parameter_form().validate_value(_value(label_prefix=label_prefix), "x")


def test_parameter_form_accepts_label_name_with_slash() -> None:
    parameter_form().validate_value(_value(label_name="a/b"), "x")


def _replacing(pattern: str, replacement: str) -> tuple[str, object]:
    return (
        "match_and_replace_value",
        [{"value_match": pattern, "value_replacement": replacement}],
    )


@pytest.mark.parametrize(
    "pattern, replacement",
    [
        pytest.param(r"Server (\d+)", r"Win \1", id="numbered-group"),
        pytest.param(r"Server (?P<version>\d+)", r"Win \g<version>", id="named-group"),
        pytest.param(r"Server", r"\g<0>", id="whole-match"),
        pytest.param(r"Server", r"Win\\1", id="escaped-backslash"),
    ],
)
def test_parameter_form_accepts_valid_replacement(pattern: str, replacement: str) -> None:
    parameter_form().validate_value(_value(value_match=_replacing(pattern, replacement)), "x")


@pytest.mark.parametrize(
    "pattern, replacement",
    [
        pytest.param(r"^Apache", r"\1", id="no-group"),
        pytest.param(r"(Apache)", r"\2", id="missing-number"),
        pytest.param(r"(?P<name>Apache)", r"\g<version>", id="missing-name"),
        pytest.param(r"Apache", r"\d", id="bad-escape"),
        pytest.param(r"Apache", r"\x4", id="incomplete-hex-escape"),
        pytest.param(r"(Apache)", r"\g<1", id="unterminated-group"),
        pytest.param(r"Apache", "Win\\", id="trailing-backslash"),
    ],
)
def test_parameter_form_rejects_invalid_replacement(pattern: str, replacement: str) -> None:
    with pytest.raises(MKUserError):
        parameter_form().validate_value(_value(value_match=_replacing(pattern, replacement)), "x")
