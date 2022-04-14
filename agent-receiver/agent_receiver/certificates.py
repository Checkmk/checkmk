#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from base64 import urlsafe_b64decode
from binascii import Error
from datetime import datetime
from typing import Any, Callable, Coroutine, Optional

from agent_receiver.site_context import root_cert_path
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPublicKey
from cryptography.x509 import (
    Certificate,
    load_der_x509_certificate,
    load_pem_x509_certificate,
    load_pem_x509_csr,
)
from cryptography.x509.oid import NameOID
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute
from starlette.requests import Headers
from starlette.status import HTTP_400_BAD_REQUEST, HTTP_401_UNAUTHORIZED


def uuid_from_pem_csr(pem_csr: str) -> str:
    try:
        return (
            load_pem_x509_csr(pem_csr.encode())
            .subject.get_attributes_for_oid(NameOID.COMMON_NAME)[0]
            .value
        )
    except ValueError:
        return "[CSR parsing failed]"


class CertificateValidationError(Exception):
    pass


def _decode_base64_cert(cert_b64: str) -> Certificate:
    try:
        cert_der = urlsafe_b64decode(cert_b64)
    except Error:
        raise ValueError("Client certificate deserialization: base64 decoding failed")
    return load_der_x509_certificate(cert_der)


def _check_validity_period(certificate: Certificate) -> None:
    utc_now = datetime.utcnow()
    if certificate.not_valid_before > utc_now:
        raise CertificateValidationError("Client certificate not yet valid")
    if certificate.not_valid_after < utc_now:
        raise CertificateValidationError("Client certificate expired")


def _check_signature(certificate: Certificate) -> None:
    root_certificate = load_pem_x509_certificate(root_cert_path().read_bytes())
    if not isinstance(
        root_public_key := root_certificate.public_key(),
        RSAPublicKey,
    ):
        raise CertificateValidationError(
            "Public key of root certificate has wrong format (expected RSA, got "
            f"{type(root_public_key)})"
        )
    try:
        root_public_key.verify(
            certificate.signature,
            certificate.tbs_certificate_bytes,
            padding.PKCS1v15(),
            certificate.signature_hash_algorithm,
        )
    except InvalidSignature:
        raise CertificateValidationError("Client certificate not trusted")


def _validate_certificate(certificate: Certificate) -> None:
    _check_validity_period(certificate)
    _check_signature(certificate)


def _invalid_certificate_response(headers: Headers) -> Optional[JSONResponse]:
    try:
        cert_b64 = headers["certificate"]
    except KeyError:
        return JSONResponse(
            status_code=HTTP_400_BAD_REQUEST,
            content={"detail": "Client certificate missing in header"},
        )
    try:
        cert = _decode_base64_cert(cert_b64)
    except ValueError as excpt:
        return JSONResponse(
            status_code=HTTP_400_BAD_REQUEST,
            content={"detail": str(excpt)},
        )
    try:
        _validate_certificate(cert)
    except CertificateValidationError as excpt:
        return JSONResponse(
            status_code=HTTP_401_UNAUTHORIZED,
            content={"detail": str(excpt)},
        )
    return None


class CertValidationRoute(APIRoute):
    def get_route_handler(self) -> Callable[[Request], Coroutine[Any, Any, Response]]:
        original_route_handler = super().get_route_handler()

        async def custom_route_handler(request: Request) -> Response:
            if invalid_cert_response := _invalid_certificate_response(request.headers):
                return invalid_cert_response
            response: Response = await original_route_handler(request)
            return response

        return custom_route_handler
