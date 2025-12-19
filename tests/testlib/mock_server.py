#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import datetime
import logging
import os
import ssl
import threading
from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from http.server import BaseHTTPRequestHandler, HTTPServer
from ipaddress import IPv4Address
from types import TracebackType

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

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
    body: bytes
    request_validator: Callable[[dict[str, str], bytes], bool] | None = None


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
        if not (response := endpoints.get(endpoint)):
            self.send_response(404)
            self.end_headers()
            return
        if response.request_validator is not None:
            request_headers = {key: value for key, value in self.headers.items()}
            size = int(self.headers.get("Content-Length", 0))
            request_body = self.rfile.read(size)
            try:
                assert response.request_validator(request_headers, request_body)
            except AssertionError as excp:
                self.send_response(400, "Request Validation Failed")
                self.end_headers()
                self.wfile.write(str(excp).encode())
                return
        self.send_response(response.status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(response.body)


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
    Attributes:
        server: The HTTPServer instance.
        thread: The daemon thread running the server.
        url: The full URL of the running server (set after entering context).
        cert_file: Path to the certificate file (only set when using HTTPS).
        key_file: Path to the private key file (only set when using HTTPS).
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
        cert_dir: str = "/tmp",  # nosec
    ) -> None:
        self.host = host
        self.https = https
        self.cert_dir = cert_dir
        self.dns_name = "localhost"
        self.key_file = os.path.join(self.cert_dir, "mock_private_key.pem")
        self.cert_file = os.path.join(self.cert_dir, "mock_cert.pem")

        if self.https:
            self._create_self_signed_cert()

        self.server = MockHTTPServer((host, port), MockHandler)
        self.thread = threading.Thread(target=self.server.serve_forever)
        self.thread.daemon = True

    def _create_self_signed_cert(self) -> None:
        # Generate our key
        key = rsa.generate_private_key(65537, 2048)
        # Write our key to disk for safe keeping
        with open(self.key_file, "wb") as f:
            f.write(
                key.private_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PrivateFormat.TraditionalOpenSSL,
                    encryption_algorithm=serialization.NoEncryption(),
                )
            )

        # create a self-signed cert
        subject = issuer = x509.Name(
            [
                x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Checkmk"),
                x509.NameAttribute(NameOID.COMMON_NAME, self.dns_name),
            ]
        )
        csr = (
            x509.CertificateBuilder()
            .subject_name(subject)
            .issuer_name(issuer)
            .public_key(key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(datetime.datetime.now(datetime.UTC))
            .not_valid_after(  # Our certificate will be valid for 10 days
                datetime.datetime.now(datetime.UTC) + datetime.timedelta(days=10)
            )
            .add_extension(
                x509.SubjectAlternativeName(
                    [
                        x509.DNSName(self.dns_name),
                        x509.IPAddress(IPv4Address(self.host)),
                    ]
                ),
                critical=False,
            )
            .sign(key, hashes.SHA256())
        )
        # Write our CSR out to disk.
        with open(self.cert_file, "wb") as f:
            f.write(csr.public_bytes(serialization.Encoding.PEM))

    def __enter__(self) -> "MockServer":
        if self.https:
            ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            ssl_context.load_cert_chain(keyfile=self.key_file, certfile=self.cert_file)
            self.server.socket = ssl_context.wrap_socket(self.server.socket, server_side=True)

        self.thread.start()
        addr, port = self.server.server_address[:2]  # handles IPv4/IPv6
        if isinstance(addr, bytes):
            addr = addr.decode()
        protocol = "https" if self.https else "http"
        self.url = f"{protocol}://{addr}:{port}"
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
