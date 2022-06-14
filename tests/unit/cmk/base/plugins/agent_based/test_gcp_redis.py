#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import abc
from dataclasses import dataclass
from typing import Any, Callable, Mapping, Optional, Sequence, Union

import pytest
from hypothesis import given
from hypothesis import strategies as st

from cmk.base.api.agent_based.checking_classes import CheckFunction, IgnoreResults, ServiceLabel
from cmk.base.plugins.agent_based.agent_based_api.v1 import Metric, Result, State
from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import DiscoveryResult, StringTable
from cmk.base.plugins.agent_based.gcp_redis import (
    check_cpu_util,
    check_hitratio,
    check_memory_util,
    discover,
    parse,
)
from cmk.base.plugins.agent_based.utils import gcp

from .gcp_test_util import DiscoverTester, ParsingTester

SECTION_TABLE = [
    [
        '{"metric": {"type": "redis.googleapis.com/stats/cpu_utilization", "labels": {}}, "resource": {"type": "redis_instance", "labels": {"project_id": "tribe29-check-development", "instance_id": "projects/tribe29-check-development/locations/us-central1/instances/red"}}, "metric_kind": 1, "value_type": 3, "points": [{"interval": {"start_time": "2022-03-28T13:12:56.015707Z", "end_time": "2022-03-28T13:12:56.015707Z"}, "value": {"double_value": 0.15167707163365662}}, {"interval": {"start_time": "2022-03-28T13:11:56.015707Z", "end_time": "2022-03-28T13:11:56.015707Z"}, "value": {"double_value": 0.1499983802172551}}, {"interval": {"start_time": "2022-03-28T13:10:56.015707Z", "end_time": "2022-03-28T13:10:56.015707Z"}, "value": {"double_value": 0.15832454283443553}}, {"interval": {"start_time": "2022-03-28T13:09:56.015707Z", "end_time": "2022-03-28T13:09:56.015707Z"}, "value": {"double_value": 0.14167698246944482}}, {"interval": {"start_time": "2022-03-28T13:08:56.015707Z", "end_time": "2022-03-28T13:08:56.015707Z"}, "value": {"double_value": 0.15664704199009805}}, {"interval": {"start_time": "2022-03-28T13:07:56.015707Z", "end_time": "2022-03-28T13:07:56.015707Z"}, "value": {"double_value": 0.14000039712246348}}, {"interval": {"start_time": "2022-03-28T13:06:56.015707Z", "end_time": "2022-03-28T13:06:56.015707Z"}, "value": {"double_value": 0.14167590417747178}}, {"interval": {"start_time": "2022-03-28T13:05:56.015707Z", "end_time": "2022-03-28T13:05:56.015707Z"}, "value": {"double_value": 0.15000036805128758}}, {"interval": {"start_time": "2022-03-28T13:04:56.015707Z", "end_time": "2022-03-28T13:04:56.015707Z"}, "value": {"double_value": 0.14167532604880861}}, {"interval": {"start_time": "2022-03-28T13:03:56.015707Z", "end_time": "2022-03-28T13:03:56.015707Z"}, "value": {"double_value": 0.1483240590400321}}, {"interval": {"start_time": "2022-03-28T13:02:56.015707Z", "end_time": "2022-03-28T13:02:56.015707Z"}, "value": {"double_value": 0.14832587823343601}}, {"interval": {"start_time": "2022-03-28T13:01:56.015707Z", "end_time": "2022-03-28T13:01:56.015707Z"}, "value": {"double_value": 0.13334920623569602}}, {"interval": {"start_time": "2022-03-28T13:00:56.015707Z", "end_time": "2022-03-28T13:00:56.015707Z"}, "value": {"double_value": 0.1483249073135191}}, {"interval": {"start_time": "2022-03-28T12:59:56.015707Z","end_time": "2022-03-28T12:59:56.015707Z"}, "value": {"double_value": 0.1416756330935165}}, {"interval": {"start_time": "2022-03-28T12:58:56.015707Z", "end_time": "2022-03-28T12:58:56.015707Z"}, "value": {"double_value": 0.1583239359033577}}, {"interval": {"start_time": "2022-03-28T12:57:56.015707Z", "end_time": "2022-03-28T12:57:56.015707Z"}, "value": {"double_value": 0.1483265854485083}}, {"interval": {"start_time": "2022-03-28T12:56:56.015707Z", "end_time": "2022-03-28T12:56:56.015707Z"}, "value": {"double_value": 0.14334988111616198}}, {"interval": {"start_time": "2022-03-28T12:55:56.015707Z", "end_time": "2022-03-28T12:55:56.015707Z"}, "value": {"double_value": 0.1700026708617699}}], "unit": ""}'
    ],
    [
        '{"metric": {"type": "redis.googleapis.com/stats/memory/usage_ratio", "labels": {}}, "resource": {"type": "redis_instance", "labels": {"instance_id": "projects/tribe29-check-development/locations/europe-west6/instances/red", "project_id": "tribe29-check-development"}}, "metric_kind": 1, "value_type": 3, "points": [{"interval": {"start_time": "2022-03-28T13:12:56.015707Z", "end_time": "2022-03-28T13:12:56.015707Z"}, "value": {"double_value": 0.0034887492656707764}}, {"interval": {"start_time": "2022-03-28T13:11:56.015707Z", "end_time": "2022-03-28T13:11:56.015707Z"}, "value": {"double_value": 0.0034887492656707764}}, {"interval": {"start_time": "2022-03-28T13:10:56.015707Z", "end_time": "2022-03-28T13:10:56.015707Z"}, "value": {"double_value": 0.0034887492656707764}}, {"interval": {"start_time": "2022-03-28T13:09:56.015707Z", "end_time": "2022-03-28T13:09:56.015707Z"}, "value": {"double_value": 0.0034887492656707764}}, {"interval": {"start_time": "2022-03-28T13:08:56.015707Z", "end_time": "2022-03-28T13:08:56.015707Z"}, "value": {"double_value": 0.0034887492656707764}}, {"interval": {"start_time": "2022-03-28T13:07:56.015707Z", "end_time": "2022-03-28T13:07:56.015707Z"}, "value": {"double_value": 0.0034887492656707764}}, {"interval": {"start_time": "2022-03-28T13:06:56.015707Z", "end_time": "2022-03-28T13:06:56.015707Z"}, "value": {"double_value": 0.0034887492656707764}}, {"interval": {"start_time": "2022-03-28T13:05:56.015707Z", "end_time": "2022-03-28T13:05:56.015707Z"}, "value": {"double_value": 0.0034887492656707764}}, {"interval": {"start_time": "2022-03-28T13:04:56.015707Z", "end_time": "2022-03-28T13:04:56.015707Z"}, "value": {"double_value": 0.0034887492656707764}}, {"interval": {"start_time": "2022-03-28T13:03:56.015707Z", "end_time": "2022-03-28T13:03:56.015707Z"}, "value": {"double_value": 0.0034887492656707764}}, {"interval": {"start_time": "2022-03-28T13:02:56.015707Z", "end_time": "2022-03-28T13:02:56.015707Z"}, "value": {"double_value": 0.0034887492656707764}}, {"interval": {"start_time": "2022-03-28T13:01:56.015707Z", "end_time": "2022-03-28T13:01:56.015707Z"}, "value": {"double_value": 0.0034887492656707764}}, {"interval": {"start_time": "2022-03-28T13:00:56.015707Z", "end_time": "2022-03-28T13:00:56.015707Z"}, "value": {"double_value": 0.0034887492656707764}}, {"interval": {"start_time": "2022-03-28T12:59:56.015707Z", "end_time": "2022-03-28T12:59:56.015707Z"}, "value": {"double_value": 0.0034887492656707764}}, {"interval": {"start_time": "2022-03-28T12:58:56.015707Z", "end_time": "2022-03-28T12:58:56.015707Z"}, "value": {"double_value": 0.0034887492656707764}}, {"interval": {"start_time": "2022-03-28T12:57:56.015707Z", "end_time": "2022-03-28T12:57:56.015707Z"}, "value": {"double_value": 0.0034887492656707764}}, {"interval": {"start_time": "2022-03-28T12:56:56.015707Z", "end_time": "2022-03-28T12:56:56.015707Z"}, "value": {"double_value": 0.0034887492656707764}}, {"interval": {"start_time": "2022-03-28T12:55:56.015707Z", "end_time": "2022-03-28T12:55:56.015707Z"}, "value": {"double_value": 0.0034887492656707764}}], "unit": ""}'
    ],
    [
        '{"metric": {"type": "redis.googleapis.com/stats/memory/usage_ratio", "labels": {}}, "resource": {"type": "redis_instance", "labels": {"project_id": "tribe29-check-development", "instance_id": "projects/tribe29-check-development/locations/us-central1/instances/red"}}, "metric_kind": 1, "value_type": 3, "points": [{"interval": {"start_time": "2022-03-28T13:12:56.015707Z", "end_time": "2022-03-28T13:12:56.015707Z"}, "value":{"double_value": 0.003488503396511078}}, {"interval": {"start_time": "2022-03-28T13:11:56.015707Z", "end_time": "2022-03-28T13:11:56.015707Z"}, "value": {"double_value": 0.003488503396511078}}, {"interval": {"start_time": "2022-03-28T13:10:56.015707Z", "end_time": "2022-03-28T13:10:56.015707Z"}, "value": {"double_value": 0.003488503396511078}}, {"interval": {"start_time": "2022-03-28T13:09:56.015707Z", "end_time": "2022-03-28T13:09:56.015707Z"}, "value": {"double_value": 0.003488503396511078}}, {"interval": {"start_time": "2022-03-28T13:08:56.015707Z", "end_time": "2022-03-28T13:08:56.015707Z"}, "value": {"double_value": 0.003488503396511078}}, {"interval": {"start_time": "2022-03-28T13:07:56.015707Z", "end_time": "2022-03-28T13:07:56.015707Z"}, "value": {"double_value": 0.003488503396511078}}, {"interval": {"start_time": "2022-03-28T13:06:56.015707Z", "end_time": "2022-03-28T13:06:56.015707Z"}, "value": {"double_value": 0.003488503396511078}}, {"interval": {"start_time": "2022-03-28T13:05:56.015707Z", "end_time": "2022-03-28T13:05:56.015707Z"}, "value": {"double_value": 0.003488503396511078}}, {"interval": {"start_time": "2022-03-28T13:04:56.015707Z", "end_time": "2022-03-28T13:04:56.015707Z"}, "value": {"double_value": 0.003488503396511078}}, {"interval":{"start_time": "2022-03-28T13:03:56.015707Z", "end_time": "2022-03-28T13:03:56.015707Z"}, "value": {"double_value": 0.003488503396511078}}, {"interval": {"start_time": "2022-03-28T13:02:56.015707Z", "end_time": "2022-03-28T13:02:56.015707Z"}, "value": {"double_value": 0.003488503396511078}}, {"interval": {"start_time": "2022-03-28T13:01:56.015707Z", "end_time": "2022-03-28T13:01:56.015707Z"}, "value": {"double_value": 0.003488503396511078}}, {"interval": {"start_time": "2022-03-28T13:00:56.015707Z", "end_time": "2022-03-28T13:00:56.015707Z"}, "value": {"double_value": 0.003488503396511078}}, {"interval": {"start_time": "2022-03-28T12:59:56.015707Z", "end_time": "2022-03-28T12:59:56.015707Z"}, "value": {"double_value": 0.003488503396511078}}, {"interval": {"start_time": "2022-03-28T12:58:56.015707Z", "end_time": "2022-03-28T12:58:56.015707Z"}, "value": {"double_value": 0.003488503396511078}}, {"interval": {"start_time": "2022-03-28T12:57:56.015707Z", "end_time": "2022-03-28T12:57:56.015707Z"}, "value": {"double_value": 0.003488503396511078}}, {"interval": {"start_time": "2022-03-28T12:56:56.015707Z", "end_time": "2022-03-28T12:56:56.015707Z"}, "value": {"double_value": 0.003488503396511078}}, {"interval": {"start_time": "2022-03-28T12:55:56.015707Z", "end_time": "2022-03-28T12:55:56.015707Z"}, "value": {"double_value": 0.003488503396511078}}], "unit": ""}'
    ],
    [
        '{"metric": {"type": "redis.googleapis.com/stats/memory/system_memory_usage_ratio", "labels": {}}, "resource": {"type": "redis_instance", "labels": {"instance_id": "projects/tribe29-check-development/locations/europe-west6/instances/red", "project_id": "tribe29-check-development"}}, "metric_kind": 1, "value_type": 3, "points": [{"interval": {"start_time": "2022-03-28T13:12:56.015707Z", "end_time": "2022-03-28T13:12:56.015707Z"}, "value": {"double_value": 0.004995731710715344}}, {"interval": {"start_time": "2022-03-28T13:11:56.015707Z", "end_time": "2022-03-28T13:11:56.015707Z"}, "value": {"double_value": 0.004937675560677978}}, {"interval": {"start_time": "2022-03-28T13:10:56.015707Z", "end_time": "2022-03-28T13:10:56.015707Z"}, "value": {"double_value": 0.005050885053250841}}, {"interval": {"start_time": "2022-03-28T13:09:56.015707Z", "end_time": "2022-03-28T13:09:56.015707Z"}, "value": {"double_value": 0.004902841870655558}}, {"interval": {"start_time": "2022-03-28T13:08:56.015707Z", "end_time": "2022-03-28T13:08:56.015707Z"}, "value": {"double_value": 0.005050885053250841}}, {"interval": {"start_time": "2022-03-28T13:07:56.015707Z", "end_time": "2022-03-28T13:07:56.015707Z"}, "value": {"double_value": 0.004928967138172373}}, {"interval": {"start_time": "2022-03-28T13:06:56.015707Z", "end_time": "2022-03-28T13:06:56.015707Z"}, "value": {"double_value": 0.004998634518217212}}, {"interval": {"start_time": "2022-03-28T13:05:56.015707Z", "end_time": "2022-03-28T13:05:56.015707Z"}, "value": {"double_value": 0.004931869945674241}}, {"interval": {"start_time": "2022-03-28T13:04:56.015707Z", "end_time": "2022-03-28T13:04:56.015707Z"}, "value": {"double_value": 0.005007342940722817}}, {"interval": {"start_time": "2022-03-28T13:03:56.015707Z", "end_time": "2022-03-28T13:03:56.015707Z"}, "value": {"double_value": 0.004905744678157426}}, {"interval": {"start_time": "2022-03-28T13:02:56.015707Z", "end_time": "2022-03-28T13:02:56.015707Z"}, "value": {"double_value": 0.005010245748224685}}, {"interval": {"start_time": "2022-03-28T13:01:56.015707Z", "end_time": "2022-03-28T13:01:56.015707Z"}, "value": {"double_value": 0.00493477275317611}}, {"interval": {"start_time": "2022-03-28T13:00:56.015707Z", "end_time": "2022-03-28T13:00:56.015707Z"}, "value": {"double_value": 0.0048767166031387435}}, {"interval": {"start_time": "2022-03-28T12:59:56.015707Z", "end_time": "2022-03-28T12:59:56.015707Z"}, "value": {"double_value": 0.0049667036356966605}}, {"interval": {"start_time": "2022-03-28T12:58:56.015707Z", "end_time": "2022-03-28T12:58:56.015707Z"}, "value": {"double_value": 0.004894133448149953}}, {"interval": {"start_time": "2022-03-28T12:57:56.015707Z", "end_time": "2022-03-28T12:57:56.015707Z"}, "value": {"double_value": 0.004943481175681714}}, {"interval": {"start_time": "2022-03-28T12:56:56.015707Z", "end_time": "2022-03-28T12:56:56.015707Z"}, "value": {"double_value": 0.004957995213191056}}, {"interval": {"start_time": "2022-03-28T12:55:56.015707Z", "end_time": "2022-03-28T12:55:56.015707Z"}, "value": {"double_value": 0.0050450794382471045}}], "unit": ""}'
    ],
    [
        '{"metric": {"type": "redis.googleapis.com/stats/memory/system_memory_usage_ratio", "labels": {}}, "resource": {"type": "redis_instance", "labels": {"instance_id": "projects/tribe29-check-development/locations/us-central1/instances/red", "project_id": "tribe29-check-development"}}, "metric_kind": 1, "value_type": 3, "points": [{"interval": {"start_time": "2022-03-28T13:12:56.015707Z", "end_time": "2022-03-28T13:12:56.015707Z"}, "value": {"double_value": 0.005088621550775129}}, {"interval": {"start_time": "2022-03-28T13:11:56.015707Z", "end_time": "2022-03-28T13:11:56.015707Z"}, "value": {"double_value": 0.005135066470805022}}, {"interval": {"start_time": "2022-03-28T13:10:56.015707Z", "end_time": "2022-03-28T13:10:56.015707Z"}, "value": {"double_value": 0.005187317005838651}}, {"interval": {"start_time": "2022-03-28T13:09:56.015707Z", "end_time": "2022-03-28T13:09:56.015707Z"}, "value": {"double_value": 0.005222150695861071}}, {"interval": {"start_time": "2022-03-28T13:08:56.015707Z", "end_time": "2022-03-28T13:08:56.015707Z"}, "value": {"double_value": 0.005097329973280734}}, {"interval": {"start_time": "2022-03-28T13:07:56.015707Z", "end_time": "2022-03-28T13:07:56.015707Z"}, "value": {"double_value": 0.0051815113908349145}}, {"interval": {"start_time": "2022-03-28T13:06:56.015707Z", "end_time": "2022-03-28T13:06:56.015707Z"}, "value": {"double_value": 0.005210539465853598}}, {"interval": {"start_time": "2022-03-28T13:05:56.015707Z", "end_time": "2022-03-28T13:05:56.015707Z"}, "value": {"double_value": 0.005062496283258315}}, {"interval": {"start_time": "2022-03-28T13:04:56.015707Z", "end_time": "2022-03-28T13:04:56.015707Z"}, "value": {"double_value": 0.005129260855801286}}, {"interval": {"start_time": "2022-03-28T13:03:56.015707Z", "end_time": "2022-03-28T13:03:56.015707Z"}, "value": {"double_value": 0.0052047338508498615}}, {"interval": {"start_time": "2022-03-28T13:02:56.015707Z", "end_time": "2022-03-28T13:02:56.015707Z"}, "value": {"double_value": 0.005082815935771393}}, {"interval": {"start_time": "2022-03-28T13:01:56.015707Z", "end_time": "2022-03-28T13:01:56.015707Z"}, "value": {"double_value": 0.00517280296832931}}, {"interval": {"start_time": "2022-03-28T13:00:56.015707Z", "end_time": "2022-03-28T13:00:56.015707Z"}, "value": {"double_value": 0.005059593475756447}}, {"interval": {"start_time": "2022-03-28T12:59:56.015707Z", "end_time": "2022-03-28T12:59:56.015707Z"}, "value": {"double_value": 0.0050915243582769975}}, {"interval": {"start_time": "2022-03-28T12:58:56.015707Z", "end_time": "2022-03-28T12:58:56.015707Z"}, "value": {"double_value": 0.005175705775831178}}, {"interval": {"start_time": "2022-03-28T12:57:56.015707Z", "end_time": "2022-03-28T12:57:56.015707Z"}, "value": {"double_value": 0.005068301898262051}}, {"interval": {"start_time": "2022-03-28T12:56:56.015707Z", "end_time": "2022-03-28T12:56:56.015707Z"}, "value": {"double_value": 0.005135066470805022}}, {"interval": {"start_time": "2022-03-28T12:55:56.015707Z", "end_time": "2022-03-28T12:55:56.015707Z"}, "value": {"double_value": 0.005175705775831178}}], "unit": ""}'
    ],
    [
        '{"metric": {"type": "redis.googleapis.com/stats/cache_hit_ratio", "labels": {}}, "resource": {"type": "redis_instance", "labels": {"instance_id": "projects/tribe29-check-development/locations/us-central1/instances/blue", "project_id": "tribe29-check-development"}}, "metric_kind": 1, "value_type": 3, "points": [{"interval": {"start_time": "2022-04-01T10:45:29.989061Z", "end_time": "2022-04-01T10:45:29.989061Z"}, "value": {"double_value": 0.3333333333333333}}, {"interval": {"start_time": "2022-04-01T10:44:29.989061Z", "end_time": "2022-04-01T10:44:29.989061Z"}, "value": {"double_value": 0.3333333333333333}}], "unit": ""}'
    ],
]

