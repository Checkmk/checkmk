#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Unit tests for the distributed setup helper :func:`tests.testlib.site.connection`."""

from unittest.mock import MagicMock

import pytest

from tests.testlib.common.version import CMKVersion
from tests.testlib.site import connection, Site


def _site(site_id: str) -> MagicMock:
    site = MagicMock(spec=Site)
    site.id = site_id
    # not a class attribute of Site, so the spec does not provide it
    site.openapi = MagicMock()
    site.version = CMKVersion("3.0.0")
    site.edition.is_ultimatemt_edition.return_value = False
    site.http_address = "127.0.0.1"
    site.livestatus_port = 6557
    site.message_broker_port = 5672
    site.internal_url = f"http://127.0.0.1/{site_id}/check_mk/"
    return site


def test_connection_is_removed_when_the_site_login_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CLEANUP", "1")
    central_site = _site("central")
    remote_site = _site("remote")
    central_site.openapi.sites.login.side_effect = RuntimeError("no answer from the remote site")

    with (
        pytest.raises(RuntimeError),
        connection(central_site=central_site, remote_site=remote_site, enable_replication=True),
    ):
        pytest.fail("the connection setup must not succeed")

    central_site.openapi.sites.delete.assert_called_once_with(remote_site.id)


def test_no_connection_is_removed_when_none_was_created(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CLEANUP", "1")
    central_site = _site("central")
    remote_site = _site("remote")
    central_site.openapi.sites.create.side_effect = RuntimeError("connection rejected")

    with (
        pytest.raises(RuntimeError),
        connection(central_site=central_site, remote_site=remote_site, enable_replication=True),
    ):
        pytest.fail("the connection setup must not succeed")

    central_site.openapi.sites.delete.assert_not_called()
