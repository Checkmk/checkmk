#!/usr/bin/env python2
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2016             mk@mathias-kettner.de |
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
"""This module provides generic Check_MK ruleset processing functionality"""

# TODO: Reduce different ruleset types (item vs. non-item and binary vs. value)
# TODO: Use objects for object_spec. We already have
# cmk_base.config.HostConfig. We would need something similar for service
# objects

from typing import Text, List, Dict, Any, Optional  # pylint: disable=unused-import

from cmk.utils.rulesets.rule_matcher import RuleMatcher


class RulesetMatchObject(object):
    """Wrapper around dict to ensure the ruleset match objects are correctly created"""
    __slots__ = ["host_name", "host_tags", "service_description"]

    def __init__(self, host_name=None, host_tags=None, service_description=None):
        # type: (Optional[str], Optional[Dict[Text, Text]], Optional[Text]) -> None
        super(RulesetMatchObject, self).__init__()
        self.host_name = host_name
        self.host_tags = host_tags
        self.service_description = service_description

    def to_dict(self):
        # type: () -> Dict
        # TODO: Two getattr()?
        return {k: getattr(self, k) for k in self.__slots__ if getattr(self, k) is not None}

    def copy(self):
        return RulesetMatchObject(**self.to_dict())

    def __repr__(self):
        kwargs = ", ".join(["%s=%r" % e for e in self.to_dict().iteritems()])
        return "RulesetMatchObject(%s)" % kwargs


class RulesetMatcher(object):
    def __init__(self):
        # type: () -> None
        super(RulesetMatcher, self).__init__()
        self._matcher = RuleMatcher()

    def is_matching(self, match_object, ruleset):
        # type: (RulesetMatchObject, List[Dict]) -> bool
        """Compute outcome of a ruleset set that just says yes/no

        The binary match only cares about the first matching rule of an object.
        Depending on the value the outcome is negated or not.

        Replaces in_binary_hostlist / in_boolean_serviceconf_list"""
        for rule in ruleset:
            if rule.get("options", {}).get("disabled", False):
                continue

            if self._matcher.match(match_object.to_dict(), rule["condition"]):
                return rule["value"]
        return False

    def get_merged_dict(self, match_object, ruleset):
        # type: (RulesetMatchObject, List[Dict]) -> Dict
        """Returns a dictionary of the merged dict values of the matched rules
        The first dict setting a key defines the final value.

        Replaces host_extra_conf_merged / service_extra_conf_merged"""
        rule_dict = {}  # type: Dict
        for value_dict in self.get_values(match_object, ruleset):
            for key, value in value_dict.items():
                rule_dict.setdefault(key, value)
        return rule_dict

    def get_values(self, match_object, ruleset):
        # type: (RulesetMatchObject, List) -> List[Any]
        """Returns a list of the values of the matched rules

        Replaces host_extra_conf / service_extra_conf"""
        return [r["value"] for r in self.get_matching_rules(match_object, ruleset)]

    def get_matching_rules(self, match_object, ruleset):
        # type: (RulesetMatchObject, List) -> List[Dict]
        """Filter the ruleset of this matcher for the given object and return the filtered rule list
        """
        return [
            rule for rule in ruleset if not rule.get("options", {}).get("disabled", False) and
            self._matcher.match(match_object.to_dict(), rule["condition"])
        ]
