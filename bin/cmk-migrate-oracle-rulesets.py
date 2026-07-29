#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""CLI to migrate legacy agent_config:mk_oracle bakery rules to agent_config:mk_oracle_unified."""

import argparse
import logging
import sys
from collections.abc import Sequence

from cmk.ccc.version import edition
from cmk.gui import main_modules
from cmk.gui.config import active_config
from cmk.gui.site_config import is_distributed_setup_remote_site
from cmk.gui.utils.script_helpers import gui_context
from cmk.gui.watolib.rulesets import AllRulesets
from cmk.update_config.plugins.lib.mk_oracle_migration import migrate_ruleset, MigrationResult
from cmk.utils import paths

logger = logging.getLogger(__name__)


def main(argv: Sequence[str] | None = None) -> int:
    logger.addHandler(handler := logging.StreamHandler(stream=sys.stdout))
    handler.setFormatter(logging.Formatter("%(message)s"))
    logger.setLevel(logging.INFO)
    main_modules.register(edition(paths.omd_root))
    parser = argparse.ArgumentParser(
        description="Migrate legacy agent_config:mk_oracle rules to agent_config:mk_oracle_unified."
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Actually create the migrated rules. Without this flag, only a dry-run report is printed.",
    )
    parser.add_argument(
        "--enable-migrated-rules",
        action="store_true",
        help="Create migrated rules as enabled. By default, migrated rules are created disabled.",
    )
    args = parser.parse_args(argv)

    with gui_context():
        if is_distributed_setup_remote_site(active_config.sites):
            logger.info(
                "This is a remote site. Oracle rules are managed on a central site. Run this tool there instead."
            )
            return 0

        all_rulesets = AllRulesets.load_all_rulesets()
        legacy_ruleset = all_rulesets.get("agent_config:mk_oracle")
        unified_ruleset = all_rulesets.get("agent_config:mk_oracle_unified")

        results, skipped = migrate_ruleset(
            legacy_ruleset, unified_ruleset, disabled=not args.enable_migrated_rules
        )
        _print_report(results, skipped)

        if args.apply:
            for result in results:
                unified_ruleset.append_rule(result.new_rule.folder, result.new_rule)
            all_rulesets.save(pprint_value=True, debug=False)
        else:
            logger.info(
                "\nDry run only — no rules were written. Re-run with --apply to create them."
            )

    return 0


def _print_report(results: Sequence[MigrationResult], skipped: int) -> None:
    for result in results:
        legacy_rule = result.legacy_rule
        name = legacy_rule.description() if legacy_rule.description() else legacy_rule.id
        logger.info(
            "Rule '%(name)s' (folder: %(folder)s)",
            {"name": name, "folder": legacy_rule.folder.path() or "/"},
        )
        for w in result.warnings:
            logger.info("  - %(warning)s", {"warning": w})
        if not result.warnings:
            logger.info("  - no warnings")
        logger.info("")

    total = len(results)
    with_warnings = sum(len(result.warnings) for result in results if result.warnings)
    logger.info(
        "%(total)d rule(s) processed, %(with_warnings)d total warning(s).",
        {"total": total, "with_warnings": with_warnings},
    )
    if skipped:
        logger.info("%(skipped)d rule(s) already migrated — skipped.", {"skipped": skipped})


if __name__ == "__main__":
    sys.exit(main())
