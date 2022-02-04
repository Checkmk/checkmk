#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2020 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Any, Dict, List, Type, Union

from marshmallow_oneofschema import OneOfSchema  # type: ignore[import]

from cmk.utils.bi.bi_lib import (
    ABCBIAction,
    ABCBICompiledNode,
    ABCBISearcher,
    ABCWithSchema,
    ActionArgument,
    ActionArguments,
    bi_action_registry,
    BIHostSearchMatch,
    BIParams,
    BIParamsSchema,
    replace_macros,
    ReqConstant,
    ReqNested,
    ReqString,
    SearchResult,
    SearchResults,
)
from cmk.utils.bi.bi_rule_interface import bi_rule_id_registry
from cmk.utils.bi.bi_schema import Schema
from cmk.utils.bi.bi_trees import BICompiledLeaf, BIRemainingResult
from cmk.utils.macros import MacroMapping

#   .--CallARule-----------------------------------------------------------.
#   |               ____      _ _    _    ____        _                    |
#   |              / ___|__ _| | |  / \  |  _ \ _   _| | ___               |
#   |             | |   / _` | | | / _ \ | |_) | | | | |/ _ \              |
#   |             | |__| (_| | | |/ ___ \|  _ <| |_| | |  __/              |
#   |              \____\__,_|_|_/_/   \_\_| \_\\__,_|_|\___|              |
#   |                                                                      |
#   +----------------------------------------------------------------------+


@bi_action_registry.register
class BICallARuleAction(ABCBIAction, ABCWithSchema):
    @classmethod
    def type(cls) -> str:
        return "call_a_rule"

    @classmethod
    def schema(cls) -> Type["BICallARuleActionSchema"]:
        return BICallARuleActionSchema

    def serialize(self):
        return {
            "type": self.type(),
            "rule_id": self.rule_id,
            "params": self.params.serialize(),
        }

    def __init__(self, action_config: Dict[str, Any]):
        super().__init__(action_config)
        self.rule_id = action_config["rule_id"]
        self.params = BIParams(action_config["params"])

    def _generate_action_arguments(
        self, search_results: SearchResults, macros: MacroMapping
    ) -> ActionArguments:
        return [
            tuple(replace_macros(self.params.arguments, {**macros, **x})) for x in search_results
        ]

    def execute(
        self, argument: ActionArgument, bi_searcher: ABCBISearcher
    ) -> List[ABCBICompiledNode]:
        return bi_rule_id_registry[self.rule_id].compile(argument, bi_searcher)

    def preview_rule_title(self, search_result: SearchResult) -> str:
        bi_rule = bi_rule_id_registry[self.rule_id]
        rule_arguments = replace_macros(self.params.arguments, search_result)
        mapped_rule_arguments = dict(
            zip(["$%s$" % x for x in bi_rule.params.arguments], rule_arguments)
        )
        return replace_macros(bi_rule.properties.title, mapped_rule_arguments)


class BICallARuleActionSchema(Schema):
    type = ReqConstant(BICallARuleAction.type())
    rule_id = ReqString(dump_default="", example="test_rule_1")
    params = ReqNested(
        BIParamsSchema, dump_default=BIParamsSchema().dump({}), example=BIParamsSchema().dump({})
    )


#   .--StateOfHost---------------------------------------------------------.
#   |        ____  _        _        ___   __ _   _           _            |
#   |       / ___|| |_ __ _| |_ ___ / _ \ / _| | | | ___  ___| |_          |
#   |       \___ \| __/ _` | __/ _ \ | | | |_| |_| |/ _ \/ __| __|         |
#   |        ___) | || (_| | ||  __/ |_| |  _|  _  | (_) \__ \ |_          |
#   |       |____/ \__\__,_|\__\___|\___/|_| |_| |_|\___/|___/\__|         |
#   |                                                                      |
#   +----------------------------------------------------------------------+


@bi_action_registry.register
class BIStateOfHostAction(ABCBIAction, ABCWithSchema):
    @classmethod
    def type(cls) -> str:
        return "state_of_host"

    @classmethod
    def schema(cls) -> Type["BIStateOfHostActionSchema"]:
        return BIStateOfHostActionSchema

    def serialize(self):
        return {
            "type": self.type(),
            "host_regex": self.host_regex,
        }

    def __init__(self, action_config: Dict[str, Any]):
        super().__init__(action_config)
        self.host_regex = action_config["host_regex"]

    def _generate_action_arguments(
        self, search_results: SearchResults, macros: MacroMapping
    ) -> ActionArguments:
        return [(replace_macros(self.host_regex, {**macros, **x}),) for x in search_results]

    def execute(
        self, argument: ActionArgument, bi_searcher: ABCBISearcher
    ) -> List[ABCBICompiledNode]:
        host_matches, _match_groups = bi_searcher.get_host_name_matches(
            list(bi_searcher.hosts.values()), argument[0]
        )
        return [BICompiledLeaf(host_name=x.name, site_id=x.site_id) for x in host_matches]


class BIStateOfHostActionSchema(Schema):
    type = ReqConstant(BIStateOfHostAction.type())
    host_regex = ReqString(dump_default="", example="testhost")


