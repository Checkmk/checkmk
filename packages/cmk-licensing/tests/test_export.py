#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="explicit-any"
# mypy: disable-error-code="type-arg"

from collections.abc import Mapping
from dataclasses import replace
from typing import Final, get_args, Literal
from uuid import UUID

import pytest

from cmk.licensing.basics.protocol_version import AllowedUsageHistoryVersions
from cmk.licensing.export import (
    _parse_extensions,
    LicenseUsageSample,
    make_sample_parser,
    RawSubscriptionDetailsForAggregation,
    SubscriptionDetailsForAggregation,
)

_GIVEN_INSTANCE_ID: Final = UUID("11111111-1111-1111-1111-111111111111")
_SAMPLE_INSTANCE_ID: Final = UUID("22222222-2222-2222-2222-222222222222")


def _without(raw_sample: Mapping[str, object], key: str) -> dict[str, object]:
    return {k: v for k, v in raw_sample.items() if k != key}


_RAW_SAMPLE_V1_0: Final[Mapping[str, object]] = {
    "site_hash": "sample-site-hash",
    "version": "2.5.0p1",
    "edition": "ultimate",
    "platform": "Ubuntu 24.04",
    "is_cma": False,
    "sample_time": 1700000000,
    "timezone": "UTC",
    "num_hosts": 1,
    "num_services": 6,
}
_RAW_SAMPLE_V1_1: Final = {
    **_RAW_SAMPLE_V1_0,
    "num_hosts_excluded": 5,
    "num_services_excluded": 9,
    "extensions": {"ntop": True},
}
_RAW_SAMPLE_V1_4: Final = {**_RAW_SAMPLE_V1_1, "num_shadow_hosts": 4}
_RAW_SAMPLE_V1_5: Final = {**_RAW_SAMPLE_V1_4, "instance_id": str(_SAMPLE_INSTANCE_ID)}
_RAW_SAMPLE_V2_0: Final = {
    **_without(_RAW_SAMPLE_V1_1, "extensions"),
    "instance_id": str(_SAMPLE_INSTANCE_ID),
    "num_hosts_cloud": 2,
    "num_hosts_shadow": 3,
    "num_services_cloud": 7,
    "num_services_shadow": 8,
    "extension_ntop": True,
}
_RAW_SAMPLE_V3_0: Final = {
    **_RAW_SAMPLE_V2_0,
    "num_synthetic_tests": 10,
    "num_synthetic_tests_excluded": 11,
}
_RAW_SAMPLE_V3_1: Final = {
    **_RAW_SAMPLE_V3_0,
    "num_synthetic_kpis": 12,
    "num_synthetic_kpis_excluded": 13,
}
_RAW_SAMPLE_V3_2: Final = {**_RAW_SAMPLE_V3_1, "num_active_metric_series": 14}
_RAW_SAMPLE: Final = {**_RAW_SAMPLE_V3_2, "num_shadow_hosts": 4, "unknown_key": "unknown"}

_RAW_SAMPLES: Final[Mapping[AllowedUsageHistoryVersions, Mapping[str, object]]] = {
    "1.0": _RAW_SAMPLE_V1_0,
    "1.1": _RAW_SAMPLE_V1_1,
    "1.2": _RAW_SAMPLE_V1_1,
    "1.3": _RAW_SAMPLE_V1_1,
    "1.4": _RAW_SAMPLE_V1_4,
    "1.5": _RAW_SAMPLE_V1_5,
    "2.0": _RAW_SAMPLE_V2_0,
    "2.1": _RAW_SAMPLE_V2_0,
    "3.0": _RAW_SAMPLE_V3_0,
    "3.1": _RAW_SAMPLE_V3_1,
    "3.2": _RAW_SAMPLE_V3_2,
}
_KEYS_NOT_RAISING_KEY_ERROR: Final = {"instance_id", "site_hash", "extensions", "extension_ntop"}

_SAMPLE_WITHOUT_COUNTERS: Final = LicenseUsageSample(
    instance_id=_GIVEN_INSTANCE_ID,
    site_hash="sample-site-hash",
    version="2.5.0p1",
    edition="ultimate",
    platform="Ubuntu 24.04",
    is_cma=False,
    sample_time=1700000000,
    timezone="UTC",
    num_hosts=0,
    num_hosts_cloud=0,
    num_hosts_shadow=0,
    num_hosts_excluded=0,
    num_services=0,
    num_services_cloud=0,
    num_services_shadow=0,
    num_services_excluded=0,
    num_synthetic_tests=0,
    num_synthetic_tests_excluded=0,
    num_synthetic_kpis=0,
    num_synthetic_kpis_excluded=0,
    num_active_metric_series=0,
    extension_ntop=True,
)

