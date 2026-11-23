# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import copy
import dataclasses
import re
import uuid

import pytest

from cmk.crypto import certificate
from cmk.licensing.basics import protocol_version, verification

STATIC_TEST_CERT_PEM = """-----BEGIN CERTIFICATE-----
MIIDvDCCAyWgAwIBAgIUHMeaXj2awEj4ECme5CrxDYHzxxUwDQYJKoZIhvcNAQEN
BQAwKDEMMAoGA1UEAwwDZm9vMRgwFgYDVQQKDA9DaGVja21rIFRlc3RpbmcwHhcN
MjUwNzAzMTQxMDU2WhcNMjcwNzAzMTQxMDU2WjAoMQwwCgYDVQQDDANmb28xGDAW
BgNVBAoMD0NoZWNrbWsgVGVzdGluZzCCAiIwDQYJKoZIhvcNAQEBBQADggIPADCC
AgoCggIBALLw6esK23awvG+fMF2WSg1vcGMW3t03yIFTnyQ9MYpRz+yv4BIdj4mY
NnNEo46EMOmfy/vg4W+2IKStIEphnAlq/tBe2/RRfthwqqPII+ethKFdzhweGxy4
jieHJIZOG+AW3ZBy7Z05YhIaCoDAhEUVCA9ybd1GZMQs6mpOiDn/i8m1CSmcn31P
ih/VY0UI4dei+8Fp7Azp0MEstH+GS+kxWj/5/SrhkRHxtipJqaB3AHlYHGySCtEp
MlQVwUS+Dz5WiM4OnRxedAcqEyBFa5mogzni1FUQnQTD7dxqpdKa14sls2FhdeZh
vXUyzTpunLw6FGOmGlvNc6Th+AdfnUD6gUg26uxeKK+PL+NanpCagz3Uf/mL6in5
fv+7lZM0rNEWgn6JXlHbBlxCxJf0IcDcE+ghMdiHHuyoJ/DoFiaIdFTkCMlJCMt/
+/EiO7SxwfCQBeIuXpRsWCWN9d3zm6U6TyKAupOuW4iGa8KnRxeKViI40OTIpt0F
P5Hfks+VYmzVyKjmpDcM8NBbLz9wlyyiHscE+Mcm6MAsYAdTe3Ltkqb1qVHzhTdf
mDenoGRenA9OlXGM9djhDsHM9BWUQzDNFpx6bPy0e8+Aya7YZnm6UB/Q4yQdTXG+
vnbiYtL9+HlP6LCmXVVYtkdYnjevyU4QOtxbUajOMyOBH53+NMZtAgMBAAGjXzBd
MAwGA1UdEwEB/wQCMAAwHQYDVR0OBBYEFISG6gVr2PfUsSgsiTMXkEz4hjRfMA4G
A1UdDwEB/wQEAwIHgDAeBgNVHREEFzAVghNsaWNlbnNlLmNoZWNrbWsuY29tMA0G
CSqGSIb3DQEBDQUAA4GBAAcWShP6+jtr46/XVdo+1csVoA3Vr1uE5sTsKqjD2zvZ
YKDD4bMyz72rP+9AguMUfjUPUQBCCf9yr0vVl319k7abugxAu2Cv1HFgxfImL21F
Gd8BoduJnhp+RyKE2rMf61VbBqx5yVW61b9PsqCTLODRLdWsrJzP7nbE+q5y7EuS
-----END CERTIFICATE-----
"""
STATIC_TEST_CERT = certificate.Certificate.load_pem(
    certificate.CertificatePEM(STATIC_TEST_CERT_PEM)
)

ALL_PROTOCOL_VERSIONS = ["2.0", "3.0", "3.2"]


