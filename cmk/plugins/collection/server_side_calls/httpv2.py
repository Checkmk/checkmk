#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Iterator, Mapping, Sequence
from enum import StrEnum
from typing import Final, Literal

from pydantic import BaseModel

from cmk.server_side_calls.v1 import (
    ActiveCheckCommand,
    ActiveCheckConfig,
    HostConfig,
    HTTPProxy,
    parse_http_proxy,
    replace_macros,
)

_DAY: Final[int] = 24 * 3600


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


class ProxyMode(StrEnum):
    ENVIRONMENT = "environment"
    NO_PROXY = "no_proxy"
    GLOBAL = "global"
    URL = "url"


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
    HEAD = "head"
    POST = "post"
    PUT = "put"
    DELETE = "delete"


class SendDataType(StrEnum):
    COMMON = "common"
    CUSTOM = "custom"


class AuthMode(StrEnum):
    BASIC_AUTH = "user_auth"
    TOKEN_AUTH = "token_auth"


class ContentType(StrEnum):
    APPLICATION_JSON = "application_json"
    APPLICATION_XML = "application_xml"
    APPLICATION_X_WWW_FORM_URLENCODED = "application_x_www_form_urlencoded"
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


ProxySpec = (
    tuple[Literal[ProxyMode.ENVIRONMENT], Literal[ProxyMode.ENVIRONMENT]]
    | tuple[Literal[ProxyMode.NO_PROXY], None]
    | tuple[Literal[ProxyMode.GLOBAL], str]
    | tuple[Literal[ProxyMode.URL], str]
)

PasswordSpec = tuple[PasswordType, str]

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
    proxy: ProxySpec | None = None
    redirects: RedirectPolicy | None = None
    timeout: float | None = None
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
        | tuple[Literal[Validation.VALIDATE], FloatLevels]
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
    params: Sequence[HttpEndpoint], host_config: HostConfig, http_proxies: Mapping[str, HTTPProxy]
) -> Iterator[ActiveCheckCommand]:
    for endpoint in params:
        protocol = "HTTPS" if endpoint.url.startswith("https://") else "HTTP"
        prefix = f"{protocol} " if endpoint.service_name.prefix is ServicePrefix.AUTO else ""
        endpoint.url = replace_macros(endpoint.url, host_config.macros)
        yield ActiveCheckCommand(
            service_description=f"{prefix}{endpoint.service_name.name}",
            command_arguments=list(_command_arguments(endpoint, http_proxies)),
        )


def _command_arguments(
    endpoint: HttpEndpoint, http_proxies: Mapping[str, HTTPProxy]
) -> Iterator[str]:
    yield "--url"
    yield endpoint.url

    if (settings := endpoint.settings) is None:
        return

    if (connection := settings.connection) is not None:
        yield from _connection_args(connection, http_proxies)
    if (response_time := settings.response_time) is not None:
        yield from _response_time_arguments(response_time)
    if (server_response := settings.server_response) is not None:
        yield from _status_code_args(server_response)
    if (cert := settings.cert) is not None:
        yield from _cert_args(cert)
    if (document := settings.document) is not None:
        yield from _document_args(document)
    if (content := settings.content) is not None:
        yield from _content_args(content)


def _connection_args(
    connection: Connection, http_proxies: Mapping[str, HTTPProxy]
) -> Iterator[str]:
    if (auth := connection.auth) is not None:
        yield from _auth_args(auth)
    if (tls_versions := connection.tls_versions) is not None:
        yield from _tls_version_arg(tls_versions)
    if (method_spec := connection.method) is not None:
        yield from _send_args(method_spec)
    if (proxy_spec := connection.proxy) is not None:
        yield from _proxy_args(proxy_spec, http_proxies)
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


def _proxy_args(proxy_spec: ProxySpec, http_proxies: Mapping[str, HTTPProxy]) -> Iterator[str]:
    match proxy_spec:
        case (ProxyMode.ENVIRONMENT, ProxyMode.ENVIRONMENT):
            return
        case (ProxyMode.NO_PROXY, None):
            yield "--ignore-proxy-env"
        # Note: check_httpv2 is capable of taking the credentials separately,
        # and to read the password from password store, with arguments
        # --proxy-user and --proxy-pw-plain/--proxy-pw-pwstore.
        # However, if everthing is passed via url, as it's done now, check_httpv2 is
        # also capable of handling that correctly.
        case (ProxyMode.URL, str(url)):
            yield "--proxy-url"
            yield url
        case (ProxyMode.GLOBAL, _):
            yield "--proxy-url"
            yield parse_http_proxy(proxy_spec, http_proxies)


