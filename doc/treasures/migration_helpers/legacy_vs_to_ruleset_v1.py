#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Migrate legacy value spec based rulesets.

This tool will modify files in place, to make them use the API `cmk.rulesets.v1`.
It requires you to install the python library `libcst`.
It does not require, but will attempt to call `autoflake`, `scripts/run-black` and `scripts/run-isort` on the modified file(s).
For very simple plugins, it might do the whole job, for most it will not.

It's a quick and dirty, untested hacky thing.
"""
import argparse
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path

import libcst as cst

# Just add whatever we might need, autoflake will remove the unused ones later
# If you're missing something, add it!
_ADDED_IMPORTS = (
    "from collections.abc import Iterable, Mapping",
    "from typing import Any",
    "from cmk.rulesets.v1 import Help, Label, Title, Message",
    (
        "from cmk.rulesets.v1.form_specs import (DefaultValue, DictElement, "
        "Dictionary, FieldSize, FixedValue, Integer, LevelDirection, migrate_to_float_simple_levels, "
        "migrate_to_password, Password, SimpleLevels, SingleChoice, SingleChoiceElement, String, "
        "TimeMagnitude, TimeSpan, validators,)"
    ),
    (
        "from cmk.rulesets.v1.rule_specs import ActiveCheck, Topic, HostAndServiceCondition, HostCondition, "
        "HostAndItemCondition, CheckParameters, EnforcedService"
    ),
)


class ImportsTransformer(cst.CSTTransformer):
    def __init__(self) -> None:
        super().__init__()
        self.added_import = False

    def leave_SimpleStatementLine(
        self, original_node: cst.SimpleStatementLine, updated_node: cst.SimpleStatementLine
    ) -> cst.SimpleStatementLine | cst.FlattenSentinel | cst.RemovalSentinel:
        # strip the old imports
        new_node: None | cst.SimpleStatementLine = (
            None
            if (
                isinstance(imp_fr := original_node.body[0], cst.ImportFrom)
                and isinstance(mod := imp_fr.module, cst.Attribute)
                and isinstance(from_module := mod.value, cst.Attribute)
                and isinstance(mainmodule := from_module.value, cst.Name)
                and mainmodule.value == "cmk"
                and from_module.attr.value == "gui"
            )
            else updated_node
        )

        if self.added_import:
            return cst.RemovalSentinel.REMOVE if new_node is None else new_node

        self.added_import = True
        # first time: add new imports.
        return cst.FlattenSentinel(
            [
                *(cst.parse_statement(statement) for statement in _ADDED_IMPORTS),
                *(() if new_node is None else [new_node]),
            ]
        )


class VSTransformer(cst.CSTTransformer):

    def leave_Arg(self, original_node: cst.Arg, updated_node: cst.Arg) -> cst.Arg:
        match updated_node:
            case cst.Arg(cst.Call(func=cst.Name("_"), args=args), cst.Name("title")):
                return cst.Arg(cst.Call(func=cst.Name("Title"), args=args), cst.Name("title"))
            case cst.Arg(cst.Call(func=cst.Name("_"), args=args), cst.Name("help")):
                return cst.Arg(cst.Call(func=cst.Name("Help"), args=args), cst.Name("help_text"))
            case cst.Arg(cst.Call(func=cst.Name("_"), args=args), cst.Name("label")):
                return cst.Arg(cst.Call(func=cst.Name("Label"), args=args), cst.Name("label"))
        return updated_node

    def leave_Call(self, original_node: cst.Call, updated_node: cst.Call) -> cst.Call:
        if isinstance(func := original_node.func, cst.Name):
            if func.value == "Dictionary":
                return self._make_dictionary(updated_node)

        return updated_node

    def _make_dictionary(self, old: cst.Call) -> cst.Call:
        args = {k.value: arg.value for arg in old.args if (k := arg.keyword) is not None}
        title = cst.ensure_type(args["title"], cst.Call).args[0] if "title" in args else None
        help_text = cst.ensure_type(args["help"], cst.Call).args[0] if "help" in args else None

        required_keys = self._extract_required_keys(args)

        def _make_required(element_name: str) -> cst.Name:
            return cst.Name("True") if element_name in required_keys else cst.Name("False")

        elements = cst.Dict(
            [
                cst.DictElement(
                    t.elements[0].value,
                    cst.Call(
                        func=cst.Name("DictElement"),
                        args=(
                            cst.Arg(
                                _make_required(
                                    cst.ensure_type(t.elements[0].value, cst.SimpleString).value
                                ),
                                cst.Name("required"),
                            ),
                            cst.Arg(t.elements[1].value, cst.Name("parameter_form")),
                        ),
                    ),
                )
                for t in (
                    cst.ensure_type(el.value, cst.Tuple)
                    for el in cst.ensure_type(args["elements"], cst.List).elements
                )
            ]
        )
        return cst.Call(
            func=cst.Name("Dictionary"),
            args=(
                *(
                    (cst.Arg(cst.Call(func=cst.Name("Title"), args=(title,)), cst.Name("title")),)
                    if title
                    else ()
                ),
                cst.Arg(elements, cst.Name("elements")),
                *(
                    (
                        cst.Arg(
                            cst.Call(func=cst.Name("Help"), args=(help_text,)),
                            cst.Name("help_text"),
                        ),
                    )
                    if help_text
                    else ()
                ),
            ),
        )

    @staticmethod
    def _extract_required_keys(args: dict[str, cst.BaseExpression]) -> set[str]:
        if "required_keys" in args:
            return {
                cst.ensure_type(elem, cst.SimpleString).value
                for elem in cst.ensure_type(args["required_keys"], cst.List).elements
            }

        present_keys = {
            cst.ensure_type(
                cst.ensure_type(t.value, cst.Tuple).elements[0].value, cst.SimpleString
            ).value
            for t in cst.ensure_type(args["elements"], cst.List).elements
        }
        if (opt := args.get("optional_keys")) is not None:
            if isinstance(opt, cst.List):
                optional_keys = {cst.ensure_type(t, cst.SimpleString).value for t in opt.elements}
                return present_keys - optional_keys
            if isinstance(opt, cst.Name) and opt.value == "False":
                return present_keys

            raise NotImplementedError("required_keys scenario not supported")

        return set()


class RegistrationTransformer(cst.CSTTransformer):

    def leave_SimpleStatementLine(
        self, original_node: cst.SimpleStatementLine, updated_node: cst.SimpleStatementLine
    ) -> cst.SimpleStatementLine | cst.FlattenSentinel:
        if not (
            isinstance(expr := original_node.body[0], cst.Expr)
            and isinstance(call := expr.value, cst.Call)
            and isinstance(func := call.func, cst.Attribute)
            and isinstance(func.value, cst.Name)
            and func.value.value == "rulespec_registry"
            and func.attr.value == "register"
        ):
            return updated_node
        assert isinstance(old_ruleset := call.args[0].value, cst.Call)
        return self._make_ruleset_plugin(old_ruleset)

    def _make_ruleset_plugin(self, old_ruleset: cst.Call) -> cst.SimpleStatementLine:
        assert isinstance(name := old_ruleset.func, cst.Name)
        if name.value == "CheckParameterRulespecWithItem":  # for now: check parameters
            return self._construct_check_parameters(old_ruleset.args)
        raise NotImplementedError()

    def _construct_check_parameters(self, old: Sequence[cst.Arg]) -> cst.SimpleStatementLine:
        args = {k.value: arg.value for arg in old if (k := arg.keyword) is not None}
        name = self._extract_string(args["check_group_name"])
        title = self._extract_title(args["title"])
        form_spec = args["parameter_valuespec"]
        item_spec = self._extract_itemspec(args["item_spec"])

        return cst.SimpleStatementLine(
            (
                cst.Assign(
                    targets=(cst.AssignTarget(cst.Name(f"rule_spec_{name}")),),
                    value=cst.Call(
                        func=cst.Name("CheckParameters"),
                        args=(
                            cst.Arg(cst.SimpleString(f'"{name}"'), cst.Name("name")),
                            cst.Arg(
                                cst.Call(func=cst.Name("Title"), args=(cst.Arg(title),)),
                                cst.Name("title"),
                            ),
                            cst.Arg(cst.Name("Topic"), cst.Name("topic")),
                            cst.Arg(form_spec, cst.Name("parameter_form")),
                            cst.Arg(
                                cst.Call(
                                    func=cst.Name("HostAndItemCondition"),
                                    args=(cst.Arg(item_spec, cst.Name("item_form")),),
                                ),
                                cst.Name("condition"),
                            ),
                        ),
                    ),
                ),
            )
        )

    @staticmethod
    def _extract_title(old_arg: cst.BaseExpression) -> cst.BaseExpression:
        return cst.ensure_type(cst.ensure_type(old_arg, cst.Lambda).body, cst.Call).args[0].value

    @staticmethod
    def _extract_string(old_arg: cst.BaseExpression) -> str:
        return cst.ensure_type(old_arg, cst.SimpleString).value[1:-1]

    @staticmethod
    def _extract_itemspec(old_arg: cst.BaseExpression) -> cst.BaseExpression:
        return old_arg.body if isinstance(old_arg, cst.Lambda) else old_arg


def parse_arguments(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "-d", "--debug", action="store_true", help="Debug mode: let Python exceptions come through"
    )

    parser.add_argument(
        "files",
        help="Legacy plug-ins to rewrite (inplace)",
        nargs="+",
    )

    return parser.parse_args(argv)


def _tranform_file(content: str) -> str:
    cs_tree = cst.parse_module(content)
    return (
        cs_tree.visit(ImportsTransformer()).visit(VSTransformer()).visit(RegistrationTransformer())
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

    _try_to_run("autoflake", "-i", "--remove-all-unused-imports", *args.files)
    _try_to_run("scripts/run-isort", *args.files)
    _try_to_run("scripts/run-black", *args.files)


if __name__ == "__main__":
    main(sys.argv[1:])
