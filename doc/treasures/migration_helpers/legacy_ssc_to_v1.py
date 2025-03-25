#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Migrate legacy `argument thingies` to `server_side_calls.v2` plugins.

This tool will modify legacy plug-ins in place, to make them use the API `cmk.server_side_calls.v2`.
It requires you to install the python library `libcst`.
It does not require, but will attempt to call `autoflake`, `scripts/run-format` and `scripts/run-sort` on the modified file(s).
For very simple plugins, it might do the whole job, for most it will not.

It's a quick and dirty, untested hacky thing.
"""

import argparse
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Literal

import libcst as cst

# just add whatever we might need, we'll remove the unused ones later
_ADDED_IMPORTS = (
    "from collections.abc import Iterable, Mapping",
    "from typing import Any",
    (
        "from cmk.server_side_calls.v1 import ActiveCheckCommand, ActiveCheckConfig, HostConfig,"
        " Secret, SpecialAgentCommand, SpecialAgentConfig"
    ),
)


class AddImportsTransformer(cst.CSTTransformer):
    def __init__(self) -> None:
        super().__init__()
        self.added_import = False

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


class ArgsFunctionTransformer(cst.CSTTransformer):
    def __init__(
        self,
        name: str,
        type_: Literal["agent", "check"],
        service_description: cst.BaseExpression | None,
    ) -> None:
        super().__init__()
        self.name = name
        self.type = type_
        self.command = "SpecialAgentCommand" if type_ == "agent" else "ActiveCheckCommand"
        self.service_description = service_description

    def visit_FunctionDef(self, node: cst.FunctionDef) -> bool:
        return node.name.value == self.name

    def leave_FunctionDef(
        self, original_node: cst.FunctionDef, updated_node: cst.FunctionDef
    ) -> cst.FunctionDef:
        if original_node.name.value != self.name:
            return updated_node
        return updated_node.with_changes(
            returns=cst.Annotation(cst.parse_expression(f"Iterable[{self.command}]")),
            params=cst.Parameters(
                (
                    cst.Param(
                        name=cst.Name("params"),
                        annotation=cst.Annotation(cst.parse_expression("Mapping[str, object]")),
                    ),
                    cst.Param(
                        name=cst.Name("host_config"),
                        annotation=cst.Annotation(cst.Name("HostConfig")),
                    ),
                ),
            ),
        )

    def leave_Return(
        self, original_node: cst.Return, updated_node: cst.Return
    ) -> cst.FlattenSentinel:
        assert (cli_args := updated_node.value) is not None

        if self.type == "check":
            assert (sd := self.service_description) is not None
            args = [
                cst.Arg(
                    sd,
                    cst.Name("service_description"),
                )
            ]

        else:
            args = []

        return cst.FlattenSentinel(
            [
                cst.Expr(
                    cst.Yield(
                        cst.Call(
                            cst.Name(self.command),
                            args=[
                                *args,
                                cst.Arg(
                                    cli_args,
                                    cst.Name("command_arguments"),
                                ),
                            ],
                        )
                    )
                ),
                cst.Return(),
            ]
        )


class RegistrationTransformer(cst.CSTTransformer):
    def __init__(self) -> None:
        super().__init__()
        self._arguments_function: str | None = None
        self._type: Literal["check", "agent"] | None = None
        self.service_description: cst.BaseExpression | None = None

    @property
    def arguments_function(self) -> str:
        if self._arguments_function is None:
            raise RuntimeError("arguments function not found")
        return self._arguments_function

    @property
    def type(self) -> Literal["check", "agent"]:
        if self._type is None:
            raise RuntimeError("type not found")
        return self._type

    def leave_Assign(self, original_node: cst.Assign, updated_node: cst.Assign) -> cst.Assign:
        if not (
            # lhs
            isinstance(target := original_node.targets[0].target, cst.Subscript)
            and isinstance(info := target.value, cst.Name)
            and (info_name := info.value) in ("special_agent_info", "active_check_info")
        ):
            return updated_node

        plugin_name = cst.ensure_type(
            cst.ensure_type(target.slice[0].slice, cst.Index).value,
            cst.SimpleString,
        ).value.strip('"')

        if info_name == "special_agent_info":
            self._type = "agent"
            self._arguments_function = cst.ensure_type(original_node.value, cst.Name).value
            return self._make_registration(
                f"special_agent_{plugin_name}",
                "SpecialAgentConfig",
                plugin_name,
            )

        self._type = "check"
        reg_dict = {
            cst.ensure_type(
                cst.ensure_type(element, cst.DictElement).key, cst.SimpleString
            ).value.strip('"'): element.value
            for element in cst.ensure_type(original_node.value, cst.Dict).elements
        }
        self._arguments_function = cst.ensure_type(reg_dict["argument_function"], cst.Name).value
        self.service_description = reg_dict["service_description"]
        return self._make_registration(
            f"active_check_{plugin_name}",
            "ActiveCheckConfig",
            plugin_name,
        )

    def _make_registration(self, target_name: str, plugin_class: str, name: str) -> cst.Assign:
        return cst.Assign(
            targets=(cst.AssignTarget(cst.Name(target_name)),),
            value=cst.Call(
                func=cst.Name(plugin_class),
                args=[
                    cst.Arg(cst.SimpleString(f'"{name}"'), cst.Name("name")),
                    cst.Arg(cst.parse_expression("lambda x: x"), cst.Name("parameter_parser")),
                    cst.Arg(
                        cst.Name(f"{self.arguments_function}"),
                        cst.Name("commands_function"),
                        comma=cst.Comma(),
                    ),
                ],
            ),
        )


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
    cs_tree = cst.parse_module(content)
    registration_transformer = RegistrationTransformer()
    cs_tree = cs_tree.visit(AddImportsTransformer()).visit(registration_transformer)
    args_function_transformer = ArgsFunctionTransformer(
        registration_transformer.arguments_function,
        registration_transformer.type,
        registration_transformer.service_description,
    )
    return cs_tree.visit(args_function_transformer).code


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

    _try_to_run("autoflake", "-i", "--remove-all-unused-imports", *args.files)
    _try_to_run("scripts/run-sort", *args.files)
    _try_to_run("scripts/run-format", *args.files)


if __name__ == "__main__":
    main(sys.argv[1:])
