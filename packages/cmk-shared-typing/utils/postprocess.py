#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import override

import libcst as cst
import libcst.matchers as m
from black import FileMode, format_str

# Codegen ignores the required flag if default is set
STRIP_OPTIONAL = [
    ("FormSpec", "validators"),
    ("Dictionary", "elements"),
    ("Dictionary", "layout"),
    ("SingleChoice", "elements"),
    ("MultipleChoice", "elements"),
    ("MultipleChoice", "show_toggle_all"),
    ("CascadingSingleChoice", "elements"),
    ("CascadingSingleChoice", "layout"),
    ("Tuple", "layout"),
]


class EnumString(cst.CSTTransformer):
    @override
    def leave_ClassDef(
        self, original_node: cst.ClassDef, updated_node: cst.ClassDef
    ) -> cst.ClassDef:
        if len(updated_node.bases) == 1:
            expression = updated_node.bases[0].value
            if isinstance(expression, cst.Name) and expression.value == "Enum":
                return updated_node.with_changes(
                    bases=[cst.Arg(value=cst.Name(value="str"))] + list(updated_node.bases)
                )
        return updated_node


# Str-enum members shadowing a str method trip mypy's assignment check
SHADOWING_ENUM_MEMBERS = ["count"]


class ShadowingEnumMemberIgnorer(cst.CSTTransformer):
    @override
    def leave_ClassDef(
        self, original_node: cst.ClassDef, updated_node: cst.ClassDef
    ) -> cst.ClassDef:
        base_names = [
            base.value.value for base in updated_node.bases if isinstance(base.value, cst.Name)
        ]
        if base_names not in (["StrEnum"], ["str", "Enum"]) or not isinstance(
            updated_node.body, cst.IndentedBlock
        ):
            return updated_node
        return updated_node.with_changes(
            body=updated_node.body.with_changes(
                body=[self._member_with_ignore(statement) for statement in updated_node.body.body]
            )
        )

    @staticmethod
    def _member_with_ignore(statement: cst.BaseStatement) -> cst.BaseStatement:
        if not (
            isinstance(statement, cst.SimpleStatementLine)
            and len(statement.body) == 1
            and isinstance(assign := statement.body[0], cst.Assign)
            and len(assign.targets) == 1
            and isinstance(target := assign.targets[0].target, cst.Name)
            and target.value in SHADOWING_ENUM_MEMBERS
        ):
            return statement
        return statement.with_changes(
            trailing_whitespace=cst.TrailingWhitespace(
                whitespace=cst.SimpleWhitespace("  "),
                comment=cst.Comment("# type: ignore[assignment]"),
            )
        )


class OptionalRemover(cst.CSTTransformer):
    def __init__(self) -> None:
        self.current_class: str | None = None

    @override
    def visit_ClassDef(self, node: cst.ClassDef) -> None:
        self.current_class = node.name.value

    @override
    def leave_ClassDef(
        self, original_node: cst.ClassDef, updated_node: cst.ClassDef
    ) -> cst.ClassDef:
        self.current_class = None
        return updated_node

    @override
    def leave_AnnAssign(
        self, original_node: cst.AnnAssign, updated_node: cst.AnnAssign
    ) -> cst.AnnAssign:
        for class_name, member_name in STRIP_OPTIONAL:
            if self.current_class == class_name and m.matches(
                updated_node.target, m.Name(member_name)
            ):
                subscript = updated_node.annotation.annotation
                assert isinstance(subscript, cst.Subscript)
                if m.matches(subscript.value, m.Name("Optional")):
                    index = subscript.slice[0].slice
                    assert isinstance(index, cst.Index)
                    return updated_node.with_changes(annotation=cst.Annotation(index.value))
        return updated_node


def postprocess(code: str) -> str:
    tree = cst.parse_module(code)
    for transformer in (OptionalRemover(), EnumString(), ShadowingEnumMemberIgnorer()):
        tree = tree.visit(transformer)
    return format_str(tree.code, mode=FileMode())
