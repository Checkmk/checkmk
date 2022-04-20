#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

import dataclasses
import os
import pprint
import re
from typing import Any, Callable, cast, Container, Dict, List, Mapping, Optional, Tuple, Union

import cmk.utils.rulesets.ruleset_matcher as ruleset_matcher
import cmk.utils.store as store
from cmk.utils.object_diff import make_diff_text
from cmk.utils.regex import escape_regex_chars
from cmk.utils.type_defs import (
    HostOrServiceConditionRegex,
    HostOrServiceConditions,
    Labels,
    RuleConditionsSpec,
    RuleOptions,
    RulesetName,
    RuleSpec,
    RuleValue,
    TagConditionNE,
    TaggroupIDToTagCondition,
    TagID,
    TagIDToTaggroupID,
)

# Tolerate this for 1.6. Should be cleaned up in future versions,
# e.g. by trying to move the common code to a common place
import cmk.base.export  # pylint: disable=cmk-module-layer-violation

from cmk.gui import utils
from cmk.gui.config import register_post_config_load_hook
from cmk.gui.exceptions import MKGeneralException
from cmk.gui.globals import active_config, html
from cmk.gui.i18n import _
from cmk.gui.log import logger
from cmk.gui.utils.html import HTML
from cmk.gui.valuespec import DropdownChoiceEntries, ValueSpec
from cmk.gui.watolib.changes import add_change
from cmk.gui.watolib.hosts_and_folders import (
    CREFolder,
    CREHost,
    Folder,
    get_wato_redis_client,
    Host,
    may_use_redis,
)
from cmk.gui.watolib.objref import ObjectRef, ObjectRefType
from cmk.gui.watolib.rulespecs import rulespec_group_registry, rulespec_registry
from cmk.gui.watolib.utils import ALL_HOSTS, ALL_SERVICES, has_agent_bakery, NEGATE, wato_root_dir

# Make the GUI config module reset the base config to always get the latest state of the config
register_post_config_load_hook(cmk.base.export.reset_config)

FolderPath = str
SearchOptions = Dict[str, Any]


# This macro is needed to make the to_config() methods be able to use native
# pprint/repr for the ruleset data structures. Have a look at
# to_config_with_folder_macro() for further information.
_FOLDER_PATH_MACRO = "%#%FOLDER_PATH%#%"


class RuleConditions:
    def __init__(
        self,
        host_folder: str,
        host_tags: Optional[TaggroupIDToTagCondition] = None,
        host_labels: Optional[Labels] = None,
        host_name: Optional[HostOrServiceConditions] = None,
        service_description: Optional[HostOrServiceConditions] = None,
        service_labels: Optional[Labels] = None,
    ) -> None:
        self.host_folder = host_folder
        self.host_tags: TaggroupIDToTagCondition = host_tags or {}
        self.host_labels = host_labels or {}
        self.host_name = host_name
        self.service_description = service_description
        self.service_labels = service_labels or {}

    def from_config(self, conditions: Any) -> RuleConditions:
        self.host_folder = conditions.get("host_folder", self.host_folder)
        self.host_tags = conditions.get("host_tags", {})
        self.host_labels = conditions.get("host_labels", {})
        self.host_name = conditions.get("host_name")
        self.service_description = conditions.get("service_description")
        self.service_labels = conditions.get("service_labels", {})
        return self

    def to_config_with_folder_macro(self) -> RuleConditionsSpec:
        """Create serializable data structure for the conditions

        In the WATO folder hierarchy each folder may have a rules.mk which
        contains the rules of that folder.

        It is an important feature that there is no path stored in the .mk
        files of the folders. This makes the user able to move the folders around
        without the need to update the files.

        However, Checkmk still needs the information which rule has been loaded
        from which folder. To make this possible we add the _FOLDER_PATH_MACRO here
        and replace it with the FOLDER_PATH reference before writing the rules.mk to
        disk.

        Checkmk can then resolve the FOLDER_PATH while loading the configuration file.
        Have a look at _load_folder_rulesets() for an example.
        """
        cfg = self._to_config()
        cfg["host_folder"] = _FOLDER_PATH_MACRO
        return cfg

    def to_config_with_folder(self) -> RuleConditionsSpec:
        cfg = self._to_config()
        cfg["host_folder"] = self.host_folder
        return cfg

    def to_config_without_folder(self) -> RuleConditionsSpec:
        return self._to_config()

    def _to_config(self) -> RuleConditionsSpec:
        cfg: RuleConditionsSpec = {}

        if self.host_tags:
            cfg["host_tags"] = self.host_tags

        if self.host_labels:
            cfg["host_labels"] = self.host_labels

        if self.host_name is not None:
            cfg["host_name"] = self.host_name

        if self.service_description is not None:
            cfg["service_description"] = self.service_description

        if self.service_labels:
            cfg["service_labels"] = self.service_labels

        return cfg

    def has_only_explicit_service_conditions(self) -> bool:
        if self.service_description is None:
            return False

        service_name_conditions = (
            self.service_description.get("$nor", [])
            if isinstance(self.service_description, dict)
            else self.service_description
        )

        return bool(service_name_conditions) and all(
            not isinstance(i, dict) or i["$regex"].endswith("$") for i in service_name_conditions
        )

    # Compatibility code for pre 1.6 WATO code
    @property
    def tag_list(self) -> Container[Optional[TagID]]:
        tag_list = []
        for tag_spec in self.host_tags.values():
            is_not = isinstance(tag_spec, dict) and "$ne" in tag_spec
            if isinstance(tag_spec, dict) and is_not:
                tag_id = cast(TagConditionNE, tag_spec)["$ne"]
            else:
                tag_id = cast(Optional[TagID], tag_spec)

            tag_list.append(("!%s" % tag_id) if is_not else tag_id)
        return tag_list

    # Compatibility code for pre 1.6 WATO code
    @property
    def host_list(self):
        return self._condition_list(self.host_name, is_service=False)

    # Compatibility code for pre 1.6 WATO code
    @property
    def item_list(self):
        return self._condition_list(self.service_description, is_service=True)

    def _condition_list(
        self, object_list: Optional[HostOrServiceConditions], is_service: bool
    ) -> Optional[Tuple[List[str], bool]]:
        if object_list is None:
            return None

        negate, object_list = ruleset_matcher.parse_negated_condition_list(object_list)

        pattern_list = []
        for entry in object_list:
            if isinstance(entry, dict):
                if "$regex" not in entry:
                    raise NotImplementedError()

                if is_service:
                    pattern_list.append("%s" % entry["$regex"])
                else:
                    pattern_list.append("~%s" % entry["$regex"])
            else:
                pattern_list.append(entry)

        return pattern_list, negate

    def clone(self) -> RuleConditions:
        return RuleConditions(
            host_folder=self.host_folder,
            host_tags={**self.host_tags},
            host_labels={**self.host_labels},
            host_name=self.host_name.copy()
            if isinstance(
                self.host_name,
                dict,
            )
            else [*self.host_name]
            if self.host_name is not None
            else None,
            service_description=self.service_description.copy()
            if isinstance(
                self.service_description,
                dict,
            )
            else [*self.service_description]
            if self.service_description is not None
            else None,
            service_labels={**self.service_labels},
        )


