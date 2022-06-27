#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2020 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import abc
from typing import Any, Dict, List, Sequence, Type

import cmk.utils.plugin_registry
from cmk.utils.bi.bi_lib import (
    ABCBICompiledNode,
    ABCBISearcher,
    ABCWithSchema,
    ActionArgument,
    BIParams,
    ReqBoolean,
    ReqDict,
    ReqString,
)
from cmk.utils.bi.bi_node_generator_interface import ABCBINodeGenerator
from cmk.utils.bi.bi_schema import Schema


class BIRulePropertiesSchema(Schema):
    title = ReqString(dump_default="", example="Rule title")
    comment = ReqString(dump_default="", example="Rule comment")
    docu_url = ReqString(dump_default="", example="Rule documentation")
    icon = ReqString(dump_default="", example="icon1.png")
    state_messages = ReqDict(dump_default={}, example={})


class BIRuleProperties(ABCWithSchema):
    def __init__(self, properties_config: Dict[str, Any]) -> None:
        super().__init__()
        self.title = properties_config["title"]
        self.comment = properties_config["comment"]
        self.state_messages = properties_config["state_messages"]
        self.docu_url = properties_config["docu_url"]
        self.icon = properties_config["icon"]

    @classmethod
    def schema(cls) -> Type["BIRulePropertiesSchema"]:
        return BIRulePropertiesSchema

    def serialize(self):
        return {
            "title": self.title,
            "comment": self.comment,
            "docu_url": self.docu_url,
            "icon": self.icon,
            "state_messages": self.state_messages,
        }


class BIRuleComputationOptionsSchema(Schema):
    disabled = ReqBoolean(dump_default=False, example=False)


class BIRuleComputationOptions(ABCWithSchema):
    def __init__(self, computation_config: Dict[str, Any]) -> None:
        super().__init__()
        self.disabled = computation_config["disabled"]

    @classmethod
    def schema(cls) -> Type[BIRuleComputationOptionsSchema]:
        return BIRuleComputationOptionsSchema

    def serialize(self):
        return {
            "disabled": self.disabled,
        }


class ABCBIRule(ABCWithSchema):
    def __init__(self) -> None:
        self.id = ""

    @property
    @abc.abstractmethod
    def params(self) -> BIParams:
        raise NotImplementedError()

    @property
    @abc.abstractmethod
    def properties(self) -> BIRuleProperties:
        raise NotImplementedError()

    @property
    @abc.abstractmethod
    def title(self) -> str:
        raise NotImplementedError()

    @classmethod
    @abc.abstractmethod
    def schema(cls) -> Type[Schema]:
        raise NotImplementedError()

    @abc.abstractmethod
    def clone(self) -> "ABCBIRule":
        raise NotImplementedError()

    @abc.abstractmethod
    def get_nodes(self) -> Sequence[ABCBINodeGenerator]:
        raise NotImplementedError()

    @abc.abstractmethod
    def num_nodes(self) -> int:
        raise NotImplementedError()

    @abc.abstractmethod
    def compile(
        self, extern_arguments: ActionArgument, bi_searcher: ABCBISearcher
    ) -> List[ABCBICompiledNode]:
        raise NotImplementedError()

    @classmethod
    @abc.abstractmethod
    def create_tree_from_schema(cls, schema_config: Dict[str, Any]) -> Any:
        raise NotImplementedError()


class BIRuleIDRegistry(cmk.utils.plugin_registry.Registry[ABCBIRule]):
    def plugin_name(self, instance: ABCBIRule) -> str:
        return instance.id

    def clear(self):
        self._entries.clear()


bi_rule_id_registry = BIRuleIDRegistry()
