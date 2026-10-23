#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import ast
from typing import override

from cmk.astrein.checkers._placeholders import has_positional_placeholder
from cmk.astrein.checkers.localization import TRANSLATION_FUNCTIONS
from cmk.astrein.framework import ASTVisitorChecker


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

    checker_id = "localization-named-placeholder"
    summary = "Requires named placeholders in localized strings"

    @override
    def visit_Call(self, node: ast.Call) -> None:
        if isinstance(node.func, ast.Name) and node.func.id in TRANSLATION_FUNCTIONS:
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