_SAMPLE_V1_0: Final = replace(
    _SAMPLE_WITHOUT_COUNTERS, num_hosts=1, num_services=6, extension_ntop=False
)
_SAMPLE_V1_1: Final = replace(
    _SAMPLE_WITHOUT_COUNTERS,
    num_hosts=1,
    num_hosts_excluded=5,
    num_services=6,
    num_services_excluded=9,
)
_SAMPLE_V1_4: Final = replace(
    _SAMPLE_WITHOUT_COUNTERS,
    num_hosts=1,
    num_hosts_shadow=4,
    num_hosts_excluded=5,
    num_services=6,
    num_services_excluded=9,
)
_SAMPLE_V1_5: Final = replace(
    _SAMPLE_WITHOUT_COUNTERS,
    instance_id=_SAMPLE_INSTANCE_ID,
    num_hosts=1,
    num_hosts_shadow=4,
    num_hosts_excluded=5,
    num_services=6,
    num_services_excluded=9,
)
_SAMPLE_V2_0: Final = replace(
    _SAMPLE_WITHOUT_COUNTERS,
    instance_id=_SAMPLE_INSTANCE_ID,
    num_hosts=1,
    num_hosts_cloud=2,
    num_hosts_shadow=3,
    num_hosts_excluded=5,
    num_services=6,
    num_services_cloud=7,
    num_services_shadow=8,
    num_services_excluded=9,
)
_SAMPLE_V3_0: Final = replace(
    _SAMPLE_WITHOUT_COUNTERS,
    instance_id=_SAMPLE_INSTANCE_ID,
    num_hosts=1,
    num_hosts_cloud=2,
    num_hosts_shadow=3,
    num_hosts_excluded=5,
    num_services=6,
    num_services_cloud=7,
    num_services_shadow=8,
    num_services_excluded=9,
    num_synthetic_tests=10,
    num_synthetic_tests_excluded=11,
)
_SAMPLE_V3_1: Final = replace(
    _SAMPLE_WITHOUT_COUNTERS,
    instance_id=_SAMPLE_INSTANCE_ID,
    num_hosts=1,
    num_hosts_cloud=2,
    num_hosts_shadow=3,
    num_hosts_excluded=5,
    num_services=6,
    num_services_cloud=7,
    num_services_shadow=8,
    num_services_excluded=9,
    num_synthetic_tests=10,
    num_synthetic_tests_excluded=11,
    num_synthetic_kpis=12,
    num_synthetic_kpis_excluded=13,
)
_SAMPLE_V3_2: Final = replace(
    _SAMPLE_WITHOUT_COUNTERS,
    instance_id=_SAMPLE_INSTANCE_ID,
    num_hosts=1,
    num_hosts_cloud=2,
    num_hosts_shadow=3,
    num_hosts_excluded=5,
    num_services=6,
    num_services_cloud=7,
    num_services_shadow=8,
    num_services_excluded=9,
    num_synthetic_tests=10,
    num_synthetic_tests_excluded=11,
    num_synthetic_kpis=12,
    num_synthetic_kpis_excluded=13,
    num_active_metric_series=14,
)

_VERSIONS_WITHOUT_INSTANCE_ID_IN_SAMPLE: Final = ["1.0", "1.1", "1.2", "1.3", "1.4"]
_VERSIONS_WITH_INSTANCE_ID_IN_SAMPLE: Final = ["1.5", "2.0", "2.1", "3.0", "3.1", "3.2"]