class RulesetCollection:
    """Abstract class for holding a collection of rulesets. The most basic
    specific class is the FolderRulesets class which cares about all rulesets
    configured in a folder."""

    def __init__(self) -> None:
        super().__init__()
        # A dictionary containing all ruleset objects of the collection.
        # The name of the ruleset is used as key in the dict.
        self._tag_to_group_map = ruleset_matcher.get_tag_to_group_map(active_config.tags)
        self._rulesets: Dict[RulesetName, Ruleset] = {}

    # Has to be implemented by the subclasses to load the right rulesets
    def load(self):
        raise NotImplementedError()

    def _initialize_rulesets(self, only_varname: Optional[RulesetName] = None) -> None:
        varnames = [only_varname] if only_varname else rulespec_registry.keys()
        self._rulesets = {varname: Ruleset(varname, self._tag_to_group_map) for varname in varnames}

    def _load_folder_rulesets(
        self, folder: CREFolder, only_varname: Optional[RulesetName] = None
    ) -> None:
        path = folder.rules_file_path()

        if not os.path.exists(path):
            return  # Do not initialize rulesets when no rule at all exists

        config_dict = {
            "ALL_HOSTS": ALL_HOSTS,
            "ALL_SERVICES": ALL_SERVICES,
            "NEGATE": NEGATE,
            "FOLDER_PATH": folder.path(),
        }

        # Prepare empty rulesets so that rules.mk has something to
        # append to. We need to initialize all variables here, even
        # when only loading with only_varname.
        for varname in rulespec_registry.keys():
            if ":" in varname:
                dictname, _subkey = varname.split(":")
                config_dict[dictname] = {}
            else:
                config_dict[varname] = []

        self.from_config(folder, store.load_mk_file(path, config_dict), only_varname)

    def from_config(
        self, folder: CREFolder, rulesets_config, only_varname: Optional[RulesetName] = None
    ) -> None:
        varnames = [only_varname] if only_varname else rulespec_registry.keys()
        config_varname: str
        subkey: Optional[str]
        for varname in varnames:
            if ":" in varname:
                config_varname, subkey = varname.split(":", 1)
                rulegroup_config = rulesets_config.get(config_varname, {})
                if subkey not in rulegroup_config:
                    continue  # Nothing configured: nothing left to do

                ruleset_config = rulegroup_config[subkey]
            else:
                config_varname, subkey = varname, None
                ruleset_config = rulesets_config.get(config_varname, [])

            if not ruleset_config:
                continue  # Nothing configured: nothing left to do

            self._rulesets[varname].from_config(folder, ruleset_config)

    def save(self):
        raise NotImplementedError()

    def save_folder(self, folder):
        raise NotImplementedError()

    def _save_folder(self, folder):
        store.mkdir(folder.get_root_dir())

        has_content = False
        content = ""
        for varname, ruleset in sorted(self._rulesets.items(), key=lambda x: x[0]):
            if varname not in rulespec_registry:
                continue  # don't save unknown rulesets

            if ruleset.is_empty_in_folder(folder):
                continue  # don't save empty rule sets

            has_content = True
            content += ruleset.to_config(folder)

        rules_file_path = folder.rules_file_path()
        try:
            # Remove rules files if it has no content. This prevents needless reads
            if not has_content:
                if os.path.exists(rules_file_path):
                    os.unlink(rules_file_path)  # Do not keep empty rules.mk files
                return

            # Adding this instead of the full path makes it easy to move config
            # files around. The real FOLDER_PATH will be added dynamically while
            # loading the file in cmk.base.config
            content = content.replace("'%s'" % _FOLDER_PATH_MACRO, "'/%s/' % FOLDER_PATH")

            store.save_mk_file(rules_file_path, content, add_header=not active_config.wato_use_git)
        finally:
            if may_use_redis():
                get_wato_redis_client().folder_updated(folder.filesystem_path())

    def exists(self, name: RulesetName) -> bool:
        return name in self._rulesets

    def get(self, name: RulesetName, deflt=None) -> Ruleset:
        return self._rulesets[name]

    def set(self, name: RulesetName, ruleset: Ruleset) -> None:
        self._rulesets[name] = ruleset

    def delete(self, name: RulesetName):
        del self._rulesets[name]

    def get_rulesets(self) -> Mapping[RulesetName, Ruleset]:
        return self._rulesets

    def set_rulesets(self, rulesets: Dict[RulesetName, Ruleset]) -> None:
        self._rulesets = rulesets

    # Groups the rulesets in 3 layers (main group, sub group, rulesets)
    def get_grouped(self) -> List[Tuple[str, List[Tuple[str, List[Ruleset]]]]]:
        grouped_dict: Dict[str, Dict[str, List[Ruleset]]] = {}
        for ruleset in self._rulesets.values():
            main_group = grouped_dict.setdefault(ruleset.rulespec.main_group_name, {})
            group_rulesets = main_group.setdefault(ruleset.rulespec.group_name, [])
            group_rulesets.append(ruleset)

        grouped = []
        for main_group_name, sub_groups in grouped_dict.items():
            sub_group_list = []

            for group_name, group_rulesets in sorted(sub_groups.items(), key=lambda x: x[0]):
                sub_group_list.append(
                    (group_name, sorted(group_rulesets, key=lambda x: str(x.title())))
                )

            grouped.append((main_group_name, sub_group_list))

        return grouped


