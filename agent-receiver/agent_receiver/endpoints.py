#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
import os
import tempfile
from contextlib import suppress
from pathlib import Path
from uuid import UUID

from agent_receiver.apps_and_routers import AGENT_RECEIVER_APP, UUID_VALIDATION_ROUTER
from agent_receiver.checkmk_rest_api import (
    cmk_edition,
    controller_certificate_settings,
    get_root_cert,
    host_configuration,
    HostConfiguration,
    link_host_with_uuid,
    post_csr,
)
from agent_receiver.decompression import DecompressionError, Decompressor
from agent_receiver.log import logger
from agent_receiver.models import (
    CertificateRenewalBody,
    CsrField,
    HostTypeEnum,
    PairingBody,
    PairingResponse,
    RegistrationStatus,
    RegistrationStatusEnum,
    RegistrationWithHNBody,
    RegistrationWithLabelsBody,
    RenewCertResponse,
)
from agent_receiver.site_context import r4r_dir, site_name
from agent_receiver.utils import (
    get_registration_status_from_file,
    Host,
    internal_credentials,
    uuid_from_pem_csr,
)
from cryptography.x509 import Certificate
from fastapi import Depends, File, Header, HTTPException, Response, UploadFile
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from starlette.status import (
    HTTP_204_NO_CONTENT,
    HTTP_400_BAD_REQUEST,
    HTTP_403_FORBIDDEN,
    HTTP_501_NOT_IMPLEMENTED,
)

from .certs import extract_cn_from_csr, serialize_to_pem, sign_agent_csr

# pylint does not understand the syntax of agent_receiver.checkmk_rest_api.log_http_exception
# pylint: disable=too-many-function-args

security = HTTPBasic()


def _validate_uuid_against_csr(uuid: UUID, csr_field: CsrField) -> None:
    if str(uuid) != (cn := extract_cn_from_csr(csr_field.csr)):
        raise HTTPException(
            status_code=HTTP_400_BAD_REQUEST,
            detail=f"UUID ({uuid}) does not match CN ({cn}) of CSR.",
        )


def _sign_agent_csr(uuid: UUID, csr_field: CsrField) -> Certificate:
    return sign_agent_csr(
        csr_field.csr,
        controller_certificate_settings(
            f"uuid={uuid} Querying agent controller certificate settings failed",
            internal_credentials(),
        ).lifetime_in_months,
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
            detail=f"This host is monitored on the site {host_config.site}, but you tried to register it at the site {site_name()}.",
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


def _write_registration_file(
    username: str,
    registration_body: RegistrationWithLabelsBody,
) -> None:
    (dir_new_requests := r4r_dir() / RegistrationStatusEnum.NEW.name).mkdir(
        mode=0o770,
        parents=True,
        exist_ok=True,
    )
    (new_request := dir_new_requests / f"{registration_body.uuid}.json").write_text(
        json.dumps(
            {
                "uuid": str(registration_body.uuid),
                "username": username,
                "agent_labels": registration_body.agent_labels,
            }
        )
    )
    new_request.chmod(0o660)
    logger.info(
        "uuid=%s Stored new request for registration",
        registration_body.uuid,
    )


@AGENT_RECEIVER_APP.post(
    "/register_with_labels",
    status_code=HTTP_204_NO_CONTENT,
)
async def register_with_labels(
    *,
    credentials: HTTPBasicCredentials = Depends(security),
    registration_body: RegistrationWithLabelsBody,
) -> Response:
    if not (
        edition := cmk_edition(
            f"uuid={registration_body.uuid} Querying Checkmk edition failed",
            credentials,
        )
    ).supports_registration_with_labels():
        logger.error(
            "uuid=%s Registration with labels not supported",
            registration_body.uuid,
        )
        raise HTTPException(
            status_code=HTTP_501_NOT_IMPLEMENTED,
            detail=f"The Checkmk {edition.value} edition does not support registration with agent labels",
        )
    _write_registration_file(
        credentials.username,
        registration_body,
    )
    return Response(status_code=HTTP_204_NO_CONTENT)


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


def _move_ready_file(uuid: UUID) -> None:
    (dir_discoverable := r4r_dir() / RegistrationStatusEnum.DISCOVERABLE.name).mkdir(exist_ok=True)
    with suppress(FileNotFoundError):
        (r4r_dir() / RegistrationStatusEnum.READY.name / f"{uuid}.json").rename(
            dir_discoverable / f"{uuid}.json"
        )


@UUID_VALIDATION_ROUTER.post(
    "/agent_data/{uuid}",
    status_code=HTTP_204_NO_CONTENT,
)
async def agent_data(
    uuid: UUID,
    *,
    compression: str = Header(...),
    monitoring_data: UploadFile = File(...),
) -> Response:
    host = Host(uuid)
    if not host.registered:
        logger.error(
            "uuid=%s Host is not registered",
            uuid,
        )
        raise HTTPException(
            status_code=HTTP_403_FORBIDDEN,
            detail="Host is not registered",
        )
    if host.host_type is not HostTypeEnum.PUSH:
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
    except ValueError:
        logger.error(
            "uuid=%s Unsupported compression algorithm: %s",
            uuid,
            compression,
        )
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported compression algorithm: {compression}",
        )

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

    _move_ready_file(uuid)

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
    uuid: UUID,
) -> RegistrationStatus:
    host = Host(uuid)
    registration_data = get_registration_status_from_file(uuid)

    if not host.registered:
        if registration_data:
            return RegistrationStatus(
                status=registration_data.status, message=registration_data.message
            )
        raise HTTPException(status_code=404, detail="Host is not registered")

    return RegistrationStatus(
        hostname=host.hostname,
        status=registration_data.status if registration_data else None,
        type=host.host_type,
        message="Host registered",
    )


@UUID_VALIDATION_ROUTER.post(
    "/renew_certificate/{uuid}",
    response_model=RenewCertResponse,
)
async def renew_certificate(
    *,
    uuid: UUID,
    cert_renewal_body: CertificateRenewalBody,
) -> RenewCertResponse:

    # Note: Technically, we could omit the {uuid} part of the endpoint url.
    # We explicitly require it for consistency with other endpoints.
    _validate_uuid_against_csr(uuid, cert_renewal_body.csr)

    # Don't maintain deleted registrations.
    host = Host(uuid)
    if not host.registered:
        logger.error(
            "uuid=%s Host is not registered",
            uuid,
        )
        raise HTTPException(
            status_code=HTTP_403_FORBIDDEN,
            detail="Host is not registered",
        )

    agent_cert = _sign_agent_csr(uuid, cert_renewal_body.csr)

    logger.info(
        "uuid=%s Certificate renewal succeeded",
        uuid,
    )

    return RenewCertResponse(
        agent_cert=serialize_to_pem(agent_cert),
    )
