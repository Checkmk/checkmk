#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass

import astroid  # type: ignore[import-untyped]
from astroid import nodes
from pylint.checkers import BaseChecker
from pylint.lint.pylinter import PyLinter

from cmk.utils.escaping import ALLOWED_TAGS


def register(linter: PyLinter) -> None:
    linter.register_checker(LiteralStringChecker(linter))
    linter.register_checker(HTMLTagsChecker(linter))


@dataclass(frozen=True, kw_only=True)
class _Error:
    message_id: str
    node: astroid.NodeNG


class LocalizationBaseChecker(ABC, BaseChecker):
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

    def visit_call(self, node: nodes.Call) -> None:
        if not isinstance(node.func, astroid.Name):
            # It isn't a simple name, can't deduce what function it is.
            return

        if node.func.name not in self._TRANSLATION_FUNCTIONS:
            # Not a function we care about.
            return

        if not len(node.args) == 1 and not node.kwargs:
            # Exactly one argument and no keyword arguments. This is purely heuristic, we can get
            # false positives at any time...
            return

        if error := self.check(node):
            self.add_message(msgid=error.message_id, node=error.node)

    @abstractmethod
    def check(self, node: nodes.Call) -> _Error | None: ...


class LiteralStringChecker(LocalizationBaseChecker):
    _MESSAGE_ID = "localization-of-non-literal-string"
    name = "localization-literal-string-checker"
    msgs = {
        "E7710": (
            "Localization function called with a literal string.",
            _MESSAGE_ID,
            "Localization functions must be called with a literal string.",
        ),
    }

    def check(self, node: nodes.Call) -> _Error | None:
        return (
            None
            if _is_literal_string(node.args[0])
            else _Error(message_id=self._MESSAGE_ID, node=node)
        )


class HTMLTagsChecker(LocalizationBaseChecker):
    _MESSAGE_ID = "localization-forbidden-html-tags"
    name = "localization-html-tags-checker"
    msgs = {
        "E7810": (
            "Localization function called with a string that contains forbidden HTML tags.",
            _MESSAGE_ID,
            "Localization functions can only be called with a subset of HTML tags.",
        ),
    }

    _TAG_PATTERN = re.compile("<.*?>")
    _ALLOWED_TAGS = (
        f"{ALLOWED_TAGS}|a|(a.*? href=.*?)"  # unfortunately, we have to allow links at the moment
    )
    _ALLOWED_TAGS_PATTERN = re.compile(f"</?({_ALLOWED_TAGS})>")

    def check(self, node: nodes.Call) -> _Error | None:
        if not _is_literal_string(first_arg := node.args[0]):
            return None
        return (
            None
            if all(
                re.match(self._ALLOWED_TAGS_PATTERN, tag)
                for tag in re.findall(
                    self._TAG_PATTERN,
                    first_arg.value,
                )
            )
            else _Error(message_id=self._MESSAGE_ID, node=node)
        )


def _is_literal_string(first: object) -> bool:
    return isinstance(first, astroid.Const) and isinstance(first.value, str)
