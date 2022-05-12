#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
import os
import tempfile
from contextlib import suppress
from pathlib import Path
from uuid import UUID

from agent_receiver.apps import agent_receiver_app, cert_validation_router
from agent_receiver.certificates import uuid_from_pem_csr
from agent_receiver.checkmk_rest_api import (
    cmk_edition,
    get_root_cert,
    host_configuration,
    HostConfiguration,
    link_host_with_uuid,
    parse_error_response_body,
    post_csr,
)
from agent_receiver.decompression import DecompressionError, Decompressor
from agent_receiver.log import logger
from agent_receiver.models import (
    HostTypeEnum,
    PairingBody,
    PairingResponse,
    RegistrationStatus,
    RegistrationStatusEnum,
    RegistrationWithHNBody,
    RegistrationWithLabelsBody,
)
from agent_receiver.site_context import r4r_dir, site_name
from agent_receiver.utils import get_registration_status_from_file, Host
from fastapi import Depends, File, Header, HTTPException, Response, UploadFile
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from starlette.status import HTTP_204_NO_CONTENT, HTTP_403_FORBIDDEN, HTTP_501_NOT_IMPLEMENTED

security = HTTPBasic()


@agent_receiver_app.post("/pairing", response_model=PairingResponse)
async def pairing(
    *,
    credentials: HTTPBasicCredentials = Depends(security),
    pairing_body: PairingBody,
) -> PairingResponse:
    uuid = uuid_from_pem_csr(pairing_body.csr)

    if not (rest_api_root_cert_resp := get_root_cert(credentials)).ok:
        logger.error(
            "uuid=%s Getting root cert failed with %s",
            uuid,
            rest_api_root_cert_resp.text,
        )
        raise HTTPException(
            status_code=rest_api_root_cert_resp.status_code,
            detail=parse_error_response_body(rest_api_root_cert_resp.text),
        )
    logger.info(
        "uuid=%s Got root cert",
        uuid,
    )

    if not (
        rest_api_csr_resp := post_csr(
            credentials,
            pairing_body.csr,
        )
    ).ok:
        logger.error(
            "uuid=%s CSR failed with %s",
            uuid,
            rest_api_csr_resp.text,
        )
        raise HTTPException(
            status_code=rest_api_csr_resp.status_code,
            detail=parse_error_response_body(rest_api_csr_resp.text),
        )
    logger.info(
        "uuid=%s CSR signed",
        uuid,
    )

    return PairingResponse(
        root_cert=rest_api_root_cert_resp.json()["cert"],
        client_cert=rest_api_csr_resp.json()["cert"],
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


@agent_receiver_app.post(
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
            credentials,
            registration_body.host_name,
        )
    )
    link_host_with_uuid(
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


@agent_receiver_app.post(
    "/register_with_labels",
    status_code=HTTP_204_NO_CONTENT,
)
async def register_with_labels(
    *,
    credentials: HTTPBasicCredentials = Depends(security),
    registration_body: RegistrationWithLabelsBody,
) -> Response:
    if not (edition := cmk_edition(credentials)).supports_registration_with_labels():
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


@cert_validation_router.post(
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

    try:
        _store_agent_data(
            host.source_path,
            decompressed_agent_data,
        )
    except FileNotFoundError:
        # We only end up here in case someone re-configures the host at exactly the same time when
        # data is being pushed. To avoid internal server errors, we still handle this case.
        logger.error(
            "uuid=%s Host is not registered or not configured as push host.",
            uuid,
        )
        raise HTTPException(
            status_code=403,
            detail="Host is not registered or not configured as push host",
        )

    _move_ready_file(uuid)

    logger.info(
        "uuid=%s Agent data saved",
        uuid,
    )
    return Response(status_code=HTTP_204_NO_CONTENT)


@cert_validation_router.get("/registration_status/{uuid}", response_model=RegistrationStatus)
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
