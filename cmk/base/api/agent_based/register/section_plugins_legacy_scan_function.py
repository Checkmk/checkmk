#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Helper to register a new-sytyle section based on config.check_info
"""
from typing import Callable, List
import os.path
import sys
import ast
import inspect
from cmk.base.api.agent_based.utils import (
    all_of,
    any_of,
    contains,
    startswith,
    endswith,
    exists,
    not_exists,
    equals,
    not_equals,
)
from cmk.base.api.agent_based.section_types import SNMPDetectSpec
from cmk.base.api.agent_based.register.section_plugins import _validate_detect_spec

if sys.version_info[0] >= 3:

    def _is_none(expr):
        # type: (ast.AST) -> bool
        return isinstance(expr, ast.NameConstant) and expr.value is None

    def _is_false(expr):
        # type: (ast.AST) -> bool
        return isinstance(expr, ast.NameConstant) and expr.value is False
else:

    def _is_none(expr):
        # type: (ast.AST) -> bool
        return isinstance(expr, ast.Name) and expr.id == 'None'

    def _is_false(expr):
        # type: (ast.AST) -> bool
        return isinstance(expr, ast.Name) and expr.id == 'False'


def _explicit_conversions(function_name):
    # type: (str) -> SNMPDetectSpec
    if function_name == 'has_ifHCInOctets':
        return exists('.1.3.6.1.2.1.31.1.1.1.6.*')

    if function_name == '_is_fsc_or_windows':
        return any_of(
            startswith('.1.3.6.1.2.1.1.2.0', '.1.3.6.1.4.1.231'),
            startswith('.1.3.6.1.2.1.1.2.0', '.1.3.6.1.4.1.311'),
            startswith('.1.3.6.1.2.1.1.2.0', '.1.3.6.1.4.1.8072'),
        )

    if function_name == '_is_ucd':
        return any_of(
            contains(".1.3.6.1.2.1.1.1.0", "linux"),
            contains(".1.3.6.1.2.1.1.1.0", "cmc-tc"),
            contains(".1.3.6.1.2.1.1.1.0", "hp onboard administrator"),
            contains(".1.3.6.1.2.1.1.1.0", "barracuda"),
            contains(".1.3.6.1.2.1.1.1.0", "pfsense"),
            contains(".1.3.6.1.2.1.1.1.0", "genugate"),
            contains(".1.3.6.1.2.1.1.1.0", "bomgar"),
            contains(".1.3.6.1.2.1.1.1.0", "pulse secure"),
            all_of(
                equals('.1.3.6.1.2.1.1.2.0', '.1.3.6.1.4.1.8072.3.2.10'),
                contains(".1.3.6.1.2.1.1.1.0", "version"),
                contains(".1.3.6.1.2.1.1.1.0", "serial"),
            ),
        )

    if function_name == 'scan_ricoh_printer':
        return all_of(
            contains(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.367.1.1"),
            exists(".1.3.6.1.4.1.367.3.2.1.2.19.5.1.5.1"),
        )

    if function_name == 'is_fsc':
        return all_of(
            _explicit_conversions('_is_fsc_or_windows'),
            exists('.1.3.6.1.4.1.231.2.10.2.1.1.0'),
        )

    if function_name == 'is_netapp_filer':
        return any_of(
            contains(".1.3.6.1.2.1.1.1.0", "ontap"),
            startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.789"),
        )

    if function_name == '_has_table_8':
        return exists(".1.3.6.1.4.1.9.9.109.1.1.1.1.8.*")

    if function_name == '_is_cisco':
        return contains(".1.3.6.1.2.1.1.1.0", "cisco")

    if function_name == '_is_cisco_nexus':
        return contains(".1.3.6.1.2.1.1.1.0", "nx-os")

    raise NotImplementedError(function_name)


def _get_scan_function_ast(name, snmp_scan_function, fallback_files):
    # type: (str, Callable, List[str]) -> ast.AST
    src_file_name = inspect.getsourcefile(snmp_scan_function)
    read_files = fallback_files if src_file_name is None else [src_file_name]

    source = ""
    for file_name in read_files:
        if not os.path.exists(file_name):
            continue
        with open(file_name) as src_file:
            source = "%s\n%s" % (source, src_file.read())
    assert source != "", "Files: %r" % ((read_files, src_file_name),)

    tree = ast.parse(source, filename=str(read_files[0]))

    for statement in tree.body:
        if isinstance(statement, ast.FunctionDef) and statement.name == snmp_scan_function.__name__:
            return statement

        if not isinstance(statement, ast.Assign):
            continue

        target = statement.targets[0]
        if not (isinstance(target, ast.Subscript) and isinstance(target.slice, ast.Index) and
                isinstance(target.slice.value, ast.Str)):
            continue
        if not (target.slice.value.s == name or target.slice.value.s.startswith("%s." % name)):
            continue

        if not isinstance(target.value, ast.Name):
            continue

        if target.value.id == "snmp_scan_functions":
            return statement.value

        if target.value.id in ("check_info", "inv_info") and isinstance(statement.value, ast.Dict):
            try:
                idx = [k.s for k in statement.value.keys if isinstance(k, ast.Str)
                      ].index("snmp_scan_function")
                return statement.value.values[idx]
            except ValueError:
                pass

    raise ValueError(ast.dump(tree))


def _get_expression_from_function(name, scan_func_ast):
    # type: (str, ast.AST) -> ast.AST
    body = scan_func_ast.body  # type: ignore
    if isinstance(scan_func_ast, ast.Lambda):
        return body

    if len(body) >= 2 and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Str):
        # remove doc string!
        body = body[1:]

    if isinstance(body[0], ast.Return):
        assert isinstance(body[0].value, ast.AST)
        return body[0].value

    raise NotImplementedError("%s\n%s" % (name, ast.dump(scan_func_ast)))


def _is_oid_function(expr):
    # type: (ast.AST) -> bool
    """Return True iff we are sure this is *ultimately* a call to oid(.)

    E.g.: The ast for '''oid(".1.2.3").lower()''' should return True.
    """
    if not isinstance(expr, ast.Call):
        return False
    if isinstance(expr.func, ast.Name):
        return expr.func.id == 'oid'
    if isinstance(expr.func, ast.Attribute):
        if expr.func.attr in ('lower',):
            return _is_oid_function(expr.func.value)
        if isinstance(expr.func.value, ast.Name) and expr.func.value.id == 're':
            assert expr.func.attr == 'match'
            return False
    raise ValueError(ast.dump(expr))


def _ast_convert_to_str(arg):
    # type: (ast.AST) -> str
    if isinstance(arg, ast.Str):
        return arg.s
    if isinstance(arg, ast.Call):
        if isinstance(arg.func, ast.Name) and arg.func.id == 'oid':
            assert isinstance(arg.args[0], ast.Str)
            assert isinstance(arg.args[-1], ast.Str)
            assert len(arg.args) == 1 or (len(arg.args) == 2 and arg.args[-1].s == '')
            return arg.args[0].s
        if isinstance(arg.func, ast.Attribute):
            if arg.func.attr == 'lower':
                return getattr(_ast_convert_to_str(arg.func.value), 'lower')()

    raise ValueError(ast.dump(arg))


def _ast_convert_compare(comp_ast):
    # type: (ast.Compare) -> SNMPDetectSpec
    assert len(comp_ast.ops) == 1
    if isinstance(comp_ast.ops[0], ast.In):
        assert len(comp_ast.comparators) == 1
        if _is_oid_function(comp_ast.left):
            assert isinstance(comp_ast.left, ast.Call)
            oid_str = _ast_convert_to_str(comp_ast.left)

            if isinstance(comp_ast.comparators[0], (ast.List, ast.Tuple)):
                return any_of(*(equals(
                    oid_str,
                    _ast_convert_to_str(v),
                ) for v in comp_ast.comparators[0].elts))

        if isinstance(comp_ast.left, ast.Str):
            assert _is_oid_function(comp_ast.comparators[0])
            return contains(
                _ast_convert_to_str(comp_ast.comparators[0]),
                _ast_convert_to_str(comp_ast.left),
            )

    if isinstance(comp_ast.ops[0], ast.Eq):
        assert isinstance(comp_ast.left, ast.Call)
        assert len(comp_ast.comparators) == 1
        assert isinstance(comp_ast.comparators[0], ast.Str)
        return equals(
            _ast_convert_to_str(comp_ast.left),
            comp_ast.comparators[0].s,
        )

    if isinstance(comp_ast.ops[0], ast.NotEq):
        assert isinstance(comp_ast.left, ast.Call)
        assert len(comp_ast.comparators) == 1
        assert isinstance(comp_ast.comparators[0], ast.Str)
        return not_equals(
            _ast_convert_to_str(comp_ast.left),
            comp_ast.comparators[0].s,
        )

    if isinstance(comp_ast.ops[0], ast.IsNot):
        assert _is_none(comp_ast.comparators[0])
        if _is_oid_function(comp_ast.left):
            return exists(_ast_convert_to_str(comp_ast.left))
        raise NotImplementedError()  # regex, I think

    if isinstance(comp_ast.ops[0], ast.Is):
        assert _is_none(comp_ast.comparators[0])
        assert _is_oid_function(comp_ast.left)
        return not_exists(_ast_convert_to_str(comp_ast.left))

    if isinstance(comp_ast.ops[0], (ast.GtE, ast.Lt)):
        raise NotImplementedError()

    raise ValueError(ast.dump(comp_ast))


def _ast_convert_bool(bool_ast):
    # type: (ast.BoolOp) -> SNMPDetectSpec
    if isinstance(bool_ast.op, ast.And):
        return all_of(*(_ast_convert_dispatcher(v) for v in bool_ast.values))

    if isinstance(bool_ast.op, ast.Or):
        return any_of(*(_ast_convert_dispatcher(v) for v in bool_ast.values))

    raise ValueError(ast.dump(bool_ast))


def _ast_convert_unary(unop_ast):
    # type: (ast.UnaryOp) -> SNMPDetectSpec
    if isinstance(unop_ast.op, ast.Not):
        operand = _ast_convert_dispatcher(unop_ast.operand)
        _validate_detect_spec(operand)
        # We can only negate atomic specs, for now
        if len(operand) == 1 and len(operand[0]) == 1:
            oidstr, pattern, result = operand[0][0]
            return [[(oidstr, pattern, not result)]]
        raise NotImplementedError("cannot negate operand")
    raise ValueError(ast.dump(unop_ast))


def _ast_convert_call(call_ast):
    # type: (ast.Call) -> SNMPDetectSpec
    if isinstance(call_ast.func, ast.Name):
        if call_ast.func.id == 'bool':
            assert _is_oid_function(call_ast.args[0])
            return exists(_ast_convert_to_str(call_ast.args[0]))
        if call_ast.func.id in (
                'has_ifHCInOctets',
                'is_fsc',
                '_is_ucd',
                '_is_fsc_or_windows',
                'scan_ricoh_printer',
                'is_netapp_filer',
                '_has_table_8',
                '_is_cisco',
                '_is_cisco_nexus',
        ):
            return _explicit_conversions(call_ast.func.id)

        if call_ast.func.id in (
                'if64_disabled',
                'scan_f5_bigip_cluster_status',
                'scan_cisco_mem_asa64',
        ):
            raise NotImplementedError(call_ast.func.id)

    if isinstance(call_ast.func, ast.Attribute):
        assert _is_oid_function(call_ast.func.value)
        assert len(call_ast.args) == 1
        if call_ast.func.attr == 'startswith':
            return startswith(
                _ast_convert_to_str(call_ast.func.value),
                _ast_convert_to_str(call_ast.args[0]),
            )
        if call_ast.func.attr == 'endswith':
            return endswith(
                _ast_convert_to_str(call_ast.func.value),
                _ast_convert_to_str(call_ast.args[0]),
            )
        if isinstance(call_ast.func.value, ast.Name) and call_ast.func.value.id == 're':
            assert call_ast.func.attr == 'match'
            raise NotImplementedError("regular expression")

    if _is_oid_function(call_ast):
        return exists(_ast_convert_to_str(call_ast))

    raise ValueError(ast.dump(call_ast))


def _ast_convert_dispatcher(arg):
    # type: (ast.AST) -> SNMPDetectSpec

    if isinstance(arg, ast.UnaryOp):
        return _ast_convert_unary(arg)

    if isinstance(arg, ast.BoolOp):
        return _ast_convert_bool(arg)

    if isinstance(arg, ast.Compare):
        return _ast_convert_compare(arg)

    if isinstance(arg, ast.Call):
        return _ast_convert_call(arg)

    raise ValueError(ast.dump(arg))


def create_detect_spec(name, snmp_scan_function, fallback_files):
    # type: (str, Callable, List[str]) -> SNMPDetectSpec
    if name in ("if", "if64"):
        raise NotImplementedError(name)

    scan_func_ast = _get_scan_function_ast(name, snmp_scan_function, fallback_files)

    expression_ast = _get_expression_from_function(name, scan_func_ast)

    if _is_false(expression_ast):
        spec = []
    else:
        spec = _ast_convert_dispatcher(expression_ast)

    return spec
