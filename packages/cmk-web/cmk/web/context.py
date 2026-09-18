#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Iterator, Sequence
from typing import overload, Protocol


class RequestProtocol(Protocol):
    @property
    def path(self) -> str: ...

    # Mirrors cmk.gui's Request.var, overloads and parameter names included: a Protocol
    # only matches when both agree.
    @overload
    def var(self, name: str) -> str | None: ...

    @overload
    def var(self, name: str, default: str) -> str: ...

    @overload
    def var(self, name: str, default: str | None) -> str | None: ...

    def has_var(self, varname: str) -> bool: ...

    def itervars(self, prefix: str = "") -> Iterator[tuple[str, str]]: ...

    def get_integer_input_mandatory(self, varname: str, deflt: int | None = None) -> int: ...

    def get_str_input_mandatory(self, varname: str, deflt: str | None = None) -> str: ...

    @property
    def remote_ip(self) -> str | None: ...

    def cookie(self, varname: str, default: str | None = None) -> str | None: ...

    @property
    def is_secure(self) -> bool: ...


class ResponseProtocol(Protocol):
    """Mirrors the parts of cmk.gui's Response the web package writes to."""

    # Mirrors werkzeug's Response.set_cookie: the parameters we use are keyword-only
    # here because their position differs in the implementation. In contrast to
    # werkzeug, "path" has no default: its "/" would set the cookie outside of the
    # site's URL prefix, so callers have to name the path explicitly.
    def set_cookie(self, key: str, value: str = "", *, path: str, secure: bool = False) -> None: ...

    def set_http_cookie(
        self, key: str, value: str, *, secure: bool, max_age: int | None = None
    ) -> None: ...


class UserProtocol(Protocol):
    def may(self, pname: str) -> bool: ...


class ActionUrlBuilder(Protocol):
    """Builds a transaction- and CSRF-protected action URL.

    Injected by ``cmk.gui`` so a feature page can link to an action endpoint
    without depending on the transaction manager or session.
    """

    def __call__(
        self, variables: Sequence[tuple[str, str | int | None]], *, filename: str
    ) -> str: ...
