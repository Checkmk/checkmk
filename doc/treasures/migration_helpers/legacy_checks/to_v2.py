#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Migrate legacy checks.

This tool will modify legacy check plug-ins in place, to make them use the API `cmk.agent_based.v2`.
It requires you to install the python library `libcst`.
It does not require, but will attempt to call `scripts/run-uvenv` on the modified file(s).
For very simple plugins, it might do the whole job, for most it will not.

It's a quick and dirty, untested hacky thing.
"""

import argparse
import subprocess
import sys
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path
from typing import Final, Literal

import libcst as cst

# just add whatever we might need, we'll remove the unused ones later
_ADDED_IMPORTS = (
    "from collections.abc import Iterable, Mapping",
    "from typing import Any",
    (
        "from cmk.agent_based.legacy.conversion import (\n"
        "    # Temporary compatibility layer untile we migrate the corresponding ruleset.\n"
        "    check_levels_legacy_compatible as check_levels,\n"
        ")"
    ),
    (
        "from cmk.agent_based.v2 import Service, DiscoveryResult, CheckResult,"
        " Result, State, Metric, AgentSection, SNMPSection, SimpleSNMPSection, CheckPlugin"
    ),
)

_REMOVED = (
    "\ncheck_info = {}\n",
)


def _is_service(expr: cst.BaseExpression) -> bool:
    """is this expression "Service(...)"?"""
    return (
        isinstance(expr, cst.Call)
        and isinstance(expr.func, cst.Name)
        and expr.func.value == "Service"
    )


def _make_service(
    item: cst.BaseElement,
    params: cst.BaseElement,
) -> cst.Call:
    assert not (isinstance(item.value, cst.SimpleString) and item.value.value in {"''", '""'})
    item_is_none = isinstance(item.value, cst.Name) and item.value.value == "None"
    params_are_falsey = (isinstance(params.value, cst.Dict) and not params.value.elements) or (
        isinstance(params.value, cst.Name) and params.value.value == "None"
    )
    return cst.Call(
        func=cst.Name("Service"),
        args=[
            *(() if item_is_none else (cst.Arg(value=item.value, keyword=cst.Name("item")),)),
            *(
                ()
                if params_are_falsey
                else (cst.Arg(value=params.value, keyword=cst.Name("parameters")),)
            ),
        ],
    )


def _make_state(value: cst.BaseExpression) -> cst.BaseExpression:
    if isinstance(value, cst.Integer):
        match value.value:
            case "0":
                return cst.parse_expression("State.OK")
            case "1":
                return cst.parse_expression("State.WARN")
            case "2":
                return cst.parse_expression("State.CRIT")
            case "3":
                return cst.parse_expression("State.UNKNOWN")
            case _:
                return value
    return value


def _make_result(
    state: cst.BaseElement,
    text: cst.BaseElement,
) -> cst.Call:
    return cst.Call(
        func=cst.Name("Result"),
        args=[
            cst.Arg(value=_make_state(state.value), keyword=cst.Name("state")),
            cst.Arg(value=text.value, keyword=cst.Name("summary")),
        ],
    )


def _make_metrics(metric_list: cst.BaseExpression) -> Iterable[cst.Call | cst.From | cst.Name]:
    match metric_list:
        case cst.List():
            for e in metric_list.elements:
                yield _make_single_metric(e.value)
        case cst.Name():
            yield cst.From(metric_list)
        case other:
            raise NotImplementedError(other)


def _make_single_metric(element: cst.BaseExpression) -> cst.Call | cst.Name:
    def _make_levels_kwarg(w: cst.BaseExpression, c: cst.BaseExpression) -> Iterable[cst.Arg]:
        if (
            isinstance(w, cst.Name)
            and w.value == "None"
            and isinstance(c, cst.Name)
            and c.value == "None"
        ):
            return
        yield cst.Arg(cst.Tuple((cst.Element(w), cst.Element(c))), keyword=cst.Name("levels"))

    match element:
        case cst.Name():
            return element
        case cst.Tuple():
            match element.elements:
                case (name, value) | (name, value, object()):
                    return cst.Call(
                        cst.Name("Metric"), args=[cst.Arg(name.value), cst.Arg(value.value)]
                    )
                case name, value, warn, crit:
                    return cst.Call(
                        cst.Name("Metric"),
                        args=[
                            cst.Arg(name.value),
                            cst.Arg(value.value),
                            *_make_levels_kwarg(warn.value, crit.value),
                        ],
                    )
                case name, value, warn, crit, min_:
                    return cst.Call(
                        cst.Name("Metric"),
                        args=[
                            cst.Arg(name.value),
                            cst.Arg(value.value),
                            *_make_levels_kwarg(warn.value, crit.value),
                            cst.Arg(
                                cst.Tuple((min_, cst.Element(cst.Name("None")))),
                                keyword=cst.Name("boundaries"),
                            ),
                        ],
                    )
                case name, value, warn, crit, min_, max_:
                    return cst.Call(
                        cst.Name("Metric"),
                        args=[
                            cst.Arg(name.value),
                            cst.Arg(value.value),
                            *_make_levels_kwarg(warn.value, crit.value),
                            cst.Arg(cst.Tuple((min_, max_)), keyword=cst.Name("boundaries")),
                        ],
                    )
    raise NotImplementedError(element)


def _make_results_and_metrics(tpl: cst.Tuple) -> Iterable[cst.Call | cst.Name | cst.From]:
    if len(tpl.elements) < 2:
        return
    yield _make_result(tpl.elements[0], tpl.elements[1])
    if len(tpl.elements) <= 2:
        return
    yield from _make_metrics(tpl.elements[2].value)


class ImportsTransformer(cst.CSTTransformer):
    def __init__(self) -> None:
        super().__init__()
        self.added_import = False

    def leave_ImportFrom(
        self, original_node: cst.ImportFrom, updated_node: cst.ImportFrom
    ) -> cst.ImportFrom | cst.RemovalSentinel:
        """Remove imports from cmk.agent_based.legacy.v0_unstable"""
        if updated_node.module is None:
            return updated_node

        # Build the full module path
        module_parts = list[str]()
        current: object = updated_node.module
        while current:
            if isinstance(current, cst.Attribute):
                if isinstance(current.attr, cst.Name):
                    module_parts.insert(0, current.attr.value)
                current = current.value
            elif isinstance(current, cst.Name):
                module_parts.insert(0, current.value)
                break
            else:
                break

        module_path = ".".join(module_parts)
        if module_path == "cmk.agent_based.legacy.v0_unstable":
            return cst.RemovalSentinel.REMOVE

        return updated_node

    def leave_SimpleStatementLine(
        self, original_node: cst.SimpleStatementLine, updated_node: cst.SimpleStatementLine
    ) -> cst.SimpleStatementLine | cst.FlattenSentinel | cst.RemovalSentinel:
        if not self.added_import:
            self.added_import = True
            return cst.FlattenSentinel(
                [
                    *(cst.parse_statement(statement) for statement in _ADDED_IMPORTS),
                    updated_node,
                ]
            )
        return updated_node


class DiscoveryTransformer(cst.CSTTransformer):
    def __init__(self, check_defs: Mapping[str, Mapping[str, cst.BaseExpression]]) -> None:
        super().__init__()
        self.functions_to_transform: Final = {
            df.value
            for node in check_defs.values()
            if isinstance((df := node.get("discovery_function")), cst.Name)
        }
        self.rename: str | None = None

    def leave_SimpleStatementLine(
        self, original_node: cst.SimpleStatementLine, updated_node: cst.SimpleStatementLine
    ) -> cst.SimpleStatementLine | cst.FlattenSentinel | cst.RemovalSentinel:
        if not isinstance((retrn := updated_node.body[0]), cst.Return):
            return updated_node

        match retrn.value:
            case None:
                return updated_node

            case cst.Name() | cst.Call() as node:
                item = cst.Element(cst.Name("item"))
                parm = cst.Element(cst.Name("parameters"))
                return updated_node.with_changes(
                    body=[
                        cst.Expr(
                            cst.Yield(
                                cst.From(
                                    cst.ListComp(
                                        elt=_make_service(item, parm),
                                        for_in=cst.CompFor(
                                            target=cst.Tuple(elements=[item, parm]),
                                            iter=node,
                                        ),
                                    )
                                )
                            )
                        )
                    ],
                )

            case cst.List() as lst:
                if len(lst.elements) == 1:
                    tpl = cst.ensure_type(lst.elements[0].value, cst.Tuple)
                    return updated_node.with_changes(
                        body=[
                            cst.Expr(
                                cst.Yield(
                                    _make_service(
                                        tpl.elements[0],
                                        tpl.elements[1],
                                    )
                                )
                            )
                        ]
                    )
                if not lst.elements:
                    return cst.RemoveFromParent()

            case cst.ListComp() as lcomp:
                match lcomp.elt:
                    case cst.Tuple() as tpl:
                        return updated_node.with_changes(
                            body=[
                                cst.Expr(
                                    cst.Yield(
                                        cst.From(
                                            item=lcomp.with_changes(
                                                elt=_make_service(
                                                    tpl.elements[0],
                                                    tpl.elements[1],
                                                )
                                            )
                                        ),
                                    )
                                ),
                            ],
                        )
                    case other:
                        raise NotImplementedError(other)

        raise NotImplementedError(retrn.value)

    def visit_FunctionDef(self, node: cst.FunctionDef) -> bool:
        if node.name.value in self.functions_to_transform:
            self.rename = node.params.params[0].name.value
            return True
        return False

    def leave_FunctionDef(
        self, original_node: cst.FunctionDef, updated_node: cst.FunctionDef
    ) -> cst.FunctionDef:
        self.rename = None
        if updated_node.name.value not in self.functions_to_transform:
            return updated_node

        fst_arg = cst.ensure_type(updated_node.params.params[0], cst.Param)

        new_node = updated_node.with_changes(
            returns=cst.Annotation(cst.Name("DiscoveryResult")),
            params=updated_node.params.with_changes(
                params=[
                    fst_arg.with_changes(name=cst.Name("section")),
                    *updated_node.params.params[1:],
                ]
            ),
        )
        return (
            new_node
            if updated_node.params.params[0].annotation is not None
            else new_node.with_changes(
                body=updated_node.body.with_changes(
                    header=cst.TrailingWhitespace(
                        whitespace=cst.SimpleWhitespace(value=" "),
                        comment=cst.Comment("# type: ignore[no-untyped-def]"),
                        newline=cst.Newline(value=None),
                    ),
                ),
            )
        )

    def leave_Yield(self, original_node: cst.Yield, updated_node: cst.Yield) -> cst.Yield:
        match updated_node.value:
            case cst.Tuple() as tpl:
                return cst.Yield(
                    value=_make_service(tpl.elements[0], tpl.elements[1]),
                )
            case cst.Call() as cll:
                if _is_service(cll):
                    return updated_node
            case cst.From() as frm:
                match frm.item:
                    case cst.ListComp() | cst.GeneratorExp():
                        if _is_service(frm.item.elt):
                            return updated_node
                        tpl = cst.ensure_type(frm.item.elt, cst.Tuple)
                        return updated_node.with_changes(
                            value=updated_node.value.with_changes(
                                item=updated_node.value.item.with_changes(
                                    elt=_make_service(tpl.elements[0], tpl.elements[1])
                                )
                            )
                        )
                    case cst.Name() | cst.Call() as node:
                        item = cst.Element(cst.Name("item"))
                        parm = cst.Element(cst.Name("parameters"))
                        return updated_node.with_changes(
                            value=cst.From(
                                cst.GeneratorExp(
                                    elt=_make_service(item, parm),
                                    for_in=cst.CompFor(
                                        target=cst.Tuple(elements=[item, parm]),
                                        iter=node,
                                    ),
                                )
                            )
                        )

        raise NotImplementedError(updated_node.value)

    def leave_Name(self, original_node: cst.Name, updated_node: cst.Name) -> cst.Name:
        if self.rename == updated_node.value:
            return cst.Name("section")
        return updated_node


class SectionTypeCollector(cst.CSTTransformer):
    def __init__(self, check_defs: Mapping[str, Mapping[str, cst.BaseExpression]]) -> None:
        super().__init__()
        self.parse_functions: Final = {
            pf.value: name
            for name, node in check_defs.items()
            if isinstance((pf := node.get("parse_function")), cst.Name)
        }
        self.section_types: dict[str, cst.Annotation] = {}

    def visit_FunctionDef(self, node: cst.FunctionDef) -> Literal[False]:
        if (section_name := self.parse_functions.get(node.name.value)) is None:
            return False

        if node.returns is None:
            return False

        match node.returns.annotation:
            case None:
                pass
            case cst.BinaryOperation() as bop:
                if isinstance(bop.left, cst.Name) and bop.left.value == "None":
                    self.section_types[section_name] = cst.Annotation(bop.right)
                if isinstance(bop.right, cst.Name) and bop.right.value == "None":
                    self.section_types[section_name] = cst.Annotation(bop.left)
            case _other:
                self.section_types[section_name] = node.returns
        return False


class SignatureTransformer(cst.CSTTransformer):
    def __init__(
        self,
        check_defs: Mapping[str, Mapping[str, cst.BaseExpression]],
        section_types: Mapping[str, cst.Annotation],
    ) -> None:
        super().__init__()
        self.discovery_functions: Final = {
            cf.value: name
            for name, node in check_defs.items()
            if isinstance((cf := node.get("discovery_function")), cst.Name)
        }
        self.check_functions: Final = {
            cf.value: name
            for name, node in check_defs.items()
            if isinstance((cf := node.get("check_function")), cst.Name)
        }
        self._d_or_c_functions = self.discovery_functions | self.check_functions
        self.section_types = section_types
        self.renames: list[dict[str, str]] = [{}]

    def visit_FunctionDef(self, node: cst.FunctionDef) -> bool:
        if node.name.value in self._d_or_c_functions:
            arg_names = {p.name.value for p in node.params.params}
            self.renames.append(
                {"info": "section"} if "info" in arg_names else {"parsed": "section"}
            )
            return True
        self.renames.append({})
        return False

    def _get_section_type(self, func_name: str) -> cst.Annotation:
        try:
            return self.section_types[self._d_or_c_functions[func_name].split(".")[0]]
        except KeyError:
            return cst.Annotation(cst.parse_expression("Any"))

    def leave_FunctionDef(
        self, original_node: cst.FunctionDef, updated_node: cst.FunctionDef
    ) -> cst.FunctionDef:
        self.renames.pop()
        func_name = updated_node.name.value
        if func_name not in self._d_or_c_functions:
            return updated_node

        section_annotation = self._get_section_type(func_name)

        if func_name in self.discovery_functions:
            fst_arg = cst.ensure_type(updated_node.params.params[0], cst.Param)
            return updated_node.with_changes(
                params=updated_node.params.with_changes(
                    params=[
                        fst_arg.with_changes(annotation=fst_arg.annotation or section_annotation),
                        *updated_node.params.params[1:],
                    ]
                ),
                returns=updated_node.returns
                or cst.Annotation(cst.parse_expression("DiscoveryResult")),
            )

        item_param = [
            p.with_changes(annotation=cst.Annotation(cst.parse_expression("str")))
            for p in updated_node.params.params
            if p.name.value == "item"
        ]
        params_param = [
            p.with_changes(
                annotation=p.annotation or cst.Annotation(cst.parse_expression("Mapping[str, Any]"))
            )
            for p in updated_node.params.params
            if p.name.value == "params"
        ]
        section_param = [
            p.with_changes(annotation=p.annotation or section_annotation)
            for p in updated_node.params.params
            if p.name.value == "section"
        ]
        return updated_node.with_changes(
            params=updated_node.params.with_changes(
                params=item_param + params_param + section_param
            ),
            returns=updated_node.returns or cst.Annotation(cst.parse_expression("CheckResult")),
        )

    def leave_Name(self, original_node: cst.Name, updated_node: cst.Name) -> cst.BaseExpression:
        try:
            return updated_node.with_changes(value=self.renames[-1][updated_node.value])
        except KeyError:
            return updated_node


class CheckTransformer(cst.CSTTransformer):
    def __init__(self, check_defs: Mapping[str, Mapping[str, cst.BaseExpression]]) -> None:
        super().__init__()
        self.functions_to_transform: Final = {
            cf.value
            for node in check_defs.values()
            if isinstance((cf := node.get("check_function")), cst.Name)
        }
        self.rename: str | None = None

    def leave_SimpleStatementLine(
        self, original_node: cst.SimpleStatementLine, updated_node: cst.SimpleStatementLine
    ) -> cst.SimpleStatementLine | cst.FlattenSentinel | cst.RemovalSentinel:
        if not isinstance((retrn := updated_node.body[0]), cst.Return):
            return updated_node

        match retrn.value:
            case None:
                return updated_node

            case cst.Name() as node if node.value == "None":
                return updated_node

            case cst.Name() | cst.Call() as node:
                return updated_node.with_changes(
                    body=[cst.Expr(cst.Yield(cst.From(node)))],
                )

            case cst.Tuple() as tpl:
                return cst.FlattenSentinel(
                    [
                        updated_node.with_changes(
                            body=[
                                cst.Expr(cst.Yield(new)) for new in _make_results_and_metrics(tpl)
                            ]
                        ),
                        cst.parse_statement("return"),
                    ]
                )

        return updated_node

    def visit_FunctionDef(self, node: cst.FunctionDef) -> bool:
        if node.name.value in self.functions_to_transform:
            return True
        return False

    def leave_FunctionDef(
        self, original_node: cst.FunctionDef, updated_node: cst.FunctionDef
    ) -> cst.FunctionDef:
        self.rename = None
        if updated_node.name.value not in self.functions_to_transform:
            return updated_node

        new_node = updated_node.with_changes(
            returns=cst.Annotation(cst.Name("CheckResult")),
            params=updated_node.params.with_changes(
                params=[
                    # fst_arg.with_changes(name=cst.Name("section")),
                    # *updated_node.params.params[1:],
                    *updated_node.params.params,
                ]
            ),
        )
        return (
            new_node
            if updated_node.params.params[0].annotation is not None
            else new_node.with_changes(
                body=updated_node.body.with_changes(
                    header=cst.TrailingWhitespace(
                        whitespace=cst.SimpleWhitespace(value=" "),
                        comment=cst.Comment("# type: ignore[no-untyped-def]"),
                        newline=cst.Newline(value=None),
                    ),
                ),
            )
        )

    def leave_Yield(self, original_node: cst.Yield, updated_node: cst.Yield) -> cst.Yield:
        match updated_node.value:
            case cst.Tuple() as tpl if len(tpl.elements) == 2:
                return cst.Yield(
                    value=_make_result(tpl.elements[0], tpl.elements[1]),
                )

        return updated_node

    def leave_Name(self, original_node: cst.Name, updated_node: cst.Name) -> cst.Name:
        if self.rename == updated_node.value:
            return cst.Name("section")
        return updated_node


class RegistrationTransformer(cst.CSTTransformer):
    def __init__(self, check_defs: Mapping[str, Mapping[str, cst.BaseExpression]]) -> None:
        super().__init__()
        self.check_defs = check_defs
        self.section_kwargs = ("detect", "fetch", "parse_function")

    def leave_SimpleStatementLine(
        self, original_node: cst.SimpleStatementLine, updated_node: cst.SimpleStatementLine
    ) -> cst.SimpleStatementLine | cst.FlattenSentinel:
        if not (
            # lhs
            isinstance(assign := original_node.body[0], cst.Assign)
            and isinstance(atarget := assign.targets[0], cst.AssignTarget)
            and isinstance(sub := atarget.target, cst.Subscript)
            and isinstance(subi := sub.slice[0], cst.SubscriptElement)
            and isinstance(subii := subi.slice, cst.Index)
            and isinstance(value := subii.value, cst.SimpleString)
            # rhs
            and isinstance(rhs := assign.value, cst.Call)
            and isinstance(constr := rhs.func, cst.Name)
            and constr.value == "LegacyCheckDefinition"
        ):
            return updated_node

        plugin_name = value.value.strip('"')
        return cst.FlattenSentinel(
            [
                *self._make_section_plugin(plugin_name),
                *self._make_check_plugin(plugin_name),
            ]
        )

    def _make_section_plugin(self, plugin_name: str) -> Iterable[cst.SimpleStatementLine]:
        kwargs = self.check_defs[plugin_name]
        if "parse_function" not in kwargs:
            return

        section_name = plugin_name.split(".")[0]

        prefix = "snmp_section_" if "detect" in kwargs else "agent_section_"
        match kwargs.get("fetch"):
            case None:
                type_ = "AgentSection"
            case cst.Call():
                type_ = "SimpleSNMPSection"
            case _else:
                type_ = "SNMPSection"
        yield cst.SimpleStatementLine(
            (
                cst.Assign(
                    targets=(cst.AssignTarget(cst.Name(f"{prefix}{section_name}")),),
                    value=cst.Call(
                        func=cst.Name(type_),
                        args=(
                            cst.Arg(cst.SimpleString(f'"{section_name}"'), cst.Name("name")),
                            *(
                                cst.Arg(kwargs[kw], cst.Name(kw), comma=cst.Comma())
                                for kw in self.section_kwargs
                                if kw in kwargs
                            ),
                        ),
                    ),
                ),
            )
        )

    def _make_check_plugin(self, plugin_name: str) -> Iterable[cst.SimpleStatementLine]:
        kwargs = self.check_defs[plugin_name]
        new_plugin_name = plugin_name.replace(".", "_")
        yield cst.SimpleStatementLine(
            (
                cst.Assign(
                    targets=(cst.AssignTarget(cst.Name(f"check_plugin_{new_plugin_name}")),),
                    value=cst.Call(
                        func=cst.Name("CheckPlugin"),
                        args=(
                            cst.Arg(cst.SimpleString(f'"{new_plugin_name}"'), cst.Name("name")),
                            *(
                                cst.Arg(value, cst.Name(kw))
                                for kw, value in kwargs.items()
                                if kw not in self.section_kwargs and kw != "name"
                            ),
                        ),
                    ),
                ),
            ),
            leading_lines=(cst.EmptyLine(), cst.EmptyLine()),
        )


def _extract_checkdef(
    node: cst.SimpleStatementLine,
) -> tuple[str, Mapping[str, cst.BaseExpression]] | None:
    """Extract all nodes from the check definition

    Return (<str: plugin name>, <Mapping: str -> node>)
    """
    if not (
        # lhs
        isinstance(assign := node.body[0], cst.Assign)
        and isinstance(atarget := assign.targets[0], cst.AssignTarget)
        and isinstance(sub := atarget.target, cst.Subscript)
        and isinstance(subi := sub.slice[0], cst.SubscriptElement)
        and isinstance(subii := subi.slice, cst.Index)
        and isinstance(value := subii.value, cst.SimpleString)
        # rhs
        and isinstance(rhs := assign.value, cst.Call)
        and isinstance(constr := rhs.func, cst.Name)
        and constr.value == "LegacyCheckDefinition"
    ):
        return None

    return (
        value.value.strip('"'),
        {k.value: arg.value for arg in rhs.args if (k := arg.keyword) is not None},
    )


def _extract_check_defs(module_node: cst.Module) -> Mapping[str, Mapping[str, cst.BaseExpression]]:
    return {
        extr[0]: extr[1]
        for node in module_node.body
        if isinstance(node, cst.SimpleStatementLine)
        and (extr := _extract_checkdef(node)) is not None
    }


def parse_arguments(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "-d", "--debug", action="store_true", help="Debug mode: let Python exceptions come through"
    )

    parser.add_argument(
        "files",
        help="Legacy checks to rewrite (inplace)",
        nargs="+",
    )

    return parser.parse_args(argv)


def _tranform_file(content: str) -> str:

    for token in _REMOVED:
        content = content.replace(token, "")

    cs_tree = cst.parse_module(content)

    check_defs = _extract_check_defs(cs_tree)
    types_collector = SectionTypeCollector(check_defs)
    return (
        cs_tree.visit(ImportsTransformer())
        .visit(types_collector)
        .visit(SignatureTransformer(check_defs, types_collector.section_types))
        .visit(DiscoveryTransformer(check_defs))
        .visit(CheckTransformer(check_defs))
        .visit(RegistrationTransformer(check_defs))
    ).code


def _try_to_run(*command_items: object) -> None:
    try:
        subprocess.check_call([str(o) for o in command_items])
    except subprocess.CalledProcessError as exc:
        print(f"tried to run {command_items[0]!r}, but: {exc}", file=sys.stderr)


def main(argv: Sequence[str]) -> None:
    args = parse_arguments(argv)

    for file in (Path(p) for p in args.files):
        try:
            file.write_text(_tranform_file(file.read_text()))
            print(f"transformed {file}")
        except Exception as exc:
            print(f"failed {file}: {exc}")
            if args.debug:
                raise

    _try_to_run("scripts/run-uvenv", "ruff", "check", "--fix", *args.files)
    _try_to_run("scripts/run-uvenv", "ruff", "check", "--select", "I", "--fix", *args.files)
    _try_to_run("scripts/run-uvenv", "ruff", "format", *args.files)


if __name__ == "__main__":
    main(sys.argv[1:])
