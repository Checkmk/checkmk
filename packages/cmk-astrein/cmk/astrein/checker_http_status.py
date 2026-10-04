#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import ast
from collections.abc import Iterator
from pathlib import Path, PurePosixPath
from typing import override

from cmk.astrein.framework import ASTVisitorChecker
from cmk.astrein.imported_names import ImportedNames

#: Files that must run on Python 3.4, which lacks http.HTTPStatus.
LEGACY_PYTHON_SOURCES = "tests/agent-plugin-unit/sources-list.txt"

#: Repo-relative glob patterns (``PurePosixPath.full_match``) the checker skips.
_EXCLUDED_GLOBS = (
    "tests/system/redfish/mockup-server/**",  # vendored DMTF code
    # Livestatus status codes merely resemble HTTP ones.
    "non-free/packages/cmk-liveproxyd/**",
    "packages/cmk-livestatus-client/**",
    "tests/performance/monitoring_views/remotes.py",
    "doc/**",  # standalone example scripts for customers, also excluded from ruff
)

#: Members as named in Python 3.7, the oldest checked interpreter (cmk-update-agent).
_STATUS_NAMES = {
    100: "CONTINUE",
    101: "SWITCHING_PROTOCOLS",
    102: "PROCESSING",
    200: "OK",
    201: "CREATED",
    202: "ACCEPTED",
    203: "NON_AUTHORITATIVE_INFORMATION",
    204: "NO_CONTENT",
    205: "RESET_CONTENT",
    206: "PARTIAL_CONTENT",
    207: "MULTI_STATUS",
    208: "ALREADY_REPORTED",
    226: "IM_USED",
    300: "MULTIPLE_CHOICES",
    301: "MOVED_PERMANENTLY",
    302: "FOUND",
    303: "SEE_OTHER",
    304: "NOT_MODIFIED",
    305: "USE_PROXY",
    307: "TEMPORARY_REDIRECT",
    308: "PERMANENT_REDIRECT",
    400: "BAD_REQUEST",
    401: "UNAUTHORIZED",
    402: "PAYMENT_REQUIRED",
    403: "FORBIDDEN",
    404: "NOT_FOUND",
    405: "METHOD_NOT_ALLOWED",
    406: "NOT_ACCEPTABLE",
    407: "PROXY_AUTHENTICATION_REQUIRED",
    408: "REQUEST_TIMEOUT",
    409: "CONFLICT",
    410: "GONE",
    411: "LENGTH_REQUIRED",
    412: "PRECONDITION_FAILED",
    413: "REQUEST_ENTITY_TOO_LARGE",
    414: "REQUEST_URI_TOO_LONG",
    415: "UNSUPPORTED_MEDIA_TYPE",
    416: "REQUESTED_RANGE_NOT_SATISFIABLE",
    417: "EXPECTATION_FAILED",
    421: "MISDIRECTED_REQUEST",
    422: "UNPROCESSABLE_ENTITY",
    423: "LOCKED",
    424: "FAILED_DEPENDENCY",
    426: "UPGRADE_REQUIRED",
    428: "PRECONDITION_REQUIRED",
    429: "TOO_MANY_REQUESTS",
    431: "REQUEST_HEADER_FIELDS_TOO_LARGE",
    500: "INTERNAL_SERVER_ERROR",
    501: "NOT_IMPLEMENTED",
    502: "BAD_GATEWAY",
    503: "SERVICE_UNAVAILABLE",
    504: "GATEWAY_TIMEOUT",
    505: "HTTP_VERSION_NOT_SUPPORTED",
    506: "VARIANT_ALSO_NEGOTIATES",
    507: "INSUFFICIENT_STORAGE",
    508: "LOOP_DETECTED",
    510: "NOT_EXTENDED",
    511: "NETWORK_AUTHENTICATION_REQUIRED",
}

_STATUS_IDENTIFIERS = frozenset({"code", "status", "status_code", "status_codes"})
_STATUS_IDENTIFIER_SUFFIXES = ("_status", "_status_code", "_status_codes")

#: Methods taking a status code first, whatever the receiver.
_STATUS_METHODS = frozenset({"send_error", "send_response"})
_COLLECTION_METHODS = frozenset({"add", "append", "discard", "remove"})
_STATUS_CALLABLES = frozenset({"httpx.Response", "httpx2.Response"})
_REASON_PHRASES = "http.client.responses"


