#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from unittest.mock import MagicMock

import pytest
from pytest_mock import MockerFixture

from tests.unit.cmk.gui.conftest import WebTestAppForCMK

_BASE = "/NO_SITE/check_mk/api/1.0"
_URL_ROOT_CERT = f"{_BASE}/root_cert"
_URL_CSR = f"{_BASE}/csr"

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
_CSR_INVALID = """-----BEGIN CERTIFICATE REQUEST-----
MIICVDCCATwCAQIwDzENMAsGA1UEAwwEaHVyejCCASIwDQYJKoZIhvcNAQEBBQAD
ggEPADCCAQoCggEBAMoIqXeS86zKNwd3auWbBIsJZz6yQL4z3yVMzGuEwpMN8DBN
UxEygrvjLJr9BV4+TRnoyxErAlFvaGevZHuhCyLFHPrTZFcKqPCqrmZ1yy4dD/Kp
qhCbUH/ewMbrQdw5tQAJfeDmQU+RGAfoSWxnCqaclyeJ5WXRVw7oz/MN3Y2a+pkN
vvK4pxhsy+5HeovGDY7ZI5jXEtbBjdvznp8q18NSG3A+fd/j1y1MKBw9Ni79DFMF
EQGHNpc2L1PDAizfUOZlSgf/fAp3qSCBFchB2iYtLIACjXvNqT7HCPoOQ50rDPvo
KeUSXlFflELGMVzBIfp+/sh+YtJJafHMYU40CBUCAwEAAaAAMA0GCSqGSIb3DQEB
CwUAA4IBAQCFWE1BlX6+NGJqOuinHNoWteYwXzt2SxVb6FUD/q9SyC+QtEELWK/4
Mh3atWu1Gl9Xlhkd9ycaOrRKvbW+atermcIF9f8iY8wJMsaGdemCrDZzTBlNUYu8
p+taKwXrzoo7vJMSsx23BPJl7m6MZxgzLWXF6Sp7lH4DJTiZYM98nfb6JluRbPlg
M+WTC90G/Fzn8S6OWmmFcAilVxHPrtpdPdD9s+hb4SMyMzHI+xcxF3nObwL9OGd4
izSZOfdvQ+6nV8m1zeKV80QJPPAsigkQRJ4mN0r7HBkTdIU+rwiCKlitsePb5vyV
nkrndRn3MoyHIO3cuT7inOlFb/VYPRWP
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


@pytest.fixture(name="user_may_not")
def fixture_user_may_not(mocker: MockerFixture) -> MagicMock:
    return mocker.patch(
        "cmk.gui.logged_in.LoggedInUser.may",
        return_value=False,
    )


def test_root_cert_403(
    aut_user_auth_wsgi_app: WebTestAppForCMK,
    user_may_not: MagicMock,
) -> None:
    aut_user_auth_wsgi_app.call_method(
        "get",
        _URL_ROOT_CERT,
        status=403,
        headers={"Accept": "application/json"},
    )
    user_may_not.assert_called_once_with("general.agent_pairing")


def test_root_cert_200(
    mocker: MockerFixture,
    aut_user_auth_wsgi_app: WebTestAppForCMK,
) -> None:
    mocker.patch(
        "cmk.gui.plugins.openapi.endpoints.certs._serialized_root_cert",
        return_value="fake_root_cert",
    )
    resp = aut_user_auth_wsgi_app.call_method(
        "get",
        _URL_ROOT_CERT,
        status=200,
        headers={"Accept": "application/json"},
    )
    assert resp.json_body["cert"] == "fake_root_cert"


def test_csr_403(
    aut_user_auth_wsgi_app: WebTestAppForCMK,
    user_may_not: MagicMock,
) -> None:
    aut_user_auth_wsgi_app.call_method(
        "post",
        _URL_CSR,
        params=json.dumps({"csr": _CSR}),
        status=403,
        headers={"Accept": "application/json"},
        content_type="application/json; charset=utf-8",
    )
    user_may_not.assert_called_once_with("general.agent_pairing")


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
        "cmk.gui.plugins.openapi.endpoints.certs._serialized_signed_cert",
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
