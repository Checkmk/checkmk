#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Iterator, Mapping, Sequence
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel

from cmk.server_side_calls.v1 import ActiveCheckCommand, ActiveCheckConfig, HostConfig, HTTPProxy


class HttpVersion(StrEnum):
    AUTO = "auto"
    HTTP_2 = "http_2"
    HTTP_1_1 = "http_1_1"


class TlsVersion(StrEnum):
    AUTO = "auto"
    TLS_1_0 = "tls_1_0"
    TLS_1_1 = "tls_1_1"
    TLS_1_2 = "tls_1_2"
    TLS_1_3 = "tls_1_3"


class RedirectPolicy(StrEnum):
    OK = "ok"
    WARNING = "warning"
    CRITICAL = "critical"
    FOLLOW = "follow"
    STICKY = "sticky"
    STICKYPORT = "stickyport"


class DocumentBodyOption(StrEnum):
    FETCH = "fetch"
    IGNORE = "ignore"


class LevelsType(StrEnum):
    NO_LEVELS = "no_levels"
    FIXED = "fixed"


class Validation(StrEnum):
    NO_VALIDATION = "no_validation"
    VALIDATE = "validate"


class HttpMethod(StrEnum):
    GET = "get"
    POST = "post"
    PUT = "put"
    DELETE = "delete"
    OPTIONS = "options"
    TRACE = "trace"
    HEAD = "head"
    CONNECT = "connect"
    CONNECT_POST = "connect_post"
    PROPFIND = "propfind"


class SendDataType(StrEnum):
    COMMON = "common"
    CUSTOM = "custom"


class AuthMode(StrEnum):
    BASIC_AUTH = "user_auth"
    TOKEN_AUTH = "token_auth"


class ContentType(StrEnum):
    APPLICATION_JSON = "application_json"
    APPLICATION_OCTET_STREAM = "application_octet_stream"
    APPLICATION_XML = "application_xml"
    APPLICATION_ZIP = "application_zip"
    TEXT_CSV = "text_csv"
    TEXT_PLAIN = "text_plain"
    TEXT_XML = "text_xml"
    TEXT_HTML = "text_html"


class PasswordType(StrEnum):
    PASSWORD = "password"
    STORE = "store"


class ServicePrefix(StrEnum):
    AUTO = "auto"
    NONE = "none"


class MatchType(StrEnum):
    STRING = "string"
    REGEX = "regex"


PasswordSpec = tuple[PasswordType, str]

FloatLevels = (
    tuple[Literal[LevelsType.NO_LEVELS], None]
    | tuple[Literal[LevelsType.FIXED], tuple[float, float]]
)

IntLevels = (
    tuple[Literal[LevelsType.NO_LEVELS], None] | tuple[Literal[LevelsType.FIXED], tuple[int, int]]
)


class EnforceTlsVersion(BaseModel):
    min_version: TlsVersion
    allow_higher: bool


class SendData(BaseModel):
    body_text: str
    content_type: (
        tuple[Literal[SendDataType.COMMON], ContentType] | tuple[Literal[SendDataType.CUSTOM], str]
    )


class HeaderSpec(BaseModel):
    header_name: str
    header_value: str


class HeaderRegexSpec(BaseModel):
    header_name_pattern: str
    header_value_pattern: str


class UserAuth(BaseModel):
    user: str
    password: PasswordSpec


class TokenAuth(BaseModel):
    header: str
    token: PasswordSpec


class Connection(BaseModel):
    http_versions: HttpVersion | None = None
    tls_versions: EnforceTlsVersion | None = None
    method: tuple[HttpMethod, SendData | None] | None = None  # TODO(ma): CMK-15749
    redirects: RedirectPolicy | None = None
    timeout: int | None = None
    user_agent: str | None = None
    add_headers: list[HeaderSpec] | None = None
    auth: (
        tuple[Literal[AuthMode.BASIC_AUTH], UserAuth]
        | tuple[Literal[AuthMode.TOKEN_AUTH], TokenAuth]
        | None
    ) = None


class ServerResponse(BaseModel):
    expected: list[int]


class PageSize(BaseModel):
    min: int | None = None
    max: int | None = None


class Document(BaseModel):
    document_body: DocumentBodyOption
    max_age: float | None = None
    page_size: PageSize | None = None


class HeaderRegex(BaseModel):
    regex: HeaderRegexSpec
    case_insensitive: bool
    invert: bool


class BodyRegex(BaseModel):
    regex: str
    case_insensitive: bool
    multiline: bool
    invert: bool


class Content(BaseModel):
    header: (
        tuple[Literal[MatchType.STRING], HeaderSpec]
        | tuple[Literal[MatchType.REGEX], HeaderRegex]
        | None
    ) = None
    body: (
        tuple[Literal[MatchType.STRING], str] | tuple[Literal[MatchType.REGEX], BodyRegex] | None
    ) = None


class HttpSettings(BaseModel):
    connection: Connection | None = None
    response_time: FloatLevels | None = None
    server_response: ServerResponse | None = None
    cert: (
        tuple[Literal[Validation.NO_VALIDATION], None]
        | tuple[Literal[Validation.VALIDATE], IntLevels]
        | None
    ) = None
    document: Document | None = None
    content: Content | None = None


class ServiceDescription(BaseModel):
    prefix: ServicePrefix
    name: str


class HttpEndpoint(BaseModel):
    service_name: ServiceDescription
    url: str
    settings: HttpSettings | None = None


class RawEndpoint(BaseModel):
    service_name: ServiceDescription
    url: str
    individual_settings: HttpSettings | None = None


class RawParams(BaseModel):
    endpoints: list[RawEndpoint]
    standard_settings: HttpSettings | None = None


def parse_http_params(raw_params: Mapping[str, object]) -> Sequence[HttpEndpoint]:
    params = RawParams.model_validate(raw_params)
    return [
        HttpEndpoint(
            service_name=endpoint.service_name,
            url=endpoint.url,
            settings=_merge_settings(params.standard_settings, endpoint.individual_settings),
        )
        for endpoint in params.endpoints
    ]


def _merge_settings(
    standard: HttpSettings | None, individual: HttpSettings | None
) -> HttpSettings | None:
    if individual is None:
        return standard

    if standard is None:
        return individual

    return HttpSettings.model_validate(
        standard.model_dump(exclude_none=True) | individual.model_dump(exclude_none=True)
    )


def generate_http_services(
    params: Sequence[HttpEndpoint], host_config: HostConfig, _http_proxies: Mapping[str, HTTPProxy]
) -> Iterator[ActiveCheckCommand]:
    for endpoint in params:
        protocol = "HTTPS" if endpoint.url.startswith("https://") else "HTTP"
        prefix = f"{protocol} " if endpoint.service_name.prefix is ServicePrefix.AUTO else ""
        yield ActiveCheckCommand(
            service_description=f"{prefix}{endpoint.service_name.name}",
            command_arguments=list(_command_arguments(endpoint)),
        )


def _command_arguments(endpoint: HttpEndpoint) -> Iterator[str]:
    yield "--url"
    yield endpoint.url


active_check_httpv2 = ActiveCheckConfig(
    name="httpv2",
    parameter_parser=parse_http_params,
    commands_function=generate_http_services,
)
