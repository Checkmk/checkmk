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


class Method(StrEnum):
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"


@dataclass(frozen=True)
class Endpoint:
    method: Method
    path: str


class MockHandler(BaseHTTPRequestHandler):
    endpoints: dict[Endpoint, tuple[int, str | dict[str, object] | list[object]]] = {}

    def do_GET(self) -> None:
        self._handle(Method.GET)

    def do_POST(self) -> None:
        self._handle(Method.POST)

    def do_PUT(self) -> None:
        self._handle(Method.PUT)

    def do_DELETE(self) -> None:
        self._handle(Method.DELETE)

    def _handle(self, method: Method) -> None:
        endpoint = Endpoint(method=method, path=self.path)
        if endpoint in MockHandler.endpoints:
            status, body = MockHandler.endpoints[endpoint]
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            if isinstance(body, dict | list):
                body = json.dumps(body)
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
        >>> with MockServer() as server:
        ...     server.add_endpoint(Endpoint(method="GET", path="/test"), 200, {"text": "hello"})
        ...     # Make requests to server.url
        ...     pass
    """

    def __init__(self, host: str = "127.0.0.1", port: int = 0) -> None:  # port=0 → random free port
        self.server = HTTPServer((host, port), MockHandler)
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
        endpoint: Endpoint,
        status: int = 200,
        body: str | dict[str, object] | list[object] = "",
    ) -> None:
        MockHandler.endpoints[endpoint] = (status, body)
