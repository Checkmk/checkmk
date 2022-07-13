#!/usr/bin/env python3
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
# mypy: disallow_untyped_defs
from typing import Optional

import pytest

from cmk.base.api.agent_based.checking_classes import ServiceLabel
from cmk.base.plugins.agent_based.agent_based_api.v1 import Metric, Result, State
from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import (
    CheckResult,
    DiscoveryResult,
    StringTable,
)
from cmk.base.plugins.agent_based.gcp_assets import parse_assets
from cmk.base.plugins.agent_based.gcp_sql import (
    check_gcp_sql_cpu,
    check_gcp_sql_disk,
    check_gcp_sql_memory,
    check_gcp_sql_network,
    check_gcp_sql_status,
    check_summary,
    discover,
    parse,
)
from cmk.base.plugins.agent_based.utils import gcp
from cmk.base.plugins.agent_based.utils.gcp import Section, SectionItem

from cmk.special_agents.agent_gcp import CLOUDSQL

from .gcp_test_util import DiscoverTester, generate_timeseries, Plugin

ASSET_TABLE = [
    [f'{{"project":"backup-255820", "config": ["{CLOUDSQL.name}"]}}'],
    [
        '{"name": "//cloudsql.googleapis.com/projects/tribe29-check-development/instances/checktest", "asset_type": "sqladmin.googleapis.com/Instance", "resource": {"version": "v1beta4", "discovery_document_uri": "https://www.googleapis.com/discovery/v1/apis/sqladmin/v1beta4/rest", "discovery_name": "DatabaseInstance", "parent": "//cloudresourcemanager.googleapis.com/projects/1074106860578", "data": {"serviceAccountEmailAddress": "p1074106860578-yhxe0q@gcp-sa-cloud-sql.iam.gserviceaccount.com", "instanceType": "CLOUDSQL_INSTANCE", "settings": {"dataDiskSizeGb": "20", "kind": "sql#settings", "storageAutoResize": true, "availabilityType": "ZONAL", "settingsVersion": "1", "backupConfiguration": {"kind": "sql#backupConfiguration", "backupRetentionSettings": {"retainedBackups": 7.0, "retentionUnit": "COUNT"}, "startTime": "01:00", "enabled": true, "transactionLogRetentionDays": 7.0, "binaryLogEnabled": false, "location": "us"}, "userLabels": {"reason": "check-development", "team": "dev"}, "activationPolicy": "ALWAYS", "replicationType": "SYNCHRONOUS", "pricingPlan": "PER_USE", "locationPreference": {"kind": "sql#locationPreference", "zone": "us-central1-f"}, "storageAutoResizeLimit": "0", "dataDiskType": "PD_HDD", "ipConfiguration": {"ipv4Enabled": true}, "tier": "db-custom-4-26624", "maintenanceWindow": {"hour": 0.0, "day": 0.0, "kind": "sql#maintenanceWindow"}}, "ipAddresses": [{"ipAddress": "34.121.172.190", "type": "PRIMARY"}], "selfLink": "https://sqladmin.googleapis.com/sql/v1beta4/projects/tribe29-check-development/instances/checktest", "region": "us-central1", "backendType": "SECOND_GEN", "databaseInstalledVersion": "MYSQL_5_7_36", "createTime": "2022-03-15T08:48:13.998Z", "connectionName": "tribe29-check-development:us-central1:checktest", "kind": "sql#instance", "serverCaCert": {"expirationTime": "2032-03-12T08:51:12.19Z", "kind": "sql#sslCert", "certSerialNumber": "0", "instance": "checktest", "sha1Fingerprint": "05e6c602375a78bd86ca46d9b80709d9bb43a0f2", "createTime": "2022-03-15T08:50:12.19Z", "commonName": "C=US,O=Google\\\\, Inc,CN=Google Cloud SQL Server CA,dnQualifier=8c6bc987-8655-4ff1-aebc-01d408409866"}, "databaseVersion": "MYSQL_5_7", "gceZone": "us-central1-f", "project": "tribe29-check-development", "state": "RUNNABLE", "name": "checktest"}, "location": "us-central1", "resource_url": ""}, "ancestors": ["projects/1074106860578", "folders/1022571519427", "organizations/668598212003"], "update_time": "2022-03-15T08:53:30.997492Z", "org_policy": []}'
    ],
]


