#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import json
import logging
import threading
from dataclasses import dataclass
from enum import StrEnum
from http.server import BaseHTTPRequestHandler, HTTPServer
from types import TracebackType

logger = logging.getLogger(__name__)


class MockMethod(StrEnum):
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"


@dataclass(frozen=True)
class MockEndpoint:
    method: MockMethod
    path: str


@dataclass(frozen=True)
class MockResponse:
    status: int
    body: str | dict[str, object] | list[object]


class MockHTTPServer(HTTPServer):
    def __init__(
        self,
        server_address: tuple[str, int],
        RequestHandlerClass: type[BaseHTTPRequestHandler],
        bind_and_activate: bool = True,
    ) -> None:
        super().__init__(server_address, RequestHandlerClass, bind_and_activate)
        self.endpoints: dict[MockEndpoint, MockResponse] = {}


class MockHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        self._handle(MockMethod.GET)

    def do_POST(self) -> None:
        self._handle(MockMethod.POST)

    def do_PUT(self) -> None:
        self._handle(MockMethod.PUT)

    def do_DELETE(self) -> None:
        self._handle(MockMethod.DELETE)

    def _handle(self, method: MockMethod) -> None:
        if not isinstance(self.server, MockHTTPServer):
            raise TypeError(f"Expected MockHTTPServer, got {type(self.server)}")
        endpoints = self.server.endpoints
        endpoint = MockEndpoint(method=method, path=self.path)
        if response := endpoints.get(endpoint):
            self.send_response(response.status)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            if isinstance(response.body, dict | list):
                body = json.dumps(response.body)
            else:
                body = response.body
            self.wfile.write(body.encode())
        else:
            self.send_response(404)
            self.end_headers()


class MockServer:
    """
    A mock HTTP server for testing purposes.

    This class provides a context manager interface for running a temporary HTTP server
    that can be configured with custom endpoints and responses. The server runs in a
    separate daemon thread and automatically finds an available port.

    Args:
        host (str, optional): The host address to bind to. Defaults to "127.0.0.1".
        port (int, optional): The port to bind to. If 0 (default), a random free port is used.

    Attributes:
        server: The HTTPServer instance.
        thread: The daemon thread running the server.
        url: The full URL of the running server (set after entering context).

    Example:
        >>> with MockServer() as mock_server:
        ...     mock_server.add_endpoint(
        ...         MockEndpoint(method="GET", path="/test"),
        ...         MockResponse(status=200, body={"text": "hello"}),
        ...     )
        ...     # Make requests to server.url (e.g. via requests.request())
        ...     pass
    """

    def __init__(self, host: str = "127.0.0.1", port: int = 0) -> None:  # port=0 → random free port
        self.server = MockHTTPServer((host, port), MockHandler)
        self.thread = threading.Thread(target=self.server.serve_forever)
        self.thread.daemon = True

    def __enter__(self) -> "MockServer":
        self.thread.start()
        addr, port = self.server.server_address[:2]  # handles IPv4/IPv6
        if isinstance(addr, bytes):
            addr = addr.decode()
        self.url = f"http://{addr}:{port}"
        logger.info(f"Mock server running at {self.url}")
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        self.server.shutdown()
        self.thread.join()
        logger.info("Mock server stopped")

    def add_endpoint(
        self,
        endpoint: MockEndpoint,
        response: MockResponse,
    ) -> None:
        self.server.endpoints[endpoint] = response
