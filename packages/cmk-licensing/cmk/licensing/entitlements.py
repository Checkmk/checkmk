#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from enum import StrEnum
from typing import Annotated

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
    StrictBool,
    StrictInt,
    ValidationError,
    ValidationInfo,
    ValidatorFunctionWrapHandler,
)

from cmk.licensing.helper import get_licensing_logger

_LOGGER = get_licensing_logger()

# In the license, a limit of -1 means "unlimited"
Limit = Annotated[StrictInt, Field(ge=-1)]

# Without a grace period and recurrence unit, use the same values as
# basics/verification.py does for responses that don't have them.
_DEFAULT_GRACE_PERIOD_AFTER_EXPIRATION_SEC = 2592000  # seconds in 30 days
_DEFAULT_SUBSCRIPTION_RECURRENCE_UNIT = "yearly"


class LicenseEdition(StrEnum):
    """The Checkmk edition the customer bought."""

    cee = "cee"
    cce = "cce"
    cme = "cme"
    cse = "cse"
    unknown = "unknown"


class LicenseOperationalState(StrEnum):
    """The state of the subscription, e.g. running normally or suspended"""

    active = "active"
    confirmed_renewal = "confirmed_renewal"
    suspended = "suspended"
    in_termination = "in_termination"
    unknown = "unknown"


class LicenseEntitlements(BaseModel):
    """What a license grants (5.0 license format)

    - Numbers and booleans are strict: a wrong type means the response is
      broken, and reading true as 1, "123" as 123 or "yes" as true would
      hide that.
    - Frozen: what the license service granted is passed around as is,
      and no caller can change it by accident.
    - Extra keys are kept: the license service can add new entitlements
      without breaking older Checkmk versions.
    """

    model_config = ConfigDict(frozen=True, extra="allow")

    checkmk_edition: LicenseEdition = LicenseEdition.unknown
    operational_state: LicenseOperationalState = LicenseOperationalState.unknown
    service_limit: Limit = 0
    active_metric_series_limit: Limit = 0
    unbound_license: StrictBool = False
    subscription_start_ts_sec: StrictInt = 0
    subscription_expiration_ts_sec: StrictInt = 0
    subscription_auto_renewal: StrictBool = False
    subscription_recurrence_unit: str = _DEFAULT_SUBSCRIPTION_RECURRENCE_UNIT
    grace_period_after_expiration_sec: StrictInt = _DEFAULT_GRACE_PERIOD_AFTER_EXPIRATION_SEC
    reseller_name: str = ""
    group_and_managed_services_use: StrictBool = False
    ntop_enabled: StrictBool = Field(default=False, alias="ntop/enabled")
    virt1_appliance_enabled: StrictBool = Field(default=False, alias="virt1_appliance/enabled")
    synthetic_monitoring_enabled: StrictBool = Field(
        default=False, alias="synthetic_monitoring/enabled"
    )
    synthetic_monitoring_limit: Limit = Field(default=0, alias="synthetic_monitoring/limit")

    @classmethod
    def _key(cls, field_name: str) -> str:
        """The key as the license writes it"""
        return cls.model_fields[field_name].alias or field_name

    @model_validator(mode="before")
    @classmethod
    def _default_missing(cls, raw: object) -> object:
        """A missing or null value gets its default and a warning naming the key"""
        if not isinstance(raw, dict):
            return raw
        known_keys = [cls._key(name) for name in cls.model_fields]
        for key in known_keys:
            if raw.get(key) is None:
                # Only the key is logged, never the value.
                _LOGGER.warning(
                    "License entitlement %(key)r is missing, using its default", {"key": key}
                )
        # Drop the null values of known keys, so pydantic uses their defaults.
        return {k: v for k, v in raw.items() if v is not None or k not in known_keys}

    @field_validator("*", mode="wrap")
    @classmethod
    def _default_wrong(
        cls, value: object, handler: ValidatorFunctionWrapHandler, info: ValidationInfo[object]
    ) -> object:
        """A wrong value gets its default and a warning naming the key"""
        try:
            return handler(value)
        except ValidationError:
            if info.field_name is None:
                raise
            _LOGGER.warning(
                "License entitlement value for %(key)r is invalid, using its default",
                {"key": cls._key(info.field_name)},
            )
            return cls.model_fields[info.field_name].default