ASSET_TABLE = [
    ['{"project":"backup-255820"}'],
    [
        '{"name": "//redis.googleapis.com/projects/tribe29-check-development/locations/europe-west6/instances/red", "asset_type": "redis.googleapis.com/Instance", "resource": {"version": "v1", "discovery_document_uri":"https://redis.googleapis.com/$discovery/rest", "discovery_name": "Instance", "parent": "//cloudresourcemanager.googleapis.com/projects/1074106860578", "data": {"persistenceIamIdentity": "serviceAccount:136208174824-compute@developer.gserviceaccount.com", "currentLocationId": "europe-west6-b", "reservedIpRange": "10.33.170.64/29", "authorizedNetwork": "projects/tribe29-check-development/global/networks/default", "displayName": "red2", "host": "10.33.170.67", "port": 6379.0, "locationId": "europe-west6-b", "state": "READY", "redisVersion": "REDIS_6_X", "transitEncryptionMode": "DISABLED", "createTime": "2022-03-28T11:04:35.40073338Z", "persistenceConfig": {"persistenceMode": "DISABLED"}, "tier": "BASIC", "name": "projects/tribe29-check-development/locations/europe-west6/instances/red", "memorySizeGb": 1.0, "connectMode": "DIRECT_PEERING", "nodes": [{"id": "node-0", "zone": "europe-west6-b"}], "readReplicasMode": "READ_REPLICAS_DISABLED"}, "location": "europe-west6", "resource_url": ""}, "ancestors": ["projects/1074106860578", "folders/1022571519427", "organizations/668598212003"], "update_time": "2022-03-28T11:08:19.425454Z", "org_policy": []}'
    ],
]


