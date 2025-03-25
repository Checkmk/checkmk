#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from collections.abc import Iterator
from unittest.mock import patch
from urllib.parse import urljoin

import pytest
from pytest_mock import MockerFixture

from tests.unit.cmk.web_test_app import WebTestAppForCMK

_BASE = "/NO_SITE/check_mk/api/1.0/"
_URL_ROOT_CERT = urljoin(_BASE, "root_cert")
_URL_CSR = urljoin(_BASE, "csr")

_CSR = """-----BEGIN CERTIFICATE REQUEST-----
MIIChTCCAW0CAQAwLzEtMCsGA1UEAwwkYWJjZDY3YzYtNjdhNi00N2Q2LWFiNzYt
N2I5ZTdkNjgzNzg3MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA0iPc
DgCxvZqIDrm0fpZrXNnkXmhYKxHv5km/FsaVWH/XEc3KxiUfy8ma+t4lITAuE4t1
KAU4e2Z8ywuGeVEysTzWVLBx9U6kmtwF4m5QBcmzdlDr9+/5fJSwFq1MSZEpbWw8
aHa/ezlF2JP5UQ7VEvH+RRJVxb+9G9FbP1TL5UmgutTPVqmIVDCqVhYajMBvk6BJ
rJb3vzuFG5Emd0Sdq34YrDM82XcRemdEPbCIMkraeOddeOfdJfqu5c30ip/GlS3i
jVILGOtASz5Khogzl+gOU2CceFlvgctSn8lynAUskhTpp6+GrqURCI1MI9jP9Cdy
dzVDGOm2fwu9dUjF1QIDAQABoBEwDwYJKoZIhvcNAQkOMQIwADANBgkqhkiG9w0B
AQsFAAOCAQEAZ1QZ88coppJvRLLfnOixXJkbGPTRJcjnY+nWV1CcRS1puwyJ/QTI
tCfGfV4OJO88Vzpkde/hLfOI6Fhi+N40ouKjLjrt2K04ckrz3jW7cZXAM41uvod3
b7b+K8I84oEzJFhcA684OHQ2B9bpnCRdY7WjRh852StxBvOsAcByYvtpt/EEDhJu
kMwfku+OmT23cBX/IRZmrZdVBpYPiKrfMQjoTMBfsvco84Qlf9z14CXF88rLjQ9H
ZHJCNN5QlnOgbFF8RyRqVMkPp80jto0pbrCbeLZuFx4PxCmd17X4kQdMdecGXxv0
1f4nM7YVk0qCs7UYn79TMCnz+pJqYyJ7dQ==
-----END CERTIFICATE REQUEST-----
"""

# CSR which was signed by a different public key than the one it contains
# created by tampering with the agent controller's `make_csr` function
_CSR_INVALID = """-----BEGIN CERTIFICATE REQUEST-----
MIICVTCCAT0CAQAwEDEOMAwGA1UEAwwFc3R1ZmYwggEiMA0GCSqGSIb3DQEBAQUA
A4IBDwAwggEKAoIBAQC9gRz+9MuwTmzPyrNV+qj51YQoWSjCiA5vTFwftJ7Kjg9h
KJ/UcirgtP20DtFloU7DG8CTbxCHMXpHnquugGv/GpmrttD/3CTdJXNEyK7Frh/K
MTEgPZMq2dv9L+08Djbv/T2tShMbBpif7aCngU3ZmIpHhSLLUgC0f7/OaxVC8gWY
EpUzbLdNJMOz4qGiB+H7nV4BGO8dT44eIKOtwH68ruTzQ7bqwKTZ1WFiKm71PPxK
tBKMe89thtkeaz91k3YPri3mbO8R0t0rylN6kN2dIngJ/0OX1vnypuF2dsBZmKh+
xfX/1Wx5L7Il6ZBtQaULqzO3p95K1cIXN2W7Ji+PAgMBAAGgADANBgkqhkiG9w0B
AQsFAAOCAQEAiBPD5dZ2BNQYefG2OEvfqek1QPizwIf3dEUi7hoqZnGe31uyiiWX
0Q0SyT/xVdOKrm0QDBQm3El/32DV9DanJNotEjOTFtK+gUan7lw7uDlk9nxhIJhm
6uUsV3zBqdo44j/CkoMKfYxD2RwLn+mRUdnWkolgB68NCvdgNkuTE98kNoWca1Im
mAtenKKgwZUsquCSfU6yNbCsWvvjfXoqhQ3la8zCmN/cRJPbtSByXhfA3k/dLMv3
oPajdDb2p3SzEThY3odri+iLB5iPt/FdSGu4NZ/rbiImPbDznvq8IEZuU+9KMUxk
0ry/GD3iBXZwX4USPLUl8rP+XOasltsgUQ==
-----END CERTIFICATE REQUEST-----
"""

