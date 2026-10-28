#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from collections.abc import Mapping
from dataclasses import dataclass

from cmk.agent_based.v2 import (
    AgentSection,
    Attributes,
    InventoryPlugin,
    InventoryResult,
    StringTable,
    TableRow,
)


@dataclass(frozen=True)
class AwsMetadata:
    attributes: Mapping[str, str]
    tags: Mapping[str, str]


def parse_aws_metadata(string_table: StringTable) -> AwsMetadata:
    # The agent writes the data of an account host once for every region.
    attributes: dict[str, str] = {}
    tags: dict[str, str] = {}
    for (line,) in string_table:
        metadata = json.loads(line)
        tags.update(metadata.pop("tags", {}))
        attributes.update(metadata)
    return AwsMetadata(attributes, tags)


agent_section_aws_v2_metadata = AgentSection(
    name="aws_v2_metadata",
    parse_function=parse_aws_metadata,
)


def inventory_aws_metadata(section: AwsMetadata) -> InventoryResult:
    path = ["software", "applications", "aws"]
    yield Attributes(path=[*path, "metadata"], inventory_attributes=section.attributes)
    for key, value in section.tags.items():
        yield TableRow(
            path=[*path, "tags"],
            key_columns={"name": key},
            inventory_columns={"value": value},
        )


inventory_plugin_aws_v2_metadata = InventoryPlugin(
    name="aws_v2_metadata",
    inventory_function=inventory_aws_metadata,
)
