#!/usr/bin/python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2014             mk@mathias-kettner.de |
# +------------------------------------------------------------------+
#
# This file is part of Check_MK.
# The official homepage is at http://mathias-kettner.de/check_mk.
#
# check_mk is free software;  you can redistribute it and/or modify it
# under the  terms of the  GNU General Public License  as published by
# the Free Software Foundation in version 2.  check_mk is  distributed
# in the hope that it will be useful, but WITHOUT ANY WARRANTY;  with-
# out even the implied warranty of  MERCHANTABILITY  or  FITNESS FOR A
# PARTICULAR PURPOSE. See the  GNU General Public License for more de-
# tails. You should have  received  a copy of the  GNU  General Public
# License along with GNU Make; see the file  COPYING.  If  not,  write
# to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
# Boston, MA 02110-1301 USA.

import os
import re
import pprint
from typing import Text, Dict, Union, NamedTuple, List, Optional  # pylint: disable=unused-import

import cmk.utils.store as store
import cmk.utils.rulesets.ruleset_matcher as ruleset_matcher
from cmk.utils.labels import LabelManager

import cmk.gui.config as config
from cmk.gui.log import logger
from cmk.gui.globals import html
from cmk.gui.i18n import _
from cmk.gui.exceptions import MKGeneralException

from cmk.gui.watolib.utils import has_agent_bakery
from cmk.gui.watolib.changes import add_change
from cmk.gui.watolib.rulespecs import (
    rulespec_registry,
    rulespec_group_registry,
)
from cmk.gui.watolib.hosts_and_folders import (
    Folder,
    Host,
)
from cmk.gui.watolib.utils import (
    ALL_HOSTS,
    ALL_SERVICES,
    NEGATE,
)

# This macro is needed to make the to_config() methods be able to use native
# pprint/repr for the ruleset data structures. Have a look at
# to_config_with_folder_macro() for further information.
_FOLDER_PATH_MACRO = "%#%FOLDER_PATH%#%"


class RuleConditions(object):
    def __init__(self,
                 host_folder,
                 host_tags=None,
                 host_labels=None,
                 host_name=None,
                 service_description=None,
                 service_labels=None):
        # type: (str, Dict[str, str], Dict[str, str], Optional[Union[Dict[str, List[str]], List[str]]], Optional[List[str]], Dict[str, str]) -> None
        self.host_folder = host_folder
        self.host_tags = host_tags or {}
        self.host_labels = host_labels or {}
        self.host_name = host_name
        self.service_description = service_description
        self.service_labels = service_labels or {}

    def from_config(self, conditions):
        self.host_folder = conditions.get("host_folder", self.host_folder)
        self.host_tags = conditions.get("host_tags", {})
        self.host_labels = conditions.get("host_labels", {})
        self.host_name = conditions.get("host_name")
        self.service_description = conditions.get("service_description")
        self.service_labels = conditions.get("service_labels", {})
        return self

    def to_config_with_folder_macro(self):
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

    def to_config_with_folder(self):
        cfg = self._to_config()
        cfg["host_folder"] = self.host_folder
        return cfg

    def to_config_without_folder(self):
        return self._to_config()

    def _to_config(self):
        cfg = {}

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

    def has_only_explicit_service_conditions(self):
        if self.service_description is None:
            return

        return all([
            not isinstance(i, dict) or i["$regex"].endswith("$") for i in self.service_description
        ])

    # Compatibility code for pre 1.6 WATO code
    @property
    def tag_list(self):
        tag_list = []
        for tag_spec in self.host_tags.itervalues():
            is_not = isinstance(tag_spec, dict) and "$ne" in tag_spec
            if is_not:
                tag_id = tag_spec["$ne"]
            else:
                tag_id = tag_spec

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

    def _condition_list(self, object_list, is_service):
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


