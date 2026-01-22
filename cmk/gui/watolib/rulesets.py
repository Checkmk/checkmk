#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="type-arg"


from __future__ import annotations

import dataclasses
import itertools
import os
import pprint
import re
from collections.abc import (
    Callable,
    Container,
    Generator,
    Iterable,
    Iterator,
    Mapping,
    Sequence,
)
from enum import auto, Enum
from pathlib import Path
from typing import Any, assert_never, cast, Final, Literal, override, TypedDict

from cmk import trace
from cmk.ccc import store
from cmk.ccc.exceptions import MKGeneralException
from cmk.ccc.hostaddress import HostAddress, HostName
from cmk.ccc.regex import escape_regex_chars
from cmk.ccc.version import Edition, edition
from cmk.gui import hooks, utils
from cmk.gui.config import active_config
from cmk.gui.exceptions import MKAuthException, MKUserError
from cmk.gui.form_specs import DEFAULT_VALUE, get_visitor, RawDiskData, VisitorOptions
from cmk.gui.form_specs.generators.config_host_name import create_config_host_name
from cmk.gui.form_specs.unstable import (
    BinaryConditionChoices,
    CommentTextArea,
    ConditionChoices,
    not_empty,
)
from cmk.gui.form_specs.unstable import (
    ListOfStrings as ListOfStringsAPI,
)
from cmk.gui.form_specs.unstable import (
    SingleChoiceElementExtended as SingleChoiceElementExtendedAPI,
)
from cmk.gui.form_specs.unstable import SingleChoiceExtended as SingleChoiceExtendedAPI
from cmk.gui.form_specs.unstable.catalog import Catalog, Locked, Topic, TopicElement
from cmk.gui.form_specs.unstable.time_specific import TimeSpecific
from cmk.gui.form_specs.unstable.validators import HostAddressList
from cmk.gui.hooks import request_memoize
from cmk.gui.htmllib.html import html
from cmk.gui.i18n import _, _l
from cmk.gui.log import logger
from cmk.gui.logged_in import user
from cmk.gui.oauth2_connections.watolib.store import load_oauth2_connections
from cmk.gui.utils.html import HTML
from cmk.gui.utils.labels import get_labels_from_core, LabelType
from cmk.gui.valuespec import DropdownChoiceEntries
from cmk.gui.watolib.check_mk_automations import (
    analyze_host_rule_effectiveness,
    analyze_host_rule_matches,
    analyze_service_rule_matches,
)
from cmk.gui.watolib.configuration_bundle_store import is_locked_by_quick_setup
from cmk.gui.watolib.predefined_conditions import PredefinedConditionStore
from cmk.rulesets.v1 import Help, Label, Message, Title
from cmk.rulesets.v1.form_specs import (
    BooleanChoice as BooleanChoiceAPI,
)
from cmk.rulesets.v1.form_specs import (
    CascadingSingleChoice as CascadingSingleChoiceAPI,
)
from cmk.rulesets.v1.form_specs import (
    CascadingSingleChoiceElement as CascadingSingleChoiceElementAPI,
)
from cmk.rulesets.v1.form_specs import (
    DefaultValue as DefaultValueAPI,
)
from cmk.rulesets.v1.form_specs import (
    DictElement as DictElementAPI,
)
from cmk.rulesets.v1.form_specs import (
    Dictionary as DictionaryAPI,
)
from cmk.rulesets.v1.form_specs import (
    FieldSize as FieldSizeAPI,
)
from cmk.rulesets.v1.form_specs import (
    FixedValue as FixedValueAPI,
)
from cmk.rulesets.v1.form_specs import FormSpec, MatchingScope
from cmk.rulesets.v1.form_specs import (
    MultipleChoice as MultipleChoiceAPI,
)
from cmk.rulesets.v1.form_specs import (
    MultipleChoiceElement as MultipleChoiceElementAPI,
)
from cmk.rulesets.v1.form_specs import RegularExpression as RegularExpressionAPI
from cmk.rulesets.v1.form_specs import (
    SingleChoice as SingleChoiceAPI,
)
from cmk.rulesets.v1.form_specs import (
    SingleChoiceElement as SingleChoiceElementAPI,
)
from cmk.rulesets.v1.form_specs import (
    String as StringAPI,
)
from cmk.server_side_calls_backend.config_processing import (
    GlobalProxiesWithLookup,
    OAuth2Connection,
    process_configuration_to_parameters,
)
from cmk.shared_typing.vue_formspec_components import (
    BinaryCondition,
    Condition,
    ConditionGroup,
)
from cmk.utils import paths
from cmk.utils.automation_config import LocalAutomationConfig, RemoteAutomationConfig
from cmk.utils.global_ident_type import GlobalIdent
from cmk.utils.labels import LabelGroups, Labels
from cmk.utils.object_diff import make_diff, make_diff_text
from cmk.utils.rulesets import ruleset_matcher
from cmk.utils.rulesets.conditions import (
    allow_host_label_conditions,
    allow_service_label_conditions,
    HostOrServiceConditionRegex,
    HostOrServiceConditions,
    HostOrServiceConditionsSimple,
)
from cmk.utils.rulesets.definition import RuleGroup
from cmk.utils.rulesets.ruleset_matcher import (
    RuleConditionsSpec,
    RuleOptionsSpec,
    RulesetName,
    RuleSpec,
    TagCondition,
    TagConditionNE,
)
from cmk.utils.tags import AuxTag, TagGroup, TagGroupID, TagID
from cmk.utils.timeperiod import TIMESPECIFIC_DEFAULT_KEY, TIMESPECIFIC_VALUES_KEY

from .changes import add_change
from .check_mk_automations import get_services_labels, update_merged_password_file
from .hosts_and_folders import (
    Folder,
    folder_preserving_link,
    folder_tree,
    FolderTree,
    Host,
    may_use_redis,
)
from .objref import ObjectRef, ObjectRefType
from .rulespecs import (
    FormSpecNotImplementedError,
    MatchType,
    Rulespec,
    rulespec_group_registry,
    rulespec_registry,
    RulespecAllowList,
    TimeperiodValuespec,
)
from .simple_config_file import WatoConfigFile
from .timeperiods import TimeperiodUsage
from .utils import ALL_HOSTS, ALL_SERVICES, NEGATE, wato_root_dir

tracer = trace.get_tracer()

FolderPath = str
SearchOptions = dict[str, Any]
RuleValue = Any


# This macro is needed to make the to_config() methods be able to use native pprint/repr for the
# ruleset data structures. Have a look at to_config() for further information.
_FOLDER_PATH_MACRO = "%#%FOLDER_PATH%#%"


class InvalidRuleException(MKGeneralException):
    pass


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
    # cf. Folder.folder, Folder.folder_choices etc.
    HOST_FOLDER_FOR_UI = auto()
    # cmk.base sets folders this way when loading the configuration:
    # /wato/subfolder/subsubfolder/...
    # cf. FOLDER_PATH in cmk.base.config
    HOST_FOLDER_FOR_BASE = auto()


