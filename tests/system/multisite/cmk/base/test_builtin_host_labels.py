#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
from collections.abc import Iterator, Mapping
from contextlib import contextmanager

import pytest

from tests.testlib.common.utils import wait_until
from tests.testlib.site import Site

logger = logging.getLogger(__name__)

_CUSTOMER = "customer1"
_FOLDER = "builtin_labels_cust1"
_HOST_NAME = "builtin-labels-remote-host"


@contextmanager
def _remote_site_customer(central_site: Site, remote_site: Site, customer: str) -> Iterator[None]:
    """Assign ``customer`` to the (session-scoped) remote site, restoring the original after."""

    def _set(value: str) -> None:
        connection = central_site.openapi.sites.show(remote_site.id)
        connection["basic_settings"]["customer"] = value
        central_site.openapi.sites.update(remote_site.id, connection)
        central_site.openapi.changes.activate_and_wait_for_completion()

    original_customer = central_site.openapi.sites.show(remote_site.id)["basic_settings"][
        "customer"
    ]
    _set(customer)
    try:
        yield
    finally:
        _set(original_customer)


@pytest.fixture(name="remote_monitored_host", scope="module")
def remote_monitored_host_fixture(central_site: Site, remote_site: Site) -> Iterator[str]:
    with _remote_site_customer(central_site, remote_site, _CUSTOMER):
        # A folder pinned to the remote site inherits the remote's customer; the host placed in
        # it inherits both the site and the customer (CME derives the customer from the site).
        central_site.openapi.folders.create(f"/{_FOLDER}", attributes={"site": remote_site.id})
        central_site.openapi.hosts.create(
            _HOST_NAME, folder=f"/{_FOLDER}", attributes={"ipaddress": "127.0.0.1"}
        )
        try:
            central_site.openapi.changes.activate_and_wait_for_completion()
            yield _HOST_NAME
        finally:
            central_site.openapi.hosts.delete(_HOST_NAME)
            central_site.openapi.folders.delete(f"/{_FOLDER}")
            central_site.openapi.changes.activate_and_wait_for_completion()


def _monitored_host_labels(central_site: Site, host_name: str) -> Mapping[str, str] | None:
    # The monitoring host endpoint is multisite (livestatus), so querying the central site
    # returns the remote-monitored host's labels.
    response = central_site.openapi.get(
        f"/objects/host/{host_name}", params={"columns": ["labels"]}
    )
    if response.status_code == 404:
        return None
    response.raise_for_status()
    return {str(k): str(v) for k, v in response.json()["extensions"]["labels"].items()}


@pytest.mark.skip_if_not_edition("ultimatemt")
def test_remote_host_has_builtin_site_and_customer_labels(
    central_site: Site, remote_site: Site, remote_monitored_host: str
) -> None:
    """A host monitored by a managed remote carries the remote's builtin ``cmk/site`` and
    ``cmk/customer`` labels.

    This exercises the distributed behavior: the builtin host labels file is generated locally
    on the remote during its activation (it is not synced from the central site), so ``cmk/site``
    is the remote site id and ``cmk/customer`` is the customer assigned to the remote.
    """
    wait_until(
        lambda: _monitored_host_labels(central_site, remote_monitored_host) is not None,
        timeout=60,
        interval=2,
        condition_name=f"host {remote_monitored_host} appears in monitoring",
    )
    labels = _monitored_host_labels(central_site, remote_monitored_host)
    assert labels is not None
    assert labels["cmk/site"] == remote_site.id
    assert labels["cmk/customer"] == _CUSTOMER