class RulesetCollection(object):
    """Abstract class for holding a collection of rulesets. The most basic
    specific class is the FolderRulesets class which cares about all rulesets
    configured in a folder."""
    def __init__(self):
        super(RulesetCollection, self).__init__()
        # A dictionary containing all ruleset objects of the collection.
        # The name of the ruleset is used as key in the dict.
        self._tag_to_group_map = ruleset_matcher.get_tag_to_group_map(config.tags)
        self._rulesets = {}

    # Has to be implemented by the subclasses to load the right rulesets
    def load(self):
        raise NotImplementedError()

    def _load_folder_rulesets(self, folder, only_varname=None):
        path = folder.rules_file_path()

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
            if ':' in varname:
                dictname, _subkey = varname.split(":")
                config_dict[dictname] = {}
            else:
                config_dict[varname] = []

        # Initialize rulesets once
        self._initialize_rulesets(only_varname=only_varname)

        if os.path.exists(path):
            self.from_config(folder, store.load_mk_file(path, config_dict), only_varname)

    def _initialize_rulesets(self, only_varname=None):
        if only_varname:
            varnames = [only_varname]
        else:
            varnames = rulespec_registry.keys()

        for varname in varnames:
            if varname in self._rulesets:
                continue
            self._rulesets[varname] = Ruleset(varname, self._tag_to_group_map)

    def from_config(self, folder, rulesets_config, only_varname=None):
        if only_varname:
            varnames = [only_varname]
        else:
            varnames = rulespec_registry.keys()

        for varname in varnames:
            if varname not in self._rulesets:
                self._rulesets[varname] = Ruleset(varname, self._tag_to_group_map)
            if ':' in varname:
                dictname, subkey = varname.split(":")
                ruleset_config = rulesets_config.get(dictname, {})
                if subkey in ruleset_config:
                    self._rulesets[varname].from_config(folder, ruleset_config[subkey])
            else:
                self._rulesets[varname].from_config(folder, rulesets_config.get(varname, []))

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

        # Adding this instead of the full path makes it easy to move config
        # files around. The real FOLDER_PATH will be added dynamically while
        # loading the file in cmk_base.config
        content = content.replace("'%s'" % _FOLDER_PATH_MACRO, "'/' + FOLDER_PATH")

        rules_file_path = folder.rules_file_path()
        # Remove rules files if it has no content. This prevents needless reads
        if not has_content and os.path.exists(rules_file_path):
            os.unlink(rules_file_path)
            return

        store.save_mk_file(rules_file_path, content, add_header=not config.wato_use_git)

    def exists(self, name):
        return name in self._rulesets

    def get(self, name, deflt=None):
        return self._rulesets[name]

    def set(self, name, ruleset):
        self._rulesets[name] = ruleset

    def get_rulesets(self):
        return self._rulesets

    def set_rulesets(self, rulesets):
        self._rulesets = rulesets

    # Groups the rulesets in 3 layers (main group, sub group, rulesets)
    def get_grouped(self):
        grouped_dict = {}
        for ruleset in self._rulesets.itervalues():
            main_group = grouped_dict.setdefault(ruleset.rulespec.main_group_name, {})
            group_rulesets = main_group.setdefault(ruleset.rulespec.group_name, [])
            group_rulesets.append(ruleset)

        grouped = []
        for main_group_name, sub_groups in grouped_dict.items():
            sub_group_list = []

            for group_name, group_rulesets in sorted(sub_groups.items(), key=lambda x: x[0]):
                sub_group_list.append((group_name, sorted(group_rulesets, key=lambda x: x.title())))

            grouped.append((main_group_name, sub_group_list))

        return grouped


class AllRulesets(RulesetCollection):
    def _load_rulesets_recursively(self, folder, only_varname=None):
        for subfolder in folder.all_subfolders().values():
            self._load_rulesets_recursively(subfolder, only_varname)

        self._load_folder_rulesets(folder, only_varname)

    def load(self):
        """Load all rules of all folders"""
        self._load_rulesets_recursively(Folder.root_folder())

    def save_folder(self, folder):
        self._save_folder(folder)

    def save(self):
        """Save all rulesets of all folders recursively"""
        self._save_rulesets_recursively(Folder.root_folder())

    def _save_rulesets_recursively(self, folder):
        for subfolder in folder.all_subfolders().values():
            self._save_rulesets_recursively(subfolder)

        self._save_folder(folder)


class SingleRulesetRecursively(AllRulesets):
    def __init__(self, name):
        super(SingleRulesetRecursively, self).__init__()
        self._name = name

    # Load single ruleset from all folders
    def load(self):
        self._load_rulesets_recursively(Folder.root_folder(), only_varname=self._name)

    def save_folder(self, folder):
        raise NotImplementedError()