TEST_VERIFICATION_RESPONSE_V3_2 = {
    "VERSION": "3.2",
    "certificate": STATIC_TEST_CERT_PEM,
    "created_at": 1795093935,
    "payload": {
        "active_metric_series_limit": 6969,
        "additional_features": [
            {"enabled": False, "name": "ntop"},
            {"enabled": False, "name": "virt1_appliance"},
            {"enabled": False, "limit": 0, "name": "synthetic_monitoring"},
        ],
        "checkmk_edition": "cme",
        "checkmk_max_version": "",
        "grace_period_after_expiration": 0,
        "group_and_managed_services_use": False,
        "message": "Thank you for uploading your license usage report.",
        "operational_state": "active",
        "reseller_name": "",
        "service_limit": 3000,
        "status": "successful",
        "subscription_auto_renewal": True,
        "subscription_expiration_ts": 1785196800,
        "subscription_recurrence_unit": "millenially",
        "subscription_start_ts": 1753660800,
        "unbound_license": False,
    },
    "request_id": "45c7fcba-7c67-11f1-8d8b-325096b39f47",
    "response_id": "587d0c9b-c9dd-480f-b835-dd830afba72d",
    "signature": "dEaDBeeF",
}

TEST_VERIFICATION_RESPONSE_V3_0 = {
    "VERSION": "3.0",
    "certificate": STATIC_TEST_CERT_PEM,
    "created_at": 1795093935,
    "payload": {
        "additional_features": [
            {"enabled": False, "name": "ntop"},
            {"enabled": False, "name": "virt1_appliance"},
            {"enabled": True, "limit": 17, "name": "synthetic_monitoring"},
        ],
        "checkmk_edition": "cme",
        "checkmk_max_version": "",
        "group_and_managed_services_use": False,
        "message": "Thank you for uploading your license usage report.",
        "operational_state": "active",
        "reseller_name": "",
        "service_limit": 3000,
        "status": "successful",
        "subscription_auto_renewal": True,
        "subscription_expiration_ts": 1785196800,
        "subscription_start_ts": 1753660800,
        "unbound_license": False,
    },
    "request_id": "45c7fcba-7c67-11f1-8d8b-325096b39f47",
    "response_id": "587d0c9b-c9dd-480f-b835-dd830afba72d",
    "signature": "dEaDBeeF",
}

TEST_VERIFICATION_RESPONSE_V2_0 = {
    "VERSION": "2.0",
    "certificate": STATIC_TEST_CERT_PEM,
    "created_at": 1795093935,
    "payload": {
        "additional_features": ["ntop", "virt1_appliance"],
        "checkmk_edition": "cme",
        "checkmk_max_version": "",
        "group_and_managed_services_use": True,
        "limits": {
            "services": 3000,
        },
        "message": "Thank you for uploading your license usage report.",
        "operational_state": "active",
        "reseller_name": "Bob Reseller Inc.",
        "status": "successful",
        "subscription_auto_renewal": True,
        "subscription_expiration_ts": 1785196800,
        "subscription_start_ts": 1753660800,
        "unbound_license": False,
    },
    "request_id": "45c7fcba-7c67-11f1-8d8b-325096b39f47",
    "response_id": "587d0c9b-c9dd-480f-b835-dd830afba72d",
    "signature": "dEaDBeeF",
}


