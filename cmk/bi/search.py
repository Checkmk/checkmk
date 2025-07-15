#!/usr/bin/env python3
# Copyright (C) 2020 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from marshmallow import post_dump, post_load, pre_dump, pre_load
from marshmallow_oneofschema import OneOfSchema

from cmk.ccc.hostaddress import HostName

from cmk.utils.labels import AndOrNotLiteral, LabelGroup
from cmk.utils.macros import MacroMapping

from cmk import fields
from cmk.bi.lib import (
    ABCBISearch,
    ABCBISearcher,
    bi_search_registry,
    BIHostData,
    BIHostSearchMatch,
    BIServiceSearchMatch,
    replace_macros,
    ReqConstant,
    ReqDict,
    ReqList,
    ReqNested,
    ReqString,
    SearchKind,
)
from cmk.bi.schema import Schema


class BIAllHostsChoiceSchema(Schema):
    type = ReqConstant("all_hosts", description="Select all hosts.")


class BIHostNameRegexChoiceSchema(Schema):
    type = ReqConstant(
        "host_name_regex", description="Select hosts based on a regex against their host name."
    )
    pattern = ReqString(dump_default="", example="testhostn.*", description="Regex pattern.")


class BIHostAliasRegexChoiceSchema(Schema):
    type = ReqConstant(
        "host_alias_regex", description="Select hosts based on a regex against their alias."
    )
    pattern = ReqString(dump_default="", example="testali.*", description="Regex pattern.")


class BIHostChoice(OneOfSchema):
    type_field = "type"
    type_field_remove = False
    type_schemas = {
        "all_hosts": BIAllHostsChoiceSchema,
        "host_name_regex": BIHostNameRegexChoiceSchema,
        "host_alias_regex": BIHostAliasRegexChoiceSchema,
    }

    def get_obj_type(self, obj: Mapping[str, str]) -> str:
        return obj["type"]


class LabelConditionSchema(Schema):
    operator = ReqString(enum=["and", "or", "not"], description="Condition operator.")
    label = ReqString(description="Label name and value.")


class LabelGroupConditionSchema(Schema):
    operator = fields.String(
        enum=["and", "or", "not"],
        description="Condition operator.",
        load_default="and",
    )
    label_group = ReqList(
        fields.Nested(LabelConditionSchema),
        description="Label conditions.",
    )

    @pre_dump
    def _pre_dump(
        self, data: dict[str, Any] | tuple[AndOrNotLiteral, LabelGroup], **kwargs: Any
    ) -> dict[str, Any]:
        if isinstance(data, dict):
            return data
        return {
            "operator": data[0],
            "label_group": [{"operator": op, "label": val} for op, val in data[1]],
        }

    @post_load
    def _post_load(self, data: dict[str, Any], **kwargs: Any) -> tuple[AndOrNotLiteral, LabelGroup]:
        op: AndOrNotLiteral = data["operator"]
        label_group: LabelGroup = [
            (label_condition["operator"], label_condition["label"])
            for label_condition in data["label_group"]
        ]
        return op, label_group


class HostConditionsSchema(Schema):
    host_folder = ReqString(dump_default="", example="servers/groupA", description="Host folder.")
    host_label_groups = ReqList(
        fields.Nested(LabelGroupConditionSchema),
        dump_default=[],
        example=[
            {
                "label_group": [
                    {
                        "operator": "and",
                        "label": "db:mssql",
                    },
                ],
            },
            {
                "operator": "and",
                "label_group": [
                    {
                        "operator": "and",
                        "label": "network/primary:yes",
                    },
                ],
            },
        ],
        description="Host label conditions. Although all items in this list have a default operator"
        " value, the operator value for the the first item in the list does not have any effect.",
    )
    host_tags = ReqDict(dump_default={}, example={}, description="Host tags.")
    host_choice = ReqNested(
        BIHostChoice,
        dump_default={"type": "all_hosts"},
        example={"type": "all_hosts"},
        description="Host selection.",
    )


class ServiceConditionsSchema(HostConditionsSchema):
    service_regex = ReqString(
        dump_default="", example="Filesystem.*", description="Service name regex."
    )
    service_label_groups = ReqList(
        fields.Nested(LabelGroupConditionSchema),
        dump_default=[],
        example=[
            {
                "label_group": [
                    {
                        "operator": "and",
                        "label": "db:mssql",
                    },
                ],
            },
            {
                "operator": "and",
                "label_group": [
                    {
                        "operator": "and",
                        "label": "network/primary:yes",
                    },
                ],
            },
        ],
        description="Service label conditions. Although all items in this list have a default operator"
        " value, the operator value for the the first item in the list does not have any effect.",
    )


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
    def kind(cls) -> SearchKind:
        return "empty"

    @classmethod
    def schema(cls) -> type[BIEmptySearchSchema]:
        return BIEmptySearchSchema

    def execute(self, macros: MacroMapping, bi_searcher: ABCBISearcher) -> list[dict]:
        return [{}]

    def serialize(self):
        return {
            "type": self.kind(),
        }


