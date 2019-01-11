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

import re

import cmk.utils.regex
import cmk.utils.store as store

from cmk.gui.log import logger
from cmk.gui.globals import html
from cmk.gui.i18n import _
from cmk.gui.exceptions import MKGeneralException

from cmk.gui.watolib.utils import has_agent_bakery
from cmk.gui.watolib.changes import add_change
from cmk.gui.watolib.rulespecs import g_rulespecs
from cmk.gui.watolib.hosts_and_folders import (
    Folder,
    Host,
)
from cmk.gui.watolib.utils import (
    ALL_HOSTS,
    ALL_SERVICES,
    NO_ITEM,
    NEGATE,
    ENTRY_NEGATE_CHAR,
)


class RulesetCollection(object):
    """Abstract class for holding a collection of rulesets. The most basic
    specific class is the FolderRulesets class which cares about all rulesets
    configured in a folder."""

    def __init__(self):
        super(RulesetCollection, self).__init__()
        # A dictionary containing all ruleset objects of the collection.
        # The name of the ruleset is used as key in the dict.
        self._rulesets = {}

    # Has to be implemented by the subclasses to load the right rulesets
    def load(self):
        raise NotImplementedError()

    def _load_folder_rulesets(self, folder, only_varname=None):
        path = folder.rules_file_path()

        config = {
            "ALL_HOSTS": ALL_HOSTS,
            "ALL_SERVICES": [""],
            "NEGATE": NEGATE,
            "FOLDER_PATH": folder.path(),
            "FILE_PATH": folder.path() + "/hosts.mk",
        }

        # Prepare empty rulesets so that rules.mk has something to
        # append to. We need to initialize all variables here, even
        # when only loading with only_varname.
        for varname in g_rulespecs.get_rulespecs():
            if ':' in varname:
                dictname, _subkey = varname.split(":")
                config[dictname] = {}
            else:
                config[varname] = []

        self.from_config(folder, store.load_mk_file(path, config), only_varname)

    def from_config(self, folder, rulesets_config, only_varname=None):
        for varname in g_rulespecs.get_rulespecs():
            if only_varname and varname != only_varname:
                continue  # skip unwanted options

            ruleset = self._rulesets.setdefault(varname, Ruleset(varname))

            if ':' in varname:
                dictname, subkey = varname.split(":")
                ruleset_config = rulesets_config.get(dictname, {})
                if subkey in ruleset_config:
                    ruleset.from_config(folder, ruleset_config[subkey])
            else:
                ruleset.from_config(folder, rulesets_config.get(varname, []))

    def save(self):
        raise NotImplementedError()

    def save_folder(self, folder):
        raise NotImplementedError()

    def _save_folder(self, folder):
        store.mkdir(folder.get_root_dir())

        content = ""
        for varname, ruleset in sorted(self._rulesets.items(), key=lambda x: x[0]):
            if not g_rulespecs.exists(varname):
                continue  # don't save unknown rulesets

            if ruleset.is_empty_in_folder(folder):
                continue  # don't save empty rule sets

            content += ruleset.to_config(folder)

        store.save_mk_file(folder.rules_file_path(), content)

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
            group_rulesets = main_group.setdefault(ruleset.rulespec.sub_group_name, [])
            group_rulesets.append(ruleset)

        grouped = []
        for main_group_name, sub_groups in grouped_dict.items():
            sub_group_list = []

            for sub_group_title, group_rulesets in sorted(sub_groups.items(), key=lambda x: x[0]):
                sub_group_list.append((sub_group_title,
                                       sorted(group_rulesets, key=lambda x: x.title())))

            grouped.append((main_group_name, sub_group_list))

        return grouped


