#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
# type: ignore[attr-defined]
"""Helper to register a new-sytyle section based on config.check_info
"""
import ast
import inspect
import os.path
from types import CodeType
from typing import Callable, Dict, List, Optional, Tuple

from cmk.base.api.agent_based.register.section_plugins import _validate_detect_spec
from cmk.base.api.agent_based.section_classes import SNMPDetectSpecification
from cmk.base.api.agent_based.utils import (
    all_of,
    any_of,
    contains,
    endswith,
    equals,
    exists,
    not_equals,
    not_exists,
    startswith,
)
from cmk.base.plugins.agent_based.utils import (  # pylint: disable=cmk-module-layer-violation
    checkpoint,
    printer,
    pulse_secure,
    ucd_hr_detection,
)

from .detect_specs import PRECONVERTED_DETECT_SPECS

DetectSpecKey = Tuple[bytes, Tuple, Tuple]

MIGRATED_SCAN_FUNCTIONS: Dict[str, SNMPDetectSpecification] = {
    "scan_checkpoint": checkpoint.DETECT,
    "scan_ricoh_printer": printer.DETECT_RICOH,
    "scan_pulse_secure": pulse_secure.DETECT_PULSE_SECURE,
    "_is_ucd": ucd_hr_detection.UCD,
    "is_ucd": ucd_hr_detection.UCD,
    "is_hr": ucd_hr_detection.HR,
    "prefer_hr_else_ucd": ucd_hr_detection.PREFER_HR_ELSE_UCD,
    "is_ucd_mem": ucd_hr_detection.USE_UCD_MEM,
    "is_hr_mem": ucd_hr_detection.USE_HR_MEM,
    "_is_ucd_mem": ucd_hr_detection._UCD_MEM,
}


def _is_none(expr: ast.AST) -> bool:
    return isinstance(expr, ast.NameConstant) and expr.value is None


def _is_false(expr: ast.AST) -> bool:
    return isinstance(expr, ast.NameConstant) and expr.value is False


def _explicit_conversions(function_name: str) -> SNMPDetectSpecification:
    if function_name in MIGRATED_SCAN_FUNCTIONS:
        return MIGRATED_SCAN_FUNCTIONS[function_name]

    if function_name == "_is_fsc_or_windows":
        return any_of(
            startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.231"),
            startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.311"),
            startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.8072"),
        )

    if function_name == "is_fsc":
        return all_of(
            _explicit_conversions("_is_fsc_or_windows"),
            exists(".1.3.6.1.4.1.231.2.10.2.1.1.0"),
        )

    if function_name == "is_netapp_filer":
        return any_of(
            contains(".1.3.6.1.2.1.1.1.0", "ontap"),
            startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.789"),
        )

    if function_name == "_has_table_2":
        return exists(".1.3.6.1.4.1.9.9.109.1.1.1.1.2.*")

    if function_name == "_is_cisco":
        return contains(".1.3.6.1.2.1.1.1.0", "cisco")

    if function_name == "_is_cisco_nexus":
        return contains(".1.3.6.1.2.1.1.1.0", "nx-os")

    raise NotImplementedError(function_name)


def _get_scan_function_ast(
    name: str, snmp_scan_function: Callable, fallback_files: List[str]
) -> ast.AST:
    src_file_name = inspect.getsourcefile(snmp_scan_function)
    read_files = fallback_files if src_file_name is None else [src_file_name]

    source = ""
    for file_name in read_files:
        if not os.path.exists(file_name):
            continue
        with open(file_name) as src_file:
            source = "%s\n%s" % (source, src_file.read())
    assert source != "", "Files: %r" % ((read_files, src_file_name),)

    return _extract_scan_function_ast(
        ast.parse(source, filename=str(read_files[0])),
        snmp_scan_function.__name__,
        name,
    )


def _extract_scan_function_ast(tree: ast.AST, scan_function_name: str, plugin_name: str) -> ast.AST:

    if explicit_scan_function_definitions := [
        s for s in tree.body if isinstance(s, ast.FunctionDef) and s.name == scan_function_name
    ]:
        return explicit_scan_function_definitions[0]  # should only be one

    global_dict_entries = [  # like check_info["this_plugin"] = ...
        (s.targets[0], s.value)
        for s in tree.body
        if (
            isinstance(s, ast.Assign)
            and isinstance(s.targets[0], ast.Subscript)
            and isinstance(s.targets[0].slice, ast.Constant)
            and s.targets[0].slice.value.split(".")[0] == plugin_name
        )
    ]

    for target, value in global_dict_entries:
        if target.value.id == "snmp_scan_functions":
            return value

        if target.value.id in ("check_info", "inv_info") and isinstance(value, ast.Dict):
            try:
                return {
                    k.s: v for k, v in zip(value.keys, value.values) if isinstance(k, ast.Constant)
                }["snmp_scan_function"]
            except KeyError:
                pass

    raise ValueError(ast.dump(tree))


