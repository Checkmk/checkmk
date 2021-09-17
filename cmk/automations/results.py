#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from abc import ABC, abstractmethod
from ast import literal_eval
from dataclasses import astuple, dataclass
from typing import Type, TypeVar

from cmk.utils.plugin_registry import Registry
from cmk.utils.python_printer import pformat


class ResultTypeRegistry(Registry[Type["ABCAutomationResult"]]):
    def plugin_name(self, instance: Type["ABCAutomationResult"]) -> str:
        return instance.automation_call()


result_type_registry = ResultTypeRegistry()


class SerializedResult(str):
    ...


_DeserializedType = TypeVar("_DeserializedType", bound="ABCAutomationResult")


@dataclass  # type: ignore[misc]  # https://github.com/python/mypy/issues/5374
class ABCAutomationResult(ABC):
    def serialize(self) -> SerializedResult:
        return SerializedResult(pformat(astuple(self)))

    def to_pre_21(self) -> object:
        # Needed to support remote automation calls from an old central site to a new remote site.
        # In such cases, we must send the result in a format understood by the old central site.
        return astuple(self)[0]

    @classmethod
    def deserialize(
        cls: Type[_DeserializedType],
        serialized_result: SerializedResult,
    ) -> _DeserializedType:
        return cls(*literal_eval(serialized_result))

    @staticmethod
    @abstractmethod
    def automation_call() -> str:
        ...
