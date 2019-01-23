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
from typing import Text  # pylint: disable=unused-import
import six

import cmk.utils.plugin_registry

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
    def plugin_base_class(self):
        return RulespecBaseGroup

    def plugin_name(self, plugin_class):
        return plugin_class().name


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


class Rulespecs(object):
    def __init__(self):
        super(Rulespecs, self).__init__()
        self._rulespecs = {}
        self._by_group = {}  # for conveniant lookup
        self._sorted_groups = []  # for keeping original order

    def clear(self):
        self._rulespecs.clear()
        self._by_group.clear()
        del self._sorted_groups[:]

    def register(self, rulespec):
        group = rulespec.group_name
        name = rulespec.name

        if group not in self._by_group:
            self._sorted_groups.append(group)
            self._by_group[group] = [rulespec]

        else:
            for nr, this_rulespec in enumerate(self._by_group[group]):
                if this_rulespec.name == name:
                    del self._by_group[group][nr]
                    break  # There cannot be two duplicates!

            self._by_group[group].append(rulespec)

        self._rulespecs[name] = rulespec

    def get(self, name):
        return self._rulespecs[name]

    def exists(self, name):
        return name in self._rulespecs

    def get_rulespecs(self):
        return self._rulespecs

    def get_by_group(self, group_name):
        return self._by_group[group_name]

    # Returns all available ruleset groups to be used in dropdown choices
    # TODO: Move the group logic to RulespecGroup / RulespecSubGroup classes
    def get_group_choices(self, mode):
        choices = []

        for main_group_name in self.get_main_groups():
            main_group = get_rulegroup(main_group_name)

            if mode == "static_checks" and main_group_name != "static":
                continue
            elif mode != "static_checks" and main_group_name == "static":
                continue

            choices.append((main_group_name, main_group.title))

            for group_name in self._by_group:
                if group_name.startswith(main_group_name + "/"):
                    sub_group = get_rulegroup(group_name)
                    choices.append((group_name, sub_group.choice_title))

        return choices

    # Now we collect all rulesets that apply to hosts, except those specifying
    # new active or static checks
    # TODO: Move the group logic to RulespecGroup / RulespecSubGroup classes
    def get_all_groups(self):
        seen = set()
        return [gn for gn in self._sorted_groups if not (gn in seen or seen.add(gn))]

    # Group names are separated with "/" into main group and optional subgroup.
    # Do not lose carefully manually crafted order of groups!
    # TODO: Move the group logic to RulespecGroup / RulespecSubGroup classes
    def get_main_groups(self):
        seen = set()
        group_names = []

        for group_name in self._sorted_groups:
            main_group = cmk.utils.make_utf8(group_name.split('/')[0])
            if main_group not in seen:
                group_names.append(main_group)
                seen.add(main_group)

        return group_names

    # Now we collect all rulesets that apply to hosts, except those specifying
    # new active or static checks
    # TODO: Move the group logic to RulespecGroup / RulespecSubGroup classes
    def get_host_groups(self):
        seen = set()
        return [
            gn for gn in self._sorted_groups
            if not gn.startswith("static/") and not gn.startswith("checkparams/") and
            gn != "activechecks" and not (gn in seen or seen.add(gn))
        ]

    # Get the exactly matching main groups and all matching sub group names
    # TODO: Move the group logic to RulespecGroup / RulespecSubGroup classes
    def get_matching_groups(self, group_name):
        seen = set()
        return [
            gn for gn in self._sorted_groups
            if (gn == group_name or (group_name and gn.startswith(group_name + "/"))) and
            not (gn in seen or seen.add(gn))
        ]


class Rulespec(object):
    # needed for unique ID
    NO_FACTORY_DEFAULT = []  # type: list
    # means this ruleset is not used if no rule is entered
    FACTORY_DEFAULT_UNUSED = []  # type: list

    def __init__(self, name, group_name, valuespec, item_spec, item_type, item_name, item_help,
                 item_enum, match_type, title, help_txt, is_optional, factory_default,
                 is_deprecated):
        super(Rulespec, self).__init__()

        self.name = name
        self.group_name = group_name
        self.main_group_name = group_name.split("/")[0]
        self.sub_group_name = group_name.split("/")[1] if "/" in group_name else ""
        self.valuespec = valuespec
        self.item_spec = item_spec  # original item spec, e.g. if validation is needed
        self.item_type = item_type  # None, "service", "checktype" or "checkitem"

        if not item_name and item_type == "service":
            self.item_name = _("Service")
        else:
            self.item_name = item_name  # e.g. "mount point"

        self.item_help = item_help  # a description of the item, only rarely used
        self.item_enum = item_enum  # possible fixed values for items
        self.match_type = match_type  # used by WATO rule analyzer (green and grey balls)
        self.title = title or valuespec.title()
        self.help = help_txt or valuespec.help()
        self.factory_default = factory_default
        self.is_optional = is_optional  # rule may be None (like only_hosts)
        self.is_deprecated = is_deprecated


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

    # Added during 1.6 development for easier transition. Is not needed for
    # pre 1.6 compatibility
    if not isinstance(group, six.string_types) and issubclass(group, RulespecBaseGroup):
        group = group().name

    rulespec = Rulespec(
        name=varname,
        group_name=group,
        valuespec=valuespec,
        item_spec=itemspec,
        item_type=itemtype,
        item_name=itemname,
        item_help=itemhelp,
        item_enum=itemenum,
        match_type=match,
        title=title,
        help_txt=help,
        is_optional=optional,
        factory_default=factory_default,
        is_deprecated=deprecated,
    )

    g_rulespecs.register(rulespec)


g_rulespecs = Rulespecs()