def _send_args(method_spec: tuple[HttpMethod, SendData | None]) -> Iterator[str]:
    method, send_data = method_spec

    yield "--method"
    yield {
        HttpMethod.GET: "GET",
        HttpMethod.HEAD: "HEAD",
        HttpMethod.POST: "POST",
        HttpMethod.PUT: "PUT",
        HttpMethod.DELETE: "DELETE",
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
                ContentType.APPLICATION_XML: "application/xml",
                ContentType.APPLICATION_X_WWW_FORM_URLENCODED: "application/x-www-form-urlencoded",
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


def _timeout_args(timeout: float) -> Iterator[str]:
    yield "--timeout"
    yield str(round(timeout))


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
        | tuple[Literal[Validation.VALIDATE], FloatLevels]
    )
) -> Iterator[str]:
    match cert_validation:
        case (Validation.VALIDATE, (LevelsType.FIXED, (float(warn), float(crit)))):
            yield "--certificate-levels"
            yield f"{round(warn / _DAY)},{round(crit / _DAY)}"


def _document_args(document: Document) -> Iterator[str]:
    yield from _fetch_document_args(document.document_body)
    if (max_age := document.max_age) is not None:
        yield from _max_document_age_args(max_age)
    if (page_size := document.page_size) is not None:
        yield from _page_size_args(page_size)


def _fetch_document_args(fetch_body: DocumentBodyOption) -> Iterator[str]:
    if fetch_body is DocumentBodyOption.IGNORE:
        yield "--without-body"


def _max_document_age_args(max_age: float) -> Iterator[str]:
    yield "--document-age-levels"  # TODO(au): Rename argument. This is only one level
    yield str(int(max_age))


def _page_size_args(page_size: PageSize) -> Iterator[str]:
    if page_size.min is None and page_size.max is None:
        return

    min_part = "0" if page_size.min is None else str(page_size.min)
    max_part = "" if page_size.max is None else f",{page_size.max}"

    yield "--page-size"
    yield f"{min_part}{max_part}"


def _content_args(content: Content) -> Iterator[str]:
    if (header := content.header) is not None:
        yield from _header_match_args(header)
    if (body := content.body) is not None:
        yield from _body_match_args(body)


def _header_match_args(
    header: (
        tuple[Literal[MatchType.STRING], HeaderSpec] | tuple[Literal[MatchType.REGEX], HeaderRegex]
    )
) -> Iterator[str]:
    match header:
        case (MatchType.STRING, HeaderSpec(header_name=name, header_value=value)):
            yield "--header-strings"
            yield f"{name}:{value}"

        case (
            MatchType.REGEX,
            HeaderRegex(
                regex=HeaderRegexSpec(header_name_pattern=name, header_value_pattern=value),
                case_insensitive=case_insensitive,
                invert=invert,
            ),
        ):
            yield "--header-regexes"
            flagged_value = f"(?i){value}" if case_insensitive else value
            # Note: Header name is always case insensitive, so there's no need to apply the flag
            yield f"{name}:{flagged_value}"
            if invert:
                yield "--header-regexes-invert"


def _body_match_args(
    body: tuple[Literal[MatchType.STRING], str] | tuple[Literal[MatchType.REGEX], BodyRegex]
) -> Iterator[str]:
    match body:
        case (MatchType.STRING, str(string)):
            yield "--body-string"
            yield string

        case (
            MatchType.REGEX,
            BodyRegex(
                regex=regex,
                case_insensitive=case_insensitive,
                multiline=multiline,
                invert=invert,
            ),
        ):
            yield "--body-regex"
            # multiline == True translates to (?m), while multiline == False translates to (?s):
            # m: match anchors ^ and $ on line beginnings/endings
            # s: match "." also on newlines. The standard is to *not* match the dot on newlines.
            yield f"(?{'i' if case_insensitive else ''}{'m' if multiline else 's'}){regex}"
            if invert:
                yield "--body-regex-invert"


active_check_httpv2 = ActiveCheckConfig(
    name="httpv2",
    parameter_parser=parse_http_params,
    commands_function=generate_http_services,
)