class RuleConditions:
    def __init__(
        self,
        host_folder: str,
        host_tags: Mapping[TagGroupID, TagCondition] | None = None,
        host_label_groups: LabelGroups | None = None,
        host_name: HostOrServiceConditions | None = None,
        service_description: HostOrServiceConditions | None = None,
        service_label_groups: LabelGroups | None = None,
    ) -> None:
        self.host_folder: Final = host_folder
        self.host_tags: Final[Mapping[TagGroupID, TagCondition]] = host_tags or {}
        self.host_label_groups: Final = host_label_groups or []
        self.host_name: Final = host_name
        self.service_description: Final = service_description
        self.service_label_groups: Final = service_label_groups or []

    @classmethod
    def from_config(cls, host_folder: str, conditions: Mapping[str, Any]) -> RuleConditions:
        return cls(
            host_folder=conditions.get("host_folder", host_folder),
            host_tags=conditions.get("host_tags", {}),
            host_label_groups=conditions.get("host_label_groups", []),
            host_name=conditions.get("host_name"),
            service_description=conditions.get("service_description"),
            service_label_groups=conditions.get("service_label_groups", []),
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

        if self.host_label_groups:
            cfg["host_label_groups"] = self.host_label_groups

        if self.host_name is not None:
            cfg["host_name"] = self.host_name

        if self.service_description is not None:
            cfg["service_description"] = self.service_description

        if self.service_label_groups:
            cfg["service_label_groups"] = self.service_label_groups

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

            tag_list.append(TagID("!%s" % tag_id) if is_not else tag_id)
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
    def host_list(self) -> tuple[list[str], bool] | None:
        return self._condition_list(self.host_name, is_service=False)

    # Compatibility code for pre 1.6 Setup code
    @property
    def item_list(self) -> tuple[list[str], bool] | None:
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
            host_label_groups=self.host_label_groups,
            host_name=(
                self.host_name.copy()
                if isinstance(
                    self.host_name,
                    dict,
                )
                else [*self.host_name]
                if self.host_name is not None
                else None
            ),
            service_description=(
                self.service_description.copy()
                if isinstance(
                    self.service_description,
                    dict,
                )
                else [*self.service_description]
                if self.service_description is not None
                else None
            ),
            service_label_groups=self.service_label_groups,
        )

    def __bool__(self) -> bool:
        return bool(self.to_config(UseHostFolder.HOST_FOLDER_FOR_UI))

    def __eq__(self, other: object) -> bool:
        return isinstance(other, RuleConditions) and self.to_config(
            UseHostFolder.HOST_FOLDER_FOR_UI
        ) == other.to_config(UseHostFolder.HOST_FOLDER_FOR_UI)


class RulesetCollection:
    """A collection of rulesets."""

    def __init__(self, rulesets: Mapping[RulesetName, Ruleset]) -> None:
        super().__init__()
        # A dictionary containing all ruleset objects of the collection.
        # The name of the ruleset is used as key in the dict.
        self._rulesets = dict(rulesets)
        self._unknown_rulesets: dict[str, dict[str, Sequence[RuleSpec[object]]]] = {}

    @staticmethod
    def _initialize_rulesets(
        only_varname: RulesetName | None = None,
    ) -> Mapping[RulesetName, Ruleset]:
        varnames = [only_varname] if only_varname else rulespec_registry.keys()
        return {varname: Ruleset(varname) for varname in varnames}

    def _load_folder_rulesets(
        self, folder: Folder, only_varname: RulesetName | None = None
    ) -> None:
        path = folder.rules_file_path()

        if not path.exists():
            return  # Do not initialize rulesets when no rule at all exists

        self.replace_folder_config(
            folder,
            RuleConfigFile(path).load_for_reading(),
            only_varname,
        )

    @staticmethod
    def _context_helpers(folder: Folder) -> Mapping[str, object]:
        return {
            "ALL_HOSTS": ALL_HOSTS,
            "ALL_SERVICES": ALL_SERVICES,
            "NEGATE": NEGATE,
            "FOLDER_PATH": folder.path(),
        }

    @staticmethod
    def _prepare_empty_rulesets() -> Mapping[str, Sequence[object] | Mapping[str, object]]:
        """Prepare empty rulesets so that rules.mk has something to append to

        We need to initialize all variables here, even when only loading with only_varname.
        """
        default: Callable[[], Sequence[object] | Mapping[str, object]] = dict
        return dict(
            ((name.split(":")[0], default()) if ":" in name else (name, []))
            for name in rulespec_registry.keys()
        )

    def get_ruleset_configs_from_file(
        self,
        folder: Folder,
        loaded_file_config: Mapping[str, Any],
        only_varname: RulesetName | None = None,
    ) -> Iterable[tuple[RulesetName, list[RuleSpec[object]]]]:
        if only_varname:
            variable_names_to_load: list[RulesetName] = [only_varname]
        else:

            def varnames_from_item(name: str, value: object) -> Sequence[str]:
                if isinstance(value, dict):
                    return [f"{name}:{key}" for key in value]
                if isinstance(value, list):
                    return [name]
                return []

            helpers = RulesetCollection._context_helpers(folder)
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

                yield varname, rulegroup_config[subkey]
            else:
                yield varname, loaded_file_config.get(varname, [])

    def replace_folder_ruleset_config(
        self, folder: Folder, ruleset_config: Sequence[RuleSpec[object]], varname: RulesetName
    ) -> None:
        if varname in self._rulesets:
            self._rulesets[varname].replace_folder_config(folder, ruleset_config)
        else:
            self._unknown_rulesets.setdefault(folder.path(), {})[varname] = ruleset_config

    def replace_folder_config(
        # The Any below should most likely be RuleSpec[object] but I am not sure.
        self,
        folder: Folder,
        loaded_file_config: Mapping[str, Any],
        only_varname: RulesetName | None = None,
    ) -> None:
        for varname, ruleset_config in self.get_ruleset_configs_from_file(
            folder, loaded_file_config, only_varname
        ):
            if not ruleset_config:
                continue  # Nothing configured: nothing left to do

            self.replace_folder_ruleset_config(folder, ruleset_config, varname)

    @staticmethod
    def _save_folder(
        folder: Folder,
        rulesets: Mapping[RulesetName, Ruleset],
        unknown_rulesets: Mapping[str, Mapping[str, Sequence[RuleSpec[object]]]],
        *,
        pprint_value: bool,
    ) -> bool:
        RuleConfigFile(folder.rules_file_path()).save_rulesets_and_unknown_rulesets(
            rulesets, unknown_rulesets, pprint_value=pprint_value
        )

        # check if this contains a password. If so, the password file must be updated
        return any(
            process_configuration_to_parameters(
                rule.value,
                global_proxies_with_lookup=GlobalProxiesWithLookup(
                    global_proxies={},
                    password_lookup=lambda _name: None,
                ),
                oauth2_connections={
                    ident: OAuth2Connection(**entry)
                    for ident, entry in load_oauth2_connections().items()
                },
                usage_hint=f"ruleset: {name}",
                is_internal=True,
            ).found_secrets
            for name, rules in rulesets.items()
            if RuleGroup.is_active_checks_rule(name) or RuleGroup.is_special_agents_rule(name)
            for rule in rules.get_folder_rules(folder)
            if isinstance(rule.value, dict)  # this is true for all _FormSpec_ SSC rules.
        )

    def exists(self, name: RulesetName) -> bool:
        return name in self._rulesets

    def get(self, name: RulesetName) -> Ruleset:
        return self._rulesets[name]

    def set(self, name: RulesetName, ruleset: Ruleset) -> None:
        self._rulesets[name] = ruleset

    def delete(self, name: RulesetName) -> None:
        del self._rulesets[name]

    def delete_unknown_rule(self, folder_path: FolderPath, name: RulesetName, rule_id: str) -> None:
        self._unknown_rulesets[folder_path][name] = [
            rs for rs in self._unknown_rulesets[folder_path][name] if rs["id"] != rule_id
        ]

    def delete_unknown(self, folder_path: FolderPath, name: RulesetName) -> None:
        del self._unknown_rulesets[folder_path][name]

    def get_rulesets(self) -> Mapping[RulesetName, Ruleset]:
        return self._rulesets

    def get_unknown_rulesets(
        self,
    ) -> Mapping[FolderPath, Mapping[RulesetName, Sequence[RuleSpec[object]]]]:
        return self._unknown_rulesets


class AllRulesets(RulesetCollection):
    def _load_rulesets_recursively(self, folder: Folder) -> None:
        if may_use_redis():
            self._load_rulesets_via_redis(folder)
            return

        for subfolder in folder.subfolders():
            self._load_rulesets_recursively(subfolder)

        self._load_folder_rulesets(folder)

    def _load_rulesets_via_redis(self, folder: Folder) -> None:
        tree = folder_tree()
        # Search relevant folders with rules.mk files
        # Note: The sort order of the folders does not matter here
        #       self._load_folder_rulesets ultimately puts each folder into a dict
        #       and groups/sorts them later on with a different mechanism
        all_folders = tree.redis_client.recursive_subfolders_for_path(
            f"{folder.path()}/".lstrip("/")
        )

        root_dir = str(wato_root_dir())
        relevant_folders = []
        for folder_path in all_folders:
            if os.path.exists(f"{root_dir}/{folder_path}rules.mk"):
                relevant_folders.append(folder_path)

        for folder_path_with_slash in relevant_folders:
            stripped_folder = folder_path_with_slash.strip("/")
            self._load_folder_rulesets(tree.folder(stripped_folder))

    @staticmethod
    def load_all_rulesets() -> AllRulesets:
        """Load all rules of all folders"""
        rulesets = RulesetCollection._initialize_rulesets()
        self = AllRulesets(rulesets)
        self._load_rulesets_recursively(folder_tree().root_folder())
        return self

    def save(self, *, pprint_value: bool, debug: bool) -> None:
        """Save all rulesets of all folders recursively"""
        if self._save_rulesets_recursively(folder_tree().root_folder(), pprint_value=pprint_value):
            update_merged_password_file(debug=debug)

    def save_folder(self, folder: Folder, *, pprint_value: bool, debug: bool) -> None:
        if self._save_folder(
            folder, self._rulesets, self._unknown_rulesets, pprint_value=pprint_value
        ):
            update_merged_password_file(debug=debug)

    def _save_rulesets_recursively(self, folder: Folder, *, pprint_value: bool) -> bool:
        needs_password_file_updating = False
        for subfolder in folder.subfolders():
            needs_password_file_updating |= self._save_rulesets_recursively(
                subfolder, pprint_value=pprint_value
            )

        needs_password_file_updating |= self._save_folder(
            folder, self._rulesets, self._unknown_rulesets, pprint_value=pprint_value
        )
        return needs_password_file_updating


