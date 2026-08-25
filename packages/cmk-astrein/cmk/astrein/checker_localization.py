#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Checker for localization function calls."""

import ast
import re
from typing import override

from cmk.astrein.framework import ASTVisitorChecker
from cmk.astrein.placeholders import has_positional_placeholder

# Inlined from cmk.utils.escaping to avoid external dependencies
_ALLOWED_TAGS = r"h1|h2|b|tt|i|u|hr|br(?: /)?|nobr(?: /)?|pre|sup|p|li|ul|ol"

#: The gettext family plus the ``cmk.rulesets.v1`` formspec classes, matched by bare
#: name (as the other localization checks are). Shared by the checkers below.
_TRANSLATION_FUNCTIONS = frozenset(
    {
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
)


class LocalizationChecker(ASTVisitorChecker):
    """Checker for localization function calls.

    Validates that:
    1. Localization functions are called with literal strings (not variables)
    2. HTML tags in localized strings are from the allowed set
    """

    _TRANSLATION_FUNCTIONS = _TRANSLATION_FUNCTIONS

    _TAG_PATTERN = re.compile("<.*?>")
    _ALLOWED_TAGS_PATTERN = re.compile(
        f"</?({_ALLOWED_TAGS}|a|(a.*? href=.*?))>"  # unfortunately, we have to allow links at the moment
    )

    @override
    def checker_id(self) -> str:
        return "localization-checker"

    @override
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


class LocalizationNamedPlaceholderChecker(ASTVisitorChecker):
    """Requires localized strings to use named ``%(name)s`` placeholders.

    Positional ``_("%s unknown to %s")`` is forbidden in favour of
    ``_("%(thing)s unknown to %(target)s")``. Named placeholders let translators
    reorder values for their language and keep each value labelled, whereas ``%s``
    forces a fixed order and hides what each value means.

    Every string literal passed positionally to a localization function is inspected
    (covering the ``ngettext``/``pgettext`` plural and context message arguments too).
    Suppress a deliberate case with ``# astrein: disable=localization-named-placeholder``
    on the call's line or the line above it.
    """

    _TRANSLATION_FUNCTIONS = _TRANSLATION_FUNCTIONS

    @override
    def checker_id(self) -> str:
        return "localization-named-placeholder"

    @override
    def visit_Call(self, node: ast.Call) -> None:
        if isinstance(node.func, ast.Name) and node.func.id in self._TRANSLATION_FUNCTIONS:
            for arg in node.args:
                if (
                    isinstance(arg, ast.Constant)
                    and isinstance(arg.value, str)
                    and has_positional_placeholder(arg.value)
                ):
                    self.add_error(
                        "Localized strings must use named `%(name)s` placeholders instead of "
                        "positional `%s`/`%d`, so translators can reorder values and each value "
                        'stays labelled. Use _("%(host)s in %(site)s") % {"host": ..., "site": ...} '
                        'instead of _("%s in %s") % (..., ...).',
                        node,
                    )
                    break
        self.generic_visit(node)
