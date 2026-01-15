#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import re
from collections.abc import Iterator, Mapping, Sequence
from enum import StrEnum
from typing import Final, Literal

from pydantic import BaseModel

from cmk.server_side_calls.v1 import (
    ActiveCheckCommand,
    ActiveCheckConfig,
    EnvProxy,
    HostConfig,
    IPAddressFamily,
    NoProxy,
    replace_macros,
    Secret,
    URLProxy,
)

_DAY: Final[int] = 24 * 3600


class HttpVersion(StrEnum):
    AUTO = "auto"
    HTTP_2 = "http_2"
    HTTP_1_1 = "http_1_1"


class TlsVersion(StrEnum):
    AUTO = "auto"
    TLS_1_2 = "tls_1_2"
    TLS_1_3 = "tls_1_3"


class RedirectPolicy(StrEnum):
    OK = "ok"
    WARNING = "warning"
    CRITICAL = "critical"
    FOLLOW = "follow"
    STICKY = "sticky"
    STICKYPORT = "stickyport"


class AddressFamily(StrEnum):
    ANY = "any"
    IPV4 = "ipv4"
    IPV6 = "ipv6"
    PRIMARY = "primary"


class DocumentBodyOption(StrEnum):
    FETCH = "fetch"
    IGNORE = "ignore"


class LevelsType(StrEnum):
    NO_LEVELS = "no_levels"
    FIXED = "fixed"


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


class ServicePrefix(StrEnum):
    AUTO = "auto"
    NONE = "none"


class MatchType(StrEnum):
    STRING = "string"
    REGEX = "regex"


class CertificateValidity(StrEnum):
    VALIDATE = "validate"
    NO_VALIDATION = "no_validation"


FloatLevels = (
    tuple[Literal[LevelsType.NO_LEVELS], None]
    | tuple[Literal[LevelsType.FIXED], tuple[float, float]]
)


class EnforceTlsVersion(BaseModel):
    min_version: TlsVersion
    allow_higher: bool
    compatibility_mode: bool = False


class SendDataInner(BaseModel):
    content: str
    content_type: (
        tuple[Literal[SendDataType.COMMON], ContentType] | tuple[Literal[SendDataType.CUSTOM], str]
    )


class SendData(BaseModel):
    send_data: SendDataInner | None = None


class HeaderSpec(BaseModel):
    header_name: str
    header_value: str


class HeaderRegexSpec(BaseModel):
    header_name_pattern: str
    header_value_pattern: str


class UserAuth(BaseModel):
    user: str
    password: Secret


class TokenAuth(BaseModel):
    header: str
    token: Secret


class Connection(BaseModel):
    method: tuple[HttpMethod, SendData | None]
    http_versions: HttpVersion | None = None
    tls_versions: EnforceTlsVersion | None = None
    proxy: URLProxy | EnvProxy | NoProxy | None = None
    address_family: AddressFamily | None = None
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
    fail_state: Literal[0, 1, 2, 3] | None = None


class HttpSettings(BaseModel):
    server: str | None = None
    connection: Connection | None = None
    response_time: FloatLevels | None = None
    server_response: ServerResponse | None = None
    cert: tuple[CertificateValidity, FloatLevels | None] | None = None
    document: Document | None = None
    content: Content | None = None


class ServiceDescription(BaseModel):
    prefix: ServicePrefix
    name: str


class HttpEndpoint(BaseModel):
    service_name: ServiceDescription
    url: str
    settings: HttpSettings


def parse_http_params(params: Mapping[str, object]) -> Sequence[HttpEndpoint]:
    def _parse_dict(o: object) -> dict:
        if not isinstance(o, dict):
            raise TypeError(o)
        return o

    if not isinstance(endpoints := params["endpoints"], Sequence):
        raise TypeError(endpoints)

    fallbacks = _parse_dict(params.get("standard_settings", {}))
    return [
        HttpEndpoint.model_validate(
            {
                **endpoint,
                "settings": {
                    **fallbacks,
                    **_parse_dict(endpoint.get("individual_settings", {})),
                },
            },
        )
        for endpoint in endpoints
    ]


def generate_http_services(
    params: Sequence[HttpEndpoint], host_config: HostConfig
) -> Iterator[ActiveCheckCommand]:
    for endpoint in params:
        protocol = "HTTPS" if endpoint.url.startswith("https://") else "HTTP"
        prefix = f"{protocol} " if endpoint.service_name.prefix is ServicePrefix.AUTO else ""
        yield ActiveCheckCommand(
            service_description=f"{prefix}{replace_macros(endpoint.service_name.name, host_config.macros)}",
            command_arguments=list(_command_arguments(endpoint, host_config)),
        )


IPV6_PATTERN = re.compile(
    r"(?:\[)?(?<![:.\w])(?:[a-fA-F0-9]{1,4}:){2,7}[a-fA-F0-9]{1,4}(?!\d|[a-fA-F0-9]:)(?:\])?"
)


def _command_arguments(endpoint: HttpEndpoint, host_config: HostConfig) -> Iterator[str | Secret]:
    macros = host_config.macros

    yield "--url"

    def wrap_ipv6(match: re.Match) -> str:
        """Wrap IPv6 addresses in square brackets if they don't already have them."""
        if not match.group(0).startswith("[") and not match.group(0).endswith("]"):
            return f"[{match.group(0)}]"
        return match.group(0)

    yield IPV6_PATTERN.sub(wrap_ipv6, replace_macros(endpoint.url, macros))

    if (server := endpoint.settings.server) is not None:
        yield "--server"
        yield replace_macros(server, macros)
    if (connection := endpoint.settings.connection) is not None:
        yield from _connection_args(connection, host_config)
    if (response_time := endpoint.settings.response_time) is not None:
        yield from _response_time_arguments(response_time)
    if (server_response := endpoint.settings.server_response) is not None:
        yield from _status_code_args(server_response)
    if (cert := endpoint.settings.cert) is not None:
        yield from _cert_args(cert)
    if (document := endpoint.settings.document) is not None:
        yield from _document_args(document)
    if (content := endpoint.settings.content) is not None:
        yield from _content_args(content, host_config.macros)


