#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2020 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import List, Dict, Type, Any, Union, Set

from marshmallow import fields, pre_load, post_dump
from marshmallow_oneofschema import OneOfSchema  # type: ignore[import]

from cmk.utils.macros import MacroMapping
from cmk.utils.bi.bi_schema import Schema
from cmk.utils.type_defs import HostName
from cmk.utils.bi.bi_lib import (
    replace_macros,
    bi_search_registry,
    ABCBISearch,
    ReqConstant,
    ReqDict,
    ReqList,
    ReqString,
    ReqNested,
    ABCBISearcher,
    BIHostData,
    BIHostSearchMatch,
    BIServiceSearchMatch,
)


class BIAllHostsChoiceSchema(Schema):
    type = ReqConstant("all_hosts")


class BIHostNameRegexChoiceSchema(Schema):
    type = ReqConstant("host_name_regex")
    pattern = ReqString(default="", example="testhostn.*")


class BIHostAliasRegexChoiceSchema(Schema):
    type = ReqConstant("host_alias_regex")
    pattern = ReqString(default="", example="testali.*")


class BIHostChoice(OneOfSchema):
    type_field = "type"
    type_field_remove = False
    type_schemas = {
        "all_hosts": BIAllHostsChoiceSchema,
        "host_name_regex": BIHostNameRegexChoiceSchema,
        "host_alias_regex": BIHostAliasRegexChoiceSchema,
    }

    def get_obj_type(self, obj) -> str:
        return obj["type"]


class HostConditionsSchema(Schema):
    host_folder = ReqString(default="", example="servers/groupA")
    host_labels = ReqDict(default={}, example={"db": "mssql"})
    host_tags = ReqDict(default={}, example={})
    host_choice = ReqNested(BIHostChoice,
                            default={"type": "all_hosts"},
                            example={"type": "all_hosts"})


class ServiceConditionsSchema(HostConditionsSchema):
    service_regex = ReqString(default="", example="Filesystem.*")
    service_labels = ReqDict(default={}, example={"db": "mssql"})


#   .--Empty---------------------------------------------------------------.
#   |                   _____                 _                            |
#   |                  | ____|_ __ ___  _ __ | |_ _   _                    |
#   |                  |  _| | '_ ` _ \| '_ \| __| | | |                   |
#   |                  | |___| | | | | | |_) | |_| |_| |                   |
#   |                  |_____|_| |_| |_| .__/ \__|\__, |                   |
#   |                                  |_|        |___/                    |
#   +----------------------------------------------------------------------+


@bi_search_registry.register
class BIEmptySearch(ABCBISearch):
    @classmethod
    def type(cls) -> str:
        return "empty"

    @classmethod
    def schema(cls) -> Type["BIEmptySearchSchema"]:
        return BIEmptySearchSchema

    def execute(self, macros: MacroMapping, bi_searcher: ABCBISearcher) -> List[Dict]:
        return [{}]

    def serialize(self):
        return {
            "type": self.type(),
        }


class BIEmptySearchSchema(Schema):
    type = ReqConstant(BIEmptySearch.type())


#   .--Host----------------------------------------------------------------.
#   |                         _   _           _                            |
#   |                        | | | | ___  ___| |_                          |
#   |                        | |_| |/ _ \/ __| __|                         |
#   |                        |  _  | (_) \__ \ |_                          |
#   |                        |_| |_|\___/|___/\__|                         |
#   |                                                                      |
#   +----------------------------------------------------------------------+


