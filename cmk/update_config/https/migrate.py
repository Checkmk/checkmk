#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""
*Known Limitations*

The option `Additional header lines` with value `:abc` will now result in following error:
```
error: invalid value ':abc' for '--header <HEADERS>': invalid HTTP header name
```
According to RFC 7320, a header-name has to be non-empty, and V2 does not support sending invalid HTTP requests.

Why did the user agent change from `check_http/v2.3.3 (monitoring-plugins 2.3.3)` to `checkmk-active-httpv2/2.4.0`?
The migration script does not aim to always preserve behaviour. It makes little sense for `check_httpv2` to impersonate `check_http`.

Selecting the options `Don't wait for document body` and `Fixed string to expect in the content` results in the following error:
```
error: the argument '--without-body' cannot be used with '--body-string <BODY_STRING>'
```
In the version V1, this was also an error with a different message. The new check correctly explains the configuration error.

Why has the `request-target` changed?
V1 supports HTTP/1.0 and HTTP/1.1. V2 only supports HTTP/1.1 and HTTP/2.0. HTTP/1.1 was designed in such a way that old applications can handle the new format. Since `check_http` and `check_httpv2` work differently at the HTTP protocol level, these changes are expected.
"""

from collections.abc import Mapping
from typing import assert_never, Literal

from cmk.update_config.https.conflict_options import (
    CantHaveRegexAndString,
    CantPostData,
    V2ChecksCertificates,
)
from cmk.update_config.https.conflicts import ForMigration, MigratableCert, MigratableUrl
from cmk.update_config.https.render import MIGRATE_POSTFIX


def _migrate_method(method: Literal["GET", "HEAD", "DELETE", "POST", "PUT"]) -> str:
    match method:
        case "GET":
            return "get"
        case "HEAD":
            return "head"
        case "DELETE":
            return "delete"
        case "POST":
            return "post"
        case "PUT":
            return "put"


def _migrate_url_params(
    v2_checks_certificates: V2ChecksCertificates,
    cant_have_regex_and_string: CantHaveRegexAndString,
    cant_post_data: CantPostData,
    url_params: MigratableUrl,
    address_family: str,
) -> tuple[dict[str, object], Mapping[str, object]]:
    match url_params.ssl:
        case None:
            tls_versions = {}
        case "auto":
            # TODO: PMs specified allow_higher False, revisit this, once we have their reasoning.
            tls_versions = {"tls_versions": {"min_version": "auto", "allow_higher": True}}
        case "ssl_1_2":
            tls_versions = {"tls_versions": {"min_version": "tls_1_2", "allow_higher": False}}
        case "ssl_1_1" | "ssl_1" | "ssl_2" | "ssl_3":
            tls_versions = {"tls_versions": {"min_version": "auto", "allow_higher": True}}
        case never:
            assert_never(never)
    match url_params.response_time:
        case None:
            response_time: Mapping[str, object] = {}
        case levels:
            response_time = {"response_time": levels}
    match url_params.timeout:
        case None:
            timeout: Mapping[str, object] = {}
        case timeout_sec:
            timeout = {"timeout": float(timeout_sec)}
    match url_params.user_agent:
        case None:
            user_agent: Mapping[str, object] = {}
        case agent:
            user_agent = {"user_agent": agent}
    match url_params.migrate_add_headers():
        case None:
            add_headers: Mapping[str, object] = {}
        case headers:
            add_headers = {"add_headers": headers}
    match url_params.auth:
        case None:
            auth: Mapping[str, object] = {}
        case user_auth:
            auth = {"auth": ("user_auth", user_auth.model_dump())}
    match url_params.migrate_expect_response_header():
        case None:
            content_header: Mapping[str, object] = {}
        case expect_response_header:
            content_header = {"header": ("string", expect_response_header)}
    match url_params.migrate_expect_response():
        case None:
            server_response: Mapping[str, object] = {}
        case expect_response:
            server_response = {"server_response": {"expected": expect_response}}
    match url_params.onredirect:
        case None:
            redirects: Mapping[str, object] = {"redirects": "ok"}
        case onredirect:
            redirects = {"redirects": onredirect}

    match (
        url_params.migrate_expect_string(),
        url_params.migrate_expect_regex(),
        cant_have_regex_and_string,
    ):
        case None, None, _:
            body: Mapping[str, object] = {}
        case migrate_expect_string, None, _:
            body = {"body": migrate_expect_string}
        case None, migrate_expect_regex, _:
            body = {"body": migrate_expect_regex}
        case migrate_expect_string, migrate_expect_regex, CantHaveRegexAndString.string:
            body = {"body": migrate_expect_string}
        case migrate_expect_string, migrate_expect_regex, CantHaveRegexAndString.regex:
            body = {"body": migrate_expect_regex}
        case migrate_expect_string, migrate_expect_regex, CantHaveRegexAndString.skip:
            raise NotImplementedError()
    match url_params.method, url_params.migrate_to_send_data(), cant_post_data:
        case None, None, _:
            method: Mapping[str, object] = {"method": ("get", None)}
        case "GET" | "HEAD" | "DELETE", None, _:
            method = {"method": (_migrate_method(url_params.method), None)}
        case "POST" | "PUT", send_data, _:
            method = {"method": (_migrate_method(url_params.method), send_data or {})}
        case None, send_data, _:
            method = {"method": ("post", send_data or {})}  # TODO: Is this truly the default?
        case "GET" | "HEAD" | "DELETE", send_data, CantPostData.post:
            method = {"method": ("post", send_data or {})}
        case "GET" | "HEAD" | "DELETE", _send_data, CantPostData.prefermethod:
            method = {"method": (_migrate_method(url_params.method), None)}
        case "GET" | "HEAD" | "DELETE", _send_data, CantPostData.skip:
            raise NotImplementedError()
        case (
            "OPTIONS" | "TRACE" | "CONNECT" | "CONNECT_POST" | "PROPFIND",
            None,
            _,
        ):
            method = {"method": ("get", None)}
        case (
            "OPTIONS" | "TRACE" | "CONNECT" | "CONNECT_POST" | "PROPFIND",
            send_data,
            _,
        ):
            method = {"method": ("post", send_data)}
    match url_params.no_body:
        case None:
            document_body: Mapping[str, object] = {"document_body": "fetch"}
        case True:
            document_body = {"document_body": "ignore"}
    match url_params.page_size:
        case None:
            page_size_new: Mapping[str, object] = {}
        case page_size:
            page_size_new = {"page_size": {"min": page_size.minimum, "max": page_size.maximum}}
    match url_params.max_age:
        case None:
            max_age_new: Mapping[str, object] = {}
        case max_age:
            max_age_new = {"max_age": float(max_age)}
    match v2_checks_certificates:
        case V2ChecksCertificates.keep | V2ChecksCertificates.skip:
            cert: Mapping[str, object] = {}
        case V2ChecksCertificates.disable:
            cert = {"cert": ("no_validation", None)}
    content = {**content_header, **body}
    return (
        {
            **method,  # TODO: Proxy sets this to CONNECT.
            **tls_versions,
            **timeout,
            **user_agent,
            **add_headers,
            **auth,
            **redirects,
            "address_family": address_family,
        },
        {
            **server_response,
            **response_time,
            **({"content": content} if content else {}),
            "document": {
                **document_body,
                **page_size_new,
                **max_age_new,
            },
            **cert,
        },
    )


def _migrate_cert_params(
    cert_params: MigratableCert, address_family: str
) -> tuple[dict[str, object], Mapping[str, object]]:
    return (
        {
            "method": ("get", None),
            "address_family": address_family,
        },
        {
            "cert": ("validate", cert_params.cert_days),
        },
    )


def _migrate_name(name: str) -> Mapping[str, object]:
    # Currently, this implementation is consistent with V1.
    if name.startswith("^"):
        return {"prefix": "none", "name": name[1:] + MIGRATE_POSTFIX}
    return {"prefix": "auto", "name": name + MIGRATE_POSTFIX}


def migrate(for_migration: ForMigration) -> Mapping[str, object]:
    value = for_migration.value
    match value.host.address_family:
        case "any":
            address_family = "any"
        case "ipv4_enforced":
            address_family = "ipv4"
        case "ipv6_enforced":
            address_family = "ipv6"
        case "primary_enforced":
            address_family = "primary"
        case None:
            address_family = "any"
    if isinstance(value.mode[1], MigratableCert):
        connection, remaining_settings = _migrate_cert_params(value.mode[1], address_family)
    else:
        connection, remaining_settings = _migrate_url_params(
            for_migration.config.v2_checks_certificates,
            for_migration.config.cant_have_regex_and_string,
            for_migration.config.cant_post_data,
            value.mode[1],
            address_family,
        )
    if value.host.address is None:
        server = "$HOSTADDRESS$"
    else:
        server = value.host.address[1]
    return {
        "endpoints": [
            {
                "service_name": _migrate_name(name=value.name),
                # Risk: We can't be sure the active checks and the config cache use the same IP look
                # up (but both of them are based on the same user data. Moreover,
                # `primary_ip_config.address` (see `get_ssc_host_config` is slightly differently
                # implemented than `HOSTADDRESS` (see `attrs["address"]` in
                # `cmk/base/config.py:3454`).
                "url": value.url(),
                "individual_settings": {
                    "connection": connection,
                    "server": server,
                    **remaining_settings,
                },
            },
        ],
        "standard_settings": {},
    }