def _connection_args(connection: Connection, host_config: HostConfig) -> Iterator[str | Secret]:
    yield from _method_args(connection.method)
    if (auth := connection.auth) is not None:
        yield from _auth_args(auth)
    if (tls_versions := connection.tls_versions) is not None:
        yield from _tls_version_arg(tls_versions)
    if (proxy := connection.proxy) is not None:
        yield from _proxy_args(proxy)
    if (address_family := connection.address_family) is not None:
        yield from _address_family_args(address_family, host_config)
    if (redirects := connection.redirects) is not None:
        yield from _redirect_args(redirects)
    if (http_versions := connection.http_versions) is not None:
        yield from _http_version_args(http_versions)
    if (timeout := connection.timeout) is not None:
        yield from _timeout_args(timeout)
    if (user_agent := connection.user_agent) is not None:
        yield from _user_agent_args(replace_macros(user_agent, host_config.macros))
    if (add_headers := connection.add_headers) is not None:
        yield from _send_header_args(add_headers)


def _auth_args(
    auth: (
        tuple[Literal[AuthMode.BASIC_AUTH], UserAuth]
        | tuple[Literal[AuthMode.TOKEN_AUTH], TokenAuth]
    ),
) -> tuple[str | Secret, ...]:
    match auth:
        case (AuthMode.BASIC_AUTH, UserAuth(user=user, password=password)):
            return ("--auth-user", user, "--auth-pw-pwstore", password)
        case (AuthMode.TOKEN_AUTH, TokenAuth(header=header, token=token)):
            return ("--token-header", header, "--token-key-pwstore", token)
    raise ValueError(auth)


def _tls_version_arg(tls_versions: EnforceTlsVersion) -> Iterator[str]:
    if tls_versions.compatibility_mode:
        yield "--tls-compatibility-mode"

    if tls_versions.min_version is TlsVersion.AUTO:
        return

    tls_version_arg = {
        TlsVersion.TLS_1_2: "tls12",
        TlsVersion.TLS_1_3: "tls13",
    }[tls_versions.min_version]

    yield "--min-tls-version" if tls_versions.allow_higher else "--tls-version"
    yield tls_version_arg


def _proxy_args(proxy: EnvProxy | URLProxy | NoProxy) -> Iterator[str]:
    match proxy:
        case EnvProxy():
            return
        case NoProxy():
            yield "--ignore-proxy-env"
        # Note: check_httpv2 is capable of taking the credentials separately,
        # and to read the password from password store, with arguments
        # --proxy-user and --proxy-pw-plain/--proxy-pw-pwstore.
        # However, if everthing is passed via url, as it's done now, check_httpv2 is
        # also capable of handling that correctly.
        case URLProxy(url=url):
            yield "--proxy-url"
            yield url


def _address_family_args(address_family: AddressFamily, host_config: HostConfig) -> Iterator[str]:
    match address_family:
        case AddressFamily.ANY:
            return
        case AddressFamily.IPV4:
            yield "--force-ip-version"
            yield "ipv4"
        case AddressFamily.IPV6:
            yield "--force-ip-version"
            yield "ipv6"
        case AddressFamily.PRIMARY:
            try:
                primary_family = host_config.primary_ip_config.family
            except ValueError:
                return
            yield "--force-ip-version"
            yield "ipv4" if primary_family is IPAddressFamily.IPV4 else "ipv6"


def _method_args(method_spec: tuple[HttpMethod, SendData | None]) -> Iterator[str]:
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

    yield from _send_data_args(send_data)


def _send_data_args(send_data: SendData) -> Iterator[str]:
    if (send_data_inner := send_data.send_data) is None:
        return

    yield "--body"
    yield send_data_inner.content

    yield "--content-type"
    match send_data_inner.content_type:
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


def _cert_args(cert_validation: tuple[CertificateValidity, FloatLevels | None]) -> Iterator[str]:
    match cert_validation:
        case (CertificateValidity.NO_VALIDATION, _):
            yield "--disable-cert"
            return
        case (CertificateValidity.VALIDATE, cert_levels):
            match cert_levels:
                case (LevelsType.FIXED, (float(warn), float(crit))):
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


def _content_args(content: Content, macros: Mapping[str, str]) -> Iterator[str]:
    if (header := content.header) is not None:
        yield from _header_match_args(header)
    if (body := content.body) is not None:
        yield from _body_match_args(body, macros)
    if (fail_state := content.fail_state) is not None:
        yield "--content-search-fail-state"
        match fail_state:
            case 0:
                yield "ok"
            case 1:
                yield "warning"
            case 2:
                yield "critical"
            case 3:
                yield "unknown"


def _header_match_args(
    header: (
        tuple[Literal[MatchType.STRING], HeaderSpec] | tuple[Literal[MatchType.REGEX], HeaderRegex]
    ),
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
    body: (tuple[Literal[MatchType.STRING], str] | tuple[Literal[MatchType.REGEX], BodyRegex]),
    macros: Mapping[str, str],
) -> Iterator[str]:
    match body:
        case (MatchType.STRING, str(string)):
            yield "--body-string"
            yield replace_macros(string, macros)

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
