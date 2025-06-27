#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import json
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import assert_never

DEFAULT_SOCKET_PATH = "/run/podman/podman.sock"


@dataclass(frozen=True)
class JSONSection:
    name: str
    content: str


@dataclass(frozen=True)
class Error:
    label: str
    message: str


def write_section(section: JSONSection | Error) -> None:
    match section:
        case JSONSection():
            _write_serialized_section(section.name, section.content)
        case Error():
            _write_serialized_section(
                "errors", json.dumps({"endpoint": section.label, "message": section.message})
            )
        case _:
            assert_never(section)


def _write_serialized_section(name: str, json_content: str) -> None:
    sys.stdout.write(f"<<<podman_{name}:sep(0)>>>\n")
    sys.stdout.write(f"{json_content}\n")
    sys.stdout.flush()


try:
    import requests_unixsocket  # type: ignore[import-untyped]
except ImportError as e:
    write_section(
        Error(
            label="requests_unixsocket",
            message=f"Failed to import requests_unixsocket: {e}. "
            "Please install the requests-unixsocket package.",
        )
    )


def write_piggyback_section(target_host: str, section: JSONSection | Error) -> None:
    sys.stdout.write(f"<<<<{target_host}>>>>\n")
    write_section(section)
    sys.stdout.write("<<<<>>>>\n")
    sys.stdout.flush()


def _build_url_human_readable(socket_path: str, endpoint_uri: str) -> str:
    return f"{socket_path}{endpoint_uri}"


def _build_url_callable(socket_path: str, endpoint_uri: str) -> str:
    return f"http+unix://{socket_path.replace('/', '%2F')}{endpoint_uri}"


def query_containers(
    session: requests_unixsocket.Session, socket_path: str
) -> Sequence[Mapping[str, object]]:
    endpoint = "/v4.0.0/libpod/containers/json"
    try:
        response = session.get(_build_url_callable(socket_path, endpoint))
        response.raise_for_status()
        output = response.json()
    except Exception as e:
        write_section(Error(_build_url_human_readable(socket_path, endpoint), str(e)))
    write_section(JSONSection("containers", json.dumps(output)))
    return output


def query_disk_usage(session: requests_unixsocket.Session, socket_path: str) -> None:
    endpoint = "/v4.0.0/libpod/system/df"
    try:
        response = session.get(_build_url_callable(socket_path, endpoint))
        response.raise_for_status()
    except Exception as e:
        write_section(Error(_build_url_human_readable(socket_path, endpoint), str(e)))
    write_section(JSONSection("disk_usage", json.dumps(response.json())))


def query_engine(session: requests_unixsocket.Session, socket_path: str) -> None:
    endpoint = "/v4.0.0/libpod/info"
    try:
        response = session.get(_build_url_callable(socket_path, endpoint))
        response.raise_for_status()
    except Exception as e:
        write_section(Error(_build_url_human_readable(socket_path, endpoint), str(e)))
    write_section(JSONSection("engine", json.dumps(response.json())))


def query_pods(session: requests_unixsocket.Session, socket_path: str) -> None:
    endpoint = "/v4.0.0/libpod/pods/json"
    try:
        response = session.get(_build_url_callable(socket_path, endpoint))
        response.raise_for_status()
    except Exception as e:
        write_section(Error(_build_url_human_readable(socket_path, endpoint), str(e)))
    write_section(JSONSection("pods", json.dumps(response.json())))


def query_container_inspect(
    session: requests_unixsocket.Session,
    socket_path: str,
    container_id: str,
    container_name: str,
) -> None:
    endpoint = f"/v4.0.0/libpod/containers/{container_id}/json"
    try:
        response = session.get(_build_url_callable(socket_path, endpoint))
        response.raise_for_status()
        section: JSONSection | Error = JSONSection("container_inspect", json.dumps(response.json()))
    except Exception as e:
        section = Error(_build_url_human_readable(socket_path, endpoint), str(e))
    write_piggyback_section(target_host=f"{container_name}_{container_id[:12]}", section=section)


def query_container_stats(
    session: requests_unixsocket.Session, socket_path: str
) -> Mapping[str, object]:
    endpoint = "/v4.0.0/libpod/containers/stats?stream=false&all=true"
    try:
        response = session.get(_build_url_callable(socket_path, endpoint))
        response.raise_for_status()
        return response.json()
    except Exception as e:
        write_section(Error(_build_url_human_readable(socket_path, endpoint), str(e)))
    return {}


def _container_id_to_stats(stats_data: Mapping[str, object]) -> Mapping[str, object]:
    if not isinstance(stats := stats_data.get("Stats", []), list):
        return {}
    return {stat["ContainerID"]: stat for stat in stats if "ContainerID" in stat}


def _get_container_name(names: object) -> str:
    if isinstance(names, list) and names:
        return names[0].lstrip("/")
    return "unnamed"


def main() -> None:
    socket_paths = [DEFAULT_SOCKET_PATH]

    for socket_path in socket_paths:
        with requests_unixsocket.Session() as session:
            containers = query_containers(session, socket_path)
            query_disk_usage(session, socket_path)
            query_engine(session, socket_path)
            query_pods(session, socket_path)

        container_to_stats = _container_id_to_stats(query_container_stats(session, socket_path))

        for container in containers:
            if not (container_id := str(container.get("Id", ""))):
                continue

            container_name = _get_container_name(container["Names"])

            query_container_inspect(session, socket_path, container_id, container_name)

            if stats := container_to_stats.get(container_id):
                write_piggyback_section(
                    target_host=f"{container_name}_{container_id[:12]}",
                    section=JSONSection("container_stats", json.dumps(stats)),
                )


if __name__ == "__main__":
    main()
