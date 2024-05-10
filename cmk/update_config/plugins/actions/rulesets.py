#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# pylint: disable=protected-access

import re
from collections.abc import Iterable, Mapping, Sequence
from logging import Logger
from typing import Any

import cmk.utils.store as store
from cmk.utils import debug
from cmk.utils.labels import single_label_group_from_labels
from cmk.utils.log import VERBOSE
from cmk.utils.rulesets.definition import RuleGroup
from cmk.utils.rulesets.ruleset_matcher import RulesetName, RuleSpec

from cmk.base import config

from cmk.gui.exceptions import MKUserError
from cmk.gui.watolib.hosts_and_folders import Folder, folder_tree
from cmk.gui.watolib.rulesets import (
    AllRulesets,
    FolderPath,
    Rule,
    RuleConditions,
    RulesetCollection,
)

from cmk.update_config.lib import format_warning
from cmk.update_config.registry import update_action_registry, UpdateAction

REPLACED_RULESETS: Mapping[RulesetName, RulesetName] = {
    "checkgroup_parameters:fileinfo-groups": "checkgroup_parameters:fileinfo_groups_checking",
    "checkgroup_parameters:robotmk_suite": "checkgroup_parameters:robotmk_plan",
    "static_checks:fileinfo-groups": "static_checks:fileinfo_groups_checking",
    "checkgroup_parameters:if": "checkgroup_parameters:interfaces",
    "static_checks:if": "static_checks:interfaces",
    "special_agents:3par": "special_agents:three_par",
}

RULESETS_LOOSING_THEIR_ITEM: Iterable[RulesetName] = {
    "mongodb_replica_set",
    "netapp_fcportio",
    "azure_agent_info",
}

DEPRECATED_RULESET_PATTERNS = (re.compile("^agent_simulator$"),)


