#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import json
import sys

import requests
import requests_unixsocket  # type: ignore[import-untyped]

DEFAULT_SOCKET_PATH = "/run/podman/podman.sock"


def write_section(name: str, json_content: str) -> None:
    sys.stdout.write(f"<<<podman_{name}:sep(0)>>>\n")
    sys.stdout.write(f"{json_content}\n")
    sys.stdout.flush()


def _handle_exception(e: Exception, endpoint: str) -> dict:
    if isinstance(e, requests.exceptions.HTTPError):
        return {
            "error": f"HTTP errorfor endpoint {endpoint}: {str(e)}",
            "status_code": e.response.status_code if e.response else None,
        }
    return {"error": f"Error accessing endpoint {endpoint}: {str(e)}"}


def query_containers(session: requests_unixsocket.Session, base_url: str) -> None:
    endpoint = "/v4.0.0/libpod/containers/json"
    try:
        response = session.get(base_url + endpoint)
        response.raise_for_status()
        output = response.json()
    except Exception as e:
        output = _handle_exception(e, endpoint)
    write_section("containers", json.dumps(output))


def query_disk_usage(session: requests_unixsocket.Session, base_url: str) -> None:
    endpoint = "/v4.0.0/libpod/system/df"
    try:
        response = session.get(base_url + endpoint)
        response.raise_for_status()
        output = response.json()
    except Exception as e:
        output = _handle_exception(e, endpoint)
    write_section("disk_usage", json.dumps(output))


def query_engine(session: requests_unixsocket.Session, base_url: str) -> None:
    endpoint = "/v4.0.0/libpod/info"
    try:
        response = session.get(base_url + endpoint)
        response.raise_for_status()
        output = response.json()
    except Exception as e:
        output = _handle_exception(e, endpoint)
    write_section("engine", json.dumps(output))


def query_pods(session: requests_unixsocket.Session, base_url: str) -> None:
    endpoint = "/v4.0.0/libpod/pods/json"
    try:
        response = session.get(base_url + endpoint)
        response.raise_for_status()
        output = response.json()
    except Exception as e:
        output = _handle_exception(e, endpoint)
    write_section("pods", json.dumps(output))


def main() -> None:
    with requests_unixsocket.Session() as session:
        base_url = f"http+unix://{DEFAULT_SOCKET_PATH.replace('/', '%2F')}"

        query_containers(session, base_url)
        query_disk_usage(session, base_url)
        query_engine(session, base_url)
        query_pods(session, base_url)


if __name__ == "__main__":
    main()