class TestDiscover(DiscoverTester):
    @property
    def _assets(self) -> StringTable:
        return ASSET_TABLE

    @property
    def expected_services(self) -> set[str]:
        return {
            "projects/tribe29-check-development/locations/europe-west6/instances/red",
        }

    @property
    def expected_labels(self) -> set[ServiceLabel]:
        return {
            ServiceLabel("gcp/projectId", "backup-255820"),
            ServiceLabel("gcp/redis/tier", "BASIC"),
            ServiceLabel("gcp/redis/host", "10.33.170.67"),
            ServiceLabel("gcp/redis/version", "REDIS_6_X"),
            ServiceLabel("gcp/redis/port", "6379"),
            ServiceLabel("gcp/redis/nr_nodes", "1"),
            ServiceLabel("gcp/redis/displayname", "red2"),
            ServiceLabel("gcp/redis/connectMode", "DIRECT_PEERING"),
            ServiceLabel("gcp/location", "europe-west6-b"),
        }

    def discover(self, assets: Optional[gcp.AssetSection]) -> DiscoveryResult:
        yield from discover(section_gcp_service_redis=None, section_gcp_assets=assets)


class TestParsing(ParsingTester):
    def parse(self, string_table):
        return parse(string_table)

    @property
    def section_table(self) -> StringTable:
        return SECTION_TABLE


