#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os
from pathlib import Path
from shutil import copyfileobj
from tempfile import mkstemp
from typing import Dict

from fastapi import FastAPI, File, Form, HTTPException, UploadFile

app = FastAPI()

OMD_ROOT = Path(os.environ.get("OMD_ROOT", ""))
AGENT_OUTPUT_DIR = OMD_ROOT / "var/marcv/received_output"


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
        raise HTTPException(status_code=403, detail="Host is not registered")

    return {"message": "Agent data saved."}
