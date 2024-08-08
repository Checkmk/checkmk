#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import contextlib
import logging
from collections.abc import Iterator, Mapping
from pathlib import Path
from typing import Any

from tests.testlib.agent import (
    controller_connection_json,
    controller_status_json,
    register_controller,
)
from tests.testlib.pytest_helpers.marks import skip_if_not_cloud_edition, skip_if_not_containerized
from tests.testlib.site import Site

from cmk.utils.agent_registration import HostAgentConnectionMode
from cmk.utils.hostaddress import HostName

logger = logging.getLogger("agent-receiver")


@contextlib.contextmanager
def _get_status_output_json(
    *,
    site: Site,
    agent_ctl: Path,
    hostname: HostName,
    host_attributes: Mapping[str, object],
) -> Iterator[Mapping[str, Any]]:
    try:
        site.openapi.create_host(hostname=hostname, attributes=dict(host_attributes))
        site.openapi.activate_changes_and_wait_for_completion()

        register_controller(agent_ctl, site, hostname)
        yield controller_status_json(agent_ctl)
    finally:
        site.openapi.delete_host(hostname=hostname)
        site.openapi.activate_changes_and_wait_for_completion(force_foreign_changes=True)


def test_status_pull(
    central_site: Site,
    agent_ctl: Path,
) -> None:
    with _get_status_output_json(
        site=central_site,
        agent_ctl=agent_ctl,
        hostname=HostName("pull-host"),
        host_attributes={},
    ) as controller_status:
        remote_status = controller_connection_json(controller_status, central_site)["remote"]
        logger.debug("Status output: {remote_status}")
        assert not remote_status.get("error"), f"Error in status output: {remote_status['error']}"
        assert remote_status.get(
            "hostname"
        ), 'Error in status output: No "hostname" field returned!'
        assert (
            remote_status["hostname"] == "pull-host"
        ), f"Error in status output: Invalid host name {remote_status['hostname']} returned!"
        assert (
            HostAgentConnectionMode(remote_status["connection_mode"])
            is HostAgentConnectionMode.PULL
        )


@skip_if_not_containerized
@skip_if_not_cloud_edition
def test_status_push(
    central_site: Site,
    agent_ctl: Path,
) -> None:
    with _get_status_output_json(
        site=central_site,
        agent_ctl=agent_ctl,
        hostname=HostName("push-host"),
        host_attributes={"cmk_agent_connection": HostAgentConnectionMode.PUSH.value},
    ) as controller_status:
        remote_status = controller_connection_json(controller_status, central_site)["remote"]
        assert not remote_status.get("error"), f"Error in status output: {remote_status['error']}"
        assert remote_status.get(
            "hostname"
        ), 'Error in status output: No "hostname" field returned!'
        assert (
            remote_status["hostname"] == "push-host"
        ), f'Error in status output: Invalid host name "{remote_status["hostname"]}" returned!'
        assert (
            HostAgentConnectionMode(remote_status["connection_mode"])
            is HostAgentConnectionMode.PUSH
        )
