#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os
import tempfile
from functools import cache
from pathlib import Path
from typing import assert_never

from cryptography.x509 import Certificate
from fastapi import Depends, File, Header, HTTPException, Response, UploadFile
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pydantic import UUID4
from starlette.status import (
    HTTP_204_NO_CONTENT,
    HTTP_400_BAD_REQUEST,
    HTTP_403_FORBIDDEN,
    HTTP_404_NOT_FOUND,
    HTTP_500_INTERNAL_SERVER_ERROR,
    HTTP_501_NOT_IMPLEMENTED,
)

from .apps_and_routers import AGENT_RECEIVER_APP, UUID_VALIDATION_ROUTER
from .certs import (
    agent_root_ca,
    current_time_naive,
    extract_cn_from_csr,
    serialize_to_pem,
    sign_agent_csr,
    site_root_certificate,
)
from .checkmk_rest_api import (
    cmk_edition,
    controller_certificate_settings,
    get_root_cert,
    host_configuration,
    HostConfiguration,
    link_host_with_uuid,
    post_csr,
    register,
)
from .decompression import DecompressionError, Decompressor
from .log import logger
from .models import (
    CertificateRenewalBody,
    ConnectionMode,
    CsrField,
    PairingBody,
    PairingResponse,
    R4RStatus,
    RegisterExistingBody,
    RegisterExistingResponse,
    RegisterNewBody,
    RegisterNewOngoingResponseDeclined,
    RegisterNewOngoingResponseInProgress,
    RegisterNewOngoingResponseSuccess,
    RegisterNewResponse,
    RegistrationStatus,
    RegistrationStatusV2ResponseNotRegistered,
    RegistrationStatusV2ResponseRegistered,
    RegistrationWithHNBody,
    RenewCertResponse,
    RequestForRegistration,
)
from .site_context import site_name
from .utils import (
    internal_credentials,
    NotRegisteredException,
    R4R,
    RegisteredHost,
    uuid_from_pem_csr,
)

security = HTTPBasic()


def _validate_uuid_against_csr(uuid: UUID4, csr_field: CsrField) -> None:
    if str(uuid) != (cn := extract_cn_from_csr(csr_field.csr)):
        raise HTTPException(
            status_code=HTTP_400_BAD_REQUEST,
            detail=f"UUID ({uuid}) does not match CN ({cn}) of CSR.",
        )


def _sign_agent_csr(uuid: UUID4, csr_field: CsrField) -> Certificate:
    return sign_agent_csr(
        csr_field.csr,
        controller_certificate_settings(
            f"uuid={uuid} Querying agent controller certificate settings failed",
            internal_credentials(),
        ).lifetime_in_months,
        agent_root_ca(),
        current_time_naive(),
    )


@cache
def _pem_serizialized_site_root_cert() -> str:
    return serialize_to_pem(site_root_certificate())


@AGENT_RECEIVER_APP.post(
    "/register_existing",
    response_model=RegisterExistingResponse,
)
async def register_existing(
    *,
    credentials: HTTPBasicCredentials = Depends(security),
    registration_body: RegisterExistingBody,
) -> RegisterExistingResponse:
    _validate_uuid_against_csr(registration_body.uuid, registration_body.csr)
    root_cert = _pem_serizialized_site_root_cert()
    agent_cert = serialize_to_pem(
        _sign_agent_csr(
            registration_body.uuid,
            registration_body.csr,
        )
    )
    register_response = register(
        f"uuid={registration_body.uuid} Registration failed",
        credentials,
        registration_body.uuid,
        registration_body.host_name,
    )
    logger.info(
        "uuid=%s registered host %s",
        registration_body.uuid,
        registration_body.host_name,
    )
    return RegisterExistingResponse(
        root_cert=root_cert,
        agent_cert=agent_cert,
        connection_mode=register_response.connection_mode,
    )


@AGENT_RECEIVER_APP.post("/pairing", response_model=PairingResponse)
async def pairing(
    *,
    credentials: HTTPBasicCredentials = Depends(security),
    pairing_body: PairingBody,
) -> PairingResponse:
    uuid = uuid_from_pem_csr(pairing_body.csr)

    root_cert = get_root_cert(
        f"uuid={uuid} Getting root cert failed",
        credentials,
    )
    client_cert = post_csr(
        f"uuid={uuid} CSR signing failed",
        credentials,
        pairing_body.csr,
    )

    logger.info(
        "uuid=%s Pairing succesful",
        uuid,
    )

    return PairingResponse(
        root_cert=root_cert,
        client_cert=client_cert,
    )


def _validate_registration_request(host_config: HostConfiguration) -> None:
    if host_config.site != site_name():
        raise HTTPException(
            status_code=HTTP_403_FORBIDDEN,
            detail=(
                f"This host is monitored on the site {host_config.site}, "
                f"but you tried to register it at the site {site_name()}."
            ),
        )
    if host_config.is_cluster:
        raise HTTPException(
            status_code=HTTP_403_FORBIDDEN,
            detail="This host is a cluster host. Register its nodes instead.",
        )


