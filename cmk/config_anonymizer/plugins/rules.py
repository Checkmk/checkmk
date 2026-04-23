#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import logging
import re
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any

from cmk.base.app import make_app
from cmk.base.config import AutochecksConfigurer, load, load_all_plugins
from cmk.base.configlib.servicename import (
    make_final_service_name_config,
    make_passive_service_name_config,
)
from cmk.ccc import store
from cmk.ccc.site import omd_site
from cmk.ccc.version import edition
from cmk.checkengine.discovery import AutochecksStore
from cmk.checkengine.plugin_backend import extract_known_discovery_rulesets, get_check_plugin
from cmk.checkengine.plugins import AutocheckEntry
from cmk.checkengine.plugins._check import CheckPlugin, CheckPluginName
from cmk.config_anonymizer.interface import AnonInterface
from cmk.config_anonymizer.step import AnonymizeStep
from cmk.gui.config import Config
from cmk.gui.watolib.hosts_and_folders import Folder, folder_tree
from cmk.gui.watolib.rulesets import (
    _FOLDER_PATH_MACRO,
    AllRulesets,
    Rule,
    RuleConditions,
    RuleConfigFile,
    RuleOptions,
    Ruleset,
    RulesetCollection,
)
from cmk.gui.watolib.tags import load_tag_config_read_only
from cmk.gui.watolib.utils import wato_root_dir
from cmk.utils import paths
from cmk.utils.global_ident_type import GlobalIdent
from cmk.utils.labels import LabelGroups, Labels
from cmk.utils.rulesets.conditions import (
    HostOrServiceConditionRegex,
    HostOrServiceConditions,
)
from cmk.utils.rulesets.definition import RuleGroup
from cmk.utils.rulesets.ruleset_matcher import (
    RuleSpec,
    TagCondition,
)
from cmk.utils.tags import BuiltinTagConfig, TagGroupID, TagID


class AnonymizedAllRulesets(AllRulesets):
    def __init__(self, anon_interface: AnonInterface) -> None:
        """Load all rules of all folders"""
        rulesets = RulesetCollection._initialize_rulesets()
        super().__init__(rulesets)
        self._load_rulesets_recursively(folder_tree().root_folder())
        self._anon_interface = anon_interface
        self._unknown_rulesets = {}

    def save_anon_rulesets(self, pprint_value: bool) -> None:
        """Save all rulesets of all folders recursively"""
        self._save_anon_rulesets_recursively(folder_tree().root_folder(), pprint_value=pprint_value)

    def _save_anon_rulesets_recursively(self, folder: Folder, pprint_value: bool) -> None:
        for subfolder in folder.subfolders():
            self._save_anon_folder(
                subfolder, self._rulesets, self._unknown_rulesets, pprint_value=pprint_value
            )
        self._save_anon_folder(
            folder, self._rulesets, self._unknown_rulesets, pprint_value=pprint_value
        )

    def _save_anon_folder(
        self,
        folder: Folder,
        rulesets: dict[str, Ruleset],
        unknown_rulesets: Mapping[str, Mapping[str, Sequence[RuleSpec[object]]]],
        pprint_value: bool,
    ) -> None:
        content = RuleConfigFile.get_content_for_rules_file(
            folder, rulesets, unknown_rulesets, pprint_value
        )
        folders_path = (
            str(folder.rules_file_path())
            .removeprefix(str(wato_root_dir()))
            .removesuffix("rules.mk")
        )
        anon_folders_path = self._anon_interface.get_folder_path(folders_path)
        anon_file_path = self._anon_interface.relative_to_anon_dir(
            Path(f"{wato_root_dir()}{anon_folders_path}/rules.mk")
        )
        anon_file_path.parent.mkdir(mode=0o770, exist_ok=True, parents=True)

        # Remove empty rules files. This prevents needless reads
        if not content:
            anon_file_path.unlink(missing_ok=True)
            return
        store.save_mk_file(
            anon_file_path,
            # Adding this instead of the full path makes it easy to move config
            # files around. The real FOLDER_PATH will be added dynamically while
            # loading the file in cmk.base.config
            "".join(content).replace("'%s'" % _FOLDER_PATH_MACRO, "'/%s/' % FOLDER_PATH"),
        )