class TestDiscover(DiscoverTester):
    @property
    def _assets(self) -> StringTable:
        return ASSET_TABLE

    @property
    def expected_services(self) -> set[str]:
        return {
            "checktest",
        }

    @property
    def expected_labels(self) -> set[ServiceLabel]:
        return {
            ServiceLabel("gcp/labels/reason", "check-development"),
            ServiceLabel("gcp/cloud_sql/name", "checktest"),
            ServiceLabel("gcp/cloud_sql/databaseVersion", "MYSQL_5_7"),
            ServiceLabel("gcp/labels/team", "dev"),
            ServiceLabel("gcp/cloud_sql/availability", "ZONAL"),
            ServiceLabel("gcp/location", "us-central1"),
            ServiceLabel("gcp/projectId", "backup-255820"),
        }

    def discover(self, assets: Optional[gcp.AssetSection]) -> DiscoveryResult:
        yield from discover(section_gcp_service_cloud_sql=None, section_gcp_assets=assets)


def test_discover_labels_labels_without_user_labels() -> None:
    asset_table = [
        [f'{{"project":"backup-255820", "config": ["{CLOUDSQL.name}"]}}'],
        [
            '{"name": "//cloudsql.googleapis.com/projects/tribe29-check-development/instances/checktest", "asset_type": "sqladmin.googleapis.com/Instance", "resource": {"version": "v1beta4", "discovery_document_uri": "https://www.googleapis.com/discovery/v1/apis/sqladmin/v1beta4/rest", "discovery_name": "DatabaseInstance", "parent": "//cloudresourcemanager.googleapis.com/projects/1074106860578", "data": {"serviceAccountEmailAddress": "p1074106860578-yhxe0q@gcp-sa-cloud-sql.iam.gserviceaccount.com", "instanceType": "CLOUDSQL_INSTANCE", "settings": {"dataDiskSizeGb": "20", "kind": "sql#settings", "storageAutoResize": true, "availabilityType": "ZONAL", "settingsVersion": "1", "backupConfiguration": {"kind": "sql#backupConfiguration", "backupRetentionSettings": {"retainedBackups": 7.0, "retentionUnit": "COUNT"}, "startTime": "01:00", "enabled": true, "transactionLogRetentionDays": 7.0, "binaryLogEnabled": false, "location": "us"}, "activationPolicy": "ALWAYS", "replicationType": "SYNCHRONOUS", "pricingPlan": "PER_USE", "locationPreference": {"kind": "sql#locationPreference", "zone": "us-central1-f"}, "storageAutoResizeLimit": "0", "dataDiskType": "PD_HDD", "ipConfiguration": {"ipv4Enabled": true}, "tier": "db-custom-4-26624", "maintenanceWindow": {"hour": 0.0, "day": 0.0, "kind": "sql#maintenanceWindow"}}, "ipAddresses": [{"ipAddress": "34.121.172.190", "type": "PRIMARY"}], "selfLink": "https://sqladmin.googleapis.com/sql/v1beta4/projects/tribe29-check-development/instances/checktest", "region": "us-central1", "backendType": "SECOND_GEN", "databaseInstalledVersion": "MYSQL_5_7_36", "createTime": "2022-03-15T08:48:13.998Z", "connectionName": "tribe29-check-development:us-central1:checktest", "kind": "sql#instance", "serverCaCert": {"expirationTime": "2032-03-12T08:51:12.19Z", "kind": "sql#sslCert", "certSerialNumber": "0", "instance": "checktest", "sha1Fingerprint": "05e6c602375a78bd86ca46d9b80709d9bb43a0f2", "createTime": "2022-03-15T08:50:12.19Z", "commonName": "C=US,O=Google\\\\, Inc,CN=Google Cloud SQL Server CA,dnQualifier=8c6bc987-8655-4ff1-aebc-01d408409866"}, "databaseVersion": "MYSQL_5_7", "gceZone": "us-central1-f", "project": "tribe29-check-development", "state": "RUNNABLE", "name": "checktest"}, "location": "us-central1", "resource_url": ""}, "ancestors": ["projects/1074106860578", "folders/1022571519427", "organizations/668598212003"], "update_time": "2022-03-15T08:53:30.997492Z", "org_policy": []}'
        ],
    ]
    asset_section = parse_assets(asset_table)
    servers = list(discover(section_gcp_service_cloud_sql=None, section_gcp_assets=asset_section))
    labels = servers[0].labels
    assert set(labels) == {
        ServiceLabel("gcp/cloud_sql/name", "checktest"),
        ServiceLabel("gcp/cloud_sql/databaseVersion", "MYSQL_5_7"),
        ServiceLabel("gcp/cloud_sql/availability", "ZONAL"),
        ServiceLabel("gcp/location", "us-central1"),
        ServiceLabel("gcp/projectId", "backup-255820"),
    }