class AllRulesets(RulesetCollection):
    def _load_rulesets_recursively(
        self, folder: CREFolder, only_varname: Optional[RulesetName] = None
    ) -> None:

        if may_use_redis():
            self._load_rulesets_via_redis(folder, only_varname)
            return

        for subfolder in folder.subfolders():
            self._load_rulesets_recursively(subfolder, only_varname)

        self._load_folder_rulesets(folder, only_varname)

    def _load_rulesets_via_redis(
        self, folder: CREFolder, only_varname: Optional[RulesetName] = None
    ) -> None:
        # Search relevant folders with rules.mk files
        # Note: The sort order of the folders does not matter here
        #       self._load_folder_rulesets ultimately puts each folder into a dict
        #       and groups/sorts them later on with a different mechanism
        all_folders = get_wato_redis_client().recursive_subfolders_for_path(
            f"{folder.path()}/".lstrip("/")
        )

        root_dir = wato_root_dir()[:-1]
        relevant_folders = []
        for folder_path in all_folders:
            if os.path.exists(f"{root_dir}/{folder_path}rules.mk"):
                relevant_folders.append(folder_path)

        for folder_path_with_slash in relevant_folders:
            stripped_folder = folder_path_with_slash.strip("/")
            self._load_folder_rulesets(Folder.folder(stripped_folder), only_varname)

    def load(self) -> None:
        """Load all rules of all folders"""
        self._initialize_rulesets()
        self._load_rulesets_recursively(Folder.root_folder())

    def save_folder(self, folder):
        self._save_folder(folder)

    def save(self) -> None:
        """Save all rulesets of all folders recursively"""
        self._save_rulesets_recursively(Folder.root_folder())

    def _save_rulesets_recursively(self, folder: CREFolder) -> None:
        for subfolder in folder.subfolders():
            self._save_rulesets_recursively(subfolder)

        self._save_folder(folder)


class SingleRulesetRecursively(AllRulesets):
    def __init__(self, name: RulesetName) -> None:
        super().__init__()
        self._name = name

    # Load single ruleset from all folders
    def load(self) -> None:
        self._initialize_rulesets(only_varname=self._name)
        self._load_rulesets_recursively(Folder.root_folder(), only_varname=self._name)

    def save_folder(self, folder: CREFolder) -> None:
        raise NotImplementedError()


class FolderRulesets(RulesetCollection):
    def __init__(self, folder: CREFolder) -> None:
        super().__init__()
        self._folder = folder

    def load(self) -> None:
        self._initialize_rulesets()
        self._load_folder_rulesets(self._folder)

    def save(self) -> None:
        self._save_folder(self._folder)


class FilteredRulesetCollection(AllRulesets):
    def save(self) -> None:
        raise NotImplementedError("Filtered ruleset collections can not be saved.")


class StaticChecksRulesets(FilteredRulesetCollection):
    def load(self) -> None:
        super().load()
        self._remove_non_static_checks_rulesets()

    def _remove_non_static_checks_rulesets(self) -> None:
        for name, ruleset in list(self._rulesets.items()):
            if ruleset.rulespec.main_group_name != "static":
                del self._rulesets[name]


