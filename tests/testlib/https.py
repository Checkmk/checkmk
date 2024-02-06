#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import os
import ssl
from http.server import HTTPServer, SimpleHTTPRequestHandler
from multiprocessing import Process
from pathlib import Path

from OpenSSL import crypto


class RedirectHandler(SimpleHTTPRequestHandler):
    def do_POST(self) -> None:
        site_apache_address = "{}{}".format(
            # Note: It would be nice to set this needed URL on __init__ of RedirectHandler,
            # but that's not possible because HTTPServer insists in taking a
            # SimpleHTTPSRequestHandler class instead of an instance. Hence we set it on the HTTPServer instead.
            self.server.site_apache_url,  # type: ignore[attr-defined]
            self.path,
        )
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
        http_port: int = 80,
        https_port: int = 443,
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

        raise Exception("No port available for HTTP Server")

    def create_self_signed_cert(self) -> None:
        # create a key pair
        k = crypto.PKey()
        k.generate_key(crypto.TYPE_RSA, 2048)

        # create a self-signed cert
        cert = crypto.X509()
        cert.get_subject().CN = self.dns_name
        cert.set_serial_number(1000)
        cert.gmtime_adj_notBefore(0)
        cert.gmtime_adj_notAfter(10 * 365 * 24 * 60 * 60)
        cert.set_issuer(cert.get_subject())
        cert.set_pubkey(k)
        san_list = [
            "DNS:" + self.dns_name,
            "IP:" + self.address,
        ]
        cert.add_extensions(
            [crypto.X509Extension(b"subjectAltName", False, ", ".join(san_list).encode("utf-8"))]
        )
        cert.sign(k, "sha256")

        # save to files
        Path(self.cert_file).write_bytes(crypto.dump_certificate(crypto.FILETYPE_PEM, cert))
        Path(self.key_file).write_bytes(crypto.dump_privatekey(crypto.FILETYPE_PEM, k))

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
