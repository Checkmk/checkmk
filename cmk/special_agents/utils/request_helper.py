#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Common module request related stuff"""

from typing import (
    Optional,
    Any,
    Dict,
)
import abc
import base64
import json
import ssl
from http.client import HTTPConnection, HTTPSConnection, HTTPResponse
from urllib.request import build_opener, HTTPSHandler, Request

StringMap = Dict[str, str]  # should be Mapping[] but we're not ready yet..


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
            if self.__ca_file == HTTPSConfigurableConnection.IGNORE:
                self.sock = ssl.wrap_socket(self.sock, cert_reqs=ssl.CERT_NONE)
            else:
                self.sock = ssl.wrap_socket(
                    self.sock,
                    ca_certs=self.__ca_file,
                    cert_reqs=ssl.CERT_REQUIRED,
                )


class HTTPSAuthHandler(HTTPSHandler):
    def __init__(self, ca_file: str):
        super().__init__()
        self.__ca_file = ca_file

    def https_open(self, request: Request) -> HTTPResponse:  # pylint: disable=arguments-differ
        # TODO: Slightly interesting things in the typeshed here, investigate...
        return self.do_open(self.get_connection, request)  # type: ignore[arg-type]

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
            'Authorization': "Basic " + base64.encodebytes(
                ("%s:%s" % (username, password)).encode()).strip().decode()
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
