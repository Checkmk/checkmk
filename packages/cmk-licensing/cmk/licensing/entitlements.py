#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from enum import StrEnum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StrictInt

# In the license, a limit of -1 means "unlimited"
Limit = Annotated[StrictInt, Field(ge=-1)]


class LicenseEdition(StrEnum):
    """The Checkmk edition the customer bought."""

    cee = "cee"
    cce = "cce"
    cme = "cme"
    cse = "cse"


class LicenseOperationalState(StrEnum):
    """The state of the subscription, e.g. running normally or suspended"""

    active = "active"
    confirmed_renewal = "confirmed_renewal"
    suspended = "suspended"
    in_termination = "in_termination"


class LicenseEntitlements(BaseModel):
    """What a license grants (5.0 license format)

    - Numbers are strict: a wrong type means the response is broken, and
      reading true as 1 or "123" as 123 would hide that.
    - Frozen: what the license service granted is passed around as is,
      and no caller can change it by accident.
    - Extra keys are kept: the license service can add new entitlements
      without breaking older Checkmk versions.
    """

    model_config = ConfigDict(frozen=True, extra="allow")

    checkmk_edition: LicenseEdition
    operational_state: LicenseOperationalState
    service_limit: Limit
    active_metric_series_limit: Limit
    unbound_license: bool
    subscription_start_ts_sec: StrictInt
    subscription_expiration_ts_sec: StrictInt
    subscription_auto_renewal: bool
    subscription_recurrence_unit: str
    grace_period_after_expiration_sec: StrictInt
    reseller_name: str
    group_and_managed_services_use: bool
    ntop_enabled: bool = Field(alias="ntop/enabled")
    virt1_appliance_enabled: bool = Field(alias="virt1_appliance/enabled")
    synthetic_monitoring_enabled: bool = Field(alias="synthetic_monitoring/enabled")
    synthetic_monitoring_limit: Limit = Field(alias="synthetic_monitoring/limit")
