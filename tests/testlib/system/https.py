#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""This module provides functionality to create and manage an HTTPS server with self-signed
certificates for testing purposes.
"""

import ssl
import threading
from http import HTTPStatus
from http.server import HTTPServer, SimpleHTTPRequestHandler
from ipaddress import IPv4Address
from pathlib import Path

from cmk.crypto.certificate import (
    CertificateWithPrivateKey,
    PersistedCertificateWithPrivateKey,
)
from cmk.crypto.x509 import (
    SAN,
    SubjectAlternativeNames,
)


class RedirectHandler(SimpleHTTPRequestHandler):
    def do_POST(self) -> None:
        # Note: It would be nice to set this needed URL on __init__ of RedirectHandler,
        # but that's not possible because HTTPServer insists in taking a
        # SimpleHTTPSRequestHandler class instead of an instance. Hence we set it on the HTTPServer instead.
        site_apache_address = f"{self.server.site_apache_url}{self.path}"  # type: ignore[attr-defined]
        self.send_response(HTTPStatus.PERMANENT_REDIRECT)
        self.send_header("Location", site_apache_address)
        self.end_headers()


class SiteApacheHTTPServer(HTTPServer):
    def __init__(
        self,
        site_apache_url: str,
        server_address: tuple[str, int],
        request_handler_class: type[RedirectHandler],
    ) -> None:
        super().__init__(server_address, request_handler_class)
        self.site_apache_url = site_apache_url


class HTTPSDummy:
    def __init__(
        self,
        redirect_target_port: int = 8080,
        cert_dir: Path = Path("/tmp"),
        address: str = "127.0.0.1",
    ) -> None:
        self.key_file = cert_dir / "private_key.pem"
        self.cert_file = cert_dir / "cert.pem"
        self.dns_name = "localhost"
        self.address = address

        self.create_self_signed_cert()

        self.httpd = SiteApacheHTTPServer(
            f"http://{self.address}:{redirect_target_port}", (self.address, 0), RedirectHandler
        )
        self.port: int = self.httpd.socket.getsockname()[1]

        self.ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        self.ssl_context.load_cert_chain(keyfile=self.key_file, certfile=self.cert_file)

        self._thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)

    def create_self_signed_cert(self) -> None:
        PersistedCertificateWithPrivateKey.persist(
            CertificateWithPrivateKey.generate_self_signed(
                common_name="test",
                organization="Checkmk",
                key_size=2048,
                subject_alternative_names=SubjectAlternativeNames(
                    [SAN.dns_name(self.dns_name), SAN.ip_address(IPv4Address(self.address))]
                ),
            ),
            self.cert_file,
            self.key_file,
        )

    def run(self) -> int:
        self.httpd.socket = self.ssl_context.wrap_socket(self.httpd.socket, server_side=True)
        self._thread.start()
        return self.port

    def stop(self) -> None:
        self.httpd.shutdown()
        self._thread.join()
        self.httpd.server_close()
