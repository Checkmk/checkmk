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

IntLevels = (
    tuple[Literal[LevelsType.NO_LEVELS], None] | tuple[Literal[LevelsType.FIXED], tuple[int, int]]
)

FloatLevels = (
    tuple[Literal[LevelsType.NO_LEVELS], None]
    | tuple[Literal[LevelsType.FIXED], tuple[float, float]]
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

    if (settings := endpoint.settings) is None:
        return

    if (connection := settings.connection) is not None:
        yield from _connection_args(connection)
    if (response_time := settings.response_time) is not None:
        yield from _response_time_arguments(response_time)
    if (server_response := settings.server_response) is not None:
        yield from _status_code_args(server_response)
    if (cert := settings.cert) is not None:
        yield from _cert_args(cert)


def _connection_args(connection: Connection) -> Iterator[str]:
    if (auth := connection.auth) is not None:
        yield from _auth_args(auth)
    if (tls_versions := connection.tls_versions) is not None:
        yield from _tls_version_arg(tls_versions)
    if (method_spec := connection.method) is not None:
        yield from _send_args(method_spec)
    if (redirects := connection.redirects) is not None:
        yield from _redirect_args(redirects)
    if (http_versions := connection.http_versions) is not None:
        yield from _http_version_args(http_versions)
    if (timeout := connection.timeout) is not None:
        yield from _timeout_args(timeout)
    if (user_agent := connection.user_agent) is not None:
        yield from _user_agent_args(user_agent)
    if (add_headers := connection.add_headers) is not None:
        yield from _send_header_args(add_headers)


def _auth_args(
    auth: (
        tuple[Literal[AuthMode.BASIC_AUTH], UserAuth]
        | tuple[Literal[AuthMode.TOKEN_AUTH], TokenAuth]
    )
) -> Iterator[str]:
    match auth:
        case (AuthMode.BASIC_AUTH, UserAuth(user=user, password=password)):
            yield "--auth-user"
            yield user
            yield from _password_args(password, "--auth-pw-plain", "--auth-pw-pwstore")
        case (AuthMode.TOKEN_AUTH, TokenAuth(header=header, token=token)):
            yield "--token-header"
            yield header
            yield from _password_args(token, "--token-key-plain", "--token-key-pwstore")


def _password_args(password: PasswordSpec, plain_arg: str, store_arg: str) -> Iterator[str]:
    match password:
        case (PasswordType.PASSWORD, pw):
            yield plain_arg
            yield pw
        case (PasswordType.STORE, ident):
            yield store_arg
            yield ident


def _tls_version_arg(tls_versions: EnforceTlsVersion) -> Iterator[str]:
    if tls_versions.min_version is TlsVersion.AUTO:
        return

    tls_version_arg = {
        TlsVersion.TLS_1_0: "tls10",
        TlsVersion.TLS_1_1: "tls11",
        TlsVersion.TLS_1_2: "tls12",
        TlsVersion.TLS_1_3: "tls13",
    }[tls_versions.min_version]

    yield "--min-tls-version" if tls_versions.allow_higher else "--tls-version"
    yield tls_version_arg


def _send_args(method_spec: tuple[HttpMethod, SendData | None]) -> Iterator[str]:
    method, send_data = method_spec

    yield "--method"
    yield {
        HttpMethod.GET: "GET",
        HttpMethod.POST: "POST",
        HttpMethod.PUT: "PUT",
        HttpMethod.DELETE: "DELETE",
        HttpMethod.OPTIONS: "OPTIONS",
        HttpMethod.TRACE: "TRACE",
        HttpMethod.HEAD: "HEAD",
        HttpMethod.CONNECT: "CONNECT",
        HttpMethod.CONNECT_POST: "CONNECT:POST",
        HttpMethod.PROPFIND: "PROPFIND",
    }[method]

    if send_data is None:
        return

    yield "--body"
    yield send_data.body_text

    yield "--content-type"
    match send_data.content_type:
        case (SendDataType.CUSTOM, str(ct_str)):
            yield ct_str
        case (SendDataType.COMMON, ContentType(ct_enum)):
            yield {
                ContentType.APPLICATION_JSON: "application/json",
                ContentType.APPLICATION_OCTET_STREAM: "application/octet-stream",
                ContentType.APPLICATION_XML: "application/xml",
                ContentType.APPLICATION_ZIP: "application/zip",
                ContentType.TEXT_CSV: "text/csv",
                ContentType.TEXT_PLAIN: "text/plain",
                ContentType.TEXT_XML: "text/xml",
                ContentType.TEXT_HTML: "text/html",
            }[ct_enum]


def _redirect_args(policy: RedirectPolicy) -> Iterator[str]:
    yield "--onredirect"
    yield str(policy)


def _http_version_args(http_version: HttpVersion) -> Iterator[str]:
    if http_version is HttpVersion.AUTO:
        return
    yield "--http-version"
    yield {
        HttpVersion.HTTP_2: "http2",
        HttpVersion.HTTP_1_1: "http11",
    }[http_version]


def _timeout_args(timeout: int) -> Iterator[str]:
    yield "--timeout"
    yield str(timeout)


def _user_agent_args(user_agent: str) -> Iterator[str]:
    yield "--user-agent"
    yield user_agent


def _send_header_args(headers: Sequence[HeaderSpec]) -> Iterator[str]:
    for header_spec in headers:
        yield "--header"
        yield f"{header_spec.header_name}:{header_spec.header_value}"


def _response_time_arguments(response_time: FloatLevels) -> Iterator[str]:
    match response_time:
        case (LevelsType.FIXED, (float(warn), float(crit))):
            yield "--response-time-levels"
            yield f"{warn},{crit}"


def _status_code_args(response_codes: ServerResponse) -> Iterator[str]:
    for code in response_codes.expected:
        yield "--status-code"
        yield str(code)


def _cert_args(
    cert_validation: (
        tuple[Literal[Validation.NO_VALIDATION], None]
        | tuple[Literal[Validation.VALIDATE], IntLevels]
    )
) -> Iterator[str]:
    match cert_validation:
        case (Validation.VALIDATE, (LevelsType.FIXED, (int(warn), int(crit)))):
            yield "--certificate-levels"
            yield f"{warn},{crit}"


active_check_httpv2 = ActiveCheckConfig(
    name="httpv2",
    parameter_parser=parse_http_params,
    commands_function=generate_http_services,
)
