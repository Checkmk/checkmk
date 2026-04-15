#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from logging import Logger
from typing import override

import cmk.ec.export as ec  # astrein: disable=cmk-module-layer-violation
import cmk.utils.paths
from cmk.update_config.lib import ExpiryVersion
from cmk.update_config.registry import update_action_registry, UpdateAction

DEPRECATED_INTERVAL = 10
NEW_INTERVAL = 60


class MigrateECRuleExpectInterval(UpdateAction):
    @override
    def __call__(self, logger: Logger) -> None:
        paths = ec.create_paths(cmk.utils.paths.omd_root)
        rule_packs = ec.load_rule_packs(paths)

        non_proxy_packs = [p for p in rule_packs if not isinstance(p, ec.MkpRulePackProxy)]
        should_save = False
        for rule_pack in non_proxy_packs:
            for rule in rule_pack.get("rules", []):
                if (expect := rule.get("expect")) and expect.get("interval") == DEPRECATED_INTERVAL:
                    expect["interval"] = NEW_INTERVAL
                    logger.debug(
                        "Found unsupported 10 second interval in EC rule %s. Updating it to 1 minute.",
                        rule["id"],
                    )
                    should_save = True

        if should_save:
            ec.save_rule_packs(non_proxy_packs, pretty_print=False, path=paths.rule_pack_dir.value)


update_action_registry.register(
    MigrateECRuleExpectInterval(
        name="migrate_ec_rule_expect_interval",
        title="Event Console: Migrate 10 second expect interval to 1 minute",
        sort_index=137,
        expiry_version=ExpiryVersion.CMK_260,
    )
)
