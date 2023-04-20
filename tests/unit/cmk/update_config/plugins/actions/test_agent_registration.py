#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
from pathlib import Path

import cmk.utils.paths
from cmk.utils.agent_registration import get_uuid_link_manager

from cmk.update_config.plugins.actions.agent_registration import AgentRegistration


def test_fix_agent_receiver_symlinks() -> None:
    source = Path(cmk.utils.paths.received_outputs_dir, "f0ca2e5d-06ea-4b04-89d1-67df0203d449")
    source.parent.mkdir(parents=True, exist_ok=True)

    target = Path(cmk.utils.paths.data_source_push_agent_dir, "my_new_host")
    source.symlink_to(target)

    link_manager = get_uuid_link_manager()
    links = list(link_manager)

    assert len(links) == 1
    assert links[0].source == source
    assert links[0].target == target

    run_update = AgentRegistration(
        name="fix_agent_registration_symlinks",
        title="Change absolute paths in registered hosts symlinks to relative",
        sort_index=100,  # can run whenever
    )
    run_update(logging.getLogger(), {})

    links = list(link_manager)
    assert len(links) == 1
    assert links[0].source == source
    assert links[0].target == Path(
        "../../../../tmp/check_mk/data_source_cache/push-agent/inactive/my_new_host"
    )