@pytest.mark.parametrize(
    "protocol_version, raw_message, expected_response",
    [
        pytest.param(
            "3.2",
            TEST_VERIFICATION_RESPONSE_V3_2,
            verification.PlainVerificationResponse(
                certificate=STATIC_TEST_CERT,
                created_at=1795093935,
                active_metric_series_limit=6969,
                additional_features=[
                    verification.AdditionalFeature(name="ntop", enabled=False),
                    verification.AdditionalFeature(name="virt1_appliance", enabled=False),
                    verification.AdditionalLimitFeature(
                        name="synthetic_monitoring", enabled=False, limit=0
                    ),
                ],
                checkmk_edition=verification.CheckmkEdition.cme,
                checkmk_max_version="",
                grace_period_after_expiration=0,
                group_and_managed_services_use=False,
                message="Thank you for uploading your license usage report.",
                operational_state=verification.OperationalState.active,
                reseller_name="",
                service_limit=3000,
                status=verification.VerificationStatus.successful,
                subscription_auto_renewal=True,
                subscription_expiration_ts=1785196800,
                subscription_recurrence_unit="millenially",
                subscription_start_ts=1753660800,
                unbound_license=False,
                request_id=uuid.UUID("45c7fcba-7c67-11f1-8d8b-325096b39f47"),
                response_id=uuid.UUID("587d0c9b-c9dd-480f-b835-dd830afba72d"),
                signature=b"tF\x83\x05\xe7\x85",
            ),
            id="protocol_v3_2",
        ),
        pytest.param(
            "3.0",
            TEST_VERIFICATION_RESPONSE_V3_0,
            verification.PlainVerificationResponse(
                certificate=STATIC_TEST_CERT,
                created_at=1795093935,
                active_metric_series_limit=3000,
                additional_features=[
                    verification.AdditionalFeature(name="ntop", enabled=False),
                    verification.AdditionalFeature(name="virt1_appliance", enabled=False),
                    verification.AdditionalLimitFeature(
                        name="synthetic_monitoring", enabled=True, limit=17
                    ),
                ],
                checkmk_edition=verification.CheckmkEdition.cme,
                checkmk_max_version="",
                grace_period_after_expiration=2592000,
                group_and_managed_services_use=False,
                message="Thank you for uploading your license usage report.",
                operational_state=verification.OperationalState.active,
                reseller_name="",
                service_limit=3000,
                status=verification.VerificationStatus.successful,
                subscription_auto_renewal=True,
                subscription_expiration_ts=1785196800,
                subscription_recurrence_unit="yearly",
                subscription_start_ts=1753660800,
                unbound_license=False,
                request_id=uuid.UUID("45c7fcba-7c67-11f1-8d8b-325096b39f47"),
                response_id=uuid.UUID("587d0c9b-c9dd-480f-b835-dd830afba72d"),
                signature=b"tF\x83\x05\xe7\x85",
            ),
            id="protocol_v3_0",
        ),
        pytest.param(
            "2.0",
            TEST_VERIFICATION_RESPONSE_V2_0,
            verification.PlainVerificationResponse(
                certificate=STATIC_TEST_CERT,
                created_at=1795093935,
                active_metric_series_limit=3000,
                additional_features=[
                    verification.AdditionalFeature(name="ntop", enabled=True),
                    verification.AdditionalFeature(name="virt1_appliance", enabled=True),
                ],
                checkmk_edition=verification.CheckmkEdition.cme,
                checkmk_max_version="",
                grace_period_after_expiration=2592000,
                group_and_managed_services_use=True,
                message="Thank you for uploading your license usage report.",
                operational_state=verification.OperationalState.active,
                reseller_name="Bob Reseller Inc.",
                service_limit=3000,
                status=verification.VerificationStatus.successful,
                subscription_auto_renewal=True,
                subscription_expiration_ts=1785196800,
                subscription_recurrence_unit="yearly",
                subscription_start_ts=1753660800,
                unbound_license=False,
                request_id=uuid.UUID("45c7fcba-7c67-11f1-8d8b-325096b39f47"),
                response_id=uuid.UUID("587d0c9b-c9dd-480f-b835-dd830afba72d"),
                signature=b"tF\x83\x05\xe7\x85",
            ),
            id="protocol_v2_0",
        ),
        pytest.param(
            "2.0",
            {
                "VERSION": "2.0",
                "certificate": STATIC_TEST_CERT_PEM,
                "created_at": 1795093935,
                "payload": {
                    "additional_features": ["ntop"],
                    "checkmk_edition": "cme",
                    "checkmk_max_version": "",
                    "group_and_managed_services_use": True,
                    "limits": {
                        "services": 3000,
                    },
                    "message": "Thank you for uploading your license usage report.",
                    "operational_state": "active",
                    "reseller_name": "Bob Reseller Inc.",
                    "status": "successful",
                    "subscription_auto_renewal": True,
                    "subscription_expiration_ts": 1785196800,
                    "subscription_start_ts": 1753660800,
                    "unbound_license": False,
                },
                "request_id": "45c7fcba-7c67-11f1-8d8b-325096b39f47",
                "response_id": "587d0c9b-c9dd-480f-b835-dd830afba72d",
                "signature": "dEaDBeeF",
            },
            verification.PlainVerificationResponse(
                certificate=STATIC_TEST_CERT,
                created_at=1795093935,
                active_metric_series_limit=3000,
                additional_features=[
                    verification.AdditionalFeature(name="ntop", enabled=True),
                    verification.AdditionalFeature(name="virt1_appliance", enabled=False),
                ],
                checkmk_edition=verification.CheckmkEdition.cme,
                checkmk_max_version="",
                grace_period_after_expiration=2592000,
                group_and_managed_services_use=True,
                message="Thank you for uploading your license usage report.",
                operational_state=verification.OperationalState.active,
                reseller_name="Bob Reseller Inc.",
                service_limit=3000,
                status=verification.VerificationStatus.successful,
                subscription_auto_renewal=True,
                subscription_expiration_ts=1785196800,
                subscription_recurrence_unit="yearly",
                subscription_start_ts=1753660800,
                unbound_license=False,
                request_id=uuid.UUID("45c7fcba-7c67-11f1-8d8b-325096b39f47"),
                response_id=uuid.UUID("587d0c9b-c9dd-480f-b835-dd830afba72d"),
                signature=b"tF\x83\x05\xe7\x85",
            ),
            id="protocol_v2_0_with_disabled_feature",
        ),
    ],
)
def test_parse_plain_verification_response(
    protocol_version: protocol_version.AllowedVerificationResponseVersions,
    raw_message: object,
    expected_response: verification.PlainVerificationResponse,
) -> None:
    response = verification.parse_plain_verification_response(protocol_version, raw_message)

    # Check certificate separately because it does not support equality.
    assert response.certificate.dump_pem().str == expected_response.certificate.dump_pem().str
    response = dataclasses.replace(response, certificate=expected_response.certificate)
    assert response == expected_response


