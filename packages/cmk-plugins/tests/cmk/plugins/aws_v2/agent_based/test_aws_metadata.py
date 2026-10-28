#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json

from cmk.agent_based.v2 import Attributes, TableRow
from cmk.plugins.aws_v2.agent_based.aws_metadata import inventory_aws_metadata, parse_aws_metadata


def test_resource_metadata_and_tags_are_inventoried() -> None:
    metadata = {
        "cloud_provider": "AWS",
        "account_id": "123",
        "entity": "resource",
        "service": "s3",
        "name": "bucket",
        "tags": {"team": "a:b"},
    }

    section = parse_aws_metadata([[json.dumps(metadata)]])

    assert list(inventory_aws_metadata(section)) == [
        Attributes(
            path=["software", "applications", "aws", "metadata"],
            inventory_attributes={
                "cloud_provider": "AWS",
                "account_id": "123",
                "entity": "resource",
                "service": "s3",
                "name": "bucket",
            },
        ),
        TableRow(
            path=["software", "applications", "aws", "tags"],
            key_columns={"name": "team"},
            inventory_columns={"value": "a:b"},
        ),
    ]


def test_metadata_of_every_region_is_merged() -> None:
    line = '{"cloud_provider": "AWS", "account_id": "123", "entity": "account"}'

    section = parse_aws_metadata([[line], [line]])

    assert list(inventory_aws_metadata(section)) == [
        Attributes(
            path=["software", "applications", "aws", "metadata"],
            inventory_attributes={
                "cloud_provider": "AWS",
                "account_id": "123",
                "entity": "account",
            },
        ),
    ]
