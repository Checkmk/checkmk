#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Sequence
from typing import overload, Protocol


class RequestProtocol(Protocol):
    @overload
    def var(self, name: str) -> str | None: ...

    @overload
    def var(self, name: str, default: str) -> str: ...

    @overload
    def var(self, name: str, default: str | None) -> str | None: ...

    def has_var(self, varname: str) -> bool: ...

    def get_integer_input_mandatory(self, varname: str, deflt: int | None = None) -> int: ...

    def get_str_input_mandatory(self, varname: str, deflt: str | None = None) -> str: ...

    @property
    def remote_ip(self) -> str | None: ...


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
