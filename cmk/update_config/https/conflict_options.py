#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import enum
from argparse import ArgumentParser
from collections.abc import Iterable
from typing import Protocol

from pydantic import BaseModel


class ConflictType(enum.Enum):
    invalid_value = "invalid-value"
    ssl_incompatible = "ssl-incompatible"
    add_headers_incompatible = "add-headers-incompatible"
    expect_response_header = "expect-response-header"
    only_status_codes_allowed = "only-status-codes-allowed"
    cant_post_data = "cant-post-data"
    method_unavailable = "method-unavailable"
    cant_disable_sni_with_https = "cant-disable-sni-with-https"
    v1_checks_redirect_response = "v1-checks-redirect-response"
    cant_construct_url = "cant-construct-url"
    cant_migrate_proxy = "cant-migrate-proxy"
    cant_have_regex_and_string = "cant-have-regex-and-string"
    v2_checks_certificates = "v2-checks-certificates"
    cant_ignore_certificate_validation = "cant-ignore-certificate-validation"


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


class CantPostData(enum.Enum):
    skip = "skip"
    post = "post"
    prefermethod = "prefermethod"

    @classmethod
    def type_(cls) -> ConflictType:
        return ConflictType.cant_post_data

    @classmethod
    def default(cls) -> "CantPostData":
        return cls.skip

    def help(self) -> str:
        match self:
            case CantPostData.skip:
                return "do not migrate rule"
            case CantPostData.post:
                return "use POST method with migrating post data"
            case CantPostData.prefermethod:
                return "migrate `HTTP method` without migrating post data"

    @classmethod
    def help_header(cls) -> str:
        return (
            "the option `Send HTTP POST data` is incompatible with HTTP methods GET, DELETE, HEAD"
        )


class MethodUnavailable(enum.Enum):
    skip = "skip"
    ignore = "ignore"

    @classmethod
    def type_(cls) -> ConflictType:
        return ConflictType.method_unavailable

    @classmethod
    def default(cls) -> "MethodUnavailable":
        return cls.skip

    def help(self) -> str:
        match self:
            case MethodUnavailable.skip:
                return "do not migrate rule"
            case MethodUnavailable.ignore:
                return "ignore unsupported HTTP method and use POST if post data is present, otherwise use GET"

    @classmethod
    def help_header(cls) -> str:
        return "v2 does not support OPTIONS, TRACE, CONNECT, CONNECT_POST, PROPFIND options"


class CantDisableSNIWithHTTPS(enum.Enum):
    skip = "skip"
    ignore = "ignore"

    @classmethod
    def type_(cls) -> ConflictType:
        return ConflictType.cant_disable_sni_with_https

    @classmethod
    def default(cls) -> "CantDisableSNIWithHTTPS":
        return cls.skip

    def help(self) -> str:
        match self:
            case CantDisableSNIWithHTTPS.skip:
                return "do not migrate rule"
            case CantDisableSNIWithHTTPS.ignore:
                return "ignore `Disable SSL/TLS host name extension support` option, enable SNI"

    @classmethod
    def help_header(cls) -> str:
        return "v2 does not have option to use TLS without SNI"


class V1ChecksRedirectResponse(enum.Enum):
    skip = "skip"
    acknowledge = "acknowledge"

    @classmethod
    def type_(cls) -> ConflictType:
        return ConflictType.v1_checks_redirect_response

    @classmethod
    def default(cls) -> "V1ChecksRedirectResponse":
        return cls.skip

    def help(self) -> str:
        match self:
            case V1ChecksRedirectResponse.skip:
                return "do not migrate rule"
            case V1ChecksRedirectResponse.acknowledge:
                return "migrate both options despite change in behaviour"

    @classmethod
    def help_header(cls) -> str:
        return "version v1 will checks the response obtained before following the redirect, version v2 will first follow the redirect and then check the status code"


class CantConstructURL(enum.Enum):
    skip = "skip"
    force = "force"

    @classmethod
    def type_(cls) -> ConflictType:
        return ConflictType.cant_construct_url

    @classmethod
    def default(cls) -> "CantConstructURL":
        return cls.skip

    def help(self) -> str:
        match self:
            case CantConstructURL.skip:
                return "do not migrate rule"
            case CantConstructURL.force:
                return "use invalid URL"

    @classmethod
    def help_header(cls) -> str:
        return "URL can not be properly constructed in v2"


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
                return "create rule choosing string"
            case CantHaveRegexAndString.regex:
                return "create rule choosing regex"

    @classmethod
    def help_header(cls) -> str:
        return "must choose `Fixed string to expect in the content` or `Regular expression to expect in the content`, but not both"


