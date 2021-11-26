#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os
import shutil
import tempfile
from pathlib import Path
from typing import Dict, Mapping, Optional

from agent_receiver.checkmk_rest_api import (
    get_root_cert,
    host_exists,
    link_host_with_uuid,
    post_csr,
)
from agent_receiver.constants import AGENT_OUTPUT_DIR, REGISTRATION_REQUESTS
from agent_receiver.log import logger
from cryptography.x509 import load_pem_x509_csr
from cryptography.x509.oid import NameOID
from fastapi import FastAPI, File, Form, Header, HTTPException, Response, UploadFile
from pydantic import BaseModel
from starlette.status import HTTP_204_NO_CONTENT, HTTP_404_NOT_FOUND

app = FastAPI()


class PairingBody(BaseModel):
    csr: str


def _uuid_from_pem_csr(pem_csr: str) -> str:
    try:
        return (
            load_pem_x509_csr(pem_csr.encode())
            .subject.get_attributes_for_oid(NameOID.COMMON_NAME)[0]
            .value
        )
    except ValueError:
        return "[CSR parsing failed]"


@app.post("/pairing")
async def pairing(
    *,
    authentication: str = Header(...),
    pairing_body: PairingBody,
) -> Mapping[str, str]:
    uuid = _uuid_from_pem_csr(pairing_body.csr)

    if not (rest_api_root_cert_resp := get_root_cert(authentication)).ok:
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
            authentication,
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


class RegistrationWithHNBody(BaseModel):
    uuid: str
    host_name: str


@app.post(
    "/register_with_hostname",
    status_code=HTTP_204_NO_CONTENT,
)
async def register_with_hostname(
    *,
    authentication: str = Header(...),
    registration_body: RegistrationWithHNBody,
) -> Response:
    if not host_exists(
        authentication,
        registration_body.host_name,
    ):
        raise HTTPException(
            status_code=HTTP_404_NOT_FOUND,
            detail=f"Host {registration_body.host_name} does not exist",
        )
    link_host_with_uuid(
        authentication,
        registration_body.host_name,
        registration_body.uuid,
    )
    logger.info(
        "uuid=%s registered host %s",
        registration_body.uuid,
        registration_body.host_name,
    )
    return Response(status_code=HTTP_204_NO_CONTENT)


def get_hostname(uuid: str) -> Optional[str]:
    link_path = AGENT_OUTPUT_DIR / uuid

    try:
        target_path = os.readlink(link_path)
    except FileNotFoundError:
        return None

    return Path(target_path).name


@app.post("/agent_data")
async def agent_data(uuid: str = Form(...), upload_file: UploadFile = File(...)) -> Dict[str, str]:
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

    shutil.copyfileobj(upload_file.file, temp_file)
    try:
        os.rename(temp_file.name, target_path)
    finally:
        Path(temp_file.name).unlink(missing_ok=True)

    ready_file = REGISTRATION_REQUESTS / "READY" / f"{uuid}.json"
    hostname = get_hostname(uuid)

    if ready_file.exists() and hostname:
        try:
            shutil.move(ready_file, REGISTRATION_REQUESTS / "DISCOVERABLE" / f"{hostname}.json")
        except FileNotFoundError:
            logger.warning(
                "uuid=%s Could not move registration request from READY to DISCOVERABLE",
                uuid,
            )

    logger.info(
        "uuid=%s Agent data saved",
        uuid,
    )
    return {"message": "Agent data saved."}
