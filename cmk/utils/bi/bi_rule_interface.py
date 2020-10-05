#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2020 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import abc
from marshmallow import Schema  # type: ignore[import]
from typing import List, Dict, Any, Type, Sequence
import cmk.utils.plugin_registry
from cmk.utils.bi.bi_lib import (
    ABCBICompiledNode,
    BIParams,
    ReqString,
    ReqBoolean,
    ReqDict,
    ABCWithSchema,
)

from cmk.utils.bi.bi_node_generator_interface import ABCBINodeGenerator


class BIRulePropertiesSchema(Schema):
    title = ReqString(default="", example="Rule title")
    comment = ReqString(default="", example="Rule comment")
    docu_url = ReqString(default="", example="Rule documentation")
    icon = ReqString(default="", example="icon1.png")
    state_messages = ReqDict(default={}, example={})


class BIRuleProperties(ABCWithSchema):
    def __init__(self, properties_config: Dict[str, Any]):
        super().__init__()
        self.title = properties_config["title"]
        self.comment = properties_config["comment"]
        self.state_messages = properties_config["state_messages"]
        self.docu_url = properties_config["docu_url"]
        self.icon = properties_config["icon"]

    @classmethod
    def schema(cls) -> Type["BIRulePropertiesSchema"]:
        return BIRulePropertiesSchema


class BIRuleComputationOptionsSchema(Schema):
    disabled = ReqBoolean(default=False, example=False)


class BIRuleComputationOptions(ABCWithSchema):
    def __init__(self, computation_config: Dict[str, Any]):
        super().__init__()
        self.disabled = computation_config["disabled"]

    @classmethod
    def schema(cls) -> Type[BIRuleComputationOptionsSchema]:
        return BIRuleComputationOptionsSchema


class ABCBIRule(ABCWithSchema):
    def __init__(self):
        self.id = ""

    @abc.abstractproperty
    def params(self) -> BIParams:
        raise NotImplementedError()

    @abc.abstractproperty
    def properties(self) -> BIRuleProperties:
        raise NotImplementedError()

    @abc.abstractproperty
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
    def compile(self, extern_arguments: List[str]) -> List[ABCBICompiledNode]:
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