@pytest.mark.parametrize(
    "raw_sample, expected_ntop_enabled",
    [
        pytest.param(
            {
                "instance_id": "",
                "site_hash": "",
                "version": "",
                "edition": "",
                "platform": "",
                "is_cma": False,
                "sample_time": 0,
                "timezone": "",
                "num_hosts": 0,
                "num_hosts_cloud": 0,
                "num_hosts_shadow": 0,
                "num_hosts_excluded": 0,
                "num_services": 0,
                "num_services_cloud": 0,
                "num_services_shadow": 0,
                "num_services_excluded": 0,
                "extension_ntop": True,
            },
            True,
            id="new format ntop enabled",
        ),
        pytest.param(
            {
                "instance_id": "",
                "site_hash": "",
                "version": "",
                "edition": "",
                "platform": "",
                "is_cma": False,
                "sample_time": 0,
                "timezone": "",
                "num_hosts": 0,
                "num_hosts_cloud": 0,
                "num_hosts_shadow": 0,
                "num_hosts_excluded": 0,
                "num_services": 0,
                "num_services_cloud": 0,
                "num_services_shadow": 0,
                "num_services_excluded": 0,
                "extension_ntop": False,
            },
            False,
            id="new format ntop disabled",
        ),
        pytest.param(
            {
                "version": "",
                "edition": "",
                "platform": "",
                "is_cma": False,
                "sample_time": 0,
                "timezone": "",
                "num_hosts": 0,
                "num_hosts_excluded": 0,
                "num_services": 0,
                "num_services_excluded": 0,
                "extensions": {"ntop": True},
            },
            True,
            id="old format ntop enabled",
        ),
        pytest.param(
            {
                "version": "",
                "edition": "",
                "platform": "",
                "is_cma": False,
                "sample_time": 0,
                "timezone": "",
                "num_hosts": 0,
                "num_hosts_excluded": 0,
                "num_services": 0,
                "num_services_excluded": 0,
                "extensions": {"ntop": False},
            },
            False,
            id="old format ntop disabled",
        ),
        pytest.param(
            {
                "version": "",
                "edition": "",
                "platform": "",
                "is_cma": False,
                "sample_time": 0,
                "timezone": "",
                "num_hosts": 0,
                "num_hosts_excluded": 0,
                "num_services": 0,
                "num_services_excluded": 0,
            },
            False,
            id="no extensions ntop disabled",
        ),
    ],
)
def test_LicenseUsageExtensions_parse_from_sample(  # type: ignore[misc]
    raw_sample: dict, expected_ntop_enabled: bool
) -> None:
    extensions = _parse_extensions(raw_sample)
    assert extensions.ntop is expected_ntop_enabled


@pytest.mark.parametrize(
    "protocol_version, expected_sample",
    [
        # Extensions are parsed regardless of the protocol version.
        pytest.param("1.0", replace(_SAMPLE_V1_0, extension_ntop=True), id="1.0"),
        pytest.param("1.1", _SAMPLE_V1_1, id="1.1"),
        pytest.param("1.2", _SAMPLE_V1_1, id="1.2"),
        pytest.param("1.3", _SAMPLE_V1_1, id="1.3"),
        pytest.param("1.4", _SAMPLE_V1_4, id="1.4"),
        pytest.param("1.5", _SAMPLE_V1_5, id="1.5"),
        pytest.param("2.0", _SAMPLE_V2_0, id="2.0"),
        pytest.param("2.1", _SAMPLE_V2_0, id="2.1"),
        pytest.param("3.0", _SAMPLE_V3_0, id="3.0"),
        pytest.param("3.1", _SAMPLE_V3_1, id="3.1"),
        pytest.param("3.2", _SAMPLE_V3_2, id="3.2"),
    ],
)
def test_sample_ignores_keys_not_of_its_protocol_version(
    protocol_version: AllowedUsageHistoryVersions, expected_sample: LicenseUsageSample
) -> None:
    sample = make_sample_parser(protocol_version).parse_sample(
        _GIVEN_INSTANCE_ID, "given-site-hash", dict(_RAW_SAMPLE)
    )

    assert sample == expected_sample


@pytest.mark.parametrize(
    "protocol_version, raw_sample, expected_sample",
    [
        pytest.param("1.0", _RAW_SAMPLE_V1_0, _SAMPLE_V1_0, id="1.0"),
        pytest.param("1.1", _RAW_SAMPLE_V1_1, _SAMPLE_V1_1, id="1.1"),
        pytest.param("1.2", _RAW_SAMPLE_V1_1, _SAMPLE_V1_1, id="1.2"),
        pytest.param("1.3", _RAW_SAMPLE_V1_1, _SAMPLE_V1_1, id="1.3"),
        pytest.param("1.4", _RAW_SAMPLE_V1_4, _SAMPLE_V1_4, id="1.4"),
        pytest.param("1.5", _RAW_SAMPLE_V1_5, _SAMPLE_V1_5, id="1.5"),
        pytest.param("2.0", _RAW_SAMPLE_V2_0, _SAMPLE_V2_0, id="2.0"),
        pytest.param("2.1", _RAW_SAMPLE_V2_0, _SAMPLE_V2_0, id="2.1"),
        pytest.param("3.0", _RAW_SAMPLE_V3_0, _SAMPLE_V3_0, id="3.0"),
        pytest.param("3.1", _RAW_SAMPLE_V3_1, _SAMPLE_V3_1, id="3.1"),
        pytest.param("3.2", _RAW_SAMPLE_V3_2, _SAMPLE_V3_2, id="3.2"),
    ],
)
def test_sample_without_counters_of_later_versions_gets_them_as_0(
    protocol_version: AllowedUsageHistoryVersions,
    raw_sample: Mapping[str, object],
    expected_sample: LicenseUsageSample,
) -> None:
    sample = make_sample_parser(protocol_version).parse_sample(
        _GIVEN_INSTANCE_ID, "given-site-hash", dict(raw_sample)
    )

    assert sample == expected_sample


