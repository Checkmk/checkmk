#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import subprocess
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from pydantic import BaseModel

from tests.testlib.site import Site

from cmk.ccc.hostaddress import HostName

_THIS_DIR = Path(__file__).parent

_MOCKUP_SERVER_FILE = _THIS_DIR / "mockup-server/redfishMockupServer.py"

MOCKUP_DUMPS_DIR = _THIS_DIR / "mockup-server/dumps"


@dataclass(frozen=True)
class Hosts:
    dell_ok: HostName
    hpe_ok: HostName
    raritan_ok: HostName


def create_special_agent_host(site: Site, host_name: HostName) -> HostName:
    """Create a host with special agent attributes.

    For convenience, we return the host name.
    """
    site.openapi.hosts.create(
        host_name,
        attributes={
            "ipaddress": "127.0.0.1",
            "tag_address_family": "ip-v4-only",
            "tag_agent": "special-agents",
            "tag_piggyback": "no-piggyback",
        },
    )
    return host_name


def create_special_agent_rule(
    site: Site,
    host_name: HostName,
    agent: Literal["redfish", "redfish_power"],
    **value: object,
) -> str:
    return site.openapi.rules.create(
        {
            "user": "stgns",
            "password": (
                "cmk_postprocessed",
                "explicit_password",
                ("uuid672cd00a-d45d-4b06-b179-77fb5ca922d7", "stbstb"),
            ),
            "proto": "http",
            "retries": 2,
            "timeout": 3.0,
            **({"debug": False} if agent == "redfish" else {}),
            **value,
        },
        f"special_agents:{agent}",
        "/",
        {
            "host_name": {
                "match_on": [host_name],
                "operator": "one_of",
            },
        },
    )


def run_mockup_server(*, dataset_path: Path, port: int) -> subprocess.Popen:
    return subprocess.Popen(
        ["python3", _MOCKUP_SERVER_FILE, "--port", f"{port}", "-D", dataset_path],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
    )


class Service(BaseModel, frozen=True):
    description: str
    check_command: str
    state: Literal[0, 1, 2, 3]
    plugin_output: str


def get_service(site: Site, host_name: HostName, description: str) -> Service:
    return {s.description: s for s in get_services(site, host_name)}[description]


def get_services(site: Site, host_name: HostName) -> Sequence[Service]:
    return [
        Service.model_validate(v["extensions"])
        for v in site.openapi.services.get_host_services(
            host_name,
            columns=list(Service.model_fields),
        )
    ]