@pytest.fixture(name="redis_section")
def fixture_section():
    return parse(SECTION_TABLE)


@dataclass(frozen=True)
class Plugin:
    metrics: Sequence[str]
    function: Callable


PLUGINS = [
    Plugin(function=check_cpu_util, metrics=["util"]),
    Plugin(function=check_memory_util, metrics=["memory_util", "system_memory_util"]),
]
ITEM = "projects/tribe29-check-development/locations/europe-west6/instances/red"


@pytest.fixture(params=PLUGINS, name="checkplugin")
def fixture_checkplugin(request):
    return request.param


@pytest.fixture(name="results")
def fixture_results(checkplugin, redis_section):
    params = {k: None for k in checkplugin.metrics}
    results = list(
        checkplugin.function(
            item=ITEM,
            params=params,
            section_gcp_service_redis=redis_section,
            section_gcp_assets=None,
        )
    )
    return results, checkplugin


def test_no_redis_section_yields_no_metric_data(checkplugin) -> None:
    params = {k: None for k in checkplugin.metrics}
    results = list(
        checkplugin.function(
            item=ITEM, params=params, section_gcp_service_redis=None, section_gcp_assets=None
        )
    )
    assert len(results) == 0


def test_yield_metrics_as_specified(results) -> None:
    results, checkplugin = results
    res = {r.name: r for r in results if isinstance(r, Metric)}
    assert len(res) == len(checkplugin.metrics)
    assert set(res.keys()) == set(checkplugin.metrics)


