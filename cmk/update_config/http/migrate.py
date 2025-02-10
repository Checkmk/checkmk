#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Mapping

from cmk.update_config.http.conflicts import (
    MigratableCert,
    MigratableUrl,
    MigratableValue,
)


def _migrate_header(header: str) -> dict[str, object]:
    name, value = header.split(":", 1)
    return {"header_name": name, "header_value": value.strip()}  # TODO: This is not a 1:1 mapping.


def _migrate_url_params(
    url_params: MigratableUrl, address_family: str
) -> tuple[str, dict[str, object], Mapping[str, object]]:
    path = url_params.uri or ""
    match url_params.ssl:
        case None:
            tls_versions = {}
        case "auto":
            # TODO: PMs specified allow_higher False, revisit this, once we have their reasoning.
            tls_versions = {"tls_versions": {"min_version": "auto", "allow_higher": True}}
        case "ssl_1_2":
            tls_versions = {"tls_versions": {"min_version": "tls_1_2", "allow_higher": False}}
        case "ssl_1_3":
            tls_versions = {"tls_versions": {"min_version": "tls_1_3", "allow_higher": False}}
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
            # TODO: This implicitly changes the user agent from `check_http/v2.3.3
            # (monitoring-plugins 2.3.3)` to `checkmk-active-httpv2/2.4.0`
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
        # TODO: V1 and V2 work differently, if searching for strings in documents, also need to test
        # with http codes.
        case None:
            redirects: Mapping[str, object] = {}
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
            # TODO: What happens to the searching document bodies here?
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
        path,
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


def _build_url(scheme: str, host: str, port: int | None, path: str) -> str:
    port_suffix = f":{port}" if port is not None else ""
    return f"{scheme}://{host}{port_suffix}{path}"


def migrate(rule_value: Mapping[str, object]) -> Mapping[str, object]:
    value = MigratableValue.model_validate(rule_value)
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
        path, connection, remaining_settings = (
            "",
            *_migrate_cert_params(value.mode[1], address_family),
        )
    else:
        path, connection, remaining_settings = _migrate_url_params(value.mode[1], address_family)
    scheme = "https" if value.uses_https() else "http"

    address = value.host.address[1]
    if isinstance(address, str):
        url = _build_url(scheme, address, value.host.port, path)
    else:
        proxy = _build_url(scheme, address.address, address.port or value.host.port, path)
        connection["proxy"] = proxy

    return {
        "endpoints": [
            {
                "service_name": _migrate_name(name=value.name),
                # Risk: We can't be sure the active checks and the config cache use the same IP look
                # up (but both of them are based on the same user data. Moreover,
                # `primary_ip_config.address` (see `get_ssc_host_config` is slightly differently
                # implemented than `HOSTADDRESS` (see `attrs["address"]` in
                # `cmk/base/config.py:3454`).
                "url": url,
                "individual_settings": {
                    "connection": connection,
                    **remaining_settings,
                },
            },
        ],
    }
