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

from typing import List, Type

from cmk.utils.bi.bi_actions import BIActionSchema, BICallARuleAction, BIStateOfHostActionSchema
from cmk.utils.bi.bi_lib import ABCBICompiledNode, ABCBISearcher, create_nested_schema
from cmk.utils.bi.bi_node_generator_interface import ABCBINodeGenerator
from cmk.utils.bi.bi_schema import Schema
from cmk.utils.bi.bi_search import BIEmptySearchSchema, BISearchSchema
from cmk.utils.macros import MacroMapping


class BINodeGenerator(ABCBINodeGenerator):
    @classmethod
    def schema(cls) -> Type["BINodeGeneratorSchema"]:
        return BINodeGeneratorSchema

    def compile(self, macros: MacroMapping, bi_searcher: ABCBISearcher) -> List[ABCBICompiledNode]:
        search_results = self.search.execute(macros, bi_searcher)

        # Note: This feature is currently unused
        if self.restrict_rule_title is not None and isinstance(self.action, BICallARuleAction):
            filtered_search_results = []
            for search_result in search_results:
                action_arguments = dict(macros)
                action_arguments.update(search_result)
                if self.restrict_rule_title == self.action.preview_rule_title(action_arguments):
                    filtered_search_results.append(search_result)
            search_results = filtered_search_results

        return sorted(self.action.execute_search_results(search_results, macros, bi_searcher))

    def serialize(self):
        return {
            "search": self.search.serialize(),
            "action": self.action.serialize(),
        }


class BINodeGeneratorSchema(Schema):
    search = create_nested_schema(BISearchSchema, default_schema=BIEmptySearchSchema)
    action = create_nested_schema(BIActionSchema, default_schema=BIStateOfHostActionSchema)