def _anonymize_tag_condition(
    tag_condition: TagCondition, tag_anonymizer: Callable[[str], str]
) -> TagCondition:
    match tag_condition:
        case None:
            return tag_condition
        case str():
            return TagID(tag_anonymizer(tag_condition))
        case {"$ne": str() | None as condition_value}:
            if condition_value is None:
                return None
            return {"$ne": TagID(tag_anonymizer(condition_value))}
        case {"$or": list(tags)}:
            return {"$or": [None if tag is None else TagID(tag_anonymizer(tag)) for tag in tags]}
        case {"$nor": list(tags)}:
            return {"$nor": [None if tag is None else TagID(tag_anonymizer(tag)) for tag in tags]}
        case _:
            raise ValueError(f"Unknown tag condition type: {tag_condition}")


def _anonymize_service_condition(
    condition: HostOrServiceConditionRegex | str,
    ruleset: Ruleset,
    rule_folder: Folder,
    all_service_descriptions: Mapping[str, tuple[str, Any, str]],
    plugins: Mapping[CheckPluginName, CheckPlugin],
    anon_interface: AnonInterface,
) -> HostOrServiceConditionRegex | str:
    rule_folder_hosts = rule_folder.all_hosts_recursively()
    match condition:
        case {"$regex": str(regex_value)}:
            match regex_value:
                case ".*":
                    return condition
                case _:
                    match ruleset.rulespec.item_type:
                        case "service":
                            anonymized_service_descriptions = set()
                            for discovered_service_description, (
                                anonymized_service_description,
                                entry,
                                host,
                            ) in all_service_descriptions.items():
                                if (
                                    re.match(regex_value, discovered_service_description)
                                    and host in rule_folder_hosts.keys()
                                ):
                                    anonymized_service_descriptions.add(
                                        f"^{anonymized_service_description}$"
                                    )

                            if not anonymized_service_descriptions:
                                # if nothing matched, return a regex that matches nothing
                                return {"$regex": "$^"}
                            anon_regex = "|".join(anonymized_service_descriptions)
                            return {"$regex": anon_regex}
                        case "item":
                            # entry1.check_plugin_name -> CheckPlugin1 -> CheckPlugin1.ruleset_reference == ruleset.name  -> entry1.item
                            # entry2.check_plugin_name -> CheckPlugin2 -> CheckPlugin2.ruleset_reference == ruleset.name  -> entry2.item
                            # for all "worthy" items
                            # if re.match(regex_value, entry.item):
                            #   anonymize item and return regex of anonymized items
                            matched_items = set()
                            for discovered_service_description, (
                                anonymized_service_description,
                                entry,
                                host,
                            ) in all_service_descriptions.items():
                                check_plugin = get_check_plugin(entry.check_plugin_name, plugins)
                                if (
                                    check_plugin is not None
                                    and RuleGroup.CheckgroupParameters(
                                        check_plugin.check_ruleset_name
                                    )
                                    == ruleset.name
                                    and host in rule_folder_hosts.keys()
                                ):
                                    if re.match(regex_value, entry.item):
                                        matched_items.add(
                                            f"^{anon_interface.get_item(entry.item)}$"
                                        )
                            if not matched_items:
                                # if nothing matched, return a regex that matches nothing
                                return {"$regex": "$^"}
                            anon_regex = "|".join(matched_items)
                            return {"$regex": anon_regex}
                        case other:
                            raise ValueError(
                                f"Unknown ruleset item type for regex service description condition: {other}"
                            )

        case str():
            raise ValueError("Explicit option should only be used for host matching")
        case _:
            raise ValueError(f"Unknown service condition item type: {condition}")


def _anonymize_service_description(
    service_conditions: HostOrServiceConditions | None,
    ruleset: Ruleset,
    rule_folder: Folder,
    all_service_descriptions: Mapping[str, tuple[str, Any, str]],
    plugins: Mapping[CheckPluginName, CheckPlugin],
    anon_interface: AnonInterface,
) -> HostOrServiceConditions | None:
    match service_conditions:
        case None:
            return None
        case {"$nor": list(items)}:
            return {
                "$nor": [
                    _anonymize_service_condition(
                        item,
                        ruleset,
                        rule_folder,
                        all_service_descriptions,
                        plugins,
                        anon_interface,
                    )
                    for item in items
                ]
            }
        case list(items):
            return [
                _anonymize_service_condition(
                    item, ruleset, rule_folder, all_service_descriptions, plugins, anon_interface
                )
                for item in items
            ]
        case _:
            raise ValueError(f"Unknown service description type: {service_conditions}")


