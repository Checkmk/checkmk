#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import astroid  # type: ignore[import]
from pylint.checkers import BaseChecker  # type: ignore[import]
from pylint.interfaces import IAstroidChecker  # type: ignore[import]


def register(linter) -> None:
    linter.register_checker(CollectionsNamedTupleChecker(linter))
    linter.register_checker(TypingNamedTupleChecker(linter))


class ForbiddenFunctionChecker(BaseChecker):
    __implements__ = IAstroidChecker
    name = "forbidden-function"
    target_function = ""
    target_lib = ""

    def __init__(self, linter) -> None:
        super().__init__(linter)
        self.was_imported = False
        self.function_name = self.target_function
        self.library_name = self.target_lib

    def visit_import(self, node: astroid.node_classes.Import) -> None:
        for library, alias in node.names:
            if library == self.target_lib or library.endswith("." + self.target_lib):
                self.library_name = alias or library

    def visit_importfrom(self, node: astroid.node_classes.ImportFrom) -> None:
        if node.modname == self.target_lib or node.modname.endswith("." + self.target_lib):
            for fct, alias in node.names:
                if fct == self.target_function:
                    self.was_imported = True
                    self.function_name = alias or self.target_function

    def _called_with_library(self, value: astroid.NodeNG) -> bool:
        if not isinstance(value, astroid.node_classes.Attribute):
            return False
        if isinstance(value.expr, astroid.node_classes.Name):
            return value.attrname == self.target_function and value.expr.name == self.library_name
        if isinstance(value.expr, astroid.node_classes.Attribute):
            return (
                value.attrname == self.target_function
                and value.expr.as_string() == self.library_name
            )
        return False

    def _called_directly(self, value: astroid.NodeNG) -> bool:
        return (
            isinstance(value, astroid.node_classes.Name)
            and value.name == self.function_name
            and self.was_imported
        )

    def visit_module(self, node: astroid.scoped_nodes.Module) -> None:
        self.was_imported = False

    def _visit_call(self, node: astroid.NodeNG) -> bool:
        if not isinstance(node, astroid.node_classes.Call):
            return False
        return self._called_with_library(node.func) or self._called_directly(node.func)

    def visit_call(self, node: astroid.node_classes.Call) -> None:
        if self._visit_call(node):
            self.add_message(self.name, node=node)


class TypingNamedTupleChecker(ForbiddenFunctionChecker):
    name = "typing-namedtuple-call"
    target_lib = "typing"
    target_function = "NamedTuple"
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
    target_function = "namedtuple"
    msgs = {
        "E8910": (
            "Called collections.namedtuple",
            "collections-namedtuple-call",
            "NamedTuples should be declared using inheritance",
        ),
    }
