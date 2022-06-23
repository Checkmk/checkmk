#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Optional

import pytest
from pytest_mock import MockerFixture

from cmk.utils.type_defs.pluginname import CheckPluginName

from cmk.base.api.agent_based.checking_classes import ServiceLabel
from cmk.base.plugin_contexts import current_host, current_service
from cmk.base.plugins.agent_based.agent_based_api.v1 import Metric, Result, State
from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import (
    CheckResult,
    DiscoveryResult,
    StringTable,
)
from cmk.base.plugins.agent_based.gcp_assets import parse_assets
from cmk.base.plugins.agent_based.gcp_function import (
    check_gcp_function_execution,
    check_gcp_function_instances,
    check_gcp_function_network,
    discover,
    parse_gcp_function,
)
from cmk.base.plugins.agent_based.utils import gcp

from cmk.special_agents.agent_gcp import FUNCTIONS

from .gcp_test_util import DiscoverTester, generate_timeseries, ParsingTester, Plugin

ASSET_TABLE = [
    ['{"project":"backup-255820", "config": ["cloud_functions"]}'],
    [
        '{"name": "//cloudfunctions.googleapis.com/projects/backup-255820/locations/us-central1/functions/function-1", "asset_type": "cloudfunctions.googleapis.com/CloudFunction", "resource": {"version": "v1", "discovery_document_uri": "https://cloudfunctions.googleapis.com/$discovery/rest", "discovery_name": "CloudFunction", "parent": "//cloudresourcemanager.googleapis.com/projects/360989076580", "data": {"dockerRegistry": "CONTAINER_REGISTRY", "timeout": "60s", "updateTime": "2022-02-07T20:37:20.735Z", "serviceAccountEmail": "backup-255820@appspot.gserviceaccount.com", "name": "projects/backup-255820/locations/us-central1/functions/function-1", "buildId": "bbbb3f80-54e4-4460-b10d-d7b912cd6b57", "status": "ACTIVE", "availableMemoryMb": 256.0, "entryPoint": "hello_world", "httpsTrigger": {"url": "https://us-central1-backup-255820.cloudfunctions.net/function-1", "securityLevel": "SECURE_ALWAYS"}, "versionId": "1", "ingressSettings": "ALLOW_ALL", "runtime": "python37", "buildName": "projects/360989076580/locations/us-central1/builds/bbbb3f80-54e4-4460-b10d-d7b912cd6b57", "maxInstances": 3000.0, "labels": {"deployment-tool": "console-cloud"}, "sourceUploadUrl": "https://storage.googleapis.com/gcf-upload-us-central1-bab35793-a665-4418-b5e0-d1e9495d23d7/a9c82954-5087-4655-9656-04c7cdb2410e.zip?GoogleAccessId=service-360989076580@gcf-admin-robot.iam.gserviceaccount.com&Expires=1644267947&Signature=z4UoLtkcqj3Y3Vo3cMgL0IZIJowhg5NrSsyS2O2wuLT%2BkjXRFxj%2BFWyeovp3YWG%2Fw3TbB1nS1Aq3uyIRjtlB4aVI%2FgfLxDeHwuoH7gx2EiULukSxT8YztuqNQmdlw67mWG%2FUbcxVpHSFrv%2FPqX6QJLd9IpqnAvs9wu5IiBriWJnImBqAQNJF9Lw%2FEz4QutK7fDUWNwiRSjnvEEByRTPLu14d%2FZxSG3wbikDdCmGibHFEMCd6KKjl%2FxLPkLH68SQczKwePwtx9nrRaaXEBwKNt4S0Omk8tjfaJSljbVrRmsfENpDUpvMUoGXa3SCXYujQOXPccWZLCLTPumf6vcSszw%3D%3D"}, "location": "us-central1", "resource_url": ""}, "ancestors": ["projects/360989076580"], "update_time": "2022-02-08T00:40:50.926703Z", "org_policy": []}'
    ],
    [
        '{"name": "//cloudfunctions.googleapis.com/projects/backup-255820/locations/us-central1/functions/function-2", "asset_type": "cloudfunctions.googleapis.com/CloudFunction", "resource": {"version": "v1", "discovery_document_uri": "https://cloudfunctions.googleapis.com/$discovery/rest", "discovery_name": "CloudFunction", "parent": "//cloudresourcemanager.googleapis.com/projects/360989076580", "data": {"name": "projects/backup-255820/locations/us-central1/functions/function-2", "labels": {"deployment-tool": "console-cloud"}, "dockerRegistry": "CONTAINER_REGISTRY", "runtime": "python39", "versionId": "1", "maxInstances": 3000.0, "ingressSettings": "ALLOW_ALL", "updateTime": "2022-02-10T13:14:39.705Z", "status": "ACTIVE", "sourceUploadUrl": "https://storage.googleapis.com/gcf-upload-us-central1-bab35793-a665-4418-b5e0-d1e9495d23d7/51f5c053-d0cc-4632-b383-7ac46c26e24a.zip?GoogleAccessId=service-360989076580@gcf-admin-robot.iam.gserviceaccount.com&Expires=1644500617&Signature=nsWqYK%2BECAUav5QiakO%2B%2Fosk0hu9nzgrFWuzsOj6Ldz5KfnV67Gx9lDLQdk1DUSEqOYgXndzOZYPTuLEOu0aRX8nbbbehZG%2BK1xmx0S189nHLkHbaS12ysxSHN%2Bj4j2XLJ3d4PP5AgANuHTtmgRo2BC8FKWHNJb%2F6OGXwKofJPJqHL7IS%2BNbAWwK6y9BYnFcvthpMmegB99%2F9dptIEpgttn80AqGforM6ICOvd0QUeSFR0vnJiUOlUooX39iE9zdoPogPVNOJPbFesqO0%2FZJ5r1obV3nGfb3j1K6c929lCA96s4r8FiVK7r6YiCQcSCf%2FAeC56BHPZbB3FhM%2Bj0a0Q%3D%3D", "timeout": "60s", "httpsTrigger": {"securityLevel": "SECURE_ALWAYS", "url": "https://us-central1-backup-255820.cloudfunctions.net/function-2"}, "entryPoint": "hello_world", "availableMemoryMb": 256.0, "buildName": "projects/360989076580/locations/us-central1/builds/8bf4f2d0-e2f8-4121-b4d2-69fd972c5b4b", "serviceAccountEmail": "backup-255820@appspot.gserviceaccount.com", "buildId": "8bf4f2d0-e2f8-4121-b4d2-69fd972c5b4b"}, "location": "us-central1", "resource_url": ""}, "ancestors": ["projects/360989076580"], "update_time": "2022-02-10T14:16:00.779110Z", "org_policy": []}'
    ],
    [
        '{"name": "//cloudfunctions.googleapis.com/projects/backup-255820/locations/us-central1/functions/function-3", "asset_type": "cloudfunctions.googleapis.com/CloudFunction", "resource": {"version": "v1", "discovery_document_uri": "https://cloudfunctions.googleapis.com/$discovery/rest", "discovery_name": "CloudFunction", "parent": "//cloudresourcemanager.googleapis.com/projects/360989076580", "data": {"httpsTrigger": {"securityLevel": "SECURE_ALWAYS", "url": "https://us-central1-backup-255820.cloudfunctions.net/function-3"}, "ingressSettings": "ALLOW_ALL", "availableMemoryMb": 256.0, "labels": {"deployment-tool": "console-cloud"}, "timeout": "60s", "name": "projects/backup-255820/locations/us-central1/functions/function-3", "dockerRegistry": "CONTAINER_REGISTRY", "maxInstances": 3000.0, "runtime": "go116", "serviceAccountEmail": "backup-255820@appspot.gserviceaccount.com", "versionId": "1", "buildId": "20cf97bd-bbfd-4577-926e-2ebc288bafd4", "buildName": "projects/360989076580/locations/us-central1/builds/20cf97bd-bbfd-4577-926e-2ebc288bafd4", "entryPoint": "HelloWorld", "sourceUploadUrl": "https://storage.googleapis.com/gcf-upload-us-central1-bab35793-a665-4418-b5e0-d1e9495d23d7/eaf63803-d12c-43cb-84c5-9b3ad74ec5a4.zip?GoogleAccessId=service-360989076580@gcf-admin-robot.iam.gserviceaccount.com&Expires=1645179719&Signature=oytdprPfv7ajmG9wfawf%2F0XArGBJQ%2BlQccksB60QvslHX2FowmbB%2BiMzcr1Kd2Yo665OIGe5x%2BQOlOFWrj8DBzw58WwJDukEVicT9XtnAUl0MFZnchmlUbwDIFslzOm3YpkPU3BacVjkQm145cxh3tT6CkT0i5hA7l6nAXqyNxrPxQ1C8GngfARsLvgRitDvWA4376aE95k%2BLoDgauYCO5n%2Fi4iJGGrp9U9x483Izj5dd6bOLrmt2UtnoTNEPRj53pSTWkFYWjm28aGSfDiryvpa1qNKwh%2Fs2fk9FAAi1G7kVLm6UV51yPUwQfZ%2FmMOSyzEmMU7gKvXiQEYbySr7KQ%3D%3D", "updateTime": "2022-02-18T09:53:07.805Z", "status": "ACTIVE"}, "location": "us-central1", "resource_url": ""}, "ancestors": ["projects/360989076580"], "update_time": "2022-02-18T12:37:37.181555Z", "org_policy": []}'
    ],
]


