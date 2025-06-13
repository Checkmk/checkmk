#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import json
import sys
from collections.abc import Mapping, Sequence

import requests
import requests_unixsocket  # type: ignore[import-untyped]

DEFAULT_SOCKET_PATH = "/run/podman/podman.sock"


def write_section(name: str, json_content: str) -> None:
    sys.stdout.write(f"<<<podman_{name}:sep(0)>>>\n")
    sys.stdout.write(f"{json_content}\n")
    sys.stdout.flush()


def write_piggyback_section(target_host: str, section_name: str, json_content: str) -> None:
    sys.stdout.write(f"<<<<{target_host}>>>>\n")
    write_section(section_name, json_content)
    sys.stdout.write("<<<<>>>>\n")
    sys.stdout.flush()


def _handle_exception(e: Exception, endpoint: str) -> dict:
    if isinstance(e, requests.exceptions.HTTPError):
        return {
            "error": f"HTTP errorfor endpoint {endpoint}: {str(e)}",
            "status_code": e.response.status_code if e.response else None,
        }
    return {"error": f"Error accessing endpoint {endpoint}: {str(e)}"}


def query_containers(
    session: requests_unixsocket.Session, base_url: str
) -> Sequence[Mapping[str, object]]:
    endpoint = "/v4.0.0/libpod/containers/json"
    try:
        response = session.get(base_url + endpoint)
        response.raise_for_status()
        output = response.json()
    except Exception as e:
        output = _handle_exception(e, endpoint)
    write_section("containers", json.dumps(output))
    return output


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


def query_container_inspect(
    session: requests_unixsocket.Session,
    base_url: str,
    container_id: str,
) -> None:
    endpoint = f"/v4.0.0/libpod/containers/{container_id}/json"
    try:
        response = session.get(base_url + endpoint)
        response.raise_for_status()
        output = response.json()
    except Exception as e:
        output = _handle_exception(e, endpoint)
    write_piggyback_section(
        target_host=container_id, section_name="container_inspect", json_content=json.dumps(output)
    )


def query_container_stats(
    session: requests_unixsocket.Session, base_url: str
) -> Mapping[str, object]:
    endpoint = "/v4.0.0/libpod/containers/stats?stream=false&all=true"
    try:
        response = session.get(base_url + endpoint)
        response.raise_for_status()
        output = response.json()
    except Exception as e:
        output = _handle_exception(e, endpoint)
    return output


def _container_id_to_stats(stats_data: Mapping[str, object]) -> Mapping[str, object]:
    if error := stats_data.get("Error"):
        return {"Error": error}

    if not isinstance(stats := stats_data.get("Stats", []), list):
        return {}
    return {stat["ContainerID"]: stat for stat in stats if "ContainerID" in stat}


def main() -> None:
    with requests_unixsocket.Session() as session:
        base_url = f"http+unix://{DEFAULT_SOCKET_PATH.replace('/', '%2F')}"

        containers = query_containers(session, base_url)
        query_disk_usage(session, base_url)
        query_engine(session, base_url)
        query_pods(session, base_url)

        container_to_stats = _container_id_to_stats(query_container_stats(session, base_url))

        for container in containers:
            if not (container_id := str(container.get("Id", ""))):
                continue

            query_container_inspect(session, base_url, container_id)

            if stats := container_to_stats.get(container_id) or container_to_stats.get("Error"):
                write_piggyback_section(
                    target_host=container_id,
                    section_name="container_stats",
                    json_content=json.dumps(stats),
                )


if __name__ == "__main__":
    main()
