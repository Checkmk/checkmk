#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Helper functions for dealing with host tags"""

import abc
from collections.abc import Mapping, Sequence
from enum import Enum
from typing import Any, override, TypeVar

from cmk.ccc import store
from cmk.ccc.exceptions import MKGeneralException
from cmk.ccc.i18n import _

import cmk.utils.paths
import cmk.utils.tags
from cmk.utils.rulesets.ruleset_matcher import TagCondition
from cmk.utils.tags import BuiltinTagConfig, TagConfig, TagConfigSpec, TagGroup, TagGroupID, TagID

from cmk.gui import hooks
from cmk.gui.config import load_config
from cmk.gui.exceptions import MKAuthException
from cmk.gui.hooks import request_memoize
from cmk.gui.logged_in import user
from cmk.gui.watolib.hosts_and_folders import Folder, folder_tree, Host
from cmk.gui.watolib.php_formatter import format_php
from cmk.gui.watolib.rulesets import AllRulesets, Rule, RuleConditions, Ruleset
from cmk.gui.watolib.simple_config_file import ConfigFileRegistry, WatoSingleConfigFile
from cmk.gui.watolib.utils import multisite_dir, wato_root_dir


class TagConfigFile(WatoSingleConfigFile[TagConfigSpec]):
    """Handles loading the tag definitions from GUI tags.mk

    When saving the configuration it also writes out the tags.mk for the cmk.base world.
    """

    def __init__(self) -> None:
        super().__init__(
            config_file_path=multisite_dir() / "tags.mk",
            config_variable="wato_tags",
            spec_class=TagConfigSpec,
        )

    @override
    def _load_file(self, *, lock: bool) -> TagConfigSpec:
        # NOTE: Typing chaos...
        default: TagConfigSpec = {}  # type: ignore[typeddict-item]
        cfg = store.load_from_mk_file(
            self._config_file_path,
            key=self._config_variable,
            default=default,
            lock=lock,
        )
        if not cfg:
            cfg = {"tag_groups": [], "aux_tags": []}

        return cfg

    @override
    def save(self, cfg: TagConfigSpec, pprint_value: bool) -> None:
        self._save_gui_config(cfg, pprint_value)
        self._save_base_config(cfg, pprint_value)
        _export_hosttags_to_php(cfg)

    def _save_gui_config(self, cfg: TagConfigSpec, pprint_value: bool) -> None:
        super().save(cfg, pprint_value)

    def _save_base_config(self, cfg: TagConfigSpec, pprint_value: bool) -> None:
        self._config_file_path.parent.mkdir(mode=0o770, exist_ok=True, parents=True)
        store.save_to_mk_file(
            wato_root_dir() / "tags.mk", key="tag_config", value=cfg, pprint_value=pprint_value
        )


def register(config_file_registry: ConfigFileRegistry) -> None:
    config_file_registry.register(TagConfigFile())


def load_tag_config() -> TagConfig:
    """Load the tag config object based upon the most recently saved tag config file"""
    return TagConfig.from_config(TagConfigFile().load_for_modification())


def load_tag_config_read_only() -> TagConfig:
    return TagConfig.from_config(TagConfigFile().load_for_reading())


def load_all_tag_config_read_only() -> TagConfig:
    """Load the tag config + the built in tag config.  Read Only"""
    tag_config = load_tag_config_read_only()
    tag_config += BuiltinTagConfig()
    return tag_config


def update_tag_config(tag_config: TagConfig, pprint_value: bool) -> None:
    """Persist the tag config saving the information to the mk file
    and update the current environment

    Args:
        tag_config:
            The tag config object to persist

    """
    user.need_permission("wato.hosttags")
    TagConfigFile().save(tag_config.get_dict_format(), pprint_value)
    _update_tag_dependencies(pprint_value=pprint_value)
    hooks.call("tags-changed")


def load_tag_group(ident: TagGroupID) -> TagGroup | None:
    """Load a tag group

    Args:
        ident:
            identifier of the tag group

    """
    tag_config = load_tag_config()
    tag_config += BuiltinTagConfig()
    return tag_config.get_tag_group(ident)


def save_tag_group(tag_group: TagGroup, pprint_value: bool) -> None:
    """Save a new tag group

    Args:
        tag_group:
            the tag group object

    """
    tag_config = load_tag_config()
    tag_config.insert_tag_group(tag_group)
    tag_config.validate_config()
    update_tag_config(tag_config, pprint_value)