class AllRulesets(RulesetCollection):
    def _load_rulesets_recursively(self, folder, only_varname=None):
        for subfolder in folder.all_subfolders().values():
            self._load_rulesets_recursively(subfolder, only_varname)

        self._load_folder_rulesets(folder, only_varname)

    # Load all rules of all folders
    def load(self):
        self._load_rulesets_recursively(Folder.root_folder())

    def save_folder(self, folder):
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
    def __init__(self, name):
        super(Ruleset, self).__init__()
        self.name = name
        self.rulespec = g_rulespecs.get(name)
        # Holds list of the rules. Using the folder paths as keys.
        self._rules = {}

        # Temporary needed during search result processing
        self.search_matching_rules = []

    def is_empty(self):
        return not self._rules

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
        return sorted(
            rules, key=lambda x: (x[0].path().split("/"), len(rules) - x[1]), reverse=True)

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
        add_change(
            "clone-ruleset",
            _("Cloned rule in ruleset '%s'") % self.title(),
            sites=rule.folder.all_site_ids())
        self._on_change()

    def from_config(self, folder, rules_config):
        if not rules_config:
            return

        # Resets the rules of this ruleset for this folder!
        self._rules[folder.path()] = []

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

        content += "\n%s = [\n" % varname
        for rule in self._rules[folder.path()]:
            content += rule.to_config()
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

        if "ruleset_used" in search_options and search_options["ruleset_used"] == self.is_empty():
            return False

        if "ruleset_group" in search_options \
           and self.rulespec.group_name not in g_rulespecs.get_matching_groups(search_options["ruleset_group"]):
            return False

        if not _match_search_expression(search_options, "ruleset_name", self.name):
            return False

        if not _match_search_expression(search_options, "ruleset_title", self.title()):
            return False

        if not _match_search_expression(search_options, "ruleset_help", self.help()):
            return False

        return True

    def get_rule(self, folder, rule_index):
        return self._rules[folder.path()][rule_index]

    def edit_rule(self, rule):
        add_change(
            "edit-rule",
            _("Changed properties of rule \"%s\" in folder \"%s\"") % (self.title(),
                                                                       rule.folder.alias_path()),
            sites=rule.folder.all_site_ids())
        self._on_change()

    def delete_rule(self, rule):
        self._rules[rule.folder.path()].remove(rule)
        add_change(
            "edit-ruleset",
            _("Deleted rule in ruleset '%s'") % self.title(),
            sites=rule.folder.all_site_ids())
        self._on_change()

    def move_rule_up(self, rule):
        rules = self._rules[rule.folder.path()]
        index = rules.index(rule)
        del rules[index]
        rules[index - 1:index - 1] = [rule]
        add_change(
            "edit-ruleset",
            _("Moved rule #%d up in ruleset \"%s\"") % (index, self.title()),
            sites=rule.folder.all_site_ids())

    def move_rule_down(self, rule):
        rules = self._rules[rule.folder.path()]
        index = rules.index(rule)
        del rules[index]
        rules[index + 1:index + 1] = [rule]
        add_change(
            "edit-ruleset",
            _("Moved rule #%d down in ruleset \"%s\"") % (index, self.title()),
            sites=rule.folder.all_site_ids())

    def move_rule_to_top(self, rule):
        rules = self._rules[rule.folder.path()]
        index = rules.index(rule)
        rules.remove(rule)
        rules.insert(0, rule)
        add_change(
            "edit-ruleset",
            _("Moved rule #%d to top in ruleset \"%s\"") % (index, self.title()),
            sites=rule.folder.all_site_ids())

    def move_rule_to_bottom(self, rule):
        rules = self._rules[rule.folder.path()]
        index = rules.index(rule)
        rules.remove(rule)
        rules.append(rule)
        add_change(
            "edit-ruleset",
            _("Moved rule #%d to bottom in ruleset \"%s\"") % (index, self.title()),
            sites=rule.folder.all_site_ids())

    def move_rule_to(self, rule, index):
        rules = self._rules[rule.folder.path()]
        old_index = rules.index(rule)
        rules.remove(rule)
        rules.insert(index, rule)
        add_change(
            "edit-ruleset",
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
    def create(cls, folder, ruleset, host_list, item_list):
        rule = Rule(folder, ruleset)

        if rule.ruleset.valuespec():
            rule.value = rule.ruleset.valuespec().default_value()

        rule.host_list = host_list

        if rule.ruleset.item_type():
            rule.item_list = item_list

        return rule

    def __init__(self, folder, ruleset):
        super(Rule, self).__init__()
        self.ruleset = ruleset
        self.folder = folder

        # Content of the rule itself
        self._initialize()

    def clone(self):
        cloned = Rule(self.folder, self.ruleset)
        cloned.from_config(self._format_rule())
        return cloned

    def _initialize(self):
        self.tag_specs = []
        self.host_list = []
        self.item_list = None
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
            raise MKGeneralException(_("Invalid rule <tt>%s</tt>") % (rule_config,))

    def _parse_rule(self, rule_config):
        if isinstance(rule_config, dict):
            self._parse_dict_rule(rule_config)
        else:  # tuple
            self._parse_tuple_rule(rule_config)

    def _parse_dict_rule(self, rule_config):
        self.rule_options = rule_config.get("options", {})

        # Extract value from front, if rule has a value
        if self.ruleset.valuespec():
            self.value = rule_config["value"]
        else:
            if rule_config.get("negate"):
                self.value = False
            else:
                self.value = True

        conditions = rule_config.get("conditions", {})
        self.host_list = conditions.get("host_specs", [])
        self.item_list = conditions.get("service_specs")

        # Remove folder tag from tag list
        tag_specs = conditions.get("host_tags", [])
        self.tag_specs = [t for t in tag_specs if not t.startswith("/")]

    def _parse_tuple_rule(self, rule_config):
        if isinstance(rule_config[-1], dict):
            self.rule_options = rule_config[-1]
            rule_config = rule_config[:-1]

        # Extract value from front, if rule has a value
        if self.ruleset.valuespec():
            self.value = rule_config[0]
            rule_config = rule_config[1:]
        else:
            if rule_config[0] == NEGATE:
                self.value = False
                rule_config = rule_config[1:]
            else:
                self.value = True

        # Extract liste of items from back, if rule has items
        if self.ruleset.item_type():
            self.item_list = rule_config[-1]
            rule_config = rule_config[:-1]

        # Rest is host list or tag list + host list
        if len(rule_config) == 1:
            tag_specs = []
            self.host_list = rule_config[0]
        else:
            tag_specs = rule_config[0]
            self.host_list = rule_config[1]

        # Remove folder tag from tag list
        self.tag_specs = [t for t in tag_specs if not t.startswith("/")]

    def to_config(self):
        content = "  ( "

        if self.ruleset.valuespec():
            content += repr(self.value) + ", "
        elif not self.value:
            content += "NEGATE, "

        content += "["
        for tag in self.tag_specs:
            content += repr(tag)
            content += ", "

        if not self.folder.is_root():
            content += "'/' + FOLDER_PATH + '/+'"

        content += "], "

        if self.host_list and self.host_list[-1] == ALL_HOSTS[0]:
            if len(self.host_list) > 1:
                content += repr(self.host_list[:-1])
                content += " + ALL_HOSTS"
            else:
                content += "ALL_HOSTS"
        else:
            content += repr(self.host_list)

        if self.ruleset.item_type():
            content += ", "
            if self.item_list == ALL_SERVICES:
                content += "ALL_SERVICES"
            else:
                if self.item_list[-1] == ALL_SERVICES[0]:
                    content += repr(self.item_list[:-1])
                    content += " + ALL_SERVICES"
                else:
                    content += repr(self.item_list)

        if self.rule_options:
            content += ", %r" % self._rule_options_to_config()

        content += " ),\n"

        return content

    def to_dict_config(self):
        result = {"conditions": {}}

        result["path"] = self.folder.path()
        result["options"] = self._rule_options_to_config()

        if self.ruleset.valuespec():
            result["value"] = self.value
        else:
            if self.value:
                result["negate"] = False
            else:
                result["negate"] = True

        result["conditions"]["host_specs"] = self.host_list
        result["conditions"]["host_tags"] = self.tag_specs

        if self.ruleset.item_type():
            result["conditions"]["service_specs"] = self.item_list

        return result

    def _format_rule(self):
        if self.ruleset.valuespec():
            rule = [self.value]
        elif not self.value:
            rule = [NEGATE]
        else:
            rule = []

        if self.tag_specs != []:
            rule.append(self.tag_specs)

        rule.append(self.host_list)
        if self.item_list is not None:
            rule.append(self.item_list)

        ro = self._rule_options_to_config()

        if ro:
            rule.append(ro)

        return tuple(rule)

    # Append rule options, but only if they are not trivial. That way we
    # keep as close as possible to the original Check_MK in rules.mk so that
    # command line users will feel at home...
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
            if self.matches_host_and_item(host.folder(), host_name, NO_ITEM):
                return False
        return True

    def matches_host_and_item(self, host_folder, hostname, item):
        """Whether or not the given folder/host/item matches this rule"""
        return not any(True for _r in self.get_mismatch_reasons(host_folder, hostname, item))

    def get_mismatch_reasons(self, host_folder, hostname, item):
        """A generator that provides the reasons why a given folder/host/item not matches this rule"""
        host = host_folder.host(hostname)

        if not self._matches_hostname(hostname):
            yield _("The host name does not match.")

        host_tags = host.tags()
        for tag in self.tag_specs:
            if tag[0] != '/' and tag[0] != '!' and tag not in host_tags:
                yield _("The host is missing the tag %s") % tag
            elif tag[0] == '!' and tag[1:] in host_tags:
                yield _("The host has the tag %s") % tag

        if not self.folder.is_transitive_parent_of(host_folder):
            yield _("The rule does not apply to the folder of the host.")

        if item != NO_ITEM and self.ruleset.item_type():
            if not self.matches_item(item):
                yield _("The %s \"%s\" does not match this rule.") % \
                                      (self.ruleset.item_name(), item)

    def _matches_hostname(self, hostname):
        if not self.host_list:
            return False  # empty list of explicit host does never match

        # Assume WATO conforming rule where either *all* or *none* of the
        # host expressions are negated.
        negate = self.host_list[0].startswith("!")

        for check_host in self.host_list:
            if check_host == "@all":
                return True

            if check_host[0] == '!':  # strip negate character
                check_host = check_host[1:]

            if check_host[0] == '~':
                check_host = check_host[1:]
                regex_match = True
            else:
                regex_match = False

            if not regex_match and hostname == check_host:
                return not negate

            elif regex_match and cmk.utils.regex.regex(check_host).match(hostname):
                return not negate

        return negate

    def matches_item(self, item):
        for item_spec in self.item_list:
            do_negate = False
            compare_item = item_spec
            if compare_item and compare_item[0] == ENTRY_NEGATE_CHAR:
                compare_item = compare_item[1:]
                do_negate = True
            if re.match(compare_item, "%s" % item):
                return not do_negate
        return False

    def matches_search(self, search_options):
        if "rule_folder" in search_options and self.folder.name() not in self._get_search_folders(
                search_options):
            return False

        if "rule_disabled" in search_options and search_options[
                "rule_disabled"] != self.is_disabled():
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
                    _("Failed to search rule of ruleset '%s' in folder '%s' (%s): %s") %
                    (self.ruleset.title(), self.folder.title(), self.to_config(), e))

        if value_text is not None and not _match_search_expression(search_options, "rule_value",
                                                                   value_text):
            return False

        if not _match_one_of_search_expression(search_options, "rule_host_list", self.host_list):
            return False

        if self.item_list and not _match_one_of_search_expression(search_options, "rule_item_list",
                                                                  self.item_list):
            return False

        to_search = [
            self.comment(),
            self.description(),
        ] + self.host_list \
          + (self.item_list or [])

        if value_text is not None:
            to_search.append(value_text)

        if not _match_one_of_search_expression(search_options, "fulltext", to_search):
            return False

        searching_host_tags = search_options.get("rule_hosttags")
        if searching_host_tags:
            for host_tag in searching_host_tags:
                if host_tag not in self.tag_specs:
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

    def is_discovery_rule_of(self, host):
        return self.host_list == [host.name()] \
               and self.tag_specs == [] \
               and all([ i.endswith("$") for i in self.item_list ]) \
               and self.folder.is_transitive_parent_of(host.folder())


def _match_search_expression(search_options, attr_name, search_in):
    if attr_name not in search_options:
        return True  # not searched for this. Matching!

    return search_in and re.search(search_options[attr_name], search_in, re.I) is not None


def _match_one_of_search_expression(search_options, attr_name, search_in_list):
    for search_in in search_in_list:
        if _match_search_expression(search_options, attr_name, search_in):
            return True
    return False
