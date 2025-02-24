#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import enum
from argparse import ArgumentParser
from typing import Iterable, Protocol

from pydantic import BaseModel


class ConflictType(enum.Enum):
    http_1_0_not_supported = "http-1-0-not-supported"
    ssl_incompatible = "ssl-incompatible"
    add_headers_incompatible = "add-headers-incompatible"
    expect_response_header = "expect-response-header"
    cant_have_regex_and_string = "cant-have-regex-and-string"
    only_status_codes_allowed = "only-status-codes-allowed"


class HTTP10NotSupported(enum.Enum):
    skip = "skip"
    ignore = "ignore"

    @classmethod
    def type_(cls) -> ConflictType:
        return ConflictType.http_1_0_not_supported

    @classmethod
    def default(cls) -> "HTTP10NotSupported":
        return cls.skip

    def help(self) -> str:
        cls = type(self)
        match self:
            case cls.skip:
                return "do not migrate rule"
            case cls.ignore:
                return "use HTTP/1.1 with virtual host set to the address"

    @classmethod
    def help_header(cls) -> str:
        return "v2 does not support HTTP/1.0"


class SSLIncompatible(enum.Enum):
    skip = "skip"
    negotiate = "negotiate"

    @classmethod
    def type_(cls) -> ConflictType:
        return ConflictType.ssl_incompatible

    @classmethod
    def default(cls) -> "SSLIncompatible":
        return cls.skip

    def help(self) -> str:
        cls = type(self)
        match self:
            case cls.skip:
                return "do not migrate rule"
            case cls.negotiate:
                return "migrate rule without `SSL` option, allow auto-negotiation"

    @classmethod
    def help_header(cls) -> str:
        return "v2 only support TLS 1.2 or 1.3"


class AdditionalHeaders(enum.Enum):
    skip = "skip"
    ignore = "ignore"

    @classmethod
    def type_(cls) -> ConflictType:
        return ConflictType.add_headers_incompatible

    @classmethod
    def default(cls) -> "AdditionalHeaders":
        return cls.skip

    def help(self) -> str:
        cls = type(self)
        match self:
            case cls.skip:
                return "do not migrate rule"
            case cls.ignore:
                return "create rule without header lines in incompatible format"

    @classmethod
    def help_header(cls) -> str:
        return "`Additional header lines` must be in the format `Header: Value` for migration"


class ExpectResponseHeader(enum.Enum):
    skip = "skip"
    ignore = "ignore"

    @classmethod
    def type_(cls) -> ConflictType:
        return ConflictType.expect_response_header

    @classmethod
    def default(cls) -> "ExpectResponseHeader":
        return cls.skip

    def help(self) -> str:
        cls = type(self)
        match self:
            case cls.skip:
                return "do not migrate rule"
            case cls.ignore:
                return "create rule without this option"

    @classmethod
    def help_header(cls) -> str:
        return "`String to expect in response headers` must be in the format `Header: Value` for migration"


class CantHaveRegexAndString(enum.Enum):
    skip = "skip"
    string = "string"
    regex = "regex"

    @classmethod
    def type_(cls) -> ConflictType:
        return ConflictType.cant_have_regex_and_string

    @classmethod
    def default(cls) -> "CantHaveRegexAndString":
        return cls.skip

    def help(self) -> str:
        match self:
            case CantHaveRegexAndString.skip:
                return "do not migrate rule"
            case CantHaveRegexAndString.string:
                return "create rule choosing string, if two options are available"
            case CantHaveRegexAndString.regex:
                return "create rule choosing regex, if two options are available"

    @classmethod
    def help_header(cls) -> str:
        return "must choose `Fixed string to expect in the content` or `Regular expression to expect in the content`"


class OnlyStatusCodesAllowed(enum.Enum):
    skip = "skip"
    ignore = "ignore"

    @classmethod
    def type_(cls) -> ConflictType:
        return ConflictType.only_status_codes_allowed

    @classmethod
    def default(cls) -> "OnlyStatusCodesAllowed":
        return cls.skip

    def help(self) -> str:
        match self:
            case OnlyStatusCodesAllowed.skip:
                return "do not migrate rule"
            case OnlyStatusCodesAllowed.ignore:
                return "create rule without incompatible entries"

    @classmethod
    def help_header(cls) -> str:
        return (
            "`Strings to expect in server response` must be a three-digit status code for migration"
        )


class Config(BaseModel):
    http_1_0_not_supported: HTTP10NotSupported = HTTP10NotSupported.default()
    ssl_incompatible: SSLIncompatible = SSLIncompatible.default()
    add_headers_incompatible: AdditionalHeaders = AdditionalHeaders.default()
    expect_response_header: ExpectResponseHeader = ExpectResponseHeader.default()
    only_status_codes_allowed: OnlyStatusCodesAllowed = OnlyStatusCodesAllowed.default()
    cant_have_regex_and_string: CantHaveRegexAndString = CantHaveRegexAndString.default()


def add_migrate_parsing(parser: ArgumentParser) -> None:
    parser.add_argument("--write", action="store_true", help="persist changes on disk")
    _add_argument(parser, HTTP10NotSupported, HTTP10NotSupported.default())
    _add_argument(parser, SSLIncompatible, SSLIncompatible.default())
    _add_argument(parser, AdditionalHeaders, AdditionalHeaders.default())
    _add_argument(parser, ExpectResponseHeader, ExpectResponseHeader.default())
    _add_argument(parser, OnlyStatusCodesAllowed, OnlyStatusCodesAllowed.default())
    _add_argument(parser, CantHaveRegexAndString, CantHaveRegexAndString.default())


class Option(Protocol):
    @property
    def value(self) -> str: ...

    def help(self) -> str: ...

    @classmethod
    def help_header(cls) -> str: ...

    @classmethod
    def type_(cls) -> ConflictType: ...


def _help(option: Option, default: Option) -> str:
    if option == default:
        return f"{option.value}: {option.help()} (default)"
    return f"{option.value}: {option.help()}"


def _add_argument(parser: ArgumentParser, option_set: Iterable[Option], default: Option) -> None:
    help_ = [
        f"conflict: {default.help_header()}",
        *(_help(option, default) for option in option_set),
    ]
    parser.add_argument(
        f"--{default.type_().value}",
        default=default.value,
        choices=[option.value for option in option_set],
        help="; ".join(help_),
    )
