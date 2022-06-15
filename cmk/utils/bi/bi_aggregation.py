#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Any, Dict, List, Optional, Set, Type

from cmk.utils.bi.bi_lib import (
    ABCBISearcher,
    BIAggregationComputationOptions,
    BIAggregationGroups,
    create_nested_schema,
    create_nested_schema_for_class,
    ReqString,
    String,
)
from cmk.utils.bi.bi_node_generator import BINodeGenerator
from cmk.utils.bi.bi_node_vis import BIAggregationVisualizationSchema
from cmk.utils.bi.bi_rule import BIRule
from cmk.utils.bi.bi_schema import Schema
from cmk.utils.bi.bi_trees import BICompiledAggregation, BICompiledRule
from cmk.utils.bi.type_defs import AggrConfigDict

# TODO: fix duplicate type def. the original type def is in gui-managed (module layer violation)
from cmk.utils.type_defs import HostName, ServiceName

SCOPE_GLOBAL = None

#   .--Aggregation---------------------------------------------------------.
#   |         _                                    _   _                   |
#   |        / \   __ _  __ _ _ __ ___  __ _  __ _| |_(_) ___  _ __        |
#   |       / _ \ / _` |/ _` | '__/ _ \/ _` |/ _` | __| |/ _ \| '_ \       |
#   |      / ___ \ (_| | (_| | | |  __/ (_| | (_| | |_| | (_) | | | |      |
#   |     /_/   \_\__, |\__, |_|  \___|\__, |\__,_|\__|_|\___/|_| |_|      |
#   |             |___/ |___/          |___/                               |
#   +----------------------------------------------------------------------+


class BIAggregation:
    def __init__(self, aggr_config: Optional[AggrConfigDict] = None, pack_id: str = "") -> None:
        super().__init__()
        if aggr_config is None:
            aggr_config = self.schema()().dump({})
        self.id = aggr_config["id"]

        self.comment = aggr_config.get("comment", "")
        self.customer = aggr_config.get("customer")
        self.pack_id = pack_id
        self.node = BINodeGenerator(aggr_config["node"])
        self.groups = BIAggregationGroups(aggr_config["groups"])
        self.computation_options = BIAggregationComputationOptions(
            aggr_config["computation_options"]
        )
        self.aggregation_visualization = aggr_config["aggregation_visualization"]

    @classmethod
    def schema(cls) -> Type["BIAggregationSchema"]:
        return BIAggregationSchema

    def serialize(self):
        return {
            "id": self.id,
            "comment": self.comment,
            "customer": self.customer,
            "groups": self.groups.serialize(),
            "node": self.node.serialize(),
            "aggregation_visualization": self.aggregation_visualization,
            "computation_options": self.computation_options.serialize(),
        }

    def clone(self) -> "BIAggregation":
        aggregation_config = self.schema()().dump(self)
        return BIAggregation(aggregation_config)

    def compile(self, bi_searcher: ABCBISearcher) -> BICompiledAggregation:
        compiled_branches: List[BICompiledRule] = []
        if not self.computation_options.disabled:
            branches = self.node.compile({}, bi_searcher)

            # Each sub-branch represents one BI Aggregation with an unique name
            # The postprocessing phase takes care of the "remaining services" action
            for branch in branches:
                services_of_host: Dict[HostName, Set[ServiceName]] = {}
                for _site, host_name, service_description in branch.required_elements():
                    if service_description is None:
                        continue
                    services_of_host.setdefault(host_name, set()).add(service_description)
                branch.compile_postprocess(branch, services_of_host, bi_searcher)

            compiled_branches = self._verify_all_branches_start_with_rule(branches)

        return BICompiledAggregation(
            self.id,
            compiled_branches,
            self.computation_options,
            self.aggregation_visualization,
            self.groups,
        )

    def _verify_all_branches_start_with_rule(self, branches) -> List[BICompiledRule]:
        new_branches: List[BICompiledRule] = [x for x in branches if isinstance(x, BICompiledRule)]
        assert len(branches) == len(new_branches)
        return new_branches

    @classmethod
    def create_trees_from_schema(cls, schema_config: Dict[str, Any]) -> BICompiledAggregation:
        branches = [BIRule.create_tree_from_schema(config) for config in schema_config["branches"]]
        aggregation_id = schema_config["id"]
        computation_options = BIAggregationComputationOptions(schema_config["computation_options"])
        aggregation_visualization = schema_config["aggregation_visualization"]
        groups = BIAggregationGroups(schema_config["groups"])
        return BICompiledAggregation(
            aggregation_id, branches, computation_options, aggregation_visualization, groups
        )


class BIAggregationSchema(Schema):
    class Meta:
        ordered = True

    id = ReqString(
        dump_default="",
        example="aggr1",
        description="TODO: Hier muß Andreas noch etwas reinschreiben!",
    )
    comment = String(
        description="An optional comment that may be used to explain the purpose of this object.",
        allow_none=True,
        example="Rule comment",
    )
    customer = String(
        description="CME Edition only: The customer id for this aggregation.",
        allow_none=True,
        example="customer1",
    )
    groups = create_nested_schema_for_class(
        BIAggregationGroups,
        example_config={
            "names": ["groupA", "groupB"],
            "paths": [["path", "group", "a"], ["path", "group", "b"]],
        },
    )
    node = create_nested_schema_for_class(BINodeGenerator)
    aggregation_visualization = create_nested_schema(BIAggregationVisualizationSchema)
    computation_options = create_nested_schema_for_class(BIAggregationComputationOptions)