def visible_rulesets(rulesets: Mapping[RulesetName, Ruleset]) -> Mapping[RulesetName, Ruleset]:
    if edition(paths.omd_root) is not Edition.CLOUD:
        return rulesets

    allow_list = RulespecAllowList.from_config()
    return {
        name: ruleset
        for name, ruleset in rulesets.items()
        if allow_list.is_visible(ruleset.rulespec.name)
    }


def visible_ruleset(rulespec_name: str) -> bool:
    if edition(paths.omd_root) is not Edition.CLOUD:
        return True

    return RulespecAllowList.from_config().is_visible(rulespec_name)


class SingleRulesetRecursively(RulesetCollection):
    # Load single ruleset from all folders
    def _load_rulesets_recursively(self, folder: Folder, only_varname: RulesetName) -> None:
        # Copy/paste from AllRulesets

        if may_use_redis():
            self._load_rulesets_via_redis(folder, only_varname)
            return

        for subfolder in folder.subfolders():
            self._load_rulesets_recursively(subfolder, only_varname)

        self._load_folder_rulesets(folder, only_varname)

    def _load_rulesets_via_redis(self, folder: Folder, only_varname: RulesetName) -> None:
        # Copy/paste from AllRulesets

        tree = folder_tree()
        # Search relevant folders with rules.mk files
        # Note: The sort order of the folders does not matter here
        #       self._load_folder_rulesets ultimately puts each folder into a dict
        #       and groups/sorts them later on with a different mechanism
        all_folders = tree.redis_client.recursive_subfolders_for_path(
            f"{folder.path()}/".lstrip("/")
        )

        root_dir = str(wato_root_dir())
        relevant_folders = []
        for folder_path in all_folders:
            if os.path.exists(f"{root_dir}/{folder_path}rules.mk"):
                relevant_folders.append(folder_path)

        for folder_path_with_slash in relevant_folders:
            stripped_folder = folder_path_with_slash.strip("/")
            self._load_folder_rulesets(tree.folder(stripped_folder), only_varname)

    @staticmethod
    def load_single_ruleset_recursively(name: RulesetName) -> SingleRulesetRecursively:
        rulesets = RulesetCollection._initialize_rulesets(only_varname=name)
        self = SingleRulesetRecursively(rulesets)
        self._load_rulesets_recursively(folder_tree().root_folder(), only_varname=name)
        return self


class FolderRulesets(RulesetCollection):
    def __init__(
        self,
        rulesets: Mapping[RulesetName, Ruleset],
        *,
        folder: Folder,
    ) -> None:
        super().__init__(rulesets)
        self._folder: Final = folder

    @staticmethod
    def load_folder_rulesets(folder: Folder) -> FolderRulesets:
        rulesets = RulesetCollection._initialize_rulesets()
        self = FolderRulesets(rulesets, folder=folder)
        self._load_folder_rulesets(folder)
        return self

    def save_folder(self, *, pprint_value: bool, debug: bool) -> None:
        if RulesetCollection._save_folder(
            self._folder, self._rulesets, self._unknown_rulesets, pprint_value=pprint_value
        ):
            update_merged_password_file(debug=debug)