def test_yield_results_as_specified(results) -> None:
    results, checkplugin = results
    res = [r for r in results if isinstance(r, Result)]
    assert len(res) == len(checkplugin.metrics)
    for r in res:
        assert r.state == State.OK


class TestDefaultMetricValues:
    # requests does not contain example data
    def test_zero_default_if_metric_does_not_exist(self, redis_section) -> None:
        params = {k: None for k in ["util"]}
        results = (
            el
            for el in check_cpu_util(
                item=ITEM,
                params=params,
                section_gcp_service_redis=redis_section,
                section_gcp_assets=None,
            )
            if isinstance(el, Metric)
        )
        for result in results:
            assert result.value == 0.0

    # objects does contain example data
    def test_non_zero_if_metric_exist(self, redis_section) -> None:
        params = {k: None for k in ["memory_util", "system_memory_util"]}
        results = (
            el
            for el in check_memory_util(
                item=ITEM,
                params=params,
                section_gcp_service_redis=redis_section,
                section_gcp_assets=None,
            )
            if isinstance(el, Metric)
        )
        for result in results:
            assert result.value != 0.0

    def test_zero_default_if_item_does_not_exist(self, redis_section, checkplugin: Plugin) -> None:
        params = {k: None for k in checkplugin.metrics}
        results = (
            el
            for el in checkplugin.function(
                item="no I do not exist",
                params=params,
                section_gcp_service_redis=redis_section,
                section_gcp_assets=None,
            )
            if isinstance(el, Metric)
        )
        for result in results:
            assert result.value == 0.0


