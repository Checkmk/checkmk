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
"""The rulespecs are the ruleset specifications registered to WATO."""

import abc
import re
from typing import Text, List, Type, Optional, Any  # pylint: disable=unused-import
import six

import cmk.utils.plugin_registry

from cmk.gui.valuespec import ValueSpec  # pylint: disable=unused-import
from cmk.gui.i18n import _


class RulespecBaseGroup(object):
    """Base class for all rulespec group types"""
    __metaclass__ = abc.ABCMeta

    @abc.abstractproperty
    def name(self):
        # type: () -> Text
        """Unique internal key of this group"""
        raise NotImplementedError()

    @abc.abstractproperty
    def title(self):
        # type: () -> Text
        """Human readable title of this group"""
        raise NotImplementedError()

    @abc.abstractproperty
    def help(self):
        # type: () -> Text
        """Helpful description of this group"""
        raise NotImplementedError()

    @abc.abstractproperty
    def is_sub_group(self):
        # type: () -> bool
        raise NotImplementedError()

    @abc.abstractproperty
    def choice_title(self):
        # type: () -> Text
        raise NotImplementedError()


class RulespecGroup(RulespecBaseGroup):
    @abc.abstractproperty
    def name(self):
        # type: () -> Text
        """Unique internal key of this group"""
        raise NotImplementedError()

    @abc.abstractproperty
    def title(self):
        # type: () -> Text
        """Human readable title of this group"""
        raise NotImplementedError()

    @abc.abstractproperty
    def help(self):
        # type: () -> Text
        """Helpful description of this group"""
        raise NotImplementedError()

    @property
    def is_sub_group(self):
        return False

    @property
    def choice_title(self):
        return self.title


class RulespecSubGroup(RulespecBaseGroup):
    __metaclass__ = abc.ABCMeta

    @abc.abstractproperty
    def main_group(self):
        """A reference to the main group class"""
        raise NotImplementedError()

    @abc.abstractproperty
    def sub_group_name(self):
        """The internal name of the sub group"""
        raise NotImplementedError()

    @property
    def name(self):
        return "/".join([self.main_group().name, self.sub_group_name])

    @property
    def choice_title(self):
        return u"&nbsp;&nbsp;⌙ %s" % self.title

    @property
    def help(self):
        return None  # Sub groups currently have no help text

    @property
    def is_sub_group(self):
        return True


class RulespecGroupRegistry(cmk.utils.plugin_registry.ClassRegistry):
    def __init__(self):
        super(RulespecGroupRegistry, self).__init__()
        self._main_groups = []  # type: List[Type[RulespecGroup]]
        self._sub_groups_by_main_group = {
        }  # type: Dict[Type[RulespecGroup], Type[RulespecSubGroup]]

    def plugin_base_class(self):
        return RulespecBaseGroup

    def plugin_name(self, plugin_class):
        return plugin_class().name

    def registration_hook(self, plugin_class):
        group = plugin_class()
        if not group.is_sub_group:
            self._main_groups.append(plugin_class)
        else:
            self._sub_groups_by_main_group.setdefault(group.main_group, []).append(plugin_class)

    def get_group_choices(self, mode):
        """Returns all available ruleset groups to be used in dropdown choices"""
        choices = []

        main_groups = [g_class() for g_class in self.get_main_groups()]
        for main_group in sorted(main_groups, key=lambda g: g.title):
            if mode == "static_checks" and main_group.name != "static":
                continue
            elif mode != "static_checks" and main_group.name == "static":
                continue

            choices.append((main_group.name, main_group.choice_title))

            sub_groups = [g_class() for g_class in self._get_sub_groups_of(main_group.__class__)]
            for sub_group in sorted(sub_groups, key=lambda g: g.title):
                choices.append((sub_group.name, sub_group.choice_title))

        return choices

    def get_main_groups(self):
        # type: () -> List[Type[RulespecGroup]]
        return self._main_groups

    def _get_sub_groups_of(self, main_group):
        # type: (Type[RulespecGroup]) -> List[Type[RulespecSubGroup]]
        return self._sub_groups_by_main_group.get(main_group, [])

    def get_matching_group_names(self, group_name):
        # type: (str) -> List[str]
        """Get either the main group and all sub groups of a matching main group or the matching sub group"""
        for group_class in self._main_groups:
            if group_class().name == group_name:
                return [group_name
                       ] + [g_class().name for g_class in self._get_sub_groups_of(group_class)]

        return [name for name in self._entries if name == group_name]

    def get_host_rulespec_group_names(self):
        """Collect all rulesets that apply to hosts, except those specifying new active or static checks"""
        names = []
        hidden_groups = ("static", "checkparams", "activechecks")
        hidden_main_groups = ("monconf", "agents", "agent")
        for g_class in self.values():
            group = g_class()
            if group.is_sub_group and group.main_group().name in hidden_groups:
                continue

            if not group.is_sub_group and group.name in hidden_groups or group.name in hidden_main_groups:
                continue

            names.append(group.name)
        return names


rulespec_group_registry = RulespecGroupRegistry()


@rulespec_group_registry.register
class RulespecGroupStaticChecks(RulespecGroup):
    @property
    def name(self):
        return "static"

    @property
    def title(self):
        return _("Manual Checks")

    @property
    def help(self):
        return _("Statically configured Check_MK checks that do not rely on the inventory")


