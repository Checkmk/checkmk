#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2020 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from marshmallow import Schema  # type: ignore[import]
from marshmallow_oneofschema import OneOfSchema  # type: ignore[import]
from typing import List, Dict, Type, Any
from cmk.utils.bi.bi_lib import (
    BIParams,
    BIParamsSchema,
    bi_action_registry,
    ABCBIAction,
    ABCBICompiledNode,
    replace_macros,
    SearchResult,
    ReqConstant,
    ReqString,
    ReqNested,
)

from cmk.utils.bi.bi_rule_interface import bi_rule_id_registry
from cmk.utils.bi.bi_searcher import bi_searcher
from cmk.utils.bi.bi_trees import (
    BICompiledLeaf,
    BIRemainingResult,
)

#   .--CallARule-----------------------------------------------------------.
#   |               ____      _ _    _    ____        _                    |
#   |              / ___|__ _| | |  / \  |  _ \ _   _| | ___               |
#   |             | |   / _` | | | / _ \ | |_) | | | | |/ _ \              |
#   |             | |__| (_| | | |/ ___ \|  _ <| |_| | |  __/              |
#   |              \____\__,_|_|_/_/   \_\_| \_\\__,_|_|\___|              |
#   |                                                                      |
#   +----------------------------------------------------------------------+


@bi_action_registry.register
class BICallARuleAction(ABCBIAction):
    @classmethod
    def type(cls) -> str:
        return "call_a_rule"

    @classmethod
    def schema(cls) -> Type["BICallARuleActionSchema"]:
        return BICallARuleActionSchema

    def __init__(self, action_config: Dict[str, Any]):
        super().__init__(action_config)
        self.rule_id = action_config["rule_id"]
        self.params = BIParams(action_config["params"])

    def execute(self, search_result: SearchResult) -> List[ABCBICompiledNode]:
        rule_arguments = replace_macros(self.params.arguments, search_result)
        return bi_rule_id_registry[self.rule_id].compile(rule_arguments)

    def preview_rule_title(self, search_result: SearchResult) -> str:
        bi_rule = bi_rule_id_registry[self.rule_id]

        rule_arguments = replace_macros(self.params.arguments, search_result)
        mapped_rule_arguments = dict(
            zip(["$%s$" % x for x in bi_rule.params.arguments], rule_arguments))
        return replace_macros(bi_rule.properties.title, mapped_rule_arguments)


class BICallARuleActionSchema(Schema):
    type = ReqConstant(BICallARuleAction.type())
    rule_id = ReqString(default="", example="test_rule_1")
    params = ReqNested(BIParamsSchema,
                       default=BIParamsSchema().dump({}).data,
                       example=BIParamsSchema().dump({}).data)


#   .--StateOfHost---------------------------------------------------------.
#   |        ____  _        _        ___   __ _   _           _            |
#   |       / ___|| |_ __ _| |_ ___ / _ \ / _| | | | ___  ___| |_          |
#   |       \___ \| __/ _` | __/ _ \ | | | |_| |_| |/ _ \/ __| __|         |
#   |        ___) | || (_| | ||  __/ |_| |  _|  _  | (_) \__ \ |_          |
#   |       |____/ \__\__,_|\__\___|\___/|_| |_| |_|\___/|___/\__|         |
#   |                                                                      |
#   +----------------------------------------------------------------------+


@bi_action_registry.register
class BIStateOfHostAction(ABCBIAction):
    @classmethod
    def type(cls) -> str:
        return "state_of_host"

    @classmethod
    def schema(cls) -> Type["BIStateOfHostActionSchema"]:
        return BIStateOfHostActionSchema

    def __init__(self, action_config: Dict[str, Any]):
        super().__init__(action_config)
        self.host_regex = action_config["host_regex"]

    def execute(self, search_result: SearchResult) -> List[ABCBICompiledNode]:
        host_re = replace_macros(self.host_regex, search_result)
        # TODO: check performance!
        host_matches, _match_groups = bi_searcher.get_host_name_matches(
            list(bi_searcher.hosts.values()), host_re)

        action_results: List[ABCBICompiledNode] = []
        for host_match in host_matches:
            action_results.append(
                BICompiledLeaf(host_name=host_match.name, site_id=host_match.site_id))
        return action_results


