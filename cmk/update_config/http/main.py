#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from pprint import pprint
from typing import Literal

from pydantic import BaseModel, Extra, ValidationError

from cmk.utils.redis import disable_redis

from cmk.gui.main_modules import load_plugins
from cmk.gui.session import SuperUserContext
from cmk.gui.utils.script_helpers import gui_context
from cmk.gui.watolib.rulesets import AllRulesets
from cmk.gui.wsgi.blueprints.global_vars import set_global_vars


class V1Host(BaseModel):
    # "ipv4_enforced", "ipv6_enforced", "primary_enforced" don't have a counter part in V2.
    # "primary_enforced" has the additional issue, that the ssc would also need to support it.
    address_family: Literal["any", None] = None

    class Config:
        extra = Extra.forbid


class V1Url(BaseModel):
    class Config:
        extra = Extra.forbid


class V1Value(BaseModel):
    name: str
    host: V1Host
    mode: tuple[Literal["url"], V1Url]

    class Config:
        extra = Extra.forbid


def _migratable(rule_value: Mapping[str, object]) -> bool:
    try:
        V1Value.model_validate(rule_value)
        return True
    except ValidationError:
        return False


def _migrate(rule_value: V1Value) -> Mapping[str, object]:
    # Risk: We can't be sure the active checks and the config cache use the same IP look up (but
    # both of them are based on the same user data. Moreover, `primary_ip_config.address` (see
    # `get_ssc_host_config` is slightly differently implemented than `HOSTADDRESS` (see
    # `attrs["address"]` in `cmk/base/config.py:3454`).
    return {
        "endpoints": [
            {
                "service_name": {"prefix": "auto", "name": rule_value.name},
                "url": "https://$HOSTADDRESS$",
            }
        ],
    }


def main() -> None:
    load_plugins()
    with disable_redis(), gui_context(), SuperUserContext():
        set_global_vars()
        all_rulesets = AllRulesets.load_all_rulesets()
    for folder, rule_index, rule in all_rulesets.get_rulesets()["active_checks:http"].get_rules():
        if _migratable(rule.value):
            print(f"MIGRATABLE: {folder}, {rule_index}")
        else:
            print(f"IMPOSSIBLE: {folder}, {rule_index}")
        pprint(rule.value)
        print("")


if __name__ == "__main__":
    main()