class SearchedRulesets(FilteredRulesetCollection):
    def __init__(self, origin_rulesets: RulesetCollection, search_options: SearchOptions) -> None:
        super().__init__()
        self._origin_rulesets = origin_rulesets
        self._search_options = search_options
        self._load_filtered()

    def _load_filtered(self) -> None:
        """Iterates the rulesets from the original collection,
        applies the search option and takes over the rulesets
        that have at least one matching rule or match itself,
        e.g. by their name, title or help."""

        for ruleset in self._origin_rulesets.get_rulesets().values():
            if ruleset.matches_search_with_rules(self._search_options):
                self._rulesets[ruleset.name] = ruleset


class Ruleset:
    def __init__(self, name: RulesetName, tag_to_group_map: TagIDToTaggroupID) -> None:
        super().__init__()
        self.name = name
        self.tag_to_group_map = tag_to_group_map
        self.rulespec = rulespec_registry[name]

        # Holds list of the rules. Using the folder paths as keys.
        self._rules: Dict[FolderPath, List[Rule]] = {}
        self._rules_by_id: Dict[str, Rule] = {}

        # Temporary needed during search result processing
        self.search_matching_rules: List[Rule] = []

        # Converts pre 1.6 tuple rulesets in place to 1.6+ format
        self.tuple_transformer = ruleset_matcher.RulesetToDictTransformer(
            tag_to_group_map=tag_to_group_map
        )

    def clone(self):
        cloned = Ruleset(self.name, self.tag_to_group_map)
        cloned.rulespec = self.rulespec
        for folder, _rule_index, rule in self.get_rules():
            cloned.append_rule(folder, rule)
        return cloned

    def set_name(self, name: RulesetName) -> None:
        self.name = name

    def object_ref(self) -> ObjectRef:
        return ObjectRef(ObjectRefType.Ruleset, self.name)

    def is_empty(self) -> bool:
        return self.num_rules() == 0

    def is_empty_in_folder(self, folder: CREFolder) -> bool:
        return not bool(self.get_folder_rules(folder))

    def num_rules(self) -> int:
        return len(self._rules_by_id)

    def num_rules_in_folder(self, folder: CREFolder) -> int:
        return len(self.get_folder_rules(folder))

    def get_rules(self) -> List[Tuple[CREFolder, int, Rule]]:
        rules = []
        for _folder_path, folder_rules in self._rules.items():
            for rule_index, rule in enumerate(folder_rules):
                rules.append((rule.folder, rule_index, rule))
        return sorted(
            rules, key=lambda x: (x[0].path().split("/"), len(rules) - x[1]), reverse=True
        )

    def get_folder_rules(self, folder: CREFolder) -> List[Rule]:
        try:
            return self._rules[folder.path()]
        except KeyError:
            return []

    def prepend_rule(self, folder: CREFolder, rule: Rule) -> None:
        rules = self._rules.setdefault(folder.path(), [])
        rules.insert(0, rule)
        self._rules_by_id[rule.id] = rule
        self._on_change()

    def clone_rule(self, orig_rule: Rule, rule: Rule) -> None:
        if rule.folder == orig_rule.folder:
            self.insert_rule_after(rule, orig_rule)
        else:
            self.append_rule(rule.folder, rule)

        add_change(
            "new-rule",
            _('Cloned rule from rule %s in ruleset "%s" in folder "%s"')
            % (orig_rule.id, self.title(), rule.folder.alias_path()),
            sites=rule.folder.all_site_ids(),
            diff_text=make_diff_text({}, rule.to_log()),
            object_ref=rule.object_ref(),
        )

    def append_rule(self, folder: CREFolder, rule: Rule) -> int:
        rules = self._rules.setdefault(folder.path(), [])
        index = len(rules)
        rules.append(rule)
        self._rules_by_id[rule.id] = rule
        self._on_change()
        return index

    def insert_rule_after(self, rule: Rule, after: Rule) -> None:
        index = self._rules[rule.folder.path()].index(after) + 1
        self._rules[rule.folder.path()].insert(index, rule)
        self._rules_by_id[rule.id] = rule
        self._on_change()

    def from_config(self, folder: CREFolder, rules_config) -> None:
        if not rules_config:
            return

        if folder.path() in self._rules:
            for rule in self._rules[folder.path()]:
                del self._rules_by_id[rule.id]

        # Resets the rules of this ruleset for this folder!
        self._rules[folder.path()] = []

        self.tuple_transformer.transform_in_place(
            rules_config,
            is_service=self.rulespec.is_for_services,
            is_binary=self.rulespec.is_binary_ruleset,
            use_ruleset_id_cache=False,
        )

        for rule_config in rules_config:
            rule = Rule.from_config(folder, self, rule_config)
            self._rules[folder.path()].append(rule)
            self._rules_by_id[rule.id] = rule

    def to_config(self, folder: CREFolder) -> str:
        content = ""

        if ":" in self.name:
            dictname, subkey = self.name.split(":")
            varname = "%s[%r]" % (dictname, subkey)

            content += "\n%s.setdefault(%r, [])\n" % (dictname, subkey)
        else:
            varname = self.name

            content += "\nglobals().setdefault(%r, [])\n" % (varname)

            if self.is_optional():
                content += "\nif %s is None:\n    %s = []\n" % (varname, varname)

        content += "\n%s = [\n" % varname
        for rule in self._rules[folder.path()]:
            # When using pprint we get a deterministic representation of the
            # data structures because it cares about sorting of the dict keys
            if active_config.wato_use_git:
                text = pprint.pformat(rule.to_config())
            else:
                text = repr(rule.to_config())

            content += "%s,\n" % text
        content += "] + %s\n\n" % varname

        return content

    # Whether or not either the ruleset itself matches the search or the rules match
    def matches_search_with_rules(self, search_options: SearchOptions) -> bool:
        if not self.matches_ruleset_search_options(search_options):
            return False

        # The ruleset matched or did not decide to skip the whole ruleset.
        # The ruleset should be matched in case a rule matches.
        if not self.has_rule_search_options(search_options):
            return self.matches_fulltext_search(search_options)

        # Store the matching rules for later result rendering
        self.search_matching_rules = []
        for _folder, _rule_index, rule in self.get_rules():
            if rule.matches_search(search_options):
                self.search_matching_rules.append(rule)

        # Show all rulesets where at least one rule matched
        if self.search_matching_rules:
            return True

        # e.g. in case ineffective rules are searched and no fulltext
        # search is filled in: Then don't show empty rulesets.
        if not search_options.get("fulltext"):
            return False

        return self.matches_fulltext_search(search_options)

    def has_rule_search_options(self, search_options: SearchOptions) -> bool:
        return bool([k for k in search_options.keys() if k == "fulltext" or k.startswith("rule_")])

    def matches_fulltext_search(self, search_options: SearchOptions) -> bool:
        return _match_one_of_search_expression(
            search_options, "fulltext", [self.name, str(self.title()), str(self.help())]
        )

    def matches_ruleset_search_options(self, search_options: SearchOptions) -> bool:
        if (
            "ruleset_deprecated" in search_options
            and search_options["ruleset_deprecated"] != self.is_deprecated()
        ):
            return False

        if "ruleset_used" in search_options and search_options["ruleset_used"] is self.is_empty():
            return False

        if "ruleset_group" in search_options and not self._matches_group_search(search_options):
            return False

        if not _match_search_expression(search_options, "ruleset_name", self.name):
            return False

        if not _match_search_expression(search_options, "ruleset_title", str(self.title())):
            return False

        if not _match_search_expression(search_options, "ruleset_help", str(self.help())):
            return False

        return True

    def _matches_group_search(self, search_options: SearchOptions) -> bool:
        # All rulesets are in a single group. Only the two rulesets "agent_ports" and
        # "agent_encryption" are in the RulespecGroupAgentCMKAgent but are also used
        # by the agent bakery. Users often try to find the ruleset in the wrong group.
        # For this reason we make the ruleset available in both groups.
        # Instead of making the ruleset specification more complicated for this special
        # case we hack it here into the ruleset search which is used to populate the
        # group pages.
        if search_options["ruleset_group"] == "agents" and self.rulespec.name in [
            "agent_ports",
            "agent_encryption",
        ]:
            return True

        return self.rulespec.group_name in rulespec_group_registry.get_matching_group_names(
            search_options["ruleset_group"]
        )

    def get_rule(self, folder: CREFolder, rule_index: int) -> Rule:
        return self._rules[folder.path()][rule_index]

    def get_rule_by_id(self, rule_id: str) -> Rule:
        return self._rules_by_id[rule_id]

    def edit_rule(self, orig_rule: Rule, rule: Rule) -> None:
        folder_rules = self._rules[orig_rule.folder.path()]
        index = folder_rules.index(orig_rule)

        folder_rules[index] = rule

        add_change(
            "edit-rule",
            _('Changed properties of rule #%d in ruleset "%s" in folder "%s"')
            % (index, self.title(), rule.folder.alias_path()),
            sites=rule.folder.all_site_ids(),
            diff_text=make_diff_text(orig_rule.to_log(), rule.to_log()),
            object_ref=rule.object_ref(),
        )
        self._on_change()

    def delete_rule(self, rule: Rule, create_change: bool = True) -> None:
        folder_rules = self._rules[rule.folder.path()]
        index = folder_rules.index(rule)

        folder_rules.remove(rule)
        del self._rules_by_id[rule.id]

        if create_change:
            add_change(
                "edit-rule",
                _('Deleted rule #%d in ruleset "%s" in folder "%s"')
                % (index, self.title(), rule.folder.alias_path()),
                sites=rule.folder.all_site_ids(),
                object_ref=rule.object_ref(),
            )
        self._on_change()

    def move_rule_to(self, rule: Rule, index: int) -> None:
        rules = self._rules[rule.folder.path()]
        old_index = rules.index(rule)
        rules.remove(rule)
        rules.insert(index, rule)
        add_change(
            "edit-ruleset",
            _('Moved rule %s from position #%d to #%d in ruleset "%s" in folder "%s"')
            % (rule.id, old_index, index, self.title(), rule.folder.alias_path()),
            sites=rule.folder.all_site_ids(),
            object_ref=self.object_ref(),
        )

    # TODO: Remove these getters
    def valuespec(self) -> ValueSpec:
        return self.rulespec.valuespec

    def help(self) -> Union[None, str, HTML]:
        return self.rulespec.help

    def title(self) -> Optional[str]:
        return self.rulespec.title

    def item_type(self) -> Optional[str]:
        return self.rulespec.item_type

    def item_name(self) -> Optional[str]:
        return self.rulespec.item_name

    def item_help(self) -> Union[None, str, HTML]:
        return self.rulespec.item_help

    def item_enum(self) -> Optional[DropdownChoiceEntries]:
        return self.rulespec.item_enum

    def match_type(self) -> str:
        return self.rulespec.match_type

    def is_deprecated(self) -> bool:
        return self.rulespec.is_deprecated

    def is_optional(self) -> bool:
        return self.rulespec.is_optional

    def _on_change(self) -> None:
        if has_agent_bakery():
            import cmk.gui.cee.agent_bakery as agent_bakery  # pylint: disable=no-name-in-module

            agent_bakery.ruleset_changed(self.name)

    # Returns the outcoming value or None and a list of matching rules. These are pairs
    # of rule_folder and rule_number
    def analyse_ruleset(self, hostname, svc_desc_or_item, svc_desc):
        resultlist = []
        resultdict: Dict[str, Any] = {}
        effectiverules = []
        for folder, rule_index, rule in self.get_rules():
            if rule.is_disabled():
                continue

            if not rule.matches_host_and_item(
                Folder.current(), hostname, svc_desc_or_item, svc_desc
            ):
                continue

            if self.match_type() == "all":
                resultlist.append(rule.value)
                effectiverules.append((folder, rule_index, rule))

            elif self.match_type() == "list":
                assert isinstance(rule.value, list)
                resultlist += rule.value
                effectiverules.append((folder, rule_index, rule))

            elif self.match_type() == "dict":
                # It may happen that a ruleset started with non-dict values. For example
                # a ruleset that has only has a WARN and CRIT threshold in a two element
                # tuple.
                # When we then have to extend the ruleset to hold dict values and change
                # the match type to dict, we normally do this by adding a top-level
                # Transform() valuespec which encapsulates the Dictionary() valuespec.
                # The logic for migrating the parameters is implemented in the forth()
                # method of the transform.
                # Users which already have saved rules using the previous valuespec now
                # have tuples in their ruleset and reach this code with other data
                # structures than dictionaries.
                # We currently have no 100% safe way of automatically fixing this on the
                # fly. The best we can do is print a meaningful error message to the user.
                # Would be better to do these transforms once during site update. The
                # cmk-update-config command would be a good place to do this.
                if not isinstance(rule.value, dict):
                    raise MKGeneralException(
                        _(
                            'Failed to process rule #%d of ruleset "%s" in folder "%s". '
                            "The value of a rule is incompatible to the current rule "
                            "specification. You can try fix this by opening the rule "
                            "for editing and save the rule again without modification."
                        )
                        % (rule_index, self.title(), folder.title())
                    )

                new_result = rule.value.copy()
                new_result.update(resultdict)
                resultdict = new_result
                effectiverules.append((folder, rule_index, rule))

            else:
                return rule.value, [(folder, rule_index, rule)]

        if self.match_type() in ("list", "all"):
            return resultlist, effectiverules

        if self.match_type() == "dict":
            return resultdict, effectiverules

        return None, []  # No match


