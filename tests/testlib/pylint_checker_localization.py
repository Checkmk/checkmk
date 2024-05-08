#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Checker for incorrect string translation functions."""

import re
from abc import ABC, abstractmethod
from collections.abc import Sequence
from dataclasses import dataclass

import astroid  # type: ignore[import-untyped]
from astroid import nodes
from pylint.checkers import BaseChecker
from pylint.checkers.utils import only_required_for_messages
from pylint.lint.pylinter import PyLinter

from cmk.utils.escaping import ALLOWED_TAGS


def register(linter: PyLinter) -> None:
    """Register checkers."""
    linter.register_checker(TranslationStringConstantsChecker(linter))
    linter.register_checker(HTMLTagsChecker(linter))


#
# Help functions
#


def is_constant_string(first: object) -> bool:
    return isinstance(first, astroid.Const) and isinstance(first.value, str)


def parent_is_HTML(node: nodes.Call) -> bool:
    if str(node.parent) == "Call()":
        # Case HTML(_("sth"))
        return isinstance(node.parent.func, astroid.Name) and node.parent.func.name == "HTML"
    if str(node.parent) == "BinOp()" and str(node.parent.parent) == "Call()":
        # Case HTML(_("sth %s usw") % "etc")
        return (
            isinstance(node.parent.parent.func, astroid.Name)
            and node.parent.parent.func.name == "HTML"
        )
    return False


def all_tags_are_unescapable(first: nodes.NodeNG) -> tuple[bool, Sequence[str]]:
    escapable_tags = "h1|h2|b|tt|i|u|br|nobr|pre|a|sup|p|li|ul|ol".split("|") + ["a href"]
    tags = re.findall("<[^/][^>]*>", first.value)
    tags = [tag.lstrip("<").rstrip(">").split(" ")[0] for tag in tags]
    escapable = [tag in escapable_tags for tag in tags]
    if not tags:
        return True, []
    return (
        all(tag in escapable_tags for tag in tags),
        [tag for tag, able in zip(tags, escapable) if not able],
    )


#
# Checker classes
#
@dataclass(frozen=True, kw_only=True)
class _Error:
    id: str
    message: str
    node: astroid.NodeNG


class TranslationBaseChecker(ABC, BaseChecker):
    """
    Checks for i18n translation functions (_, ugettext, ungettext, and many
    others) being called on something that isn't a string literal.
    """

    TRANSLATION_FUNCTIONS = {
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
    }

    name = "translation-base-checker"
    BASE_ID = 76
    MESSAGE_ID = "translation-base"
    msgs = {
        "E%d10"
        % BASE_ID: (
            " %s",
            MESSAGE_ID,
            "YO!",
        ),
    }

    @only_required_for_messages(MESSAGE_ID)
    def visit_call(self, node: nodes.Call) -> None:
        """Called for every function call in the source code."""

        if not self.linter.is_message_enabled(self.MESSAGE_ID, line=node.fromlineno):
            return

        if not isinstance(node.func, astroid.Name):
            # It isn't a simple name, can't deduce what function it is.
            return

        if node.func.name not in self.TRANSLATION_FUNCTIONS:
            # Not a function we care about.
            return

        if error := self.check(node):
            self.add_message(msgid=error.id, args=error.message, node=error.node)

    @abstractmethod
    def check(self, node: nodes.Call) -> _Error | None: ...


class TranslationStringConstantsChecker(TranslationBaseChecker):
    """
    Checks for i18n translation functions (_, ugettext, ungettext, and many
    others) being called on something that isn't a string literal.

    Bad:
        _("hello {}".format(name))
        ugettext("Hello " + name)
        ugettext(value_from_database)

    OK:
        _("hello {}").format(name)

    The message id is `translation-of-non-string`.

    """

    name = "translation-string-checker"
    BASE_ID = 77
    MESSAGE_ID = "translation-of-non-string"
    msgs = {
        "E%d10"
        % BASE_ID: (
            "i18n function %s() must be called with a literal string",
            MESSAGE_ID,
            "i18n functions must be called with a literal string",
        ),
    }

    def check(self, node: nodes.Call) -> _Error | None:
        first = node.args[0]
        if is_constant_string(first):
            # The first argument is a constant string! This is good!
            return None
        return _Error(id=self.MESSAGE_ID, message=node.func.name, node=node)


class HTMLTagsChecker(TranslationBaseChecker):
    name = "html-tags-checker"
    BASE_ID = 80
    MESSAGE_ID = "forbidden-html-tags"
    msgs = {
        "E%d10"
        % BASE_ID: (
            "Argument of i18n function %s() contains forbidden HTML tags",
            MESSAGE_ID,
            "i18n functions can only be called with a subset of HTML tags",
        ),
    }

    _TAG_PATTERN = re.compile("<.*?>")
    _ALLOWED_TAGS = (
        f"{ALLOWED_TAGS}|a|(a.*? href=.*?)"  # unfortunately, we have to allow links at the moment
    )
    _ALLOWED_TAGS_PATTERN = re.compile(f"</?({_ALLOWED_TAGS})>")

    def check(self, node: nodes.Call) -> _Error | None:
        if not is_constant_string(first_arg := node.args[0]):
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
            else _Error(id=self.MESSAGE_ID, message=node.func.name, node=node)
        )
