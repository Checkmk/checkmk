#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from enum import auto, Enum
from typing import Annotated, assert_never, Final

from cryptography.x509.oid import NameOID
from fastapi import Header, HTTPException, Path
from fastapi.params import Depends

from cmk.agent_receiver.lib.certs import agent_root_ca, relay_root_ca
from cmk.agent_receiver.lib.log import logger

INJECTED_UUID_HEADER: Final[str] = "verified-uuid"
INJECTED_ISSUER_HEADER: Final[str] = "verified-issuer-cn"


class ExpectedCA(Enum):
    """The CA an mTLS-authenticated endpoint's client certificates must be issued by."""

    AGENT = auto()
    RELAY = auto()


def _common_name_of(expected_ca: ExpectedCA) -> str:
    match expected_ca:
        case ExpectedCA.AGENT:
            ca_certificate, _ = agent_root_ca()
        case ExpectedCA.RELAY:
            ca_certificate, _ = relay_root_ca()
        case _:
            assert_never(expected_ca)
    cn_attributes = ca_certificate.subject.get_attributes_for_oid(NameOID.COMMON_NAME)
    if not cn_attributes:
        raise ValueError(f"{expected_ca.name} CA certificate does not contain a Common Name (CN)")
    cn_value = cn_attributes[0].value
    assert isinstance(cn_value, str)
    return cn_value


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
    4. If the subject CN doesn't match the URL UUID, or the issuer CN doesn't match
       the CA named by `expected_ca`, the request is rejected with the status code
       provided as argument.

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
        HTTPException: if the certificate CN doesn't match the URL UUID, or the
            certificate wasn't issued by the expected CA

    Example:
        @router.post(
            "/{uuid}/data",
            dependencies=[mtls_authorization_dependency("uuid", 400, ExpectedCA.AGENT)],
        )
        async def receive_data(uuid: str): ...
    """

    def _mtls_authorization_check(
        header_uuid: Annotated[str, Header(alias=INJECTED_UUID_HEADER)],
        header_issuer_cn: Annotated[str, Header(alias=INJECTED_ISSUER_HEADER)],
        path_uuid: Annotated[str, Path(alias=path_alias)],
    ) -> None:
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

    return Depends(_mtls_authorization_check)
