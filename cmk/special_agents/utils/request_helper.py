#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Common module request related stuff"""

import abc
import base64
import json
import os
import ssl
from functools import reduce
from http.client import HTTPConnection, HTTPResponse, HTTPSConnection
from typing import Any, Dict, Optional, TypedDict, Union
from urllib.request import build_opener, HTTPSHandler, Request

from requests import Session

StringMap = Dict[str, str]  # should be Mapping[] but we're not ready yet..


class TokenDict(TypedDict):
    access_token: str
    refresh_token: str
    expires_in: float
    expires_in_abs: Optional[str]


def to_token_dict(data: Any) -> TokenDict:
    return {
        "access_token": str(data["access_token"]),
        "refresh_token": str(data["refresh_token"]),
        "expires_in": float(data["expires_in"]),
        "expires_in_abs": str(data["expires_in_abs"]) if "expires_in_abs" in data else None,
    }


class Requester(abc.ABC):
    @abc.abstractmethod
    def get(self, path: str, parameters: Optional[StringMap] = None) -> Any:
        raise NotImplementedError()


class HTTPSConfigurableConnection(HTTPSConnection):

    IGNORE = "__ignore"

    def __init__(self, host: str, ca_file: Optional[str] = None) -> None:
        super().__init__(host)
        self.__ca_file = ca_file

    def connect(self) -> None:
        if not self.__ca_file:
            HTTPSConnection.connect(self)
        else:
            HTTPConnection.connect(self)
            # TODO: Use SSLContext.wrap_socket() instead of the deprecated ssl.wrap_socket()!
            # See https://docs.python.org/3/library/ssl.html#socket-creation
            if self.__ca_file == HTTPSConfigurableConnection.IGNORE:
                self.sock = ssl.wrap_socket(  # pylint: disable=deprecated-method
                    self.sock,
                    cert_reqs=ssl.CERT_NONE,
                )
            else:
                self.sock = ssl.wrap_socket(  # pylint: disable=deprecated-method
                    self.sock,
                    ca_certs=self.__ca_file,
                    cert_reqs=ssl.CERT_REQUIRED,
                )


class HTTPSAuthHandler(HTTPSHandler):
    def __init__(self, ca_file: str):
        super().__init__()
        self.__ca_file = ca_file

    def https_open(self, req: Request) -> HTTPResponse:  # pylint: disable=arguments-differ
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
            + base64.encodebytes(("%s:%s" % (username, password)).encode()).strip().decode()
        }
        self._base_url = "https://%s:%d/%s" % (server, port, base_url)
        self._opener = build_opener(HTTPSAuthHandler(HTTPSConfigurableConnection.IGNORE))

    def get(self, path: str, parameters: Optional[StringMap] = None) -> Any:
        url = "%s/%s/" % (self._base_url, path)
        if parameters is not None:
            url = "%s?%s" % (url, "&".join(["%s=%s" % par for par in parameters.items()]))

        request = Request(url, headers=self._req_headers)
        response = self._opener.open(request)
        return json.loads(response.read())


def create_api_connect_session(
    api_url: str,
    no_cert_check: bool = False,
    auth: Any = None,
    token: Optional[str] = None,
) -> "ApiSession":
    """Create a custom requests Session

    Args:
        api_url:
            url address to the server api

        no_cert_check:
            option if ssl certificate should be verified. session.verify = False cannot be
            used at this point due to a bug in requests.session

        auth:
            authentication option (either username & password or OAuth1 object)

        token:
            token for Bearer token request
    """
    ssl_verify = None
    if not no_cert_check:
        ssl_verify = os.environ.get("REQUESTS_CA_BUNDLE")

    session = ApiSession(api_url, ssl_verify)

    if auth:
        session.auth = auth
    elif token:
        session.headers.update({"Authorization": "Bearer " + token})

    return session


class ApiSession(Session):
    """Adjusted requests.session class with a focus on multiple API calls

    ApiSession behaves similar to the requests.session
    with the exception that a base url is provided and persisted
    all requests forms use the base url and append the actual request

    """

    def __init__(
        self, base_url: Optional[str] = None, ssl_verify: Optional[Union[str, bool]] = None
    ):
        super().__init__()
        self._base_url = base_url if base_url else ""
        self.ssl_verify = ssl_verify if ssl_verify else False

    def request(self, method, url, **kwargs):  # pylint: disable=arguments-differ
        url = urljoin(self._base_url, url)
        return super().request(method, url, verify=self.ssl_verify, **kwargs)


def parse_api_url(
    server_address,
    api_path,
    protocol="http",
    port=None,
    url_prefix=None,
    path_prefix=None,
) -> str:
    """Parse the server api address

    custom url always has priority over other options, if not specified the address contains
    either the ip-address or the hostname in the url

    the protocol should not be specified through the custom url

    Args:
        api_path:
            the path to the api seen from the full server address. This is the address
            where the API can be queried

        server_address:
            hostname or ip-address to the server

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


def urljoin(*args):
    """Join two urls without stripping away any parts

    >>> urljoin("http://127.0.0.1:8080", "api/v2")
    'http://127.0.0.1:8080/api/v2'

    >>> urljoin("http://127.0.0.1:8080/prometheus", "api/v2")
    'http://127.0.0.1:8080/prometheus/api/v2'

    >>> urljoin("http://127.0.0.1:8080/", "api/v2/")
    'http://127.0.0.1:8080/api/v2/'
    """

    def join_slash(base, part):
        return base.rstrip("/") + "/" + part.lstrip("/")

    return reduce(join_slash, args) if args else ""
