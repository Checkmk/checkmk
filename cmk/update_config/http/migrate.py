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
from typing import assert_never

from cmk.update_config.http.conflicts import (
    ForMigration,
    MigratableCert,
    MigratableUrl,
)


def _migrate_header(header: str) -> dict[str, object]:
    name, value = header.split(":", 1)
    return {"header_name": name, "header_value": value.strip()}


def _migrate_url_params(
    url_params: MigratableUrl, address_family: str
) -> tuple[dict[str, object], Mapping[str, object]]:
    match url_params.ssl:
        case None:
            tls_versions = {}
        case "auto":
            # TODO: PMs specified allow_higher False, revisit this, once we have their reasoning.
            tls_versions = {"tls_versions": {"min_version": "auto", "allow_higher": True}}
        case "ssl_1_2":
            tls_versions = {"tls_versions": {"min_version": "tls_1_2", "allow_higher": False}}
        case too_old:
            assert_never(too_old)
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
    match url_params.add_headers:
        case None:
            add_headers: Mapping[str, object] = {}
        case headers:
            add_headers = {"add_headers": [_migrate_header(header) for header in headers]}
    match url_params.auth:
        case None:
            auth: Mapping[str, object] = {}
        case user_auth:
            auth = {"auth": ("user_auth", user_auth.model_dump())}
    match url_params.expect_response_header:
        case None:
            content_header: Mapping[str, object] = {}
        case expect_response_header:
            content_header = {
                "header": ("string", _migrate_header(expect_response_header.strip("\r\n")))
            }
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
    match url_params.expect_string, url_params.expect_regex:
        case None, None:
            body: Mapping[str, object] = {}
        case expect_string, None:
            assert expect_string is not None
            body = {"body": ("string", expect_string)}
        case None, expect_regex:
            assert expect_regex is not None
            body = {
                "body": (
                    "regex",
                    {
                        "regex": expect_regex.regex,
                        "case_insensitive": expect_regex.case_insensitive,
                        "multiline": expect_regex.multiline,
                        "invert": expect_regex.crit_if_found,
                    },
                )
            }
        case _, _:
            raise NotImplementedError()
    match url_params.method, url_params.post_data:
        case None, None:
            method: Mapping[str, object] = {"method": ("get", None)}
        case "GET", None:
            method = {"method": ("get", None)}
        case "HEAD", None:
            method = {"method": ("head", None)}
        case "DELETE", None:
            method = {"method": ("delete", None)}
        case "POST" | "PUT" | None, post_data:
            method_type = {
                "POST": "post",
                "PUT": "put",
                None: "post",  # TODO: Is this truly the default?
            }[url_params.method]
            send_data = (
                {}
                if post_data is None
                else {
                    "send_data": {
                        "content": post_data.data,
                        "content_type": ("custom", post_data.content_type),
                    }
                }
            )
            method = {"method": (method_type, send_data)}
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
            max_age_new = {"max_age": max_age}
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
            "content": {
                **content_header,
                **body,
            },
            "document": {
                **document_body,
                **page_size_new,
                **max_age_new,
            },
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
        return {"prefix": "none", "name": name[1:]}
    return {"prefix": "auto", "name": name}


def migrate(id_: str, for_migration: ForMigration) -> Mapping[str, object]:
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
        connection, remaining_settings = _migrate_url_params(value.mode[1], address_family)
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
                    "server": value.host.address[1],
                    **remaining_settings,
                },
            },
        ],
        "standard_settings": {},
        "from_v1": id_,
    }
