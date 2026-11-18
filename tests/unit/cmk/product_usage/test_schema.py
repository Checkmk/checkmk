#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import datetime
import json
import uuid

from cmk.product_usage.schema import CloudTrialPayload, ProductUsagePayload


def _product_usage_data() -> dict[str, object]:
    return {
        "id": str(uuid.uuid4()),
        "count_hosts": 10,
        "count_services": 20,
        "count_folders": 30,
        "edition": "community",
        "cmk_version": "1.2.3",
        "os": "Ubuntu 24.04.3 LTS",
        "users": {
            "humans": {
                "total": 1,
                "by_role": {"admin": 1},
                "by_connector_type": {"htpasswd": 1},
                "active": {"24h": 1, "7d": 1, "30d": 1},
            },
            "automation": {
                "total": 0,
                "by_role": {},
                "by_connector_type": {},
                "active": {"24h": 0, "7d": 0, "30d": 0},
            },
        },
        "timestamp": int(datetime.datetime.now(tz=datetime.UTC).timestamp()),
        "inventory": {"hosts_with_inventory": 4},
        "distributed_monitoring": {"is_remote_setup_site": False},
        "languages": {
            "default_language": "en",
            "users": {
                "active": {"count_per_language": {"de": 1}, "count_with_default_language": 0},
                "inactive": {"count_per_language": {}, "count_with_default_language": 0},
            },
        },
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


def test_product_usage_payload_dump_with_metadata_json() -> None:
    payload = _product_usage_data()

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


def test_product_usage_payload_without_the_optional_fields_has_them_as_null() -> None:
    """os, users and inventory are optional, a collector that fails sends its field as null"""
    payload = {
        key: value
        for key, value in _product_usage_data().items()
        if key not in {"os", "users", "inventory"}
    }

    data = json.loads(ProductUsagePayload.model_validate(payload).model_dump_with_metadata_json())

    assert (data["data"]["os"], data["data"]["users"], data["data"]["inventory"]) == (
        None,
        None,
        None,
    )


def test_cloud_trial_payload_carries_product_usage_data_and_null_trial_signals() -> None:
    payload = _product_usage_data()

    json_payload = CloudTrialPayload.model_validate(payload).model_dump_with_metadata_json()

    assert json.loads(json_payload) == {
        "metadata": {"version": "v1", "namespace": "checkmk", "name": "cloud_trial_analytics"},
        "data": {
            **payload,
            "site_created_at": None,
            "count_users": None,
            "sessions": None,
            "audit_log": None,
            "count_hosts_default_services_only": None,
        },
    }


def test_cloud_trial_payload_carries_audit_log_entries_per_actor_class() -> None:
    audit_log = {
        "interactive": {"entries": 12, "last_entry_at": 1767789000},
        "automation": {"entries": 0, "last_entry_at": None},
        "platform": {"entries": 41, "last_entry_at": 1767790000},
    }
    payload = {**_product_usage_data(), "audit_log": audit_log}

    json_payload = CloudTrialPayload.model_validate(payload).model_dump_with_metadata_json()

    assert json.loads(json_payload)["data"]["audit_log"] == audit_log


def test_cloud_trial_payload_carries_the_count_of_hosts_with_default_services_only() -> None:
    payload = {**_product_usage_data(), "count_hosts_default_services_only": 2}

    json_payload = CloudTrialPayload.model_validate(payload).model_dump_with_metadata_json()

    assert json.loads(json_payload)["data"]["count_hosts_default_services_only"] == 2


def test_cloud_trial_payload_carries_the_site_creation_time() -> None:
    payload = {**_product_usage_data(), "site_created_at": 1767700800}

    json_payload = CloudTrialPayload.model_validate(payload).model_dump_with_metadata_json()

    assert json.loads(json_payload)["data"]["site_created_at"] == 1767700800
