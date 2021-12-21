#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import socket
import time
from typing import Any, Dict

from tests.testlib.site import Site


class CMKEventConsole:
    def __init__(self, site: Site):
        super().__init__()
        self.site = site
        self.status = CMKEventConsoleStatus("%s/tmp/run/mkeventd/status" % site.root)

    def _config(self):
        cfg: Dict[str, Any] = {}
        content = self.site.read_file("etc/check_mk/mkeventd.d/wato/global.mk")
        exec(content, {}, cfg)
        return cfg

    def _gather_status_port(self):
        config = self._config()

        if self.site.reuse and self.site.exists() and "remote_status" in config:
            port = config["remote_status"][0]
        else:
            port = self.site.get_free_port_from(self.site.livestatus_port + 1)

        self.status_port = port

    def enable_remote_status_port(self, web):
        html = web.get("wato.py?mode=mkeventd_config").text
        assert "mode=mkeventd_edit_configvar&amp;site=&amp;varname=remote_status" in html

        html = web.get(
            "wato.py?folder=&mode=mkeventd_edit_configvar&site=&varname=remote_status"
        ).text
        assert "Save" in html

        html = web.post(
            "wato.py",
            data={
                "filled_in": "value_editor",
                "ve_use": "on",
                "ve_value_0": self.status_port,
                "ve_value_2_use": "on",
                "ve_value_2_value_0": "127.0.0.1",
                "save": "Save",
                "varname": "remote_status",
                "mode": "mkeventd_edit_configvar",
            },
            add_transid=True,
        ).text
        assert "%d, no commands, 127.0.0.1" % self.status_port in html

    @classmethod
    def new_event(cls, attrs):
        now = time.time()
        default_event = {
            "rule_id": 815,
            "text": "",
            "phase": "open",
            "count": 1,
            "time": now,
            "first": now,
            "last": now,
            "comment": "",
            "host": "test-host",
            "ipaddress": "127.0.0.1",
            "application": "",
            "pid": 0,
            "priority": 3,
            "facility": 1,  # user
            "match_groups": (),
        }

        event = default_event.copy()
        event.update(attrs)
        return event


class CMKEventConsoleStatus:
    def __init__(self, address):
        self._address = address

    # Copied from web/htdocs/mkeventd.py. Better move to some common lib.
    def query(self, query):
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        timeout = 10

        sock.settimeout(timeout)
        sock.connect(self._address)
        sock.sendall(query)
        sock.shutdown(socket.SHUT_WR)

        response_text = b""
        while True:
            chunk = sock.recv(8192)
            response_text += chunk
            if not chunk:
                break

        return eval(response_text)  # pylint:disable=eval-used

    def query_table_assoc(self, query):
        response = self.query(query)
        headers = response[0]
        result = []
        for line in response[1:]:
            result.append(dict(zip(headers, line)))
        return result

    def query_value(self, query):
        return self.query(query)[0][0]