# test the status check. This check does not follow the standard checks for gcp and has to be tested separetely.

ITEM = "checktest"
SECTION_TABLE = [
    [
        '{"metric": {"type": "cloudsql.googleapis.com/database/up", "labels": {}}, "resource": {"type": "cloudsql_database", "labels": {"project_id": "tribe29-check-development", "database_id": "tribe29-check-development:checktest"}}, "metric_kind": 1, "value_type": 2, "points": [{"interval": {"start_time": "2022-03-15T12:10:45.186892Z", "end_time": "2022-03-15T12:10:45.186892Z"}, "value": {"int64_value": "1"}}, {"interval": {"start_time": "2022-03-15T12:09:45.186892Z", "end_time": "2022-03-15T12:09:45.186892Z"}, "value": {"int64_value": "1"}}, {"interval": {"start_time": "2022-03-15T12:08:45.186892Z", "end_time": "2022-03-15T12:08:45.186892Z"}, "value": {"int64_value": "1"}}, {"interval": {"start_time": "2022-03-15T12:07:45.186892Z", "end_time": "2022-03-15T12:07:45.186892Z"}, "value": {"int64_value": "1"}}, {"interval": {"start_time": "2022-03-15T12:06:45.186892Z", "end_time": "2022-03-15T12:06:45.186892Z"}, "value": {"int64_value": "1"}}, {"interval": {"start_time": "2022-03-15T12:05:45.186892Z", "end_time": "2022-03-15T12:05:45.186892Z"}, "value": {"int64_value": "1"}}, {"interval": {"start_time": "2022-03-15T12:04:45.186892Z", "end_time": "2022-03-15T12:04:45.186892Z"}, "value": {"int64_value": "1"}}, {"interval": {"start_time": "2022-03-15T12:03:45.186892Z", "end_time": "2022-03-15T12:03:45.186892Z"}, "value": {"int64_value": "1"}}, {"interval": {"start_time": "2022-03-15T12:02:45.186892Z", "end_time": "2022-03-15T12:02:45.186892Z"}, "value": {"int64_value": "1"}}, {"interval": {"start_time": "2022-03-15T12:01:45.186892Z", "end_time": "2022-03-15T12:01:45.186892Z"}, "value": {"int64_value": "1"}}, {"interval": {"start_time": "2022-03-15T12:00:45.186892Z", "end_time": "2022-03-15T12:00:45.186892Z"}, "value": {"int64_value": "1"}}, {"interval": {"start_time": "2022-03-15T11:59:45.186892Z", "end_time": "2022-03-15T11:59:45.186892Z"}, "value": {"int64_value": "1"}}, {"interval": {"start_time": "2022-03-15T11:58:45.186892Z", "end_time": "2022-03-15T11:58:45.186892Z"}, "value": {"int64_value": "1"}}, {"interval": {"start_time": "2022-03-15T11:57:45.186892Z", "end_time": "2022-03-15T11:57:45.186892Z"},"value": {"int64_value": "1"}}, {"interval": {"start_time": "2022-03-15T11:56:45.186892Z", "end_time": "2022-03-15T11:56:45.186892Z"}, "value": {"int64_value": "1"}}, {"interval": {"start_time": "2022-03-15T11:55:45.186892Z", "end_time": "2022-03-15T11:55:45.186892Z"}, "value": {"int64_value": "1"}}, {"interval": {"start_time": "2022-03-15T11:54:45.186892Z", "end_time": "2022-03-15T11:54:45.186892Z"}, "value": {"int64_value": "1"}}, {"interval": {"start_time": "2022-03-15T11:53:45.186892Z", "end_time": "2022-03-15T11:53:45.186892Z"}, "value": {"int64_value": "1"}}], "unit": ""}'
    ],
    [
        '{"metric": {"type": "cloudsql.googleapis.com/database/state", "labels": {}}, "resource": {"type": "cloudsql_database", "labels": {"region": "us-central", "project_id": "tribe29-check-development", "database_id": "tribe29-check-development:checktest"}}, "metric_kind": 1, "value_type": 4, "points": [{"interval": {"start_time": "2022-03-15T12:10:45.186892Z", "end_time": "2022-03-15T12:10:45.186892Z"}, "value": {"string_value": "RUNNING"}}, {"interval": {"start_time": "2022-03-15T12:09:45.186892Z", "end_time": "2022-03-15T12:09:45.186892Z"}, "value": {"string_value": "RUNNING"}}, {"interval": {"start_time": "2022-03-15T12:08:45.186892Z", "end_time": "2022-03-15T12:08:45.186892Z"}, "value": {"string_value": "RUNNING"}}, {"interval": {"start_time": "2022-03-15T12:07:45.186892Z", "end_time": "2022-03-15T12:07:45.186892Z"}, "value": {"string_value": "RUNNING"}}, {"interval": {"start_time": "2022-03-15T12:06:45.186892Z", "end_time": "2022-03-15T12:06:45.186892Z"}, "value": {"string_value": "RUNNING"}}, {"interval": {"start_time": "2022-03-15T12:05:45.186892Z", "end_time": "2022-03-15T12:05:45.186892Z"}, "value": {"string_value": "RUNNING"}}, {"interval": {"start_time": "2022-03-15T12:04:45.186892Z", "end_time": "2022-03-15T12:04:45.186892Z"}, "value": {"string_value": "RUNNING"}}, {"interval": {"start_time": "2022-03-15T12:03:45.186892Z", "end_time": "2022-03-15T12:03:45.186892Z"}, "value": {"string_value": "RUNNING"}}, {"interval": {"start_time": "2022-03-15T12:02:45.186892Z", "end_time": "2022-03-15T12:02:45.186892Z"}, "value": {"string_value": "RUNNING"}}, {"interval": {"start_time": "2022-03-15T12:01:45.186892Z", "end_time": "2022-03-15T12:01:45.186892Z"}, "value": {"string_value": "RUNNING"}}, {"interval": {"start_time": "2022-03-15T12:00:45.186892Z", "end_time": "2022-03-15T12:00:45.186892Z"}, "value": {"string_value": "RUNNING"}}, {"interval": {"start_time": "2022-03-15T11:59:45.186892Z", "end_time": "2022-03-15T11:59:45.186892Z"}, "value": {"string_value": "RUNNING"}}, {"interval": {"start_time": "2022-03-15T11:58:45.186892Z", "end_time": "2022-03-15T11:58:45.186892Z"}, "value": {"string_value": "RUNNING"}}, {"interval": {"start_time": "2022-03-15T11:57:45.186892Z", "end_time": "2022-03-15T11:57:45.186892Z"}, "value": {"string_value": "RUNNING"}}, {"interval": {"start_time": "2022-03-15T11:56:45.186892Z", "end_time": "2022-03-15T11:56:45.186892Z"}, "value": {"string_value": "RUNNING"}}, {"interval": {"start_time": "2022-03-15T11:55:45.186892Z", "end_time": "2022-03-15T11:55:45.186892Z"}, "value": {"string_value": "RUNNING"}}, {"interval": {"start_time": "2022-03-15T11:54:45.186892Z", "end_time": "2022-03-15T11:54:45.186892Z"}, "value": {"string_value": "RUNNING"}}, {"interval": {"start_time": "2022-03-15T11:53:45.186892Z", "end_time": "2022-03-15T11:53:45.186892Z"}, "value": {"string_value": "RUNNING"}}], "unit": ""}'
    ],
]


