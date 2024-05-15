#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

import pytest

from cmk.plugins.collection.rulesets.alertmanager import (
    migrate_dropdown_ident,
    migrate_non_identifier_key,
)


@pytest.mark.parametrize(
    "raw_value, expected_value",
    [
        pytest.param(
            (True, {"min_amount_rules": 3, "no_group_services": ["service_name"]}),
            ("multiple_services", {"min_amount_rules": 3, "no_group_services": ["service_name"]}),
            id="legacy multiple services",
        ),
        pytest.param(
            (False, {}),
            ("one_service", None),
            id="legacy one service",
        ),
        pytest.param(
            ("multiple_services", {"min_amount_rules": 3, "no_group_services": ["service_name"]}),
            ("multiple_services", {"min_amount_rules": 3, "no_group_services": ["service_name"]}),
            id="multiple services",
        ),
        pytest.param(
            ("one_service", None),
            ("one_service", None),
            id="one service",
        ),
    ],
)
def test_migrate_dropdown_ident(
    raw_value: object, expected_value: tuple[str, object] | None
) -> None:
    assert migrate_dropdown_ident(raw_value) == expected_value


def test_migrate_dropdown_ident_exception() -> None:
    raw_value = {"key1": 1, "key2": 2}
    with pytest.raises(TypeError, match="Invalid type. group_services should be a tuple."):
        migrate_dropdown_ident(raw_value)


@pytest.mark.parametrize(
    "raw_value, expected_value",
    [
        pytest.param(
            {"inactive": 0, "pending": 2, "firing": 0, "none": 2, "n/a": 2},
            {"inactive": 0, "pending": 2, "firing": 0, "none": 2, "not_applicable": 2},
            id="legacy not applicable key",
        ),
        pytest.param(
            {"inactive": 0, "pending": 2, "firing": 0, "none": 2, "not_applicable": 2},
            {"inactive": 0, "pending": 2, "firing": 0, "none": 2, "not_applicable": 2},
            id="migrated not applicable key",
        ),
    ],
)
def test_migrate_non_identifier_key(
    raw_value: object, expected_value: Mapping[str, object]
) -> None:
    assert migrate_non_identifier_key(raw_value) == expected_value


def test_migrate_non_identifier_key_exception() -> None:
    raw_value = (1, 2, 3)
    with pytest.raises(TypeError, match="Invalid type. map should be a dict."):
        migrate_non_identifier_key(raw_value)
