#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.gui.form_specs import get_visitor, RawDiskData, VisitorOptions
from cmk.gui.plugins.wato.check_parameters.systemd_services_summary import (
    _migrate_required_states,
    _parameter_form_systemd_units_summary,
)


@pytest.mark.parametrize(
    "value, expected",
    [
        pytest.param(
            {"states": {"failed": 1}, "states_default": 1},
            {"states": {"active": 0, "inactive": 0, "failed": 1}, "states_default": 1},
            id="2.4 states without required keys",
        ),
        pytest.param(
            {"states": {"active": 1, "inactive": 1, "failed": 1}},
            {"states": {"active": 1, "inactive": 1, "failed": 1}},
            id="complete states",
        ),
        pytest.param({"states_default": 1}, {"states_default": 1}, id="no states"),
    ],
)
def test_migrate_required_states(value: object, expected: dict[str, object]) -> None:
    assert _migrate_required_states(value) == expected


def test_value_stored_by_2_4_is_migrated_to_a_valid_value() -> None:
    visitor = get_visitor(
        _parameter_form_systemd_units_summary(),
        VisitorOptions(migrate_values=True, mask_values=False),
    )
    stored = RawDiskData(
        {
            "states": {"failed": 1},
            "activating_levels": None,
            "deactivating_levels": (30, 60),
            "ignored": ["foo"],
        }
    )

    assert visitor.to_disk(stored) == {
        "states": {"active": 0, "inactive": 0, "failed": 1},
        "activating_levels": ("no_levels", None),
        "deactivating_levels": ("fixed", (30.0, 60.0)),
        "ignored": ["foo"],
    }
    assert not visitor.validate(stored)