#   .--StateOfSvc----------------------------------------------------------.
#   |           ____  _        _        ___   __ ____                      |
#   |          / ___|| |_ __ _| |_ ___ / _ \ / _/ ___|_   _____            |
#   |          \___ \| __/ _` | __/ _ \ | | | |_\___ \ \ / / __|           |
#   |           ___) | || (_| | ||  __/ |_| |  _|___) \ V / (__            |
#   |          |____/ \__\__,_|\__\___|\___/|_| |____/ \_/ \___|           |
#   |                                                                      |
#   +----------------------------------------------------------------------+


@bi_action_registry.register
class BIStateOfServiceAction(ABCBIAction, ABCWithSchema):
    @classmethod
    def type(cls) -> str:
        return "state_of_service"

    @classmethod
    def schema(cls) -> Type["BIStateOfServiceActionSchema"]:
        return BIStateOfServiceActionSchema

    def serialize(self):
        return {
            "type": self.type(),
            "host_regex": self.host_regex,
            "service_regex": self.service_regex,
        }

    def __init__(self, action_config: Dict[str, Any]):
        super().__init__(action_config)
        self.host_regex = action_config["host_regex"]
        self.service_regex = action_config["service_regex"]

    def _generate_action_arguments(
        self, search_results: SearchResults, macros: MacroMapping
    ) -> ActionArguments:
        return [
            (
                replace_macros(self.host_regex, {**macros, **x}),
                replace_macros(self.service_regex, {**macros, **x}),
            )
            for x in search_results
        ]

    def execute(
        self, argument: ActionArgument, bi_searcher: ABCBISearcher
    ) -> List[ABCBICompiledNode]:
        matched_hosts, match_groups = bi_searcher.get_host_name_matches(
            list(bi_searcher.hosts.values()), argument[0]
        )

        host_search_matches = [BIHostSearchMatch(x, match_groups[x.name]) for x in matched_hosts]
        service_matches = bi_searcher.get_service_description_matches(
            host_search_matches, argument[1]
        )
        return [
            BICompiledLeaf(
                site_id=x.host_match.host.site_id,
                host_name=x.host_match.host.name,
                service_description=x.service_description,
            )
            for x in service_matches
        ]


class BIStateOfServiceActionSchema(Schema):
    type = ReqConstant(BIStateOfServiceAction.type())
    host_regex = ReqString(dump_default="", example="testhost")
    service_regex = ReqString(dump_default="", example="testservice")


#   .--StateOfRmn----------------------------------------------------------.
#   |       ____  _        _        ___   __ ____                          |
#   |      / ___|| |_ __ _| |_ ___ / _ \ / _|  _ \ _ __ ___  _ __          |
#   |      \___ \| __/ _` | __/ _ \ | | | |_| |_) | '_ ` _ \| '_ \         |
#   |       ___) | || (_| | ||  __/ |_| |  _|  _ <| | | | | | | | |        |
#   |      |____/ \__\__,_|\__\___|\___/|_| |_| \_\_| |_| |_|_| |_|        |
#   |                                                                      |
#   +----------------------------------------------------------------------+


@bi_action_registry.register
class BIStateOfRemainingServicesAction(ABCBIAction, ABCWithSchema):
    @classmethod
    def type(cls) -> str:
        return "state_of_remaining_services"

    @classmethod
    def schema(cls) -> Type["BIStateOfRemainingServicesActionSchema"]:
        return BIStateOfRemainingServicesActionSchema

    def serialize(self):
        return {
            "type": self.type(),
            "host_regex": self.host_regex,
        }

    def __init__(self, action_config: Dict[str, Any]):
        super().__init__(action_config)
        self.host_regex = action_config["host_regex"]

    def _generate_action_arguments(
        self, search_results: SearchResults, macros: MacroMapping
    ) -> ActionArguments:
        return [(replace_macros(self.host_regex, {**macros, **x}),) for x in search_results]

    def execute(
        self, argument: ActionArgument, bi_searcher: ABCBISearcher
    ) -> List[ABCBICompiledNode]:
        host_matches, _match_groups = bi_searcher.get_host_name_matches(
            list(bi_searcher.hosts.values()), argument[0]
        )
        return [BIRemainingResult([x.name for x in host_matches])]


class BIStateOfRemainingServicesActionSchema(Schema):
    type = ReqConstant(BIStateOfRemainingServicesAction.type())
    host_regex = ReqString(dump_default="", example="testhost")


#   .--Schemas-------------------------------------------------------------.
#   |              ____       _                                            |
#   |             / ___|  ___| |__   ___ _ __ ___   __ _ ___               |
#   |             \___ \ / __| '_ \ / _ \ '_ ` _ \ / _` / __|              |
#   |              ___) | (__| | | |  __/ | | | | | (_| \__ \              |
#   |             |____/ \___|_| |_|\___|_| |_| |_|\__,_|___/              |
#   |                                                                      |
#   +----------------------------------------------------------------------+


class BIActionSchema(OneOfSchema):
    type_field = "type"
    type_field_remove = False
    type_schemas = dict((k, v.schema()) for k, v in bi_action_registry.items())

    # type_schemas = {
    #    "call_a_rule": BICallARuleActionSchema,
    #    "state_of_host": BIStateOfHostActionSchema,
    #    "state_of_service": BIStateOfServiceActionSchema,
    #    "state_of_remaining_services": BIStateOfRemainingServicesActionSchema,
    # }

    def get_obj_type(self, obj: Union[ABCBIAction, dict]) -> str:
        if isinstance(obj, dict):
            return obj["type"]
        return obj.type()
