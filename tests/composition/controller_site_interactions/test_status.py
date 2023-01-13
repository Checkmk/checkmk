#!/usr/bin/env python3
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from pathlib import Path
from typing import Any

import pytest

from tests.testlib.site import Site

from tests.composition.controller_site_interactions.common import controller_status_json
from tests.composition.utils import execute

from cmk.utils.type_defs import HostName


def _get_status_output_json(
    *,
    site: Site,
    agent_ctl: Path,
    hostname: HostName,
    host_attributes: Mapping[str, object],
) -> Mapping[str, Any]:
    site.openapi.create_host(hostname=hostname, attributes=dict(host_attributes))
    site.openapi.activate_changes_and_wait_for_completion()
    execute(
        [
            "sudo",
            agent_ctl.as_posix(),
            "register",
            "--server",
            site.http_address,
            "--site",
            site.id,
            "--hostname",
            hostname,
            "--user",
            "cmkadmin",
            "--password",
            site.admin_password,
            "--trust-cert",
        ]
    )
    return controller_status_json(agent_ctl)


def test_status_pull(
    central_site: Site,
    agent_ctl: Path,
) -> None:
    remote_status = _get_status_output_json(
        site=central_site,
        agent_ctl=agent_ctl,
        hostname=HostName("pull-host"),
        host_attributes={},
    )["connections"][0]["remote"]
    assert remote_status["host_name"] == "pull-host"
    assert remote_status["connection_type"] == "pull-agent"


@pytest.mark.usefixtures("skip_if_not_cloud_edition")
def test_status_push(
    central_site: Site,
    agent_ctl: Path,
) -> None:
    remote_status = _get_status_output_json(
        site=central_site,
        agent_ctl=agent_ctl,
        hostname=HostName("push-host"),
        host_attributes={"cmk_agent_connection": "push-agent"},
    )["connections"][0]["remote"]
    assert remote_status["host_name"] == "push-host"
    assert remote_status["connection_type"] == "push-agent"
