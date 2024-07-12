#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

import pytest

from cmk.plugins.siemens_plc.rulesets.special_agent import _migrate_value_entry, _validate_values
from cmk.rulesets.v1.form_specs.validators import ValidationError


@pytest.mark.parametrize(
    ["old_value", "migrated_value"],
    [
        (
            (("db", 1), 1.2, "dint", None, "id1"),
            {
                "address": 1.2,
                "area": (
                    "db",
                    1,
                ),
                "data_type": (
                    "dint",
                    None,
                ),
                "id": "id1",
                "value_type": "unclassified",
            },
        ),
        (
            ("merker", 1.3, "real", "seconds_since_service", "id2"),
            {
                "address": 1.3,
                "area": (
                    "merker",
                    None,
                ),
                "data_type": (
                    "real",
                    None,
                ),
                "id": "id2",
                "value_type": "seconds_since_service",
            },
        ),
        (
            ("timer", 2.5, "bit", "temp", "t1"),
            {
                "address": 2.5,
                "area": (
                    "timer",
                    None,
                ),
                "data_type": (
                    "bit",
                    None,
                ),
                "id": "t1",
                "value_type": "temp",
            },
        ),
        (
            ("counter", 3.4, ("str", 2), "text", "s1"),
            {
                "address": 3.4,
                "area": (
                    "counter",
                    None,
                ),
                "data_type": (
                    "str",
                    2,
                ),
                "id": "s1",
                "value_type": "text",
            },
        ),
    ],
)
def test_migrate_value_entry(old_value: object, migrated_value: Mapping[str, object]) -> None:
    assert _migrate_value_entry(old_value) == migrated_value


def test_validate_values_ok() -> None:
    _validate_values(
        [
            {
                "address": 1.2,
                "area": (
                    "db",
                    1,
                ),
                "data_type": (
                    "dint",
                    None,
                ),
                "id": "id1",
                "value_type": "unclassified",
            },
            {
                "address": 1.3,
                "area": (
                    "merker",
                    None,
                ),
                "data_type": (
                    "real",
                    None,
                ),
                "id": "id2",
                "value_type": "seconds_since_service",
            },
            {
                "address": 2.5,
                "area": (
                    "timer",
                    None,
                ),
                "data_type": (
                    "bit",
                    None,
                ),
                "id": "t1",
                "value_type": "temp",
            },
            {
                "address": 3.4,
                "area": (
                    "counter",
                    None,
                ),
                "data_type": (
                    "str",
                    2,
                ),
                "id": "s1",
                "value_type": "text",
            },
        ]
    )


def test_validate_values_error() -> None:
    with pytest.raises(ValidationError):
        _validate_values(
            [
                {
                    "address": 1.2,
                    "area": (
                        "db",
                        1,
                    ),
                    "data_type": (
                        "dint",
                        None,
                    ),
                    "id": "id1",
                    "value_type": "unclassified",
                },
                {
                    "address": 1.3,
                    "area": (
                        "db",
                        2,
                    ),
                    "data_type": (
                        "dint",
                        None,
                    ),
                    "id": "id1",
                    "value_type": "unclassified",
                },
            ]
        )
