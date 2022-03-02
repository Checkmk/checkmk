#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from time import time

import pytest
from agent_receiver.certificates import (
    _decode_base64_cert,
    _invalid_certificate_response,
    _validate_certificate,
    CertificateValidationError,
    CertValidationRoute,
)
from cryptography.hazmat.primitives.serialization import Encoding
from cryptography.x509 import Certificate
from fastapi import APIRouter, FastAPI
from fastapi.testclient import TestClient
from pytest_mock import MockerFixture
from starlette.requests import Headers

from tests.testlib import on_time

from cmk.utils.certs import RootCA


def test_decode_base64_cert_b64_invalid() -> None:
    with pytest.raises(
        ValueError,
        match="Client certificate deserialization: base64 decoding failed",
    ):
        _decode_base64_cert("asgasdg")


def test_decode_base64_cert_der_invalid() -> None:
    with pytest.raises(ValueError):
        _decode_base64_cert("bm90IGEgdmFsaWQgY2VydA==")


def test_decode_base64_cert_ok(
    trusted_cert_b64: str,
    trusted_cert: Certificate,
) -> None:
    assert _decode_base64_cert(trusted_cert_b64).public_bytes(
        Encoding.DER
    ) == trusted_cert.public_bytes(Encoding.DER)


@pytest.mark.usefixtures("root_ca")
def test_validate_certificate_invalid_signature(untrusted_cert: Certificate) -> None:
    with pytest.raises(
        CertificateValidationError,
        match="Client certificate not trusted",
    ):
        _validate_certificate(untrusted_cert)


def test_validate_certificate_expired(root_ca: RootCA) -> None:
    with on_time(1638174087, "UTC"):
        cert, _priv_key = root_ca.new_signed_cert("abc123", 1)
    with pytest.raises(
        CertificateValidationError,
        match="Client certificate expired",
    ):
        _validate_certificate(cert)


def test_validate_certificate_not_yet_valid(root_ca: RootCA) -> None:
    with on_time(time() + 24 * 3600, "UTC"):
        cert, _priv_key = root_ca.new_signed_cert("abc123", 100)
    with pytest.raises(
        CertificateValidationError,
        match="Client certificate not yet valid",
    ):
        _validate_certificate(cert)


def test_validate_certificate_ok(trusted_cert: Certificate) -> None:
    _validate_certificate(trusted_cert)


def test_invalid_certificate_response_missing() -> None:
    resp = _invalid_certificate_response(Headers(headers={}))
    assert resp
    assert resp.status_code == 400
    assert resp.body == b'{"detail":"Client certificate missing in header"}'


def test_invalid_certificate_response_malformed() -> None:
    resp = _invalid_certificate_response(Headers(headers={"certificate": "let me in!"}))
    assert resp
    assert resp.status_code == 400
    assert resp.body == b'{"detail":"Client certificate deserialization: base64 decoding failed"}'


@pytest.mark.usefixtures("root_ca")
def test_invalid_certificate_response_untrusted(untrusted_cert_b64: str) -> None:
    resp = _invalid_certificate_response(Headers(headers={"certificate": untrusted_cert_b64}))
    assert resp
    assert resp.status_code == 401
    assert resp.body == b'{"detail":"Client certificate not trusted"}'


def test_invalid_certificate_response_ok(trusted_cert_b64: str) -> None:
    assert _invalid_certificate_response(Headers(headers={"certificate": trusted_cert_b64})) is None


def test_cert_validation_route(mocker: MockerFixture) -> None:
    app = FastAPI()
    cert_validation_router = APIRouter(route_class=CertValidationRoute)

    @cert_validation_router.get("/endpoint")
    def endpoint():
        return {"Hello": "World"}

    app.include_router(cert_validation_router)

    client = TestClient(app)
    response = client.get(
        "/endpoint",
    )
    assert response.status_code == 400
    assert response.json() == {"detail": "Client certificate missing in header"}

    mocker.patch(
        "agent_receiver.certificates._invalid_certificate_response",
        lambda _h: None,
    )
    response = client.get(
        "/endpoint",
    )
    assert response.status_code == 200
    assert response.json() == {"Hello": "World"}