class FolderRulesets(RulesetCollection):
    def __init__(self, folder):
        super(FolderRulesets, self).__init__()
        self._folder = folder

    def load(self):
        self._load_folder_rulesets(self._folder)

    def save(self):
        self._save_folder(self._folder)


class FilteredRulesetCollection(AllRulesets):
    def save(self):
        raise NotImplementedError("Filtered ruleset collections can not be saved.")


class StaticChecksRulesets(FilteredRulesetCollection):
    def load(self):
        super(StaticChecksRulesets, self).load()
        self._remove_non_static_checks_rulesets()

    def _remove_non_static_checks_rulesets(self):
        for name, ruleset in self._rulesets.items():
            if ruleset.rulespec.main_group_name != "static":
                del self._rulesets[name]


class NonStaticChecksRulesets(FilteredRulesetCollection):
    def load(self):
        super(NonStaticChecksRulesets, self).load()
        self._remove_static_checks_rulesets()

    def _remove_static_checks_rulesets(self):
        for name, ruleset in self._rulesets.items():
            if ruleset.rulespec.main_group_name == "static":
                del self._rulesets[name]


class SearchedRulesets(FilteredRulesetCollection):
    def __init__(self, origin_rulesets, search_options):
        super(SearchedRulesets, self).__init__()
        self._origin_rulesets = origin_rulesets
        self._search_options = search_options
        self._load_filtered()

    def _load_filtered(self):
        """Iterates the rulesets from the original collection,
        applies the search option and takes over the rulesets
        that have at least one matching rule or match itself,
        e.g. by their name, title or help."""

        for ruleset in self._origin_rulesets.get_rulesets().values():
            if ruleset.matches_search_with_rules(self._search_options):
                self._rulesets[ruleset.name] = ruleset


