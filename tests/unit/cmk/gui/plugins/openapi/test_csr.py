#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from typing import Tuple

import pytest
from pytest_mock import MockerFixture

from tests.unit.cmk.gui.conftest import WebTestAppForCMK

_URL = "/NO_SITE/check_mk/api/1.0/csr"

_CSR = """-----BEGIN CERTIFICATE REQUEST-----
MIICVDCCATwCAQIwDzENMAsGA1UEAwwEaHVyejCCASIwDQYJKoZIhvcNAQEBBQAD
ggEPADCCAQoCggEBAOyw0NwGW79wK5+7gG2o5osJ4HwWiT5SjF8v3zHwWfy0YD1W
hHkoplXzUzvGGMYGcc5xIdRmd8O8qJ63RN7hvDfPQBrOQkSKuATzQJaNRGd21cdv
nhYIAEBWJW8cf9tMlHhgEwxCrNuC+wWFK7EFbw3Zgb2hVPa4ME8ICWNsS8qnN0i2
Od/WpUoEBmx7zVWkIUJEgy3wvEkR+wW1v72GELnLzKfvyXroWh6m/XMTdK0J1lnw
PEASrt3+EozhpSxA1f2qsmwx5OcOAo5AMoTvQzYRYKdsS6dLo1WAEZn8M2NrRWnp
KKp5gDDZoULAHZrnBuIAUIML7rOdMMa5fhK9ebUCAwEAAaAAMA0GCSqGSIb3DQEB
CwUAA4IBAQC0C19SSVEDUIj7OR1ISbev8etlUa2fDVEf3s64yQS+D3+xQvxfqvuP
9H/IrMof6s38cRCLSF4gxWtMmRpSLbkB2KFOSkN/zIRGsQ/SR3vbUkNqTfU98vAx
QeaVo0glagZFA1QhmYEWvGGi0GwszPkfTwGsSh72OHtogzhR6ODFEky7ZSAQWVn5
8aQHZAKsKvJyUSlPx9FKXH6xjwWyFlTa1+8nGyAXBjRbVYs2cVggKgiEjD/6tpkS
UWFmeMk2qnNT07U5tftdro41NSs/y9l1fClKNbAZLf29YthSKJd7EkcHi+bdLlry
kafjVIj7D4963Shrnqeb9BaYfAP6x0gi
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


@pytest.fixture(name="wsgi_app_with_user")
def fixture_wsgi_app_with_user(
    wsgi_app: WebTestAppForCMK,
    with_automation_user: Tuple[str, str],
) -> WebTestAppForCMK:
    wsgi_app.set_authorization(("Bearer", " ".join(with_automation_user)))
    return wsgi_app


def test_csr_403(
    mocker: MockerFixture,
    wsgi_app_with_user: WebTestAppForCMK,
) -> None:
    mocker.patch(
        "cmk.gui.plugins.openapi.endpoints.csr._user_is_authorized",
        return_value=False,
    )
    wsgi_app_with_user.call_method(
        "post",
        _URL,
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
    ],
)
def test_csr_400(
    wsgi_app_with_user: WebTestAppForCMK,
    csr_str: str,
) -> None:
    wsgi_app_with_user.call_method(
        "post",
        _URL,
        params=json.dumps({"csr": csr_str}),
        status=400,
        headers={"Accept": "application/json"},
        content_type="application/json; charset=utf-8",
    )


def test_csr_200(
    mocker: MockerFixture,
    wsgi_app_with_user: WebTestAppForCMK,
) -> None:
    mocker.patch(
        "cmk.gui.plugins.openapi.endpoints.csr._serialized_signed_cert",
        return_value="3pi4ghjwerihg",
    )
    wsgi_app_with_user.call_method(
        "post",
        _URL,
        params=json.dumps({"csr": _CSR}),
        status=200,
        headers={"Accept": "application/json"},
        content_type="application/json; charset=utf-8",
    )
