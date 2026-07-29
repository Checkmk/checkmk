#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence
from logging import Logger
from typing import Final, override

from cmk.gui.config import active_config
from cmk.gui.site_config import is_distributed_setup_remote_site
from cmk.gui.watolib.hosts_and_folders import Folder
from cmk.gui.watolib.rulesets import AllRulesets, Rule
from cmk.update_config.lib import ExpiryVersion, format_warning
from cmk.update_config.plugins.lib.mk_oracle_migration import convert
from cmk.update_config.registry import update_action_registry, UpdateAction

_AGENT_CONFIG_LEGACY_ORACLE: Final[str] = "agent_config:mk_oracle"


class WarnAboutLegacyOracleRules(UpdateAction):
    @override
    def __call__(self, logger: Logger) -> None:
        if is_distributed_setup_remote_site(active_config.sites):
            return

        all_rulesets = AllRulesets.load_all_rulesets()
        if not all_rulesets.exists(_AGENT_CONFIG_LEGACY_ORACLE):
            return

        if not (rules := all_rulesets.get(_AGENT_CONFIG_LEGACY_ORACLE).get_rules()):
            return

        total_warnings = _count_migration_warnings(rules, logger)

        logger.warning(
            format_warning(
                f"Found {len(rules)} rule(s) in the legacy Oracle agent configuration "
                f"({_AGENT_CONFIG_LEGACY_ORACLE}). This plug-in has been superseded by the unified "
                f"Oracle plug-in. Migrating them would produce {total_warnings} warning(s) to "
                "review. Run 'cmk-migrate-oracle-rulesets' to migrate them (no flags for a "
                "dry-run preview, --apply to actually create the migrated rules)."
            )
        )


update_action_registry.register(
    WarnAboutLegacyOracleRules(
        name="warn_about_legacy_oracle_rules",
        title="Checking for legacy Oracle agent configuration rules",
        sort_index=100,  # pure read-only check, no ordering constraints
        expiry_version=ExpiryVersion.CMK_310,
    )
)


def _count_migration_warnings(rules: Sequence[tuple[Folder, int, Rule]], logger: Logger) -> int:
    total = 0
    for _folder, _index, rule in rules:
        try:
            total += len(convert(rule.value).warnings)
        except Exception:
            logger.debug(
                "Could not pre-compute migration warnings for rule %(rule_id)s",
                {"rule_id": rule.id},
            )
    return total
