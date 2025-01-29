#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import socket
from typing import Any

from tests.testlib.site import Site


class CMKEventConsole:
    def __init__(self, site: Site) -> None:
        super().__init__()
        self.site = site
        self.status = CMKEventConsoleStatus(f"{site.root}/tmp/run/mkeventd/status")

    def _config(self) -> dict[str, Any]:
        cfg: dict[str, Any] = {}
        content = self.site.read_file("etc/check_mk/mkeventd.d/wato/global.mk")
        exec(content, {}, cfg)
        return cfg

    def _gather_status_port(self) -> None:
        config = self._config()

        if self.site.reuse and self.site.exists() and "remote_status" in config:
            port = config["remote_status"][0]
        else:
            port = self.site.get_free_port_from(self.site.livestatus_port + 1)

        self.status_port = port


class CMKEventConsoleStatus:
    def __init__(self, address: str) -> None:
        self._address = address

    # Copied from web/htdocs/mkeventd.py. Better move to some common lib.
    def query(self, query: str) -> Any:
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        timeout = 10

        sock.settimeout(timeout)
        sock.connect(self._address)
        sock.sendall(query.encode("utf-8"))
        sock.shutdown(socket.SHUT_WR)

        response_text = b""
        while True:
            chunk = sock.recv(8192)
            response_text += chunk
            if not chunk:
                break

        return eval(response_text)

    def query_table_assoc(self, query: str) -> list[dict]:
        response = self.query(query)
        headers = response[0]
        result = []
        for line in response[1:]:
            result.append(dict(zip(headers, line)))
        return result

    def query_value(self, query: str) -> Any:
        return self.query(query)[0][0]
