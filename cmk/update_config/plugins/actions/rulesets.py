#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import re
from collections.abc import Container, Mapping, Sequence
from datetime import time as dt_time
from itertools import chain
from logging import Logger
from re import Pattern

from cmk.utils import debug
from cmk.utils.log import VERBOSE
from cmk.utils.rulesets.ruleset_matcher import RulesetName

from cmk.checkers.checking import CheckPluginName

from cmk.gui.exceptions import MKUserError
from cmk.gui.watolib import timeperiods
from cmk.gui.watolib.rulesets import AllRulesets, Rule, RulesetCollection

from cmk.update_config.plugins.actions.replaced_check_plugins import REPLACED_CHECK_PLUGINS
from cmk.update_config.registry import update_action_registry, UpdateAction
from cmk.update_config.update_state import format_warning, UpdateActionState

REPLACED_RULESETS: Mapping[RulesetName, RulesetName] = {
    "discovery_systemd_units_services_rules": "discovery_systemd_units_services",
    "checkgroup_parameters:systemd_services": "checkgroup_parameters:systemd_units_services",
    "checkgroup_parameters:apc_symmetra_power": "checkgroup_parameters:epower",
    "static_checks:systemd_services": "static_checks:systemd_units_services",
}

DEPRECATED_RULESET_PATTERNS = (re.compile("^inv_exports:"),)


class UpdateRulesets(UpdateAction):
    def __call__(self, logger: Logger, update_action_state: UpdateActionState) -> None:
        all_rulesets = AllRulesets.load_all_rulesets()

        # this *must* be done before the transorms, otherwise information is lost!
        _extract_connection_encryption_handling_from_210_rules(logger, all_rulesets)

        _transform_fileinfo_timeofday_to_timeperiods(all_rulesets)
        _delete_deprecated_wato_rulesets(
            logger,
            all_rulesets,
            DEPRECATED_RULESET_PATTERNS,
        )
        _transform_replaced_wato_rulesets(
            logger,
            all_rulesets,
            REPLACED_RULESETS,
        )
        _transform_wato_rulesets_params(
            logger,
            all_rulesets,
        )
        _remove_removed_check_plugins_from_ignored_checks(
            all_rulesets,
            REPLACED_CHECK_PLUGINS,
        )
        _validate_rule_values(logger, all_rulesets)
        all_rulesets.save()


update_action_registry.register(
    UpdateRulesets(
        name="rulesets",
        title="Rulesets",
        sort_index=30,
    )
)


def _extract_connection_encryption_handling_from_210_rules(
    logger: Logger, all_rulesets: RulesetCollection
) -> None:
    """Exctract the new 2.2 'encryption_handling' rule from the old 2.1 'agent_encryption'

    We must do this befor we transform the rules, as the used information is then removed by the migration.
    This can be removed after 2.2 is forked away.
    """
    if not (encryption_handling := all_rulesets.get("encryption_handling")).is_empty():
        logger.log(VERBOSE, "New rule 'encryption_handling' is already present")
        return

    if (encryption_ruleset := all_rulesets.get("agent_encryption")).is_empty():
        logger.log(VERBOSE, "No 'agent_encryption' rules to transform")
        return

    logger.log(VERBOSE, "Create 'encryption_handling' rules from 'agent_encryption'")
    for folder, _folder_index, rule in encryption_ruleset.get_rules():
        if not rule.value or "use_regular" not in rule.value:
            continue

        new_rule = Rule.from_ruleset_defaults(folder, encryption_handling)
        match rule.value["use_regular"]:
            case "enforce":
                new_rule.value["accept"] = "any_encrypted"
            case "allow":
                new_rule.value["accept"] = "any_and_plain"
            case "disable":
                continue
            case unknown_setting:
                raise ValueError(f"Unknown setting in {encryption_ruleset.name}: {unknown_setting}")

        new_rule.rule_options.comment = (
            "This rule has been created automatically during the upgrade to Checkmk version 2.2.\n"
            f"Please refer to Werk #14982 for details.\n\n{new_rule.comment()}"
        )
        logger.log(VERBOSE, "Adding 'encryption_handling' rule: %s", new_rule.id)
        encryption_handling.append_rule(folder, new_rule)


def _delete_deprecated_wato_rulesets(
    logger: Logger,
    all_rulesets: RulesetCollection,
    deprecated_ruleset_patterns: tuple[Pattern],
) -> None:
    for ruleset_name in list(all_rulesets.get_rulesets()):
        if any(p.match(ruleset_name) for p in deprecated_ruleset_patterns):
            logger.log(VERBOSE, f"Removing ruleset {ruleset_name}")
            all_rulesets.delete(ruleset_name)
            continue


def _transform_replaced_wato_rulesets(
    logger: Logger,
    all_rulesets: RulesetCollection,
    replaced_rulesets: Mapping[RulesetName, RulesetName],
) -> None:
    deprecated_ruleset_names: set[RulesetName] = set()
    for ruleset_name, ruleset in all_rulesets.get_rulesets().items():
        if ruleset_name not in replaced_rulesets:
            continue

        new_ruleset = all_rulesets.get(replaced_rulesets[ruleset_name])

        if not new_ruleset.is_empty():
            logger.log(VERBOSE, "Found deprecated ruleset: %s" % ruleset_name)

        logger.log(VERBOSE, f"Replacing ruleset {ruleset_name} with {new_ruleset.name}")
        for folder, _folder_index, rule in ruleset.get_rules():
            new_ruleset.append_rule(folder, rule)

        deprecated_ruleset_names.add(ruleset_name)

    for deprecated_ruleset_name in deprecated_ruleset_names:
        all_rulesets.delete(deprecated_ruleset_name)


