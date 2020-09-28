#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Helper functions for dealing with host tags"""

from typing import Any, Dict, List, Set, Tuple as _Tuple, Union, Optional

import errno
from pathlib import Path

import abc
from enum import Enum

from six import ensure_str

import cmk.gui.config as config
import cmk.gui.watolib as watolib
from cmk.gui.exceptions import (MKAuthException, MKGeneralException)

import cmk.utils.paths
import cmk.utils.store as store
from cmk.utils.i18n import _

import cmk.utils.tags
from cmk.gui.watolib.simple_config_file import WatoSimpleConfigFile
from cmk.gui.watolib.utils import (
    multisite_dir,
    wato_root_dir,
)
from cmk.utils.tags import TagGroup, TagConfig


class TagConfigFile(WatoSimpleConfigFile):
    """Handles loading the 1.6 tag definitions from GUI tags.mk or
    the pre 1.6 tag configuration from hosttags.mk

    When saving the configuration it also writes out the tags.mk for
    the cmk.base world.
    """
    def __init__(self):
        file_path = Path(multisite_dir()) / "tags.mk"
        super(TagConfigFile, self).__init__(config_file_path=file_path, config_variable="wato_tags")

    def _load_file(self, lock=False):
        if not self._config_file_path.exists():
            return self._load_pre_16_config(lock=lock)
        return super(TagConfigFile, self)._load_file(lock=lock)

    def _pre_16_hosttags_path(self):
        return Path(multisite_dir(), "hosttags.mk")

    def _load_pre_16_config(self, lock):
        legacy_cfg = store.load_mk_file(str(self._pre_16_hosttags_path()), {
            "wato_host_tags": [],
            "wato_aux_tags": []
        },
                                        lock=lock)

        _migrate_old_sample_config_tag_groups(legacy_cfg["wato_host_tags"],
                                              legacy_cfg["wato_aux_tags"])
        return cmk.utils.tags.transform_pre_16_tags(legacy_cfg["wato_host_tags"],
                                                    legacy_cfg["wato_aux_tags"])

    def save(self, cfg):
        super(TagConfigFile, self).save(cfg)
        self._save_base_config(cfg)

        # Cleanup pre 1.6 config files (tags were just saved with new path)
        try:
            self._pre_16_hosttags_path().unlink()
        except OSError as e:
            if e.errno != errno.ENOENT:
                raise

        _export_hosttags_to_php(cfg)

    def _save_base_config(self, cfg):
        base_config_file = WatoSimpleConfigFile(config_file_path=Path(wato_root_dir()) / "tags.mk",
                                                config_variable="tag_config")
        base_config_file.save(cfg)


def load_tag_config() -> TagConfig:
    """Load the tag config object based upon the most recently saved tag config file"""
    tag_config = cmk.utils.tags.TagConfig()
    tag_config.parse_config(TagConfigFile().load_for_modification())
    return tag_config


def update_tag_config(tag_config: TagConfig):
    """Persist the tag config saving the information to the mk file
    and update the current environment

    Args:
        tag_config:
            The tag config object to persist

    """
    TagConfigFile().save(tag_config.get_dict_format())
    _update_tag_dependencies()


def load_tag_group(ident: str) -> Optional[TagGroup]:
    """Load a tag group

    Args:
        ident:
            identifier of the tag group

    """
    tag_config = load_tag_config()
    return tag_config.get_tag_group(ident)


def save_tag_group(tag_group: TagGroup):
    """Save a new tag group

    Args:
        tag_group:
            the tag group object

    """
    tag_config = load_tag_config()
    tag_config.insert_tag_group(tag_group)
    tag_config.validate_config()
    update_tag_config(tag_config)


def tag_group_exists(ident: str) -> bool:
    """Verify if a tag group exists"""
    tag_config = load_tag_config()
    return tag_config.tag_group_exists(ident)


def load_aux_tags() -> List[str]:
    """Return the list available auxiliary tag ids (ID != GUI title)"""
    tag_config = load_tag_config()
    tag_config += cmk.utils.tags.BuiltinTagConfig()
    return [entry[0] for entry in tag_config.aux_tag_list.get_choices()]


