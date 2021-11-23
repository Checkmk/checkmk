#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os
from http import HTTPStatus
from typing import Any

import requests
from fastapi import HTTPException


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


def _forward_get(
    endpoint: str,
    authentication: str,
) -> requests.Response:
    return requests.get(
        f"{_local_rest_api_url()}/{endpoint}",
        headers={
            "Authorization": authentication,
        },
    )


def _forward_put(
    endpoint: str,
    authentication: str,
    json_body: Any,
) -> requests.Response:
    return requests.put(
        f"{_local_rest_api_url()}/{endpoint}",
        headers={
            "Authorization": authentication,
            "Accept": "application/json",
        },
        json=json_body,
    )


def get_root_cert(authentication: str) -> requests.Response:
    return _forward_get(
        "root_cert",
        authentication,
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


def host_exists(
    authentication: str,
    host_name: str,
) -> bool:
    return (
        _forward_get(f"objects/host_config/{host_name}", authentication).status_code
        == HTTPStatus.OK
    )


def link_host_with_uuid(
    authentication: str,
    host_name: str,
    uuid: str,
) -> None:
    if (
        respone := _forward_put(
            f"objects/host_config/{host_name}/actions/link_uuid/invoke",
            authentication,
            {"uuid": uuid},
        )
    ).status_code != HTTPStatus.NO_CONTENT:
        raise HTTPException(
            status_code=respone.status_code,
            detail=respone.text,
        )
