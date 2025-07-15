#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import re
from collections.abc import Collection, Iterable, Mapping, Sequence
from logging import Logger
from typing import Final

from cmk.ccc import debug

from cmk.utils.log import VERBOSE
from cmk.utils.rulesets.definition import RuleGroup
from cmk.utils.rulesets.ruleset_matcher import RulesetName, TagCondition
from cmk.utils.tags import TagGroupID

from cmk.base import config

from cmk.gui.watolib.hosts_and_folders import folder_tree
from cmk.gui.watolib.rulesets import (
    AllRulesets,
    FolderPath,
    Rule,
    RuleConditions,
    RulesetCollection,
)

REPLACED_RULESETS: Mapping[RulesetName, RulesetName] = {
    "entersekt_soaprrors": "entersekt_soaperrors",  # 2.4 -> 2.5
}

RULESETS_LOOSING_THEIR_ITEM: Iterable[RulesetName] = {}

DEPRECATED_RULESET_PATTERNS = (re.compile("^agent_simulator$"),)

SKIP_ACTION: Final = {
    # the valid choices for this ruleset are user-dependent (SLAs) and not even an admin can
    # see all of them
    RuleGroup.ExtraServiceConf("_sla_config"),
    # Validating the ignored checks ruleset does not make sense:
    # Invalid choices are the plugins that don't exist (anymore).
    # These do no harm, they are dropped upon rule edit. On the other hand, the plugin
    # could be missing only temporarily, so better not remove it.
    "ignored_checks",
    "snmp_exclude_sections",  # same as "ignored_checks".
}

SKIP_PREACTION: Final = SKIP_ACTION | {
    # validating a ruleset for static checks, where we want to replace the ruleset anyway,
    # does not work:
    # * the validation checks if there are checks which subscribe to that check group
    # * when replacing a ruleset, we have no check anymore subscribing to the old name
    # * in that case, the validation will always fail, so we skip it during update
    # * the rule validation with the replaced ruleset will happen after the replacing anyway again
    # see cmk.update_config.plugins.actions.rulesets._validate_rule_values
    *{ruleset for ruleset in REPLACED_RULESETS if ruleset.startswith("static_checks:")},
}


def load_and_transform(logger: Logger) -> AllRulesets:
    all_rulesets = AllRulesets.load_all_rulesets()

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
    transform_wato_rulesets_params(
        logger,
        all_rulesets,
        raise_errors=debug.enabled(),
    )
    transform_remove_null_host_tag_conditions_from_rulesets(
        logger,
        all_rulesets,
        raise_errors=debug.enabled(),
    )
    return all_rulesets


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
    if (
        not all_rulesets.exists("active_checks:http")
        or (http_ruleset := all_rulesets.get("active_checks:http")).is_empty()
    ):
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


def transform_wato_rulesets_params(
    logger: Logger,
    all_rulesets: RulesetCollection,
    raise_errors: bool = False,
) -> Collection[RulesetName]:
    migrated_rulesets = set()
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
                    rule.value,
                    e,
                )
    return migrated_rulesets


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


def transform_remove_null_host_tag_conditions_from_rulesets(
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
