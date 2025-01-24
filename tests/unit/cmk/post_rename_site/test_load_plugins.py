#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence

import pytest

from tests.testlib.repo import is_cloud_repo, is_enterprise_repo

from cmk.post_rename_site import main
from cmk.post_rename_site.registry import rename_action_registry


@pytest.fixture(name="expected_plugins")
def fixture_expected_plugins() -> list[str]:
    expected = [
        "sites",
        "messaging",
        "hosts_and_folders",
        "update_core_config",
        "warn_remote_site",
        "warn_about_network_ports",
        "warn_about_configs_to_review",
        "compute_api_spec",
    ]

    # ATTENTION. The edition related code below is confusing and incorrect. The reason we need it
    # because our test environments do not reflect our Checkmk editions properly.
    # We cannot fix that in the short (or even mid) term because the
    # precondition is a more cleanly separated structure.
    if is_enterprise_repo():
        # The CEE plug-ins are loaded when the CEE plug-ins are available, i.e.
        # when the "enterprise/" path is present.
        expected.append("dcd_connections")

    if is_cloud_repo():
        # The CCE plug-ins are loaded when the CCE plug-ins are available
        expected.append("agent_controller_connections")

    return expected


def test_load_plugins(expected_plugins: Sequence[str]) -> None:
    """The test changes a global variable `rename_action_registry`.
    We can't reliably monkey patch this variable - must use separate module for testing"""
    main.load_plugins()
    assert sorted(rename_action_registry.keys()) == sorted(expected_plugins)
