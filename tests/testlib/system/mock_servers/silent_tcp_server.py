#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""A TCP server that accepts connections and never answers, for timeout tests.

Depends only on the stdlib so it runs under a plain ``python3`` in a mock container.
"""

import argparse
import socketserver
from typing import override


class _HoldTheLine(socketserver.BaseRequestHandler):
    @override
    def handle(self) -> None:
        # Read whatever the client sends and reply with nothing, until the client
        # gives up and closes the connection.
        while self.request.recv(4096):
            pass


class _Server(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, required=True)
    args = parser.parse_args()
    with _Server(("", args.port), _HoldTheLine) as server:
        server.serve_forever()


if __name__ == "__main__":
    main()