class Ruleset:
    # These constants are used to give a name to positions within the ruleset.
    # mylist[-1] is the last element, mylist[0] is the first. See `move_to_folder`.
    TOP = 0
    BOTTOM = -1

    def __init__(
        self,
        name: RulesetName,
        rulespec: Rulespec | None = None,
    ) -> None:
        super().__init__()
        self.name: Final = name
        self.rulespec: Final = rulespec_registry[name] if rulespec is None else rulespec

        # Holds list of the rules. Using the folder paths as keys.
        self._rules: dict[FolderPath, list[Rule]] = {}
        self._rules_by_id: dict[str, Rule] = {}

        # Temporary needed during search result processing
        self.search_matching_rules: list[Rule] = []

    def clone(self) -> Ruleset:
        cloned = Ruleset(self.name, self.rulespec)
        for folder, _rule_index, rule in self.get_rules():
            cloned.append_rule(folder, rule)
        return cloned

    def object_ref(self) -> ObjectRef:
        return ObjectRef(ObjectRefType.Ruleset, self.name)

    def is_empty(self) -> bool:
        return self.num_rules() == 0

    def is_empty_in_folder(self, folder: Folder) -> bool:
        return not self.get_folder_rules(folder)

    def num_rules(self) -> int:
        return len(self._rules_by_id)

    def num_rules_in_folder(self, folder: Folder) -> int:
        return len(self.get_folder_rules(folder))

    def get_rules(self) -> list[tuple[Folder, int, Rule]]:
        rules = []
        for _folder_path, folder_rules in self._rules.items():
            for rule_index, rule in enumerate(folder_rules):
                rules.append((rule.folder, rule_index, rule))
        return sorted(
            rules, key=lambda x: (x[0].path().split("/"), len(rules) - x[1]), reverse=True
        )

    def get_folder_rules(self, folder: Folder) -> list[Rule]:
        try:
            return self._rules[folder.path()]
        except KeyError:
            return []

    def _num_quick_setup_rules(self, folder: Folder) -> int:
        # the assertion is that all quick setup rules are at the top
        folder_rules = self.get_folder_rules(folder)
        for idx, rule in enumerate(folder_rules):
            if not is_locked_by_quick_setup(rule.locked_by):
                return idx
        # if we get here either there are no rules or all of them are managed by qs
        return len(folder_rules)

    def get_index_for_move(self, folder: Folder, rule: Rule, target: int) -> int:
        num_qs_rules = self._num_quick_setup_rules(folder)
        if is_locked_by_quick_setup(rule.locked_by):
            if rule in self.get_folder_rules(folder):
                return min(num_qs_rules - 1, target)

            return min(num_qs_rules, target)

        return max(num_qs_rules, target)

    def prepend_rule(self, folder: Folder, rule: Rule) -> None:
        rules = self._rules.setdefault(folder.path(), [])
        rules.insert(self.get_index_for_move(folder, rule, 0), rule)
        self._rules_by_id[rule.id] = rule
        self._on_change()

    def clone_rule(self, orig_rule: Rule, rule: Rule, *, use_git: bool) -> None:
        if rule.folder == orig_rule.folder:
            self.insert_rule_after(rule, orig_rule)
        else:
            self.append_rule(rule.folder, rule)

        add_change(
            action_name="new-rule",
            text=_l('Cloned rule from rule %s in ruleset "%s" in folder "%s"')
            % (orig_rule.id, self.title(), rule.folder.alias_path()),
            user_id=user.id,
            sites=rule.folder.all_site_ids(),
            diff_text=self.diff_rules(None, rule),
            object_ref=rule.object_ref(),
            use_git=use_git,
        )

    def move_to_folder(
        self, rule: Rule, folder: Folder, index: int = BOTTOM, *, use_git: bool
    ) -> None:
        source_folder = rule.folder
        if source_folder == folder:
            # same folder, use the simpler audit log entry
            self.move_rule_to(rule, index=index, use_git=use_git)
            return

        source_rules = self._rules[source_folder.path()]
        dest_rules = self._rules.setdefault(folder.path(), [])

        # The actual move
        source_rules.remove(rule)
        if index == Ruleset.BOTTOM:
            index = len(dest_rules)  # write correct index to audit log
            dest_rules.append(rule)
        else:
            index = self.get_index_for_move(folder, rule, index)
            dest_rules.insert(index, rule)
        rule.folder = folder

        affected_sites = set(source_folder.all_site_ids())
        affected_sites.update(folder.all_site_ids())

        add_change(
            action_name="edit-rule",
            text=_l('Moved rule %s of ruleset "%s" from folder "%s" to position #%d in folder "%s"')
            % (rule.id, self.title(), source_folder.title(), index, folder.title()),
            user_id=user.id,
            sites=list(affected_sites),
            object_ref=rule.object_ref(),
            use_git=use_git,
        )
        self._on_change()

    def append_rule(self, folder: Folder, rule: Rule) -> int:
        rules = self._rules.setdefault(folder.path(), [])
        if is_locked_by_quick_setup(rule.locked_by):
            index = self._num_quick_setup_rules(folder)
            rules.insert(index, rule)
        else:
            index = len(rules)
            rules.append(rule)
        self._rules_by_id[rule.id] = rule
        self._on_change()
        return index

    def add_new_rule_change(self, index: int, folder: Folder, rule: Rule, *, use_git: bool) -> None:
        add_change(
            action_name="new-rule",
            text=_('Created new rule #%d in ruleset "%s" in folder "%s"')
            % (index, self.title(), folder.alias_path()),
            user_id=user.id,
            sites=folder.all_site_ids(),
            diff_text=self.diff_rules(None, rule),
            object_ref=rule.object_ref(),
            use_git=use_git,
        )

    def insert_rule_after(self, rule: Rule, after: Rule) -> None:
        rules = self._rules[rule.folder.path()]
        index = self.get_index_for_move(rule.folder, rule, rules.index(after) + 1)
        rules.insert(index, rule)
        self._rules_by_id[rule.id] = rule
        self._on_change()

    def replace_folder_config(
        self,
        folder: Folder,
        rules_config: Sequence[RuleSpec[object]],
    ) -> None:
        if not rules_config:
            return

        if folder.path() in self._rules:
            for rule in self._rules[folder.path()]:
                del self._rules_by_id[rule.id]

        # Resets the rules of this ruleset for this folder!
        self._rules[folder.path()] = []

        for rule_config in rules_config:
            rule = Rule.from_config(folder, self, rule_config)
            self._rules[folder.path()].append(rule)
            self._rules_by_id[rule.id] = rule

    def to_config(self, folder: Folder, pprint_value: bool) -> str:
        return self.format_raw_value(
            self.name,
            (r.to_config() for r in self._rules[folder.path()]),
            self.is_optional(),
            pprint_value=pprint_value,
        )

    @staticmethod
    def format_raw_value(
        name: str, rule_specs: Iterable[RuleSpec], is_optional: bool, pprint_value: bool
    ) -> str:
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
            if pprint_value:
                text = pprint.pformat(rule_spec)
            else:
                text = repr(rule_spec)

            content += "%s,\n" % text
        content += "] + %s\n\n" % varname

        return content

    # Whether or not either the ruleset itself matches the search or the rules match
    def matches_search_with_rules(self, search_options: SearchOptions, *, debug: bool) -> bool:
        if not self.matches_ruleset_search_options(search_options):
            return False

        # The ruleset matched or did not decide to skip the whole ruleset.
        # The ruleset should be matched in case a rule matches.
        if not self.has_rule_search_options(search_options):
            return self.matches_fulltext_search(search_options)

        rules = self.get_rules()

        # Compute rule effectiveness for all rules in a rule set if needed
        # Interesting: This has always tried host matching. Whether or not a service ruleset
        # does not match any service has never been tested. Probably because this would be
        # too expensive.
        rule_effectiveness = (
            analyze_host_rule_effectiveness(
                [r.to_single_base_ruleset() for _f, _i, r in rules], debug=debug
            ).results
            if rules and "rule_ineffective" in search_options
            else {}
        )

        # Store the matching rules for later result rendering
        self.search_matching_rules = []
        for _folder, _rule_index, rule in rules:
            if rule.matches_search(search_options, rule_effectiveness):
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
        # by the Agent Bakery. Users often try to find the ruleset in the wrong group.
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

    def get_rule(self, folder: Folder, rule_index: int) -> Rule:
        return self._rules[folder.path()][rule_index]

    def get_rule_by_id(self, rule_id: str) -> Rule:
        return self._rules_by_id[rule_id]

    def diff_rules(self, old: Rule | None, new: Rule) -> str:
        """Diff two rules, masking secrets and serializing the rule value to a log-friendly format"""
        if old is None:
            return make_diff_text({}, new.to_log())
        return old.diff_to(new)

    def edit_rule(self, orig_rule: Rule, rule: Rule, *, use_git: bool) -> None:
        folder_rules = self._rules[orig_rule.folder.path()]
        index = folder_rules.index(orig_rule)

        folder_rules[index] = rule

        add_change(
            action_name="edit-rule",
            text=_l('Changed properties of rule #%d in ruleset "%s" in folder "%s"')
            % (index, self.title(), rule.folder.alias_path()),
            user_id=user.id,
            sites=rule.folder.all_site_ids(),
            diff_text=self.diff_rules(orig_rule, rule),
            object_ref=rule.object_ref(),
            use_git=use_git,
        )
        self._on_change()

    def delete_rule(self, rule: Rule, *, create_change: bool, use_git: bool) -> None:
        folder_rules = self._rules[rule.folder.path()]
        index = folder_rules.index(rule)

        folder_rules.remove(rule)
        del self._rules_by_id[rule.id]

        if create_change:
            add_change(
                action_name="edit-rule",
                text=_l('Deleted rule #%d in ruleset "%s" in folder "%s"')
                % (index, self.title(), rule.folder.alias_path()),
                user_id=user.id,
                sites=rule.folder.all_site_ids(),
                object_ref=rule.object_ref(),
                use_git=use_git,
            )
        self._on_change()

    def move_rule_to(self, rule: Rule, *, index: int, use_git: bool) -> int:
        rules = self._rules[rule.folder.path()]
        old_index = rules.index(rule)
        index = self.get_index_for_move(rule.folder, rule, index)
        if old_index == index:
            return index

        rules.remove(rule)
        rules.insert(index, rule)
        add_change(
            action_name="edit-ruleset",
            text=_l('Moved rule %s from position #%d to #%d in ruleset "%s" in folder "%s"')
            % (rule.id, old_index, index, self.title(), rule.folder.alias_path()),
            user_id=user.id,
            sites=rule.folder.all_site_ids(),
            object_ref=self.object_ref(),
            use_git=use_git,
        )
        return index

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

    def item_type(self) -> Literal["service", "item"] | None:
        return self.rulespec.item_type

    def item_name(self) -> str | None:
        return self.rulespec.item_name

    def item_help(self) -> None | str | HTML:
        return self.rulespec.item_help

    def item_enum(self) -> DropdownChoiceEntries | None:
        return self.rulespec.item_enum

    def match_type(self) -> MatchType:
        return self.rulespec.match_type

    def is_deprecated(self) -> bool:
        return self.rulespec.is_deprecated

    def is_optional(self) -> bool:
        return self.rulespec.is_optional

    def _on_change(self) -> None:
        hooks.call("ruleset-changed", self.name)

    # Returns the outcoming value or None and a list of matching rules. These are pairs
    # of rule_folder and rule_number
    def analyse_ruleset(
        self,
        hostname: HostName,
        svc_desc_or_item: str | None,
        svc_desc: str | None,
        service_labels: Labels,
        *,
        debug: bool,
    ) -> tuple[object, list[tuple[Folder, int, Rule]]]:
        resultlist = []
        resultdict: dict[str, Any] = {}
        effectiverules = []

        rules = self.get_rules()
        if self.rulespec.is_for_services:
            rule_matches = {
                rule_id: bool(matches)
                for rule_id, matches in analyze_service_rule_matches(
                    hostname,
                    (svc_desc if self.rulespec.item_type == "service" else svc_desc_or_item) or "",
                    service_labels,
                    [r.to_single_base_ruleset() for _f, _i, r in rules],
                    debug=debug,
                ).results.items()
            }
        else:
            rule_matches = {
                rule_id: bool(matches)
                for rule_id, matches in analyze_host_rule_matches(
                    hostname,
                    [r.to_single_base_ruleset() for _f, _i, r in rules],
                    debug=debug,
                ).results.items()
            }

        for folder, rule_index, rule in rules:
            if rule.is_disabled():
                continue

            if not rule_matches[rule.id]:
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

    @property
    def rules(self) -> dict[FolderPath, list[Rule]]:
        return self._rules


