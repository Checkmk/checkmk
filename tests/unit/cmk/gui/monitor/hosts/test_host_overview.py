#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import pytest

from cmk.gui.monitor.hosts._api._host_overview import _handle_get_host_overview
from cmk.gui.monitor.hosts._api._list_hosts import _handle_list_hosts
from cmk.gui.openapi.utils import ProblemException

from .testlib import get_fake_host_repository


def test_get_host_overview_success() -> None:
    host_repo = get_fake_host_repository(n_hosts=10)
    response = _handle_list_hosts(host_repo, limit=1)
    host = response.hosts[0]

    fetched_host = _handle_get_host_overview(
        host_repo,
        hostname=host.name,
        site_id=host.site_id,
        site_alias="Local site",
    )

    assert host.name == fetched_host.name
    assert host.site_id == fetched_host.site_id


def test_get_host_not_found() -> None:
    host_repo = get_fake_host_repository(n_hosts=10)
    with pytest.raises(ProblemException, match="404"):
        _handle_get_host_overview(host_repo, hostname="foo", site_id="bar", site_alias="bar")
