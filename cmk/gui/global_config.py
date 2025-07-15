#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pydantic import BaseModel

from cmk.ccc.version import Edition, edition
from cmk.gui.log import logger
from cmk.utils import paths
from cmk.utils.paths import cse_config_dir
from cmk.utils.rulesets.definition import RuleGroupType

LOGGER = logger.getChild("global-config")


class GlobalSettings(BaseModel):
    is_activate: set[str]

    def is_activated(self, varname: str) -> bool:
        return edition(paths.omd_root) is not Edition.CSE or varname in self.is_activate


class RuleSetGroup(BaseModel):
    type_: RuleGroupType | None = None
    rule_names: set[str] = set()


class RulespecAllowList(BaseModel):
    rule_groups: list[RuleSetGroup] = []


class GlobalConfig(BaseModel):
    global_settings: GlobalSettings
    rulespec_allow_list: RulespecAllowList


def load_global_config() -> GlobalConfig:
    path = cse_config_dir / "global-config.json"
    try:
        with open(path, encoding="utf-8") as file:
            return GlobalConfig.model_validate_json(file.read())
    except Exception as e:
        if edition(paths.omd_root) is not Edition.CSE:
            LOGGER.debug("Failed to load config from %s: %s", path, e)
        return GlobalConfig(
            global_settings=GlobalSettings(is_activate=set[str]()),
            rulespec_allow_list=RulespecAllowList(),
        )


def get_global_config() -> GlobalConfig:
    return load_global_config()
