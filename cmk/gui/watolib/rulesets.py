#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

import dataclasses
import itertools
import os
import pprint
import re
from collections.abc import Callable, Container, Generator, Iterator, Mapping
from enum import auto, Enum
from pathlib import Path
from typing import Any, assert_never, cast, Final, Iterable

import cmk.utils.rulesets.ruleset_matcher as ruleset_matcher
import cmk.utils.store as store
from cmk.utils.exceptions import MKGeneralException
from cmk.utils.labels import Labels
from cmk.utils.object_diff import make_diff, make_diff_text
from cmk.utils.regex import escape_regex_chars
from cmk.utils.rulesets.ruleset_matcher import (
    RuleConditionsSpec,
    RuleOptionsSpec,
    RulesetName,
    RuleSpec,
    TagConditionNE,
    TaggroupIDToTagCondition,
    TagIDToTaggroupID,
)
from cmk.utils.tags import TagID
from cmk.utils.type_defs import HostOrServiceConditionRegex, HostOrServiceConditions

# Tolerate this for 1.6. Should be cleaned up in future versions,
# e.g. by trying to move the common code to a common place
import cmk.base.export  # pylint: disable=cmk-module-layer-violation

from cmk.gui import hooks, utils
from cmk.gui.config import active_config, register_post_config_load_hook
from cmk.gui.exceptions import MKUserError
from cmk.gui.htmllib.html import html
from cmk.gui.i18n import _, _l
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
from cmk.gui.watolib.rulespecs import Rulespec, rulespec_group_registry, rulespec_registry
from cmk.gui.watolib.utils import ALL_HOSTS, ALL_SERVICES, NEGATE, wato_root_dir

# Make the GUI config module reset the base config to always get the latest state of the config
register_post_config_load_hook(cmk.base.export.reset_config)

FolderPath = str
SearchOptions = dict[str, Any]
RuleValue = Any


# This macro is needed to make the to_config() methods be able to use native pprint/repr for the
# ruleset data structures. Have a look at to_config() for further information.
_FOLDER_PATH_MACRO = "%#%FOLDER_PATH%#%"


@dataclasses.dataclass()
class RuleOptions:
    disabled: bool | None
    description: str
    comment: str
    docu_url: str
    predefined_condition_id: str | None = None

    @classmethod
    def from_config(
        cls,
        rule_options_config: RuleOptionsSpec,
    ) -> RuleOptions:
        return cls(
            disabled=rule_options_config.get("disabled", None),
            description=rule_options_config.get("description", ""),
            comment=rule_options_config.get("comment", ""),
            docu_url=rule_options_config.get("docu_url", ""),
            predefined_condition_id=rule_options_config.get("predefined_condition_id"),
        )

    def to_config(self) -> RuleOptionsSpec:
        rule_options_config: RuleOptionsSpec = {}
        if self.disabled is not None:
            rule_options_config["disabled"] = self.disabled
        if self.description:
            rule_options_config["description"] = self.description
        if self.comment:
            rule_options_config["comment"] = self.comment
        if self.docu_url:
            rule_options_config["docu_url"] = self.docu_url
        if self.predefined_condition_id:
            rule_options_config["predefined_condition_id"] = self.predefined_condition_id
        return rule_options_config


class UseHostFolder(Enum):
    NONE = auto()
    MACRO = auto()
    # cmk.gui uses folders like this:
    # subfolder/subsubfolder/...
    # cf. CREFolder.folder, CREFolder.folder_choices etc.
    HOST_FOLDER_FOR_UI = auto()
    # cmk.base sets folders this way when loading the configuration:
    # /wato/subfolder/subsubfolder/...
    # cf. FOLDER_PATH in cmk.base.config
    HOST_FOLDER_FOR_BASE = auto()


