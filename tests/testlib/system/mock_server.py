#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import logging
import ssl
import threading
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from enum import StrEnum
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, HTTPServer
from ipaddress import IPv4Address
from pathlib import Path
from types import TracebackType
from urllib.parse import urlsplit

from cmk.crypto.certificate import (
    CertificateWithPrivateKey,
    PersistedCertificateWithPrivateKey,
)
from cmk.crypto.x509 import (
    SAN,
    SubjectAlternativeNames,
)

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
    body: bytes | Callable[[dict[str, str], bytes], bytes]
    request_validator: Callable[[dict[str, str], bytes], bool] | None = None
    content_type: str = "application/json"


@dataclass(frozen=True)
class ReceivedRequest:
    method: MockMethod
    path: str
    headers: dict[str, str]
    body: bytes


@dataclass(frozen=True)
class MockAnswer:
    """What the mock sends back for a request."""

    status: int
    reason: str | None = None
    headers: Mapping[str, str] = field(default_factory=dict)
    body: bytes = b""


class MockEndpoints:
    """The responses configured for each endpoint, the answer they give to a request, and
    the requests answered so far.

    No HTTP here: MockHandler reads the request and writes the answer.
    """

    def __init__(self, *, ignore_query: bool = False) -> None:
        self._ignore_query = ignore_query
        self._responses: dict[MockEndpoint, list[MockResponse]] = {}
        self._received_requests: list[ReceivedRequest] = []

    def add(
        self, endpoint: MockEndpoint, response: MockResponse, *next_responses: MockResponse
    ) -> None:
        """Answer the first request to the endpoint with response, the next ones with
        next_responses in turn; the last response answers every further request."""
        self._responses[endpoint] = [response, *next_responses]

    @property
    def received_requests(self) -> Sequence[ReceivedRequest]:
        """Every request answered so far, in order, including those to unknown paths."""
        return list(self._received_requests)

    def reset(self) -> None:
        """Forget the endpoints and the received requests."""
        self._responses.clear()
        self._received_requests.clear()

    def answer(self, request: ReceivedRequest) -> MockAnswer:
        self._received_requests.append(request)
        path = urlsplit(request.path).path if self._ignore_query else request.path
        endpoint = MockEndpoint(method=request.method, path=path)
        if not (responses := self._responses.get(endpoint)):
            return MockAnswer(status=HTTPStatus.NOT_FOUND)
        # The last response answers every further request.
        response = responses.pop(0) if len(responses) > 1 else responses[0]
        if response.request_validator is not None:
            try:
                if not response.request_validator(request.headers, request.body):
                    raise AssertionError("Request validation failed")
            except AssertionError as excp:
                return MockAnswer(
                    status=HTTPStatus.BAD_REQUEST,
                    reason="Request Validation Failed",
                    body=str(excp).encode(),
                )
        body = (
            response.body
            if isinstance(response.body, bytes)
            else response.body(request.headers, request.body)
        )
        return MockAnswer(
            status=response.status,
            headers={"Content-Type": response.content_type, "Content-Length": str(len(body))},
            body=body,
        )


class MockHTTPServer(HTTPServer):
    def __init__(
        self,
        server_address: tuple[str, int],
        RequestHandlerClass: type[BaseHTTPRequestHandler],
        bind_and_activate: bool = True,
        ignore_query: bool = False,
    ) -> None:
        super().__init__(server_address, RequestHandlerClass, bind_and_activate)
        self.endpoints = MockEndpoints(ignore_query=ignore_query)


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

        # Always consume the request body before sending a response to avoid
        # BrokenPipeError on the client side (e.g. with OpenSSL 3.5+).
        size = int(self.headers.get("Content-Length", 0))
        request = ReceivedRequest(
            method=method,
            path=self.path,
            headers=dict(self.headers.items()),
            body=self.rfile.read(size) if size > 0 else b"",
        )

        answer = self.server.endpoints.answer(request)
        self.send_response(answer.status, answer.reason)
        for name, value in answer.headers.items():
            self.send_header(name, value)
        self.end_headers()
        self.wfile.write(answer.body)