def _anonymize_host_condition(
    condition: HostOrServiceConditionRegex | str, rule_folder: Folder, anon_interface: AnonInterface
) -> HostOrServiceConditionRegex | str:
    match condition:
        case {"$regex": str(regex_value)}:
            match regex_value:
                case ".*":
                    return condition
                case _:
                    anonymized_matched_host_names = set()
                    for host_name in rule_folder.all_hosts_recursively().keys():
                        if re.match(regex_value, host_name):
                            anonymized_matched_host_names.add(
                                f"^{anon_interface.get_host(host_name)}$"
                            )
                    if not anonymized_matched_host_names:
                        # if nothing matched, return a regex that matches nothing
                        return {"$regex": "$^"}
                    anon_regex = "|".join(anonymized_matched_host_names)
                    return {"$regex": anon_regex}
        case str():
            return anon_interface.get_host(condition)
        case _:
            raise ValueError(f"Unknown host name condition type: {condition}")


def _anonymize_host_name(
    host_name: HostOrServiceConditions | None,
    rule_folder: Folder,
    anon_interface: AnonInterface,
) -> HostOrServiceConditions | None:
    match host_name:
        case None:
            return None
        case {"$nor": list(items)}:
            return {
                "$nor": [
                    _anonymize_host_condition(item, rule_folder, anon_interface) for item in items
                ]
            }
        case list(items):
            return [_anonymize_host_condition(item, rule_folder, anon_interface) for item in items]
        case _:
            raise ValueError(f"Unknown host name type: {host_name}")


def _anonymize_label_group(
    label_groups: LabelGroups | None,
    builtin_host_labels: Labels,
    anon_interface: AnonInterface,
    anon_label_groups_call: Callable[[str, str], tuple[str, str]],
) -> LabelGroups | None:
    if label_groups is None:
        return None

    anon_label_groups = []

    for and_operator, label_group_blocks in label_groups:
        anon_label_group_block = []
        for condition_operator, label_group in label_group_blocks:
            # from cmk.gui.watolib.sample_config._constants._CMK_SERVER_CONDITION
            if label_group == "":
                anon_label_group_block.append((condition_operator, label_group))
                continue
            label_key, label_value = label_group.split(":", maxsplit=1)

            if label_key in builtin_host_labels:
                anon_label_key = label_key
                match label_key:
                    case "cmk/site":
                        anon_label_value = anon_interface.get_site(label_value)
                    case "cmk/customer":
                        anon_label_value = anon_interface.get_customer(label_value)
                    case _:
                        raise ValueError(f"Unknown built-in label key: {label_key}")
                anon_label_group_block.append(
                    (condition_operator, f"{anon_label_key}:{anon_label_value}")
                )
            else:
                anon_label_key, anon_label_value = anon_label_groups_call(label_key, label_value)
                anon_label_group_block.append(
                    (condition_operator, f"{anon_label_key}:{anon_label_value}")
                )
        anon_label_groups.append((and_operator, anon_label_group_block))

    return anon_label_groups


