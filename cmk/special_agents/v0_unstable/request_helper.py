#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Common module request related stuff"""

import abc
import base64
import json
import ssl
from collections.abc import Mapping
from http.client import HTTPConnection, HTTPResponse, HTTPSConnection
from typing import Any, Literal, TypedDict
from urllib.parse import urljoin
from urllib.request import build_opener, HTTPSHandler, Request

from requests import Response, Session
from requests.adapters import HTTPAdapter
from requests.auth import HTTPBasicAuth

StringMap = dict[str, str]  # should be Mapping[] but we're not ready yet..


class TokenDict(TypedDict):
    access_token: str
    refresh_token: str
    expires_in: float
    expires_in_abs: str | None


def to_token_dict(data: Any) -> TokenDict:
    return {
        "access_token": str(data["access_token"]),
        "refresh_token": str(data["refresh_token"]),
        "expires_in": float(data["expires_in"]),
        "expires_in_abs": str(data["expires_in_abs"]) if "expires_in_abs" in data else None,
    }


class Requester(abc.ABC):
    @abc.abstractmethod
    def get(self, path: str, parameters: StringMap | None = None) -> Any:
        raise NotImplementedError()


class HTTPSConfigurableConnection(HTTPSConnection):
    IGNORE = "__ignore"

    def __init__(self, host: str, ca_file: str | None = None) -> None:
        self.__ca_file = ca_file
        context = ssl.create_default_context(
            cafile=None if ca_file == HTTPSConfigurableConnection.IGNORE else ca_file
        )
        if self.__ca_file:
            if self.__ca_file == HTTPSConfigurableConnection.IGNORE:
                context.check_hostname = False
                context.verify_mode = ssl.CERT_NONE
            else:
                context.verify_mode = ssl.CERT_REQUIRED
                context.check_hostname = True

        super().__init__(host, context=context)

    def connect(self) -> None:
        if not self.__ca_file:
            HTTPSConnection.connect(self)
        else:
            HTTPConnection.connect(self)


class HTTPSAuthHandler(HTTPSHandler):
    def __init__(self, ca_file: str) -> None:
        super().__init__()
        self.__ca_file = ca_file

    def https_open(self, req: Request) -> HTTPResponse:
        # TODO: Slightly interesting things in the typeshed here, investigate...
        return self.do_open(self.get_connection, req)  # type: ignore[arg-type]

    # Hmmm, this should be a HTTPConnectionProtocol...
    def get_connection(self, host: str, timeout: float) -> HTTPSConnection:
        return HTTPSConfigurableConnection(host, ca_file=self.__ca_file)


class HTTPSAuthRequester(Requester):
    def __init__(
        self,
        server: str,
        port: int,
        base_url: str,
        username: str,
        password: str,
    ) -> None:
        self._req_headers = {
            "Authorization": "Basic "
            + base64.encodebytes((f"{username}:{password}").encode())
            .strip()
            .decode()
            .replace("\n", "")
        }
        self._base_url = "https://%s:%d/%s" % (server, port, base_url)
        self._opener = build_opener(HTTPSAuthHandler(HTTPSConfigurableConnection.IGNORE))

    def get(self, path: str, parameters: StringMap | None = None) -> Any:
        url = f"{self._base_url}/{path}/"
        if parameters is not None:
            url = "{}?{}".format(url, "&".join(["%s=%s" % par for par in parameters.items()]))

        request = Request(url, headers=self._req_headers)
        response = self._opener.open(request)
        return json.loads(response.read())


class HostnameValidationAdapter(HTTPAdapter):
    def __init__(self, hostname: str) -> None:
        super().__init__()
        self._reference_hostname = hostname

    def cert_verify(self, conn, url, verify, cert):
        conn.assert_hostname = self._reference_hostname
        return super().cert_verify(conn, url, verify, cert)


class ApiSession:
    """Class for issuing multiple API calls

    ApiSession behaves similar to requests.Session with the exception that a
    base URL is provided and persisted.
    All requests use the base URL and append the provided url to it.
    """

    def __init__(
        self,
        base_url: str,
        auth: HTTPBasicAuth | None = None,
        tls_cert_verification: bool | HostnameValidationAdapter = True,
        additional_headers: Mapping[str, str] | None = None,
    ):
        self._session = Session()
        self._session.auth = auth
        self._session.headers.update(additional_headers or {})
        self._base_url = base_url

        if isinstance(tls_cert_verification, HostnameValidationAdapter):
            self._session.mount(self._base_url, tls_cert_verification)
            self.verify = True
        else:
            self.verify = tls_cert_verification

    def request(
        self,
        method: str,
        url: str,
        params: Mapping[str, str] | None = None,
    ) -> Response:
        return self._session.request(
            method,
            urljoin(self._base_url, url),
            params=params,
            verify=self.verify,
        )

    def get(
        self,
        url: str,
        params: Mapping[str, str] | None = None,
    ) -> Response:
        return self.request(
            "get",
            url,
            params=params,
        )


def parse_api_url(
    server_address: str,
    api_path: str,
    protocol: Literal["http", "https"] = "http",
    port: int | None = None,
    url_prefix: str | None = None,
    path_prefix: str | None = None,
) -> str:
    """Parse the server api address

    custom url always has priority over other options, if not specified the address contains
    either the ip address or the hostname in the url

    the protocol should not be specified through the custom url

    Args:
        api_path:
            the path to the api seen from the full server address. This is the address
            where the API can be queried

        server_address:
            hostname or ip address to the server

        protocol:
            the transfer protocol (http or https)

        port:
            TCP/Web port of the server

        url_prefix:
            custom url prefix for the server address

        path_prefix:
            custom path_prefix which is appended to the server address

    Returns:
        the full api url address

    Examples:
        >>> parse_api_url("localhost", "api/v1/", port=8080, path_prefix="extra")
        'http://localhost:8080/extra/api/v1/'


    """
    if url_prefix is None:
        url_prefix = ""

    address_start = f"{protocol}://{url_prefix}{server_address}"
    if port:
        address = f"{address_start}:{port}/"
    else:
        address = f"{address_start}/"

    path_prefix = f"{path_prefix}/" if path_prefix else ""
    api_address = f"{address}{path_prefix}{api_path}"
    return api_address


def parse_api_custom_url(
    url_custom: str,
    api_path: str,
    protocol: str = "http",
) -> str:
    """Parse API address with custom url

    Args:
        url_custom:
            the custom url to connect to the server

        api_path:
            the api path which is appended to the custom url

        protocol:
            the transfer protocol (http or https)

    Returns:
        str representing the API url

    Examples:
        >>> parse_api_custom_url("localhost:8080", "api/v1/")
        'http://localhost:8080/api/v1/'

    """
    return f"{protocol}://{url_custom}/{api_path}"