@bi_search_registry.register
class BIHostSearch(ABCBISearch):
    @classmethod
    def type(cls) -> str:
        return "host_search"

    @classmethod
    def schema(cls) -> Type["BIHostSearchSchema"]:
        return BIHostSearchSchema

    def serialize(self):
        return {
            "type": self.type(),
            "conditions": self.conditions,
            "refer_to": self.refer_to,
        }

    def __init__(self, search_config: Dict[str, Any]):
        super().__init__(search_config)
        self.conditions = search_config["conditions"]
        self.refer_to = search_config["refer_to"]

    def execute(self, macros: MacroMapping, bi_searcher: ABCBISearcher) -> List[Dict]:
        new_conditions = replace_macros(self.conditions, macros)
        search_matches: List[BIHostSearchMatch] = bi_searcher.search_hosts(new_conditions)

        if isinstance(self.refer_to, str):
            # TODO: remove with version 2.3: unconverted legacy refer_to field
            referred_type = self.refer_to
        else:
            referred_type = self.refer_to["type"]
        if referred_type == "host":
            return self._refer_to_host_results(search_matches)
        if referred_type == "child":
            return self._refer_to_children_results(search_matches, bi_searcher)
        if referred_type == "parent":
            return self._refer_to_parent_results(search_matches)
        if referred_type == "child_with":
            return self._refer_to_children_with_results(search_matches, bi_searcher, self.refer_to)

        raise NotImplementedError("Invalid refer to type %r" % (self.refer_to,))

    def _refer_to_host_results(self, search_matches: List[BIHostSearchMatch]) -> List[Dict]:
        search_results = []
        for search_match in search_matches:
            search_result = {
                "$1$": search_match.match_groups[0] if search_match.match_groups else "",
                "$HOSTNAME$": search_match.host.name,
                "$HOSTALIAS$": search_match.host.alias
            }
            for idx, group in enumerate(search_match.match_groups):
                search_result["$HOST_MG_%d$" % idx] = group
            search_results.append(search_result)
        return search_results

    def _refer_to_children_results(self, search_matches: List[BIHostSearchMatch],
                                   bi_searcher: ABCBISearcher) -> List[Dict]:
        search_results = []
        handled_children = set()
        for search_match in search_matches:
            for child in search_match.host.children:
                if child in handled_children:
                    continue
                handled_children.add(child)
                search_result = {
                    "$1$": search_match.match_groups[0] if search_match.match_groups else "",
                    "$HOSTNAME$": bi_searcher.hosts[child].name,
                    "$HOSTALIAS$": bi_searcher.hosts[child].alias
                }
                search_results.append(search_result)
        return search_results

    def _refer_to_parent_results(self, search_matches: List[BIHostSearchMatch]) -> List[Dict]:
        search_results = []
        handled_parents = set()
        for search_match in search_matches:
            for parent in search_match.host.parents:
                if parent in handled_parents:
                    continue
                handled_parents.add(parent)
                search_result = {
                    "$1$": search_match.match_groups[0] if search_match.match_groups else "",
                    "$HOSTNAME$": search_match.host.name,
                    "$HOSTALIAS$": search_match.host.alias
                }
                search_result["$2$"] = parent
                search_results.append(search_result)

        return search_results

    def _refer_to_children_with_results(self, search_matches: List[BIHostSearchMatch],
                                        bi_searcher: ABCBISearcher, refer_to: dict) -> List[Dict]:
        all_children: Set[HostName] = set()

        # Determine pool of children
        for search_match in search_matches:
            all_children.update(search_match.host.children)

        # Filter children known to bi_searcher
        children_host_data: List[BIHostData] = [
            bi_searcher.hosts[x] for x in all_children if x in bi_searcher.hosts
        ]

        conditions = refer_to["conditions"]
        hosts, _matched_re_groups = bi_searcher.filter_host_choice(children_host_data,
                                                                   conditions["host_choice"])
        matched_hosts = bi_searcher.filter_host_folder(hosts, conditions["host_folder"])
        matched_hosts = bi_searcher.filter_host_tags(matched_hosts, conditions["host_tags"])
        matched_hosts = bi_searcher.filter_host_labels(matched_hosts, conditions["host_labels"])

        search_results = []
        for host in matched_hosts:
            # Note: The parameter $1$ does not reflect the first regex match group for the initial host
            #       This information was lost when all children were put into the all_children pool
            #       We can live with it. The option is not used sensibly anywhere anyway :)
            search_result = {"$1$": host.name, "$HOSTNAME$": host.name, "$HOSTALIAS$": host.alias}
            search_results.append(search_result)
        return search_results


class HostSchema(Schema):
    type = ReqConstant("host")


class ParentSchema(Schema):
    type = ReqConstant("parent")


class ChildSchema(Schema):
    type = ReqConstant("child")


class ChildWithSchema(Schema):
    conditions = ReqNested(HostConditionsSchema, default=HostConditionsSchema().dump({}))
    host_choice = ReqNested(BIHostChoice,
                            default={"type": "all_hosts"},
                            example={"type": "all_hosts"})


class ReferToSchema(OneOfSchema):
    type_field = "type"
    type_field_remove = False
    type_schemas = {
        "host": HostSchema,
        "parent": ParentSchema,
        "child": ChildSchema,
        "child_with": ChildWithSchema,
    }

    def get_obj_type(self, obj) -> str:
        if isinstance(obj, str):
            return obj
        return obj["type"]


class BIHostSearchSchema(Schema):
    type = ReqConstant(BIHostSearch.type())
    conditions = ReqNested(HostConditionsSchema, default=HostConditionsSchema().dump({}))
    refer_to = ReqNested(ReferToSchema, default={"type": "host"})

    @pre_load
    def pre_load(self, data, **kwargs):
        if isinstance(data["refer_to"], str):
            # Fixes legacy schema config: {"refer_to": "host"}
            data["refer_to"] = {"type": data["refer_to"]}
        return data

    @post_dump
    def post_dump(self, data, **kwargs):
        if isinstance(data, str):
            # Fixes legacy schema config: {"refer_to": "host"}
            return {"type": data}
        return data