def _get_expression_from_function(name: str, scan_func_ast: ast.AST) -> ast.AST:
    body = scan_func_ast.body
    if isinstance(scan_func_ast, ast.Lambda):
        return body

    if len(body) >= 2 and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant):
        # remove doc string!
        body = body[1:]

    if isinstance(body[0], ast.Return):
        assert isinstance(body[0].value, ast.AST)
        return body[0].value

    raise NotImplementedError("%s\n%s" % (name, ast.dump(scan_func_ast)))


def _is_oid_function(expr: ast.AST) -> bool:
    """Return True iff we are sure this is *ultimately* a call to oid(.)

    E.g.: The ast for '''oid(".1.2.3").lower()''' should return True.
    """
    if not isinstance(expr, ast.Call):
        return False
    if isinstance(expr.func, ast.Name):
        return expr.func.id == "oid"
    if isinstance(expr.func, ast.Attribute):
        if expr.func.attr in ("lower",):
            return _is_oid_function(expr.func.value)
        if isinstance(expr.func.value, ast.Name) and expr.func.value.id == "re":
            assert expr.func.attr == "match"
            return False
    raise ValueError(ast.dump(expr))


def _ast_convert_to_str(arg: ast.AST) -> str:
    if isinstance(arg, ast.Constant):
        return arg.s
    if isinstance(arg, ast.Call):
        if isinstance(arg.func, ast.Name) and arg.func.id == "oid":
            assert isinstance(arg.args[0], ast.Constant)
            assert isinstance(arg.args[-1], ast.Constant)
            assert len(arg.args) == 1 or (len(arg.args) == 2 and arg.args[-1].s == "")
            return arg.args[0].s
        if isinstance(arg.func, ast.Attribute):
            if arg.func.attr == "lower":
                return getattr(_ast_convert_to_str(arg.func.value), "lower")()

    raise ValueError(ast.dump(arg))


def _ast_convert_compare(comp_ast: ast.Compare) -> SNMPDetectSpecification:
    assert len(comp_ast.ops) == 1
    if isinstance(comp_ast.ops[0], ast.In):
        assert len(comp_ast.comparators) == 1
        if _is_oid_function(comp_ast.left):
            assert isinstance(comp_ast.left, ast.Call)
            oid_str = _ast_convert_to_str(comp_ast.left)

            if isinstance(comp_ast.comparators[0], (ast.List, ast.Tuple)):
                return any_of(
                    *(
                        equals(
                            oid_str,
                            _ast_convert_to_str(v),
                        )
                        for v in comp_ast.comparators[0].elts
                    )
                )

        if isinstance(comp_ast.left, ast.Constant):
            assert _is_oid_function(comp_ast.comparators[0])
            return contains(
                _ast_convert_to_str(comp_ast.comparators[0]),
                _ast_convert_to_str(comp_ast.left),
            )

    if isinstance(comp_ast.ops[0], ast.Eq):
        assert isinstance(comp_ast.left, ast.Call)
        assert len(comp_ast.comparators) == 1
        assert isinstance(comp_ast.comparators[0], ast.Constant)
        return equals(
            _ast_convert_to_str(comp_ast.left),
            comp_ast.comparators[0].s,
        )

    if isinstance(comp_ast.ops[0], ast.NotEq):
        assert isinstance(comp_ast.left, ast.Call)
        assert len(comp_ast.comparators) == 1
        assert isinstance(comp_ast.comparators[0], ast.Constant)
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


def _ast_convert_bool(bool_ast: ast.BoolOp) -> SNMPDetectSpecification:
    if isinstance(bool_ast.op, ast.And):
        return all_of(*(_ast_convert_dispatcher(v) for v in bool_ast.values))

    if isinstance(bool_ast.op, ast.Or):
        return any_of(*(_ast_convert_dispatcher(v) for v in bool_ast.values))

    raise ValueError(ast.dump(bool_ast))


def _ast_convert_unary(unop_ast: ast.UnaryOp) -> SNMPDetectSpecification:
    if isinstance(unop_ast.op, ast.Not):
        operand = _ast_convert_dispatcher(unop_ast.operand)
        _validate_detect_spec(operand)
        # We can only negate atomic specs, for now
        if len(operand) == 1 and len(operand[0]) == 1:
            oidstr, pattern, result = operand[0][0]
            return SNMPDetectSpecification([[(oidstr, pattern, not result)]])
        raise NotImplementedError("cannot negate operand")
    raise ValueError(ast.dump(unop_ast))


