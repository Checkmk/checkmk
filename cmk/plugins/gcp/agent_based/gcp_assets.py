#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
# mypy: disallow_untyped_defs
import json
from collections import defaultdict

from cmk.agent_based.v2 import AgentSection, StringTable
from cmk.plugins.gcp.lib.constants import Extractors
from cmk.plugins.gcp.lib.gcp import (
    AssetSection,
    AssetType,
    AssetTypeSection,
    Config,
    GCPAsset,
)


def parse_assets(string_table: StringTable) -> AssetSection:
    info = json.loads(string_table[0][0])
    config = Config(info["config"])

    assets = [GCPAsset.deserialize(row[0]) for row in string_table[1:]]
    sorted_assets: dict[AssetType, list[GCPAsset]] = defaultdict(list)
    for a in assets:
        sorted_assets[a.asset_type].append(a)

    typed_assets: dict[AssetType, AssetTypeSection] = {}
    for asset_type, assets in sorted_assets.items():
        if asset_type not in Extractors:
            continue
        extract = Extractors[asset_type]
        typed_assets[asset_type] = {extract(a): a for a in assets}

    return AssetSection(config, typed_assets)


agent_section_gcp_assets = AgentSection(name="gcp_assets", parse_function=parse_assets)
