#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging

import pytest
from pydantic import ValidationError

from cmk.licensing.basics.protocol_version import AllowedVerificationResponseVersions
from cmk.licensing.entitlements import (
    entitlements_from_old_response,
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

# The value each key gets when it is missing or wrong
_DEFAULTS = {
    "checkmk_edition": LicenseEdition.unknown,
    "operational_state": LicenseOperationalState.unknown,
    "service_limit": 0,
    "active_metric_series_limit": 0,
    "unbound_license": False,
    "subscription_start_ts_sec": 0,
    "subscription_expiration_ts_sec": 0,
    "subscription_auto_renewal": False,
    "subscription_recurrence_unit": "yearly",
    "grace_period_after_expiration_sec": 2592000,
    "reseller_name": "",
    "group_and_managed_services_use": False,
    "ntop/enabled": False,
    "virt1_appliance/enabled": False,
    "synthetic_monitoring/enabled": False,
    "synthetic_monitoring/limit": 0,
}


def test_parse_all_keys(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.WARNING):
        entitlements = LicenseEntitlements.model_validate(_RAW_5_0)

    assert not caplog.records
    assert entitlements.model_extra == {}
    assert entitlements.model_dump(by_alias=True) == _RAW_5_0
    assert entitlements.checkmk_edition is LicenseEdition.cce
    assert entitlements.operational_state is LicenseOperationalState.active
    assert entitlements.ntop_enabled is True
    assert entitlements.synthetic_monitoring_limit == 100


def test_valid_empty_values_are_not_missing(caplog: pytest.LogCaptureFixture) -> None:
    raw = {
        "checkmk_edition": "cee",
        "operational_state": "suspended",
        "service_limit": 0,
        "active_metric_series_limit": 0,
        "unbound_license": False,
        "subscription_start_ts_sec": 0,
        "subscription_expiration_ts_sec": 0,
        "subscription_auto_renewal": False,
        "subscription_recurrence_unit": "",
        "grace_period_after_expiration_sec": 0,
        "reseller_name": "",
        "group_and_managed_services_use": False,
        "ntop/enabled": False,
        "virt1_appliance/enabled": False,
        "synthetic_monitoring/enabled": False,
        "synthetic_monitoring/limit": 0,
    }

    with caplog.at_level(logging.WARNING):
        entitlements = LicenseEntitlements.model_validate(raw)

    assert not caplog.records
    assert entitlements.model_dump(by_alias=True) == raw


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
def test_limit_below_unlimited_gets_default(key: str, caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.WARNING):
        entitlements = LicenseEntitlements.model_validate({**_RAW_5_0, key: -2})

    assert entitlements.model_dump(by_alias=True)[key] == 0
    assert [r.getMessage() for r in caplog.records] == [
        f"License entitlement value for {key!r} is invalid, using its default"
    ]


def test_extra_keys_are_kept(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.WARNING):
        entitlements = LicenseEntitlements.model_validate(
            {**_RAW_5_0, "netflow/collector_limit": 123, "future/not_configured_yet": None}
        )
    assert entitlements.model_extra == {
        "netflow/collector_limit": 123,
        "future/not_configured_yet": None,
    }
    assert not caplog.records


@pytest.mark.parametrize("key", list(_RAW_5_0))
def test_missing_key_gets_default(key: str, caplog: pytest.LogCaptureFixture) -> None:
    raw = {k: v for k, v in _RAW_5_0.items() if k != key}

    with caplog.at_level(logging.WARNING):
        entitlements = LicenseEntitlements.model_validate(raw)

    assert entitlements.model_dump(by_alias=True)[key] == _DEFAULTS[key]
    assert [r.getMessage() for r in caplog.records] == [
        f"License entitlement {key!r} is missing, using its default"
    ]
    assert [r.name for r in caplog.records] == ["cmk.licensing"]


@pytest.mark.parametrize("key", list(_RAW_5_0))
def test_null_gets_default(key: str, caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.WARNING):
        entitlements = LicenseEntitlements.model_validate({**_RAW_5_0, key: None})

    assert entitlements.model_dump(by_alias=True)[key] == _DEFAULTS[key]
    assert entitlements.model_extra == {}
    assert [r.getMessage() for r in caplog.records] == [
        f"License entitlement {key!r} is missing, using its default"
    ]
    assert [r.name for r in caplog.records] == ["cmk.licensing"]


def test_empty_object_gets_all_defaults(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.WARNING):
        entitlements = LicenseEntitlements.model_validate({})

    assert entitlements.model_dump(by_alias=True) == _DEFAULTS
    assert len(caplog.records) == len(_DEFAULTS)


def test_not_an_object_is_rejected(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.WARNING), pytest.raises(ValidationError):
        LicenseEntitlements.model_validate([])

    assert not caplog.records


@pytest.mark.parametrize(
    "key, value",
    [
        pytest.param("service_limit", True, id="bool is not a number"),
        pytest.param("active_metric_series_limit", "123", id="string is not a number"),
        pytest.param("synthetic_monitoring/limit", 1.5, id="float is not an integer"),
        pytest.param("subscription_start_ts_sec", 1.0, id="float timestamp"),
        pytest.param("subscription_expiration_ts_sec", "1806278400", id="string timestamp"),
        pytest.param("grace_period_after_expiration_sec", False, id="bool grace period"),
        pytest.param("unbound_license", 1, id="number is not a bool"),
        pytest.param("subscription_auto_renewal", "maybe", id="string auto renewal"),
        pytest.param("group_and_managed_services_use", 2, id="number group use"),
        pytest.param("ntop/enabled", "true", id="string is not a bool"),
        pytest.param("virt1_appliance/enabled", "maybe", id="string virt1 appliance"),
        pytest.param("synthetic_monitoring/enabled", 2, id="number synthetic monitoring"),
        pytest.param("reseller_name", 123, id="number is not a text"),
        pytest.param("subscription_recurrence_unit", ["yearly"], id="list is not a text"),
        pytest.param("checkmk_edition", 1, id="number is not an edition"),
        pytest.param("operational_state", {}, id="object is not a state"),
    ],
)
def test_wrong_value_gets_default(
    key: str, value: object, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level(logging.WARNING):
        entitlements = LicenseEntitlements.model_validate({**_RAW_5_0, key: value})

    assert entitlements.model_dump(by_alias=True)[key] == _DEFAULTS[key]
    assert [r.getMessage() for r in caplog.records] == [
        f"License entitlement value for {key!r} is invalid, using its default"
    ]
    assert [r.name for r in caplog.records] == ["cmk.licensing"]


def test_unknown_edition(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.WARNING):
        entitlements = LicenseEntitlements.model_validate({**_RAW_5_0, "checkmk_edition": "cre"})

    assert entitlements.checkmk_edition is LicenseEdition.unknown
    assert [r.getMessage() for r in caplog.records] == [
        "License entitlement value for 'checkmk_edition' is invalid, using its default"
    ]


def test_unknown_operational_state(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.WARNING):
        entitlements = LicenseEntitlements.model_validate(
            {**_RAW_5_0, "operational_state": "terminated"}
        )

    assert entitlements.operational_state is LicenseOperationalState.unknown
    assert [r.getMessage() for r in caplog.records] == [
        "License entitlement value for 'operational_state' is invalid, using its default"
    ]


def test_warning_does_not_contain_value(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.WARNING):
        LicenseEntitlements.model_validate({**_RAW_5_0, "reseller_name": 987654321})

    assert "987654321" not in caplog.text


# The payload values that are the same in all old versions
_OLD_COMMON = {
    "status": "successful",
    "message": "",
    "checkmk_edition": "cce",
    "checkmk_max_version": "2.5.0",
    "operational_state": "active",
    "unbound_license": True,
    "subscription_start_ts": 1774742400,
    "subscription_expiration_ts": 1806278400,
    "subscription_auto_renewal": True,
    "reseller_name": "reseller",
    "group_and_managed_services_use": True,
}

_OLD_FEATURES = [
    {"name": "ntop", "enabled": True},
    {"name": "virt1_appliance", "enabled": True},
    {"name": "synthetic_monitoring", "enabled": True, "limit": 100},
]

# A complete payload per old format
_OLD_PAYLOADS: dict[AllowedVerificationResponseVersions, dict[str, object]] = {
    "2.0": {
        **_OLD_COMMON,
        "limits": {"services": 1000},
        "additional_features": ["ntop", "virt1_appliance"],
    },
    "3.0": {**_OLD_COMMON, "service_limit": 1000, "additional_features": _OLD_FEATURES},
    "3.2": {
        **_OLD_COMMON,
        "service_limit": 1000,
        "active_metric_series_limit": 2000,
        "grace_period_after_expiration": 1209600,
        "subscription_recurrence_unit": "monthly",
        "additional_features": _OLD_FEATURES,
    },
}

# Which payload format each old version uses
_OLD_FORMATS: dict[AllowedVerificationResponseVersions, AllowedVerificationResponseVersions] = {
    "2.0": "2.0",
    "2.1": "2.0",
    "3.0": "3.0",
    "3.1": "3.0",
    "3.2": "3.2",
}

# The entitlements that are the same for all old payloads above
_OLD_EXPECTED = {
    "checkmk_edition": "cce",
    "operational_state": "active",
    "service_limit": 1000,
    "unbound_license": True,
    "subscription_start_ts_sec": 1774742400,
    "subscription_expiration_ts_sec": 1806278400,
    "subscription_auto_renewal": True,
    "reseller_name": "reseller",
    "group_and_managed_services_use": True,
    "ntop/enabled": True,
    "virt1_appliance/enabled": True,
    "synthetic_monitoring/enabled": True,
    "synthetic_monitoring/limit": 100,
}


def _old_response(
    version: AllowedVerificationResponseVersions, **payload: object
) -> dict[str, object]:
    return {
        "VERSION": version,
        "request_id": "e26038ce-e340-46a3-868d-ab28fac4b7ab",
        "payload": {**_OLD_PAYLOADS[_OLD_FORMATS[version]], **payload},
    }


@pytest.mark.parametrize(
    "version, expected",
    [
        pytest.param(
            "2.0",
            {
                **_OLD_EXPECTED,
                "active_metric_series_limit": 1000,
                "grace_period_after_expiration_sec": 2592000,
                "subscription_recurrence_unit": "yearly",
                "synthetic_monitoring/enabled": False,
                "synthetic_monitoring/limit": 0,
            },
            id="2.0",
        ),
        pytest.param(
            "3.0",
            {
                **_OLD_EXPECTED,
                "active_metric_series_limit": 1000,
                "grace_period_after_expiration_sec": 2592000,
                "subscription_recurrence_unit": "yearly",
            },
            id="3.0",
        ),
        pytest.param(
            "3.2",
            {
                **_OLD_EXPECTED,
                "active_metric_series_limit": 2000,
                "grace_period_after_expiration_sec": 1209600,
                "subscription_recurrence_unit": "monthly",
            },
            id="3.2",
        ),
    ],
)
def test_old_response(
    version: AllowedVerificationResponseVersions,
    expected: dict[str, object],
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.WARNING):
        entitlements = entitlements_from_old_response(_old_response(version))

    assert not caplog.records
    assert entitlements.model_extra == {}
    assert entitlements.model_dump(by_alias=True) == expected


@pytest.mark.parametrize("version", list(_OLD_FORMATS))
def test_old_response_unknown_edition_and_state(
    version: AllowedVerificationResponseVersions, caplog: pytest.LogCaptureFixture
) -> None:
    raw = _old_response(version, checkmk_edition="cre", operational_state="terminated")

    with caplog.at_level(logging.WARNING):
        entitlements = entitlements_from_old_response(raw)

    assert entitlements.checkmk_edition is LicenseEdition.unknown
    assert entitlements.operational_state is LicenseOperationalState.unknown
    assert [r.getMessage() for r in caplog.records] == [
        "License entitlement value for 'checkmk_edition' is invalid, using its default",
        "License entitlement value for 'operational_state' is invalid, using its default",
    ]


@pytest.mark.parametrize("version", list(_OLD_FORMATS))
@pytest.mark.parametrize(
    "old_key, key",
    [
        pytest.param("checkmk_edition", "checkmk_edition", id="edition"),
        pytest.param("subscription_start_ts", "subscription_start_ts_sec", id="start"),
        pytest.param(
            "subscription_expiration_ts", "subscription_expiration_ts_sec", id="expiration"
        ),
        pytest.param("reseller_name", "reseller_name", id="reseller"),
    ],
)
def test_old_response_missing_value_gets_default(
    version: AllowedVerificationResponseVersions,
    old_key: str,
    key: str,
    caplog: pytest.LogCaptureFixture,
) -> None:
    raw = _old_response(version, **{old_key: None})

    with caplog.at_level(logging.WARNING):
        entitlements = entitlements_from_old_response(raw)

    assert entitlements.model_dump(by_alias=True)[key] == _DEFAULTS[key]
    assert [r.getMessage() for r in caplog.records] == [
        f"License entitlement {key!r} is missing, using its default"
    ]


# In 2.x and 3.0/3.1 one value is used for both limits, so a wrong value affects both.
_BOTH_LIMITS = ("service_limit", "active_metric_series_limit")


@pytest.mark.parametrize(
    "version, payload, keys",
    [
        pytest.param(
            "2.0", {"limits": {"services": "1000"}}, _BOTH_LIMITS, id="2.0 limit is a string"
        ),
        pytest.param("2.0", {"limits": []}, _BOTH_LIMITS, id="2.0 limits is not an object"),
        pytest.param("3.0", {"service_limit": -2}, _BOTH_LIMITS, id="3.0 limit below -1"),
        pytest.param(
            "3.2",
            {"active_metric_series_limit": True},
            ("active_metric_series_limit",),
            id="3.2 metric series limit is a bool",
        ),
        pytest.param(
            "3.2",
            {"grace_period_after_expiration": "30d"},
            ("grace_period_after_expiration_sec",),
            id="3.2 grace period is a string",
        ),
        pytest.param(
            "3.2",
            {"unbound_license": "maybe"},
            ("unbound_license",),
            id="3.2 unbound license is not a bool",
        ),
        pytest.param(
            "3.2",
            {
                "additional_features": [
                    {"name": "synthetic_monitoring", "enabled": True, "limit": -5}
                ]
            },
            ("synthetic_monitoring/limit",),
            id="3.2 synthetic monitoring limit below -1",
        ),
    ],
)
def test_old_response_wrong_value_gets_default(
    version: AllowedVerificationResponseVersions,
    payload: dict[str, object],
    keys: tuple[str, ...],
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.WARNING):
        entitlements = entitlements_from_old_response(_old_response(version, **payload))

    dump = entitlements.model_dump(by_alias=True)
    assert {k: dump[k] for k in keys} == {k: _DEFAULTS[k] for k in keys}
    assert len(caplog.records) == len(keys)
    assert all(repr(k) in caplog.text for k in keys)


@pytest.mark.parametrize(
    "version, features",
    [
        pytest.param("2.0", ["ntop"], id="2.0"),
        pytest.param("2.1", ["ntop"], id="2.1"),
        pytest.param("3.0", [{"name": "ntop", "enabled": True}], id="3.0"),
        pytest.param("3.1", [{"name": "ntop", "enabled": True}], id="3.1"),
        pytest.param("3.2", [{"name": "ntop", "enabled": True}], id="3.2"),
    ],
)
def test_old_response_feature_without_entry_is_disabled(
    version: AllowedVerificationResponseVersions,
    features: list[object],
    caplog: pytest.LogCaptureFixture,
) -> None:
    raw = _old_response(version, additional_features=features)

    with caplog.at_level(logging.WARNING):
        entitlements = entitlements_from_old_response(raw)

    assert entitlements.ntop_enabled is True
    assert entitlements.virt1_appliance_enabled is False
    assert entitlements.synthetic_monitoring_enabled is False
    assert entitlements.synthetic_monitoring_limit == 0
    assert not caplog.records


@pytest.mark.parametrize(
    "version, features",
    [
        pytest.param("2.0", ["ntop", "netflow"], id="2.0"),
        pytest.param(
            "3.2",
            [{"name": "ntop", "enabled": True}, {"name": "netflow"}, "not an entry"],
            id="3.2",
        ),
    ],
)
def test_old_response_unknown_feature_is_ignored(
    version: AllowedVerificationResponseVersions,
    features: list[object],
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.WARNING):
        entitlements = entitlements_from_old_response(
            _old_response(version, additional_features=features)
        )

    assert entitlements.ntop_enabled is True
    assert entitlements.model_extra == {}
    assert not caplog.records


@pytest.mark.parametrize("version", ["2.0", "3.2"])
def test_old_response_features_not_a_list(
    version: AllowedVerificationResponseVersions, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level(logging.WARNING):
        entitlements = entitlements_from_old_response(
            _old_response(version, additional_features=None)
        )

    assert not entitlements.ntop_enabled
    assert not entitlements.synthetic_monitoring_enabled
    assert len(caplog.records) == 4


@pytest.mark.parametrize("version", ["1.0", "1.5", "0.9"])
def test_old_response_unsupported_version(version: str) -> None:
    with pytest.raises(ValueError):
        entitlements_from_old_response({"VERSION": version, "payload": {}})


@pytest.mark.parametrize(
    "raw",
    [
        None,
        [],
        {"VERSION": 2, "payload": None},
        {"VERSION": "3.2", "payload": None},
        {"VERSION": "3.2", "payload": []},
    ],
)
def test_old_response_not_an_object(raw: object) -> None:
    with pytest.raises(TypeError):
        entitlements_from_old_response(raw)
