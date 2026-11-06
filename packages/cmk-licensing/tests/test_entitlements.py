#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest
from pydantic import ValidationError

from cmk.licensing.entitlements import (
    LicenseEdition,
    LicenseEntitlements,
    LicenseOperationalState,
)

# A complete, valid 5.0 entitlements object, as the license service sends it
_RAW_5_0 = {
    "checkmk_edition": "cce",
    "operational_state": "active",
    "service_limit": 1000,
    "active_metric_series_limit": 2000,
    "unbound_license": True,
    "subscription_start_ts_sec": 1774742400,
    "subscription_expiration_ts_sec": 1806278400,
    "subscription_auto_renewal": True,
    "subscription_recurrence_unit": "yearly",
    "grace_period_after_expiration_sec": 1209600,
    "reseller_name": "reseller",
    "group_and_managed_services_use": True,
    "ntop/enabled": True,
    "virt1_appliance/enabled": True,
    "synthetic_monitoring/enabled": True,
    "synthetic_monitoring/limit": 100,
}


def test_parse_all_keys() -> None:
    entitlements = LicenseEntitlements.model_validate(_RAW_5_0)

    assert entitlements.model_extra == {}
    assert entitlements.model_dump(by_alias=True) == _RAW_5_0
    assert entitlements.checkmk_edition is LicenseEdition.cce
    assert entitlements.operational_state is LicenseOperationalState.active
    assert entitlements.ntop_enabled is True
    assert entitlements.synthetic_monitoring_limit == 100


def test_entitlements_are_frozen() -> None:
    entitlements = LicenseEntitlements.model_validate(_RAW_5_0)
    with pytest.raises(ValidationError):
        entitlements.service_limit = 1  # type: ignore[misc]


_LIMITS = ["service_limit", "active_metric_series_limit", "synthetic_monitoring/limit"]


@pytest.mark.parametrize("key", _LIMITS)
@pytest.mark.parametrize("value", [-1, 0, 1000])
def test_valid_limit(key: str, value: int) -> None:
    entitlements = LicenseEntitlements.model_validate({**_RAW_5_0, key: value})
    assert entitlements.model_dump(by_alias=True)[key] == value


@pytest.mark.parametrize("key", _LIMITS)
def test_limit_below_unlimited(key: str) -> None:
    with pytest.raises(ValidationError):
        LicenseEntitlements.model_validate({**_RAW_5_0, key: -2})


def test_extra_keys_are_kept() -> None:
    entitlements = LicenseEntitlements.model_validate(
        {**_RAW_5_0, "netflow/collector_limit": 123, "future/not_configured_yet": None}
    )
    assert entitlements.model_extra == {
        "netflow/collector_limit": 123,
        "future/not_configured_yet": None,
    }
