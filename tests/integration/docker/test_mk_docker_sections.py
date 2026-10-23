#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import re
from collections.abc import Callable
from functools import partial
from types import SimpleNamespace

import pytest

from agents.plugins import mk_docker
from cmk.agent_based.v2 import AgentSection, entry_point_prefixes
from cmk.discover_plugins import discover_all_plugins, PluginGroup


@pytest.fixture(name="agent_section_names", scope="module")
def fixture_agent_section_names() -> set[str]:
    discovered = discover_all_plugins(
        PluginGroup.AGENT_BASED,
        {AgentSection: entry_point_prefixes()[AgentSection]},
        skip_wrong_types=True,
        raise_errors=True,
    )
    return {section.name for section in discovered.plugins.values()}


def _fake_client() -> SimpleNamespace:
    container = SimpleNamespace(
        attrs={"State": {"Status": "running"}, "NetworkSettings": {}},
        labels={},
        image=SimpleNamespace(tags=[]),
    )
    return SimpleNamespace(
        node_info={"Name": "node1"},
        all_containers={"c0ffee": container},
        get_container_stats=lambda _id: {"memory_stats": {}, "cpu_stats": {}, "blkio_stats": {}},
        device_map=dict,
        df=dict,
        api=SimpleNamespace(images=list, containers=list),
        images=SimpleNamespace(get=None),
        containers=SimpleNamespace(get=None),
        networks=SimpleNamespace(list=lambda **_: []),
    )


@pytest.mark.parametrize(
    "write_section",
    [
        *(
            pytest.param(partial(write, config={"persist_period_node_disk_usage": "0"}), id=name)
            for name, write in mk_docker.NODE_SECTIONS
        ),
        *(
            pytest.param(partial(write, container_id="c0ffee"), id=name)
            for name, write in (
                *mk_docker.CONTAINER_API_SECTIONS,
                *mk_docker.CONTAINER_API_SECTIONS_NO_AGENT,
            )
        ),
    ],
)
def test_every_section_of_the_agent_plugin_has_an_agent_section(
    write_section: Callable[[SimpleNamespace], None],
    agent_section_names: set[str],
    capsys: pytest.CaptureFixture[str],
) -> None:
    write_section(_fake_client())

    written = set(re.findall(r"^<<<(\w+):", capsys.readouterr().out, re.MULTILINE))

    assert written and written <= agent_section_names