# TODO: Cleanup the rule indexing by position in the rules list. The "rule_nr" is used
# as index accross several HTTP requests where other users may have done something with
# the ruleset. In worst cases the user modifies a rule which should not be modified.
class Ruleset(object):
    def __init__(self, name, tag_to_group_map):
        super(Ruleset, self).__init__()
        self.name = name
        self.rulespec = rulespec_registry[name]()
        # Holds list of the rules. Using the folder paths as keys.
        self._rules = {}

        # Temporary needed during search result processing
        self.search_matching_rules = []

        # Converts pre 1.6 tuple rulesets in place to 1.6+ format
        self.tuple_transformer = ruleset_matcher.RulesetToDictTransformer(
            tag_to_group_map=tag_to_group_map)

    def is_empty(self):
        return self.num_rules() == 0

    def is_empty_in_folder(self, folder):
        return not bool(self.get_folder_rules(folder))

    def num_rules(self):
        return sum([len(rules) for rules in self._rules.values()])

    def num_rules_in_folder(self, folder):
        return len(self.get_folder_rules(folder))

    def get_rules(self):
        rules = []
        for _folder_path, folder_rules in self._rules.items():
            for rule_index, rule in enumerate(folder_rules):
                rules.append((rule.folder, rule_index, rule))
        return sorted(rules,
                      key=lambda x: (x[0].path().split("/"), len(rules) - x[1]),
                      reverse=True)

    def get_folder_rules(self, folder):
        try:
            return self._rules[folder.path()]
        except KeyError:
            return []

    def prepend_rule(self, folder, rule):
        rules = self._rules.setdefault(folder.path(), [])
        rules.insert(0, rule)
        self._on_change()

    def append_rule(self, folder, rule):
        rules = self._rules.setdefault(folder.path(), [])
        rules.append(rule)
        self._on_change()

    def insert_rule_after(self, rule, after):
        index = self._rules[rule.folder.path()].index(after) + 1
        self._rules[rule.folder.path()].insert(index, rule)
        add_change("clone-ruleset",
                   _("Cloned rule in ruleset '%s'") % self.title(),
                   sites=rule.folder.all_site_ids())
        self._on_change()

    def from_config(self, folder, rules_config):
        if not rules_config:
            return

        # Resets the rules of this ruleset for this folder!
        self._rules[folder.path()] = []

        self.tuple_transformer.transform_in_place(rules_config,
                                                  is_service=bool(self.item_type()),
                                                  is_binary=not self.valuespec())

        for rule_config in rules_config:
            rule = Rule(folder, self)
            rule.from_config(rule_config)
            self._rules[folder.path()].append(rule)

    def to_config(self, folder):
        content = ""

        if ":" in self.name:
            dictname, subkey = self.name.split(':')
            varname = "%s[%r]" % (dictname, subkey)

            content += "\n%s.setdefault(%r, [])\n" % (dictname, subkey)
        else:
            varname = self.name

            content += "\nglobals().setdefault(%r, [])\n" % (varname)

            if self.is_optional():
                content += "\nif %s is None:\n    %s = []\n" % (varname, varname)

        # When using pprint we get a deterministic representation of the
        # data structures because it cares about sorting of the dict keys
        repr_func = pprint.pformat if config.wato_use_git else repr

        content += "\n%s = [\n" % varname
        for rule in self._rules[folder.path()]:
            content += "%s,\n" % repr_func(rule.to_config())
        content += "] + %s\n\n" % varname

        return content

    # Whether or not either the ruleset itself matches the search or the rules match
    def matches_search_with_rules(self, search_options):
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

    def has_rule_search_options(self, search_options):
        return bool([k for k in search_options.keys() if k == "fulltext" or k.startswith("rule_")])

    def matches_fulltext_search(self, search_options):
        return _match_one_of_search_expression(
            search_options, "fulltext",
            [self.name, self.title(), self.help()])

    def matches_ruleset_search_options(self, search_options):
        if "ruleset_deprecated" in search_options and search_options[
                "ruleset_deprecated"] != self.is_deprecated():
            return False

        if "ruleset_used" in search_options and search_options["ruleset_used"] is self.is_empty():
            return False

        if "ruleset_group" in search_options and not self._matches_group_search(search_options):
            return False

        if not _match_search_expression(search_options, "ruleset_name", self.name):
            return False

        if not _match_search_expression(search_options, "ruleset_title", self.title()):
            return False

        if not _match_search_expression(search_options, "ruleset_help", self.help()):
            return False

        return True

    def _matches_group_search(self, search_options):
        # All rulesets are in a single group. Only the two rulesets "agent_ports" and
        # "agent_encryption" are in the RulespecGroupAgentCMKAgent but are also used
        # by the agent bakery. Users often try to find the ruleset in the wrong group.
        # For this reason we make the ruleset available in both groups.
        # Instead of making the ruleset specification more complicated for this special
        # case we hack it here into the ruleset search which is used to populate the
        # group pages.
        if search_options["ruleset_group"] == "agents" and self.rulespec.name in [
                "agent_ports", "agent_encryption"
        ]:
            return True

        return self.rulespec.group_name \
            in rulespec_group_registry.get_matching_group_names(search_options["ruleset_group"])

    def get_rule(self, folder, rule_index):
        return self._rules[folder.path()][rule_index]

    def edit_rule(self, rule):
        add_change("edit-rule",
                   _("Changed properties of rule \"%s\" in folder \"%s\"") %
                   (self.title(), rule.folder.alias_path()),
                   sites=rule.folder.all_site_ids())
        self._on_change()

    def delete_rule(self, rule):
        self._rules[rule.folder.path()].remove(rule)
        add_change("edit-ruleset",
                   _("Deleted rule in ruleset '%s'") % self.title(),
                   sites=rule.folder.all_site_ids())
        self._on_change()

    def move_rule_up(self, rule):
        rules = self._rules[rule.folder.path()]
        index = rules.index(rule)
        del rules[index]
        rules[index - 1:index - 1] = [rule]
        add_change("edit-ruleset",
                   _("Moved rule #%d up in ruleset \"%s\"") % (index, self.title()),
                   sites=rule.folder.all_site_ids())

    def move_rule_down(self, rule):
        rules = self._rules[rule.folder.path()]
        index = rules.index(rule)
        del rules[index]
        rules[index + 1:index + 1] = [rule]
        add_change("edit-ruleset",
                   _("Moved rule #%d down in ruleset \"%s\"") % (index, self.title()),
                   sites=rule.folder.all_site_ids())

    def move_rule_to_top(self, rule):
        rules = self._rules[rule.folder.path()]
        index = rules.index(rule)
        rules.remove(rule)
        rules.insert(0, rule)
        add_change("edit-ruleset",
                   _("Moved rule #%d to top in ruleset \"%s\"") % (index, self.title()),
                   sites=rule.folder.all_site_ids())

    def move_rule_to_bottom(self, rule):
        rules = self._rules[rule.folder.path()]
        index = rules.index(rule)
        rules.remove(rule)
        rules.append(rule)
        add_change("edit-ruleset",
                   _("Moved rule #%d to bottom in ruleset \"%s\"") % (index, self.title()),
                   sites=rule.folder.all_site_ids())

    def move_rule_to(self, rule, index):
        rules = self._rules[rule.folder.path()]
        old_index = rules.index(rule)
        rules.remove(rule)
        rules.insert(index, rule)
        add_change("edit-ruleset",
                   _("Moved rule #%d to #%d in ruleset \"%s\"") % (old_index, index, self.title()),
                   sites=rule.folder.all_site_ids())

    # TODO: Remove these getters
    def valuespec(self):
        return self.rulespec.valuespec

    def help(self):
        return self.rulespec.help

    def title(self):
        return self.rulespec.title

    def item_type(self):
        return self.rulespec.item_type

    def item_name(self):
        return self.rulespec.item_name

    def item_help(self):
        return self.rulespec.item_help

    def item_enum(self):
        return self.rulespec.item_enum

    def match_type(self):
        return self.rulespec.match_type

    def is_deprecated(self):
        return self.rulespec.is_deprecated

    def is_optional(self):
        return self.rulespec.is_optional

    def _on_change(self):
        if has_agent_bakery():
            import cmk.gui.cee.agent_bakery as agent_bakery
            agent_bakery.ruleset_changed(self.name)

    # Returns the outcoming value or None and a list of matching rules. These are pairs
    # of rule_folder and rule_number
    def analyse_ruleset(self, hostname, service):
        resultlist = []
        resultdict = {}
        effectiverules = []
        for folder, rule_index, rule in self.get_rules():
            if rule.is_disabled():
                continue

            if not rule.matches_host_and_item(Folder.current(), hostname, service):
                continue

            if self.match_type() == "all":
                resultlist.append(rule.value)
                effectiverules.append((folder, rule_index, rule))

            elif self.match_type() == "list":
                resultlist += rule.value
                effectiverules.append((folder, rule_index, rule))

            elif self.match_type() == "dict":
                new_result = rule.value.copy()  # pylint: disable=no-member
                new_result.update(resultdict)
                resultdict = new_result
                effectiverules.append((folder, rule_index, rule))

            else:
                return rule.value, [(folder, rule_index, rule)]

        if self.match_type() in ("list", "all"):
            return resultlist, effectiverules

        elif self.match_type() == "dict":
            return resultdict, effectiverules

        return None, []  # No match


