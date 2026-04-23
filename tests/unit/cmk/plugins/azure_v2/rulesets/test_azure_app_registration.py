#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import pytest

from cmk.plugins.azure_v2.rulesets.azure_app_registration import (
    _migrate,
    SEVEN_DAYS,
    SIX_MONTHS_ONE_DAY,
    THIRTY_DAYS,
)

ONE_YEAR = 365 * 24 * 60 * 60


@pytest.mark.parametrize(
    "old_value, expected",
    [
        pytest.param(
            {
                "expiration_time_secrets": ("fixed", (THIRTY_DAYS, SEVEN_DAYS)),
                "expiration_time_certificates": ("fixed", (THIRTY_DAYS, SEVEN_DAYS)),
            },
            {
                "secrets": {"remaining_validity": ("fixed", (THIRTY_DAYS, SEVEN_DAYS))},
                "certificates": {"remaining_validity": ("fixed", (THIRTY_DAYS, SEVEN_DAYS))},
            },
            id="old flat format: both keys",
        ),
        pytest.param(
            {"expiration_time_secrets": ("fixed", (THIRTY_DAYS, SEVEN_DAYS))},
            {"secrets": {"remaining_validity": ("fixed", (THIRTY_DAYS, SEVEN_DAYS))}},
            id="old flat format: secrets only",
        ),
        pytest.param(
            {"expiration_time_certificates": ("fixed", (THIRTY_DAYS, SEVEN_DAYS))},
            {"certificates": {"remaining_validity": ("fixed", (THIRTY_DAYS, SEVEN_DAYS))}},
            id="old flat format: certificates only",
        ),
        pytest.param(
            {},
            {},
            id="old flat format: empty",
        ),
        pytest.param(
            {"secrets": {"remaining_validity": ("fixed", (THIRTY_DAYS, SEVEN_DAYS))}},
            {"secrets": {"remaining_validity": ("fixed", (THIRTY_DAYS, SEVEN_DAYS))}},
            id="new format: secrets only — passed through unchanged",
        ),
        pytest.param(
            {"certificates": {"remaining_validity": ("fixed", (THIRTY_DAYS, SEVEN_DAYS))}},
            {"certificates": {"remaining_validity": ("fixed", (THIRTY_DAYS, SEVEN_DAYS))}},
            id="new format: certificates only — passed through unchanged",
        ),
        pytest.param(
            {
                "secrets": {
                    "remaining_validity": ("fixed", (THIRTY_DAYS, SEVEN_DAYS)),
                    "max_validity": ("fixed", (SIX_MONTHS_ONE_DAY, SIX_MONTHS_ONE_DAY)),
                },
                "certificates": {
                    "remaining_validity": ("fixed", (THIRTY_DAYS, SEVEN_DAYS)),
                    "max_validity": ("fixed", (SIX_MONTHS_ONE_DAY, SIX_MONTHS_ONE_DAY)),
                },
            },
            {
                "secrets": {
                    "remaining_validity": ("fixed", (THIRTY_DAYS, SEVEN_DAYS)),
                    "max_validity": ("fixed", (SIX_MONTHS_ONE_DAY, SIX_MONTHS_ONE_DAY)),
                },
                "certificates": {
                    "remaining_validity": ("fixed", (THIRTY_DAYS, SEVEN_DAYS)),
                    "max_validity": ("fixed", (SIX_MONTHS_ONE_DAY, SIX_MONTHS_ONE_DAY)),
                },
            },
            id="new format: both keys with max_validity — passed through unchanged",
        ),
        pytest.param(
            {
                "secrets": {
                    "remaining_validity": ("fixed", (THIRTY_DAYS, SEVEN_DAYS)),
                    "ignore_if_older_than": ONE_YEAR,
                }
            },
            {
                "secrets": {
                    "remaining_validity": ("fixed", (THIRTY_DAYS, SEVEN_DAYS)),
                    "ignore_if_older_than": ONE_YEAR,
                }
            },
            id="new format: secrets with ignore_if_older_than — passed through unchanged",
        ),
    ],
)
def test_migrate(old_value: object, expected: object) -> None:
    assert _migrate(old_value) == expected
