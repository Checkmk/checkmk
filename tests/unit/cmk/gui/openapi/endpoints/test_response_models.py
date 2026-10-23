#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from pydantic import TypeAdapter

from cmk.gui.config import Config
from cmk.gui.logged_in import LoggedInNobody
from cmk.gui.openapi.api_endpoints.host_config.models.response_models import HostExtensionsModel
from tests.testlib.unit.gui.validation_context import make_validation_context


def test_cluster_nodes_validator(sample_host: str) -> None:
    result = TypeAdapter(  # astrein: disable=pydantic-type-adapter
        HostExtensionsModel
    ).validate_python(
        {
            "folder": "",
            "attributes": {"dynamic_fields": {}},
            "is_cluster": True,
            "is_offline": False,
            "cluster_nodes": [sample_host],
        },
        context=make_validation_context(Config(), LoggedInNobody()),
    )
    assert result.cluster_nodes is not None
    assert list(result.cluster_nodes) == [sample_host]