class Rule(object):
    @classmethod
    def create(cls, folder, ruleset):
        rule = Rule(folder, ruleset)
        if rule.ruleset.valuespec():
            rule.value = rule.ruleset.valuespec().default_value()
        return rule

    def __init__(self, folder, ruleset):
        super(Rule, self).__init__()
        self.ruleset = ruleset
        self.folder = folder

        # Content of the rule itself
        self._initialize()

    def clone(self):
        cloned = Rule(self.folder, self.ruleset)
        cloned.from_config(self.to_config())
        return cloned

    def _initialize(self):
        self.conditions = RuleConditions(self.folder.path())
        self.rule_options = {}
        if self.ruleset.valuespec():
            self.value = None
        else:
            self.value = True

    def from_config(self, rule_config):
        try:
            self._initialize()
            self._parse_rule(rule_config)
        except Exception:
            logger.exception()
            raise MKGeneralException(_("Invalid rule <tt>%s</tt>") % (rule_config,))

    def _parse_rule(self, rule_config):
        if isinstance(rule_config, dict):
            self._parse_dict_rule(rule_config)
        else:
            raise NotImplementedError()

    def _parse_dict_rule(self, rule_config):
        self.rule_options = rule_config.get("options", {})
        self.value = rule_config["value"]

        conditions = rule_config["condition"].copy()

        # Is known because of the folder associated with this object. Remove the
        # rendundant information here. It will be added dynamically in to_config()
        # for writing it back
        conditions.pop("host_folder", None)

        self.conditions = RuleConditions(self.folder.path())
        self.conditions.from_config(conditions)

    def to_config(self):
        # Special case: The main folder must not have a host_folder condition, because
        # these rules should also affect non WATO hosts.
        for_config = self.conditions.to_config_with_folder_macro() \
            if not self.folder.is_root() else self.conditions.to_config_without_folder()
        return self._to_config(for_config)

    def to_web_api(self):
        return self._to_config(self.conditions.to_config_without_folder())

    def _to_config(self, conditions):
        result = {
            "value": self.value,
            "condition": conditions,
        }

        rule_options = self._rule_options_to_config()
        if rule_options:
            result["options"] = rule_options

        return result

    def _rule_options_to_config(self):
        ro = {}
        if self.rule_options.get("disabled"):
            ro["disabled"] = True
        if self.rule_options.get("description"):
            ro["description"] = self.rule_options["description"]
        if self.rule_options.get("comment"):
            ro["comment"] = self.rule_options["comment"]
        if self.rule_options.get("docu_url"):
            ro["docu_url"] = self.rule_options["docu_url"]

        # Preserve other keys that we do not know of
        for k, v in self.rule_options.items():
            if k not in ["disabled", "description", "comment", "docu_url"]:
                ro[k] = v

        return ro

    def is_ineffective(self):
        hosts = Host.all()
        for host_name, host in hosts.items():
            if self.matches_host_and_item(host.folder(), host_name, service_description=None):
                return False
        return True

    def matches_host_and_item(self, host_folder, hostname, service_description):
        """Whether or not the given folder/host/item matches this rule"""
        return not any(
            True for _r in self.get_mismatch_reasons(host_folder, hostname, service_description))

    def get_mismatch_reasons(self, host_folder, hostname, service_description):
        """A generator that provides the reasons why a given folder/host/item not matches this rule"""
        host = host_folder.host(hostname)
        if host is None:
            raise MKGeneralException("Failed to get host from folder %r." % host_folder.path())

        service_labels = None  # TODO: Need to get the service labels
        match_object = ruleset_matcher.RulesetMatchObject(
            host_name=hostname,
            service_description=service_description,
            service_labels=service_labels,
        )

        for reason in self._get_mismatch_reasons_of_match_object(
                match_object,
                host_folder=host_folder.path_for_rule_matching(),
                host_tag_list=host.tags(),
                host_labels=host.labels()):
            yield reason

    def matches_item(self, item):
        match_object = ruleset_matcher.RulesetMatchObject(
            host_name=None,
            service_description=item,
        )
        return any(
            self._get_mismatch_reasons_of_match_object(
                match_object,
                host_folder="/",
                host_tag_list=[],
                host_labels={},
            ))

    def _get_mismatch_reasons_of_match_object(self, match_object, host_folder, host_tag_list,
                                              host_labels):
        # TODO:
        # - What about the host_label_rules and service_label_rules?
        # - The autochecks_manager also needs to be available here!
        # Both is only working with cmk_base code which has the checks and config loaded.
        label_manager = LabelManager(
            explicit_host_labels={match_object.host_name: host_labels},
            host_label_rules=[],
            service_label_rules=[],
            autochecks_manager=None,
        )

        matcher = ruleset_matcher.RulesetMatcher(
            tag_to_group_map=ruleset_matcher.get_tag_to_group_map(config.tags),
            host_tag_lists={match_object.host_name: host_tag_list},
            host_paths={match_object.host_name: host_folder},
            labels=label_manager,
            all_configured_hosts={match_object.host_name},
            clusters_of={},
            nodes_of={},
        )

        rule_dict = self.to_config()
        rule_dict["condition"]["host_folder"] = self.folder.path_for_rule_matching()

        if self.ruleset.item_type():
            if matcher.is_matching_service_ruleset(match_object, [rule_dict]):
                return
        else:
            if matcher.is_matching_host_ruleset(match_object, [rule_dict]):
                return

        yield _("The rule does not match")

    def matches_search(self, search_options):
        if "rule_folder" in search_options and self.folder.name() not in self._get_search_folders(
                search_options):
            return False

        if "rule_disabled" in search_options and search_options[
                "rule_disabled"] != self.is_disabled():
            return False

        if "rule_predefined_condition" in search_options and search_options[
                "rule_predefined_condition"] != self.predefined_condition_id():
            return False

        if "rule_ineffective" in search_options and search_options[
                "rule_ineffective"] != self.is_ineffective():
            return False

        if not _match_search_expression(search_options, "rule_description", self.description()):
            return False

        if not _match_search_expression(search_options, "rule_comment", self.comment()):
            return False

        if "rule_value" in search_options and not self.ruleset.valuespec():
            return False

        value_text = None
        if self.ruleset.valuespec():
            try:
                value_text = "%s" % self.ruleset.valuespec().value_to_text(self.value)
            except Exception as e:
                logger.exception()
                html.show_warning(
                    _("Failed to search rule of ruleset '%s' in folder '%s' (%r): %s") %
                    (self.ruleset.title(), self.folder.title(), self.to_config(), e))

        if value_text is not None and not _match_search_expression(search_options, "rule_value",
                                                                   value_text):
            return False

        if self.conditions.host_list \
            and not _match_one_of_search_expression(search_options, "rule_host_list", self.conditions.host_list[0]):
            return False

        if self.conditions.item_list \
           and not _match_one_of_search_expression(search_options, "rule_item_list", self.conditions.item_list[0]):
            return False

        to_search = [
            self.comment(),
            self.description(),
        ] + (self.conditions.host_list[0] if self.conditions.host_list else []) \
          + (self.conditions.item_list[0] if self.conditions.item_list else [])

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

    def _get_search_folders(self, search_options):
        current_folder, do_recursion = search_options["rule_folder"]
        current_folder = Folder.folder(current_folder)
        search_in_folders = [current_folder.name()]
        if do_recursion:
            search_in_folders = [
                x.split("/")[-1] for x, _y in current_folder.recursive_subfolder_choices()
            ]
        return search_in_folders

    def index(self):
        return self.ruleset.get_folder_rules(self.folder).index(self)

    def is_disabled(self):
        return self.rule_options.get("disabled", False)

    def description(self):
        return self.rule_options.get("description", "")

    def comment(self):
        return self.rule_options.get("comment", "")

    def predefined_condition_id(self):
        # type: () -> Optional[str]
        """When a rule refers to a predefined condition return the ID

        The predefined conditions are a pure WATO feature. These are resolved when writing
        the configuration down for Check_MK base. The configured condition ID is preserved
        in the rule options for the moment.
        """
        #TODO: Once we switched the rule format to be dict base, we can move this key to the conditions dict
        return self.rule_options.get("predefined_condition_id")

    def update_conditions(self, conditions):
        # type: (RuleConditions) -> None
        self.conditions = conditions

    def get_rule_conditions(self):
        # type: () -> RuleConditions
        return self.conditions

    def is_discovery_rule_of(self, host):
        return self.conditions.host_name == [host.name()] \
               and self.conditions.host_tags == {} \
               and self.conditions.has_only_explicit_service_conditions() \
               and self.folder.is_transitive_parent_of(host.folder())

    def replace_explicit_host_condition(self, old_name, new_name):
        """Does an in-place(!) replacement of explicit (non regex) hostnames in rules"""
        if self.conditions.host_name is None:
            return False

        did_rename = False
        _negate, host_conditions = ruleset_matcher.parse_negated_condition_list(
            self.conditions.host_name)

        for index, condition in enumerate(host_conditions):
            if condition == old_name:
                host_conditions[index] = new_name
                did_rename = True

        return did_rename


def _match_search_expression(search_options, attr_name, search_in):
    if attr_name not in search_options:
        return True  # not searched for this. Matching!

    return search_in and re.search(search_options[attr_name], search_in, re.I) is not None


def _match_one_of_search_expression(search_options, attr_name, search_in_list):
    for search_in in search_in_list:
        if _match_search_expression(search_options, attr_name, search_in):
            return True
    return False
