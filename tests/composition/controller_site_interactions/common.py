#!/usr/bin/env python3
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from tests.testlib.site import Site

from tests.composition.utils import execute

from cmk.utils.type_defs import HostName


def query_hosts_service_count(site: Site, hostname: HostName) -> int:
    services_response = site.openapi.get(f"objects/host/{hostname}/collections/services")
    assert services_response.ok
    return len(services_response.json()["value"])


def controller_status_json(contoller_path: Path) -> Mapping[str, Any]:
    return json.loads(
        execute(
            [
                "sudo",
                contoller_path.as_posix(),
                "status",
                "--json",
            ]
        ).stdout
    )
