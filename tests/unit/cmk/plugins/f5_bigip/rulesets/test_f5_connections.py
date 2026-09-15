#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

import pytest

from cmk.gui.form_specs import get_visitor, RawDiskData, registration, VisitorOptions
from cmk.plugins.f5_bigip.rulesets.f5_connections import rule_spec_f5_connections


@pytest.fixture
def _register_form_spec_visitors() -> None:
    registration.register()


def _migrate(rule: Mapping[str, object]) -> object:
    # Migrate the rule the same way it happens during runtime.
    visitor = get_visitor(
        rule_spec_f5_connections.parameter_form(),
        VisitorOptions(migrate_values=True, mask_values=False),
    )
    return visitor.to_disk(RawDiskData(rule))


_PREDICTIVE_RULE = {
    "connections_rate": (
        "cmk_postprocessed",
        "predictive_levels",
        {
            # Injected by the form spec from `PredictiveLevels(reference_metric=...)`.
            "__reference_metric__": "connections_rate",
            "__direction__": "upper",
            "period": "wday",
            "horizon": 90,
            "levels": ("absolute", (0, 0)),
            "bound": None,
        },
    ),
}


@pytest.mark.parametrize(
    "rule, expected",
    [
        pytest.param(
            {
                "conns": (25000, 30000),
                "ssl_conns": (25000, 30000),
                "connections_rate": (500, 1000),
                "connections_rate_lower": (100, 50),
                "http_req_rate": (500, 1000),
            },
            {
                "conns": ("fixed", (25000, 30000)),
                "ssl_conns": ("fixed", (25000, 30000)),
                "connections_rate": ("fixed", (500, 1000)),
                "connections_rate_lower": ("fixed", (100, 50)),
                "http_req_rate": ("fixed", (500, 1000)),
            },
            id="fixed levels stored as bare tuples",
        ),
        pytest.param(
            {"conns": None, "connections_rate_lower": (100, 50)},
            {
                # "No levels" was a valid choice of the legacy `Levels` valuespec.
                "conns": ("no_levels", None),
                "connections_rate_lower": ("fixed", (100, 50)),
            },
            id="explicit no levels",
        ),
        pytest.param(
            {
                "connections_rate": {
                    "period": "wday",
                    "horizon": 90,
                    "levels_upper": ("absolute", (0.0, 0.0)),
                },
            },
            _PREDICTIVE_RULE,
            id="legacy predictive levels dict",
        ),
        pytest.param(_PREDICTIVE_RULE, _PREDICTIVE_RULE, id="migrated rule stays unchanged"),
    ],
)
@pytest.mark.usefixtures("_register_form_spec_visitors")
def test_rule_spec_f5_connections_migration(
    rule: Mapping[str, object], expected: Mapping[str, object]
) -> None:
    assert _migrate(rule) == expected