def is_builtin(ident: TagGroupID) -> bool:
    """Verify if a tag group is a built-in"""
    user.need_permission("wato.hosttags")
    return BuiltinTagConfig().tag_group_exists(ident)


def tag_group_exists(ident: TagGroupID, builtin_included: bool = False) -> bool:
    """Verify if a tag group exists"""
    tag_config = load_tag_config()
    if builtin_included:
        tag_config += BuiltinTagConfig()
    return tag_config.tag_group_exists(ident)


def _update_tag_dependencies(*, pprint_value: bool) -> None:
    load_config()
    tree = folder_tree()
    tree.invalidate_caches()
    tree.root_folder().recursively_save_hosts(pprint_value=pprint_value)


class RepairError(MKGeneralException):
    pass


def edit_tag_group(
    ident: TagGroupID,
    edited_group: TagGroup,
    allow_repair: bool,
    pprint_value: bool,
    debug: bool,
) -> None:
    """Update attributes of a tag group & update the relevant positions which used the relevant tag group

    Args:
        ident:
            the identifier of the tag group to be updated

        edited_group:
            the tag group which represents the edited version; this tag group object will replace
            the current object

        allow_repair:
            some modifications require repair on host and folder levels. This must
    """
    tag_config = load_tag_config()
    current_tag_group = tag_config.get_tag_group(tag_group_id=ident)
    if current_tag_group is None:
        raise MKGeneralException("Group tag to modify does not exist")
    tag_ids_to_remove, tag_ids_to_replace = identify_modified_tags(edited_group, current_tag_group)
    tag_config.update_tag_group(edited_group)
    tag_config.validate_config()
    operation = OperationReplaceGroupedTags(ident, tag_ids_to_remove, tag_ids_to_replace)
    affected = change_host_tags(
        operation, TagCleanupMode.CHECK, pprint_value=pprint_value, debug=debug
    )
    if any(affected):
        if not allow_repair:
            raise RepairError("Permission missing")
        _ = change_host_tags(
            operation,
            TagCleanupMode("repair"),
            pprint_value=pprint_value,
            debug=debug,
        )
    update_tag_config(tag_config, pprint_value)


def identify_modified_tags(
    updated_group: TagGroup, old_group: TagGroup
) -> tuple[list[TagID], dict[TagID | None, TagID | None]]:
    """Identify which ids were changed and which ids are to be deleted

    Example:

    >>> _old_group = TagGroup.from_config({
    ...    'id': 'foo',
    ...    'title': 'foobar',
    ...    'tags': [{
    ...        'id': 'tester',
    ...        'title': 'something',
    ...        'aux_tags': []
    ...    }],
    ...    'topic': 'nothing'
    ... })
    >>> _updated_group = TagGroup.from_config({
    ...    'id': 'foo',
    ...    'title': 'foobar',
    ...    'tags': [{
    ...        'id': 'tutu',
    ...        'title': 'something',
    ...        'aux_tags': []
    ...    }],
    ...    'topic': 'nothing'
    ... })
    >>> identify_modified_tags(_updated_group, _old_group)
    ([], {'tester': 'tutu'})

    """
    # TODO: update GUI help highlighting that title and id should not be changed at the same time
    remove_tag_ids, replace_tag_ids = [], {}
    new_by_title = {tag.title: tag.id for tag in updated_group.tags}
    for former_tag in old_group.tags:
        # Detect renaming
        if former_tag.title in new_by_title:
            new_id = new_by_title[former_tag.title]
            if new_id != former_tag.id:
                # new_id may be None
                replace_tag_ids[former_tag.id] = new_id
                continue

        # Detect removal
        if former_tag.id is not None and former_tag.id not in [
            tmp_tag.id for tmp_tag in updated_group.tags
        ]:
            # remove explicit tag (hosts/folders) or remove it from tag specs (rules)
            remove_tag_ids.append(former_tag.id)
    return remove_tag_ids, replace_tag_ids


class TagCleanupMode(Enum):
    ABORT = "abort"  # No further action. Aborting here.
    CHECK = "check"  # only affected rulesets are collected, nothing is modified
    DELETE = "delete"  # Rules using this tag are deleted
    REMOVE = "remove"  # Remove tags from rules
    REPAIR = "repair"  # Remove tags from rules


