#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

import pytest

from cmk.gui.form_specs import get_visitor, RawDiskData, registration, VisitorOptions
from cmk.plugins.time.rulesets.timesyncd import rule_spec_timesyncd_time


@pytest.fixture(autouse=True)
def _register_form_spec_visitors() -> None:
    registration.register()


def _migrate(rule: Mapping[str, object]) -> object:
    # Migrate the rule the same way it happens during runtime.
    visitor = get_visitor(
        rule_spec_timesyncd_time.parameter_form(),
        VisitorOptions(migrate_values=True, mask_values=False),
    )
    return visitor.to_disk(RawDiskData(rule))


MIGRATED_RULE = {
    "stratum_level": ("fixed", (9, 10)),
    "quality_levels": ("fixed", (0.2, 0.5)),
    "alert_delay": ("fixed", (300.0, 3600.0)),
    "last_ntp_message": ("no_levels", None),
}


@pytest.mark.parametrize(
    "rule, expected",
    [
        pytest.param(
            {
                "stratum_level": 10,
                "quality_levels": (200.0, 500.0),
                "alert_delay": (300, 3600),
                "last_synchronized": (7500, 10800),
                "last_ntp_message": (3600, 7200),
            },
            {
                # The single "critical at stratum" integer becomes the critical
                # level, with the warning level one stratum below it.
                "stratum_level": ("fixed", (9, 10)),
                # The offset levels were stored in milliseconds; the form spec
                # works in seconds.
                "quality_levels": ("fixed", (0.2, 0.5)),
                "alert_delay": ("fixed", (300.0, 3600.0)),
                "last_synchronized": ("fixed", (7500.0, 10800.0)),
                "last_ntp_message": ("fixed", (3600.0, 7200.0)),
            },
            id="pre-migration rule (bare tuples)",
        ),
        pytest.param(
            MIGRATED_RULE,
            MIGRATED_RULE,
            id="migrated rule stays unchanged",
        ),
    ],
)
def test_rule_spec_timesyncd_time_migration(
    rule: Mapping[str, object], expected: Mapping[str, object]
) -> None:
    assert _migrate(rule) == expected
