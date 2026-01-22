#!/usr/bin/env python3
# Copyright (C) 2020 Checkmk GmbH - License: GNU General Public License v2
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

from collections.abc import Mapping
from typing import override, TypedDict

from cmk.bi.actions import BIActionSchema, BICallARuleAction, BIStateOfHostActionSchema
from cmk.bi.lib import ABCBICompiledNode, ABCBISearcher, create_nested_schema
from cmk.bi.node_generator_interface import ABCBINodeGenerator
from cmk.bi.schema import Schema
from cmk.bi.search import BIEmptySearchSchema, BISearchSchema
from cmk.bi.type_defs import ActionSerialized, SearchSerialized


class BINodeGeneratorSerialized(TypedDict):
    search: SearchSerialized
    action: ActionSerialized


class BINodeGenerator(ABCBINodeGenerator):
    @override
    @classmethod
    def schema(cls) -> type["BINodeGeneratorSchema"]:
        return BINodeGeneratorSchema

    @override
    def compile(
        self, macros: Mapping[str, str], bi_searcher: ABCBISearcher
    ) -> list[ABCBICompiledNode]:
        search_results = self.search.execute(macros, bi_searcher)

        # Note: This feature is currently unused
        if self.restrict_rule_title is not None and isinstance(self.action, BICallARuleAction):
            filtered_search_results = []
            for search_result in search_results:
                action_arguments = dict(macros)
                action_arguments |= search_result
                if self.restrict_rule_title == self.action.preview_rule_title(action_arguments):
                    filtered_search_results.append(search_result)
            search_results = filtered_search_results

        return sorted(self.action.execute_search_results(search_results, macros, bi_searcher))

    def serialize(self) -> BINodeGeneratorSerialized:
        return {
            "search": self.search.serialize(),
            "action": self.action.serialize(),
        }


class BINodeGeneratorSchema(Schema):
    search = create_nested_schema(
        BISearchSchema, default_schema=BIEmptySearchSchema, description="Search criteria."
    )
    action = create_nested_schema(
        BIActionSchema,
        default_schema=BIStateOfHostActionSchema,
        description="Action on search results.",
    )
