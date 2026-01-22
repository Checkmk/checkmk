#!/usr/bin/env python3
# Copyright (C) 2020 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-any-return"
# mypy: disable-error-code="no-untyped-call"

#   .--Rule----------------------------------------------------------------.
#   |                         ____        _                                |
#   |                        |  _ \ _   _| | ___                           |
#   |                        | |_) | | | | |/ _ \                          |
#   |                        |  _ <| |_| | |  __/                          |
#   |                        |_| \_\\__,_|_|\___|                          |
#   |                                                                      |
#   +----------------------------------------------------------------------+

from collections import OrderedDict
from collections.abc import Mapping, Sequence
from typing import Any, override

from cmk import fields
from cmk.bi.aggregation_functions import BIAggregationFunctionBest, BIAggregationFunctionSchema
from cmk.bi.fields import ReqList, ReqString
from cmk.bi.lib import (
    ABCBICompiledNode,
    ABCBISearcher,
    ABCWithSchema,
    bi_aggregation_function_registry,
    BIParams,
    create_nested_schema,
    create_nested_schema_for_class,
    get_schema_default_config,
    replace_macros,
)
from cmk.bi.node_generator import BINodeGenerator, BINodeGeneratorSchema
from cmk.bi.node_vis import BINodeVisBlockStyleSchema, BINodeVisLayoutStyleSchema
from cmk.bi.rule_interface import (
    ABCBIRule,
    bi_rule_id_registry,
    BIRuleComputationOptions,
    BIRuleProperties,
)
from cmk.bi.schema import Schema
from cmk.bi.trees import BICompiledLeaf, BICompiledRule
from cmk.bi.type_defs import ActionArgument


class BIRule(ABCBIRule, ABCWithSchema):
    def __init__(self, rule_config: dict[str, Any] | None = None, pack_id: str = "") -> None:
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

        self.nodes = [BINodeGenerator(node) for node in rule_config["nodes"]]
        bi_rule_id_registry.register(self)

    @property
    @override
    def properties(self) -> BIRuleProperties:
        return self._properties

    @property
    @override
    def params(self) -> BIParams:
        return self._params

    @property
    @override
    def title(self) -> str:
        return self.properties.title

    @classmethod
    @override
    def schema(cls) -> type["BIRuleSchema"]:
        return BIRuleSchema

    def serialize(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "nodes": [node.serialize() for node in self.nodes],
            "params": self.params.serialize(),
            "node_visualization": self.node_visualization,
            "properties": self.properties.serialize(),
            "aggregation_function": self.aggregation_function.serialize(),
            "computation_options": self.computation_options.serialize(),
        }

    @override
    def clone(self, existing_rule_ids: Sequence[str]) -> "BIRule":
        def get_clone_id(cloned_rule_id: str, existing_rule_ids: Sequence[str]) -> str:
            for index in range(1, len(existing_rule_ids) + 2):
                new_id = f"{cloned_rule_id}_clone{index}"
                if new_id not in existing_rule_ids:
                    return new_id
            raise ValueError("Could not find a unique clone id")

        rule_config = self.schema()().dump(self)
        rule_config["id"] = get_clone_id(rule_config["id"], existing_rule_ids)
        return BIRule(rule_config)

    @override
    def get_nodes(self) -> Sequence[BINodeGenerator]:
        return self.nodes

    @override
    def num_nodes(self) -> int:
        return len(self.nodes)

    @override
    def compile(
        self, extern_arguments: ActionArgument, bi_searcher: ABCBISearcher
    ) -> list[ABCBICompiledNode]:
        if self.computation_options.disabled:
            return []

        mapped_rule_arguments: Mapping[str, str] = dict(
            zip([f"${arg}$" for arg in self._params.arguments], extern_arguments)
        )

        action_results = []
        for bi_node in self.nodes:
            action_results.extend(bi_node.compile(mapped_rule_arguments, bi_searcher))

        if not action_results:
            return action_results

        return [self._generate_rule_branch(action_results, mapped_rule_arguments)]

    def _generate_rule_branch(
        self, nodes: list[ABCBICompiledNode], macros: Mapping[str, str]
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

    @override
    @classmethod
    def create_tree_from_schema(cls, schema_config: dict[str, Any]) -> BICompiledRule:
        rule_id = schema_config["id"]
        pack_id = schema_config["pack_id"]
        nodes = [cls._create_node(node) for node in schema_config["nodes"]]
        required_hosts = [
            (required_host["site_id"], required_host["host_name"])
            for required_host in schema_config["required_hosts"]
        ]
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
    def _create_node(cls, node_config: dict[str, Any]) -> ABCBICompiledNode:
        if node_config["type"] == BICompiledRule.kind():
            return cls.create_tree_from_schema(node_config)
        if node_config["type"] == BICompiledLeaf.kind():
            return BICompiledLeaf(**node_config)
        raise NotImplementedError("Unknown node type")


class BIRuleSchema(Schema):
    @property
    @override
    def dict_class(self) -> type:
        return OrderedDict

    id = ReqString(
        dump_default="",
        example="rule1",
        description="The unique rule id",
    )
    nodes = ReqList(
        fields.Nested(BINodeGeneratorSchema),
        dump_default=[],
        example=[],
        description="A list of nodes for for this rule",
    )
    params = create_nested_schema_for_class(
        BIParams,
        example_config={
            "arguments": ["foo", "bar"],
        },
        description="Parameters.",
    )
    node_visualization = create_nested_schema(
        BINodeVisLayoutStyleSchema,
        default_schema=BINodeVisBlockStyleSchema,
        description="Node visualization.",
    )
    properties = create_nested_schema_for_class(BIRuleProperties, description="Rule properties.")
    aggregation_function = create_nested_schema(
        BIAggregationFunctionSchema,
        default_schema=BIAggregationFunctionBest.schema(),
        description="Aggregation function.",
    )
    computation_options = create_nested_schema_for_class(
        BIRuleComputationOptions, description="Computation options."
    )
