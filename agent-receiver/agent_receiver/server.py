#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
import os
import shutil
import tempfile
from contextlib import suppress
from pathlib import Path
from typing import Mapping

from agent_receiver.certificates import CertValidationRoute, uuid_from_pem_csr
from agent_receiver.checkmk_rest_api import (
    cmk_edition,
    get_root_cert,
    host_exists,
    link_host_with_uuid,
    post_csr,
)
from agent_receiver.constants import AGENT_OUTPUT_DIR, REGISTRATION_REQUESTS
from agent_receiver.log import logger
from agent_receiver.models import PairingBody, RegistrationWithHNBody, RegistrationWithLabelsBody
from fastapi import APIRouter, Depends, FastAPI, File, Header, HTTPException, Response, UploadFile
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from starlette.status import HTTP_204_NO_CONTENT, HTTP_404_NOT_FOUND, HTTP_501_NOT_IMPLEMENTED

app = FastAPI()
cert_validation_router = APIRouter(route_class=CertValidationRoute)
security = HTTPBasic()


@app.post("/pairing")
async def pairing(
    *,
    credentials: HTTPBasicCredentials = Depends(security),
    pairing_body: PairingBody,
) -> Mapping[str, str]:
    uuid = uuid_from_pem_csr(pairing_body.csr)

    if not (rest_api_root_cert_resp := get_root_cert(credentials)).ok:
        logger.error(
            "uuid=%s Getting root cert failed with %s",
            uuid,
            rest_api_root_cert_resp.text,
        )
        raise HTTPException(
            status_code=rest_api_root_cert_resp.status_code,
            detail=rest_api_root_cert_resp.text,
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
            detail=rest_api_csr_resp.text,
        )
    logger.info(
        "uuid=%s CSR signed",
        uuid,
    )

    return {
        "root_cert": rest_api_root_cert_resp.json()["cert"],
        "client_cert": rest_api_csr_resp.json()["cert"],
    }


@app.post(
    "/register_with_hostname",
    status_code=HTTP_204_NO_CONTENT,
)
async def register_with_hostname(
    *,
    credentials: HTTPBasicCredentials = Depends(security),
    registration_body: RegistrationWithHNBody,
) -> Response:
    if not host_exists(
        credentials,
        registration_body.host_name,
    ):
        raise HTTPException(
            status_code=HTTP_404_NOT_FOUND,
            detail=f"Host {registration_body.host_name} does not exist",
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
    (dir_new_requests := REGISTRATION_REQUESTS / "NEW").mkdir(
        mode=0o770,
        parents=True,
        exist_ok=True,
    )
    (new_request := dir_new_requests / f"{registration_body.uuid}.json").write_text(
        json.dumps(
            {
                "uuid": registration_body.uuid,
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


@app.post(
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


def _move_ready_file(uuid: str) -> None:
    with suppress(FileNotFoundError):
        # TODO: use RegistrationState.READY.name
        (REGISTRATION_REQUESTS / "READY" / f"{uuid}.json").rename(
            REGISTRATION_REQUESTS / "DISCOVERABLE" / f"{uuid}.json"
        )


@cert_validation_router.post(
    "/agent_data/{uuid}",
    status_code=HTTP_204_NO_CONTENT,
)
async def agent_data(
    uuid: str,
    *,
    certificate: str = Header(...),
    monitoring_data: UploadFile = File(...),
) -> Response:
    target_dir = AGENT_OUTPUT_DIR / uuid
    target_path = target_dir / "received-output"

    try:
        temp_file = tempfile.NamedTemporaryFile(dir=target_dir, delete=False)
    except FileNotFoundError:
        # TODO: What are the exact criteria for "registered" and "being a push host"?
        logger.error(
            "uuid=%s Host is not registered or is not configured as push host.",
            uuid,
        )
        raise HTTPException(status_code=403, detail="Host is not registered")

    shutil.copyfileobj(monitoring_data.file, temp_file)
    try:
        os.rename(temp_file.name, target_path)
    finally:
        Path(temp_file.name).unlink(missing_ok=True)

    _move_ready_file(uuid)

    logger.info(
        "uuid=%s Agent data saved",
        uuid,
    )
    return Response(status_code=HTTP_204_NO_CONTENT)


app.include_router(cert_validation_router)