class BIStateOfHostActionSchema(Schema):
    type = ReqConstant(BIStateOfHostAction.type())
    host_regex = ReqString(default="", example="testhost")


#   .--StateOfSvc----------------------------------------------------------.
#   |           ____  _        _        ___   __ ____                      |
#   |          / ___|| |_ __ _| |_ ___ / _ \ / _/ ___|_   _____            |
#   |          \___ \| __/ _` | __/ _ \ | | | |_\___ \ \ / / __|           |
#   |           ___) | || (_| | ||  __/ |_| |  _|___) \ V / (__            |
#   |          |____/ \__\__,_|\__\___|\___/|_| |____/ \_/ \___|           |
#   |                                                                      |
#   +----------------------------------------------------------------------+


@bi_action_registry.register
class BIStateOfServiceAction(ABCBIAction):
    @classmethod
    def type(cls) -> str:
        return "state_of_service"

    @classmethod
    def schema(cls) -> Type["BIStateOfServiceActionSchema"]:
        return BIStateOfServiceActionSchema

    def __init__(self, action_config: Dict[str, Any]):
        super().__init__(action_config)
        self.host_regex = action_config["host_regex"]
        self.service_regex = action_config["service_regex"]

    def execute(self, search_result: SearchResult) -> List[ABCBICompiledNode]:
        host_re = replace_macros(self.host_regex, search_result)
        service_re = replace_macros(self.service_regex, search_result)
        host_matches, _match_groups = bi_searcher.get_host_name_matches(
            list(bi_searcher.hosts.values()), host_re)

        action_results: List[ABCBICompiledNode] = []
        service_matches = bi_searcher.get_service_description_matches(host_matches, service_re)
        for service_match in service_matches:
            action_results.append(
                BICompiledLeaf(
                    site_id=service_match.host.site_id,
                    host_name=service_match.host.name,
                    service_description=service_match.service_description,
                ))

        return action_results


class BIStateOfServiceActionSchema(Schema):
    type = ReqConstant(BIStateOfServiceAction.type())
    host_regex = ReqString(default="", example="testhost")
    service_regex = ReqString(default="", example="testservice")


#   .--StateOfRmn----------------------------------------------------------.
#   |       ____  _        _        ___   __ ____                          |
#   |      / ___|| |_ __ _| |_ ___ / _ \ / _|  _ \ _ __ ___  _ __          |
#   |      \___ \| __/ _` | __/ _ \ | | | |_| |_) | '_ ` _ \| '_ \         |
#   |       ___) | || (_| | ||  __/ |_| |  _|  _ <| | | | | | | | |        |
#   |      |____/ \__\__,_|\__\___|\___/|_| |_| \_\_| |_| |_|_| |_|        |
#   |                                                                      |
#   +----------------------------------------------------------------------+


@bi_action_registry.register
class BIStateOfRemainingServicesAction(ABCBIAction):
    @classmethod
    def type(cls) -> str:
        return "state_of_remaining_services"

    @classmethod
    def schema(cls) -> Type["BIStateOfRemainingServicesActionSchema"]:
        return BIStateOfRemainingServicesActionSchema

    def __init__(self, action_config: Dict[str, Any]):
        super().__init__(action_config)
        self.host_regex = action_config["host_regex"]

    def execute(self, search_result: SearchResult) -> List[ABCBICompiledNode]:
        host_re = replace_macros(self.host_regex, search_result)
        host_matches, _match_groups = bi_searcher.get_host_name_matches(
            list(bi_searcher.hosts.values()), host_re)
        return [BIRemainingResult([x.name for x in host_matches])]


class BIStateOfRemainingServicesActionSchema(Schema):
    type = ReqConstant(BIStateOfRemainingServicesAction.type())
    host_regex = ReqString(default="", example="testhost")


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

    #type_schemas = {
    #    "call_a_rule": BICallARuleActionSchema,
    #    "state_of_host": BIStateOfHostActionSchema,
    #    "state_of_service": BIStateOfServiceActionSchema,
    #    "state_of_remaining_services": BIStateOfRemainingServicesActionSchema,
    #}

    def get_obj_type(self, obj: ABCBIAction) -> str:
        return obj.type()