@pytest.fixture(name="section")
def fixture_section() -> Section:
    return parse(SECTION_TABLE)


@pytest.mark.parametrize("state", (State.OK, State.WARN, State.CRIT))
def test_gcp_sql_status_params(section: gcp.Section, state: State) -> None:
    params = {"RUNNING": state}
    results = list(
        check_gcp_sql_status(
            item=ITEM,
            params=params,
            section_gcp_service_cloud_sql=section,
            section_gcp_assets=parse_assets(ASSET_TABLE),
        )
    )
    assert len(results) == 3
    result = results[-1]
    assert isinstance(result, Result)
    assert result == Result(state=state, summary="State: RUNNING")


def test_gcp_sql_status_metric(section: gcp.Section) -> None:
    params = {"RUNNING": State.UNKNOWN}
    results = list(
        check_gcp_sql_status(
            item=ITEM,
            params=params,
            section_gcp_service_cloud_sql=section,
            section_gcp_assets=parse_assets(ASSET_TABLE),
        )
    )
    assert len(results) == 3
    result = results[1]
    assert isinstance(result, Metric)
    assert result.value == 1.0


def test_gcp_sql_status_no_state_metric_in_available_metrics() -> None:
    params = {"RUNNING": State.UNKNOWN}
    results = list(
        check_gcp_sql_status(
            item=ITEM,
            params=params,
            section_gcp_service_cloud_sql={"checktest": SectionItem(rows=[])},
            section_gcp_assets=parse_assets(ASSET_TABLE),
        )
    )
    assert len(results) == 3
    result = results[-1]
    assert isinstance(result, Result)
    assert result == Result(state=State.UNKNOWN, summary="No data available")