def _update_tag_dependencies():
    config.load_config()
    watolib.Folder.invalidate_caches()
    watolib.Folder.root_folder().rewrite_hosts_files()


class RepairError(MKGeneralException):
    pass


def edit_tag_group(ident: str, edited_group: TagGroup, allow_repair=False):
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
    affected = change_host_tags_in_folders(
        operation,
        TagCleanupMode.CHECK,
        watolib.Folder.root_folder(),
    )
    if any(affected):
        if not allow_repair:
            raise RepairError("Permission missing")
        _ = change_host_tags_in_folders(
            operation,
            TagCleanupMode("repair"),
            watolib.Folder.root_folder(),
        )
    update_tag_config(tag_config)


def identify_modified_tags(updated_group: TagGroup, old_group: TagGroup):
    """Identify which ids were changed and which ids are to be deleted

    Example:

    >>> _old_group = TagGroup({
    ...    'id': 'foo',
    ...    'title': 'foobar',
    ...    'tags': [{
    ...        'id': 'tester',
    ...        'title': 'something',
    ...        'aux_tags': []
    ...    }],
    ...    'topic': 'nothing'
    ... })
    >>> _updated_group = TagGroup({
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
        if former_tag.id is not None \
            and former_tag.id not in [tmp_tag.id for tmp_tag in updated_group.tags]:
            # remove explicit tag (hosts/folders) or remove it from tag specs (rules)
            remove_tag_ids.append(former_tag.id)
    return remove_tag_ids, replace_tag_ids


class TagCleanupMode(Enum):
    ABORT = "abort"  # No further action. Aborting here.
    CHECK = "check"  # only affected rulesets are collected, nothing is modified
    DELETE = "delete"  # Rules using this tag are deleted
    REMOVE = "remove"  # Remove tags from rules
    REPAIR = "repair"  # Remove tags from rules


class ABCOperation(metaclass=abc.ABCMeta):
    """Base for all tag cleanup operations"""
    @abc.abstractmethod
    def confirm_title(self) -> str:
        raise NotImplementedError()


class ABCTagGroupOperation(ABCOperation, metaclass=abc.ABCMeta):
    def __init__(self, tag_group_id: str) -> None:
        super(ABCTagGroupOperation, self).__init__()
        self.tag_group_id = tag_group_id


class OperationRemoveTagGroup(ABCTagGroupOperation):
    def confirm_title(self):
        return _("Confirm tag group deletion")


class OperationRemoveAuxTag(ABCTagGroupOperation):
    def confirm_title(self):
        return _("Confirm aux tag deletion")


class OperationReplaceGroupedTags(ABCOperation):
    def __init__(self, tag_group_id: str, remove_tag_ids: List[str],
                 replace_tag_ids: Dict[str, str]) -> None:
        super(OperationReplaceGroupedTags, self).__init__()
        self.tag_group_id = tag_group_id
        self.remove_tag_ids = remove_tag_ids
        self.replace_tag_ids = replace_tag_ids

    def confirm_title(self):
        return _("Confirm tag modifications")


def change_host_tags_in_folders(operation, mode, folder):
    """Update host tag assignments in hosts/folders

    See _rename_tags_after_confirmation() doc string for additional information.
    """
    affected_folders = []
    affected_hosts = []
    affected_rulesets = []

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
            aff_folders, aff_hosts, aff_rulespecs = change_host_tags_in_folders(
                operation, mode, subfolder)
            affected_folders += aff_folders
            affected_hosts += aff_hosts
            affected_rulesets += aff_rulespecs

        affected_hosts += _change_host_tags_in_hosts(operation, mode, folder)

    affected_rulesets += _change_host_tags_in_rules(operation, mode, folder)
    return affected_folders, affected_hosts, affected_rulesets


def _change_host_tags_in_hosts(operation, mode, folder):
    affected_hosts = []
    for host in folder.hosts().values():
        aff_hosts = _change_host_tags_in_host_or_folder(operation, mode, host)
        affected_hosts += aff_hosts

    if affected_hosts and mode != TagCleanupMode.CHECK:
        try:
            folder.save_hosts()
        except MKAuthException:
            # Ignore MKAuthExceptions of locked host.mk files
            pass
    return affected_hosts


def _change_host_tags_in_host_or_folder(operation, mode, host_or_folder):
    affected: List[Union[watolib.CREHost, watolib.CREFolder]] = []

    attrname = "tag_" + operation.tag_group_id
    attributes = host_or_folder.attributes()
    if attrname not in attributes:
        return affected  # The attribute is not set

    # Deletion of a tag group
    if isinstance(operation, OperationRemoveTagGroup):
        if attrname in attributes:
            affected.append(host_or_folder)
            if mode != TagCleanupMode.CHECK:
                del attributes[attrname]
        return affected

    if not isinstance(operation, OperationReplaceGroupedTags):
        raise NotImplementedError()

    # Deletion or replacement of a tag choice
    current = attributes[attrname]
    if current in operation.remove_tag_ids or current in operation.replace_tag_ids:
        affected.append(host_or_folder)
        if mode != TagCleanupMode.CHECK:
            if current in operation.remove_tag_ids:
                del attributes[attrname]
            elif current in operation.replace_tag_ids:
                new_tag = operation.replace_tag_ids[current]
                attributes[attrname] = new_tag
            else:
                raise NotImplementedError()

    return affected


def _change_host_tags_in_rules(operation, mode, folder):
    """Update tags in all rules

    The function parses all rules in all rulesets and looks for host tags that
    have been removed or renamed. If tags are removed then the depending on the
    mode affected rules are either deleted ("delete") or the vanished tags are
    removed from the rule ("remove").

    See _rename_tags_after_confirmation() doc string for additional information.
    """
    affected_rulesets = set()

    rulesets = watolib.FolderRulesets(folder)
    rulesets.load()

    for ruleset in rulesets.get_rulesets().values():
        for _folder, _rulenr, rule in ruleset.get_rules():
            affected_rulesets.update(_change_host_tags_in_rule(operation, mode, ruleset, rule))

    if affected_rulesets and mode != TagCleanupMode.CHECK:
        rulesets.save()

    return sorted(affected_rulesets, key=lambda x: x.title())


def _change_host_tags_in_rule(operation, mode, ruleset, rule):
    affected_rulesets: Set[watolib.FolderRulesets] = set()
    if operation.tag_group_id not in rule.conditions.host_tags:
        return affected_rulesets  # The tag group is not used

    # Handle deletion of complete tag group
    if isinstance(operation, ABCTagGroupOperation):
        affected_rulesets.add(ruleset)

        if mode == TagCleanupMode.CHECK:
            pass

        elif mode == TagCleanupMode.DELETE:
            ruleset.delete_rule(rule)
        else:
            del rule.conditions.host_tags[operation.tag_group_id]

        return affected_rulesets

    if not isinstance(operation, OperationReplaceGroupedTags):
        raise NotImplementedError()

    tag_map: List[_Tuple[str, Any]] = list(operation.replace_tag_ids.items())
    tag_map += [(tag_id, False) for tag_id in operation.remove_tag_ids]

    # Removal or renaming of single tag choices
    for old_tag, new_tag in tag_map:
        # The case that old_tag is None (an empty tag has got a name)
        # cannot be handled when it comes to rules. Rules do not support
        # such None-values.
        if not old_tag:
            continue

        current_value = rule.conditions.host_tags[operation.tag_group_id]
        if current_value not in (old_tag, {'$ne': old_tag}):
            continue  # old_tag id is not configured

        affected_rulesets.add(ruleset)

        if mode == TagCleanupMode.CHECK:
            continue  # Skip modification

        # First remove current setting
        del rule.conditions.host_tags[operation.tag_group_id]

        # In case it needs to be replaced with a new value, do it now
        if new_tag:
            was_negated = isinstance(dict, current_value) and "$ne" in current_value
            new_value = {"$ne": new_tag} if was_negated else new_tag
            rule.conditions.host_tags[operation.tag_group_id] = new_value
        elif mode == TagCleanupMode.DELETE:
            ruleset.delete_rule(rule)

    return affected_rulesets


# Previous to 1.5 the "Agent type" tag group was created as sample config and was not
# a builtin tag group (which can not be modified by the user). With werk #5535 we changed
# the tag scheme and need to deal with the user config (which might extend the original tag group).
# Use two strategies:
#
# a) Check whether or not the tag group has been modified. If not, simply remove it from the user
#    config and use the builtin tag group in the future.
# b) Extend the tag group in the user configuration with the tag configuration we need for 1.5.
# TODO: Move to wato/watolib and register using register_post_config_load_hook()
def _migrate_old_sample_config_tag_groups(host_tags, aux_tags_):
    _remove_old_sample_config_tag_groups(host_tags, aux_tags_)
    _extend_user_modified_tag_groups(host_tags)


def _remove_old_sample_config_tag_groups(host_tags, aux_tags_):
    legacy_tag_group_default = (
        'agent',
        u'Agent type',
        [
            ('cmk-agent', u'Check_MK Agent (Server)', ['tcp']),
            ('snmp-only', u'SNMP (Networking device, Appliance)', ['snmp']),
            ('snmp-v1', u'Legacy SNMP device (using V1)', ['snmp']),
            ('snmp-tcp', u'Dual: Check_MK Agent + SNMP', ['snmp', 'tcp']),
            ('ping', u'No Agent', []),
        ],
    )

    try:
        host_tags.remove(legacy_tag_group_default)

        # Former tag choices (see above) are added as aux tags to allow the user to migrate
        # these tags and the objects that use them
        aux_tags_.insert(0,
                         ("snmp-only", "Data sources/Legacy: SNMP (Networking device, Appliance)"))
        aux_tags_.insert(0, ("snmp-tcp", "Data sources/Legacy: Dual: Check_MK Agent + SNMP"))
    except ValueError:
        pass  # Not there or modified

    legacy_aux_tag_ids = [
        'snmp',
        'tcp',
    ]

    for aux_tag in aux_tags_[:]:
        if aux_tag[0] in legacy_aux_tag_ids:
            aux_tags_.remove(aux_tag)


def _extend_user_modified_tag_groups(host_tags):
    """This method supports migration from <1.5 to 1.5 in case the user has a customized "Agent type" tag group
    See help of migrate_old_sample_config_tag_groups() and werk #5535 and #6446 for further information.

    Disclaimer: The host_tags data structure is a mess which will hopefully be cleaned up during 1.6 development.
    Basically host_tags is a list of configured tag groups. Each tag group is represented by a tuple like this:

    # tag_group_id, tag_group_title, tag_choices
    ('agent', u'Agent type',
        [
            # tag_id, tag_title, aux_tag_ids
            ('cmk-agent', u'Check_MK Agent (Server)', ['tcp']),
            ('snmp-only', u'SNMP (Networking device, Appliance)', ['snmp']),
            ('snmp-v1',   u'Legacy SNMP device (using V1)', ['snmp']),
            ('snmp-tcp',  u'Dual: Check_MK Agent + SNMP', ['snmp', 'tcp']),
            ('ping',      u'No Agent', []),
        ],
    )
    """
    tag_group = None
    for this_tag_group in host_tags:
        if this_tag_group[0] == "agent":
            tag_group = this_tag_group

    if tag_group is None:
        return  # Tag group does not exist

    # Mark all existing tag choices as legacy to help the user that this should be cleaned up
    for index, tag_choice in enumerate(tag_group[2][:]):
        if tag_choice[0] in ["no-agent", "special-agents", "all-agents", "cmk-agent"]:
            continue  # Don't prefix the standard choices

        if tag_choice[1].startswith("Legacy: "):
            continue  # Don't prefix already prefixed choices

        tag_choice_list = list(tag_choice)
        tag_choice_list[1] = "Legacy: %s" % tag_choice_list[1]
        tag_group[2][index] = tuple(tag_choice_list)

    tag_choices = [c[0] for c in tag_group[2]]

    if "no-agent" not in tag_choices:
        tag_group[2].insert(0, ("no-agent", _("No agent"), []))

    if "special-agents" not in tag_choices:
        tag_group[2].insert(
            0, ("special-agents", _("No Checkmk agent, all configured special agents"), ["tcp"]))

    if "all-agents" not in tag_choices:
        tag_group[2].insert(
            0, ("all-agents", _("Normal Checkmk agent, all configured special agents"), ["tcp"]))

    if "cmk-agent" not in tag_choices:
        tag_group[2].insert(
            0, ("cmk-agent", _("Normal Checkmk agent, or special agent if configured"), ["tcp"]))
    else:
        # Change title of cmk-agent tag choice and move to top
        for index, tag_choice in enumerate(tag_group[2]):
            if tag_choice[0] == "cmk-agent":
                tag_choice_list = list(tag_group[2].pop(index))
                tag_choice_list[1] = _("Normal Checkmk agent, or special agent if configured")
                tag_group[2].insert(0, tuple(tag_choice_list))
                break


# Creates a includable PHP file which provides some functions which
# can be used by the calling program, for example NagVis. It declares
# the following API:
#
# taggroup_title(group_id)
# Returns the title of a WATO tag group
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
def _export_hosttags_to_php(cfg):
    php_api_dir = Path(cmk.utils.paths.var_dir) / "wato/php-api"
    path = php_api_dir / 'hosttags.php'
    store.mkdir(php_api_dir)

    tag_config = cmk.utils.tags.TagConfig()
    tag_config.parse_config(cfg)
    tag_config += cmk.utils.tags.BuiltinTagConfig()

    # Transform WATO internal data structures into easier usable ones
    hosttags_dict = {}
    for tag_group in tag_config.tag_groups:
        tags = {}
        for grouped_tag in tag_group.tags:
            tags[grouped_tag.id] = (grouped_tag.title, grouped_tag.aux_tag_ids)

        hosttags_dict[tag_group.id] = (tag_group.topic, tag_group.title, tags)

    auxtags_dict = dict(tag_config.aux_tag_list.get_choices())

    content = u'''<?php
// Created by WATO
global $mk_hosttags, $mk_auxtags;
$mk_hosttags = %s;
$mk_auxtags = %s;

function taggroup_title($group_id) {
    global $mk_hosttags;
    if (isset($mk_hosttags[$group_id]))
        return $mk_hosttags[$group_id][0];
    else
        return $taggroup;
}

function taggroup_choice($group_id, $object_tags) {
    global $mk_hosttags;
    if (!isset($mk_hosttags[$group_id]))
        return false;
    foreach ($object_tags AS $tag) {
        if (isset($mk_hosttags[$group_id][2][$tag])) {
            // Found a match of the objects tags with the taggroup
            // now return an array of the matched tag and its alias
            return array($tag, $mk_hosttags[$group_id][2][$tag][0]);
        }
    }
    // no match found. Test whether or not a "None" choice is allowed
    if (isset($mk_hosttags[$group_id][2][null]))
        return array(null, $mk_hosttags[$group_id][2][null][0]);
    else
        return null; // no match found
}

function all_taggroup_choices($object_tags) {
    global $mk_hosttags;
    $choices = array();
    foreach ($mk_hosttags AS $group_id => $group) {
        $choices[$group_id] = array(
            'topic' => $group[0],
            'title' => $group[1],
            'value' => taggroup_choice($group_id, $object_tags),
        );
    }
    return $choices;
}

?>
''' % (_format_php(hosttags_dict), _format_php(auxtags_dict))

    store.save_text_to_file(path, content)


# TODO: Fix copy-n-paste with cmk.gui.watolib.auth_pnp.
def _format_php(data, lvl=1):
    s = ''
    if isinstance(data, (list, tuple)):
        s += 'array(\n'
        for item in data:
            s += '    ' * lvl + _format_php(item, lvl + 1) + ',\n'
        s += '    ' * (lvl - 1) + ')'
    elif isinstance(data, dict):
        s += 'array(\n'
        for key, val in data.items():
            s += '    ' * lvl + _format_php(key, lvl + 1) + ' => ' + _format_php(val,
                                                                                 lvl + 1) + ',\n'
        s += '    ' * (lvl - 1) + ')'
    elif isinstance(data, str):
        s += '\'%s\'' % ensure_str(data).replace('\'', '\\\'')
    elif isinstance(data, bool):
        s += data and 'true' or 'false'
    elif data is None:
        s += 'null'
    else:
        s += str(data)

    return s
