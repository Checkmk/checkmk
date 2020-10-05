#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2020 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import List, Dict, Type, Any

from marshmallow import Schema, validate  # type: ignore[import]
from marshmallow_oneofschema import OneOfSchema  # type: ignore[import]

from cmk.utils.bi.bi_lib import (
    MacroMappings,
    replace_macros,
    bi_search_registry,
    ABCBISearch,
    Nested,
    String,
    ReqConstant,
    ReqDict,
    ReqList,
    ReqString,
    ReqNested,
)
from cmk.utils.bi.bi_searcher import bi_searcher, BIHostSearchMatch, BIServiceSearchMatch


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

    def __init__(self, search_config: Dict[str, Any]):
        super().__init__(search_config)

    def execute(self, macros: MacroMappings) -> List[Dict]:
        return [{}]


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

    def __init__(self, search_config: Dict[str, Any]):
        super().__init__(search_config)
        self.conditions = search_config["conditions"]
        self.refer_to = search_config["refer_to"]

    def execute(self, macros: MacroMappings) -> List[Dict]:
        new_conditions = replace_macros(self.conditions, macros)
        search_matches: List[BIHostSearchMatch] = bi_searcher.search_hosts(new_conditions)

        if self.refer_to == "host":
            return self._refer_to_host_results(search_matches)
        if self.refer_to == "child":
            return self._refer_to_children_results(search_matches)
        if self.refer_to == "parent":
            return self._refer_to_parent_results(search_matches)
        # TODO: child with, will be done in later commit

        raise NotImplementedError("Invalid refer to type %r" % self.refer_to)

    def _refer_to_host_results(self, search_matches: List[BIHostSearchMatch]) -> List[Dict]:
        search_results = []
        for search_match in search_matches:
            search_result = {
                "$HOSTNAME$": search_match.host.name,
                "$HOSTALIAS$": search_match.host.alias
            }
            for idx, group in enumerate(search_match.match_groups):
                search_result["$HOST_MG_%d$" % idx] = group
            search_results.append(search_result)
        return search_results

    def _refer_to_children_results(self, search_matches: List[BIHostSearchMatch]) -> List[Dict]:
        search_results = []
        handled_children = set()
        for search_match in search_matches:
            for child in search_match.host.children:
                if child in handled_children:
                    continue
                handled_children.add(child)
                search_result = {
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
                    "$HOSTNAME$": search_match.host.name,
                    "$HOSTALIAS$": search_match.host.alias
                }
                search_result["$2$"] = parent
                search_results.append(search_result)

        return search_results


class BIHostSearchSchema(Schema):
    type = ReqConstant(BIHostSearch.type())
    conditions = ReqNested(HostConditionsSchema, default=HostConditionsSchema().dump({}).data)
    refer_to = ReqString(validate=validate.OneOf(["host", "child", "parent"]), default="host")


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

    def __init__(self, search_config: Dict[str, Any]):
        super().__init__(search_config)
        self.conditions = search_config["conditions"]

    def execute(self, macros: MacroMappings) -> List[Dict]:
        new_conditions = replace_macros(self.conditions, macros)
        search_matches: List[BIServiceSearchMatch] = bi_searcher.search_services(new_conditions)
        search_results = []
        for search_match in sorted(search_matches, key=lambda x: x.service_description):
            search_result = {
                "$HOSTNAME$": search_match.host.name,
                "$HOSTALIAS$": search_match.host.alias
            }
            for idx, group in enumerate(search_match.match_groups):
                search_result["$%d$" % (idx + 2)] = group
            search_results.append(search_result)
        return search_results


class BIServiceSearchSchema(Schema):
    type = ReqConstant(BIServiceSearch.type())
    conditions = ReqNested(ServiceConditionsSchema, default=ServiceConditionsSchema().dump({}).data)


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

    @classmethod
    def schema(cls) -> Type["BIFixedArgumentsSearchSchema"]:
        return BIFixedArgumentsSearchSchema

    def __init__(self, search_config: Dict[str, Any]):
        super().__init__(search_config)
        self.arguments = search_config["arguments"]

    def execute(self, macros: MacroMappings) -> List[Dict]:
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
    values = ReqList(String)


class BIFixedArgumentsSearchSchema(Schema):
    type = ReqConstant(BIFixedArgumentsSearch.type())
    arguments = ReqList(Nested(BIFixedArgumentsSearchTokenSchema))


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

    def get_obj_type(self, obj: ABCBISearch) -> str:
        return obj.type()
