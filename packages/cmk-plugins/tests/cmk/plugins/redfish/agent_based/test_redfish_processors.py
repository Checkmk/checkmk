#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json

import pytest

from cmk.agent_based.v2 import Result, State
from cmk.plugins.redfish.agent_based.redfish_processors import check_redfish_processors
from cmk.plugins.redfish.lib import parse_redfish_multiple


@pytest.mark.xfail(strict=True, raises=ValueError, reason="Crash group 4986")
def test_check_redfish_processors_model_with_line_break() -> None:
    section = parse_redfish_multiple(
        [
            [
                json.dumps(
                    {
                        "@odata.id": "/redfish/v1/Systems/1/Processors/GPU1",
                        "@odata.type": "#Processor.v1_20_0.Processor",
                        "Id": "GPU1",
                        "Manufacturer": "NVIDIA",
                        "Model": "900-2101\nG40-000",
                        "Name": "NVIDIA H200 NVL",
                        "ProcessorType": "GPU",
                        "Status": {"Health": "OK", "State": "Enabled"},
                    }
                )
            ]
        ]
    )
    assert next(iter(check_redfish_processors("GPU1", section))) == Result(
        state=State.OK, summary="Type: GPU, Model: 900-2101 G40-000"
    )