class ABCTestRedisChecks(abc.ABC):
    ITEM = "redis1"
    METRIC_NAME = "hitratio"

    @abc.abstractmethod
    def _section_kwargs(self, section: Any) -> dict[str, Any]:
        raise NotImplementedError

    @abc.abstractmethod
    def _section(self, hitratio: float, item: str) -> Any:
        raise NotImplementedError

    def _parametrize(self, hitratio: float, params: Mapping[str, Any]) -> Mapping[str, Any]:
        kwargs: dict[str, Any] = {}
        kwargs["item"] = self.ITEM
        kwargs["params"] = params
        for k, v in self._section_kwargs(self._section(hitratio, self.ITEM)).items():
            kwargs[k] = v
        return kwargs

    def run(
        self, hitratio: float, params: Mapping[str, Any], check: CheckFunction
    ) -> Sequence[Union[IgnoreResults, Result, Metric]]:
        kwargs = self._parametrize(hitratio, params=params)
        return list(check(**kwargs))

    def test_expected_number_of_results_and_metrics(self, check: CheckFunction) -> None:
        params = {"levels_upper_hitratio": None, "levels_lower_hitratio": None}
        results = self.run(50, params, check)
        assert len(results) == 2

    @pytest.mark.parametrize(
        "state, hitratio, summary_ext",
        [
            pytest.param(State.OK, 0.5, "", id="ok"),
            pytest.param(State.WARN, 0.85, " (warn/crit at 80.00%/90.00%)", id="warning upper"),
            pytest.param(State.CRIT, 0.95, " (warn/crit at 80.00%/90.00%)", id="critical upper"),
            pytest.param(State.WARN, 0.35, " (warn/crit below 40.00%/30.00%)", id="warning lower"),
            pytest.param(State.CRIT, 0.25, " (warn/crit below 40.00%/30.00%)", id="critial lower"),
        ],
    )
    def test_yield_levels(
        self, state: State, hitratio: float, check: CheckFunction, summary_ext: str
    ):
        levels_upper = (80, 90)
        levels_lower = (40, 30)
        params = {"levels_upper_hitratio": levels_upper, "levels_lower_hitratio": levels_lower}
        results = [el for el in self.run(hitratio, params, check) if isinstance(el, Result)]
        summary = f"Hitratio: {(hitratio*100):.2f}%{summary_ext}"
        assert results[0] == Result(state=state, summary=summary)

    @given(hitratio=st.floats(min_value=0, max_value=1))
    def test_yield_no_levels(self, hitratio: float, check: CheckFunction) -> None:
        params = {"levels_upper_hitratio": None, "levels_lower_hitratio": None}
        results = [el for el in self.run(hitratio, params, check) if isinstance(el, Result)]
        assert results[0].state == State.OK

    @given(hitratio=st.floats(min_value=0, max_value=1))
    def test_metric(self, hitratio: float, check: CheckFunction) -> None:
        params = {"levels_upper_hitratio": None, "levels_lower_hitratio": None}
        metrics = [el for el in self.run(hitratio, params, check) if isinstance(el, Metric)]
        assert metrics[0] == Metric(self.METRIC_NAME, hitratio * 100)


class TestRedisGCP(ABCTestRedisChecks):
    @staticmethod
    @pytest.fixture(scope="class")
    def check() -> CheckFunction:
        return check_hitratio

    def _section_kwargs(self, section: gcp.Section) -> dict[str, Optional[gcp.Section]]:
        return {
            "section_gcp_service_redis": section,
            "section_gcp_assets": None,
        }

    def _section(self, hitratio: float, item: str) -> gcp.Section:
        data = f'{{"metric": {{"type": "redis.googleapis.com/stats/cache_hit_ratio", "labels": {{}}}}, "resource": {{"type": "redis_instance", "labels": {{"instance_id": "projects/tribe29-check-development/locations/us-central1/instances/blue", "project_id": "tribe29-check-development"}}}}, "metric_kind": 1, "value_type": 3, "points": [{{"interval": {{"start_time": "2022-04-01T10:45:29.989061Z", "end_time": "2022-04-01T10:45:29.989061Z"}}, "value": {{"double_value": {hitratio}}}}}], "unit": ""}}'
        row = gcp.GCPResult.deserialize(data)
        section_item = gcp.SectionItem(rows=[row])
        return {item: section_item}