def _anonymize_rule(
    rule: Rule,
    rule_folder: Folder,
    builtin_tag_config: BuiltinTagConfig,
    builtin_host_labels: Labels,
    all_service_descriptions: Mapping[str, tuple[str, Any, str]],
    plugins: Mapping[CheckPluginName, CheckPlugin],
    anon_interface: AnonInterface,
) -> None:
    """Anonymize a single rule in place"""

    anon_host_tags = {}
    custom_tag_config = load_tag_config_read_only()

    for k, v in rule.conditions.host_tags.items():
        if builtin_tag_config.tag_group_exists(k):
            anon_host_tags[k] = v
            continue  # do not anonymize built-in tags

        if TagID(k) in custom_tag_config.aux_tag_list.get_tag_ids():
            anon_group_id = anon_interface.get_id_of_aux_tag(k)
            anon_host_tags[TagGroupID(anon_group_id)] = _anonymize_tag_condition(
                v, anon_interface.get_id_of_aux_tag
            )
            continue

        if custom_tag_config.tag_group_exists(k):
            anon_group_id = anon_interface.get_id_of_tag_group(k)
            anon_host_tags[TagGroupID(anon_group_id)] = _anonymize_tag_condition(
                v, anon_interface.get_id_of_tag
            )
            continue

    anon_conditions = RuleConditions(
        host_folder=anon_interface.get_rule_folder_path(rule.conditions.host_folder),
        host_tags=anon_host_tags,
        host_name=_anonymize_host_name(rule.conditions.host_name, rule_folder, anon_interface),
        service_description=_anonymize_service_description(
            rule.conditions.service_description,
            rule.ruleset,
            rule_folder,
            all_service_descriptions,
            plugins,
            anon_interface,
        ),
        host_label_groups=_anonymize_label_group(
            rule.conditions.host_label_groups,
            builtin_host_labels,
            anon_interface,
            anon_interface.get_host_label_groups,
        ),
        service_label_groups=_anonymize_label_group(
            rule.conditions.service_label_groups,
            {},
            anon_interface,
            anon_interface.get_service_label_groups,
        ),
    )

    rule.conditions = anon_conditions
    # TODO: anonymize rule value actually instead voiding it @AB
    rule.value = {"voided": "by_config_anonymizer"}
    rule.rule_options = RuleOptions(
        disabled=rule.rule_options.disabled,
        description=anon_interface.get_generic_mapping(rule.rule_options.description, "other")
        if rule.rule_options.description
        else "",
        comment=anon_interface.get_generic_mapping(rule.rule_options.comment, "other")
        if rule.rule_options.comment
        else "",
        docu_url=anon_interface.get_url(rule.rule_options.docu_url)
        if rule.rule_options.docu_url
        else "",
        predefined_condition_id=None,
    )
    if rule.locked_by is not None:
        site_id = rule.locked_by["site_id"]
        program_id = rule.locked_by["program_id"]
        program_instance_id = rule.locked_by["instance_id"]
        rule.locked_by = GlobalIdent(
            site_id=anon_interface.get_site(site_id),
            program_id=program_id,
            instance_id=anon_interface.get_generic_mapping(
                program_instance_id,
                "program_instance_id",
            ),
        )


class RulesStep(AnonymizeStep):
    def run(
        self, anon_interface: AnonInterface, active_config: Config, logger: logging.Logger
    ) -> None:
        logger.warning("Processing rules")

        # Load rulesets
        anonymized_all_rulesets = AnonymizedAllRulesets(anon_interface)

        builtin_ids = BuiltinTagConfig()
        builtin_host_labels_callable = make_app(edition(paths.omd_root)).get_builtin_host_labels
        builtin_host_labels = builtin_host_labels_callable(omd_site())

        all_plugins = load_all_plugins()

        # TODO pass in loaded_config_result
        loaded_config_result = load(
            discovery_rulesets=extract_known_discovery_rulesets(all_plugins),
            get_builtin_host_labels=builtin_host_labels_callable,
            edition=edition(paths.omd_root),
            with_conf_d=True,
            validate_hosts=False,
        )

        make_final_service_name_config(
            loaded_config=loaded_config_result.loaded_config,
            matcher=loaded_config_result.config_cache.ruleset_matcher,
        )

        passive_service_name_config = make_passive_service_name_config(
            loaded_config=loaded_config_result.loaded_config,
            matcher=loaded_config_result.config_cache.ruleset_matcher,
            label_manager=loaded_config_result.config_cache.label_manager,
        )

        autochecks_config = AutochecksConfigurer(
            loaded_config_result.config_cache,
            all_plugins.check_plugins,
            passive_service_name_config,
        )

        # TODO optimize by moving anonymization into the _anonymize_rule
        all_service_descriptions = {}
        for folder_rel_path, folder in folder_tree().all_folders().items():
            for host in folder.hosts():
                for entry in AutochecksStore(host).read():
                    discovered_service_description = autochecks_config.service_description(
                        host, entry
                    )

                    anonymized_item = AutocheckEntry(
                        check_plugin_name=entry.check_plugin_name,
                        item=anon_interface.get_item(entry.item)
                        if entry.item is not None
                        else None,
                        parameters=entry.parameters,
                        service_labels=entry.service_labels,
                    )
                    anonymized_service_description = autochecks_config.service_description(
                        host, anonymized_item
                    )
                    all_service_descriptions[discovered_service_description] = (
                        anonymized_service_description,
                        entry,
                        host,
                    )

        for ruleset_name, ruleset in anonymized_all_rulesets.get_rulesets().items():
            for _rule_folder, _rule_index, rule in ruleset.get_rules():
                _anonymize_rule(
                    rule,
                    _rule_folder,
                    builtin_ids,
                    builtin_host_labels,
                    all_service_descriptions,
                    all_plugins.check_plugins,
                    anon_interface,
                )

        anonymized_all_rulesets.save_anon_rulesets(pprint_value=True)


anonymize_step_rules = RulesStep()
