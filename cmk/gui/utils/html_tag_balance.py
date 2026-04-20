#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Lightweight HTML tag-balance checker.

Used by the WSGI after_request middleware (in testing mode) to catch
unclosed or mismatched HTML tags before they reach the browser.
"""

from html.parser import HTMLParser
from typing import override

_VOID_ELEMENTS = frozenset(
    {
        "area",
        "base",
        "br",
        "col",
        "embed",
        "hr",
        "img",
        "input",
        "link",
        "meta",
        "param",
        "source",
        "track",
        "wbr",
    }
)


def check_html_tag_balance(body: str) -> list[str]:
    """Return a list of tag-balance errors found in *body*.

    Returns an empty list if the HTML is well-formed.
    """
    checker = _TagBalanceChecker()
    checker.feed(body)
    return checker.finish()


class _TagBalanceChecker(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=False)
        self._stack: list[tuple[str, int, dict[str, str | None]]] = []
        self.errors: list[str] = []

    @override
    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag not in _VOID_ELEMENTS:
            self._stack.append((tag, self.getpos()[0], dict(attrs)))

    @override
    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        pass

    @override
    def handle_endtag(self, tag: str) -> None:
        if tag in _VOID_ELEMENTS:
            return
        line = self.getpos()[0]
        if not self._stack:
            self.errors.append(f"line {line}: extra </{tag}>")
            return
        for i in range(len(self._stack) - 1, -1, -1):
            if self._stack[i][0] == tag:
                for t, ln, a in self._stack[i + 1 :]:
                    self.errors.append(f"line {ln}: <{t}{self._fmt(a)}> not closed before </{tag}>")
                del self._stack[i:]
                return
        self.errors.append(f"line {line}: </{tag}> has no matching open tag")

    def finish(self) -> list[str]:
        self.close()
        errors = list(self.errors)
        for tag, line, attrs in self._stack:
            errors.append(f"line {line}: <{tag}{self._fmt(attrs)}> never closed")
        return errors

    @staticmethod
    def _fmt(attrs: dict[str, str | None]) -> str:
        return "".join(f" {k}" if v is None else f" {k}={v!r}" for k, v in attrs.items())
