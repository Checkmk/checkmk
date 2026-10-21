#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable
from enum import Enum
from http import HTTPStatus
from typing import Concatenate
from urllib.parse import quote

import requests
from fastapi import HTTPException
from fastapi.security import HTTPBasicCredentials
from pydantic import BaseModel, UUID4, ValidationError

from cmk.agent_receiver.agent_receiver.models import (
    ConnectionMode,
    DownloadRequest,
    UpdateStatusRequest,
    UpdateStatusResponse,
)
from cmk.agent_receiver.lib.auth import B64SiteInternalSecret
from cmk.agent_receiver.lib.config import get_config
from cmk.agent_receiver.lib.log import logger


class CMKEdition(Enum):
    community = "Community"
    pro = "Pro"
    ultimatemt = "Ultimate multi-tenancy"
    ultimate = "Ultimate"
    cloud = "Cloud"

    def supports_register_new(self) -> bool:
        """
        >>> CMKEdition.community.supports_register_new()
        False
        >>> CMKEdition.ultimate.supports_register_new()
        True
        """
        return (
            self is CMKEdition.ultimate or self is CMKEdition.cloud or self is CMKEdition.ultimatemt
        )


def _local_rest_api_url() -> str:
    config = get_config()
    return config.rest_api_url


def _local_internal_rest_api_url() -> str:
    config = get_config()
    return config.internal_rest_api_url


def _credentials_to_rest_api_auth(credentials: HTTPBasicCredentials) -> str:
    """
    >>> _credentials_to_rest_api_auth(HTTPBasicCredentials(username="hans", password="dampf"))
    'Bearer hans dampf'
    """
    return f"Bearer {credentials.username} {credentials.password}"


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


def _forward_put_token(
    endpoint: str,
    token: str,
    json_body: dict[str, object],
) -> requests.Response:
    return requests.put(
        f"{_local_internal_rest_api_url()}/{endpoint}",
        headers={
            "Authorization": f"CMK-TOKEN {token}",
            "Accept": "application/json",
        },
        json=json_body,
        timeout=30,
    )


_DOWNLOAD_TIMEOUT_SECONDS = 120
"""The longest pause of the site while it answers a download

A host of a remote site waits for the transfer from the central site, which the remote site
reads in full before it answers. That whole transfer is one silent wait here, so the 30 seconds
of the other calls would end a slow download in every cycle. The controller allows 300 seconds
(AGENT_DOWNLOAD_TIMEOUT in packages/cmk-agent-ctl/src/agent_receiver_api.rs), and the Apache of
the site cuts a silent request after its own Timeout of 120.
"""


def _forward_post_internal(
    endpoint: str,
    site_internal_secret: B64SiteInternalSecret,
    json_body: dict[str, object],
    accept: str,
    timeout: int = 30,
) -> requests.Response:
    return requests.post(
        f"{_local_internal_rest_api_url()}/{endpoint}",
        headers={
            "Authorization": f"InternalToken {site_internal_secret}",
            "Accept": accept,
        },
        json=json_body,
        timeout=timeout,
    )


def log_http_exception[**TEndpointParams, TEndpointReturn](
    endpoint_call: Callable[TEndpointParams, TEndpointReturn],
) -> Callable[Concatenate[str, TEndpointParams], TEndpointReturn]:
    def wrapper(
        log_text: str,
        /,
        *args: TEndpointParams.args,
        **kwargs: TEndpointParams.kwargs,
    ) -> TEndpointReturn:
        try:
            return endpoint_call(*args, **kwargs)
        except HTTPException as http_excpt:
            logger.error(
                "%(log_text)s. Error message: %(detail)s",
                {"log_text": log_text, "detail": http_excpt.detail},
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
def register_token(
    token: str,
    uuid: UUID4,
    host_name: str,
) -> RegisterResponse:
    response = _forward_put_token(
        f"objects/host_config_internal/{_url_encode_hostname(host_name)}/actions/register_via_token/invoke",
        token,
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
def cmk_edition(credentials: HTTPBasicCredentials) -> CMKEdition:
    response = _forward_get(
        "version",
        credentials,
    )
    _verify_response(response, HTTPStatus.OK)
    return CMKEdition[response.json()["edition"]]


@log_http_exception
def deployment_status(
    site_internal_secret: B64SiteInternalSecret,
    host_name: str,
    uuid: UUID4,
    status_request: UpdateStatusRequest,
) -> UpdateStatusResponse:
    response = _forward_post_internal(
        f"objects/agent_deployment_internal/{_url_encode_hostname(host_name)}/actions/status/invoke",
        site_internal_secret,
        {**status_request.model_dump(exclude_none=True), "uuid": str(uuid)},
        "application/json",
    )
    _verify_agent_update_response(response)
    return UpdateStatusResponse.model_validate(response.json())


@log_http_exception
def deployment_download(
    site_internal_secret: B64SiteInternalSecret,
    host_name: str,
    uuid: UUID4,
    download_request: DownloadRequest,
) -> bytes:
    response = _forward_post_internal(
        f"objects/agent_deployment_internal/{_url_encode_hostname(host_name)}/actions/download/invoke",
        site_internal_secret,
        {**download_request.model_dump(), "uuid": str(uuid)},
        "application/octet-stream",
        timeout=_DOWNLOAD_TIMEOUT_SECONDS,
    )
    _verify_agent_update_response(response)
    return response.content


def _verify_agent_update_response(response: requests.Response) -> None:
    if response.status_code == HTTPStatus.NOT_FOUND and _matched_no_endpoint(response):
        raise HTTPException(
            status_code=HTTPStatus.NOT_IMPLEMENTED,
            detail="This site offers no agent updates.",
        )
    _verify_response(response, HTTPStatus.OK)


def _matched_no_endpoint(response: requests.Response) -> bool:
    # The REST API titles a URL that matches no endpoint with the bare status phrase, which is
    # what a Community site answers, as it has no agent deployment endpoints. The endpoints give
    # their own 404s a title of their own.
    try:
        title = _RestApiErrorDescr.model_validate_json(response.text).title
    except ValidationError:
        return True
    return title == HTTPStatus.NOT_FOUND.phrase


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
    {"title": "Insufficient permissions", "status": 403}
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
