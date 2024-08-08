#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from contextlib import suppress
from pathlib import Path

from tests.testlib.agent import (
    controller_connection_json,
    controller_status_json,
    register_controller,
)
from tests.testlib.openapi_session import UnexpectedResponse
from tests.testlib.pytest_helpers.marks import skip_if_not_containerized
from tests.testlib.site import Site

from cmk.utils.hostaddress import HostName


def _test_rename_preserves_registration(
    *,
    central_site: Site,
    registration_site: Site,
    agent_ctl: Path,
    hostname: HostName,
) -> None:
    new_hostname = HostName(f"{hostname}-renamed")
    try:
        response_create = central_site.openapi.create_host(
            hostname=hostname,
            attributes={
                "ipaddress": "127.0.0.1",
                "site": registration_site.id,
            },
        )
        central_site.openapi.activate_changes_and_wait_for_completion()
        register_controller(
            agent_ctl,
            registration_site,
            hostname,
        )
        central_site.openapi.rename_host_and_wait_for_completion(
            hostname_old=hostname,
            hostname_new=new_hostname,
            etag=response_create.headers["ETag"],
        )
        assert central_site.openapi.get_host(new_hostname) is not None
        controller_status = controller_status_json(agent_ctl)
        connection_details = controller_connection_json(controller_status, central_site)
        try:
            assert HostName(connection_details["remote"]["hostname"]) == new_hostname
        except Exception as e:
            raise Exception(
                f"Checking if controller sees renaming failed. Status output:\n{controller_status}"
            ) from e
    finally:
        with suppress(UnexpectedResponse):
            central_site.openapi.delete_host(hostname)
            central_site.openapi.delete_host(new_hostname)
        central_site.openapi.activate_changes_and_wait_for_completion(force_foreign_changes=True)


@skip_if_not_containerized
def test_rename_preserves_registration_central(
    central_site: Site,
    agent_ctl: Path,
) -> None:
    _test_rename_preserves_registration(
        central_site=central_site,
        registration_site=central_site,
        agent_ctl=agent_ctl,
        hostname=HostName("central"),
    )


@skip_if_not_containerized
def test_rename_preserves_registration_remote(
    central_site: Site,
    remote_site: Site,
    agent_ctl: Path,
) -> None:
    _test_rename_preserves_registration(
        central_site=central_site,
        registration_site=remote_site,
        agent_ctl=agent_ctl,
        hostname=HostName("remote"),
    )
