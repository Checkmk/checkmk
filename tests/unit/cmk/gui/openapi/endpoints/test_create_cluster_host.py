#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from pydantic import TypeAdapter

from cmk.ccc.hostaddress import HostName
from cmk.gui.openapi.api_endpoints.host_config.create_cluster_host import CreateClusterHostModel


def test_nodes_validator(sample_host: str) -> None:
    result = TypeAdapter(  # astrein: disable=pydantic-type-adapter
        CreateClusterHostModel
    ).validate_python(
        {
            "host_name": "new_cluster_host",
            "folder": "",
            "nodes": [sample_host],
        }
    )
    assert result.nodes == [HostName(sample_host)]