class MockServer:
    """
    A mock HTTP/HTTPS server for testing purposes.

    This class provides a context manager interface for running a temporary HTTP or HTTPS server
    that can be configured with custom endpoints and responses. The server runs in a
    separate daemon thread and automatically finds an available port.

    Args:
        host (str, optional): The host address to bind to. Defaults to "127.0.0.1".
        port (int, optional): The port to bind to. If 0 (default), a random free port is used.
        https (bool, optional): Whether to use HTTPS. Defaults to False.
        cert_dir (Path, optional): Directory to store certificates when using HTTPS.
        ignore_query (bool, optional): Match endpoints on the URL path only, whatever query
            string a request carries. Defaults to False.

    Attributes:
        server: The HTTPServer instance.
        thread: The daemon thread running the server.
        url: The full URL of the running server (set after entering context).
        cert_file: Path to the certificate file (only set when using HTTPS).
        key_file: Path to the private key file (only set when using HTTPS).
        received_requests: Every request received so far, in order, including those to
            unknown paths. Methods without a handler, such as HEAD, are answered by the
            base class and not recorded.

    Example:
        >>> # HTTP server
        >>> with MockServer() as mock_server:
        ...     mock_server.add_endpoint(
        ...         MockEndpoint(method="GET", path="/test"),
        ...         MockResponse(status=200, body=b"{'text': 'hello'}"),
        ...     )
        ...     # Make requests to server.url (e.g. via requests.request())
        ...     pass
        ...
        >>> # HTTPS server
        >>> with MockServer(https=True) as mock_server:
        ...     mock_server.add_endpoint(
        ...         MockEndpoint(method="POST", path="/api/data"),
        ...         MockResponse(status=201, body=b"{'status': 'created'}"),
        ...     )
    """

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 0,  # port=0 → random free port
        https: bool = False,
        cert_dir: Path = Path("/tmp"),  # nosec
        ignore_query: bool = False,
    ) -> None:
        self.host = host
        self.https = https
        self.cert_dir = cert_dir
        self.dns_name = "localhost"
        self.cert_file: Path | None = None
        self.key_file: Path | None = None

        if self.https:
            self._create_self_signed_cert()

        self.server = MockHTTPServer((host, port), MockHandler, ignore_query=ignore_query)
        self.thread = threading.Thread(target=self.server.serve_forever)
        self.thread.daemon = True

    def _create_self_signed_cert(self) -> None:
        """Create a self-signed certificate for HTTPS."""
        self.key_file = self.cert_dir / "mock_private_key.pem"
        self.cert_file = self.cert_dir / "mock_cert.pem"

        PersistedCertificateWithPrivateKey.persist(
            CertificateWithPrivateKey.generate_self_signed(
                common_name="test",
                organization="Checkmk",
                key_size=2048,
                subject_alternative_names=SubjectAlternativeNames(
                    [SAN.dns_name(self.dns_name), SAN.ip_address(IPv4Address(self.host))]
                ),
            ),
            self.cert_file,
            self.key_file,
        )

    def __enter__(self) -> MockServer:
        if self.https and self.cert_file and self.key_file:
            ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            ssl_context.load_cert_chain(keyfile=self.key_file, certfile=self.cert_file)
            self.server.socket = ssl_context.wrap_socket(self.server.socket, server_side=True)

        self.thread.start()
        addr, port = self.server.server_address[:2]  # handles IPv4/IPv6
        if isinstance(addr, bytes):
            addr = addr.decode()
        protocol = "https" if self.https else "http"
        self.url = f"{protocol}://{addr}:{port}"
        logger.info("Mock server running at %s", self.url)
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
        *next_responses: MockResponse,
    ) -> None:
        """Answer the first request to the endpoint with response, the next ones with
        next_responses in turn; the last response answers every further request."""
        self.server.endpoints.add(endpoint, response, *next_responses)

    @property
    def received_requests(self) -> Sequence[ReceivedRequest]:
        return self.server.endpoints.received_requests

    def reset(self) -> None:
        """Forget the endpoints and the received requests, keeping the server and its URL."""
        self.server.endpoints.reset()