@pytest.mark.parametrize("protocol_version", ALL_PROTOCOL_VERSIONS)
def test_parse_plain_verification_response_not_a_dict(
    protocol_version: protocol_version.AllowedVerificationResponseVersions,
) -> None:
    with pytest.raises(ValueError):
        verification.parse_plain_verification_response(protocol_version, "not a dict")


@pytest.mark.parametrize("protocol_version", ALL_PROTOCOL_VERSIONS)
def test_parse_plain_verification_response_payload_missing(
    protocol_version: protocol_version.AllowedVerificationResponseVersions,
) -> None:
    with pytest.raises(ValueError):
        verification.parse_plain_verification_response(protocol_version, {})


@pytest.mark.parametrize("protocol_version", ALL_PROTOCOL_VERSIONS)
def test_parse_plain_verification_response_payload_not_a_dict(
    protocol_version: protocol_version.AllowedVerificationResponseVersions,
) -> None:
    with pytest.raises(ValueError):
        verification.parse_plain_verification_response(protocol_version, {"payload": ""})


def test_parse_plain_verification_response_protocol_version_too_old() -> None:
    raw_response = {
        "VERSION": "1.0",
        "certificate": STATIC_TEST_CERT_PEM,
        "created_at": 1795093935,
        "payload": {
            "additional_features": ["ntop", "virt1_appliance"],
            "checkmk_edition": "cme",
            "checkmk_max_version": "",
            "group_and_managed_services_use": True,
            "limits": {
                "services": 3000,
            },
            "message": "Thank you for uploading your license usage report.",
            "operational_state": "active",
            "reseller_name": "Bob Reseller Inc.",
            "status": "successful",
            "subscription_auto_renewal": True,
            "subscription_expiration_ts": 1785196800,
            "subscription_start_ts": 1753660800,
            "unbound_license": False,
        },
        "request_id": "45c7fcba-7c67-11f1-8d8b-325096b39f47",
        "response_id": "587d0c9b-c9dd-480f-b835-dd830afba72d",
        "signature": "dEaDBeeF",
    }
    with pytest.raises(ValueError):
        verification.parse_plain_verification_response("1.0", raw_response)