def test_gcp_sql_status_no_agent_data_is_no_result() -> None:
    assert [] == list(
        check_gcp_sql_status(
            item=ITEM,
            params={},
            section_gcp_service_cloud_sql=None,
            section_gcp_assets=parse_assets(ASSET_TABLE),
        )
    )


def test_gcp_sql_status_no_results_if_item_not_found(section: gcp.Section) -> None:
    params = {k: None for k in ["requests"]}
    results = check_gcp_sql_status(
        item="I do not exist",
        params=params,
        section_gcp_service_cloud_sql=section,
        section_gcp_assets=parse_assets(ASSET_TABLE),
    )
    assert len(list(results)) == 0


# Test the standard checks

PLUGINS = [
    pytest.param(
        Plugin(
            function=check_gcp_sql_cpu,
            metrics=["util"],
            results=[Result(state=State.OK, summary="CPU: 42.00%")],
        ),
        id="cpu",
    ),
    pytest.param(
        Plugin(
            function=check_gcp_sql_memory,
            metrics=["memory_util"],
            results=[Result(state=State.OK, summary="Memory: 42.00%")],
        ),
        id="memory",
    ),
    pytest.param(
        Plugin(
            function=check_gcp_sql_network,
            metrics=["net_data_sent", "net_data_recv"],
            results=[
                Result(state=State.OK, summary="In: 3.36 Bit/s"),
                Result(state=State.OK, summary="Out: 3.36 Bit/s"),
            ],
        ),
        id="network",
    ),
    pytest.param(
        Plugin(
            function=check_gcp_sql_disk,
            metrics=["fs_used_percent", "disk_write_ios", "disk_read_ios"],
            results=[
                Result(state=State.OK, summary="Disk utilization: 42.00%"),
                Result(state=State.OK, summary="Read operations: 0.42"),
                Result(state=State.OK, summary="Write operations: 0.42"),
            ],
        ),
        id="disk",
    ),
]


