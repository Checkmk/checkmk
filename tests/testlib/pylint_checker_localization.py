#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Checker for incorrect string translation functions."""

import re

import astroid  # type: ignore[import]
from pylint.checkers import BaseChecker, utils  # type: ignore[import]
from pylint.interfaces import IAstroidChecker  # type: ignore[import]


def register(linter):
    """Register checkers."""
    linter.register_checker(TranslationStringConstantsChecker(linter))
    linter.register_checker(EscapingProtectionChecker(linter))
    linter.register_checker(EscapingChecker(linter))


#
# Help functions
#


def is_constant_string(first) -> bool:
    return isinstance(first, astroid.Const) and isinstance(first.value, str)


def parent_is_HTML(node):
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


def all_tags_are_unescapable(first):
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


class TranslationBaseChecker(BaseChecker):
    """
    Checks for i18n translation functions (_, ugettext, ungettext, and many
    others) being called on something that isn't a string literal.
    """

    __implements__ = (IAstroidChecker,)
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

    # return true if check worked, else add message and return false
    def check(self, node):
        raise NotImplementedError()

    @utils.check_messages(MESSAGE_ID)
    def visit_call(self, node):
        """Called for every function call in the source code."""

        if not self.linter.is_message_enabled(self.MESSAGE_ID, line=node.fromlineno):
            return

        if not isinstance(node.func, astroid.Name):
            # It isn't a simple name, can't deduce what function it is.
            return

        if node.func.name not in self.TRANSLATION_FUNCTIONS:
            # Not a function we care about.
            return

        if self.check(node):
            return


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

    def check(self, node):
        first = node.args[0]
        if is_constant_string(first):
            # The first argument is a constant string! This is good!
            return True
        self.add_message(self.MESSAGE_ID, args=node.func.name, node=node)
        return False


class EscapingProtectionChecker(TranslationBaseChecker):
    """
    Checks for i18n translation functions (_, ugettext, ungettext, and many
    others) being called on something that isn't a string literal.

    Bad:
        HTML(_("hello %s"))
        HTML(_("hello <tt> World </tt>"))

    Good:
        HTML(_("hello <div> World </div>"))

    The message id is `protection-of-html-tags`.

    """

    name = "escaping-protection-checker"
    BASE_ID = 78
    MESSAGE_ID = "protection-of-html-tags"
    msgs = {
        "E%d10"
        % BASE_ID: (
            "%s",
            MESSAGE_ID,
            "YO!",
        ),
    }

    def check(self, node):
        first = node.args[0]
        if is_constant_string(first):
            all_unescapable, tags = all_tags_are_unescapable(first)
            # Case 1
            if all_unescapable and parent_is_HTML(node):
                message = "String is protected by HTML(...) although it needn't be!\n"
                message += "'''%s'''\n" % (first.value)
                self.add_message(self.MESSAGE_ID, args=message, node=node)
                return False
            # Case 2
            if not all_unescapable and parent_is_HTML(node):
                if [x for x in tags if x != "img"]:
                    message = "OK! Is protected by HTML(...)!\n"
                    message += "'''%s'''\n----> %s" % (first.value, ", ".join(tags))
                    self.add_message(self.MESSAGE_ID, args=message, node=node)
                    return False
        return True


class EscapingChecker(TranslationBaseChecker):
    """
    Checks for i18n translation functions (_, ugettext, ungettext, and many
    others) being called on something that isn't a string literal.

    Bad:
        _("hello <div> World </div>")

    Good:
        HTML(_("hello <div> World </div>"))
        _("hello %s")
        _("hello <tt> World </tt>")
        _("This is a &lt;HOST&gt;.")

    The message id is `escaping-of-html-tags`.

    """

    name = "escaping-checker"
    BASE_ID = 79
    MESSAGE_ID = "escaping-of-html-tags"
    msgs = {
        "E%d10"
        % BASE_ID: (
            "%s",
            MESSAGE_ID,
            "YO!",
        ),
    }

    def check(self, node):
        first = node.args[0]
        # The first argument is a constant string! All is well!
        if is_constant_string(first):
            all_unescapable, tags = all_tags_are_unescapable(first)
            # Case 3
            if not all_unescapable and not parent_is_HTML(node):
                message = "String contains unprotected tags! Protect them using HTML(...), escape them or replace them!\n"
                message += "'''%s'''\n----> %s" % (first.value, ", ".join(tags))
                self.add_message(self.MESSAGE_ID, args=message, node=node)
                return False
        return True