class BIEmptySearchSchema(Schema):
    type = ReqConstant(BIEmptySearch.kind(), description="Empty search.")


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
    def kind(cls) -> SearchKind:
        return "host_search"

    @classmethod
    def schema(cls) -> type[BIHostSearchSchema]:
        return BIHostSearchSchema

    def serialize(self):
        return {
            "type": self.kind(),
            "conditions": self.conditions,
            "refer_to": self.refer_to,
        }

    def __init__(self, search_config: dict[str, Any]) -> None:
        super().__init__(search_config)
        self.conditions = search_config["conditions"]
        self.refer_to = search_config["refer_to"]

    def execute(self, macros: MacroMapping, bi_searcher: ABCBISearcher) -> list[dict]:
        new_conditions = replace_macros(self.conditions, macros)
        search_matches: list[BIHostSearchMatch] = bi_searcher.search_hosts(new_conditions)

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

        raise NotImplementedError(f"Invalid refer to type {self.refer_to!r}")

    def _refer_to_host_results(self, search_matches: list[BIHostSearchMatch]) -> list[dict]:
        search_results = []
        for search_match in search_matches:
            search_result = {
                "$1$": search_match.match_groups[0] if search_match.match_groups else "",
                "$HOSTNAME$": search_match.host.name,
                "$HOSTALIAS$": search_match.host.alias,
            }
            for idx, group in enumerate(search_match.match_groups):
                search_result["$HOST_MG_%d$" % idx] = group
            search_results.append(search_result)
        return search_results

    def _refer_to_children_results(
        self, search_matches: list[BIHostSearchMatch], bi_searcher: ABCBISearcher
    ) -> list[dict]:
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
                    "$HOSTALIAS$": bi_searcher.hosts[child].alias,
                }
                search_results.append(search_result)
        return search_results

    def _refer_to_parent_results(self, search_matches: list[BIHostSearchMatch]) -> list[dict]:
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
                    "$HOSTALIAS$": search_match.host.alias,
                }
                search_result["$2$"] = parent
                search_results.append(search_result)

        return search_results

    def _refer_to_children_with_results(
        self, search_matches: list[BIHostSearchMatch], bi_searcher: ABCBISearcher, refer_to: dict
    ) -> list[dict]:
        all_children: set[HostName] = set()

        # Determine pool of children
        for search_match in search_matches:
            all_children.update(search_match.host.children)

        # Filter childrens known to bi_searcher
        children_host_data: list[BIHostData] = [
            bi_searcher.hosts[x] for x in all_children if x in bi_searcher.hosts
        ]

        conditions = refer_to["conditions"]
        hosts, _matched_re_groups = bi_searcher.filter_host_choice(
            children_host_data, conditions["host_choice"]
        )
        matched_hosts = bi_searcher.filter_host_folder(hosts, conditions["host_folder"])
        matched_hosts = bi_searcher.filter_host_tags(matched_hosts, conditions["host_tags"])
        matched_hosts = bi_searcher.filter_host_labels(
            matched_hosts, conditions["host_label_groups"]
        )

        search_results = []
        for host in matched_hosts:
            # Note: The parameter $1$ does not reflect the first regex match group for the initial host
            #       This information was lost when all children were put into the all_children pool
            #       We can live with it. The option is not used sensibly anywhere anyway :)
            search_result = {"$1$": host.name, "$HOSTNAME$": host.name, "$HOSTALIAS$": host.alias}
            search_results.append(search_result)
        return search_results


class HostSchema(Schema):
    type = ReqConstant("host", description="Create nodes from the matched hosts themselves.")


class ParentSchema(Schema):
    type = ReqConstant("parent", description="Create nodes for all the parents of matched hosts.")


class ChildSchema(Schema):
    type = ReqConstant("child", description="Create nodes for all the children of matched hosts.")


class ChildWithSchema(Schema):
    type = ReqConstant(
        "child_with",
        description="Create nodes for all the children of matched hosts that also match other conditions.",
    )
    conditions = ReqNested(
        HostConditionsSchema,
        dump_default=HostConditionsSchema().dump({}),
        description="Extra conditions for the child.",
    )
    host_choice = ReqNested(
        BIHostChoice,
        dump_default={"type": "all_hosts"},
        example={"type": "all_hosts"},
        description="Child host selector.",
    )


