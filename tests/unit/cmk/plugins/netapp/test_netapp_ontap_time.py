#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import datetime
from zoneinfo import ZoneInfo

import time_machine
from polyfactory.factories.pydantic_factory import ModelFactory

from cmk.agent_based.v2 import Metric, Result, Service, State
from cmk.plugins.netapp.agent_based.netapp_ontap_time import (
    check_netapp_ontap_time,
    discover_netapp_ontap_time,
)
from cmk.plugins.netapp.models import NodeModel, Version


class NodeModelFactory(ModelFactory[NodeModel]):
    __model__ = NodeModel


class VersionFactory(ModelFactory[Version]):
    __model__ = Version


@time_machine.travel(
    datetime.datetime.fromisoformat("2026-01-01 08:00:00Z").replace(tzinfo=ZoneInfo("UTC")),
    tick=False,
)
def test_check_netapp_ontap_time() -> None:
    node_model = NodeModelFactory.build(
        date=datetime.datetime.fromisoformat("2026-01-01 08:00:40Z"),
    )
    section = {node_model.name: node_model}

    result = list(
        check_netapp_ontap_time(node_model.name, {"upper_levels": ("fixed", (30.0, 60.0))}, section)
    )

    assert result == [
        Result(state=State.OK, summary="Node time: 2026-01-01 08:00:40+00:00"),
        Result(
            state=State.WARN,
            summary="Absolute offset: 40 seconds (warn/crit at 30 seconds/1 minute 0 seconds)",
        ),
        Metric("time_offset", 40.0, levels=(30.0, 60.0)),
    ]


def test_discover_netapp_ontap_time() -> None:
    node_models = [
        NodeModelFactory.build(
            name="Node 1",
            date=datetime.datetime.fromisoformat("2026-01-01 08:00:40Z"),
        ),
        NodeModelFactory.build(
            name="Node 2",
            date=None,
        ),
    ]
    section = {node_model.name: node_model for node_model in node_models}

    result = list(discover_netapp_ontap_time(section))

    assert result == [Service(item="Node 1")]
