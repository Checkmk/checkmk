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

from cmk.licensing.basics.protocol_version import (
    AllowedVerificationResponseVersions,
    parse_verification_response_version,
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


def entitlements_from_old_response(raw: object) -> LicenseEntitlements:
    """Turn a 2.x or 3.x verification response into LicenseEntitlements

    The old keys are renamed to the 5.0 keys and parsed like a 5.0 license,
    so a missing or wrong value gets the same default and warning.
    """
    if not isinstance(raw, dict):
        raise TypeError("wrong verification response type: %r" % type(raw))
    protocol_version = parse_verification_response_version(raw)
    if not isinstance(payload := raw.get("payload"), dict):
        raise TypeError("wrong payload type: %r" % type(payload))

    return LicenseEntitlements.model_validate(
        {
            "checkmk_edition": payload.get("checkmk_edition"),
            "operational_state": payload.get("operational_state"),
            "unbound_license": payload.get("unbound_license"),
            "subscription_start_ts_sec": payload.get("subscription_start_ts"),
            "subscription_expiration_ts_sec": payload.get("subscription_expiration_ts"),
            "subscription_auto_renewal": payload.get("subscription_auto_renewal"),
            "reseller_name": payload.get("reseller_name"),
            "group_and_managed_services_use": payload.get("group_and_managed_services_use"),
            **_by_version(protocol_version, payload),
        }
    )


def _by_version(
    protocol_version: AllowedVerificationResponseVersions, payload: dict[str, object]
) -> dict[str, object]:
    """The values that differ per version: limits, grace period, recurrence unit and features"""
    match protocol_version:
        case "1.0" | "1.1" | "1.2" | "1.3" | "1.4" | "1.5":
            raise ValueError(
                f"Unsupported protocol version for the license entitlements: {protocol_version!r}"
            )
        case "2.0" | "2.1":
            limits = payload.get("limits")
            service_limit = limits.get("services") if isinstance(limits, dict) else None
            return {
                "service_limit": service_limit,
                # no separate metric series limit before 3.2, use the service limit
                "active_metric_series_limit": service_limit,
                "grace_period_after_expiration_sec": _DEFAULT_GRACE_PERIOD_AFTER_EXPIRATION_SEC,
                "subscription_recurrence_unit": _DEFAULT_SUBSCRIPTION_RECURRENCE_UNIT,
                **_features_v2(payload.get("additional_features")),
            }
        case "3.0" | "3.1":
            return {
                "service_limit": payload.get("service_limit"),
                # no separate metric series limit before 3.2, use the service limit
                "active_metric_series_limit": payload.get("service_limit"),
                "grace_period_after_expiration_sec": _DEFAULT_GRACE_PERIOD_AFTER_EXPIRATION_SEC,
                "subscription_recurrence_unit": _DEFAULT_SUBSCRIPTION_RECURRENCE_UNIT,
                **_features_v3(payload.get("additional_features")),
            }
        case "3.2":
            return {
                "service_limit": payload.get("service_limit"),
                "active_metric_series_limit": payload.get("active_metric_series_limit"),
                "grace_period_after_expiration_sec": payload.get("grace_period_after_expiration"),
                "subscription_recurrence_unit": payload.get("subscription_recurrence_unit"),
                **_features_v3(payload.get("additional_features")),
            }


def _features_v2(raw: object) -> dict[str, object]:
    """Turn the feature list of a 2.x response into the 5.0 feature keys"""
    if not isinstance(raw, list):
        return {}  # each feature key then gets its default and a warning
    return {
        "ntop/enabled": "ntop" in raw,
        "virt1_appliance/enabled": "virt1_appliance" in raw,
        # 2.x has no synthetic monitoring
        "synthetic_monitoring/enabled": False,
        "synthetic_monitoring/limit": 0,
    }


def _features_v3(raw: object) -> dict[str, object]:
    """Turn the feature list of a 3.x response into the 5.0 feature keys"""
    if not isinstance(raw, list):
        return {}  # each feature key then gets its default and a warning
    features: dict[str, object] = {
        "ntop/enabled": False,
        "virt1_appliance/enabled": False,
        "synthetic_monitoring/enabled": False,
        "synthetic_monitoring/limit": 0,
    }
    for entry in raw:
        if not isinstance(entry, dict):
            continue
        match name := entry.get("name"):
            case "ntop" | "virt1_appliance":
                features[f"{name}/enabled"] = entry.get("enabled")
            case "synthetic_monitoring":
                features["synthetic_monitoring/enabled"] = entry.get("enabled")
                features["synthetic_monitoring/limit"] = entry.get("limit")
            case _:
                pass  # unknown features are ignored
    return features