class TestDiscover(DiscoverTester):
    @property
    def _assets(self) -> StringTable:
        return ASSET_TABLE

    @property
    def expected_services(self) -> set[str]:
        return {"function-1", "function-2", "function-3"}

    @property
    def expected_labels(self) -> set[ServiceLabel]:
        return {
            ServiceLabel("gcp/location", "us-central1"),
            ServiceLabel("gcp/function/name", "function-1"),
            ServiceLabel("gcp/projectId", "backup-255820"),
        }

    def discover(self, assets: Optional[gcp.AssetSection]) -> DiscoveryResult:
        yield from discover(section_gcp_service_cloud_functions=None, section_gcp_assets=assets)


class TestParsing(ParsingTester):
    def parse(self, string_table):
        return parse_gcp_function(string_table)

    @property
    def section_table(self) -> StringTable:
        return generate_timeseries("Mario", 42.0, FUNCTIONS)


def test_zero_default_if_metric_does_not_exist() -> None:
    item = "some_function"
    metrics = (
        el
        for el in check_gcp_function_network(
            item=item,
            params={"net_data_sent": None},
            section_gcp_service_cloud_functions={item: gcp.SectionItem(rows=[])},
            section_gcp_assets=None,
        )
        if isinstance(el, Metric)
    )
    for metric in metrics:
        assert metric.value == 0.0