class RuleConditions:
    def __init__(
        self,
        host_folder: str,
        host_tags: TaggroupIDToTagCondition | None = None,
        host_labels: Labels | None = None,
        host_name: HostOrServiceConditions | None = None,
        service_description: HostOrServiceConditions | None = None,
        service_labels: Labels | None = None,
    ) -> None:
        self.host_folder: Final = host_folder
        self.host_tags: Final[TaggroupIDToTagCondition] = host_tags or {}
        self.host_labels: Final = host_labels or {}
        self.host_name: Final = host_name
        self.service_description: Final = service_description
        self.service_labels: Final = service_labels or {}

    @classmethod
    def from_config(cls, host_folder: str, conditions: Mapping[str, Any]) -> RuleConditions:
        return cls(
            host_folder=conditions.get("host_folder", host_folder),
            host_tags=conditions.get("host_tags", {}),
            host_labels=conditions.get("host_labels", {}),
            host_name=conditions.get("host_name"),
            service_description=conditions.get("service_description"),
            service_labels=conditions.get("service_labels", {}),
        )

    def to_config(self, use_host_folder: UseHostFolder) -> RuleConditionsSpec:
        """Create serializable data structure for the conditions

        In the Setup folder hierarchy each folder may have a rules.mk which
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

        match use_host_folder:
            case UseHostFolder.NONE:
                pass
            case UseHostFolder.MACRO:
                cfg["host_folder"] = _FOLDER_PATH_MACRO
            case UseHostFolder.HOST_FOLDER_FOR_UI:
                cfg["host_folder"] = self.host_folder
            case UseHostFolder.HOST_FOLDER_FOR_BASE:
                cfg["host_folder"] = str(Path("/wato") / self.host_folder)
            case _:
                assert_never(use_host_folder)

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

    # Compatibility code for pre 1.6 Setup code
    @property
    def tag_list(self) -> Container[TagID | None]:
        tag_list = []
        for tag_spec in self.host_tags.values():
            is_not = isinstance(tag_spec, dict) and "$ne" in tag_spec
            if isinstance(tag_spec, dict) and is_not:
                tag_id = cast(TagConditionNE, tag_spec)["$ne"]
            else:
                tag_id = cast(TagID | None, tag_spec)

            tag_list.append(("!%s" % tag_id) if is_not else tag_id)
        return tag_list

    def tag_conditions_to_tags_list(self) -> set[TagID]:
        tags: set[TagID] = set()
        for condition in self.host_tags.values():
            match condition:
                case {"$or": list() as or_list}:
                    tags.update({tag_id for tag_id in or_list if tag_id is not None})
                case {"$nor": list() as nor_list}:
                    tags.update(
                        {TagID("!%s" % tag_id) for tag_id in nor_list if tag_id is not None}
                    )
                case {"$ne": str() as tag_id}:
                    tags.add(TagID("!%s" % tag_id))
                case str():
                    tags.add(condition)
                case _:
                    raise MKGeneralException("Invalid tag condition: %s" % condition)

        return tags

    # Compatibility code for pre 1.6 Setup code
    @property
    def host_list(self):
        return self._condition_list(self.host_name, is_service=False)

    # Compatibility code for pre 1.6 Setup code
    @property
    def item_list(self):
        return self._condition_list(self.service_description, is_service=True)

    def _condition_list(
        self, object_list: HostOrServiceConditions | None, is_service: bool
    ) -> tuple[list[str], bool] | None:
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

    def __init__(self, rulesets: dict[RulesetName, Ruleset]) -> None:
        super().__init__()
        # A dictionary containing all ruleset objects of the collection.
        # The name of the ruleset is used as key in the dict.
        self._rulesets = rulesets
        self._unknown_rulesets: dict[str, dict[str, list]] = {}

    @staticmethod
    def _initialize_rulesets(
        only_varname: RulesetName | None = None,
    ) -> dict[RulesetName, Ruleset]:
        tag_to_group_map = ruleset_matcher.get_tag_to_group_map(active_config.tags)
        varnames = [only_varname] if only_varname else rulespec_registry.keys()
        return {varname: Ruleset(varname, tag_to_group_map) for varname in varnames}

    def _load_folder_rulesets(
        self, folder: CREFolder, only_varname: RulesetName | None = None
    ) -> None:
        path = folder.rules_file_path()

        if not os.path.exists(path):
            return  # Do not initialize rulesets when no rule at all exists

        self.replace_folder_config(
            folder,
            store.load_mk_file(
                path, {**self._context_helpers(folder), **self._prepare_empty_rulesets()}
            ),
            only_varname,
        )

    @staticmethod
    def _context_helpers(folder: CREFolder) -> Mapping[str, object]:
        return {
            "ALL_HOSTS": ALL_HOSTS,
            "ALL_SERVICES": ALL_SERVICES,
            "NEGATE": NEGATE,
            "FOLDER_PATH": folder.path(),
        }

    @staticmethod
    def _prepare_empty_rulesets() -> Mapping[str, list[object] | dict[str, object]]:
        """Prepare empty rulesets so that rules.mk has something to append to

        We need to initialize all variables here, even when only loading with only_varname.
        """

        def _make_dict() -> list[object] | dict[str, object]:
            return {}

        return dict(
            ((name.split(":")[0], _make_dict()) if ":" in name else (name, []))
            for name in rulespec_registry.keys()
        )

    def replace_folder_config(  # type:ignore[no-untyped-def]
        self, folder: CREFolder, loaded_file_config, only_varname: RulesetName | None = None
    ) -> None:
        if only_varname:
            variable_names_to_load = [only_varname]
        else:

            def varnames_from_item(name: str, value: object) -> list[str]:
                if isinstance(value, dict):
                    return [f"{name}:{key}" for key in value]
                if isinstance(value, list):
                    return [name]
                return []

            helpers = self._context_helpers(folder)
            variable_names_to_load = [
                name
                for config_varname, value in loaded_file_config.items()
                for name in varnames_from_item(config_varname, value)
                if name not in helpers
            ]

        for varname in variable_names_to_load:
            if ":" in varname:
                config_varname, subkey = varname.split(":", 1)
                rulegroup_config = loaded_file_config.get(config_varname, {})
                if subkey not in rulegroup_config:
                    continue  # Nothing configured: nothing left to do

                ruleset_config = rulegroup_config[subkey]
            else:
                config_varname, subkey = varname, None
                ruleset_config = loaded_file_config.get(config_varname, [])

            if not ruleset_config:
                continue  # Nothing configured: nothing left to do

            if varname in self._rulesets:
                self._rulesets[varname].replace_folder_config(folder, ruleset_config)
            else:
                self._unknown_rulesets.setdefault(folder.path(), {})[varname] = ruleset_config

    def save(self) -> None:
        raise NotImplementedError()

    def save_folder(self, folder: CREFolder) -> None:
        raise NotImplementedError()

    def _save_folder(self, folder: CREFolder) -> None:
        store.mkdir(folder.get_root_dir())

        content = [
            *(
                ruleset.to_config(folder)
                for _name, ruleset in sorted(self._rulesets.items())
                if not ruleset.is_empty_in_folder(folder)
            ),
            *(
                Ruleset.format_raw_value(varname, raw_value, False)
                for varname, raw_value in sorted(
                    self._unknown_rulesets.get(folder.path(), {}).items()
                )
            ),
        ]

        rules_file_path = folder.rules_file_path()
        try:
            # Remove empty rules files. This prevents needless reads
            if not content:
                try:
                    os.unlink(rules_file_path)
                except FileNotFoundError:
                    pass
                return

            store.save_mk_file(
                rules_file_path,
                # Adding this instead of the full path makes it easy to move config
                # files around. The real FOLDER_PATH will be added dynamically while
                # loading the file in cmk.base.config
                "".join(content).replace("'%s'" % _FOLDER_PATH_MACRO, "'/%s/' % FOLDER_PATH"),
                add_header=not active_config.wato_use_git,
            )
        finally:
            if may_use_redis():
                get_wato_redis_client().folder_updated(folder.filesystem_path())

    def exists(self, name: RulesetName) -> bool:
        return name in self._rulesets

    def get(self, name: RulesetName, deflt=None) -> Ruleset:  # type:ignore[no-untyped-def]
        return self._rulesets[name]

    def set(self, name: RulesetName, ruleset: Ruleset) -> None:
        self._rulesets[name] = ruleset

    def delete(self, name: RulesetName):  # type:ignore[no-untyped-def]
        del self._rulesets[name]

    def get_rulesets(self) -> Mapping[RulesetName, Ruleset]:
        return self._rulesets


class AllRulesets(RulesetCollection):
    def _load_rulesets_recursively(
        self, folder: CREFolder, only_varname: RulesetName | None = None
    ) -> None:

        if may_use_redis():
            self._load_rulesets_via_redis(folder, only_varname)
            return

        for subfolder in folder.subfolders():
            self._load_rulesets_recursively(subfolder, only_varname)

        self._load_folder_rulesets(folder, only_varname)

    def _load_rulesets_via_redis(
        self, folder: CREFolder, only_varname: RulesetName | None = None
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

    @staticmethod
    def load_all_rulesets() -> AllRulesets:
        """Load all rules of all folders"""
        rulesets = RulesetCollection._initialize_rulesets()
        self = AllRulesets(rulesets)
        self._load_rulesets_recursively(Folder.root_folder())
        return self

    def save_folder(self, folder: CREFolder) -> None:
        self._save_folder(folder)

    def save(self) -> None:
        """Save all rulesets of all folders recursively"""
        self._save_rulesets_recursively(Folder.root_folder())

    def _save_rulesets_recursively(self, folder: CREFolder) -> None:
        for subfolder in folder.subfolders():
            self._save_rulesets_recursively(subfolder)

        self._save_folder(folder)


class SingleRulesetRecursively(AllRulesets):
    # Load single ruleset from all folders
    @staticmethod
    def load_single_ruleset_recursively(name: RulesetName) -> SingleRulesetRecursively:
        rulesets = RulesetCollection._initialize_rulesets(only_varname=name)
        self = SingleRulesetRecursively(rulesets)
        self._load_rulesets_recursively(Folder.root_folder(), only_varname=name)
        return self

    def save_folder(self, folder: CREFolder) -> None:
        raise NotImplementedError()


class FolderRulesets(RulesetCollection):
    def __init__(
        self,
        rulesets: dict[RulesetName, Ruleset],
        *,
        folder: CREFolder,
    ) -> None:
        super().__init__(rulesets)
        self._folder: Final = folder

    @staticmethod
    def load_folder_rulesets(folder: CREFolder) -> FolderRulesets:
        rulesets = RulesetCollection._initialize_rulesets()
        self = FolderRulesets(rulesets, folder=folder)
        self._load_folder_rulesets(folder)
        return self

    def save(self) -> None:
        self._save_folder(self._folder)


class FilteredRulesetCollection:
    def __init__(self, rulesets: Mapping[RulesetName, Ruleset]) -> None:
        super().__init__()
        self._rulesets: Final = rulesets

    def get_rulesets(self) -> Mapping[RulesetName, Ruleset]:
        return self._rulesets

    @classmethod
    def filter(
        cls,
        origin: Mapping[RulesetName, Ruleset],
        *,
        key: Callable[[Ruleset], bool],
    ) -> FilteredRulesetCollection:
        return cls({name: ruleset for name, ruleset in origin.items() if key(ruleset)})


class Ruleset:
    # These constants are used to give a name to positions within the ruleset.
    # mylist[-1] is the last element, mylist[0] is the first. See `move_to_folder`.
    TOP = 0
    BOTTOM = -1

    def __init__(
        self,
        name: RulesetName,
        tag_to_group_map: TagIDToTaggroupID,
        rulespec: Rulespec | None = None,
    ) -> None:
        super().__init__()
        self.name: Final = name
        self.tag_to_group_map: Final = tag_to_group_map
        self.rulespec: Final = rulespec_registry[name] if rulespec is None else rulespec

        # Holds list of the rules. Using the folder paths as keys.
        self._rules: dict[FolderPath, list[Rule]] = {}
        self._rules_by_id: dict[str, Rule] = {}

        # Temporary needed during search result processing
        self.search_matching_rules: list[Rule] = []

        # Converts pre 1.6 tuple rulesets in place to 1.6+ format
        self.tuple_transformer = ruleset_matcher.RulesetToDictTransformer(
            tag_to_group_map=tag_to_group_map
        )

    def clone(self):
        cloned = Ruleset(self.name, self.tag_to_group_map, self.rulespec)
        for folder, _rule_index, rule in self.get_rules():
            cloned.append_rule(folder, rule)
        return cloned

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

    def get_rules(self) -> list[tuple[CREFolder, int, Rule]]:
        rules = []
        for _folder_path, folder_rules in self._rules.items():
            for rule_index, rule in enumerate(folder_rules):
                rules.append((rule.folder, rule_index, rule))
        return sorted(
            rules, key=lambda x: (x[0].path().split("/"), len(rules) - x[1]), reverse=True
        )

    def get_folder_rules(self, folder: CREFolder) -> list[Rule]:
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
            _l('Cloned rule from rule %s in ruleset "%s" in folder "%s"')
            % (orig_rule.id, self.title(), rule.folder.alias_path()),
            sites=rule.folder.all_site_ids(),
            diff_text=self.diff_rules(None, rule),
            object_ref=rule.object_ref(),
        )

    def move_to_folder(
        self,
        rule: Rule,
        folder: CREFolder,
        index: int = BOTTOM,
    ) -> None:
        source_rules = self._rules[rule.folder.path()]
        dest_rules = self._rules.setdefault(folder.path(), [])

        # The actual move
        source_rules.remove(rule)
        if index == Ruleset.BOTTOM:
            dest_rules.append(rule)
        else:
            dest_rules.insert(index, rule)
        rule.folder = folder

        self._on_change()

    def append_rule(self, folder: CREFolder, rule: Rule) -> int:
        rules = self._rules.setdefault(folder.path(), [])
        index = len(rules)
        rules.append(rule)
        self._rules_by_id[rule.id] = rule
        self._on_change()
        return index

    def insert_rule_after(self, rule: Rule, after: Rule) -> None:
        rules = self._rules[rule.folder.path()]
        index = rules.index(after) + 1
        rules.insert(index, rule)
        self._rules_by_id[rule.id] = rule
        self._on_change()

    def replace_folder_config(  # type:ignore[no-untyped-def]
        self,
        folder: CREFolder,
        rules_config,
    ) -> None:
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
        )

        for rule_config in rules_config:
            rule = Rule.from_config(folder, self, rule_config)
            self._rules[folder.path()].append(rule)
            self._rules_by_id[rule.id] = rule

    def to_config(self, folder: CREFolder) -> str:
        return self.format_raw_value(
            self.name,
            (r.to_config() for r in self._rules[folder.path()]),
            self.is_optional(),
        )

    @staticmethod
    def format_raw_value(name: str, rule_specs: Iterable[RuleSpec], is_optional: bool) -> str:
        content = ""

        if ":" in name:
            dictname, subkey = name.split(":")
            varname = f"{dictname}[{subkey!r}]"

            content += f"\n{dictname}.setdefault({subkey!r}, [])\n"
        else:
            varname = name

            content += "\nglobals().setdefault(%r, [])\n" % (varname)

            if is_optional:
                content += f"\nif {varname} is None:\n    {varname} = []\n"

        content += "\n%s = [\n" % varname
        for rule_spec in rule_specs:
            # When using pprint we get a deterministic representation of the
            # data structures because it cares about sorting of the dict keys
            if active_config.wato_use_git:
                text = pprint.pformat(rule_spec)
            else:
                text = repr(rule_spec)

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

    def diff_rules(self, old: Rule | None, new: Rule) -> str:
        """Diff two rules, masking secrets and serializing the rule value to a log-friendly format"""
        if old is None:
            return make_diff_text({}, new.to_log())
        return old.diff_to(new)

    def edit_rule(self, orig_rule: Rule, rule: Rule) -> None:
        folder_rules = self._rules[orig_rule.folder.path()]
        index = folder_rules.index(orig_rule)

        folder_rules[index] = rule

        add_change(
            "edit-rule",
            _l('Changed properties of rule #%d in ruleset "%s" in folder "%s"')
            % (index, self.title(), rule.folder.alias_path()),
            sites=rule.folder.all_site_ids(),
            diff_text=self.diff_rules(orig_rule, rule),
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
                _l('Deleted rule #%d in ruleset "%s" in folder "%s"')
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
            _l('Moved rule %s from position #%d to #%d in ruleset "%s" in folder "%s"')
            % (rule.id, old_index, index, self.title(), rule.folder.alias_path()),
            sites=rule.folder.all_site_ids(),
            object_ref=self.object_ref(),
        )

    # TODO: Remove these getters
    def valuespec(self) -> ValueSpec:
        return self.rulespec.valuespec

    def help(self) -> None | str | HTML:
        try:
            return self.rulespec.help
        except NameError:
            # This prevents the Ruleset page (e.g. 'Service monitoring rules')
            # from crashing if the module cannot be loaded due to missing
            # imports. This can be the case with external packages such as MKPs
            # from the exchange.
            return None

    def title(self) -> str | None:
        return self.rulespec.title

    def item_type(self) -> str | None:
        return self.rulespec.item_type

    def item_name(self) -> str | None:
        return self.rulespec.item_name

    def item_help(self) -> None | str | HTML:
        return self.rulespec.item_help

    def item_enum(self) -> DropdownChoiceEntries | None:
        return self.rulespec.item_enum

    def match_type(self) -> str:
        return self.rulespec.match_type

    def is_deprecated(self) -> bool:
        return self.rulespec.is_deprecated

    def is_optional(self) -> bool:
        return self.rulespec.is_optional

    def _on_change(self) -> None:
        hooks.call("ruleset-changed", self.name)

    # Returns the outcoming value or None and a list of matching rules. These are pairs
    # of rule_folder and rule_number
    def analyse_ruleset(  # type:ignore[no-untyped-def]
        self,
        hostname,
        svc_desc_or_item,
        svc_desc,
        service_labels: Labels,
    ):
        resultlist = []
        resultdict: dict[str, Any] = {}
        effectiverules = []
        for folder, rule_index, rule in self.get_rules():
            if rule.is_disabled():
                continue

            if not rule.matches_host_and_item(
                Folder.current(),
                hostname,
                svc_desc_or_item,
                svc_desc,
                service_labels=service_labels,
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
        rule_config: dict[Any, Any],
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

        return cls(
            id_,
            folder,
            ruleset,
            RuleConditions.from_config(folder.path(), conditions),
            RuleOptions.from_config(rule_options),
            rule_config["value"],
        )

    def value_masked(self) -> RuleValue:
        """Return a copy of the value with all secrets masked"""
        return self.ruleset.valuespec().mask(self.value)

    def diff_to(self, other: Rule) -> str:
        """Diff to another rule, masking secrets"""
        # We cannot mask passwords after diffing because the diff result has no type information.
        # When masking before diffing, however, we won't detect changed passwords, so we have to add
        # that extra info.
        # If masking changes the diff, secrets must have changed.
        if make_diff(self.value, other.value) != make_diff(
            self.value_masked(), other.value_masked()
        ):
            report = _("Redacted secrets changed.")
            if diff := make_diff(self.to_log(), other.to_log()):
                report = diff + "\n" + report
            return report

        return make_diff_text(self.to_log(), other.to_log())

    def to_config(
        self,
        use_host_folder: UseHostFolder = UseHostFolder.MACRO,
    ) -> RuleSpec:
        # Special case: The main folder must not have a host_folder condition, because
        # these rules should also affect non Setup hosts.
        return self._to_config(
            use_host_folder=UseHostFolder.NONE if self.folder.is_root() else use_host_folder
        )

    def to_web_api(self) -> RuleSpec:
        return self._to_config(use_host_folder=UseHostFolder.NONE)

    def to_log(self) -> RuleSpec:
        """Returns a JSON compatible format suitable for logging, where passwords are replaced"""
        vs = self.ruleset.valuespec()
        return self._to_config(
            use_host_folder=UseHostFolder.NONE,
            transform_value=lambda value: vs.value_to_json(vs.mask(self.value)),
        )

    def _to_config(
        self,
        *,
        use_host_folder: UseHostFolder,
        transform_value: Callable[[RuleValue], RuleValue] | None = None,
    ) -> RuleSpec:
        rule_spec = RuleSpec(
            id=self.id,
            value=transform_value(self.value) if transform_value else self.value,
            condition=self.conditions.to_config(use_host_folder),
        )
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
                service_labels={},
            )
        )

    def matches_host_and_item(  # type:ignore[no-untyped-def]
        self,
        host_folder,
        hostname,
        svc_desc_or_item,
        svc_desc,
        service_labels: Labels,
    ):
        """Whether or not the given folder/host/item matches this rule"""
        return not any(
            True
            for _r in self.get_mismatch_reasons(
                host_folder,
                hostname,
                svc_desc_or_item,
                svc_desc,
                only_host_conditions=False,
                service_labels=service_labels,
            )
        )

    def get_mismatch_reasons(  # type:ignore[no-untyped-def]
        self,
        host_folder,
        hostname,
        svc_desc_or_item,
        svc_desc,
        only_host_conditions,
        service_labels: Labels,
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
                hostname, svc_desc_or_item, svc_labels=service_labels
            )
        elif self.ruleset.item_type() == "item":
            match_object = cmk.base.export.ruleset_match_object_for_checkgroup_parameters(
                hostname, svc_desc_or_item, svc_desc, svc_labels=service_labels
            )
        elif not self.ruleset.item_type():
            match_object = ruleset_matcher.RulesetMatchObject(hostname)
        else:
            raise NotImplementedError()

        match_service_conditions = self.ruleset.rulespec.is_for_services
        if only_host_conditions:
            match_service_conditions = False

        yield from self._get_mismatch_reasons_of_match_object(
            match_object, match_service_conditions
        )

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

    def matches_search(  # pylint: disable=too-many-branches
        self,
        search_options: SearchOptions,
    ) -> bool:
        if "rule_folder" in search_options and self.folder.path() not in self._get_search_folders(
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

        if (searching_host_tags := search_options.get("rule_hosttags")) is not None:
            conditions_tag_set = self.conditions.tag_conditions_to_tags_list()

            for search_condition in searching_host_tags.values():
                match search_condition:
                    case {"$or": list() as one_of}:
                        if conditions_tag_set.isdisjoint(set(one_of)):
                            return False
                    case {"$nor": list() as none_of}:
                        if conditions_tag_set.isdisjoint({f"!{i}" for i in none_of}):
                            return False
                    case {"$ne": str() as not_equal}:
                        if f"!{not_equal}" not in conditions_tag_set:
                            return False
                    case str():
                        if search_condition not in conditions_tag_set:
                            return False
                    case _:
                        raise MKGeneralException(f"Unknown search condition: {search_condition}")

        return True

    def _get_search_folders(self, search_options: SearchOptions) -> list[str]:
        current_folder, do_recursion = search_options["rule_folder"]
        current_folder = Folder.folder(current_folder)
        search_in_folders = [current_folder.path()]
        if do_recursion:
            search_in_folders = [x for x, _y in current_folder.recursive_subfolder_choices()]
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

    def predefined_condition_id(self) -> str | None:
        """When a rule refers to a predefined condition return the ID

        The predefined conditions are a pure Setup feature. These are resolved when writing
        the configuration down for Checkmk base. The configured condition ID is preserved
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
    """
    >>> _match_search_expression({"rule_host_list": "foobar123"}, "rule_host_list", "~.*foo.*")
    True
    >>> _match_search_expression({"rule_host_list": "foobar123"}, "rule_host_list", "foobar123")
    True
    """
    if attr_name not in search_options:
        return True  # not searched for this. Matching!

    if search_in and search_in.startswith("~"):
        return re.search(search_in.lstrip("~"), search_options[attr_name], re.I) is not None

    try:
        return bool(search_in and re.search(search_options[attr_name], search_in, re.I) is not None)
    except re.error as e:
        raise MKUserError("", e.msg) from e


def _match_one_of_search_expression(
    search_options: SearchOptions, attr_name: str, search_in_list: list[str]
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


def rules_grouped_by_folder(
    rules: list[tuple[CREFolder, int, Rule]],
    current_folder: CREFolder,
) -> Generator[tuple[CREFolder, Iterator[tuple[CREFolder, int, Rule]]], None, None]:
    """Get ruleset groups in correct sort order. Sort by title_path() to honor
    renamed folders"""
    sorted_rules: list[tuple[CREFolder, int, Rule]] = sorted(
        rules,
        key=lambda x: (x[0].title_path(), len(rules) - x[1]),
        reverse=True,
    )
    return (
        (folder, folder_rules)  #
        for folder, folder_rules in itertools.groupby(sorted_rules, key=lambda rule: rule[0])
        if folder.is_transitive_parent_of(current_folder)
        or current_folder.is_transitive_parent_of(folder)
    )
