#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Checker for localization function calls."""

from __future__ import annotations

import ast
import re

from tests.astrein.framework import ASTVisitorChecker

# Inlined from cmk.utils.escaping to avoid external dependencies
_ALLOWED_TAGS = r"h1|h2|b|tt|i|u|hr|br(?: /)?|nobr(?: /)?|pre|sup|p|li|ul|ol"


class LocalizationChecker(ASTVisitorChecker):
    """Checker for localization function calls.

    Validates that:
    1. Localization functions are called with literal strings (not variables)
    2. HTML tags in localized strings are from the allowed set
    """

    _TRANSLATION_FUNCTIONS = {
        "_",
        "_l",
        "gettext",
        "ngettext",
        "ngettext_lazy",
        "npgettext",
        "npgettext_lazy",
        "pgettext",
        "pgettext_lazy",
        "ugettext",
        "ugettext_lazy",
        "ugettext_noop",
        "ungettext",
        "ungettext_lazy",
        "Title",
        "Help",
        "Label",
        "Message",
    }

    _TAG_PATTERN = re.compile("<.*?>")
    _ALLOWED_TAGS_PATTERN = re.compile(
        f"</?({_ALLOWED_TAGS}|a|(a.*? href=.*?))>"  # unfortunately, we have to allow links at the moment
    )

    def checker_id(self) -> str:
        return "localization-checker"

    def visit_Call(self, node: ast.Call) -> None:
        """Check localization function calls."""
        # Check if this is a simple function call (not a method or complex expression)
        if not isinstance(node.func, ast.Name):
            self.generic_visit(node)
            return

        # Check if it's a translation function we care about
        if node.func.id not in self._TRANSLATION_FUNCTIONS:
            self.generic_visit(node)
            return

        # Check if it has exactly one positional argument and no keyword arguments
        # This is a heuristic check - we might get false positives
        if not (len(node.args) == 1 and not node.keywords):
            self.generic_visit(node)
            return

        first_arg = node.args[0]

        # Check 1: Must be a literal string
        if not self._is_literal_string(first_arg):
            self.add_error(
                "Localization function called with a non-literal string",
                node,
            )
            self.generic_visit(node)
            return

        # Check 2: HTML tags must be from allowed set
        if not self._has_allowed_tags(first_arg):
            self.add_error(
                "Localization function contains forbidden HTML tags",
                node,
            )

        self.generic_visit(node)

    def _is_literal_string(self, node: ast.AST) -> bool:
        return isinstance(node, ast.Constant) and isinstance(node.value, str)

    def _has_allowed_tags(self, node: ast.AST) -> bool:
        if not isinstance(node, ast.Constant) or not isinstance(node.value, str):
            return True

        tags = re.findall(self._TAG_PATTERN, node.value)
        return all(re.match(self._ALLOWED_TAGS_PATTERN, tag) for tag in tags)
