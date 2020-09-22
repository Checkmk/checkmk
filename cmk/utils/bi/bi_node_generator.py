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
    ABCBISearcher,
    MacroMappings,
    create_nested_schema,
)

from cmk.utils.bi.bi_actions import (
    BIActionSchema,
    BIStateOfHostActionSchema,
    BICallARuleAction,
)

from cmk.utils.bi.bi_node_generator_interface import ABCBINodeGenerator
from cmk.utils.bi.bi_search import BISearchSchema, BIEmptySearchSchema


class BINodeGenerator(ABCBINodeGenerator):
    @classmethod
    def schema(cls) -> Type["BINodeGeneratorSchema"]:
        return BINodeGeneratorSchema

    def compile(self, macros: MacroMappings, bi_searcher: ABCBISearcher) -> List[ABCBICompiledNode]:
        action_results = []
        search_results = self.search.execute(macros, bi_searcher)
        for search_result in search_results:
            action_arguments = macros.copy()
            action_arguments.update(search_result)
            if self.restrict_rule_title is not None and isinstance(self.action, BICallARuleAction):
                rule_title = self.action.preview_rule_title(action_arguments)
                if rule_title != self.restrict_rule_title:
                    continue

            action_results.extend(self.action.execute(action_arguments, bi_searcher))
        return action_results


class BINodeGeneratorSchema(Schema):
    search = create_nested_schema(BISearchSchema, default_schema=BIEmptySearchSchema)
    action = create_nested_schema(BIActionSchema, default_schema=BIStateOfHostActionSchema)
