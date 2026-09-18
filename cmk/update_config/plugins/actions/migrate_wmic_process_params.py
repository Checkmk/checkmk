#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Rewrite the parameters of enforced wmic_process services as a dictionary.

Until 3.0 the ruleset stored them as a positional tuple, which the check engine cannot
merge: as soon as such a rule exists, discovery fails with "'tuple' object is not a
mapping". The form spec of the ruleset cannot do the migration. The value of an
enforced service is a tuple of check name, item and parameters, and the visitor
validates the check name against the plugins subscribing to the check group before it
reaches the parameters. That needs a running automation helper, so during an update the
migration is skipped -- silently, because the caller only logs the exception.
"""

from logging import Logger
from typing import Final, override

from cmk.agent_based.v2 import FixedLevelsT, NoLevelsT
from cmk.gui.config import active_config, Config
from cmk.gui.watolib.hosts_and_folders import make_folder_tree
from cmk.gui.watolib.rulesets import AllRulesets, RulesetCollection
from cmk.plugins.windows.agent_based.wmic_process import Params
from cmk.ruleset_matcher.definition import RuleGroup
from cmk.update_config.lib import ExpiryVersion
from cmk.update_config.registry import update_action_registry, UpdateAction
from cmk.utils.timeperiod import TIMESPECIFIC_DEFAULT_KEY

_RULESET_NAME: Final = RuleGroup.StaticChecks("wmic_process")

_LEGACY_TUPLE_LENGTH: Final = 7

_NO_LEVELS: Final[NoLevelsT] = ("no_levels", None)


def _migrated_levels(warn: object, crit: object) -> NoLevelsT | FixedLevelsT[float] | None:
    """Translate one warn/crit pair of the legacy tuple, or `None` if it holds no numbers.

    The legacy check disabled a bound by setting it to zero, independently for warn and
    crit. Level parameters can only express a pair, so a rule that kept just one of the
    two bounds is mapped to that bound alone -- keeping the zero would alert on every
    value.
    """
    if not isinstance(warn, int | float) or not isinstance(crit, int | float):
        return None
    match warn, crit:
        case (0, 0):
            return _NO_LEVELS
        case (0, active) | (active, 0):
            return "fixed", (float(active), float(active))
        case _:
            return "fixed", (float(warn), float(crit))


def migrated_parameters(value: object) -> Params | None:
    """Return the parameters to write instead, or `None` if there is nothing to do.

    We leave values we do not recognize alone. Rewriting them into something the ruleset
    accepts would lose what the user configured, and the ruleset reports them anyway.
    """
    if not isinstance(value, tuple) or len(value) != _LEGACY_TUPLE_LENGTH:
        return None
    name, mem_warn, mem_crit, page_warn, page_crit, cpu_warn, cpu_crit = value
    if not isinstance(name, str):
        return None
    if (mem_levels := _migrated_levels(mem_warn, mem_crit)) is None:
        return None
    if (page_levels := _migrated_levels(page_warn, page_crit)) is None:
        return None
    if (cpu_levels := _migrated_levels(cpu_warn, cpu_crit)) is None:
        return None
    return {
        "name": name,
        "mem_levels": mem_levels,
        "page_levels": page_levels,
        "cpu_levels": cpu_levels,
    }


def migrate_rules(all_rulesets: RulesetCollection, logger: Logger) -> int:
    """Rewrite the rule values in place, returning the number of rewritten rules."""
    if not all_rulesets.exists(_RULESET_NAME):
        return 0

    n_migrated = 0
    for folder, _index, rule in all_rulesets.get(_RULESET_NAME).get_rules():
        match rule.value:
            case (str(check_plugin), item, tuple() as legacy_parameters):
                pass
            case (str(), _item, dict() as parameters) if TIMESPECIFIC_DEFAULT_KEY not in parameters:
                continue  # already migrated
            case _:
                # Neither the legacy tuple nor an already migrated dict. That leaves the
                # {"tp_default_value": ..., "tp_values": ...} wrapper the rulespec adds
                # for time specific parameters, which holds the legacy tuples one level
                # down, and entries carrying no parameters at all. Migrating either is
                # not worth the code, but skipping them quietly is worse: the check then
                # blames the missing process name.
                logger.warning(
                    "Cannot migrate rule %(rule_id)s of ruleset '%(ruleset_name)s' in folder "
                    "'%(folder_path)s': %(old)r. Please check the rule in the Setup.",
                    {
                        "rule_id": rule.id,
                        "ruleset_name": _RULESET_NAME,
                        "folder_path": folder.path() or "main",
                        "old": rule.value,
                    },
                )
                continue

        if (migrated := migrated_parameters(legacy_parameters)) is None:
            logger.warning(
                "Cannot migrate rule %(rule_id)s of ruleset '%(ruleset_name)s' in folder "
                "'%(folder_path)s': %(old)r. Please check the rule in the Setup.",
                {
                    "rule_id": rule.id,
                    "ruleset_name": _RULESET_NAME,
                    "folder_path": folder.path() or "main",
                    "old": rule.value,
                },
            )
            continue

        logger.info(
            "Rewriting rule %(rule_id)s of ruleset '%(ruleset_name)s' in folder "
            "'%(folder_path)s': %(old)r -> %(new)r",
            {
                "rule_id": rule.id,
                "ruleset_name": _RULESET_NAME,
                "folder_path": folder.path() or "main",
                "old": legacy_parameters,
                "new": migrated,
            },
        )
        rule.value = (check_plugin, item, migrated)
        n_migrated += 1
    return n_migrated


def _migrate_rules(logger: Logger, ui_config: Config) -> None:
    all_rulesets = AllRulesets.load_all_rulesets(make_folder_tree(ui_config))
    if not migrate_rules(all_rulesets, logger):
        return
    all_rulesets.save(pprint_value=ui_config.wato_pprint_config, debug=ui_config.debug)


class MigrateWmicProcessParams(UpdateAction):
    @override
    def __call__(self, logger: Logger) -> None:
        _migrate_rules(logger, active_config)


update_action_registry.register(
    MigrateWmicProcessParams(
        name="migrate_wmic_process_params",
        title="Migrating enforced wmic_process service parameters",
        sort_index=21,  # before the rulesets action (30) validates the rule values
        expiry_version=ExpiryVersion.CMK_310,
    )
)