class UpdateRulesets(UpdateAction):
    def __call__(self, logger: Logger) -> None:
        # To transform the given ruleset config files before initialization, we cannot call
        # AllRulesets.load_all_rulesets() here.
        raw_rulesets = AllRulesets(RulesetCollection._initialize_rulesets())
        root_folder = folder_tree().root_folder()
        all_rulesets = _transform_label_conditions_in_all_folders(logger, raw_rulesets, root_folder)

        if "http" not in config.use_new_descriptions_for:
            _force_old_http_service_description(all_rulesets)

        _delete_deprecated_wato_rulesets(
            logger,
            all_rulesets,
            DEPRECATED_RULESET_PATTERNS,
        )
        _transform_rulesets_loosing_item(
            logger,
            all_rulesets,
            RULESETS_LOOSING_THEIR_ITEM,
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
        _validate_rule_values(logger, all_rulesets)
        all_rulesets.save()


update_action_registry.register(
    UpdateRulesets(
        name="rulesets",
        title="Rulesets",
        sort_index=30,
    )
)


def _transform_label_conditions_in_all_folders(
    logger: Logger, all_rulesets: AllRulesets, folder: Folder
) -> AllRulesets:
    for subfolder in folder.subfolders():
        _transform_label_conditions_in_all_folders(logger, all_rulesets, subfolder)

    loaded_file_config = store.load_mk_file(
        folder.rules_file_path(),
        {
            **RulesetCollection._context_helpers(folder),
            **RulesetCollection._prepare_empty_rulesets(),
        },
    )

    for varname, ruleset_config in all_rulesets.get_ruleset_configs_from_file(
        folder, loaded_file_config
    ):
        if not ruleset_config:
            continue  # Nothing configured: nothing left to do

        # Transform parameters per rule
        for rule_config in ruleset_config:
            _transform_label_conditions(rule_config)

        # Overwrite rulesets
        all_rulesets.replace_folder_ruleset_config(folder, ruleset_config, varname)

    return all_rulesets


def _transform_label_conditions(rule_config: RuleSpec[object]) -> None:
    if any(key.endswith("_labels") for key in rule_config.get("condition", {})):
        rule_config["condition"] = transform_condition_labels_to_label_groups(  # type: ignore[typeddict-item]
            rule_config.get("condition", {})  # type: ignore[arg-type]
        )


def transform_condition_labels_to_label_groups(conditions: dict[str, Any]) -> dict[str, Any]:
    for what in ["host", "service"]:
        old_key = f"{what}_labels"
        new_key = f"{what}_label_groups"
        if old_key in conditions:
            conditions[new_key] = (
                single_label_group_from_labels(conditions[old_key]) if conditions[old_key] else []
            )
            del conditions[old_key]
    return conditions


def _delete_deprecated_wato_rulesets(
    logger: Logger,
    all_rulesets: RulesetCollection,
    deprecated_ruleset_patterns: Sequence[re.Pattern],
) -> None:
    for ruleset_name in list(all_rulesets.get_rulesets()):
        if any(p.match(ruleset_name) for p in deprecated_ruleset_patterns):
            logger.log(VERBOSE, f"Removing ruleset {ruleset_name}")
            all_rulesets.delete(ruleset_name)
            continue


def _transform_rulesets_loosing_item(
    logger: Logger,
    all_rulesets: RulesetCollection,
    rulesets_loosing_item: Iterable[str],
) -> None:
    for ruleset_name in rulesets_loosing_item:
        logger.log(VERBOSE, f"Fixing items for ruleset {ruleset_name}")
        for _folder, _index, rule in all_rulesets.get(
            f"checkgroup_parameters:{ruleset_name}"
        ).get_rules():
            rule.conditions = RuleConditions(
                host_folder=rule.conditions.host_folder,
                host_tags=rule.conditions.host_tags,
                host_label_groups=rule.conditions.host_label_groups,
                host_name=rule.conditions.host_name,
                service_description=None,
                service_label_groups=rule.conditions.service_label_groups,
            )
        for _folder, _index, rule in all_rulesets.get(f"static_checks:{ruleset_name}").get_rules():
            rule.value = (rule.value[0], None, rule.value[2])


def _force_old_http_service_description(all_rulesets: RulesetCollection) -> None:
    # relevant for update to 2.4

    # remove "http" from configuration/ add another update step
    if (http_ruleset := all_rulesets.get("active_checks:http")).is_empty():
        return

    for _, _, rule in http_ruleset.get_rules():
        if rule.value["name"].startswith("^"):
            continue

        rule.value["name"] = f"^HTTP {rule.value['name']}"


def _transform_replaced_wato_rulesets(
    logger: Logger,
    all_rulesets: RulesetCollection,
    replaced_rulesets: Mapping[RulesetName, RulesetName],
) -> None:
    _transform_replaced_unknown_rulesets(logger, all_rulesets, replaced_rulesets)
    _transform_replaced_known_rulesets(logger, all_rulesets, replaced_rulesets)


def _transform_replaced_known_rulesets(
    logger: Logger,
    all_rulesets: RulesetCollection,
    replaced_rulesets: Mapping[RulesetName, RulesetName],
) -> None:
    deprecated_ruleset_names: set[RulesetName] = set()
    for ruleset_name, ruleset in all_rulesets.get_rulesets().items():
        if ruleset_name not in replaced_rulesets:
            continue

        new_ruleset = all_rulesets.get(replaced_rulesets[ruleset_name])

        logger.log(VERBOSE, f"Replacing ruleset {ruleset_name} with {new_ruleset.name}")
        for folder, _folder_index, rule in ruleset.get_rules():
            new_ruleset.append_rule(folder, rule)

        deprecated_ruleset_names.add(ruleset_name)
    for deprecated_ruleset_name in deprecated_ruleset_names:
        all_rulesets.delete(deprecated_ruleset_name)


def _transform_replaced_unknown_rulesets(
    logger: Logger,
    all_rulesets: RulesetCollection,
    replaced_rulesets: Mapping[RulesetName, RulesetName],
) -> None:
    deprecated_unknown_ruleset_names_per_folder: dict[FolderPath, set[RulesetName]] = {}
    for folder_path, ruleset_configs in all_rulesets.get_unknown_rulesets().items():
        folder = folder_tree().folder(folder_path)
        deprecated_unknown_ruleset_names_per_folder[folder_path] = set()
        for ruleset_name, rule_specs in ruleset_configs.items():
            if ruleset_name not in replaced_rulesets:
                continue

            new_ruleset = all_rulesets.get(replaced_rulesets[ruleset_name])

            logger.log(VERBOSE, f"Replacing ruleset {ruleset_name} with {new_ruleset.name}")
            for rule_spec in rule_specs:
                new_ruleset.append_rule(folder, Rule.from_config(folder, new_ruleset, rule_spec))

            deprecated_unknown_ruleset_names_per_folder[folder_path].add(ruleset_name)
    for (
        folder_path,
        deprecated_unknown_ruleset_names,
    ) in deprecated_unknown_ruleset_names_per_folder.items():
        for deprecated_unknown_ruleset_name in deprecated_unknown_ruleset_names:
            all_rulesets.delete_unknown(folder_path, deprecated_unknown_ruleset_name)


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
        RuleGroup.ExtraServiceConf("_sla_config"),
        # Validating the ignored checks ruleset does not make sense:
        # Invalid choices are the plugins that don't exist (anymore).
        # These do no harm, they are dropped upon rule edit. On the other hand, the plugin
        # could be missing only temporarily, so better not remove it.
        "ignored_checks",
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
