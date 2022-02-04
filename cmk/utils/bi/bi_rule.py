#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2020 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

#   .--Rule----------------------------------------------------------------.
#   |                         ____        _                                |
#   |                        |  _ \ _   _| | ___                           |
#   |                        | |_) | | | | |/ _ \                          |
#   |                        |  _ <| |_| | |  __/                          |
#   |                        |_| \_\\__,_|_|\___|                          |
#   |                                                                      |
#   +----------------------------------------------------------------------+

from typing import Any, Dict, List, Optional, Sequence, Type

from marshmallow import fields

from cmk.utils.bi.bi_aggregation_functions import (
    BIAggregationFunctionBest,
    BIAggregationFunctionSchema,
)
from cmk.utils.bi.bi_lib import (
    ABCBICompiledNode,
    ABCBISearcher,
    ABCWithSchema,
    ActionArgument,
    bi_aggregation_function_registry,
    BIParams,
    create_nested_schema,
    create_nested_schema_for_class,
    get_schema_default_config,
    replace_macros,
    ReqList,
    ReqString,
)
from cmk.utils.bi.bi_node_generator import BINodeGenerator, BINodeGeneratorSchema
from cmk.utils.bi.bi_node_vis import BINodeVisBlockStyleSchema, BINodeVisLayoutStyleSchema
from cmk.utils.bi.bi_rule_interface import (
    ABCBIRule,
    bi_rule_id_registry,
    BIRuleComputationOptions,
    BIRuleProperties,
)
from cmk.utils.bi.bi_schema import Schema
from cmk.utils.bi.bi_trees import BICompiledLeaf, BICompiledRule
from cmk.utils.macros import MacroMapping


class BIRule(ABCBIRule, ABCWithSchema):
    def __init__(self, rule_config: Optional[Dict[str, Any]] = None, pack_id: str = ""):
        super().__init__()
        if rule_config is None:
            rule_config = get_schema_default_config(self.schema())

        self.id = rule_config["id"]
        self.pack_id = pack_id
        self._params = BIParams(rule_config["params"])

        # The raw configuration is kept. It is re-used by the generated BI Branches
        self._properties_config = rule_config["properties"]

        self.aggregation_function = bi_aggregation_function_registry.instantiate(
            rule_config["aggregation_function"]
        )
        self.computation_options = BIRuleComputationOptions(rule_config["computation_options"])
        self.node_visualization = rule_config["node_visualization"]
        self._properties = BIRuleProperties(rule_config["properties"])

        self.nodes = [BINodeGenerator(x) for x in rule_config["nodes"]]
        bi_rule_id_registry.register(self)

    @property
    def properties(self) -> BIRuleProperties:
        return self._properties

    @property
    def params(self) -> BIParams:
        return self._params

    @property
    def title(self) -> str:
        return self.properties.title

    @classmethod
    def schema(cls) -> Type["BIRuleSchema"]:
        return BIRuleSchema

    def serialize(self):
        return {
            "id": self.id,
            "nodes": [node.serialize() for node in self.nodes],
            "params": self.params.serialize(),
            "node_visualization": self.node_visualization,
            "properties": self.properties.serialize(),
            "aggregation_function": self.aggregation_function.serialize(),
            "computation_options": self.computation_options.serialize(),
        }

    def clone(self) -> "BIRule":
        rule_config = self.schema()().dump(self)
        return BIRule(rule_config)

    def get_nodes(self) -> Sequence[BINodeGenerator]:
        return self.nodes

    def num_nodes(self) -> int:
        return len(self.nodes)

    def compile(
        self, extern_arguments: ActionArgument, bi_searcher: ABCBISearcher
    ) -> List[ABCBICompiledNode]:
        if self.computation_options.disabled:
            return []

        mapped_rule_arguments: MacroMapping = dict(
            zip(["$%s$" % x for x in self._params.arguments], extern_arguments)
        )

        action_results = []
        for bi_node in self.nodes:
            action_results.extend(bi_node.compile(mapped_rule_arguments, bi_searcher))

        if not action_results:
            return action_results

        return [self._generate_rule_branch(action_results, mapped_rule_arguments)]

    def _generate_rule_branch(
        self, nodes: List[ABCBICompiledNode], macros: MacroMapping
    ) -> ABCBICompiledNode:
        required_hosts = set()
        for node in nodes:
            required_hosts.update(node.required_hosts)

        bi_rule_result = BICompiledRule(
            self.id,
            self.pack_id,
            nodes,
            list(required_hosts),
            BIRuleProperties(self._properties_config),
            self.aggregation_function,
            self.node_visualization,
        )

        bi_rule_result.properties.title = replace_macros(bi_rule_result.properties.title, macros)
        return bi_rule_result

    @classmethod
    def create_tree_from_schema(cls, schema_config: Dict[str, Any]) -> BICompiledRule:
        rule_id = schema_config["id"]
        pack_id = schema_config["pack_id"]
        nodes = [cls._create_node(x) for x in schema_config["nodes"]]
        required_hosts = [(x["site_id"], x["host_name"]) for x in schema_config["required_hosts"]]
        properties = BIRuleProperties(schema_config["properties"])
        aggregation_function = bi_aggregation_function_registry.instantiate(
            schema_config["aggregation_function"]
        )
        node_visualization = schema_config["node_visualization"]

        return BICompiledRule(
            rule_id,
            pack_id,
            nodes,
            required_hosts,
            properties,
            aggregation_function,
            node_visualization,
        )

    @classmethod
    def _create_node(cls, node_config: Dict[str, Any]) -> ABCBICompiledNode:
        if node_config["type"] == BICompiledRule.type():
            return cls.create_tree_from_schema(node_config)
        if node_config["type"] == BICompiledLeaf.type():
            return BICompiledLeaf(**node_config)
        raise NotImplementedError("Unknown node type")


class BIRuleSchema(Schema):
    class Meta:
        ordered = True

    id = ReqString(
        dump_default="",
        example="rule1",
        description="TODO: Hier muß Andreas noch etwas reinschreiben!",
    )
    nodes = ReqList(
        fields.Nested(BINodeGeneratorSchema),
        dump_default=[],
        example=[],
        description="TODO: Hier muß Andreas noch etwas reinschreiben!",
    )
    params = create_nested_schema_for_class(
        BIParams,
        example_config={
            "arguments": ["foo", "bar"],
        },
    )
    node_visualization = create_nested_schema(
        BINodeVisLayoutStyleSchema, default_schema=BINodeVisBlockStyleSchema
    )
    properties = create_nested_schema_for_class(BIRuleProperties)
    aggregation_function = create_nested_schema(
        BIAggregationFunctionSchema, default_schema=BIAggregationFunctionBest.schema()
    )
    computation_options = create_nested_schema_for_class(BIRuleComputationOptions)