class ABCOperation(abc.ABC):
    """Base for all tag cleanup operations"""

    @abc.abstractmethod
    def confirm_title(self) -> str:
        raise NotImplementedError()


class ABCTagGroupOperation(ABCOperation, abc.ABC):
    def __init__(self, tag_group_id: TagGroupID) -> None:
        super().__init__()
        self.tag_group_id = tag_group_id


class OperationRemoveTagGroup(ABCTagGroupOperation):
    def confirm_title(self) -> str:
        return _("Confirm tag group deletion")


class OperationRemoveAuxTag(ABCTagGroupOperation):
    def confirm_title(self) -> str:
        return _("Confirm aux tag deletion")


class OperationReplaceGroupedTags(ABCOperation):
    def __init__(
        self,
        tag_group_id: TagGroupID,
        remove_tag_ids: Sequence[TagID | None],
        replace_tag_ids: Mapping[TagID | None, TagID | None],
    ) -> None:
        super().__init__()
        self.tag_group_id = tag_group_id
        self.remove_tag_ids = remove_tag_ids
        self.replace_tag_ids = replace_tag_ids

    def confirm_title(self) -> str:
        return _("Confirm tag modifications")


def change_host_tags(
    operation: ABCTagGroupOperation | OperationReplaceGroupedTags,
    mode: TagCleanupMode,
    *,
    pprint_value: bool,
    debug: bool,
) -> tuple[list[Folder], list[Host], list[Ruleset]]:
    affected_folder, affected_hosts = _change_host_tags_in_folders(
        operation, mode, folder_tree().root_folder(), pprint_value=pprint_value
    )

    affected_rulesets = _change_host_tags_in_rulesets(
        operation, mode, pprint_value=pprint_value, debug=debug
    )
    return affected_folder, affected_hosts, affected_rulesets


@request_memoize()
def _get_all_rulesets() -> AllRulesets:
    return cmk.gui.watolib.rulesets.AllRulesets.load_all_rulesets()


def _change_host_tags_in_rulesets(
    operation: ABCTagGroupOperation | OperationReplaceGroupedTags,
    mode: TagCleanupMode,
    *,
    pprint_value: bool,
    debug: bool,
) -> list[Ruleset]:
    affected_rulesets = set()
    all_rulesets = _get_all_rulesets()
    for ruleset in all_rulesets.get_rulesets().values():
        for _folder, _rulenr, rule in ruleset.get_rules():
            affected_rulesets.update(_change_host_tags_in_rule(operation, mode, ruleset, rule))

    if mode != TagCleanupMode.CHECK:
        all_rulesets.save(pprint_value=pprint_value, debug=debug)

    return sorted(affected_rulesets, key=lambda x: x.title() or "")


def _change_host_tags_in_folders(
    operation: ABCTagGroupOperation | OperationReplaceGroupedTags,
    mode: TagCleanupMode,
    folder: Any,
    *,
    pprint_value: bool,
) -> tuple[list[Folder], list[Host]]:
    """Update host tag assignments in hosts/folders

    See _rename_tags_after_confirmation() doc string for additional information.
    """
    affected_folders = []
    affected_hosts = []

    if not isinstance(operation, OperationRemoveAuxTag):
        aff_folders = _change_host_tags_in_host_or_folder(operation, mode, folder)
        affected_folders += aff_folders

        if aff_folders and mode != TagCleanupMode.CHECK:
            try:
                folder.save()
            except MKAuthException:
                # Ignore MKAuthExceptions of locked host.mk files
                pass

        for subfolder in folder.subfolders():
            aff_folders, aff_hosts = _change_host_tags_in_folders(
                operation, mode, subfolder, pprint_value=pprint_value
            )
            affected_folders += aff_folders
            affected_hosts += aff_hosts

        affected_hosts += _change_host_tags_in_hosts(
            operation, mode, folder, pprint_value=pprint_value
        )

    return affected_folders, affected_hosts


