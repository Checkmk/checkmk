#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from enum import Enum
from http import HTTPStatus
from typing import Any
from uuid import UUID

import requests
from agent_receiver.site_context import site_config_path, site_name
from fastapi import HTTPException
from fastapi.security import HTTPBasicCredentials


class CMKEdition(Enum):
    cre = "Raw"
    cfe = "Free"
    cee = "Enterprise"
    cme = "Managed Services"
    cpe = "Plus"

    def supports_registration_with_labels(self) -> bool:
        """
        >>> CMKEdition["cre"].supports_registration_with_labels()
        False
        >>> CMKEdition["cpe"].supports_registration_with_labels()
        True
        """
        return self is CMKEdition.cpe


def _local_apache_port() -> int:
    for site_config_line in site_config_path().read_text().splitlines():
        key, value = site_config_line.split("=")
        if key == "CONFIG_APACHE_TCP_PORT":
            return int(value.strip("'"))
    return 80


def _local_rest_api_url() -> str:
    return f"http://localhost:{_local_apache_port()}/{site_name()}/check_mk/api/1.0"


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
            f"objects/host_config_internal/{host_name}/actions/link_uuid/invoke",
            credentials,
            {"uuid": str(uuid)},
        )
    ).status_code != HTTPStatus.NO_CONTENT:
        raise HTTPException(
            status_code=response.status_code,
            detail=parse_error_response_body(response.text),
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


def parse_error_response_body(body: str) -> str:
    """
    The REST API often returns JSON error bodies such as
    {"title": "You do not have the permission for agent pairing.", "status": 403}
    from which we want to extract the title field.

    >>> parse_error_response_body("123")
    '123'
    >>> parse_error_response_body('["x", "y"]')
    '["x", "y"]'
    >>> parse_error_response_body('{"message": "Hands off this component!", "status": 403}')
    '{"message": "Hands off this component!", "status": 403}'
    >>> parse_error_response_body('{"title": "You do not have the permission for agent pairing.", "status": 403}')
    'You do not have the permission for agent pairing.'
    """
    try:
        deserialized_body = json.loads(body)
    except json.JSONDecodeError:
        return body
    try:
        return deserialized_body["title"]
    except (TypeError, KeyError):
        return body