def test_zero_default_if_item_does_not_exist() -> None:
    metrics = (
        el
        for el in check_gcp_function_network(
            item="does_not_exist",
            params={"net_data_sent": None},
            section_gcp_service_cloud_functions={},
            section_gcp_assets=None,
        )
        if isinstance(el, Metric)
    )
    for metric in metrics:
        assert metric.value == 0.0


def test_no_function_section_yields_no_metric_data() -> None:
    results = list(
        check_gcp_function_network(
            item="no_data_anyway",
            params={"net_data_sent": None},
            section_gcp_service_cloud_functions=None,
            section_gcp_assets=None,
        )
    )
    assert len(results) == 0


def test_warn_settings_in_check() -> None:
    item = "item"
    section = parse_gcp_function(generate_timeseries(item, 42.0, FUNCTIONS))
    results = [
        r
        for r in check_gcp_function_network(
            item=item,
            params={"net_data_sent": (20, 50)},
            section_gcp_service_cloud_functions=section,
            section_gcp_assets=None,
        )
        if isinstance(r, Result)
    ]
    for r in results:
        assert r.state == State.WARN


def test_crit_settings_in_check() -> None:
    item = "item"
    section = parse_gcp_function(generate_timeseries(item, 42.0, FUNCTIONS))
    results = [
        r
        for r in check_gcp_function_network(
            item=item,
            params={"net_data_sent": (20, 40)},
            section_gcp_service_cloud_functions=section,
            section_gcp_assets=None,
        )
        if isinstance(r, Result)
    ]
    for r in results:
        assert r.state == State.CRIT


