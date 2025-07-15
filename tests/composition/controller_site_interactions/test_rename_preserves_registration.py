#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

import pytest

from tests.testlib.agent import (
    controller_connection_json,
    controller_status_json,
    register_controller,
)
from tests.testlib.site import Site

from cmk.ccc.hostaddress import HostName


def _test_rename_preserves_registration(
    *,
    central_site: Site,
    registration_site: Site,
    ctl_path: Path,
    hostname: HostName,
) -> None:
    new_hostname = HostName(f"{hostname}-renamed")
    try:
        response_create = central_site.openapi.hosts.create(
            hostname=hostname,
            attributes={
                "ipaddress": "127.0.0.1",
                "site": registration_site.id,
            },
        )
        central_site.openapi.changes.activate_and_wait_for_completion()
        register_controller(
            ctl_path,
            registration_site,
            hostname,
        )
        central_site.openapi.hosts.rename_and_wait_for_completion(
            hostname_old=hostname,
            hostname_new=new_hostname,
            etag=response_create.headers["ETag"],
        )
        assert central_site.openapi.hosts.get(new_hostname) is not None
        controller_status = controller_status_json(ctl_path)
        connection_details = controller_connection_json(controller_status, registration_site)
        assert connection_details["remote"]["hostname"] == new_hostname, (
            f"Checking if controller sees renaming failed!\nStatus:\n{controller_status}"
        )
    finally:
        hostnames = set(central_site.openapi.hosts.get_all_names())
        for hostname_ in hostnames.intersection({hostname, new_hostname}):
            central_site.openapi.hosts.delete(hostname_)
        central_site.openapi.changes.activate_and_wait_for_completion(force_foreign_changes=True)


@pytest.mark.skip_if_not_containerized
def test_rename_preserves_registration_central(
    central_site: Site,
    agent_ctl: Path,
) -> None:
    _test_rename_preserves_registration(
        central_site=central_site,
        registration_site=central_site,
        ctl_path=agent_ctl,
        hostname=HostName("central"),
    )


@pytest.mark.skip_if_not_containerized
def test_rename_preserves_registration_remote(
    central_site: Site,
    remote_site: Site,
    agent_ctl: Path,
) -> None:
    _test_rename_preserves_registration(
        central_site=central_site,
        registration_site=remote_site,
        ctl_path=agent_ctl,
        hostname=HostName("remote"),
    )
