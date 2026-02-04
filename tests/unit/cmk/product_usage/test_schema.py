#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import datetime
import json
import uuid

from cmk.product_usage.schema import ProductUsagePayload


def test_product_usage_payload_dump_with_metadata_json() -> None:
    payload = {
        "id": str(uuid.uuid4()),
        "count_hosts": 10,
        "count_services": 20,
        "count_folders": 30,
        "edition": "community",
        "cmk_version": "1.2.3",
        "timestamp": int(datetime.datetime.now(tz=datetime.UTC).timestamp()),
        "grafana": {
            "is_used": True,
            "version": "2.3.4",
            "is_grafana_cloud": False,
        },
        "checks": {
            "df": {
                "count": 1,
                "count_hosts": 2,
                "count_disabled": 3,
            }
        },
    }

    json_payload = ProductUsagePayload.model_validate(payload).model_dump_with_metadata_json()

    actual_payload = json.loads(json_payload)
    assert "metadata" in actual_payload
    assert actual_payload["metadata"] == {
        "version": "v1",
        "namespace": "checkmk",
        "name": "product_usage_analytics",
    }
    assert "data" in actual_payload
    assert actual_payload["data"] == payload
