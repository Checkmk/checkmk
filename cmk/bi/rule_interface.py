#!/usr/bin/env python3
# Copyright (C) 2020 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from abc import abstractmethod
from collections.abc import Sequence
from typing import Any, override

from cmk.bi.fields import ReqBoolean, ReqDict, ReqString
from cmk.bi.lib import ABCBICompiledNode, ABCBISearcher, ABCWithSchema, BIParams
from cmk.bi.node_generator_interface import ABCBINodeGenerator
from cmk.bi.schema import Schema
from cmk.bi.type_defs import ActionArgument
from cmk.ccc.plugin_registry import Registry


class BIRulePropertiesSchema(Schema):
    title = ReqString(dump_default="", example="Rule title", description="Title of the rule.")
    comment = ReqString(dump_default="", example="Rule comment", description="Rule comment.")
    docu_url = ReqString(
        dump_default="", example="Rule documentation", description="URL to more documentation."
    )
    icon = ReqString(dump_default="", example="icon1.png", description="Icon name for the rule.")
    state_messages = ReqDict(dump_default={}, example={}, description="State messages.")


class BIRuleProperties(ABCWithSchema):
    def __init__(self, properties_config: dict[str, Any]) -> None:
        super().__init__()
        self.title = properties_config["title"]
        self.comment = properties_config["comment"]
        self.state_messages = properties_config["state_messages"]
        self.docu_url = properties_config["docu_url"]
        self.icon = properties_config["icon"]

    @override
    @classmethod
    def schema(cls) -> type["BIRulePropertiesSchema"]:
        return BIRulePropertiesSchema

    def serialize(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "comment": self.comment,
            "docu_url": self.docu_url,
            "icon": self.icon,
            "state_messages": self.state_messages,
        }


class BIRuleComputationOptionsSchema(Schema):
    disabled = ReqBoolean(
        dump_default=False, example=False, description="Enable or disable this computation option."
    )


class BIRuleComputationOptions(ABCWithSchema):
    def __init__(self, computation_config: dict[str, Any]) -> None:
        super().__init__()
        self.disabled = computation_config["disabled"]

    @override
    @classmethod
    def schema(cls) -> type[BIRuleComputationOptionsSchema]:
        return BIRuleComputationOptionsSchema

    def serialize(self) -> dict[str, Any]:
        return {
            "disabled": self.disabled,
        }


class ABCBIRule(ABCWithSchema):
    def __init__(self) -> None:
        self.id = ""

    @property
    @abstractmethod
    def params(self) -> BIParams:
        raise NotImplementedError()

    @property
    @abstractmethod
    def properties(self) -> BIRuleProperties:
        raise NotImplementedError()

    @property
    @abstractmethod
    def title(self) -> str:
        raise NotImplementedError()

    @override
    @classmethod
    @abstractmethod
    def schema(cls) -> type[Schema]:
        raise NotImplementedError()

    @abstractmethod
    def clone(self, existing_rule_ids: Sequence[str]) -> "ABCBIRule":
        raise NotImplementedError()

    @abstractmethod
    def get_nodes(self) -> Sequence[ABCBINodeGenerator]:
        raise NotImplementedError()

    @abstractmethod
    def num_nodes(self) -> int:
        raise NotImplementedError()

    @abstractmethod
    def compile(
        self, extern_arguments: ActionArgument, bi_searcher: ABCBISearcher
    ) -> list[ABCBICompiledNode]:
        raise NotImplementedError()

    @classmethod
    @abstractmethod
    def create_tree_from_schema(cls, schema_config: dict[str, Any]) -> Any:
        raise NotImplementedError()


class BIRuleIDRegistry(Registry[ABCBIRule]):
    @override
    def plugin_name(self, instance: ABCBIRule) -> str:
        return instance.id

    @override
    def clear(self) -> None:
        self._entries.clear()


bi_rule_id_registry = BIRuleIDRegistry()
