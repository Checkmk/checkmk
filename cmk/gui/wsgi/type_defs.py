#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from types import TracebackType
from typing import (
    Any,
    Callable,
    Dict,
    Iterable,
    List,
    Literal,
    Optional,
    Protocol,
    Tuple,
    TypedDict,
    Union,
)

from cmk.utils.type_defs import UserId

Scope = List[str]
UnixTimeStamp = int  # restrict to positive numbers
Audience = Union[str, List[str]]
TokenType = Literal["access_token", "refresh_token"]
AuthType = Literal["automation", "cookie", "webserver", "http_header"]
RFC7662 = TypedDict(
    "RFC7662",
    {
        "active": bool,
        "scope": AuthType,
        "client_id": str,
        "username": str,
        "token_type": TokenType,
        "exp": UnixTimeStamp,  # expires
        "iat": UnixTimeStamp,  # issued
        "nbf": UnixTimeStamp,  # not before
        "sub": UserId,  # subject
        "aud": Audience,
        "iss": str,  # issuer
        "jti": str,  # json web token-identifier
    },
    total=False,
)
HostGroup = TypedDict(
    "HostGroup",
    {
        "alias": str,
    },
)

ExcInfo = Union[Tuple[type, BaseException, Optional[TracebackType]], Tuple[None, None, None]]


# stable
class StartResponse(Protocol):
    def __call__(
        self, status: str, headers: list[tuple[str, str]], exc_info: Optional[ExcInfo] = ...
    ) -> Callable[[bytes], Any]:
        ...


WSGIEnvironment = Dict[str, Any]  # stable
WSGIApplication = Callable[[WSGIEnvironment, StartResponse], Iterable[bytes]]  # stable
WSGIResponse = Iterable[bytes]


# WSGI input streams per PEP 3333, stable
class InputStream(Protocol):
    def read(self, size: int = ...) -> bytes:
        ...

    def readline(self, size: int = ...) -> bytes:
        ...

    def readlines(self, hint: int = ...) -> list[bytes]:
        ...

    def __iter__(self) -> Iterable[bytes]:
        return iter([])  # thanks pylint :/


# WSGI error streams per PEP 3333, stable
class ErrorStream(Protocol):
    def flush(self) -> None:
        ...

    def write(self, s: str) -> None:
        ...

    def writelines(self, seq: list[str]) -> None:
        ...


class _Readable(Protocol):
    def read(self, size: int = ...) -> bytes:
        ...


# Optional file wrapper in wsgi.file_wrapper
class FileWrapper(Protocol):
    def __call__(self, file: _Readable, block_size: int = ...) -> Iterable[bytes]:
        ...
