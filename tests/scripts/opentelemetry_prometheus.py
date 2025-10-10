#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"

"""This script demonstrates the use of OpenTelemetry for metrics export via Prometheus."""

import argparse
import datetime
import logging
import signal
import ssl
import sys
import threading
import time
from pathlib import Path
from socketserver import ThreadingMixIn
from wsgiref.simple_server import make_server, WSGIRequestHandler, WSGIServer

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID
from prometheus_client import Counter, make_wsgi_app, start_http_server

logger = logging.getLogger("otel.prometheus")
logger.addHandler(logging.StreamHandler(sys.stdout))
logger.setLevel(logging.INFO)

PROMETHEUS_PORT = 9090
SLEEP_DURATION = 30

DEFAULT_OTEL_COLLECTOR_PROMETHEUS_METRIC_COUNT = 5  # metrics the site collector adds
DEFAULT_PROMETHEUS_METRIC_COUNT = 10  # metrics the client sdk adds
DEFAULT_CMK_SERVICE_COUNT = 2  # Check_MK and Check_MK Discovery
PROMETHEUS_METRIC_COUNT = 1  # only one Counter metric is used in this script
EXPECTED_PROMETHEUS_SERVICE_COUNT = (
    DEFAULT_OTEL_COLLECTOR_PROMETHEUS_METRIC_COUNT
    + DEFAULT_PROMETHEUS_METRIC_COUNT
    + DEFAULT_CMK_SERVICE_COUNT
    + PROMETHEUS_METRIC_COUNT * 2
)

CERTFILE: Path = Path("server.crt")
KEYFILE: Path = Path("server.key")


class SilentWSGIRequestHandler(WSGIRequestHandler):
    def log_message(self, format, *args):
        # Suppress all access logs (GET /metrics etc.)
        pass


def shutdown_handler(signum: object, frame: object) -> None:
    logger.info("Shutting down Prometheus HTTP server.")
    for f in (CERTFILE, KEYFILE):
        # Remove temporary cert and key files
        if f.exists():
            try:
                f.unlink()
                logger.info(f"Deleted temporary file: {f}")
            except Exception as e:
                logger.warning(f"Failed to delete {f}: {e}")
    sys.exit(0)


class ThreadingWSGIServer(ThreadingMixIn, WSGIServer):
    """WSGI server with threads."""


def _generate_self_signed_cert():
    """Generate a self-signed certificate and private key if they don't exist."""
    logger.info("Generating self-signed TLS certificate and key...")

    # Generate private key
    key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )

    # Write private key to file
    with open(KEYFILE, "wb") as f:
        f.write(
            key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.TraditionalOpenSSL,
                encryption_algorithm=serialization.NoEncryption(),
            )
        )

    # Build certificate
    subject = issuer = x509.Name(
        [
            x509.NameAttribute(NameOID.COUNTRY_NAME, "DE"),
            x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "Berlin"),
            x509.NameAttribute(NameOID.LOCALITY_NAME, "Berlin"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "TestOrg"),
            x509.NameAttribute(NameOID.COMMON_NAME, "localhost"),
        ]
    )
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.datetime.now())
        .not_valid_after(datetime.datetime.now() + datetime.timedelta(days=365))
        .add_extension(
            x509.SubjectAlternativeName([x509.DNSName("localhost")]),
            critical=False,
        )
        .sign(key, hashes.SHA256())
    )

    # Write cert to file
    with open(CERTFILE, "wb") as f:
        f.write(cert.public_bytes(serialization.Encoding.PEM))

    logger.info(f"Self-signed cert generated: {CERTFILE}, {KEYFILE}")


def start_secure_http_server(port: int) -> None:
    """Start a TLS-enabled Prometheus HTTP server."""
    app = make_wsgi_app()
    httpd = make_server(
        "", port, app, server_class=ThreadingWSGIServer, handler_class=SilentWSGIRequestHandler
    )

    _generate_self_signed_cert()
    # Create an SSL context instead of ssl.wrap_socket
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(certfile=CERTFILE, keyfile=KEYFILE)

    httpd.socket = context.wrap_socket(httpd.socket, server_side=True)

    def _serve():
        logger.info(f"Starting Prometheus HTTPS server on port {port}.")
        httpd.serve_forever()

    # Run server in background thread
    thread = threading.Thread(target=_serve, daemon=True)
    thread.start()


def main() -> None:
    parser = argparse.ArgumentParser(description="OpenTelemetry Prometheus Example")
    parser.add_argument(
        "--enable-tls",
        action="store_true",
        help="Enable OpenTelemetry TLS",
    )
    args = parser.parse_args()

    # Create a Prometheus counter metric
    prometheus_counter = Counter("test_counter", "A simple counter for testing")

    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, shutdown_handler)
    signal.signal(signal.SIGTERM, shutdown_handler)

    if args.enable_tls:
        logger.info(f"Starting Prometheus HTTPS server with TLS enabled on port {PROMETHEUS_PORT}.")
        start_secure_http_server(PROMETHEUS_PORT)
    else:
        logger.info(f"Starting Prometheus HTTP server on port {PROMETHEUS_PORT}.")
        start_http_server(PROMETHEUS_PORT)

    counter = 0
    while True:
        logger.info(f"Counter value is {counter}.")
        prometheus_counter.inc()
        counter += 1
        time.sleep(SLEEP_DURATION)


if __name__ == "__main__":
    main()
