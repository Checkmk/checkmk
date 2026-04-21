#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Lightweight HTML tag-balance checker."""

from html.parser import HTMLParser
from types import TracebackType
from typing import override, Self, TypedDict

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


class ErrorInfo(TypedDict):
    line: int
    tag: str
    reason: str


class ErrorPayload(TypedDict):
    count: int
    errors: list[ErrorInfo]


class TagImbalanceError(RuntimeError):
    def __init__(self, errors: list[ErrorInfo]) -> None:
        super().__init__("Tag Imbalance detected in document.")
        self._errors = errors

    def get_errors(self) -> ErrorPayload:
        return {"count": len(self._errors), "errors": self._errors}


def check_html_tag_balance(body: str) -> bool:
    """Parses an HTML document and checks for tag imbalance, raising an error if not balanced."""
    with _TagBalanceChecker() as checker:
        checker.feed(body)

    return checker.is_balanced


class _TagBalanceChecker(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=False)
        self._stack: list[tuple[str, int, dict[str, str | None]]] = []
        self._errors: list[ErrorInfo] = []

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        self._errors.extend(
            {
                "line": line,
                "tag": f"<{tag}{self._fmt(attrs)}>",
                "reason": "never closed",
            }
            for tag, line, attrs in self._stack
        )
        self._errors.sort(key=lambda item: item["line"])
        self._stack = []
        self.close()

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
            self._errors.append(
                {
                    "line": line,
                    "tag": f"</{tag}>",
                    "reason": "extra",
                }
            )
            return
        for i in range(len(self._stack) - 1, -1, -1):
            if self._stack[i][0] == tag:
                for t, line, a in self._stack[i + 1 :]:
                    self._errors.append(
                        {
                            "line": line,
                            "tag": f"<{t}{self._fmt(a)}>",
                            "reason": f"not closed before </{tag}>",
                        }
                    )
                del self._stack[i:]
                return
        self._errors.append(
            {
                "line": line,
                "tag": f"</{tag}",
                "reason": "has no matching open tag",
            }
        )

    @property
    def is_balanced(self) -> bool:
        if self._errors:
            raise TagImbalanceError(self._errors)
        return True

    @staticmethod
    def _fmt(attrs: dict[str, str | None]) -> str:
        return "".join(f" {k}" if v is None else f" {k}={v!r}" for k, v in attrs.items())