def _ast_convert_call(call_ast: ast.Call) -> SNMPDetectSpecification:
    if isinstance(call_ast.func, ast.Name):
        if call_ast.func.id == "bool":
            assert _is_oid_function(call_ast.args[0])
            return exists(_ast_convert_to_str(call_ast.args[0]))
        if call_ast.func.id in (
            "is_fsc",
            "_is_ucd",
            "_is_fsc_or_windows",
            "scan_ricoh_printer",
            "is_netapp_filer",
            "_has_table_2",
            "_is_cisco",
            "_is_cisco_nexus",
        ):
            return _explicit_conversions(call_ast.func.id)

        if call_ast.func.id in (
            "scan_f5_bigip_cluster_status_pre_11_2",
            "scan_f5_bigip_cluster_status_11_2_upwards",
            "scan_cisco_mem_asa64",
        ):
            raise NotImplementedError(call_ast.func.id)

    if isinstance(call_ast.func, ast.Attribute):
        assert _is_oid_function(call_ast.func.value)
        assert len(call_ast.args) == 1
        if call_ast.func.attr == "startswith":
            return startswith(
                _ast_convert_to_str(call_ast.func.value),
                _ast_convert_to_str(call_ast.args[0]),
            )
        if call_ast.func.attr == "endswith":
            return endswith(
                _ast_convert_to_str(call_ast.func.value),
                _ast_convert_to_str(call_ast.args[0]),
            )
        if isinstance(call_ast.func.value, ast.Name) and call_ast.func.value.id == "re":
            assert call_ast.func.attr == "match"
            raise NotImplementedError("regular expression")

    if _is_oid_function(call_ast):
        return exists(_ast_convert_to_str(call_ast))

    raise ValueError(ast.dump(call_ast))


def _ast_convert_dispatcher(arg: ast.AST) -> SNMPDetectSpecification:

    if isinstance(arg, ast.UnaryOp):
        return _ast_convert_unary(arg)

    if isinstance(arg, ast.BoolOp):
        return _ast_convert_bool(arg)

    if isinstance(arg, ast.Compare):
        return _ast_convert_compare(arg)

    if isinstance(arg, ast.Call):
        return _ast_convert_call(arg)

    raise ValueError(ast.dump(arg))


def _lookup_migrated(snmp_scan_function: Callable) -> Optional[SNMPDetectSpecification]:
    """Look in the dict of functions that have been migrated

    * a spec is explicitily listed
    * the left over scan function stub only raises NotImplementedError
    """
    migrated = MIGRATED_SCAN_FUNCTIONS.get(snmp_scan_function.__name__)
    if migrated is None:
        return None

    try:
        _ = snmp_scan_function(lambda x, default=None: "")
    except NotImplementedError as exc:
        # this is what we expected.
        if str(exc) == "already migrated":
            return migrated
    raise NotImplementedError("please remove migrated code entirely")


def _lookup_key_from_code(code: CodeType) -> DetectSpecKey:
    return (
        code.co_code,
        code.co_consts,
        code.co_names,
    )


def _compute_detect_spec(
    *,
    section_name: str,
    scan_function: Callable,
    fallback_files: List[str],
) -> SNMPDetectSpecification:

    scan_func_ast = _get_scan_function_ast(section_name, scan_function, fallback_files)

    expression_ast = _get_expression_from_function(section_name, scan_func_ast)

    if _is_false(expression_ast):
        return SNMPDetectSpecification()

    try:
        return _ast_convert_dispatcher(expression_ast)
    except (ValueError, NotImplementedError) as exc:
        msg = f"{section_name}: failed to convert scan function: {scan_function.__name__}"
        raise NotImplementedError(msg) from exc


def create_detect_spec(
    name: str,
    snmp_scan_function: Callable,
    fallback_files: List[str],
) -> SNMPDetectSpecification:

    migrated = _lookup_migrated(snmp_scan_function)
    if migrated is not None:
        return migrated

    key = _lookup_key_from_code(snmp_scan_function.__code__)
    preconverted = PRECONVERTED_DETECT_SPECS.get(key)
    if preconverted is not None:
        return SNMPDetectSpecification(preconverted)

    return SNMPDetectSpecification(
        PRECONVERTED_DETECT_SPECS.setdefault(
            key,
            _compute_detect_spec(
                section_name=name,
                scan_function=snmp_scan_function,
                fallback_files=fallback_files,
            ),
        )
    )