# CSR with a CN which is not a valid UUID
_CSR_CN_NO_UUID = """-----BEGIN CERTIFICATE REQUEST-----
MIICaDCCAVACAQAwEjEQMA4GA1UEAwwHbm8tdXVpZDCCASIwDQYJKoZIhvcNAQEB
BQADggEPADCCAQoCggEBAMXYb1dQXYNk7f2kvZ47dvPajPNZSv/+bolHGdG24061
s9SzxY54OUmTnXgRMbjRJVZ4izjZpALyD9T2RL25E+MLAA0uT96eZ7LNYdWRme8b
MAt5eTNRAK22E6SdZpt9iHRsaCQ+dAlwG756XuHwjWhsCcZWWqxoEn136xr5L4u4
SUFVlXxabIsPeUCe7t3yYg6HPOZh6EQdDPzsq8yg9MiavKogIipUucOlltZvlQqc
bAlHwXlfYuvwbIZDK4llJZF8/4eDxtiumsb4pKcd6PB05nwGQOBf0Bb49rMEKxq0
QZDX7QWfvSQ9biscPTMDcS8RHNb+YEl8PgDtNCaCn7sCAwEAAaARMA8GCSqGSIb3
DQEJDjECMAAwDQYJKoZIhvcNAQELBQADggEBAFhof2ckbIFwrMtwXCt2wZOWVyMI
sgpaJKPjdpxZUg3K+R0MgSp1oiB7k5GNIM8tzIxbDvbf7eJymO9V0tjzP/x9rKlM
jQPOds9oPe/vAgcsXcXJyVsspn34oASgFk9Y5Bd2GeTp8vO8Y46i3/acZ/vBu4Dx
FOQ4UfgWGDK3UYbV0vpvkVwFyyfWphc2c6/CrpqHHGBsgnPXEuC9iYQPqg4pOCzo
34DVpSX/BXy3WpBkAKGKBrDZad4rBb8QbhiO01V1G5732sdroa7WbhBHcHrYapv4
TeG0kQLRRBZ1rzPebxchjTIxfc25kdQauvp86He0FZR6LLQgX0gSmSrAgAk=
-----END CERTIFICATE REQUEST-----
"""

# CSR without a CN
_CSR_NO_CN = """-----BEGIN CERTIFICATE REQUEST-----
MIICRTCCAS0CAQAwADCCASIwDQYJKoZIhvcNAQEBBQADggEPADCCAQoCggEBALSK
w3dr9AFxwoKgHDr8W99nPMfmp+i/kiUF8yGpHpD+5OnkqE0OEGemMQESsHM7mWHG
DuOecduKd/cNeTtJ6F1C81tGkQBFVrybprlnq1xaN4OQwhtLX3VjkL0ggx4Vw/RC
+NDTdmhNAaM6/k4dbI1NCcrP5nstDsBOWKixCu8Fhi6KBR2FLAJ9r6ppk3Fpj3Pw
yn+iPJBFuhmPmAvtauBtgLX+R213Ah/7T32ehTYbR677zKSRv9uFDxrQOynHtL3S
XNxlfcYib4ATejww8OV3kOAETkyPslb6TQrZ2kqErU2Dk1WT+/EHErJ+LyzX7lWq
y99CH5mvm8RclcE32nsCAwEAAaAAMA0GCSqGSIb3DQEBCwUAA4IBAQBKDUJzyZTs
Ez0um2vLYLKrojUpYqCMZpB81zTTC3/NkuCr8OnSjD8PMA3L4ZhTaSJT0WQxmniY
XfDtZAQ8bYL7JWCGEK7fT03PFuv2O3hYPQ1eJIlZB3fR6urCyGKRPH6u8I2xTivA
jIsL4T3Pxez6bf1pgivSEXl7jdnsTylRyl6Roz7Uq1ybekTUTFyy/heGk5Rkms9f
dIsp8fuSbKY7bcWDUxnCd7cbt8ESi5VkiCSN//3qElMVLmklpyBfu1ob/WuNOcqw
T8L6kGpelFYUsC/NKdJgpkwCQMr6a03nzu8BqhDWdk6d3V4oLTr9EA4X8SoNaqyr
Oaxu+XnWKm3p
-----END CERTIFICATE REQUEST-----
"""


