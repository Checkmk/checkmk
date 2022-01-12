#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from typing import FrozenSet, List

import astroid  # type: ignore[import]
from pylint.checkers import BaseChecker  # type: ignore[import]
from pylint.interfaces import IAstroidChecker  # type: ignore[import]


def register(linter) -> None:
    linter.register_checker(CollectionsNamedTupleChecker(linter))
    linter.register_checker(TypingNamedTupleChecker(linter))
    linter.register_checker(SixEnsureStrBinChecker(linter))
    linter.register_checker(ABCMetaChecker(linter))


class ForbiddenObjectChecker(BaseChecker):
    __implements__ = IAstroidChecker
    name = "forbidden-object"
    target_objects: FrozenSet[str] = frozenset([])
    target_lib = ""

    def __init__(self, linter) -> None:
        super().__init__(linter)
        self.was_imported = False
        self.object_names: List[str] = []
        self.library_name = self.target_lib

    def visit_import(self, node: astroid.node_classes.Import) -> None:
        for library, alias in node.names:
            if library == self.target_lib or library.endswith("." + self.target_lib):
                self.library_name = alias or library

    def visit_importfrom(self, node: astroid.node_classes.ImportFrom) -> None:
        if node.modname == self.target_lib or node.modname.endswith("." + self.target_lib):
            for obj, alias in node.names:
                if obj in self.target_objects:
                    self.was_imported = True
                    if alias:
                        self.object_names.append(alias)
                    else:
                        self.object_names.append(obj)

    def visit_module(self, node: astroid.scoped_nodes.Module) -> None:
        self.was_imported = False
        self.object_names.clear()


class ForbiddenFunctionChecker(ForbiddenObjectChecker):
    def _called_with_library(self, value: astroid.NodeNG) -> bool:
        if not isinstance(value, astroid.node_classes.Attribute):
            return False
        if isinstance(value.expr, astroid.node_classes.Name):
            return value.attrname in self.target_objects and value.expr.name == self.library_name
        if isinstance(value.expr, astroid.node_classes.Attribute):
            return (
                value.attrname in self.target_objects
                and value.expr.as_string() == self.library_name
            )
        return False

    def _called_directly(self, value: astroid.NodeNG) -> bool:
        return (
            isinstance(value, astroid.node_classes.Name)
            and value.name in self.object_names
            and self.was_imported
        )

    def _visit_call(self, node: astroid.NodeNG) -> bool:
        if not isinstance(node, astroid.node_classes.Call):
            return False
        return self._called_with_library(node.func) or self._called_directly(node.func)

    def visit_call(self, node: astroid.node_classes.Call) -> None:
        if self._visit_call(node):
            self.add_message(self.name, node=node)
        for arg in node.args:
            if self._called_with_library(arg) or self._called_directly(arg):
                self.add_message(self.name, node=arg)


class ForbiddenMetaclassChecker(ForbiddenObjectChecker):
    def visit_classdef(self, node: astroid.nodes.scoped_nodes.ClassDef) -> None:
        if self._visit_classdef(node):
            self.add_message(self.name, node=node)

    def _visit_classdef(self, node: astroid.nodes.scoped_nodes.ClassDef) -> bool:
        return (
            node.declared_metaclass() is not None
            and node.declared_metaclass().name in self.target_objects
        )


class TypingNamedTupleChecker(ForbiddenFunctionChecker):
    name = "typing-namedtuple-call"
    target_lib = "typing"
    target_objects = frozenset(["NamedTuple"])
    msgs = {
        "E9010": (
            "Called typing.NamedTuple",
            "typing-namedtuple-call",
            "NamedTuples should be declared using inheritance",
        ),
    }


class CollectionsNamedTupleChecker(ForbiddenFunctionChecker):
    name = "collections-namedtuple-call"
    target_lib = "collections"
    target_objects = frozenset(["namedtuple"])
    msgs = {
        "E8910": (
            "Called collections.namedtuple",
            "collections-namedtuple-call",
            "NamedTuples should be declared using inheritance",
        ),
    }


class SixEnsureStrBinChecker(ForbiddenFunctionChecker):
    name = "six-ensure-str-bin-call"
    target_lib = "six"
    target_objects = frozenset(["ensure_str", "ensure_binary"])
    msgs = {
        "E9110": (
            "Called six.ensure_str or six.ensure_binary",
            "six-ensure-str-bin-call",
            "six.ensure_str and six.ensure_binary should not be used",
        )
    }


class ABCMetaChecker(ForbiddenMetaclassChecker):
    name = "abcmeta-metaclass"
    target_lib = "abc"
    target_objects = frozenset(["ABCMeta"])
    msgs = {
        "E9210": (
            "ABCMeta is used for metaclass argument",
            "abcmeta-metaclass",
            "Inheritance from ABC should be used instead to define metaclass",
        )
    }
