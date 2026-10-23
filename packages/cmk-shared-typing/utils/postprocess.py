#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import override

import libcst as cst
from black import FileMode, format_str


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


def postprocess(code: str) -> str:
    tree = cst.parse_module(code).visit(EnumString())
    return format_str(tree.code, mode=FileMode())
