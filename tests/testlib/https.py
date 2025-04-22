#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""This module provides functionality to create and manage an HTTPS server with self-signed
certificates for testing purposes.
"""

import datetime
import os
import ssl
from http.server import HTTPServer, SimpleHTTPRequestHandler
from ipaddress import IPv4Address
from multiprocessing import Process

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID


class RedirectHandler(SimpleHTTPRequestHandler):
    def do_POST(self) -> None:
        # Note: It would be nice to set this needed URL on __init__ of RedirectHandler,
        # but that's not possible because HTTPServer insists in taking a
        # SimpleHTTPSRequestHandler class instead of an instance. Hence we set it on the HTTPServer instead.
        site_apache_address = f"{self.server.site_apache_url}{self.path}"  # type: ignore[attr-defined]
        self.send_response(308)
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
        address: str = "127.0.0.1",
        dns_name: str = "localhost",
        http_port: int = 8080,
        https_port: int = 8443,
        cert_dir: str = "/tmp",
        tries: int = 10,
    ) -> None:
        attempt: int = 0
        self.key_file: str = os.path.join(cert_dir, "private_key.pem")
        self.cert_file: str = os.path.join(cert_dir, "cert.pem")
        self.address: str = address
        self.dns_name: str = dns_name

        self.create_self_signed_cert()

        while attempt < tries:
            try:
                current_port = https_port + attempt
                apache_url = f"http://{address}:{http_port}"
                self.httpd = SiteApacheHTTPServer(apache_url, ("", current_port), RedirectHandler)
                self.port = current_port

                return

            except OSError:
                attempt += 1

        raise Exception("Failed to bind port for HTTP server")

    def create_self_signed_cert(self) -> None:
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
                        x509.IPAddress(IPv4Address(self.address)),
                    ]
                ),
                critical=False,
            )
            .sign(key, hashes.SHA256())
        )
        # Write our CSR out to disk.
        with open(self.cert_file, "wb") as f:
            f.write(csr.public_bytes(serialization.Encoding.PEM))

    def start_server(self) -> None:
        ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ssl_context.load_cert_chain(keyfile=self.key_file, certfile=self.cert_file)
        self.httpd.socket = ssl_context.wrap_socket(self.httpd.socket, server_side=True)
        self.httpd.serve_forever()

    def run(self) -> int:
        self.httpp = Process(target=self.start_server)
        self.httpp.start()
        return self.port

    def stop(self) -> None:
        self.httpp.terminate()
        self.httpp.join()
