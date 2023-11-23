#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
# mypy: disallow_untyped_defs
from cmk.plugins.gcp.agent_based.gcp_assets import parse_assets
from cmk.plugins.gcp.lib.gcp import AssetSection, Config

ASSET_TABLE = [
    ['{"project":"backup-255820", "config":[]}'],
    [
        '{"name": "//bigquery.googleapis.com/projects/checkmk-cost-analytics/datasets/all_billing_data", "asset_type": "UNKOWN", "resource": {"version": "v2", "discovery_document_uri": "https://www.googleapis.com/discovery/v1/apis/bigquery/v2/rest", "discovery_name": "Dataset", "parent": "//cloudresourcemanager.googleapis.com/projects/611779980525", "data": {"datasetReference": {"datasetId": "all_billing_data", "projectId": "checkmk-cost-analytics"}, "kind": "bigquery#dataset", "creationTime": "1657705707220", "id": "checkmk-cost-analytics:all_billing_data", "lastModifiedTime": "1657705837322", "location": "europe-north1", "defaultTableExpirationMs": "0"}, "location": "europe-north1", "resource_url": ""}, "ancestors": ["projects/611779980525", "organizations/668598212003"], "update_time": "2022-07-13T09:50:38.463856Z", "org_policy": []}'
    ],
]


def test_skip_parsing_unkown_asset_type() -> None:
    section = parse_assets(ASSET_TABLE)
    assert section == AssetSection(config=Config(services=[]), _assets={})