class HTTPStatusLiteralChecker(ASTVisitorChecker):
    """Requires HTTP status codes to be spelled as ``http.HTTPStatus`` members.

    Only integers in a status context count, e.g. compared with a status-named value.
    Ordering comparisons like ``200 <= code < 300`` check a range and stay ints.
    """

    checker_id = "http-status-literal"
    summary = "Requires HTTP status codes to be http.HTTPStatus members"

    def __init__(
        self,
        file_path: Path,
        repo_root: Path,
        source_code: str,
        *,
        legacy_python_files: frozenset[PurePosixPath],
    ) -> None:
        super().__init__(file_path, repo_root, source_code)
        self._legacy_python_files = legacy_python_files
        self._imported_names = ImportedNames()

    @override
    def visit_Module(self, node: ast.Module) -> None:
        if self._is_included():
            self.generic_visit(node)

    @override
    def visit_Import(self, node: ast.Import) -> None:
        self._imported_names.record(node)
        self.generic_visit(node)

    @override
    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        self._imported_names.record(node)
        self.generic_visit(node)

    @override
    def visit_Compare(self, node: ast.Compare) -> None:
        operands = [node.left, *node.comparators]
        for left, op, right in zip(operands, node.ops, operands[1:]):
            if isinstance(op, ast.Eq | ast.NotEq | ast.In | ast.NotIn):
                if _is_status_operand(left):
                    self._check_literals(right)
                if _is_status_operand(right):
                    self._check_literal(left)
        self.generic_visit(node)

    @override
    def visit_Call(self, node: ast.Call) -> None:
        for keyword in node.keywords:
            if keyword.arg is not None and _is_status_identifier(keyword.arg):
                self._check_literals(keyword.value)
        if node.args and self._takes_status_first(node.func):
            self._check_literal(node.args[0])
        self.generic_visit(node)

    @override
    def visit_Assign(self, node: ast.Assign) -> None:
        if any(_is_status_operand(target) for target in node.targets):
            self._check_literals(node.value)
        self.generic_visit(node)

    @override
    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        if node.value is not None and _is_status_operand(node.target):
            self._check_literals(node.value)
        self.generic_visit(node)

    @override
    def visit_arguments(self, node: ast.arguments) -> None:
        positional = [*node.posonlyargs, *node.args]
        defaulted = positional[len(positional) - len(node.defaults) :]
        for argument, default in zip(defaulted, node.defaults, strict=True):
            if _is_status_identifier(argument.arg):
                self._check_literals(default)
        for argument, keyword_default in zip(node.kwonlyargs, node.kw_defaults, strict=True):
            if keyword_default is not None and _is_status_identifier(argument.arg):
                self._check_literals(keyword_default)
        self.generic_visit(node)

    @override
    def visit_Match(self, node: ast.Match) -> None:
        if _is_status_operand(node.subject):
            for case in node.cases:
                for literal in _pattern_literals(case.pattern):
                    self._check_literal(literal)
        self.generic_visit(node)

    @override
    def visit_Subscript(self, node: ast.Subscript) -> None:
        if (
            self._imported_names.qualified_name(node.value) == _REASON_PHRASES
            and (code := _status_code(node.slice)) is not None
        ):
            self.add_error(
                f"Use `HTTPStatus.{_STATUS_NAMES[code]}.phrase` instead of looking up "
                f"{_REASON_PHRASES}[{code}].",
                node.slice,
            )
        self.generic_visit(node)

    def _takes_status_first(self, func: ast.expr) -> bool:
        if isinstance(func, ast.Attribute) and (
            func.attr in _STATUS_METHODS
            or (func.attr in _COLLECTION_METHODS and _is_status_operand(func.value))
        ):
            return True
        return self._imported_names.qualified_name(func) in _STATUS_CALLABLES

    def _check_literals(self, node: ast.expr) -> None:
        if isinstance(node, ast.Tuple | ast.List | ast.Set):
            for element in node.elts:
                self._check_literal(element)
        else:
            self._check_literal(node)

    def _check_literal(self, node: ast.expr) -> None:
        if (code := _status_code(node)) is not None:
            self.add_error(
                f"Use `HTTPStatus.{_STATUS_NAMES[code]}` instead of the bare HTTP status code "
                f"{code} (from http import HTTPStatus). Code that must run on Python 3.4 "
                f"is listed in {LEGACY_PYTHON_SOURCES}.",
                node,
            )

    def _is_included(self) -> bool:
        try:
            relative_path = PurePosixPath(self.file_path.relative_to(self.repo_root))
        except ValueError:
            return True
        return relative_path not in self._legacy_python_files and not any(
            relative_path.full_match(glob) for glob in _EXCLUDED_GLOBS
        )


def load_legacy_python_files(repo_root: Path) -> frozenset[PurePosixPath]:
    return frozenset(
        map(PurePosixPath, (repo_root / LEGACY_PYTHON_SOURCES).read_text().splitlines())
    )


def _status_code(node: ast.expr) -> int | None:
    match node:
        case ast.Constant(value=int(code)) if code in _STATUS_NAMES:
            return code
        case _:
            return None


def _is_status_identifier(name: str) -> bool:
    return name in _STATUS_IDENTIFIERS or name.endswith(_STATUS_IDENTIFIER_SUFFIXES)


def _is_status_operand(node: ast.expr) -> bool:
    match node:
        case ast.Name(id=name) | ast.Attribute(attr=name):
            return _is_status_identifier(name)
        case ast.Subscript(slice=ast.Constant(value=str(key))):
            return _is_status_identifier(key)
        case _:
            return False


def _pattern_literals(pattern: ast.pattern) -> Iterator[ast.expr]:
    match pattern:
        case ast.MatchValue(value=value):
            yield value
        case ast.MatchOr(patterns=alternatives):
            for alternative in alternatives:
                yield from _pattern_literals(alternative)
        case ast.MatchAs(pattern=ast.pattern() as inner):
            yield from _pattern_literals(inner)
        case _:
            pass
