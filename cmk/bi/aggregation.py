#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

from collections import OrderedDict
from typing import Any

from cmk.ccc.hostaddress import HostName

# TODO: fix duplicate type def. the original type def is in gui-managed (module layer violation)
from cmk.utils.servicename import ServiceName

from cmk.bi.lib import (
    ABCBICompiledNode,
    ABCBISearcher,
    BIAggregationComputationOptions,
    BIAggregationGroups,
    create_nested_schema,
    create_nested_schema_for_class,
    ReqString,
)
from cmk.bi.node_generator import BINodeGenerator
from cmk.bi.node_vis import BIAggregationVisualizationSchema
from cmk.bi.rule import BIRule
from cmk.bi.schema import Schema
from cmk.bi.trees import BICompiledAggregation, BICompiledRule
from cmk.bi.type_defs import AggrConfigDict
from cmk.fields import String

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
    def __init__(self, aggr_config: AggrConfigDict | None = None, pack_id: str = "") -> None:
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
    def schema(cls) -> type[BIAggregationSchema]:
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

    def clone(self) -> BIAggregation:
        aggregation_config = self.schema()().dump(self)
        return BIAggregation(aggregation_config)

    def compile(self, bi_searcher: ABCBISearcher) -> BICompiledAggregation:
        compiled_branches: list[BICompiledRule] = []
        if not self.computation_options.disabled:
            branches = self.node.compile({}, bi_searcher)

            # Each sub-branch represents one BI Aggregation with an unique name
            # The postprocessing phase takes care of the "remaining services" action
            for branch in branches:
                services_of_host: dict[HostName, set[ServiceName]] = {}
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

    def _verify_all_branches_start_with_rule(
        self, branches: list[ABCBICompiledNode]
    ) -> list[BICompiledRule]:
        new_branches: list[BICompiledRule] = [x for x in branches if isinstance(x, BICompiledRule)]
        assert len(branches) == len(new_branches)
        return new_branches

    @classmethod
    def create_trees_from_schema(cls, schema_config: dict[str, Any]) -> BICompiledAggregation:
        branches = [BIRule.create_tree_from_schema(config) for config in schema_config["branches"]]
        aggregation_id = schema_config["id"]
        computation_options = BIAggregationComputationOptions(schema_config["computation_options"])
        aggregation_visualization = schema_config["aggregation_visualization"]
        groups = BIAggregationGroups(schema_config["groups"])
        return BICompiledAggregation(
            aggregation_id, branches, computation_options, aggregation_visualization, groups
        )


class BIAggregationSchema(Schema):
    @property
    def dict_class(self) -> type:
        return OrderedDict

    id = ReqString(
        dump_default="",
        example="aggr1",
        description="The unique aggregation id",
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
        description="Groups.",
    )
    node = create_nested_schema_for_class(
        BINodeGenerator,
        description="Node generation.",
    )
    aggregation_visualization = create_nested_schema(
        BIAggregationVisualizationSchema,
        description="Aggregation visualization options.",
    )
    computation_options = create_nested_schema_for_class(
        BIAggregationComputationOptions,
        description="Computation options.",
    )