@AGENT_RECEIVER_APP.post(
    "/register_with_hostname",
    status_code=HTTP_204_NO_CONTENT,
)
async def register_with_hostname(
    *,
    credentials: HTTPBasicCredentials = Depends(security),
    registration_body: RegistrationWithHNBody,
) -> Response:
    _validate_registration_request(
        host_configuration(
            f"uuid={registration_body.uuid} Getting host configuration failed",
            credentials,
            registration_body.host_name,
        )
    )
    link_host_with_uuid(
        f"uuid={registration_body.uuid} Linking host with UUID failed",
        credentials,
        registration_body.host_name,
        registration_body.uuid,
    )
    logger.info(
        "uuid=%s registered host %s",
        registration_body.uuid,
        registration_body.host_name,
    )
    return Response(status_code=HTTP_204_NO_CONTENT)


@AGENT_RECEIVER_APP.post(
    "/register_new",
    response_model=RegisterNewResponse,
)
async def register_new(
    *,
    credentials: HTTPBasicCredentials = Depends(security),
    registration_body: RegisterNewBody,
) -> RegisterNewResponse:
    _validate_is_allowed(credentials, registration_body.uuid)
    _validate_uuid_against_csr(registration_body.uuid, registration_body.csr)

    root_cert = _pem_serizialized_site_root_cert()

    R4R(
        status=R4RStatus.NEW,
        request=RequestForRegistration(
            uuid=registration_body.uuid,
            username=credentials.username,
            agent_labels=registration_body.agent_labels,
            agent_cert=serialize_to_pem(
                _sign_agent_csr(
                    registration_body.uuid,
                    registration_body.csr,
                )
            ),
        ),
    ).write()
    logger.info(
        "uuid=%s Stored new request for registration",
        registration_body.uuid,
    )

    return RegisterNewResponse(root_cert=root_cert)


@AGENT_RECEIVER_APP.post(
    "/register_new_ongoing/{uuid}",
    # https://fastapi.tiangolo.com/tutorial/extra-models/#union-or-anyof
    response_model=RegisterNewOngoingResponseInProgress
    | RegisterNewOngoingResponseDeclined
    | RegisterNewOngoingResponseSuccess,
)
async def register_new_ongoing(
    uuid: UUID4,
    *,
    credentials: HTTPBasicCredentials = Depends(security),
) -> (
    RegisterNewOngoingResponseInProgress
    | RegisterNewOngoingResponseDeclined
    | RegisterNewOngoingResponseSuccess
):
    _validate_is_allowed(credentials, uuid)

    try:
        r4r = R4R.read(uuid)
    except FileNotFoundError as e:
        logger.error(
            "uuid=%s No registration in progress",
            uuid,
        )
        raise HTTPException(
            status_code=HTTP_404_NOT_FOUND,
            detail="No registration with this UUID in progress",
        ) from e
    if r4r.request.username != credentials.username:
        logger.error(
            "uuid=%s Username mismatch",
            uuid,
        )
        raise HTTPException(
            status_code=HTTP_403_FORBIDDEN,
            detail="A registration is in progress, but it was triggered by a different user",
        )

    match r4r.status:
        case R4RStatus.NEW | R4RStatus.PENDING:
            logger.info(
                "uuid=%s Registration in progress",
                uuid,
            )
            return RegisterNewOngoingResponseInProgress()
        case R4RStatus.DECLINED:
            logger.info(
                "uuid=%s Registration declined",
                uuid,
            )
            return RegisterNewOngoingResponseDeclined(
                reason=r4r.request.rejection_notice() or "Reason unknown"
            )
        case R4RStatus.DISCOVERABLE:
            try:
                host = RegisteredHost(uuid)
            except NotRegisteredException as e:
                logger.error(
                    "uuid=%s Not registered even though r4r says otherwise!?",
                    uuid,
                )
                raise HTTPException(
                    status_code=HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Registration was successful, but host is still not registered. This "
                    "should not have happend. Maybe someone removed the registration by hand?",
                ) from e
            logger.info(
                "uuid=%s Registration successful",
                uuid,
            )
            return RegisterNewOngoingResponseSuccess(
                agent_cert=r4r.request.agent_cert,
                connection_mode=host.connection_mode,
            )

    assert_never(r4r.status)


def _validate_is_allowed(credentials: HTTPBasicCredentials, uuid: UUID4) -> None:
    if not (
        edition := cmk_edition(
            f"uuid={uuid} Querying Checkmk edition failed",
            credentials,
        )
    ).supports_register_new():
        logger.error(
            "uuid=%s Registration of new hosts not suppored",
            uuid,
        )
        raise HTTPException(
            status_code=HTTP_501_NOT_IMPLEMENTED,
            detail=(
                f"The Checkmk {edition.value} edition does not support registration of new hosts"
            ),
        )