def generate_results(plugin: Plugin) -> CheckResult:
    item = "item"
    asset_table = [
        [f'{{"project":"backup-255820", "config": ["{CLOUDSQL.name}"]}}'],
        [
            f'{{"name": "//cloudsql.googleapis.com/projects/tribe29-check-development/instances/checktest", "asset_type": "sqladmin.googleapis.com/Instance", "resource": {{"version": "v1beta4", "discovery_document_uri": "https://www.googleapis.com/discovery/v1/apis/sqladmin/v1beta4/rest", "discovery_name": "DatabaseInstance", "parent": "//cloudresourcemanager.googleapis.com/projects/1074106860578", "data": {{"serviceAccountEmailAddress": "p1074106860578-yhxe0q@gcp-sa-cloud-sql.iam.gserviceaccount.com", "instanceType": "CLOUDSQL_INSTANCE", "settings": {{"dataDiskSizeGb": "20", "kind": "sql#settings", "storageAutoResize": true, "availabilityType": "ZONAL", "settingsVersion": "1", "backupConfiguration": {{"kind": "sql#backupConfiguration", "backupRetentionSettings": {{"retainedBackups": 7.0, "retentionUnit": "COUNT"}}, "startTime": "01:00", "enabled": true, "transactionLogRetentionDays": 7.0, "binaryLogEnabled": false, "location": "us"}}, "userLabels": {{"reason": "check-development", "team": "dev"}}, "activationPolicy": "ALWAYS", "replicationType": "SYNCHRONOUS", "pricingPlan": "PER_USE", "locationPreference": {{"kind": "sql#locationPreference", "zone": "us-central1-f"}}, "storageAutoResizeLimit": "0", "dataDiskType": "PD_HDD", "ipConfiguration": {{"ipv4Enabled": true}}, "tier": "db-custom-4-26624", "maintenanceWindow": {{"hour": 0.0, "day": 0.0, "kind": "sql#maintenanceWindow"}}}}, "ipAddresses": [{{"ipAddress": "34.121.172.190", "type": "PRIMARY"}}], "selfLink": "https://sqladmin.googleapis.com/sql/v1beta4/projects/tribe29-check-development/instances/checktest", "region": "us-central1", "backendType": "SECOND_GEN", "databaseInstalledVersion": "MYSQL_5_7_36", "createTime": "2022-03-15T08:48:13.998Z", "connectionName": "tribe29-check-development:us-central1:checktest", "kind": "sql#instance", "serverCaCert": {{"expirationTime": "2032-03-12T08:51:12.19Z", "kind": "sql#sslCert", "certSerialNumber": "0", "instance": "checktest", "sha1Fingerprint": "05e6c602375a78bd86ca46d9b80709d9bb43a0f2", "createTime": "2022-03-15T08:50:12.19Z", "commonName": "C=US,O=Google\\\\, Inc,CN=Google Cloud SQL Server CA,dnQualifier=8c6bc987-8655-4ff1-aebc-01d408409866"}}, "databaseVersion": "MYSQL_5_7", "gceZone": "us-central1-f", "project": "tribe29-check-development", "state": "RUNNABLE", "name": "{item}"}}, "location": "us-central1", "resource_url": ""}}, "ancestors": ["projects/1074106860578", "folders/1022571519427", "organizations/668598212003"], "update_time": "2022-03-15T08:53:30.997492Z", "org_policy": []}}'
        ],
    ]
    section = parse(generate_timeseries(item, 0.42, CLOUDSQL))
    yield from plugin.function(
        item=item,
        params={k: None for k in plugin.metrics},
        section_gcp_service_cloud_sql=section,
        section_gcp_assets=parse_assets(asset_table),
    )


@pytest.mark.parametrize("plugin", PLUGINS)
def test_yield_results_as_specified(plugin: Plugin) -> None:
    results = {r for r in generate_results(plugin) if isinstance(r, Result)}
    assert results == set(plugin.results)


@pytest.mark.parametrize("plugin", PLUGINS)
def test_yield_metrics_as_specified(plugin: Plugin) -> None:
    results = {r.name for r in generate_results(plugin) if isinstance(r, Metric)}
    assert results == set(plugin.metrics)


def test_check_summary() -> None:
    assets = parse_assets(ASSET_TABLE)
    results = set(check_summary(section=assets))
    assert results == {Result(state=State.OK, summary="1 Server", details="Found 1 server")}
