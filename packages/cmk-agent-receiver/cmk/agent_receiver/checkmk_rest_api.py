#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable
from enum import Enum
from http import HTTPStatus
from typing import Concatenate, ParamSpec, TypeVar
from urllib.parse import quote

import requests
from fastapi import HTTPException
from fastapi.security import HTTPBasicCredentials
from pydantic import BaseModel, UUID4

from .log import logger
from .models import ConnectionMode
from .site_context import site_config_path, site_name
from .utils import B64SiteInternalSecret


class CMKEdition(Enum):
    cre = "Raw"
    cee = "Enterprise"
    cme = "Managed Services"
    cce = "Cloud"
    cse = "Saas"

    def supports_register_new(self) -> bool:
        """
        >>> CMKEdition.cre.supports_register_new()
        False
        >>> CMKEdition.cce.supports_register_new()
        True
        """
        return self is CMKEdition.cce or self is CMKEdition.cse or self is CMKEdition.cme


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
    json_body: dict[str, object],
) -> requests.Response:
    return requests.post(
        f"{_local_rest_api_url()}/{endpoint}",
        headers={
            "Authorization": _credentials_to_rest_api_auth(credentials),
            "Accept": "application/json",
        },
        json=json_body,
        timeout=30,
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
        timeout=30,
    )


def _forward_put(
    endpoint: str,
    credentials: HTTPBasicCredentials,
    json_body: dict[str, object],
) -> requests.Response:
    return requests.put(
        f"{_local_rest_api_url()}/{endpoint}",
        headers={
            "Authorization": _credentials_to_rest_api_auth(credentials),
            "Accept": "application/json",
        },
        json=json_body,
        timeout=30,
    )


_TEndpointParams = ParamSpec("_TEndpointParams")
_TEndpointReturn = TypeVar("_TEndpointReturn")


def log_http_exception(
    endpoint_call: Callable[_TEndpointParams, _TEndpointReturn],
) -> Callable[Concatenate[str, _TEndpointParams], _TEndpointReturn]:
    def wrapper(
        log_text: str,
        /,
        *args: _TEndpointParams.args,
        **kwargs: _TEndpointParams.kwargs,
    ) -> _TEndpointReturn:
        try:
            return endpoint_call(*args, **kwargs)
        except HTTPException as http_excpt:
            logger.error(
                "%s. Error message: %s",
                log_text,
                http_excpt.detail,
            )
            raise http_excpt

    return wrapper


class ControllerCertSettings(BaseModel, frozen=True):
    lifetime_in_months: int


@log_http_exception
def controller_certificate_settings(
    site_internal_secret: B64SiteInternalSecret,
) -> ControllerCertSettings:
    response = requests.get(
        f"{_local_rest_api_url()}/agent_controller_certificates_settings",
        headers={
            "Authorization": f"InternalToken {site_internal_secret}",
        },
        timeout=30,
    )
    _verify_response(response, HTTPStatus.OK)
    return ControllerCertSettings.model_validate(response.json())


class RegisterResponse(BaseModel, frozen=True):
    connection_mode: ConnectionMode


@log_http_exception
def register(
    credentials: HTTPBasicCredentials,
    uuid: UUID4,
    host_name: str,
) -> RegisterResponse:
    response = _forward_put(
        f"objects/host_config_internal/{_url_encode_hostname(host_name)}/actions/register/invoke",
        credentials,
        {
            "uuid": str(uuid),
        },
    )
    if response.status_code == HTTPStatus.NOT_FOUND:
        # The REST API error message is a bit obscure in this case
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail=f"Host {host_name} does not exist.",
        )
    _verify_response(response, HTTPStatus.OK)
    return RegisterResponse.model_validate(response.json())


@log_http_exception
def get_root_cert(credentials: HTTPBasicCredentials) -> str:
    response = _forward_get(
        "root_cert",
        credentials,
    )
    _verify_response(response, HTTPStatus.OK)
    return str(response.json()["cert"])


@log_http_exception
def post_csr(
    credentials: HTTPBasicCredentials,
    csr: str,
) -> str:
    response = _forward_post(
        "csr",
        credentials,
        {"csr": csr},
    )
    _verify_response(response, HTTPStatus.OK)
    return str(response.json()["cert"])


class HostConfiguration(BaseModel, frozen=True):
    site: str
    is_cluster: bool


def _url_encode_hostname(host_name: str) -> str:
    """Escape special characters in the host name to make it URL safe

    Allowed characters are letters, digits and '_.-~'.

        >>> _url_encode_hostname("local_host.host-name.tld~")
        'local_host.host-name.tld~'

    Slashes are not allowed.

        >>> _url_encode_hostname("heute/../../etc")
        'heute%2F..%2F..%2Fetc'

    Spaces, umlauts, emojis and the like are escaped.

        >>> _url_encode_hostname("Bäm! 💥")
        'B%C3%A4m%21%20%F0%9F%92%A5'

    """
    return quote(host_name, safe="")  # '/' is not "safe" here


@log_http_exception
def host_configuration(
    credentials: HTTPBasicCredentials,
    host_name: str,
) -> HostConfiguration:
    if (
        response := _forward_get(
            f"objects/host_config_internal/{_url_encode_hostname(host_name)}",
            credentials,
        )
    ).status_code == HTTPStatus.NOT_FOUND:
        # The REST API only says 'Not Found' in the response title here
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail=f"Host {host_name} does not exist.",
        )
    _verify_response(response, HTTPStatus.OK)
    return HostConfiguration(**response.json())


@log_http_exception
def link_host_with_uuid(
    credentials: HTTPBasicCredentials,
    host_name: str,
    uuid: UUID4,
) -> None:
    response = _forward_put(
        f"objects/host_config_internal/{_url_encode_hostname(host_name)}/actions/link_uuid/invoke",
        credentials,
        {"uuid": str(uuid)},
    )
    _verify_response(response, HTTPStatus.NO_CONTENT)


@log_http_exception
def cmk_edition(credentials: HTTPBasicCredentials) -> CMKEdition:
    response = _forward_get(
        "version",
        credentials,
    )
    _verify_response(response, HTTPStatus.OK)
    return CMKEdition[response.json()["edition"]]


def _verify_response(
    response: requests.Response,
    expected_status_code: HTTPStatus,
) -> None:
    if response.status_code != expected_status_code:
        raise HTTPException(
            status_code=response.status_code,
            detail=_parse_error_response_body(response.text),
        )


class _RestApiErrorDescr(BaseModel, frozen=True):
    title: str
    detail: str | None = None


def _parse_error_response_body(body: str) -> str:
    """
    The REST API often returns JSON error bodies such as
    {"title": "You do not have the permission for agent pairing.", "status": 403}
    from which we want to extract the title field.

    >>> _parse_error_response_body("123")
    '123'
    >>> _parse_error_response_body('["x", "y"]')
    '["x", "y"]'
    >>> _parse_error_response_body('{"message": "Hands off this component!", "status": 403}')
    '{"message": "Hands off this component!", "status": 403}'
    >>> _parse_error_response_body(
    ...  '{"title": "Insufficient permissions", '
    ...  '"detail": "You need permission xyz.", "status": 403}')
    'Insufficient permissions - Details: You need permission xyz.'
    """
    try:
        error_descr = _RestApiErrorDescr.model_validate_json(body)
    except Exception:
        return body
    return error_descr.title + (f" - Details: {error_descr.detail}" if error_descr.detail else "")
