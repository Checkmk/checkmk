#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from __future__ import annotations

from functools import lru_cache
from pprint import pformat
from typing import List, TYPE_CHECKING

from cmk.utils.site import get_omd_config

if TYPE_CHECKING:
    from cmk.gui.wsgi.type_defs import StartResponse, WSGIApplication, WSGIEnvironment, WSGIResponse


def discover_receiver(environ: WSGIEnvironment, start_response: StartResponse) -> WSGIResponse:
    """Report the port of the agent receiver

    We report the agent receivers port on this unprotected URL.
    We don't give away an information here that an attacker could not find out with a port scan.
    """
    return serve_string(f"{_get_receiver_port()}")(environ, start_response)


@lru_cache
def _get_receiver_port() -> int:
    # make sure we really only ever report a number and nothing more
    return int(get_omd_config()["CONFIG_AGENT_RECEIVER_PORT"])


def dump_environ_app(environ: WSGIEnvironment, start_response: StartResponse) -> WSGIResponse:
    dumped_env = "\n".join(["{0}: {1}".format(k, environ[k]) for k in environ.keys()])
    return serve_string(dumped_env)(environ, start_response)


def serve_string(_str: str) -> WSGIApplication:
    def _server(_environ: WSGIEnvironment, start_response: StartResponse) -> WSGIResponse:
        status = "200 OK"
        encoding = "utf-8"
        out_data = _str.encode(encoding)
        response_headers = [
            ("Content-Type", f"text/plain; charset={encoding}"),
            ("Content-Length", str(len(out_data))),
        ]
        start_response(status, response_headers)

        return [out_data]

    return _server


def test_formdata(environ: WSGIEnvironment, start_response: StartResponse) -> WSGIResponse:
    # show the environment:
    output: List[bytes] = [
        b"<pre>",
        pformat(environ).encode("utf-8"),
        b"</pre>",
        b'<form method="post">',
        b'<input type="text" name="test">',
        b'<input type="submit">',
        b"</form>",
    ]

    if environ["REQUEST_METHOD"] == "POST":
        # show form data as received by POST:
        output.append(b"<h1>FORM DATA</h1>")
        output.append(pformat(environ["wsgi.input"].read()).encode("utf-8"))

    # send results
    output_len = sum(len(line) for line in output)
    start_response(
        "200 OK",
        [
            ("Content-type", "text/html; encoding=utf-8"),
            ("Content-Length", str(output_len)),
        ],
    )
    return output
