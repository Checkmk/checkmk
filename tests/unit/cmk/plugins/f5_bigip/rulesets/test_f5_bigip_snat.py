#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

import pytest

from cmk.gui.form_specs import get_visitor, RawDiskData, registration, VisitorOptions
from cmk.plugins.f5_bigip.rulesets.f5_bigip_snat import rule_spec_f5_bigip_snat


@pytest.fixture
def _register_form_spec_visitors() -> None:
    registration.register()


def _migrate(rule: Mapping[str, object]) -> object:
    # Migrate the rule the same way it happens during runtime.
    visitor = get_visitor(
        rule_spec_f5_bigip_snat.parameter_form(),
        VisitorOptions(migrate_values=True, mask_values=False),
    )
    return visitor.to_disk(RawDiskData(rule))


_MIGRATED_PREDICTIVE = (
    "cmk_postprocessed",
    "predictive_levels",
    {
        "__reference_metric__": "if_in_octets",
        "__direction__": "lower",
        "period": "wday",
        "horizon": 90,
        "levels": ("stdev", (2.0, 4.0)),
        "bound": None,
    },
)


@pytest.mark.parametrize(
    "rule, expected",
    [
        pytest.param(
            {
                "if_in_octets": (1000.0, 2000.0),
                "if_in_octets_lower": (100.0, 50.0),
                "if_total_pkts": (10000.0, 20000.0),
            },
            {
                "if_in_octets": ("fixed", (1000.0, 2000.0)),
                "if_in_octets_lower": ("fixed", (100.0, 50.0)),
                "if_total_pkts": ("fixed", (10000.0, 20000.0)),
            },
            id="fixed levels stored as bare tuples",
        ),
        pytest.param(
            {"if_out_octets": None},
            {"if_out_octets": ("no_levels", None)},
            id="explicit no levels",
        ),
        pytest.param(
            {
                "if_in_octets_lower": {
                    "period": "wday",
                    "horizon": 90,
                    "levels_lower": ("stdev", (2.0, 4.0)),
                },
            },
            {"if_in_octets_lower": _MIGRATED_PREDICTIVE},
            id="legacy predictive lower levels",
        ),
        pytest.param(
            {"if_in_octets_lower": _MIGRATED_PREDICTIVE},
            {"if_in_octets_lower": _MIGRATED_PREDICTIVE},
            id="migrated rule stays unchanged",
        ),
    ],
)
@pytest.mark.usefixtures("_register_form_spec_visitors")
def test_rule_spec_f5_bigip_snat_migration(
    rule: Mapping[str, object], expected: Mapping[str, object]
) -> None:
    assert _migrate(rule) == expected