def test_parse_plain_verification_response_missing_key_v2_0() -> None:
    for missing_key in TEST_VERIFICATION_RESPONSE_V2_0:
        if missing_key in ("VERSION", "payload"):
            continue
        response = copy.deepcopy(TEST_VERIFICATION_RESPONSE_V2_0)
        del response[missing_key]
        with pytest.raises(ValueError, match=re.escape(missing_key)):
            verification.parse_plain_verification_response("2.0", response)
    for missing_key in TEST_VERIFICATION_RESPONSE_V2_0["payload"]:  # type: ignore[attr-defined]
        response = copy.deepcopy(TEST_VERIFICATION_RESPONSE_V2_0)
        del response["payload"][missing_key]  # type: ignore[attr-defined]
        with pytest.raises(ValueError, match=re.escape(missing_key)):
            verification.parse_plain_verification_response("2.0", response)


def test_parse_plain_verification_response_missing_key_v3_0() -> None:
    for missing_key in TEST_VERIFICATION_RESPONSE_V3_0:
        if missing_key in ("VERSION", "payload"):
            continue
        response = copy.deepcopy(TEST_VERIFICATION_RESPONSE_V3_0)
        del response[missing_key]
        with pytest.raises(ValueError, match=re.escape(missing_key)):
            verification.parse_plain_verification_response("3.0", response)
    for missing_key in TEST_VERIFICATION_RESPONSE_V3_0["payload"]:  # type: ignore[attr-defined]
        response = copy.deepcopy(TEST_VERIFICATION_RESPONSE_V3_0)
        del response["payload"][missing_key]  # type: ignore[attr-defined]
        with pytest.raises(ValueError, match=re.escape(missing_key)):
            verification.parse_plain_verification_response("3.0", response)


def test_parse_plain_verification_response_missing_key_v3_2() -> None:
    for missing_key in TEST_VERIFICATION_RESPONSE_V3_2:
        if missing_key in ("VERSION", "payload"):
            continue
        response = copy.deepcopy(TEST_VERIFICATION_RESPONSE_V3_2)
        del response[missing_key]
        with pytest.raises(ValueError, match=re.escape(missing_key)):
            verification.parse_plain_verification_response("3.2", response)
    for missing_key in TEST_VERIFICATION_RESPONSE_V3_2["payload"]:  # type: ignore[attr-defined]
        response = copy.deepcopy(TEST_VERIFICATION_RESPONSE_V3_2)
        del response["payload"][missing_key]  # type: ignore[attr-defined]
        with pytest.raises(ValueError, match=re.escape(missing_key)):
            verification.parse_plain_verification_response("3.2", response)


@pytest.mark.parametrize(
    "protocol_version,base_response",
    [
        pytest.param("3.0", TEST_VERIFICATION_RESPONSE_V3_0, id="3.0"),
        pytest.param("3.2", TEST_VERIFICATION_RESPONSE_V3_2, id="3.2"),
    ],
)
@pytest.mark.parametrize(
    "additional_features",
    [
        pytest.param("str", id="wrong-type-string"),
        pytest.param({}, id="wrong-type-object"),
        pytest.param(
            ["str"],
            id="wrong-additional-feature-type-str",
        ),
        pytest.param(
            [[]],
            id="wrong-additional-feature-type-list",
        ),
        pytest.param([{"enabled": True}], id="missing-name"),
        pytest.param([{"name": 17, "enabled": True}], id="wrong-name-type"),
        pytest.param([{"name": "ntop"}], id="missing-enabled"),
        pytest.param(
            [{"name": "ntop", "enabled": 1}],
            id="wrong-enabled-type",
        ),
        pytest.param(
            [{"name": "unknown", "enabled": True}],
            id="unknown-name",
        ),
        pytest.param(
            [{"name": "synthetic_monitoring", "enabled": True}],
            id="no-synthetic-monitoring-limit",
        ),
        pytest.param(
            [{"name": "synthetic_monitoring", "enabled": True, "limit": "17"}],
            id="wrong-synthetic-monitoring-limit",
        ),
    ],
)
def test_parse_plain_verification_response_bad_additional_features(
    protocol_version: protocol_version.AllowedVerificationResponseVersions,
    base_response: dict[str, str | dict[str, object]],
    additional_features: object,
) -> None:
    response: dict[str, str | dict[str, object]] = copy.deepcopy(base_response)
    response["payload"]["additional_features"] = additional_features  # type: ignore[index]

    with pytest.raises(ValueError):
        verification.parse_plain_verification_response(protocol_version, response)
