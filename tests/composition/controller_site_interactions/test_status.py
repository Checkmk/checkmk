#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from pathlib import Path
from typing import Any

import pytest

from tests.testlib.agent import register_controller
from tests.testlib.site import Site

from tests.composition.controller_site_interactions.common import controller_status_json

from cmk.utils.type_defs import HostAgentConnectionMode, HostName


def _get_status_output_json(
    *,
    site: Site,
    agent_ctl: Path,
    hostname: HostName,
    host_attributes: Mapping[str, object],
) -> Mapping[str, Any]:
    site.openapi.create_host(hostname=hostname, attributes=dict(host_attributes))
    site.openapi.activate_changes_and_wait_for_completion()
    register_controller(agent_ctl, site, hostname)
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
    assert remote_status["hostname"] == "pull-host"
    assert HostAgentConnectionMode(remote_status["connection_mode"]) is HostAgentConnectionMode.PULL


@pytest.mark.usefixtures("skip_if_not_cloud_edition")
def test_status_push(
    central_site: Site,
    agent_ctl: Path,
) -> None:
    remote_status = _get_status_output_json(
        site=central_site,
        agent_ctl=agent_ctl,
        hostname=HostName("push-host"),
        host_attributes={"cmk_agent_connection": HostAgentConnectionMode.PUSH.value},
    )["connections"][0]["remote"]
    assert remote_status["hostname"] == "push-host"
    assert HostAgentConnectionMode(remote_status["connection_mode"]) is HostAgentConnectionMode.PUSH