# TODO: Kept for compatibility with pre 1.6 plugins
def register_rulegroup(group_name, title, help_text):
    rulespec_group_registry.register(_get_legacy_rulespec_group_class(group_name, title, help_text))


def get_rulegroup(group_name):
    try:
        group_class = rulespec_group_registry[group_name]
    except KeyError:
        group_class = _get_legacy_rulespec_group_class(group_name, group_title=None, help_text=None)
        rulespec_group_registry.register(group_class)
    return group_class()


def _get_legacy_rulespec_group_class(group_name, group_title, help_text):
    if "/" in group_name:
        main_group_name, sub_group_name = group_name.split("/", 1)
        sub_group_title = group_title or sub_group_name

        # group_name could contain non alphanumeric characters
        internal_sub_group_name = re.sub('[^a-zA-Z]', '', sub_group_name)

        main_group_class = get_rulegroup(main_group_name).__class__
        return type(
            "LegacyRulespecSubGroup%s" % internal_sub_group_name.title(), (RulespecSubGroup,), {
                "main_group": main_group_class,
                "sub_group_name": internal_sub_group_name.lower(),
                "title": sub_group_title,
            })

    group_title = group_title or group_name

    return type("LegacyRulespecGroup%s" % group_name.title(), (RulespecGroup,), {
        "name": group_name,
        "title": group_title,
        "help": help_text,
    })


class Rulespec(object):
    __metaclass__ = abc.ABCMeta

    # needed for unique ID
    NO_FACTORY_DEFAULT = []  # type: list
    # means this ruleset is not used if no rule is entered
    FACTORY_DEFAULT_UNUSED = []  # type: list

    @abc.abstractproperty
    def name(self):
        # type: () -> str
        raise NotImplementedError()

    @abc.abstractproperty
    def group(self):
        # type: () -> Type[RulespecGroup]
        raise NotImplementedError()

    @property
    def group_name(self):
        # type: () -> Text
        return self.group().name

    @property
    def main_group_name(self):
        # type: () -> Text
        return self.group_name.split("/")[0]

    @property
    def sub_group_name(self):
        # type: () -> Text
        return self.group_name.split("/")[1] if "/" in self.group_name else ""

    @property
    def item_name(self):
        if not self._item_name and self.item_type == "service":
            return _("Service")
        return self._item_name

    @property
    def title(self):
        return self.valuespec.title()

    @property
    def help(self):
        return self.valuespec.help()

    # TODO: Which cases need this this to be optional? clarify this
    @property
    def valuespec(self):
        # type: () -> Optional[ValueSpec]
        return None

    # TODO: Move these item attributes e.g. to a subclass or a helper class
    @property
    def item_spec(self):
        # type: () -> Optional[ValueSpec]
        return None

    @property
    def item_type(self):
        # type: () -> Optional[str]
        return None

    @property
    def _item_name(self):
        # type: () -> Optional[Text]
        return None

    @property
    def item_help(self):
        # type: () -> Optional[Text]
        return None

    @property
    def item_enum(self):
        # type: () -> Optional[Text]
        return None

    @property
    def match_type(self):
        # type: () -> str
        return "first"

    @property
    def factory_default(self):
        # type: () -> Any
        return self.NO_FACTORY_DEFAULT

    @property
    def is_optional(self):
        # type: () -> bool
        return False

    @property
    def is_deprecated(self):
        # type: () -> bool
        return False


# Pre 1.6 rule registering logic. Need to be kept for some time
def register_rule(
        group,
        varname,
        valuespec=None,
        title=None,
        help=None,  # pylint: disable=redefined-builtin
        itemspec=None,
        itemtype=None,
        itemname=None,
        itemhelp=None,
        itemenum=None,
        match="first",
        optional=False,
        deprecated=False,
        **kwargs):
    factory_default = kwargs.get("factory_default", Rulespec.NO_FACTORY_DEFAULT)

    if isinstance(group, six.string_types):
        group = get_rulegroup(group).__class__

    class_attrs = {
        "name": varname,
        "group": group,
        "valuespec": valuespec,
        "item_spec": itemspec,
        "item_type": itemtype,
        "_item_name": itemname,
        "item_help": itemhelp,
        "item_enum": itemenum,
        "match_type": match,
        "factory_default": factory_default,
        "is_optional": optional,
        "is_deprecated": deprecated,
    }

    if title:
        class_attrs["title"] = title

    if help:
        class_attrs["help"] = help

    rulespec_class = type("LegacyRulespec%s" % varname, (Rulespec,), class_attrs)
    rulespec_registry.register(rulespec_class)


class RulespecRegistry(cmk.utils.plugin_registry.ClassRegistry):
    def __init__(self, group_registry):
        super(RulespecRegistry, self).__init__()
        self._group_registry = group_registry

    def plugin_base_class(self):
        return Rulespec

    def plugin_name(self, plugin_class):
        return plugin_class().name

    def get_by_group(self, group_name):
        # type: (str) -> List[Rulespec]
        rulespecs = []

        if group_name not in self._group_registry:
            raise KeyError()

        for rulespec_class in self.values():
            rulespec = rulespec_class()
            if rulespec.group_name == group_name:
                rulespecs.append(rulespec)
        return rulespecs

    def get_all_groups(self):
        """Returns a list of all rulespec groups that have rules registered for

        Can not use direct rulespec_group_registry access for this, because the
        group registry does not know whether a group is registered for it"""
        return list(set(gc().group_name for gc in self.values()))


rulespec_registry = RulespecRegistry(rulespec_group_registry)