class Rule:
    @classmethod
    def from_ruleset_defaults(cls, folder: CREFolder, ruleset: Ruleset) -> Rule:
        return Rule(
            utils.gen_id(),
            folder,
            ruleset,
            RuleConditions(folder.path()),
            RuleOptions(
                disabled=False,
                description="",
                comment="",
                docu_url="",
                predefined_condition_id=None,
            ),
            ruleset.valuespec().default_value(),
        )

    def __init__(
        self,
        id_: str,
        folder: CREFolder,
        ruleset: Ruleset,
        conditions: RuleConditions,
        options: RuleOptions,
        value: RuleValue,
    ) -> None:
        self.ruleset: Ruleset = ruleset
        self.folder: CREFolder = folder
        self.conditions: RuleConditions = conditions
        self.id: str = id_
        self.rule_options: RuleOptions = options
        self.value: RuleValue = value

    def clone(self, preserve_id: bool = False) -> Rule:
        return Rule(
            self.id if preserve_id else utils.gen_id(),
            self.folder,
            self.ruleset,
            self.conditions.clone(),
            dataclasses.replace(self.rule_options),
            self.value,
        )

    @classmethod
    def from_config(
        cls,
        folder: CREFolder,
        ruleset: Ruleset,
        rule_config: Any,
    ) -> Rule:
        try:
            if isinstance(rule_config, dict):
                return cls._parse_dict_rule(
                    folder,
                    ruleset,
                    rule_config,
                )
            raise NotImplementedError()
        except Exception:
            logger.exception("error parsing rule")
            raise MKGeneralException(_("Invalid rule <tt>%s</tt>") % (rule_config,))

    @classmethod
    def _parse_dict_rule(
        cls,
        folder: CREFolder,
        ruleset: Ruleset,
        rule_config: Dict[Any, Any],
    ) -> Rule:
        # cmk-update-config uses this to load rules from the config file for rewriting them To make
        # this possible, we need to accept missing "id" fields here. During runtime this is not
        # needed anymore, since cmk-update-config has updated all rules from the user configuration.
        id_ = rule_config["id"] if "id" in rule_config else utils.gen_id()
        assert isinstance(id_, str)

        rule_options = rule_config.get("options", {})
        assert all(isinstance(k, str) for k in rule_options)

        conditions = rule_config["condition"].copy()

        # Is known because of the folder associated with this object. Remove the
        # rendundant information here. It will be added dynamically in to_config()
        # for writing it back
        conditions.pop("host_folder", None)

        rule_conditions = RuleConditions(folder.path())
        rule_conditions.from_config(conditions)

        return cls(
            id_,
            folder,
            ruleset,
            rule_conditions,
            RuleOptions.from_config(rule_options),
            rule_config["value"],
        )

    def to_config(self) -> RuleSpec:
        # Special case: The main folder must not have a host_folder condition, because
        # these rules should also affect non WATO hosts.
        for_config = (
            self.conditions.to_config_with_folder_macro()
            if not self.folder.is_root()
            else self.conditions.to_config_without_folder()
        )
        return self._to_config(for_config)

    def to_web_api(self) -> RuleSpec:
        return self._to_config(self.conditions.to_config_without_folder())

    def to_log(self) -> RuleSpec:
        """Returns a JSON compatible format suitable for logging, where passwords are replaced"""
        return self._to_config(
            self.conditions.to_config_without_folder(), self.ruleset.valuespec().value_to_json_safe
        )

    def _to_config(
        self, conditions: RuleConditionsSpec, value_func: Callable[[Any], Any] = lambda x: x
    ) -> RuleSpec:
        rule_spec: RuleSpec = {
            "id": self.id,
            "value": value_func(self.value),
            "condition": conditions,
        }
        if options := self.rule_options.to_config():
            rule_spec["options"] = options
        return rule_spec

    def object_ref(self) -> ObjectRef:
        return ObjectRef(
            ObjectRefType.Rule,
            self.id,
            {
                "ruleset": self.ruleset.name,
            },
        )

    def is_ineffective(self) -> bool:
        """Whether or not this rule does not match at all

        Interesting: This has always tried host matching. Whether or not a service ruleset
        does not match any service has never been tested. Probably because this would be
        too expensive."""
        hosts = Host.all()
        for host_name, host in hosts.items():
            if self.matches_host_conditions(host.folder(), host_name):
                return False
        return True

    def matches_host_conditions(self, host_folder, hostname):
        """Whether or not the given folder/host matches this rule
        This only evaluates host related conditions, even if the ruleset is a service ruleset."""
        return not any(
            True
            for _r in self.get_mismatch_reasons(
                host_folder,
                hostname,
                svc_desc_or_item=None,
                svc_desc=None,
                only_host_conditions=True,
            )
        )

    def matches_host_and_item(self, host_folder, hostname, svc_desc_or_item, svc_desc):
        """Whether or not the given folder/host/item matches this rule"""
        return not any(
            True
            for _r in self.get_mismatch_reasons(
                host_folder, hostname, svc_desc_or_item, svc_desc, only_host_conditions=False
            )
        )

    def get_mismatch_reasons(
        self, host_folder, hostname, svc_desc_or_item, svc_desc, only_host_conditions
    ):
        """A generator that provides the reasons why a given folder/host/item not matches this rule"""
        host = host_folder.host(hostname)
        if host is None:
            raise MKGeneralException("Failed to get host from folder %r." % host_folder.path())

        # BE AWARE: Depending on the service ruleset the service_description of
        # the rules is only a check item or a full service description. For
        # example the check parameters rulesets only use the item, and other
        # service rulesets like disabled services ruleset use full service
        # descriptions.
        #
        # The service_description attribute of the match_object must be set to
        # either the item or the full service description, depending on the
        # ruleset, but the labels of a service need to be gathered using the
        # real service description.
        if only_host_conditions:
            match_object = ruleset_matcher.RulesetMatchObject(hostname)
        elif self.ruleset.item_type() == "service":
            match_object = cmk.base.export.ruleset_match_object_of_service(
                hostname, svc_desc_or_item
            )
        elif self.ruleset.item_type() == "item":
            match_object = cmk.base.export.ruleset_match_object_for_checkgroup_parameters(
                hostname, svc_desc_or_item, svc_desc
            )
        elif not self.ruleset.item_type():
            match_object = ruleset_matcher.RulesetMatchObject(hostname)
        else:
            raise NotImplementedError()

        match_service_conditions = self.ruleset.rulespec.is_for_services
        if only_host_conditions:
            match_service_conditions = False

        for reason in self._get_mismatch_reasons_of_match_object(
            match_object, match_service_conditions
        ):
            yield reason

    def _get_mismatch_reasons_of_match_object(self, match_object, match_service_conditions):
        matcher = cmk.base.export.get_ruleset_matcher()

        rule_dict = self.to_config()
        rule_dict["condition"]["host_folder"] = self.folder.path_for_gui_rule_matching()

        # The cache uses some id(ruleset) to build indexes for caches. When we are using
        # dynamically allocated ruleset list objects, that are quickly invalidated, it
        # may happen that the address space is reused for other objects, resulting in
        # duplicate id() results for different rulesets (because ID returns the memory
        # address the object is located at).
        # Since we do not work with regular rulesets here, we need to clear the cache
        # (that is not useful in this situation)
        matcher.ruleset_optimizer.clear_ruleset_caches()

        ruleset = [rule_dict]

        if match_service_conditions:
            if list(
                matcher.get_service_ruleset_values(
                    match_object, ruleset, is_binary=self.ruleset.rulespec.is_binary_ruleset
                )
            ):
                return
        else:
            if list(
                matcher.get_host_ruleset_values(
                    match_object, ruleset, is_binary=self.ruleset.rulespec.is_binary_ruleset
                )
            ):
                return

        yield _("The rule does not match")

    def matches_search(self, search_options: SearchOptions) -> bool:
        if "rule_folder" in search_options and self.folder.name() not in self._get_search_folders(
            search_options
        ):
            return False

        if (
            "rule_disabled" in search_options
            and search_options["rule_disabled"] != self.is_disabled()
        ):
            return False

        if (
            "rule_predefined_condition" in search_options
            and search_options["rule_predefined_condition"] != self.predefined_condition_id()
        ):
            return False

        if (
            "rule_ineffective" in search_options
            and search_options["rule_ineffective"] != self.is_ineffective()
        ):
            return False

        if not _match_search_expression(search_options, "rule_description", self.description()):
            return False

        if not _match_search_expression(search_options, "rule_comment", self.comment()):
            return False

        value_text = None
        try:
            value_text = str(self.ruleset.valuespec().value_to_html(self.value))
        except Exception as e:
            logger.exception("error searching ruleset %s", self.ruleset.title())
            html.show_warning(
                _("Failed to search rule of ruleset '%s' in folder '%s' (%r): %s")
                % (self.ruleset.title(), self.folder.title(), self.to_config(), e)
            )

        if value_text is not None and not _match_search_expression(
            search_options, "rule_value", value_text
        ):
            return False

        if self.conditions.host_list and not _match_one_of_search_expression(
            search_options, "rule_host_list", self.conditions.host_list[0]
        ):
            return False

        if self.conditions.item_list and not _match_one_of_search_expression(
            search_options, "rule_item_list", self.conditions.item_list[0]
        ):
            return False

        to_search = (
            [
                self.comment(),
                self.description(),
            ]
            + (self.conditions.host_list[0] if self.conditions.host_list else [])
            + (self.conditions.item_list[0] if self.conditions.item_list else [])
        )

        if value_text is not None:
            to_search.append(value_text)

        if not _match_one_of_search_expression(search_options, "fulltext", to_search):
            return False

        searching_host_tags = search_options.get("rule_hosttags")
        if searching_host_tags:
            for host_tag in searching_host_tags:
                if host_tag not in self.conditions.tag_list:
                    return False

        return True

    def _get_search_folders(self, search_options: SearchOptions) -> List[str]:
        current_folder, do_recursion = search_options["rule_folder"]
        current_folder = Folder.folder(current_folder)
        search_in_folders = [current_folder.name()]
        if do_recursion:
            search_in_folders = [
                x.split("/")[-1] for x, _y in current_folder.recursive_subfolder_choices()
            ]
        return search_in_folders

    def index(self) -> int:
        return self.ruleset.get_folder_rules(self.folder).index(self)

    def is_disabled(self) -> bool:
        # TODO consolidate with cmk.utils.rulesets.ruleset_matcher.py::_is_disabled
        return bool(self.rule_options.disabled)

    def description(self) -> str:
        return self.rule_options.description

    def comment(self) -> str:
        return self.rule_options.comment

    def predefined_condition_id(self) -> Optional[str]:
        """When a rule refers to a predefined condition return the ID

        The predefined conditions are a pure WATO feature. These are resolved when writing
        the configuration down for Check_MK base. The configured condition ID is preserved
        in the rule options for the moment.
        """
        # TODO: Once we switched the rule format to be dict base, we can move this key to the conditions dict
        return self.rule_options.predefined_condition_id

    def update_conditions(self, conditions: RuleConditions) -> None:
        self.conditions = conditions

    def get_rule_conditions(self) -> RuleConditions:
        return self.conditions

    def is_discovery_rule_of(self, host: CREHost) -> bool:
        return (
            self.conditions.host_name == [host.name()]
            and self.conditions.host_tags == {}
            and self.conditions.has_only_explicit_service_conditions()
            and self.folder.is_transitive_parent_of(host.folder())
        )

    def is_discovery_rule(self) -> bool:
        return bool(
            self.conditions.host_name
            and len(self.conditions.host_name) == 1
            and isinstance(self.conditions.host_name, list)
            and isinstance(self.conditions.host_name[0], str)
            and self.conditions.host_tags == {}
            and self.conditions.has_only_explicit_service_conditions()
        )

    def replace_explicit_host_condition(self, old_name: str, new_name: str) -> bool:
        """Does an in-place(!) replacement of explicit (non regex) hostnames in rules"""
        if self.conditions.host_name is None:
            return False

        did_rename = False
        _negate, host_conditions = ruleset_matcher.parse_negated_condition_list(
            self.conditions.host_name
        )

        for index, condition in enumerate(host_conditions):
            if condition == old_name:
                host_conditions[index] = new_name
                did_rename = True

        return did_rename


def _match_search_expression(search_options: SearchOptions, attr_name: str, search_in: str) -> bool:
    if attr_name not in search_options:
        return True  # not searched for this. Matching!

    return bool(search_in and re.search(search_options[attr_name], search_in, re.I) is not None)


def _match_one_of_search_expression(
    search_options: SearchOptions, attr_name: str, search_in_list: List[str]
) -> bool:
    for search_in in search_in_list:
        if _match_search_expression(search_options, attr_name, search_in):
            return True
    return False


def service_description_to_condition(service_description: str) -> HostOrServiceConditionRegex:
    r"""Packs a service description to be used as explicit match condition

    >>> service_description_to_condition("abc")
    {'$regex': 'abc$'}
    >>> service_description_to_condition("a / b / c \\ d \\ e")
    {'$regex': 'a / b / c \\\\ d \\\\ e$'}
    """
    return {"$regex": "%s$" % escape_regex_chars(service_description)}