def _store_agent_data(
    target_dir: Path,
    decompressed_data: bytes,
) -> None:
    target_dir.resolve().mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        dir=target_dir,
        delete=False,
    ) as temp_file:
        try:
            temp_file.write(decompressed_data)
            os.rename(temp_file.name, target_dir / "agent_output")
        finally:
            Path(temp_file.name).unlink(missing_ok=True)


@UUID_VALIDATION_ROUTER.post(
    "/agent_data/{uuid}",
    status_code=HTTP_204_NO_CONTENT,
)
async def agent_data(
    uuid: UUID4,
    *,
    compression: str = Header(...),
    monitoring_data: UploadFile = File(...),
) -> Response:
    try:
        host = RegisteredHost(uuid)
    except NotRegisteredException as e:
        logger.error(
            "uuid=%s Host is not registered",
            uuid,
        )
        raise HTTPException(
            status_code=HTTP_403_FORBIDDEN,
            detail="Host is not registered",
        ) from e
    if host.connection_mode is not ConnectionMode.PUSH:
        logger.error(
            "uuid=%s Host is not a push host",
            uuid,
        )
        raise HTTPException(
            status_code=HTTP_403_FORBIDDEN,
            detail="Host is not a push host",
        )

    try:
        decompressor = Decompressor(compression)
    except ValueError as e:
        logger.error(
            "uuid=%s Unsupported compression algorithm: %s",
            uuid,
            compression,
        )
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported compression algorithm: {compression}",
        ) from e

    try:
        decompressed_agent_data = decompressor(monitoring_data.file.read())
    except DecompressionError as e:
        logger.error(
            "uuid=%s Decompression of agent data failed: %s",
            uuid,
            e,
        )
        raise HTTPException(
            status_code=400,
            detail="Decompression of agent data failed",
        ) from e

    _store_agent_data(
        host.source_path,
        decompressed_agent_data,
    )

    logger.info(
        "uuid=%s Agent data saved",
        uuid,
    )
    return Response(status_code=HTTP_204_NO_CONTENT)


@UUID_VALIDATION_ROUTER.get(
    "/registration_status/{uuid}",
    response_model=RegistrationStatus,
)
async def registration_status(
    uuid: UUID4,
) -> RegistrationStatus:
    try:
        r4r = R4R.read(uuid)
    except FileNotFoundError:
        r4r = None

    try:
        host = RegisteredHost(uuid)
    except NotRegisteredException as e:
        if r4r:
            return RegistrationStatus(
                status=r4r.status,
                message=r4r.request.rejection_notice(),
            )
        raise HTTPException(status_code=404, detail="Host is not registered") from e

    return RegistrationStatus(
        hostname=host.name,
        status=r4r.status if r4r else None,
        connection_mode=host.connection_mode,
        message="Host registered",
        type=host.connection_mode,
    )


@UUID_VALIDATION_ROUTER.get(
    "/registration_status_v2/{uuid}",
    response_model=RegistrationStatusV2ResponseNotRegistered
    | RegistrationStatusV2ResponseRegistered,
)
async def registration_status_v2(
    uuid: UUID4,
) -> RegistrationStatusV2ResponseNotRegistered | RegistrationStatusV2ResponseRegistered:
    try:
        host = RegisteredHost(uuid)
    except NotRegisteredException:
        return RegistrationStatusV2ResponseNotRegistered()
    return RegistrationStatusV2ResponseRegistered(
        hostname=host.name,
        connection_mode=host.connection_mode,
    )


@UUID_VALIDATION_ROUTER.post(
    "/renew_certificate/{uuid}",
    response_model=RenewCertResponse,
)
async def renew_certificate(
    *,
    uuid: UUID4,
    cert_renewal_body: CertificateRenewalBody,
) -> RenewCertResponse:
    # Note: Technically, we could omit the {uuid} part of the endpoint url.
    # We explicitly require it for consistency with other endpoints.
    _validate_uuid_against_csr(uuid, cert_renewal_body.csr)

    # Don't maintain deleted registrations.
    try:
        RegisteredHost(uuid)
    except NotRegisteredException as e:
        logger.error(
            "uuid=%s Host is not registered",
            uuid,
        )
        raise HTTPException(
            status_code=HTTP_403_FORBIDDEN,
            detail="Host is not registered",
        ) from e

    agent_cert = _sign_agent_csr(uuid, cert_renewal_body.csr)

    logger.info(
        "uuid=%s Certificate renewal succeeded",
        uuid,
    )

    return RenewCertResponse(
        agent_cert=serialize_to_pem(agent_cert),
    )