class V2ChecksCertificates(enum.Enum):
    skip = "skip"
    keep = "keep"
    disable = "disable"

    @classmethod
    def type_(cls) -> ConflictType:
        return ConflictType.v2_checks_certificates

    @classmethod
    def default(cls) -> "V2ChecksCertificates":
        return cls.skip

    def help(self) -> str:
        match self:
            case V2ChecksCertificates.skip:
                return "do not migrate rule"
            case V2ChecksCertificates.keep:
                return "migrate with certificate validation"
            case V2ChecksCertificates.disable:
                return "create the rule and ignore certificates"

    @classmethod
    def help_header(cls) -> str:
        return (
            "v1 did not check if the certificate is valid while v2 checks the validity by default"
        )


class CantIgnoreCertificateValidation(enum.Enum):
    skip = "skip"
    keep = "keep"

    @classmethod
    def type_(cls) -> ConflictType:
        return ConflictType.cant_ignore_certificate_validation

    @classmethod
    def default(cls) -> "CantIgnoreCertificateValidation":
        return cls.skip

    def help(self) -> str:
        match self:
            case CantIgnoreCertificateValidation.skip:
                return "do not migrate rule"
            case CantIgnoreCertificateValidation.keep:
                return "create the rule with certificate validation"

    @classmethod
    def help_header(cls) -> str:
        return (
            "v1 checks the certificate age and ignores other validation errors but v2 must "
            "validate the certificate when checking the age"
        )


class Config(BaseModel):
    ssl_incompatible: SSLIncompatible = SSLIncompatible.default()
    add_headers_incompatible: AdditionalHeaders = AdditionalHeaders.default()
    expect_response_header: ExpectResponseHeader = ExpectResponseHeader.default()
    only_status_codes_allowed: OnlyStatusCodesAllowed = OnlyStatusCodesAllowed.default()
    cant_post_data: CantPostData = CantPostData.default()
    method_unavailable: MethodUnavailable = MethodUnavailable.default()
    cant_disable_sni_with_https: CantDisableSNIWithHTTPS = CantDisableSNIWithHTTPS.default()
    v1_checks_redirect_response: V1ChecksRedirectResponse = V1ChecksRedirectResponse.default()
    cant_construct_url: CantConstructURL = CantConstructURL.default()
    cant_have_regex_and_string: CantHaveRegexAndString = CantHaveRegexAndString.default()
    v2_checks_certificates: V2ChecksCertificates = V2ChecksCertificates.default()
    cant_ignore_certificate_validation: CantIgnoreCertificateValidation = (
        CantIgnoreCertificateValidation.default()
    )


def add_migrate_parsing(parser: ArgumentParser) -> ArgumentParser:
    parser.add_argument_group()
    write_or_dry_run_group = parser.add_mutually_exclusive_group(required=True)
    write_or_dry_run_group.add_argument(
        "--write",
        action="store_true",
        help="Persist changes on disk, v2 rules are created as deactivated, will have ‘migrated’ suffix in the service name and a reference to the original v1 rule in the description, use Finalize to clean this up.",
        dest="write",
    )
    write_or_dry_run_group.add_argument(
        "--dry-run",
        action="store_false",
        help=(
            "Attempts to migrate the rules as it would with ‘--write’, but does not save the rules in the end. "
            "Use this option to understand which conflicts will be encountered."
        ),
        dest="write",
    )
    _add_argument(parser, SSLIncompatible, SSLIncompatible.default())
    _add_argument(parser, AdditionalHeaders, AdditionalHeaders.default())
    _add_argument(parser, ExpectResponseHeader, ExpectResponseHeader.default())
    _add_argument(parser, OnlyStatusCodesAllowed, OnlyStatusCodesAllowed.default())
    _add_argument(parser, CantPostData, CantPostData.default())
    _add_argument(parser, MethodUnavailable, MethodUnavailable.default())
    _add_argument(parser, CantDisableSNIWithHTTPS, CantDisableSNIWithHTTPS.default())
    _add_argument(parser, V1ChecksRedirectResponse, V1ChecksRedirectResponse.default())
    _add_argument(parser, CantConstructURL, CantConstructURL.default())
    _add_argument(parser, CantHaveRegexAndString, CantHaveRegexAndString.default())
    _add_argument(parser, V2ChecksCertificates, V2ChecksCertificates.default())
    _add_argument(
        parser, CantIgnoreCertificateValidation, CantIgnoreCertificateValidation.default()
    )
    return parser


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
        f"Conflict: {default.help_header()}",
        *(_help(option, default) for option in option_set),
    ]
    parser.add_argument(
        f"--{default.type_().value}",
        default=default.value,
        choices=[option.value for option in option_set],
        help="; ".join(help_),
    )