def test_missing_item() -> None:
    item = "item"
    section = parse_gcp_function(generate_timeseries(item, 42.0, FUNCTIONS))
    results = list(
        check_gcp_function_network(
            item=item,
            params={"net_data_sent": (20, 40)},
            section_gcp_service_cloud_functions=section,
            section_gcp_assets=parse_assets(
                [
                    ['{"project":"backup-255820", "config": ["cloud_functions"]}'],
                    [
                        '{"name": "//cloudfunctions.googleapis.com/projects/backup-255820/locations/us-central1/functions/function-1", "asset_type": "cloudfunctions.googleapis.com/CloudFunction", "resource": {"version": "v1", "discovery_document_uri": "https://cloudfunctions.googleapis.com/$discovery/rest", "discovery_name": "CloudFunction", "parent": "//cloudresourcemanager.googleapis.com/projects/360989076580", "data": {"dockerRegistry": "CONTAINER_REGISTRY", "timeout": "60s", "updateTime": "2022-02-07T20:37:20.735Z", "serviceAccountEmail": "backup-255820@appspot.gserviceaccount.com", "name": "projects/backup-255820/locations/us-central1/functions/function-1", "buildId": "bbbb3f80-54e4-4460-b10d-d7b912cd6b57", "status": "ACTIVE", "availableMemoryMb": 256.0, "entryPoint": "hello_world", "httpsTrigger": {"url": "https://us-central1-backup-255820.cloudfunctions.net/function-1", "securityLevel": "SECURE_ALWAYS"}, "versionId": "1", "ingressSettings": "ALLOW_ALL", "runtime": "python37", "buildName": "projects/360989076580/locations/us-central1/builds/bbbb3f80-54e4-4460-b10d-d7b912cd6b57", "maxInstances": 3000.0, "labels": {"deployment-tool": "console-cloud"}, "sourceUploadUrl": "https://storage.googleapis.com/gcf-upload-us-central1-bab35793-a665-4418-b5e0-d1e9495d23d7/a9c82954-5087-4655-9656-04c7cdb2410e.zip?GoogleAccessId=service-360989076580@gcf-admin-robot.iam.gserviceaccount.com&Expires=1644267947&Signature=z4UoLtkcqj3Y3Vo3cMgL0IZIJowhg5NrSsyS2O2wuLT%2BkjXRFxj%2BFWyeovp3YWG%2Fw3TbB1nS1Aq3uyIRjtlB4aVI%2FgfLxDeHwuoH7gx2EiULukSxT8YztuqNQmdlw67mWG%2FUbcxVpHSFrv%2FPqX6QJLd9IpqnAvs9wu5IiBriWJnImBqAQNJF9Lw%2FEz4QutK7fDUWNwiRSjnvEEByRTPLu14d%2FZxSG3wbikDdCmGibHFEMCd6KKjl%2FxLPkLH68SQczKwePwtx9nrRaaXEBwKNt4S0Omk8tjfaJSljbVrRmsfENpDUpvMUoGXa3SCXYujQOXPccWZLCLTPumf6vcSszw%3D%3D"}, "location": "us-central1", "resource_url": ""}, "ancestors": ["projects/360989076580"], "update_time": "2022-02-08T00:40:50.926703Z", "org_policy": []}'
                    ],
                ]
            ),
        )
    )
    assert len(results) == 0


def test_predictive_checks(mocker: MockerFixture) -> None:
    item = "item"
    section = parse_gcp_function(generate_timeseries(item, 42.0, FUNCTIONS))
    mocker.patch(
        "cmk.base.check_api._prediction.get_levels", return_value=(None, (20, 50, None, None))
    )
    with current_host("unittest"), current_service(CheckPluginName("test"), item):
        results = list(
            check_gcp_function_network(
                item=item,
                params={"net_data_sent": {"levels_upper": (0, 1), "horizon": 1, "period": "day"}},
                section_gcp_service_cloud_functions=section,
                section_gcp_assets=None,
            )
        )
    res = [r for r in results if isinstance(r, Result)]
    for r in res:
        assert r.state == State.WARN


PLUGINS = [
    pytest.param(
        Plugin(
            function=check_gcp_function_network,
            metrics=["net_data_sent"],
            results=[Result(state=State.OK, summary="Out: 336 Bit/s")],
        ),
        id="network",
    ),
    pytest.param(
        Plugin(
            function=check_gcp_function_execution,
            metrics=[
                "faas_execution_count",
                "aws_lambda_memory_size_absolute",
                "faas_execution_times",
            ],
            results=[
                Result(state=State.OK, summary="Executions count: 42.0"),
                Result(state=State.OK, summary="Memory: 42 B"),
                Result(state=State.OK, summary="Execution times: 42 nanoseconds"),
            ],
        ),
        id="execution",
    ),
    pytest.param(
        Plugin(
            function=check_gcp_function_instances,
            metrics=["faas_total_instance_count", "faas_active_instance_count"],
            results=[
                Result(state=State.OK, summary="Instances: 42.0"),
                Result(state=State.OK, summary="Active instances: 42.0"),
            ],
        ),
        id="instances",
    ),
]