class Rule:
    @classmethod
    def from_ruleset(cls, folder: Folder, ruleset: Ruleset, value: object) -> Rule:
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
            value,
        )

    def __init__(
        self,
        id_: str,
        folder: Folder,
        ruleset: Ruleset,
        conditions: RuleConditions,
        options: RuleOptions,
        value: RuleValue,
        locked_by: GlobalIdent | None = None,
    ) -> None:
        self.ruleset: Ruleset = ruleset
        self.folder: Folder = folder
        self.conditions: RuleConditions = conditions
        self.id: str = id_
        self.rule_options: RuleOptions = options
        self.value: RuleValue = value
        self.locked_by = locked_by
        self._single_base_ruleset_representation: Sequence[RuleSpec] | None = None

    def clone(self, preserve_id: bool = False) -> Rule:
        return Rule(
            self.id if preserve_id else utils.gen_id(),
            self.folder,
            self.ruleset,
            self.conditions.clone(),
            dataclasses.replace(self.rule_options),
            self.value,
            self.locked_by if preserve_id else None,
        )

    @classmethod
    def from_config(
        cls,
        folder: Folder,
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
            raise InvalidRuleException(_("Invalid rule <tt>%s</tt>") % (rule_config,))

    @classmethod
    def _parse_dict_rule(
        cls,
        folder: Folder,
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
            rule_config.get("locked_by"),
        )

    def value_masked(self) -> RuleValue:
        """Return a copy of the value with all secrets masked"""
        try:
            return get_visitor(
                self.ruleset.rulespec.form_spec,
                VisitorOptions(migrate_values=True, mask_values=True),
            ).to_disk(RawDiskData(self.value))
        except FormSpecNotImplementedError:
            pass

        return self.ruleset.rulespec.valuespec.mask(self.value)

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
            use_host_folder=UseHostFolder.NONE if self.folder.is_root() else use_host_folder,
            value=self.value,
        )

    def to_single_base_ruleset(self) -> Sequence[RuleSpec]:
        """Returns a new ruleset only containing this rule and its conditions"""
        if self._single_base_ruleset_representation is not None:
            return self._single_base_ruleset_representation
        rule_dict = self.to_config(UseHostFolder.HOST_FOLDER_FOR_BASE)
        self._single_base_ruleset_representation = [rule_dict]
        return self._single_base_ruleset_representation

    def to_web_api(self) -> RuleSpec:
        return self._to_config(use_host_folder=UseHostFolder.NONE, value=self.value)

    def to_log(self) -> RuleSpec:
        return self._to_config(use_host_folder=UseHostFolder.NONE, value=self.value_masked())

    def _to_config(
        self,
        *,
        use_host_folder: UseHostFolder,
        value: object,
    ) -> RuleSpec:
        rule_spec = RuleSpec(
            id=self.id,
            value=value,
            condition=self.conditions.to_config(use_host_folder),
        )
        if options := self.rule_options.to_config():
            rule_spec["options"] = options
        if self.locked_by:
            rule_spec["locked_by"] = self.locked_by
        return rule_spec

    def object_ref(self) -> ObjectRef:
        return ObjectRef(
            ObjectRefType.Rule,
            self.id,
            {
                "ruleset": self.ruleset.name,
            },
        )

    def matches_search(
        self,
        search_options: SearchOptions,
        rule_effectiveness: Mapping[str, bool],
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
            and search_options["rule_ineffective"] is rule_effectiveness[self.id]
        ):
            return False

        if not _match_search_expression(search_options, "rule_description", self.description()):
            return False

        if not _match_search_expression(search_options, "rule_comment", self.comment()):
            return False

        value_text = None
        try:
            value_model = self.ruleset.rulespec.value_model
            if isinstance(value_model, FormSpec):
                visitor = get_visitor(
                    value_model,
                    VisitorOptions(migrate_values=True, mask_values=True),
                )
                _spec, data = visitor.to_vue(RawDiskData(self.value))
                value_text = repr(data)
            else:
                value_text = str(value_model.value_to_html(self.value))
        except MKAuthException as e:
            html.show_error(
                _("Failed to search rule of rule set '%s': %s") % (self.ruleset.title(), e)
            )
        except Exception as e:
            logger.exception("error searching ruleset %s", self.ruleset.title())
            html.show_warning(
                _("Failed to search rule of rule set '%s' in folder '%s' (%r): %s")
                % (self.ruleset.title(), self.folder.title(), self.to_config(), e)
            )

        if value_text is not None and not _match_search_expression(
            search_options, "rule_value", value_text
        ):
            return False

        if "rule_host_list" in search_options and not _match_rule_host_list(
            rule=self,
            search_hosts_str=search_options["rule_host_list"],
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
        current_folder = folder_tree().folder(current_folder)
        search_in_folders = [current_folder.path()]
        if do_recursion:
            search_in_folders = [
                x for x, _y in current_folder.recursive_subfolder_choices(pretty=True)
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

    def is_discovery_rule_of(self, host: Host) -> bool:
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


def _match_rule_host_list(rule: Rule, search_hosts_str: str) -> bool:
    # Regex
    if any(c in ".?*+^$|[](){}\\" for c in search_hosts_str):
        match_regex = re.compile(search_hosts_str)
        rule_host_list = []
        for host_name, _host in Host.all().items():
            if match_regex.search(host_name):
                rule_host_list.append(host_name)
        if not any(
            analyze_host_rule_matches(
                HostAddress(host_name),
                [rule.to_single_base_ruleset()],
                debug=False,
            ).results[rule.id]
            for host_name in rule_host_list
        ):
            return False
    # Single host or host list
    elif not all(
        analyze_host_rule_matches(
            HostAddress(host_name),
            [rule.to_single_base_ruleset()],
            debug=False,
        ).results[rule.id]
        for host_name in search_hosts_str.split(" ")
    ):
        return False
    return True


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
    r"""Packs a service name to be used as explicit match condition

    >>> service_description_to_condition("abc")
    {'$regex': 'abc$'}
    >>> service_description_to_condition("a / b / c \\ d \\ e")
    {'$regex': 'a / b / c \\\\ d \\\\ e$'}
    """
    return {"$regex": "%s$" % escape_regex_chars(service_description)}


def rules_grouped_by_folder(
    rules: list[tuple[Folder, int, Rule]],
    current_folder: Folder,
) -> Generator[tuple[Folder, Iterator[tuple[Folder, int, Rule]]]]:
    """Get ruleset groups in correct sort order. Sort by title_path() to honor
    renamed folders"""
    sorted_rules: list[tuple[Folder, int, Rule]] = sorted(
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


class EnabledDisabledServicesEditor:
    def __init__(self, host: Host) -> None:
        self._host = host

    def save_host_service_enable_disable_rules(
        self,
        to_enable: set[str],
        to_disable: set[str],
        *,
        automation_config: LocalAutomationConfig | RemoteAutomationConfig,
        pprint_value: bool,
        debug: bool,
        use_git: bool,
    ) -> None:
        self._save_service_enable_disable_rules(
            to_enable,
            value=False,
            automation_config=automation_config,
            pprint_value=pprint_value,
            debug=debug,
            use_git=use_git,
        )
        self._save_service_enable_disable_rules(
            to_disable,
            value=True,
            automation_config=automation_config,
            pprint_value=pprint_value,
            debug=debug,
            use_git=use_git,
        )

    def _save_service_enable_disable_rules(
        self,
        services: set[str],
        *,
        value: bool,
        automation_config: LocalAutomationConfig | RemoteAutomationConfig,
        pprint_value: bool,
        debug: bool,
        use_git: bool,
    ) -> None:
        """
        Load all disabled services rules from the folder, then check whether or not there is a
        rule for that host and check whether or not it currently disabled the services in question.
        if so, remove them and save the rule again.
        Then check whether or not the services are still disabled (by other rules). If so, search
        for an existing host dedicated negative rule that enables services. Modify this or create
        a new rule to override the disabling of other rules.

        Do the same vice versa for disabling services.
        """
        if not services:
            return

        rulesets = AllRulesets.load_all_rulesets()

        try:
            ruleset = rulesets.get("ignored_services")
        except KeyError:
            ruleset = Ruleset("ignored_services")

        modified_folders = []

        service_patterns = [service_description_to_condition(s) for s in services]
        modified_folders += self._remove_from_rule_of_host(
            ruleset, service_patterns, value=not value, use_git=use_git
        )

        # Check whether or not the service still needs a host specific setting after removing
        # the host specific setting above and remove all services from the service list
        # that are fine without an additional change.
        services_labels = get_services_labels(
            automation_config, self._host.name(), services, debug=debug
        )
        for service in list(services):
            service_labels = services_labels.labels[service]
            value_without_host_rule, _ = ruleset.analyse_ruleset(
                self._host.name(),
                service,
                service,
                service_labels=service_labels,
                debug=debug,
            )
            if (
                not value and value_without_host_rule in [None, False]
            ) or value == value_without_host_rule:
                services.remove(service)

        service_patterns = [service_description_to_condition(s) for s in services]
        modified_folders += self._update_rule_of_host(ruleset, service_patterns, value=value)

        for folder in modified_folders:
            rulesets.save_folder(folder, pprint_value=pprint_value, debug=debug)

    def _remove_from_rule_of_host(
        self,
        ruleset: Ruleset,
        service_patterns: Sequence[HostOrServiceConditionRegex],
        value: Any,
        *,
        use_git: bool,
    ) -> list[Folder]:
        other_rule = self._get_rule_of_host(ruleset, value)
        if other_rule and isinstance(other_rule.conditions.service_description, list):
            for service_condition in service_patterns:
                if service_condition in other_rule.conditions.service_description:
                    other_rule.conditions.service_description.remove(service_condition)

            if not other_rule.conditions.service_description:
                ruleset.delete_rule(other_rule, create_change=True, use_git=use_git)

            return [other_rule.folder]

        return []

    def _update_rule_of_host(
        self, ruleset: Ruleset, service_patterns: Sequence[HostOrServiceConditionRegex], value: Any
    ) -> list[Folder]:
        folder = self._host.folder()
        rule = self._get_rule_of_host(ruleset, value)

        if rule and isinstance(rule.conditions.service_description, list):
            rule_service_conditions = cast(
                list[HostOrServiceConditionRegex], rule.conditions.service_description
            )
            for service_condition in service_patterns:
                if service_condition not in rule_service_conditions:
                    rule.conditions.service_description.append(service_condition)

        elif service_patterns:
            value_model = ruleset.rulespec.value_model
            rule = Rule.from_ruleset(
                folder,
                ruleset,
                DEFAULT_VALUE if isinstance(value_model, FormSpec) else value_model.default_value(),
            )
            conditions = RuleConditions(
                folder.path(),
                host_name=[self._host.name()],
                # Mypy seems to get the type wrong. Didn't investigate a lot
                service_description=sorted(service_patterns, key=lambda x: x["$regex"]),  # type: ignore[index]
            )
            rule.update_conditions(conditions)

            rule.value = value
            ruleset.prepend_rule(folder, rule)

        if rule:
            return [rule.folder]
        return []

    def _get_rule_of_host(self, ruleset: Ruleset, value: Any) -> Rule | None:
        for _folder, _index, rule in ruleset.get_rules():
            if rule.is_disabled():
                continue

            if rule.is_discovery_rule_of(self._host) and rule.value == value:
                return rule
        return None


def find_timeperiod_usage_in_host_and_service_rules(time_period_name: str) -> list[TimeperiodUsage]:
    used_in: list[TimeperiodUsage] = []
    rulesets = AllRulesets.load_all_rulesets()
    for varname, ruleset in rulesets.get_rulesets().items():
        if not isinstance(ruleset.rulespec.value_model, TimeperiodValuespec | TimeSpecific):
            continue

        for _folder, _rulenr, rule in ruleset.get_rules():
            if rule.value == time_period_name:
                used_in.append(
                    (
                        "{}: {}".format(_("Rule set"), ruleset.title()),
                        folder_preserving_link([("mode", "edit_ruleset"), ("varname", varname)]),
                    )
                )
                break
    return used_in


def _is_active(value: object) -> bool:
    return isinstance(value, dict) and TIMESPECIFIC_DEFAULT_KEY in value


def _get_used_timeperiods(value: dict[str, Any]) -> set[str]:
    return {tp for tp, _params in value.get(TIMESPECIFIC_VALUES_KEY, [])}


def find_timeperiod_usage_in_time_specific_parameters(
    time_period_name: str,
) -> list[TimeperiodUsage]:
    used_in: list[TimeperiodUsage] = []
    rulesets = AllRulesets.load_all_rulesets()
    for ruleset in rulesets.get_rulesets().values():
        if not isinstance(ruleset.rulespec.value_model, TimeperiodValuespec | TimeSpecific):
            continue
        for rule_folder, rule_index, rule in ruleset.get_rules():
            if not _is_active(rule.value):
                continue
            for index, rule_tp_name in enumerate(_get_used_timeperiods(rule.value)):
                if rule_tp_name != time_period_name:
                    continue
                edit_url = folder_preserving_link(
                    [
                        ("mode", "edit_rule"),
                        ("back_mode", "timeperiods"),
                        ("varname", ruleset.name),
                        ("rulenr", rule_index),
                        ("rule_folder", rule_folder.path()),
                        ("rule_id", rule.id),
                    ]
                )
                used_in.append((_("Time specific check parameter #%d") % (index + 1), edit_url))
    return used_in


class RuleConfigFile(WatoConfigFile[Mapping[RulesetName, Any]]):
    """Handles reading and writing rules.mk files"""

    def __init__(self, config_file_path: Path) -> None:
        super().__init__(config_file_path=config_file_path, spec_class=Mapping[RulesetName, Any])

    @property
    def folder(self) -> Folder:
        root_dir = Path(folder_tree().get_root_dir())
        return folder_tree().folder(
            str(self._config_file_path.parent.relative_to(root_dir)).strip(".")
        )

    @override
    def _load_file(self, *, lock: bool) -> Mapping[RulesetName, Any]:
        folder = self.folder
        path = folder.rules_file_path()
        loaded_file_config = store.load_mk_file(
            path,
            default={
                **RulesetCollection._context_helpers(folder),
                **RulesetCollection._prepare_empty_rulesets(),
            },
            lock=lock,
        )

        return loaded_file_config

    def save_rulesets_and_unknown_rulesets(
        self,
        rulesets: Mapping[RulesetName, Ruleset],
        unknown_rulesets: Mapping[str, Mapping[str, Sequence[RuleSpec[object]]]],
        pprint_value: bool,
    ) -> None:
        self._save_and_validate_folder(self.folder, rulesets, unknown_rulesets, pprint_value)

    @override
    def save(self, cfg: Mapping[RulesetName, Any], pprint_value: bool) -> None:
        self._save_and_validate_folder(self.folder, cfg, {}, pprint_value)

    @staticmethod
    def _save_and_validate_folder(
        folder: Folder,
        rulesets: Mapping[RulesetName, Ruleset],
        unknown_rulesets: Mapping[str, Mapping[str, Sequence[RuleSpec[object]]]],
        pprint_value: bool,
    ) -> None:
        Path(folder.tree.get_root_dir()).mkdir(mode=0o770, exist_ok=True)
        content = [
            *(
                ruleset.to_config(folder, pprint_value)
                for _name, ruleset in sorted(rulesets.items())
                if not ruleset.is_empty_in_folder(folder)
            ),
            *(
                Ruleset.format_raw_value(
                    varname, raw_value, is_optional=False, pprint_value=pprint_value
                )
                for varname, raw_value in sorted(unknown_rulesets.get(folder.path(), {}).items())
            ),
        ]

        rules_file_path = folder.rules_file_path()
        try:
            # Remove empty rules files. This prevents needless reads
            if not content:
                rules_file_path.unlink(missing_ok=True)
                return
            store.save_mk_file(
                rules_file_path,
                # Adding this instead of the full path makes it easy to move config
                # files around. The real FOLDER_PATH will be added dynamically while
                # loading the file in cmk.base.config
                "".join(content).replace("'%s'" % _FOLDER_PATH_MACRO, "'/%s/' % FOLDER_PATH"),
            )
        finally:
            if may_use_redis():
                folder.tree.redis_client.folder_updated(folder.filesystem_path())


def may_edit_ruleset(varname: str) -> bool:
    if varname == "ignored_services":
        return user.may("wato.services") or user.may("wato.rulesets")
    if varname in [
        "custom_checks",
        "datasource_programs",
        RuleGroup.AgentConfig("mrpe"),
        RuleGroup.AgentConfig("agent_paths"),
        RuleGroup.AgentConfig("runas"),
        RuleGroup.AgentConfig("only_from"),
        RuleGroup.AgentConfig("python_plugins"),
        RuleGroup.AgentConfig("lnx_remote_alert_handlers"),
    ]:
        return user.may("wato.rulesets") and user.may("wato.add_or_modify_executables")
    if varname == RuleGroup.AgentConfig("custom_files"):
        return user.may("wato.rulesets") and user.may("wato.agent_deploy_custom_files")
    return user.may("wato.rulesets")


@dataclasses.dataclass(frozen=True, kw_only=True)
class RuleIdentifier:
    id: str
    name: str


@dataclasses.dataclass(frozen=True, kw_only=True)
class LockedConditions:
    instance_id: str
    render_link: HTML
    message: str


@dataclasses.dataclass(frozen=True)
class RuleSpecItem:
    name: str
    choices: DropdownChoiceEntries


def _create_rule_properties_catalog_topic(
    *, rule_identifier: RuleIdentifier, locked_conditions: LockedConditions | None
) -> dict[str, Topic]:
    elements = {
        "description": TopicElement(
            parameter_form=StringAPI(
                title=Title("Description"),
                field_size=FieldSizeAPI.LARGE,
            ),
            required=True,
        ),
        "comment": TopicElement(
            parameter_form=CommentTextArea(
                title=Title("Comment"),
            ),
            required=True,
        ),
        "docu_url": TopicElement(
            parameter_form=StringAPI(
                title=Title("Documentation URL"),
                field_size=FieldSizeAPI.LARGE,
            ),
            required=True,
        ),
        "disabled": TopicElement(
            parameter_form=BooleanChoiceAPI(
                title=Title("Rule activation"),
                label=Label("Do not apply this rule"),
            ),
            required=True,
        ),
        "id": TopicElement(
            parameter_form=FixedValueAPI(
                title=Title("Rule ID"),
                value=rule_identifier.id,
            ),
            required=True,
        ),
        "_name": TopicElement(
            parameter_form=FixedValueAPI(
                title=Title("Ruleset name"),
                value=rule_identifier.name,
            ),
            required=True,
        ),
    }
    if locked_conditions:
        elements.update(
            {
                "source": TopicElement(
                    parameter_form=FixedValueAPI(
                        title=Title("Source"),
                        value=locked_conditions.instance_id,
                        label=Label("%s") % str(locked_conditions.render_link),
                    )
                )
            }
        )
    return {
        "properties": Topic(
            title=Title("Rule properties"),
            elements=elements,
        )
    }


def create_rule_properties_catalog(
    *, rule_identifier: RuleIdentifier, locked_conditions: LockedConditions | None
) -> Catalog:
    return Catalog(
        elements=_create_rule_properties_catalog_topic(
            rule_identifier=rule_identifier, locked_conditions=locked_conditions
        )
    )


def _create_explicit_rule_services_dict(rule_spec_item: RuleSpecItem) -> DictElementAPI:
    value_parameter_form = (
        MultipleChoiceAPI(
            elements=[
                MultipleChoiceElementAPI(name=n, title=Title("%s") % t)
                for n, t in rule_spec_item.choices
            ],
            custom_validate=[
                not_empty(error_msg=Message("Please add at least one service item.")),
            ],
        )
        if rule_spec_item.choices
        else ListOfStringsAPI(
            string_spec=RegularExpressionAPI(
                predefined_help_text=MatchingScope.PREFIX,
            ),
            custom_validate=[
                not_empty(error_msg=Message("Please add at least one service item.")),
            ],
        )
    )
    return DictElementAPI(
        parameter_form=DictionaryAPI(
            title=Title("%s") % rule_spec_item.name,
            elements={
                "value": DictElementAPI(parameter_form=value_parameter_form, required=True),
                "negate": DictElementAPI(
                    parameter_form=BooleanChoiceAPI(
                        label=Label("Negate: make rule apply for all but the above entries")
                    ),
                    required=True,
                ),
            },
        ),
    )


@request_memoize()
def _get_cached_tags() -> Sequence[TagGroup | AuxTag]:
    choices: list[TagGroup | AuxTag] = []
    all_topics = active_config.tags.get_topic_choices()
    tag_groups_by_topic = dict(active_config.tags.get_tag_groups_by_topic())
    aux_tags_by_topic = dict(active_config.tags.get_aux_tags_by_topic())
    for topic_id, _topic_title in all_topics:
        for tag_group in tag_groups_by_topic.get(topic_id, []):
            choices.append(tag_group)

        for aux_tag in aux_tags_by_topic.get(topic_id, []):
            choices.append(aux_tag)

    return choices


def _get_host_tags_condition_choices() -> dict[str, ConditionGroup]:
    choices: dict[str, ConditionGroup] = {}
    for tag in _get_cached_tags():
        match tag:
            case TagGroup():
                choices[tag.id] = ConditionGroup(
                    title=tag.choice_title,
                    conditions=[
                        Condition(name=tag_id, title=tag_title)
                        for tag_id, tag_title in tag.get_non_empty_tag_choices()
                    ],
                )
            case AuxTag():
                choices[tag.id] = ConditionGroup(
                    title=tag.choice_title,
                    conditions=[Condition(name=tag.id, title=tag.title)],
                )
            case other:
                assert_never(other)
    return choices


def _create_binary_condition(id_: str, value: str) -> BinaryCondition:
    name = f"{id_}:{value}"
    return BinaryCondition(name=name, title=name)


@request_memoize()
def _get_cached_host_labels() -> Sequence[tuple[str, str]]:
    return get_labels_from_core(LabelType.ALL, search_label="")


def _get_host_label_groups_condition_choices() -> list[BinaryCondition]:
    return [_create_binary_condition(id_, value) for id_, value in _get_cached_host_labels()]


# TODO si-host-vs-service-labels: Both host_label_groups and service_label_groups used:
#   LabelGroups > _sub_vs = _SingleLabel(world=Labels.World.CORE)
#               > label_autocompleter
#               > Labels.get_labels
#               > get_labels_from_core(LabelType.ALL, search_label)
# Why not: hosts    -> get_labels_from_core(LabelType.HOST, ...)
#          services -> get_labels_from_core(LabelType.SERVICE, ...)
# @request_memoize()
# def _get_cached_service_labels() -> Sequence[tuple[str, str]]:
#     return get_labels_from_config(LabelType.SERVICE, search_label="")
#
#
# def _get_service_label_groups_condition_choices() -> list[BinaryCondition]:
#     return [_create_binary_condition(id_, value) for id_, value in _get_cached_service_labels()]


def _create_explicit_rule_conditions_dict(
    *, tree: FolderTree, rule_spec_name: str, rule_spec_item: RuleSpecItem | None
) -> DictionaryAPI:
    elements: dict[str, DictElementAPI] = {
        "folder_path": DictElementAPI(
            parameter_form=SingleChoiceExtendedAPI[str](
                title=Title("Folder"),
                help_text=Help("Create the rule in the configured folder"),
                elements=[
                    SingleChoiceElementExtendedAPI(name=n, title=Title("%s") % t)
                    for n, t in tree.folder_choices()
                ],
                prefill=DefaultValueAPI(""),
            ),
            required=True,
        ),
        "host_tags": DictElementAPI(
            parameter_form=ConditionChoices(
                title=Title("Host tags"),
                add_condition_group_label=Label("Add tag condition"),
                select_condition_group_to_add=Label("Select tag to add"),
                no_more_condition_groups_to_add=Label("No more tags to add"),
                get_conditions=_get_host_tags_condition_choices,
                custom_validate=[
                    not_empty(error_msg=Message("Please add at least one tag condition."))
                ],
            ),
        ),
        "host_label_groups": DictElementAPI(
            parameter_form=BinaryConditionChoices(
                title=Title("Host labels"),
                help_text=Help(
                    "Use this condition to select hosts based on the configured host labels."
                ),
                label=Label("Label"),
                get_conditions=(
                    lambda: _get_host_label_groups_condition_choices()
                    if allow_host_label_conditions(rule_spec_name)
                    else []
                ),
                custom_validate=[
                    not_empty(error_msg=Message("Please add at least one host label."))
                ],
            )
        ),
        "explicit_hosts": DictElementAPI(
            parameter_form=DictionaryAPI(
                title=Title("Explicit hosts"),
                elements={
                    "value": DictElementAPI(
                        parameter_form=ListOfStringsAPI(
                            string_spec=create_config_host_name(),
                            custom_validate=[
                                not_empty(error_msg=Message("Please add at least one host.")),
                                HostAddressList(),
                            ],
                        ),
                        required=True,
                    ),
                    "negate": DictElementAPI(
                        parameter_form=BooleanChoiceAPI(
                            label=Label("Negate: make rule apply for all but the above entries"),
                        ),
                        required=True,
                    ),
                },
            ),
        ),
    }
    if rule_spec_item:
        elements.update(
            {
                "explicit_services": _create_explicit_rule_services_dict(rule_spec_item),
                "service_label_groups": DictElementAPI(
                    parameter_form=BinaryConditionChoices(
                        title=Title("Service labels"),
                        help_text=Help(
                            "Use this condition to select services based on the configured service labels."
                        ),
                        label=Label("Label"),
                        get_conditions=(
                            # TODO si-host-vs-service-labels: Why do we use host labels here?
                            lambda: _get_host_label_groups_condition_choices()
                            if allow_service_label_conditions(rule_spec_name)
                            else []
                        ),
                        custom_validate=[
                            not_empty(error_msg=Message("Please add at least one service label."))
                        ],
                    )
                ),
            }
        )
    return DictionaryAPI(elements=elements)


def _create_rule_conditions_catalog_topic(
    *,
    locked_conditions: LockedConditions | None,
    tree: FolderTree,
    rule_spec_name: str,
    rule_spec_item: RuleSpecItem | None,
) -> dict[str, Topic]:
    return {
        "conditions": Topic(
            title=Title("Conditions"),
            elements={
                "type": TopicElement(
                    parameter_form=CascadingSingleChoiceAPI(
                        title=Title("Condition type"),
                        elements=[
                            CascadingSingleChoiceElementAPI(
                                name="explicit",
                                title=Title("Explicit conditions"),
                                parameter_form=_create_explicit_rule_conditions_dict(
                                    tree=tree,
                                    rule_spec_name=rule_spec_name,
                                    rule_spec_item=rule_spec_item,
                                ),
                            ),
                            CascadingSingleChoiceElementAPI(
                                name="predefined",
                                title=Title("Predefined conditions"),
                                parameter_form=SingleChoiceAPI(
                                    title=Title("Predefined condition"),
                                    elements=[
                                        SingleChoiceElementAPI(name=n, title=Title("%s") % t)
                                        for n, t in PredefinedConditionStore().choices()
                                    ],
                                ),
                            ),
                        ],
                        prefill=DefaultValueAPI("explicit"),
                    ),
                    required=True,
                ),
            },
            locked=None if locked_conditions is None else Locked(message=locked_conditions.message),
        )
    }


def create_rule_conditions_catalog(
    *,
    locked_conditions: LockedConditions | None,
    tree: FolderTree,
    rule_spec_name: str,
    rule_spec_item: RuleSpecItem | None,
) -> Catalog:
    return Catalog(
        elements=_create_rule_conditions_catalog_topic(
            locked_conditions=locked_conditions,
            tree=tree,
            rule_spec_name=rule_spec_name,
            rule_spec_item=rule_spec_item,
        )
    )


def create_rule_catalog(
    *,
    rule_identifier: RuleIdentifier,
    locked_conditions: LockedConditions | None,
    title: str | None,
    value_parameter_form: FormSpec,
    tree: FolderTree,
    rule_spec_name: str,
    rule_spec_item: RuleSpecItem | None,
) -> Catalog:
    return Catalog(
        elements={
            **_create_rule_properties_catalog_topic(
                rule_identifier=rule_identifier, locked_conditions=locked_conditions
            ),
            **{
                "value": Topic(
                    title=Title("%s") % title if title else Title("Value"),
                    elements={
                        "value": TopicElement(
                            parameter_form=value_parameter_form,
                            required=True,
                        )
                    },
                )
            },
            **_create_rule_conditions_catalog_topic(
                locked_conditions=locked_conditions,
                tree=tree,
                rule_spec_name=rule_spec_name,
                rule_spec_item=rule_spec_item,
            ),
        }
    )


def get_rule_options_from_catalog_value(raw_value: object) -> RuleOptions:
    if not isinstance(raw_value, dict):
        raise TypeError(raw_value)

    raw_properties = raw_value["properties"]
    return RuleOptions(
        description=raw_properties["description"],
        comment=raw_properties["comment"],
        docu_url=raw_properties["docu_url"],
        disabled=raw_properties["disabled"],
    )


def _parse_explicit_hosts_for_conditions(
    raw_value: object,
) -> HostOrServiceConditions | None:
    if raw_value is None:
        return None
    if not isinstance(raw_value, dict):
        raise TypeError(raw_value)
    values: HostOrServiceConditionsSimple = [
        {"$regex": e[1:]} if e.startswith("~") else e for e in raw_value["value"]
    ]
    return {"$nor": values} if raw_value["negate"] else values


def _parse_explicit_services_for_conditions(raw_value: object) -> HostOrServiceConditions | None:
    if raw_value is None:
        return None
    if not isinstance(raw_value, dict):
        raise TypeError(raw_value)
    values: HostOrServiceConditionsSimple = [{"$regex": e} for e in raw_value["value"]]
    return {"$nor": values} if raw_value["negate"] else values


class ExplicitHostsOrServices(TypedDict):
    value: Sequence[str]
    negate: bool


def parse_explicit_hosts_for_vue(value: HostOrServiceConditions) -> ExplicitHostsOrServices:
    if isinstance(value, list):
        return ExplicitHostsOrServices(
            value=[f"~{e['$regex']}" if isinstance(e, dict) else e for e in value],
            negate=False,
        )
    if isinstance(value, dict):
        return ExplicitHostsOrServices(
            value=[f"~{e['$regex']}" if isinstance(e, dict) else e for e in value["$nor"]],
            negate=True,
        )
    raise TypeError(value)


def _parse_explicit_service_entry(entry: HostOrServiceConditionRegex | str) -> str:
    assert isinstance(entry, dict)
    return entry["$regex"]


def parse_explicit_services_for_vue(value: HostOrServiceConditions) -> ExplicitHostsOrServices:
    if isinstance(value, list):
        return ExplicitHostsOrServices(
            value=[_parse_explicit_service_entry(e) for e in value],
            negate=False,
        )
    if isinstance(value, dict):
        return ExplicitHostsOrServices(
            value=[_parse_explicit_service_entry(e) for e in value["$nor"]],
            negate=True,
        )
    raise TypeError(value)


def get_rule_conditions_from_catalog_value(raw_value: object) -> RuleConditions:
    if not isinstance(raw_value, dict):
        raise TypeError(raw_value)

    cond_type, raw_conditions = raw_value["conditions"]["type"]
    match cond_type:
        case "predefined":
            pre_store = PredefinedConditionStore()
            store_entries = pre_store.filter_usable_entries(pre_store.load_for_reading())
            return RuleConditions(**store_entries[raw_conditions]["conditions"])
        case "explicit":
            return RuleConditions(
                host_folder=raw_conditions["folder_path"],
                host_tags=raw_conditions.get("host_tags"),
                host_label_groups=raw_conditions.get("host_label_groups"),
                host_name=_parse_explicit_hosts_for_conditions(
                    raw_conditions.get("explicit_hosts")
                ),
                service_description=_parse_explicit_services_for_conditions(
                    raw_conditions.get("explicit_services")
                ),
                service_label_groups=raw_conditions.get("service_label_groups"),
            )
        case _:
            raise ValueError(cond_type)
