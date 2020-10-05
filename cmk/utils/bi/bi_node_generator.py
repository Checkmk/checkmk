#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2020 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

#   .--NodeGen.------------------------------------------------------------.
#   |              _   _           _       ____                            |
#   |             | \ | | ___   __| | ___ / ___| ___ _ __                  |
#   |             |  \| |/ _ \ / _` |/ _ \ |  _ / _ \ '_ \                 |
#   |             | |\  | (_) | (_| |  __/ |_| |  __/ | | |_               |
#   |             |_| \_|\___/ \__,_|\___|\____|\___|_| |_(_)              |
#   |                                                                      |
#   +----------------------------------------------------------------------+

from marshmallow import Schema  # type: ignore[import]
from typing import List, Type

from cmk.utils.bi.bi_lib import (
    ABCBICompiledNode,
    ReqNested,
    MacroMappings,
)

from cmk.utils.bi.bi_actions import (
    BIActionSchema,
    BICallARuleAction,
    BIStateOfHostActionSchema,
)

from cmk.utils.bi.bi_node_generator_interface import ABCBINodeGenerator
from cmk.utils.bi.bi_search import BISearchSchema


class BINodeGenerator(ABCBINodeGenerator):
    @classmethod
    def schema(cls) -> Type["BINodeGeneratorSchema"]:
        return BINodeGeneratorSchema

    def compile(self, macros: MacroMappings) -> List[ABCBICompiledNode]:
        action_results = []
        search_results = self.search.execute(macros)
        for search_result in search_results:
            action_arguments = macros.copy()
            action_arguments.update(search_result)
            if self.restrict_rule_title is not None and isinstance(self.action, BICallARuleAction):
                rule_title = self.action.preview_rule_title(action_arguments)
                if rule_title != self.restrict_rule_title:
                    continue

            action_results.extend(self.action.execute(action_arguments))
        return action_results


class BINodeGeneratorSchema(Schema):
    search = ReqNested(BISearchSchema, default={"type": "empty"}, example={"type": "empty"})
    action = ReqNested(BIActionSchema,
                       default=BIStateOfHostActionSchema().dump({}).data,
                       example=BIStateOfHostActionSchema().dump({
                           "host_regex": "testhost"
                       }).data)
