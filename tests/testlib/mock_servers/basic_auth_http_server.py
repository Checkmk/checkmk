#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""HTTP server that requires basic auth and records who authenticated.

Run inside a mock container (see ``relay_component.start_basic_auth_http_server``):
``200`` for the expected ``Authorization`` header, ``401`` for anything else. Every
request appends one line to the log file, ``<client ip> auth=<ok|bad|missing>
<request line>``, so a test can assert which client presented the credential.

Standard library only: the container image has nothing else.
"""

import argparse
import base64
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import override


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument("--user", required=True)
    parser.add_argument("--password", required=True)
    parser.add_argument("--log", type=Path, required=True, help="request log to append to")
    return parser.parse_args()


def _make_handler(expected: str, log: Path) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            presented = self.headers.get("Authorization")
            if presented is None:
                outcome = "missing"
            elif presented == expected:
                outcome = "ok"
            else:
                outcome = "bad"
            with log.open("a") as stream:
                stream.write(f"{self.client_address[0]} auth={outcome} {self.requestline}\n")
            if outcome == "ok":
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b"authenticated")
                return
            self.send_response(401)
            self.send_header("WWW-Authenticate", 'Basic realm="relay-e2e"')
            self.end_headers()

        @override
        def log_message(self, format: str, *args: object) -> None:
            """Silence the default stderr log; the request log file is the record."""

    return Handler


def main() -> None:
    args = _parse_args()
    expected = "Basic " + base64.b64encode(f"{args.user}:{args.password}".encode()).decode()
    HTTPServer(("", args.port), _make_handler(expected, args.log)).serve_forever()


if __name__ == "__main__":
    main()
