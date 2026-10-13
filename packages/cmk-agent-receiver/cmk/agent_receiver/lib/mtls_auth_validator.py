#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import pathlib
from enum import auto, Enum
from typing import Annotated, assert_never, Final

from fastapi import Header, HTTPException, Path
from fastapi.params import Depends

from cmk.agent_receiver.lib.certs import agent_root_ca, is_revoked, relay_root_ca
from cmk.agent_receiver.lib.config import get_config
from cmk.agent_receiver.lib.log import logger

INJECTED_UUID_HEADER: Final[str] = "verified-uuid"
INJECTED_ISSUER_HEADER: Final[str] = "verified-issuer-cn"
INJECTED_SERIAL_HEADER: Final[str] = "verified-serial"


class ExpectedCA(Enum):
    """The CA an mTLS-authenticated endpoint's client certificates must be issued by."""

    AGENT = auto()
    RELAY = auto()


def _common_name_of(expected_ca: ExpectedCA) -> str:
    match expected_ca:
        case ExpectedCA.AGENT:
            ca_certificate = agent_root_ca().certificate
        case ExpectedCA.RELAY:
            ca_certificate = relay_root_ca().certificate
        case _:
            assert_never(expected_ca)
    if (cn := ca_certificate.common_name) is None:
        raise ValueError(f"{expected_ca.name} CA certificate does not contain a Common Name (CN)")
    return cn


def _crl_path_of(expected_ca: ExpectedCA) -> pathlib.Path:
    config = get_config()
    match expected_ca:
        case ExpectedCA.AGENT:
            return config.agent_crl_path
        case ExpectedCA.RELAY:
            return config.relay_crl_path
        case _:
            assert_never(expected_ca)


def mtls_authorization_dependency(
    path_alias: str, failure_status_code: int, expected_ca: ExpectedCA
) -> Depends:
    """FastAPI dependency generator for mutual TLS (mTLS) authorization.

    This function validates that the client certificate common name (CN) matches the
    UUID provided in the request URL path, and that the certificate was issued by the
    expected CA. It relies on a custom Uvicorn worker (ClientCertWorker) that intercepts
    incoming HTTP requests and injects the verified client certificate's CN and issuer CN
    as custom HTTP headers.

    How it works:
    1. The ClientCertWorker uses a custom H11Protocol (_ClientCertProtocol) that
       extracts the subject and issuer CN from the client's SSL certificate during
       TLS handshake
    2. These are injected into the request headers using INJECTED_UUID_HEADER
       ("verified-uuid") and INJECTED_ISSUER_HEADER ("verified-issuer-cn") before the
       request reaches FastAPI
    3. This dependency function extracts both injected headers and the UUID from the
       URL path
    4. If the subject CN doesn't match the URL UUID, if the issuer CN doesn't match
       the CA named by `expected_ca`, or if that CA has revoked the certificate, the
       request is rejected with the status code provided as argument.

    This approach ensures:
    - The certificate validation happens at the protocol level before FastAPI processing
    - The CN cannot be spoofed by clients (it's extracted from the verified TLS connection)
    - A certificate issued for one identity space (e.g. agents) cannot authenticate as an
      identity in another (e.g. relays), even if the UUIDs happen to collide -- the Uvicorn
      workers trust one combined CA bundle for the TLS handshake itself, so this must be
      enforced here
    - Individual endpoints or routers can opt-in to mTLS authorization by adding
      this dependency

    Raises:
        HTTPException: if no verified client certificate was presented (an
            injected header is absent), if the certificate CN doesn't match the
            URL UUID, if the certificate wasn't issued by the expected CA, or if
            the expected CA has revoked the certificate

    Example:
        @router.post(
            "/{uuid}/data",
            dependencies=[mtls_authorization_dependency("uuid", 400, ExpectedCA.AGENT)],
        )
        async def receive_data(uuid: str): ...
    """

    def _mtls_authorization_check(
        path_uuid: Annotated[str, Path(alias=path_alias)],
        header_uuid: Annotated[str | None, Header(alias=INJECTED_UUID_HEADER)] = None,
        header_issuer_cn: Annotated[str | None, Header(alias=INJECTED_ISSUER_HEADER)] = None,
        header_serial: Annotated[str | None, Header(alias=INJECTED_SERIAL_HEADER)] = None,
    ) -> None:
        # A missing header means the worker injected no verified identity because
        # no client certificate was presented. Reject explicitly -- never via the
        # equality checks below, so an absent identity can never match a value the
        # caller controls in the URL. Rejecting here also keeps the endpoint's
        # deliberate status and the human-readable no-certificate message instead
        # of FastAPI's default 422.
        if header_uuid is None or header_serial is None:
            raise HTTPException(
                status_code=failure_status_code,
                detail="No verified client certificate provided",
            )
        if header_uuid != path_uuid:
            raise HTTPException(
                status_code=failure_status_code,
                detail=f"Verified client UUID ({header_uuid}) does not match UUID in URL ({path_uuid})",
            )
        if header_issuer_cn != (expected := _common_name_of(expected_ca)):
            logger.warning(
                "uuid=%(uuid)s Rejected mTLS request: certificate issuer %(issuer)r does not "
                "match the expected %(expected_ca)s CA %(expected)r",
                {
                    "uuid": path_uuid,
                    "issuer": header_issuer_cn,
                    "expected_ca": expected_ca.name,
                    "expected": expected,
                },
            )
            raise HTTPException(
                status_code=failure_status_code,
                detail=(
                    f"Client certificate was not issued by the expected CA "
                    f"(issuer: {header_issuer_cn!r}, expected: {expected!r})"
                ),
            )
        if is_revoked(_crl_path_of(expected_ca), int(header_serial, 16)):
            logger.warning(
                "uuid=%(uuid)s Rejected mTLS request: the %(expected_ca)s CA revoked the "
                "certificate with serial number %(serial)s",
                {"uuid": path_uuid, "expected_ca": expected_ca.name, "serial": header_serial},
            )
            raise HTTPException(
                status_code=failure_status_code,
                detail=f"Client certificate {header_serial} has been revoked",
            )

    return Depends(_mtls_authorization_check)
