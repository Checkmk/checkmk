#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterable, Mapping, Sequence
from logging import Logger
from re import match, Pattern
from typing import Any, Collection

import cmk.utils.store as store
from cmk.utils import debug
from cmk.utils.labels import single_label_group_from_labels
from cmk.utils.log import VERBOSE
from cmk.utils.rulesets.definition import RuleGroup
from cmk.utils.rulesets.ruleset_matcher import RulesetName, RuleSpec, TagCondition
from cmk.utils.tags import TagGroupID

from cmk.gui.exceptions import MKUserError
from cmk.gui.watolib.hosts_and_folders import Folder, folder_tree
from cmk.gui.watolib.rulesets import (
    AllRulesets,
    FolderPath,
    Rule,
    RuleConditions,
    RulesetCollection,
)

from cmk.update_config.registry import update_action_registry, UpdateAction
from cmk.update_config.update_state import format_warning, UpdateActionState

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

DEPRECATED_RULESET_PATTERNS: list[Pattern] = []


class UpdateRulesets(UpdateAction):
    def __call__(self, logger: Logger, update_action_state: UpdateActionState) -> None:
        # To transform the given ruleset config files before initialization, we cannot call
        # AllRulesets.load_all_rulesets() here.
        raw_rulesets = AllRulesets(RulesetCollection._initialize_rulesets())
        root_folder = folder_tree().root_folder()
        all_rulesets = _transform_label_conditions_in_all_folders(logger, raw_rulesets, root_folder)

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
        _transform_wato_ruleset_memory_simple(
            logger,
            all_rulesets,
        )
        _transform_wato_ruleset_mail_queue_length(
            logger,
            all_rulesets,
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
        _transform_remove_null_host_tag_conditions_from_rulesets(
            logger,
            all_rulesets,
            raise_errors=debug.enabled(),
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


def transform_condition_labels_to_label_groups(
    conditions: dict[str, Any],
) -> dict[str, Any]:
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
    deprecated_ruleset_patterns: Sequence[Pattern],
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


def _transform_wato_ruleset_memory_simple(
    logger: Logger,
    all_rulesets: RulesetCollection,
) -> None:
    """Update the rulesets according to Werk #16277.

    Relevant for 2.2 -> 2.3.
    """
    if (old_ruleset := all_rulesets.get("checkgroup_parameters:memory_simple")).is_empty():
        return

    if not (
        new_ruleset := all_rulesets.get("checkgroup_parameters:memory_simple_single")
    ).is_empty():
        return

    for folder, _folder_index, rule in old_ruleset.get_rules():
        if _memory_simple_matches_single(rule.conditions):
            new_ruleset.append_rule(folder, rule)


def _memory_simple_matches_single(conditions: RuleConditions) -> bool:
    """Decide if the rule used to match the items `""` and `"System"`.

    We consider the case of an empty string as conditions here -- even
    though as far as I can see it can't be configured.
    """
    match conditions.service_description:
        case None:
            return True
        case list() as conds:
            regexes = [r for cond in conds if (r := cond.get("$regex")) is not None]
            return any(r == "" or match(r, "System") for r in regexes)
        case dict() as conds:
            regexes = [r for cond in conds["$nor"] if (r := cond.get("$regex")) is not None]
            return not any(r == "" or match(r, "System") for r in regexes)


def _transform_wato_ruleset_mail_queue_length(
    logger: Logger,
    all_rulesets: RulesetCollection,
) -> None:
    """Update the rulesets according to Werk #16261.

    Relevant for 2.2 -> 2.3.
    """
    if (old_ruleset := all_rulesets.get("checkgroup_parameters:mail_queue_length")).is_empty():
        return

    if not (
        new_ruleset := all_rulesets.get("checkgroup_parameters:mail_queue_length_single")
    ).is_empty():
        return

    for folder, _folder_index, rule in old_ruleset.get_rules():
        if _mail_queue_matches_single(rule.conditions):
            new_ruleset.append_rule(folder, rule)


def _mail_queue_matches_single(conditions: RuleConditions) -> bool:
    """Decide if the rule used to match the item `""`.

    We consider the case of an empty string as conditions here -- even
    though as far as I can see it can't be configured.
    """
    match conditions.service_description:
        case None:
            return True
        case list() as conds:
            regexes = [r for cond in conds if (r := cond.get("$regex")) is not None]
            return any(r == "" for r in regexes)
        case dict() as conds:
            regexes = [r for cond in conds["$nor"] if (r := cond.get("$regex")) is not None]
            return not any(r == "" for r in regexes)


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
        try:
            valuespec = ruleset.valuespec()
        except Exception:
            logger.error(
                "ERROR: Failed to load Ruleset: %s. "
                "There is likely an error in the implementation.",
                ruleset.name,
            )
            logger.exception("This is the exception: ")
            continue
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
        "snmp_exclude_sections",  # same as "ignored_checks".
        "snmp_check_interval",  # same as "ignored_checks".
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
                    index,
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


def _filter_out_null_host_tags(
    host_tags: Mapping[TagGroupID, TagCondition],
) -> dict[TagGroupID, TagCondition]:
    filtered_host_tags: dict[TagGroupID, TagCondition] = {}

    for tag_group, tag_id in host_tags.items():
        match tag_id:
            case {"$ne": cond} | {"$or": cond} | {"$nor": cond} | cond if cond is None:
                continue
            case _:
                filtered_host_tags[tag_group] = tag_id

    return filtered_host_tags


def _transform_remove_null_host_tag_conditions_from_rulesets(
    logger: Logger,
    all_rulesets: RulesetCollection,
    raise_errors: bool = False,
) -> Collection[RulesetName]:
    migrated_rulesets = set()
    for ruleset in all_rulesets.get_rulesets().values():
        for folder, folder_index, old_rule in ruleset.get_rules():
            host_tags = old_rule.get_rule_conditions().host_tags
            filtered_host_tags = _filter_out_null_host_tags(host_tags)
            null_tag_groups = host_tags.keys() - filtered_host_tags.keys()

            if not null_tag_groups:
                continue

            try:
                logger.warning(
                    "WARNING: Removing null host tag condition: rule=%s(id=%s), tag_groups=%s",
                    ruleset.name,
                    old_rule.id,
                    null_tag_groups,
                )

                new_conditions = {"host_tags": {**filtered_host_tags}}
                new_rule_conditions = RuleConditions.from_config(folder.name(), new_conditions)
                new_rule = old_rule.clone(preserve_id=True)
                new_rule.update_conditions(new_rule_conditions)

                ruleset.edit_rule(old_rule, new_rule)
                migrated_rulesets.add(ruleset.name)
            except Exception as e:
                if raise_errors:
                    raise
                logger.error(
                    "ERROR: Failed to transform rule: (Ruleset: %s, Folder: %s, "
                    "Rule: %d, Value: %s: %s",
                    ruleset.name,
                    folder.path(),
                    folder_index,
                    old_rule.value,
                    e,
                )
    return migrated_rulesets