#   .--Service-------------------------------------------------------------.
#   |                  ____                  _                             |
#   |                 / ___|  ___ _ ____   _(_) ___ ___                    |
#   |                 \___ \ / _ \ '__\ \ / / |/ __/ _ \                   |
#   |                  ___) |  __/ |   \ V /| | (_|  __/                   |
#   |                 |____/ \___|_|    \_/ |_|\___\___|                   |
#   |                                                                      |
#   +----------------------------------------------------------------------+


@bi_search_registry.register
class BIServiceSearch(ABCBISearch):
    @classmethod
    def type(cls) -> str:
        return "service_search"

    @classmethod
    def schema(cls) -> Type["BIServiceSearchSchema"]:
        return BIServiceSearchSchema

    def serialize(self):
        return {
            "type": self.type(),
            "conditions": self.conditions,
        }

    def __init__(self, search_config: Dict[str, Any]):
        super().__init__(search_config)
        self.conditions = search_config["conditions"]

    def execute(self, macros: MacroMapping, bi_searcher: ABCBISearcher) -> List[Dict]:
        new_conditions = replace_macros(self.conditions, macros)
        search_matches: List[BIServiceSearchMatch] = bi_searcher.search_services(new_conditions)
        search_results = []
        for search_match in sorted(search_matches, key=lambda x: x.service_description):
            search_result = {
                "$1$": next(iter(search_match.host_match.match_groups), ""),
                "$HOSTNAME$": search_match.host_match.host.name,
                "$HOSTALIAS$": search_match.host_match.host.alias
            }
            for idx, group in enumerate(search_match.match_groups, start=2):
                search_result["$%d$" % (idx)] = group

            for idx, group in enumerate(search_match.host_match.match_groups):
                search_result["$HOST_MG_%d$" % idx] = group
            search_results.append(search_result)
        return search_results


class BIServiceSearchSchema(Schema):
    type = ReqConstant(BIServiceSearch.type())
    conditions = ReqNested(ServiceConditionsSchema, default=ServiceConditionsSchema().dump({}))


#   .--Fixed---------------------------------------------------------------.
#   |                       _____ _              _                         |
#   |                      |  ___(_)_  _____  __| |                        |
#   |                      | |_  | \ \/ / _ \/ _` |                        |
#   |                      |  _| | |>  <  __/ (_| |                        |
#   |                      |_|   |_/_/\_\___|\__,_|                        |
#   |                                                                      |
#   +----------------------------------------------------------------------+


@bi_search_registry.register
class BIFixedArgumentsSearch(ABCBISearch):
    @classmethod
    def type(cls) -> str:
        return "fixed_arguments"

    def serialize(self):
        return {
            "type": self.type(),
            "arguments": self.arguments,
        }

    @classmethod
    def schema(cls) -> Type["BIFixedArgumentsSearchSchema"]:
        return BIFixedArgumentsSearchSchema

    def __init__(self, search_config: Dict[str, Any]):
        super().__init__(search_config)
        self.arguments = search_config["arguments"]

    def execute(self, macros: MacroMapping, bi_searcher: ABCBISearcher) -> List[Dict]:
        results: List[Dict] = []
        new_vars = replace_macros(self.arguments, macros)
        for argument in new_vars:
            key = argument["key"]
            for idx, value in enumerate(argument["values"]):
                if len(results) <= idx:
                    results.append({})
                results[idx]["$%s$" % key] = value

        return results


class BIFixedArgumentsSearchTokenSchema(Schema):
    key = ReqString()
    values = ReqList(fields.String)


class BIFixedArgumentsSearchSchema(Schema):
    type = ReqConstant(BIFixedArgumentsSearch.type())
    arguments = ReqList(fields.Nested(BIFixedArgumentsSearchTokenSchema))


#   .--Schemas-------------------------------------------------------------.
#   |              ____       _                                            |
#   |             / ___|  ___| |__   ___ _ __ ___   __ _ ___               |
#   |             \___ \ / __| '_ \ / _ \ '_ ` _ \ / _` / __|              |
#   |              ___) | (__| | | |  __/ | | | | | (_| \__ \              |
#   |             |____/ \___|_| |_|\___|_| |_| |_|\__,_|___/              |
#   |                                                                      |
#   +----------------------------------------------------------------------+


class BISearchSchema(OneOfSchema):
    type_field = "type"
    type_field_remove = False
    type_schemas = dict((k, v.schema()) for k, v in bi_search_registry.items())

    def get_obj_type(self, obj: Union[ABCBISearch, dict]) -> str:
        if isinstance(obj, dict):
            return obj["type"]
        return obj.type()