def _transform_wato_rulesets_params(
    logger: Logger,
    all_rulesets: RulesetCollection,
) -> None:
    for ruleset in all_rulesets.get_rulesets().values():
        valuespec = ruleset.valuespec()
        for folder, folder_index, rule in ruleset.get_rules():
            try:
                rule.value = valuespec.transform_value(rule.value)
            except Exception as e:
                if debug.enabled():
                    raise
                logger.error(
                    "ERROR: Failed to transform rule: (Ruleset: %s, Folder: %s, "
                    "Rule: %d, Value: %s: %s",
                    ruleset.name,
                    folder.path(),
                    folder_index,
                    rule.value,
                    e,
                )


def _validate_rule_values(
    logger: Logger,
    all_rulesets: RulesetCollection,
) -> None:
    rulesets_skip = {
        # the valid choices for this ruleset are user-dependent (SLAs) and not even an admin can
        # see all of them
        "extra_service_conf:_sla_config",
    }

    n_invalid = 0
    for ruleset in all_rulesets.get_rulesets().values():
        if ruleset.name in rulesets_skip:
            continue

        for folder, index, rule in ruleset.get_rules():
            try:
                ruleset.rulespec.valuespec.validate_value(
                    rule.value,
                    "",
                )
            except MKUserError as excpt:
                n_invalid += 1
                logger.warning(
                    format_warning(
                        "WARNING: Invalid rule configuration detected (Ruleset: %s, Title: %s, "
                        "Folder: %s,\nRule nr: %s, Exception: %s)"
                    ),
                    ruleset.name,
                    ruleset.title(),
                    folder.path(),
                    index + 1,
                    excpt,
                )

    if n_invalid:
        logger.warning(
            format_warning(
                "Detected %s issue(s) in configured rules.\n"
                "To correct these issues, we recommend to open the affected rules in the GUI.\n"
                "Upon attempting to save them, any problematic fields will be highlighted."
            ),
            n_invalid,
        )


def _remove_removed_check_plugins_from_ignored_checks(
    all_rulesets: RulesetCollection,
    removed_check_plugins: Container[CheckPluginName],
) -> None:
    ignored_checks_ruleset = all_rulesets.get("ignored_checks")
    for _folder, _index, rule in ignored_checks_ruleset.get_rules():
        if plugins_to_keep := [
            plugin_str
            for plugin_str in rule.value
            if CheckPluginName(plugin_str).create_basic_name() not in removed_check_plugins
        ]:
            rule.value = plugins_to_keep
        else:
            ignored_checks_ruleset.delete_rule(
                rule,
                create_change=False,
            )


def _transform_fileinfo_timeofday_to_timeperiods(collection: RulesetCollection) -> None:
    """Transforms the deprecated timeofday parameter to timeperiods

    In the general case, timeperiods shouldn't be specified if timeofday is used.
    It wasn't restriced, but it doesn't make sense to have both.
    In case of timeofday in the default timeperiod, timeofday time range is
    used and other timeperiods are removed.
    In case of timeofday in the non-default timeperiod, timeofday param is removed.

    This transformation is introduced in v2.2 and can be removed in v2.3.
    """
    all_rulesets = collection.get_rulesets()
    rulesets = [all_rulesets[f"checkgroup_parameters:{c}"] for c in ("fileinfo", "fileinfo-groups")]
    rules = [r.get_rules() for r in rulesets]

    for _folder, _folder_index, rule in chain(*rules):
        # in case there are timeperiods, look at default timepriod params
        rule_params = rule.value.get("tp_default_value", rule.value)

        timeofday = rule_params.get("timeofday")
        if not timeofday:
            # delete timeofday from non-default timeperiods
            # this configuration doesn't make sense at all, there is nothing to transform it to
            for _, tp_params in rule.value.get("tp_values", {}):
                tp_params.pop("timeofday", None)
            continue

        timeperiod_name = _get_timeperiod_name(timeofday)
        if timeperiod_name not in timeperiods.load_timeperiods():
            _create_timeperiod(timeperiod_name, timeofday)

        thresholds = {
            k: p
            for k, p in rule_params.items()
            if k not in ("timeofday", "tp_default_value", "tp_values")
        }
        tp_values = [(timeperiod_name, thresholds)]

        rule.value = {"tp_default_value": {}, "tp_values": tp_values}


TimeRange = tuple[tuple[int, int], tuple[int, int]]


def _transform_time_range(time_range: TimeRange) -> tuple[str, str]:
    begin_time = dt_time(hour=time_range[0][0], minute=time_range[0][1])
    end_time = dt_time(hour=time_range[1][0], minute=time_range[1][1])
    return (begin_time.strftime("%H:%M"), end_time.strftime("%H:%M"))


def _get_timeperiod_name(timeofday: Sequence[TimeRange]) -> str:
    periods = [_transform_time_range(t) for t in timeofday]
    period_string = "_".join((f"{b}-{e}" for b, e in periods)).replace(":", "")
    return f"timeofday_{period_string}"


def _create_timeperiod(name: str, timeofday: Sequence[TimeRange]) -> None:
    periods = [_transform_time_range(t) for t in timeofday]
    periods_alias = ", ".join((f"{b}-{e}" for b, e in periods))
    timeperiods.save_timeperiod(
        name,
        {
            "alias": f"Created by migration of timeofday parameter ({periods_alias})",
            **{
                d: periods
                for d in (
                    "monday",
                    "tuesday",
                    "wednesday",
                    "thursday",
                    "friday",
                    "saturday",
                    "sunday",
                )
            },
        },
    )