def generate_results(plugin: Plugin) -> CheckResult:
    item = "item"
    asset_table = [
        ['{"project":"backup-255820", "config": ["cloud_functions"]}'],
        [
            f'{{"name": "//cloudfunctions.googleapis.com/projects/backup-255820/locations/us-central1/functions/function-1", "asset_type": "cloudfunctions.googleapis.com/CloudFunction", "resource": {{"version": "v1", "discovery_document_uri": "https://cloudfunctions.googleapis.com/$discovery/rest", "discovery_name": "CloudFunction", "parent": "//cloudresourcemanager.googleapis.com/projects/360989076580", "data": {{"dockerRegistry": "CONTAINER_REGISTRY", "timeout": "60s", "updateTime": "2022-02-07T20:37:20.735Z", "serviceAccountEmail": "backup-255820@appspot.gserviceaccount.com", "name": "projects/backup-255820/locations/us-central1/functions/{item}", "buildId": "bbbb3f80-54e4-4460-b10d-d7b912cd6b57", "status": "ACTIVE", "availableMemoryMb": 256.0, "entryPoint": "hello_world", "httpsTrigger": {{"url": "https://us-central1-backup-255820.cloudfunctions.net/function-1", "securityLevel": "SECURE_ALWAYS"}}, "versionId": "1", "ingressSettings": "ALLOW_ALL", "runtime": "python37", "buildName": "projects/360989076580/locations/us-central1/builds/bbbb3f80-54e4-4460-b10d-d7b912cd6b57", "maxInstances": 3000.0, "labels": {{"deployment-tool": "console-cloud"}}, "sourceUploadUrl": "https://storage.googleapis.com/gcf-upload-us-central1-bab35793-a665-4418-b5e0-d1e9495d23d7/a9c82954-5087-4655-9656-04c7cdb2410e.zip?GoogleAccessId=service-360989076580@gcf-admin-robot.iam.gserviceaccount.com&Expires=1644267947&Signature=z4UoLtkcqj3Y3Vo3cMgL0IZIJowhg5NrSsyS2O2wuLT%2BkjXRFxj%2BFWyeovp3YWG%2Fw3TbB1nS1Aq3uyIRjtlB4aVI%2FgfLxDeHwuoH7gx2EiULukSxT8YztuqNQmdlw67mWG%2FUbcxVpHSFrv%2FPqX6QJLd9IpqnAvs9wu5IiBriWJnImBqAQNJF9Lw%2FEz4QutK7fDUWNwiRSjnvEEByRTPLu14d%2FZxSG3wbikDdCmGibHFEMCd6KKjl%2FxLPkLH68SQczKwePwtx9nrRaaXEBwKNt4S0Omk8tjfaJSljbVrRmsfENpDUpvMUoGXa3SCXYujQOXPccWZLCLTPumf6vcSszw%3D%3D"}}, "location": "us-central1", "resource_url": ""}}, "ancestors": ["projects/360989076580"], "update_time": "2022-02-08T00:40:50.926703Z", "org_policy": []}}'
        ],
    ]
    section = parse_gcp_function(generate_timeseries(item, 42.0, FUNCTIONS))
    yield from plugin.function(
        item=item,
        params={k: None for k in plugin.metrics},
        section_gcp_service_cloud_functions=section,
        section_gcp_assets=parse_assets(asset_table),
    )


@pytest.mark.parametrize("plugin", PLUGINS)
def test_yield_results_as_specified(plugin) -> None:
    results = {r for r in generate_results(plugin) if isinstance(r, Result)}
    assert results == set(plugin.results)


@pytest.mark.parametrize("plugin", PLUGINS)
def test_yield_metrics_as_specified(plugin) -> None:
    results = {r.name for r in generate_results(plugin) if isinstance(r, Metric)}
    assert results == set(plugin.metrics)
