#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest
from pytest_mock import MockerFixture

from cmk.automations.results import ReloadResult, RestartResult
from cmk.gui.watolib.config_domains import ConfigDomainCore


@pytest.mark.usefixtures("request_context")
def test_activate_bakes_agents_before_the_core_picks_up_the_config(
    mocker: MockerFixture,
) -> None:
    calls: list[str] = []

    def bake(**kwargs: object) -> None:
        calls.append("bake")

    def restart(*args: object, **kwargs: object) -> RestartResult:
        calls.append("restart")
        return RestartResult([])

    def reload(*args: object, **kwargs: object) -> ReloadResult:
        calls.append("reload")
        return ReloadResult([])

    mocker.patch("cmk.gui.watolib.bakery.try_bake_agents_on_activation", side_effect=bake)
    mocker.patch("cmk.gui.watolib.config_domains.restart", side_effect=restart)
    mocker.patch("cmk.gui.watolib.config_domains.reload", side_effect=reload)

    ConfigDomainCore().activate()

    assert calls[0] == "bake"
    assert calls[1] in ("restart", "reload")