def _change_host_tags_in_hosts(
    operation: ABCTagGroupOperation | OperationReplaceGroupedTags,
    mode: TagCleanupMode,
    folder: Folder,
    *,
    pprint_value: bool,
) -> list[Host]:
    affected_hosts = []
    for host in folder.hosts().values():
        aff_hosts = _change_host_tags_in_host_or_folder(operation, mode, host)
        affected_hosts += aff_hosts

    if affected_hosts and mode != TagCleanupMode.CHECK:
        try:
            folder.save_hosts(pprint_value=pprint_value)
        except MKAuthException:
            # Ignore MKAuthExceptions of locked host.mk files
            pass
    return affected_hosts


T = TypeVar("T", Folder, Host)


def _change_host_tags_in_host_or_folder(
    operation: ABCTagGroupOperation | OperationReplaceGroupedTags,
    mode: TagCleanupMode,
    host_or_folder: T,
) -> list[T]:
    affected: list[T] = []

    attrname = "tag_" + operation.tag_group_id
    attributes = host_or_folder.attributes
    if attrname not in attributes:
        return affected  # The attribute is not set

    # Deletion of a tag group
    if isinstance(operation, OperationRemoveTagGroup):
        if attrname in attributes:
            affected.append(host_or_folder)
            if mode != TagCleanupMode.CHECK:
                # Mypy can not help here with the dynamic key access
                del attributes[attrname]  # type: ignore[misc]
        return affected

    if not isinstance(operation, OperationReplaceGroupedTags):
        raise NotImplementedError()

    # Deletion or replacement of a tag choice
    # Mypy can not help here with the dynamic key access
    current = attributes[attrname]  # type: ignore[literal-required]
    if current in operation.remove_tag_ids or current in operation.replace_tag_ids:
        affected.append(host_or_folder)
        if mode != TagCleanupMode.CHECK:
            if current in operation.remove_tag_ids:
                # Mypy can not help here with the dynamic key access
                del attributes[attrname]  # type: ignore[misc]
            elif current in operation.replace_tag_ids:
                new_tag = operation.replace_tag_ids[current]
                # Mypy can not help here with the dynamic key access
                attributes[attrname] = new_tag  # type: ignore[literal-required]
            else:
                raise NotImplementedError()

    return affected


def _change_host_tags_in_rule(
    operation: ABCTagGroupOperation | OperationReplaceGroupedTags,
    mode: TagCleanupMode,
    ruleset: Ruleset,
    rule: Rule,
) -> set[Ruleset]:
    affected_rulesets: set[Ruleset] = set()
    if operation.tag_group_id not in rule.conditions.host_tags:
        return affected_rulesets  # The tag group is not used

    # Handle deletion of complete tag group
    if isinstance(operation, ABCTagGroupOperation):
        affected_rulesets.add(ruleset)

        if mode == TagCleanupMode.CHECK:
            pass

        elif mode == TagCleanupMode.DELETE:
            # Just remove if negated
            if (
                condition := rule.conditions.host_tags[operation.tag_group_id]
            ) is not None and list(condition)[0] in ["$ne", "$nor"]:
                _remove_tag_group_condition(rule, operation.tag_group_id)
            else:
                ruleset.delete_rule(rule)
        elif mode == TagCleanupMode.REMOVE:
            _remove_tag_group_condition(rule, operation.tag_group_id)

        else:
            raise NotImplementedError()

        return affected_rulesets

    if not isinstance(operation, OperationReplaceGroupedTags):
        raise NotImplementedError()

    tag_map: list[tuple[str | None, Any]] = list(operation.replace_tag_ids.items())
    tag_map += [(tag_id, False) for tag_id in operation.remove_tag_ids]

    # Removal or renaming of single tag choices
    for old_tag, new_tag in tag_map:
        # The case that old_tag is None (an empty tag has got a name)
        # cannot be handled when it comes to rules. Rules do not support
        # such None-values.
        if not old_tag:
            continue

        current_value = rule.conditions.host_tags.get(operation.tag_group_id)
        if current_value is None:
            continue

        if current_value not in (old_tag, {"$ne": old_tag}):
            continue  # old_tag id is not configured

        affected_rulesets.add(ruleset)

        if mode == TagCleanupMode.CHECK:
            continue  # Skip modification

        # First remove current setting
        _remove_tag_group_condition(rule, operation.tag_group_id)

        # In case it needs to be replaced with a new value, do it now
        if new_tag:
            was_negated = isinstance(current_value, dict) and "$ne" in current_value
            new_value: TagCondition = {"$ne": new_tag} if was_negated else new_tag
            rule.update_conditions(
                RuleConditions(
                    host_folder=rule.conditions.host_folder,
                    host_tags={**rule.conditions.host_tags, operation.tag_group_id: new_value},
                    host_label_groups=rule.conditions.host_label_groups,
                    host_name=rule.conditions.host_name,
                    service_description=rule.conditions.service_description,
                    service_label_groups=rule.conditions.service_label_groups,
                )
            )
        # Example for current_value: {'$ne': 'my_tag'} / my_tag
        elif mode == TagCleanupMode.DELETE and (
            not isinstance(current_value, dict) and list(current_value)[0] not in ["$ne", "$nor"]
        ):
            ruleset.delete_rule(rule)

    return affected_rulesets