@pytest.mark.parametrize(
    "protocol_version, missing_key",
    [
        pytest.param(protocol_version, key, id=f"{protocol_version}-{key}")
        for protocol_version, raw_sample in _RAW_SAMPLES.items()
        for key in raw_sample
        if key not in _KEYS_NOT_RAISING_KEY_ERROR
    ],
)
def test_sample_missing_a_required_key_of_its_protocol_version_is_rejected(
    protocol_version: AllowedUsageHistoryVersions, missing_key: str
) -> None:
    parser = make_sample_parser(protocol_version)
    raw_sample = _without(_RAW_SAMPLES[protocol_version], missing_key)

    with pytest.raises(KeyError):
        parser.parse_sample(_GIVEN_INSTANCE_ID, "given-site-hash", raw_sample)


@pytest.mark.parametrize("protocol_version", get_args(AllowedUsageHistoryVersions))
def test_sample_without_site_hash_gets_the_given_one(
    protocol_version: AllowedUsageHistoryVersions,
) -> None:
    sample = make_sample_parser(protocol_version).parse_sample(
        _GIVEN_INSTANCE_ID, "given-site-hash", _without(_RAW_SAMPLE, "site_hash")
    )

    assert sample.site_hash == "given-site-hash"


@pytest.mark.parametrize("protocol_version", get_args(AllowedUsageHistoryVersions))
def test_sample_without_any_site_hash_is_rejected(
    protocol_version: AllowedUsageHistoryVersions,
) -> None:
    parser = make_sample_parser(protocol_version)

    with pytest.raises(ValueError):
        parser.parse_sample(_GIVEN_INSTANCE_ID, "", _without(_RAW_SAMPLE, "site_hash"))


@pytest.mark.parametrize("protocol_version", get_args(AllowedUsageHistoryVersions))
def test_sample_with_empty_site_hash_is_rejected_despite_the_given_one(
    protocol_version: AllowedUsageHistoryVersions,
) -> None:
    parser = make_sample_parser(protocol_version)

    with pytest.raises(ValueError):
        parser.parse_sample(_GIVEN_INSTANCE_ID, "given-site-hash", {**_RAW_SAMPLE, "site_hash": ""})


@pytest.mark.parametrize("protocol_version", _VERSIONS_WITHOUT_INSTANCE_ID_IN_SAMPLE)
def test_sample_before_1_5_without_given_instance_id_has_none(
    protocol_version: AllowedUsageHistoryVersions,
) -> None:
    sample = make_sample_parser(protocol_version).parse_sample(
        None, "given-site-hash", dict(_RAW_SAMPLE)
    )

    assert sample.instance_id is None


@pytest.mark.parametrize("protocol_version", _VERSIONS_WITHOUT_INSTANCE_ID_IN_SAMPLE)
def test_sample_before_1_5_ignores_a_malformed_instance_id(
    protocol_version: AllowedUsageHistoryVersions,
) -> None:
    sample = make_sample_parser(protocol_version).parse_sample(
        _GIVEN_INSTANCE_ID, "given-site-hash", {**_RAW_SAMPLE, "instance_id": "not-a-uuid"}
    )

    assert sample.instance_id == _GIVEN_INSTANCE_ID


@pytest.mark.parametrize("protocol_version", _VERSIONS_WITH_INSTANCE_ID_IN_SAMPLE)
def test_sample_without_instance_id_is_rejected(
    protocol_version: AllowedUsageHistoryVersions,
) -> None:
    parser = make_sample_parser(protocol_version)

    with pytest.raises(ValueError):
        parser.parse_sample(
            _GIVEN_INSTANCE_ID, "given-site-hash", _without(_RAW_SAMPLE, "instance_id")
        )


