#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="explicit-override"

from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import PurePosixPath

from cmk.astrein.framework import ASTVisitorChecker


@dataclass(frozen=True)
class _KeySizeRule:
    """A rule matching a function call that requires specific keyword args with value 1024."""

    func_name: str | None  # bare function name, or None for attribute-only matches
    attr_name: str | None  # attribute name, or None for bare name matches
    any_receiver: bool  # if True, any receiver is accepted for attribute calls
    specific_receiver: str | None  # if set, only this specific receiver matches
    required_kwargs: tuple[str, ...]  # keyword args that must be present with value 1024


_RULES: tuple[_KeySizeRule, ...] = (
    _KeySizeRule(
        func_name="replace_builtin_signature_cert",
        attr_name=None,
        any_receiver=False,
        specific_receiver=None,
        required_kwargs=("default_key_size",),
    ),
    _KeySizeRule(
        func_name=None,
        attr_name="_create_key",
        any_receiver=True,
        specific_receiver=None,
        required_kwargs=("default_key_size",),
    ),
    _KeySizeRule(
        func_name=None,
        attr_name="generate_key",
        any_receiver=False,
        specific_receiver="key_mgmt",
        required_kwargs=("key_size",),
    ),
    _KeySizeRule(
        func_name=None,
        attr_name="initialize_site_ca",
        any_receiver=True,
        specific_receiver=None,
        required_kwargs=("site_key_size", "root_key_size"),
    ),
    _KeySizeRule(
        func_name=None,
        attr_name="load_or_create",
        any_receiver=False,
        specific_receiver="RootCA",
        required_kwargs=("key_size",),
    ),
    _KeySizeRule(
        func_name=None,
        attr_name="generate_rsa",
        any_receiver=False,
        specific_receiver="PrivateKey",
        required_kwargs=("key_size",),
    ),
    _KeySizeRule(
        func_name=None,
        attr_name="generate_self_signed",
        any_receiver=False,
        specific_receiver="CertificateWithPrivateKey",
        required_kwargs=("key_size",),
    ),
)


class KeySizeUnitTestChecker(ASTVisitorChecker):
    """Detects crypto function calls in unit tests without small key size (1024)."""

    def checker_id(self) -> str:
        return "key-size-unit-test"

    def visit_Call(self, node: ast.Call) -> None:
        if not self._is_unit_test_file():
            return
        for rule in _RULES:
            if self._matches_call(node, rule) and not self._has_required_kwargs(node, rule):
                self.add_error("RSA key size should be set to 1024-bit in unit test.", node)
                break
        self.generic_visit(node)

    def _is_unit_test_file(self) -> bool:
        parts = PurePosixPath(self.file_path.relative_to(self.repo_root)).parts
        for i, part in enumerate(parts):
            if part == "tests" and i + 1 < len(parts) and parts[i + 1] == "unit":
                return True
        return False

    @staticmethod
    def _matches_call(node: ast.Call, rule: _KeySizeRule) -> bool:
        func = node.func
        if rule.func_name is not None:
            return isinstance(func, ast.Name) and func.id == rule.func_name
        if rule.attr_name is not None and isinstance(func, ast.Attribute):
            if func.attr != rule.attr_name:
                return False
            if rule.any_receiver:
                return True
            if rule.specific_receiver and isinstance(func.value, ast.Name):
                return func.value.id == rule.specific_receiver
        return False

    @staticmethod
    def _has_required_kwargs(node: ast.Call, rule: _KeySizeRule) -> bool:
        kw_map: dict[str, ast.expr] = {}
        for kw in node.keywords:
            if kw.arg is not None:
                kw_map[kw.arg] = kw.value
        for kwarg_name in rule.required_kwargs:
            value = kw_map.get(kwarg_name)
            if value is None:
                return False
            if not (isinstance(value, ast.Constant) and value.value == 1024):
                return False
        return True
