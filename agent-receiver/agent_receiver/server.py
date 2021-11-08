#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os
from shutil import copyfileobj
from tempfile import mkstemp
from typing import Dict, Mapping, Optional

from cryptography.x509 import load_pem_x509_csr
from cryptography.x509.oid import NameOID
from fastapi import FastAPI, File, Form, Header, HTTPException, UploadFile
from pydantic import BaseModel

from agent_receiver.checkmk_rest_api import post_csr
from agent_receiver.constants import AGENT_OUTPUT_DIR
from agent_receiver.log import logger

app = FastAPI()


class CSRBody(BaseModel):
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


@app.post("/csr")
async def sign_csr(
    *,
    authentication: Optional[str] = Header(None),
    csr_body: CSRBody,
) -> Mapping[str, str]:
    rest_api_csr_resp = post_csr(
        str(authentication),
        csr_body.csr,
    )
    if rest_api_csr_resp.ok:
        logger.info(
            "uuid=%s CSR signed",
            _uuid_from_pem_csr(csr_body.csr),
        )
        return rest_api_csr_resp.json()

    logger.info(
        "uuid=%s CSR failed with %s",
        _uuid_from_pem_csr(csr_body.csr),
        rest_api_csr_resp.text,
    )
    raise HTTPException(
        status_code=rest_api_csr_resp.status_code,
        detail=rest_api_csr_resp.text,
    )


@app.post("/agent-data")
async def agent_data(
    uuid: str = Form(...), upload_file: UploadFile = File(...)
) -> Dict[str, str]:
    file_dir = AGENT_OUTPUT_DIR / uuid
    file_path = file_dir / "received_output"

    try:
        file_handle, temp_path = mkstemp(dir=file_dir)
        with open(file_handle, "wb") as temp_file:
            copyfileobj(upload_file.file, temp_file)

        os.rename(temp_path, file_path)

    except FileNotFoundError:
        logger.error(f"uuid={uuid} Host is not registered")
        raise HTTPException(status_code=403, detail="Host is not registered")

    logger.info(f"uuid={uuid} Agent data saved")
    return {"message": "Agent data saved."}
