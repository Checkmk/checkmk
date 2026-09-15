#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

import pytest

from cmk.gui.form_specs import get_visitor, RawDiskData, registration, VisitorOptions
from cmk.plugins.f5_bigip.rulesets.f5_bigip_vserver import rule_spec_f5_bigip_vserver


@pytest.fixture
def _register_form_spec_visitors() -> None:
    registration.register()


def _migrate(rule: Mapping[str, object]) -> object:
    # Migrate the rule the same way it happens during runtime.
    visitor = get_visitor(
        rule_spec_f5_bigip_vserver.parameter_form(),
        VisitorOptions(migrate_values=True, mask_values=False),
    )
    return visitor.to_disk(RawDiskData(rule))


_STATE_MAP = {
    "is_disabled": 1,
    "is_up_and_available": 0,
    "is_currently_not_available": 2,
    "is_not_available": 2,
    "availability_is_unknown": 1,
    "is_unlicensed": 3,
    "children_pool_members_down_if_not_available": 0,
}


@pytest.mark.parametrize(
    "rule, expected",
    [
        pytest.param(
            {
                "connections": (1000.0, 2000.0),
                "if_in_octets": (1000.0, 2000.0),
                "if_total_pkts_lower": (100.0, 10.0),
            },
            {
                "connections": ("fixed", (1000.0, 2000.0)),
                "if_in_octets": ("fixed", (1000.0, 2000.0)),
                "if_total_pkts_lower": ("fixed", (100.0, 10.0)),
            },
            id="fixed levels stored as bare tuples",
        ),
        pytest.param(
            {"state": _STATE_MAP},
            {"state": _STATE_MAP},
            id="the state map is carried over unchanged",
        ),
        pytest.param(
            {"if_out_octets": None},
            {"if_out_octets": ("no_levels", None)},
            id="explicit no levels",
        ),
        pytest.param(
            {
                "connections": {
                    "period": "wday",
                    "horizon": 90,
                    "levels_upper": ("absolute", (10.0, 20.0)),
                },
            },
            {
                "connections": (
                    "cmk_postprocessed",
                    "predictive_levels",
                    {
                        "__reference_metric__": "connections",
                        "__direction__": "upper",
                        "period": "wday",
                        "horizon": 90,
                        "levels": ("absolute", (10.0, 20.0)),
                        "bound": None,
                    },
                ),
            },
            id="legacy predictive levels",
        ),
    ],
)
@pytest.mark.usefixtures("_register_form_spec_visitors")
def test_rule_spec_f5_bigip_vserver_migration(
    rule: Mapping[str, object], expected: Mapping[str, object]
) -> None:
    assert _migrate(rule) == expected
