#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os
from typing import Any

import requests


def _local_rest_api_url() -> str:
    return f"http://localhost/{os.environ['OMD_SITE']}/check_mk/api/1.0"


def _forward_post(
    endpoint: str,
    authentication: str,
    json_body: Any,
) -> requests.Response:
    return requests.post(
        f"{_local_rest_api_url()}/{endpoint}",
        headers={
            "Authorization": authentication,
            "Accept": "application/json",
        },
        json=json_body,
    )


def post_csr(
    authentication: str,
    csr: str,
) -> requests.Response:
    return _forward_post(
        "csr",
        authentication,
        {"csr": csr},
    )