@pytest.fixture
def forbid_agent_pairing(aut_user_auth_wsgi_app: WebTestAppForCMK) -> Iterator[None]:
    with patch(
        "cmk.gui.logged_in.LoggedInUser.may",
        return_value=False,
    ) as user_may_not:
        yield
        user_may_not.assert_called_once_with("general.agent_pairing")


@pytest.mark.usefixtures("forbid_agent_pairing")
def test_root_cert_403(aut_user_auth_wsgi_app: WebTestAppForCMK) -> None:
    aut_user_auth_wsgi_app.call_method(
        "get",
        _URL_ROOT_CERT,
        status=403,
        headers={"Accept": "application/json"},
    )


def test_root_cert_200(
    mocker: MockerFixture,
    aut_user_auth_wsgi_app: WebTestAppForCMK,
) -> None:
    mocker.patch(
        "cmk.gui.openapi.endpoints.cert._serialized_root_cert",
        return_value="fake_root_cert",
    )
    resp = aut_user_auth_wsgi_app.call_method(
        "get",
        _URL_ROOT_CERT,
        status=200,
        headers={"Accept": "application/json"},
    )
    assert resp.json_body["cert"] == "fake_root_cert"


@pytest.mark.usefixtures("forbid_agent_pairing")
def test_csr_403(aut_user_auth_wsgi_app: WebTestAppForCMK) -> None:
    aut_user_auth_wsgi_app.call_method(
        "post",
        _URL_CSR,
        params=json.dumps({"csr": _CSR}),
        status=403,
        headers={"Accept": "application/json"},
        content_type="application/json; charset=utf-8",
    )


@pytest.mark.parametrize(
    "csr_str",
    [
        pytest.param(
            _CSR[:30],
            id="completely broken",
        ),
        pytest.param(
            _CSR[:100] + "let's break it" + _CSR[100:],
            id="malformed",
        ),
        pytest.param(
            _CSR_INVALID,
            id="public key mismatch",
        ),
        pytest.param(
            _CSR_CN_NO_UUID,
            id="CN no valid UUID",
        ),
        pytest.param(
            _CSR_NO_CN,
            id="No CN",
        ),
    ],
)
def test_csr_400(
    aut_user_auth_wsgi_app: WebTestAppForCMK,
    csr_str: str,
) -> None:
    aut_user_auth_wsgi_app.call_method(
        "post",
        _URL_CSR,
        params=json.dumps({"csr": csr_str}),
        status=400,
        headers={"Accept": "application/json"},
        content_type="application/json; charset=utf-8",
    )


def test_csr_200(
    mocker: MockerFixture,
    aut_user_auth_wsgi_app: WebTestAppForCMK,
) -> None:
    mocker.patch(
        "cmk.gui.openapi.endpoints.cert._serialized_signed_cert",
        return_value="3pi4ghjwerihg",
    )
    aut_user_auth_wsgi_app.call_method(
        "post",
        _URL_CSR,
        params=json.dumps({"csr": _CSR}),
        status=200,
        headers={"Accept": "application/json"},
        content_type="application/json; charset=utf-8",
    )


@pytest.mark.usefixtures("patch_theme")
def test_agent_controller_certificates_settings_ok(
    logged_in_admin_wsgi_app: WebTestAppForCMK,
) -> None:
    assert set(
        logged_in_admin_wsgi_app.get(
            urljoin(_BASE, "agent_controller_certificates_settings"),
            status=200,
            headers={"Accept": "application/json"},
        ).json_body
    ) == {"lifetime_in_months"}


@pytest.mark.usefixtures("patch_theme")
def test_agent_controller_certificates_settings_unauthorized(
    logged_in_wsgi_app: WebTestAppForCMK,
) -> None:
    assert (
        logged_in_wsgi_app.get(
            urljoin(_BASE, "agent_controller_certificates_settings"),
            status=403,
            headers={"Accept": "application/json"},
        ).json_body["title"]
        == "Unauthorized"
    )
