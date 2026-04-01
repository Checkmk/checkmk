#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json

from cmk.plugins.kube import prometheus_api


def test_parse_raw_response_tolerates_thanos_fields() -> None:
    """
    Prometheus (specifically Thanos) may add fields like 'warnings' or 'analysis'
    to the data object; verify we parse them.
    """
    raw = json.dumps(
        {
            "status": "success",
            "data": {
                "resultType": "vector",
                "result": [],
                "warnings": ["w1"],
                "analysis": {"k": "v"},
            },
        }
    )
    result = prometheus_api.parse_raw_response(raw)
    assert isinstance(result, prometheus_api.ResponseSuccess)
    assert isinstance(result.data, prometheus_api.Vector)
    assert list(result.data.warnings) == ["w1"]
    assert result.data.analysis == {"k": "v"}