def _remove_tag_group_condition(rule: Rule, tag_group_id: TagGroupID) -> None:
    rule.update_conditions(
        RuleConditions(
            host_folder=rule.conditions.host_folder,
            host_tags={k: v for k, v in rule.conditions.host_tags.items() if k != tag_group_id},
            host_label_groups=rule.conditions.host_label_groups,
            host_name=rule.conditions.host_name,
            service_description=rule.conditions.service_description,
            service_label_groups=rule.conditions.service_label_groups,
        )
    )


# Creates a includable PHP file which provides some functions which
# can be used by the calling program, for example NagVis. It declares
# the following API:
#
# taggroup_title(group_id)
# Returns the title of a Setup tag group
#
# taggroup_choice(group_id, list_of_object_tags)
# Returns either
#   false: When taggroup does not exist in current config
#   null:  When no choice can be found for the given taggroup
#   array(tag, title): When a tag of the taggroup
#
# all_taggroup_choices(object_tags):
# Returns an array of elements which use the tag group id as key
# and have an assiciative array as value, where 'title' contains
# the tag group title and the value contains the value returned by
# taggroup_choice() for this tag group.
#
def _export_hosttags_to_php(cfg: TagConfigSpec) -> None:
    php_api_dir = cmk.utils.paths.var_dir / "wato/php-api"
    path = php_api_dir / "hosttags.php"
    php_api_dir.mkdir(mode=0o770, exist_ok=True, parents=True)

    tag_config = cmk.utils.tags.TagConfig.from_config(cfg)
    tag_config += cmk.utils.tags.BuiltinTagConfig()

    # Transform Setup internal data structures into easier usable ones
    hosttags_dict = {}
    for tag_group in tag_config.tag_groups:
        tags = {}
        for grouped_tag in tag_group.tags:
            tags[grouped_tag.id] = (grouped_tag.title, grouped_tag.aux_tag_ids)

        hosttags_dict[tag_group.id] = (tag_group.topic, tag_group.title, tags)

    auxtags_dict = dict(tag_config.aux_tag_list.get_choices())

    content = f"""<?php
// Created by WATO
global $mk_hosttags, $mk_auxtags;
$mk_hosttags = {format_php(hosttags_dict)};
$mk_auxtags = {format_php(auxtags_dict)};

function taggroup_title($group_id) {{
    global $mk_hosttags;
    if (isset($mk_hosttags[$group_id]))
        return $mk_hosttags[$group_id][0];
    else
        return $taggroup;
}}

function taggroup_choice($group_id, $object_tags) {{
    global $mk_hosttags;
    if (!isset($mk_hosttags[$group_id]))
        return false;
    foreach ($object_tags AS $tag) {{
        if (isset($mk_hosttags[$group_id][2][$tag])) {{
            // Found a match of the objects tags with the taggroup
            // now return an array of the matched tag and its alias
            return array($tag, $mk_hosttags[$group_id][2][$tag][0]);
        }}
    }}
    // no match found. Test whether or not a "None" choice is allowed
    if (isset($mk_hosttags[$group_id][2][null]))
        return array(null, $mk_hosttags[$group_id][2][null][0]);
    else
        return null; // no match found
}}

function all_taggroup_choices($object_tags) {{
    global $mk_hosttags;
    $choices = array();
    foreach ($mk_hosttags AS $group_id => $group) {{
        $choices[$group_id] = array(
            'topic' => $group[0],
            'title' => $group[1],
            'value' => taggroup_choice($group_id, $object_tags),
        );
    }}
    return $choices;
}}

?>
"""

    store.save_text_to_file(path, content)
