#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os
from enum import Enum
from http import HTTPStatus
from typing import Any
from uuid import UUID

import requests
from fastapi import HTTPException
from fastapi.security import HTTPBasicCredentials


class CMKEdition(Enum):
    cre = "Raw"
    cfe = "Free"
    cee = "Enterprise"
    cme = "Managed Services"

    def supports_registration_with_labels(self) -> bool:
        """
        >>> CMKEdition["cre"].supports_registration_with_labels()
        False
        >>> CMKEdition["cee"].supports_registration_with_labels()
        True
        """
        # TODO CMK-9171
        return self is CMKEdition.cee


def _local_rest_api_url() -> str:
    return f"http://localhost/{os.environ['OMD_SITE']}/check_mk/api/1.0"


def _credentials_to_rest_api_auth(credentials: HTTPBasicCredentials) -> str:
    """
    >>> _credentials_to_rest_api_auth(HTTPBasicCredentials(username="hans", password="dampf"))
    'Bearer hans dampf'
    """
    return f"Bearer {credentials.username} {credentials.password}"


def _forward_post(
    endpoint: str,
    credentials: HTTPBasicCredentials,
    json_body: Any,
) -> requests.Response:
    return requests.post(
        f"{_local_rest_api_url()}/{endpoint}",
        headers={
            "Authorization": _credentials_to_rest_api_auth(credentials),
            "Accept": "application/json",
        },
        json=json_body,
    )


def _forward_get(
    endpoint: str,
    credentials: HTTPBasicCredentials,
) -> requests.Response:
    return requests.get(
        f"{_local_rest_api_url()}/{endpoint}",
        headers={
            "Authorization": _credentials_to_rest_api_auth(credentials),
        },
    )


def _forward_put(
    endpoint: str,
    credentials: HTTPBasicCredentials,
    json_body: Any,
) -> requests.Response:
    return requests.put(
        f"{_local_rest_api_url()}/{endpoint}",
        headers={
            "Authorization": _credentials_to_rest_api_auth(credentials),
            "Accept": "application/json",
        },
        json=json_body,
    )


def get_root_cert(credentials: HTTPBasicCredentials) -> requests.Response:
    return _forward_get(
        "root_cert",
        credentials,
    )


def post_csr(
    credentials: HTTPBasicCredentials,
    csr: str,
) -> requests.Response:
    return _forward_post(
        "csr",
        credentials,
        {"csr": csr},
    )


def host_exists(
    credentials: HTTPBasicCredentials,
    host_name: str,
) -> bool:
    return (
        _forward_get(
            f"objects/host_config/{host_name}",
            credentials,
        ).status_code
        == HTTPStatus.OK
    )


def link_host_with_uuid(
    credentials: HTTPBasicCredentials,
    host_name: str,
    uuid: UUID,
) -> None:
    if (
        response := _forward_put(
            f"objects/host_config/{host_name}/actions/link_uuid/invoke",
            credentials,
            {"uuid": str(uuid)},
        )
    ).status_code != HTTPStatus.NO_CONTENT:
        raise HTTPException(
            status_code=response.status_code,
            detail=response.text,
        )


def cmk_edition(credentials: HTTPBasicCredentials) -> CMKEdition:
    if (
        response := _forward_get(
            "version",
            credentials,
        )
    ).status_code == HTTPStatus.OK:
        return CMKEdition[response.json()["edition"]]
    raise HTTPException(
        status_code=response.status_code,
        detail="User authentication failed",
    )
