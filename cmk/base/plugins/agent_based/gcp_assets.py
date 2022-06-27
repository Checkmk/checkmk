#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import json
from collections import defaultdict
from typing import Callable, Mapping

from .agent_based_api.v1 import register
from .agent_based_api.v1.type_defs import StringTable
from .utils.gcp import AssetSection, AssetType, AssetTypeSection, Config, GCPAsset, Item


def parse_assets(string_table: StringTable) -> AssetSection:
    info = json.loads(string_table[0][0])
    project = info["project"]
    config = Config(info["config"])

    assets = [GCPAsset.deserialize(row[0]) for row in string_table[1:]]
    sorted_assets: dict[AssetType, list[GCPAsset]] = defaultdict(list)
    for a in assets:
        sorted_assets[a.asset.asset_type].append(a)

    # fmt: off
    extractors: Mapping[AssetType, Callable[[GCPAsset], Item]] = {
        "file.googleapis.com/Instance": lambda a: a.asset.resource.data["name"].split("/")[-1],
        "cloudfunctions.googleapis.com/CloudFunction": lambda a: a.asset.resource.data["name"].split("/")[-1],
        "storage.googleapis.com/Bucket": lambda a: a.asset.resource.data["id"],
        "redis.googleapis.com/Instance": lambda a: a.asset.resource.data["name"],
        "run.googleapis.com/Service": lambda a: a.asset.resource.data["metadata"]["name"],
        "sqladmin.googleapis.com/Instance": lambda a: a.asset.resource.data["name"],
    }
    # fmt: on
    typed_assets: dict[AssetType, AssetTypeSection] = {}
    for asset_type, assets in sorted_assets.items():
        extract = extractors[asset_type]
        typed_assets[asset_type] = {extract(a): a for a in assets}

    return AssetSection(project, config, typed_assets)


register.agent_section(name="gcp_assets", parse_function=parse_assets)
