#!/usr/bin/env python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2019             mk@mathias-kettner.de |
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

from cmk.utils.exceptions import MKGeneralException

# Conveniance macros for legacy tuple based host and service rules
PHYSICAL_HOSTS = ['@physical']  # all hosts but not clusters
CLUSTER_HOSTS = ['@cluster']  # all cluster hosts
ALL_HOSTS = ['@all']  # physical and cluster hosts
ALL_SERVICES = [""]  # optical replacement"
NEGATE = '@negate'  # negation in boolean lists

# TODO: We could make some more optimizations to host/item list matching:
# - Is it worth to detect matches that are no regex matches?
# - We could remove .* from end of regexes
# - What's about compilation of the regexes?


class RulesetToDictTransformer(object):
    """Transforms all rules in the given ruleset from the pre 1.6 tuple format to the dict format
    This is done in place to keep the references to the ruleset working.
    """

    def __init__(self, tag_to_group_map):
        super(RulesetToDictTransformer, self).__init__()
        self._tag_groups = tag_to_group_map

    def transform_in_place(self, ruleset, is_service, is_binary):
        for index, rule in enumerate(ruleset):
            if not isinstance(rule, dict):
                ruleset[index] = self._transform_rule(rule, is_service, is_binary)

    def _transform_rule(self, tuple_rule, is_service, is_binary):
        rule = {
            "condition": {},
        }

        tuple_rule = list(tuple_rule)

        # Extract optional rule_options from the end of the tuple
        if isinstance(tuple_rule[-1], dict):
            rule["options"] = tuple_rule.pop()

        # Extract value from front, if rule has a value
        if not is_binary:
            value = tuple_rule.pop(0)
        else:
            value = True
            if tuple_rule[0] == NEGATE:
                value = False
                tuple_rule = tuple_rule[1:]
        rule["value"] = value

        # Extract list of items from back, if rule has items
        service_condition = {}
        if is_service:
            service_condition = self._transform_item_list(tuple_rule.pop())

        # Rest is host list or tag list + host list
        host_condition = self._transform_host_conditions(tuple_rule)

        if "$or" in service_condition and "$or" in host_condition:
            rule["condition"] = {
                "$and": [
                    {
                        "$or": host_condition.pop("$or")
                    },
                    {
                        "$or": service_condition.pop("$or")
                    },
                ]
            }
        elif "$nor" in service_condition and "$nor" in host_condition:
            rule["condition"] = {
                "$and": [
                    {
                        "$nor": host_condition.pop("$nor")
                    },
                    {
                        "$nor": service_condition.pop("$nor")
                    },
                ]
            }

        rule["condition"].update(service_condition)
        rule["condition"].update(host_condition)

        return rule

    def _transform_item_list(self, item_list):
        if item_list == ALL_SERVICES:
            return {}

        if not item_list:
            return {"service_description": {"$in": []}}

        sub_conditions = []

        # Assume WATO conforming rule where either *all* or *none* of the
        # host expressions are negated.
        # TODO: This is WATO specific. Should we handle this like base did before?
        negate = item_list[0].startswith("!")

        # Remove ALL_SERVICES from end of negated lists
        if negate and item_list[-1] == ALL_SERVICES[0]:
            item_list = item_list[:-1]

        # Construct list of all item conditions
        for check_item in item_list:
            if check_item[0] == '!':  # strip negate character
                check_item = check_item[1:]
            check_item = "^" + check_item
            sub_conditions.append({"service_description": {"$regex": check_item}})

        return self._build_sub_condition("service_description", negate, "$regex", check_item,
                                         sub_conditions)

    def _transform_host_conditions(self, tuple_rule):
        if len(tuple_rule) == 1:
            host_tags = []
            host_list = tuple_rule[0]
        else:
            host_tags = tuple_rule[0]
            host_list = tuple_rule[1]

        condition = {}
        condition.update(self._transform_host_tags(host_tags))
        condition.update(self._transform_host_list(host_list))
        return condition

    def _transform_host_list(self, host_list):
        if host_list == ALL_HOSTS:
            return {}

        if not host_list:
            return {"host_name": {"$in": []}}

        sub_conditions = []

        # Assume WATO conforming rule where either *all* or *none* of the
        # host expressions are negated.
        # TODO: This is WATO specific. Should we handle this like base did before?
        negate = host_list[0].startswith("!")

        # Remove ALL_HOSTS from end of negated lists
        if negate and host_list[-1] == ALL_HOSTS[0]:
            host_list = host_list[:-1]

        num_conditions = len(host_list)
        has_regex = self._host_list_has_regex(host_list)

        # Simplify case where we only have full host name matches
        if not has_regex and num_conditions > 1:
            list_op = "$nin" if negate else "$in"
            return {"host_name": {list_op: [h.lstrip("!") for h in host_list]}}

        # Construct list of all host item conditions
        for check_item in host_list:
            if check_item[0] == '!':  # strip negate character
                check_item = check_item[1:]

            if check_item[0] == '~':
                check_item = "^" + check_item[1:]
                regex_match = True
            else:
                regex_match = False

            if check_item == CLUSTER_HOSTS[0]:
                raise MKGeneralException(
                    "Found a ruleset using CLUSTER_HOSTS as host condition. "
                    "This is not supported anymore. These rules can not be transformed "
                    "automatically to the new format. Please check out your configuration and "
                    "replace the rules in question.")
            if check_item == PHYSICAL_HOSTS[0]:
                raise MKGeneralException(
                    "Found a ruleset using PHYSICAL_HOSTS as host condition. "
                    "This is not supported anymore. These rules can not be transformed "
                    "automatically to the new format. Please check out your configuration and "
                    "replace the rules in question.")

            sub_op = "$regex" if regex_match else "$eq"

            sub_conditions.append({"host_name": {sub_op: check_item}})

        return self._build_sub_condition("host_name", negate, sub_op, check_item, sub_conditions)

    def _host_list_has_regex(self, host_list):
        for check_item in host_list:
            if check_item[0] == '!':  # strip negate character
                check_item = check_item[1:]

            if check_item[0] == '~':
                return True
        return False

    def _build_sub_condition(self, field, negate, sub_op, check_item, sub_conditions):
        """This function simplifies the constructed conditions

        - The or/nor condition is skipped where we only have a single condition
        - "$eq" is skipped where we only have a simple field equality match
        """
        if len(sub_conditions) == 1:
            if sub_op == "$eq":
                return {field: {"$ne": check_item} if negate else check_item}
            if sub_op == "$regex":
                if negate:
                    return {field: {"$not": {"$regex": check_item}}}
                return sub_conditions[0]
            raise NotImplementedError()

        op = "$nor" if negate else "$or"
        return {op: sub_conditions}

    def _transform_host_tags(self, host_tags):
        if not host_tags:
            return {}

        conditions = {}
        for tag_id in host_tags:
            # Folder is either not present (main folder) or in this format
            # "/abc/+" which matches on folder "abc" and all subfolders.
            if tag_id.startswith("/"):
                conditions["host_folder"] = {"$regex": "^%s" % tag_id.rstrip("+")}
                continue

            negate = False
            if tag_id[0] == '!':
                tag_id = tag_id[1:]
                negate = True

            # Assume it's an aux tag in case there is a tag configured without known group
            tag_group_id = self._tag_groups.get(tag_id, tag_id)

            conditions["host_tags." + tag_group_id] = {"$ne": tag_id} if negate else tag_id

        return conditions


def get_tag_to_group_map(tag_config):
    """The old rules only have a list of tags and don't know anything about the
    tag groups they are coming from. Create a map based on the current tag config
    """
    tag_id_to_tag_group_id_map = {}

    for aux_tag in tag_config.aux_tag_list.get_tags():
        tag_id_to_tag_group_id_map[aux_tag.id] = aux_tag.id

    for tag_group in tag_config.tag_groups:
        for grouped_tag in tag_group.tags:
            tag_id_to_tag_group_id_map[grouped_tag.id] = tag_group.id
    return tag_id_to_tag_group_id_map
