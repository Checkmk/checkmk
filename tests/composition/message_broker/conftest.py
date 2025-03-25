#!/usr/bin/env python3
# Copyright (C) 2020 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterator

import pytest

from tests.testlib.site import Site


@pytest.fixture(scope="session", autouse=True)
def message_broker_running(
    central_site: Site,
    remote_site: Site,
    remote_site_2: Site,
) -> Iterator[None]:
    # Note: the messsage broker can only be started indirectly.
    # It will start once it sees that it'll be needed by the piggyback hub:
    with (
        central_site.omd_config("PIGGYBACK_HUB", "on"),
        remote_site.omd_config("PIGGYBACK_HUB", "on"),
        remote_site_2.omd_config("PIGGYBACK_HUB", "on"),
    ):
        yield