@pytest.mark.parametrize("protocol_version", _VERSIONS_WITH_INSTANCE_ID_IN_SAMPLE)
def test_sample_with_malformed_instance_id_is_rejected(
    protocol_version: AllowedUsageHistoryVersions,
) -> None:
    parser = make_sample_parser(protocol_version)

    with pytest.raises(ValueError):
        parser.parse_sample(
            _GIVEN_INSTANCE_ID, "given-site-hash", {**_RAW_SAMPLE, "instance_id": "not-a-uuid"}
        )


@pytest.mark.parametrize("protocol_version", get_args(AllowedUsageHistoryVersions))
def test_sample_that_is_not_a_dict_is_rejected(
    protocol_version: AllowedUsageHistoryVersions,
) -> None:
    parser = make_sample_parser(protocol_version)

    with pytest.raises(TypeError):
        parser.parse_sample(_GIVEN_INSTANCE_ID, "given-site-hash", list(_RAW_SAMPLE.items()))


@pytest.mark.parametrize("protocol_version", get_args(AllowedUsageHistoryVersions))
def test_sample_platform_is_cut_to_50_characters(
    protocol_version: AllowedUsageHistoryVersions,
) -> None:
    sample = make_sample_parser(protocol_version).parse_sample(
        _GIVEN_INSTANCE_ID, "given-site-hash", {**_RAW_SAMPLE, "platform": "p" * 60}
    )

    assert sample.platform == "p" * 50


@pytest.mark.parametrize(
    "limit",
    [
        pytest.param(0, id="zero"),
        pytest.param(-1, id="lt-zero"),
    ],
)
def test_subscription_details_for_aggregation_limit_error(limit: int) -> None:
    with pytest.raises(ValueError):
        SubscriptionDetailsForAggregation(None, None, limit)


@pytest.mark.parametrize(
    "start",
    [
        pytest.param(None, id="start-none"),
        pytest.param(0, id="start-int"),
        pytest.param(1, id="start-int"),
    ],
)
@pytest.mark.parametrize(
    "end",
    [
        pytest.param(None, id="end-none"),
        pytest.param(0, id="end-int"),
        pytest.param(1, id="end-int"),
    ],
)
@pytest.mark.parametrize(
    "limit, is_free, real_limit",
    [
        pytest.param(None, False, None, id="limit-none"),
        pytest.param("unlimited", False, None, id="unlimited"),
        pytest.param(("free", 3), True, 3, id="free"),
        pytest.param(1, False, 1, id="limit-int"),
    ],
)
def test_subscription_details_for_aggregation(
    start: int | None,
    end: int | None,
    limit: Literal["unlimited"] | tuple[Literal["free"], Literal[3]] | int | None,
    is_free: bool,
    real_limit: Literal["unlimited"] | int | None,
) -> None:
    subscription_details = SubscriptionDetailsForAggregation(start, end, limit)
    assert subscription_details.start == start
    assert subscription_details.end == end
    assert subscription_details.limit == limit
    assert subscription_details.is_free == is_free
    assert subscription_details.real_limit == real_limit


@pytest.mark.parametrize(
    "subscription_details, expected_report",
    [
        pytest.param(
            SubscriptionDetailsForAggregation(None, None, None),
            RawSubscriptionDetailsForAggregation(start=None, end=None, limit=None),
            id="all-none",
        ),
        pytest.param(
            SubscriptionDetailsForAggregation(0, 1, 2),
            RawSubscriptionDetailsForAggregation(start=0, end=1, limit=2),
            id="all-set",
        ),
        pytest.param(
            SubscriptionDetailsForAggregation(0, 1, "unlimited"),
            RawSubscriptionDetailsForAggregation(start=0, end=1, limit="unlimited"),
            id="unlimited",
        ),
        pytest.param(
            SubscriptionDetailsForAggregation(0, 1, ("free", 3)),
            RawSubscriptionDetailsForAggregation(start=0, end=1, limit=3),
            id="free",
        ),
    ],
)
def test_subscription_details_for_aggregation_for_report(
    subscription_details: SubscriptionDetailsForAggregation,
    expected_report: RawSubscriptionDetailsForAggregation,
) -> None:
    assert subscription_details.for_report() == expected_report