class ReferToSchema(OneOfSchema):
    type_field = "type"
    type_field_remove = False
    type_schemas = {
        "host": HostSchema,
        "parent": ParentSchema,
        "child": ChildSchema,
        "child_with": ChildWithSchema,
    }

    def get_obj_type(self, obj: str | dict[str, Any]) -> str:
        return obj if isinstance(obj, str) else obj["type"]


class BIHostSearchSchema(Schema):
    type = ReqConstant(BIHostSearch.kind(), description="Host search.")
    conditions = ReqNested(
        HostConditionsSchema,
        dump_default=HostConditionsSchema().dump({}),
        description="Host conditions.",
    )
    refer_to = ReqNested(
        ReferToSchema,
        dump_default={"type": "host"},
        description="Create nodes based on the matched hosts, their parents or their children.",
    )

    @pre_load
    def pre_load(self, data: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
        if isinstance(data["refer_to"], str):
            # Fixes legacy schema config: {"refer_to": "host"}
            data["refer_to"] = {"type": data["refer_to"]}
        return data

    @post_dump
    def post_dump(self, data: str | dict[str, Any], **kwargs: Any) -> dict[str, Any]:
        # Fixes legacy schema config: {"refer_to": "host"}
        return {"type": data} if isinstance(data, str) else data


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
    def kind(cls) -> SearchKind:
        return "service_search"

    @classmethod
    def schema(cls) -> type[BIServiceSearchSchema]:
        return BIServiceSearchSchema

    def serialize(self):
        return {
            "type": self.kind(),
            "conditions": self.conditions,
        }

    def __init__(self, search_config: dict[str, Any]) -> None:
        super().__init__(search_config)
        self.conditions = search_config["conditions"]

    def execute(self, macros: MacroMapping, bi_searcher: ABCBISearcher) -> list[dict]:
        new_conditions = replace_macros(self.conditions, macros)
        search_matches: list[BIServiceSearchMatch] = bi_searcher.search_services(new_conditions)
        search_results = []
        for search_match in sorted(search_matches, key=lambda x: x.service_description):
            search_result = {
                "$1$": next(iter(search_match.host_match.match_groups), ""),
                "$HOSTNAME$": search_match.host_match.host.name,
                "$HOSTALIAS$": search_match.host_match.host.alias,
            }
            for idx, group in enumerate(search_match.match_groups, start=2):
                search_result["$%d$" % (idx)] = group

            for idx, group in enumerate(search_match.host_match.match_groups):
                search_result["$HOST_MG_%d$" % idx] = group
            search_results.append(search_result)
        return search_results


class BIServiceSearchSchema(Schema):
    type = ReqConstant(BIServiceSearch.kind(), description="Service search.")
    conditions = ReqNested(
        ServiceConditionsSchema,
        dump_default=ServiceConditionsSchema().dump({}),
        description="Service conditions.",
    )


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
    def kind(cls) -> SearchKind:
        return "fixed_arguments"

    def serialize(self):
        return {
            "type": self.kind(),
            "arguments": self.arguments,
        }

    @classmethod
    def schema(cls) -> type[BIFixedArgumentsSearchSchema]:
        return BIFixedArgumentsSearchSchema

    def __init__(self, search_config: dict[str, Any]) -> None:
        super().__init__(search_config)
        self.arguments = search_config["arguments"]

    def execute(self, macros: MacroMapping, bi_searcher: ABCBISearcher) -> list[dict]:
        results: list[dict] = []
        new_vars = replace_macros(self.arguments, macros)
        for argument in new_vars:
            key = argument["key"]
            for idx, value in enumerate(argument["values"]):
                if len(results) <= idx:
                    results.append({})
                results[idx][f"${key}$"] = value

        return results


class BIFixedArgumentsSearchTokenSchema(Schema):
    key = ReqString(description="Argument name.")
    values = ReqList(fields.String, description="Argument value.")


class BIFixedArgumentsSearchSchema(Schema):
    type = ReqConstant(BIFixedArgumentsSearch.kind(), description="Fixed search arguments.")
    arguments = ReqList(
        fields.Nested(BIFixedArgumentsSearchTokenSchema), description="Search arguments."
    )


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
    type_schemas = {k: v.schema() for k, v in bi_search_registry.items()}

    def get_obj_type(self, obj: ABCBISearch | dict) -> str:
        return obj["type"] if isinstance(obj, dict) else obj.kind()
