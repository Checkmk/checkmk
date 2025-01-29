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
    ctl_path: Path,
    hostname: HostName,
    host_attributes: Mapping[str, object],
) -> Iterator[Mapping[str, Any]]:
    try:
        site.openapi.hosts.create(hostname=hostname, attributes=dict(host_attributes))
        site.openapi.changes.activate_and_wait_for_completion()

        register_controller(ctl_path, site, hostname)
        yield controller_status_json(ctl_path)
    finally:
        site.openapi.hosts.delete(hostname=hostname)
        site.openapi.changes.activate_and_wait_for_completion(force_foreign_changes=True)


@skip_if_not_containerized
def test_status_pull(
    central_site: Site,
    agent_ctl: Path,
) -> None:
    with _get_status_output_json(
        site=central_site,
        ctl_path=agent_ctl,
        hostname=HostName("pull-host"),
        host_attributes={"ipaddress": "127.0.0.1"},
    ) as controller_status:
        connection_details = controller_connection_json(controller_status, central_site)
        assert connection_details["remote"]["hostname"] == "pull-host", (
            f"Error in status output: Invalid host name returned!\nStatus:\n{controller_status}"
        )
        assert (
            HostAgentConnectionMode(connection_details["remote"]["connection_mode"])
            is HostAgentConnectionMode.PULL
        ), (
            f"Error in status output: Invalid connection mode returned!\nStatus:\n{controller_status}"
        )


@skip_if_not_containerized
@skip_if_not_cloud_edition
def test_status_push(
    central_site: Site,
    agent_ctl: Path,
) -> None:
    with _get_status_output_json(
        site=central_site,
        ctl_path=agent_ctl,
        hostname=HostName("push-host"),
        host_attributes={"cmk_agent_connection": HostAgentConnectionMode.PUSH.value},
    ) as controller_status:
        connection_details = controller_connection_json(controller_status, central_site)
        assert connection_details["remote"]["hostname"] == "push-host", (
            f"Error in status output: Invalid host name returned!\nStatus:\n{controller_status}"
        )
        assert (
            HostAgentConnectionMode(connection_details["remote"]["connection_mode"])
            is HostAgentConnectionMode.PUSH
        )
