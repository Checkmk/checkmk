#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Literal

from pydantic import BaseModel


class V1Proxy(BaseModel, extra="forbid"):
    address: str
    port: int | None = None
    # auth: None  # TODO: This is not supported in V2. Turn into conflict?


class V1Host(BaseModel, extra="forbid"):
    address: tuple[Literal["direct"], str] | tuple[Literal["proxy"], V1Proxy]
    address_family: Literal["any", "ipv4_enforced", "ipv6_enforced", "primary_enforced", None] = (
        None
    )
    # If this field is unspecified, it will set depending on the `virtual host`, if check_cert is
    # true, if client_cert is true, client private key or -S is enabled. On redirect new ports might
    # be defined. This behaviour will not transfer to the new check, most likely.
    port: int | None = None
    # TODO: The URL always needs to point to the physical server, with a client optionally providing
    # a different destination in the HostName header, as far as I understand. This is implemented
    # correctly in check_http.c (v1). The v1 ssc behaves very strangely, since it uses HTTP 1.0, if
    # no virtual host is specified (instead of deducing the HostName from the physical server name).
    # In v2, the implementation is also strange, since it demands the virtual host, and makes the
    # physical server optional. This needs to be discussed with PM.
    # What should really happen:
    # url: contains server, that needs to be DNS resolved (given always by address field in v1)
    # host name header: contains the virtual host
    virthost: None = None


class V1Auth(BaseModel, extra="forbid"):
    user: str
    password: object


class V1Regex(BaseModel, extra="forbid"):
    regex: str
    case_insensitive: bool
    crit_if_found: bool
    multiline: bool


class V1PostData(BaseModel, extra="forbid"):
    data: str
    content_type: str


class V1PageSize(BaseModel, extra="forbid"):
    minimum: int
    maximum: int


SimpleLevelsFloat = tuple[Literal["fixed"], tuple[float, float]] | tuple[Literal["no_levels"], None]


class V1Cert(BaseModel, extra="forbid"):
    cert_days: SimpleLevelsFloat


class V1Url(BaseModel, extra="forbid"):
    uri: str | None = None  # TODO: passed via -u in V1, unclear whether this is the same as V2.
    ssl: (
        Literal[
            "auto",  # use with auto-negotiation
            "ssl_1_2",  # enforce TLS 1.2
            "ssl_1_3",  # enforce TLS 1.3
            "ssl_1",  # enforce TLS 1.0
            "ssl_2",  # enforce SSL 2.0
            "ssl_3",  # enforce SSL 3.0
        ]
        | None
    ) = None
    response_time: SimpleLevelsFloat | None = None
    timeout: int | None = None
    user_agent: str | None = None
    add_headers: list[str] | None = None
    auth: V1Auth | None = None
    onredirect: Literal["ok", "warning", "critical", "follow", "sticky", "stickyport"] | None = None
    expect_response_header: str | None = None
    expect_response: list[str] | None = None
    expect_string: str | None = None
    expect_regex: V1Regex | None = None
    post_data: V1PostData | None = None
    method: (
        Literal[
            "GET",
            "POST",
            "PUT",
            "DELETE",
            "HEAD",
            # Not supported by V2
            # "OPTIONS", "TRACE", "CONNECT", "CONNECT_POST", "PROPFIND",
        ]
        | None
    ) = None
    no_body: Literal[True, None] = None
    page_size: V1PageSize | None = None
    max_age: int | None = None
    urlize: Literal[True, None] = None
    extended_perfdata: Literal[True, None] = None


class V1Value(BaseModel, extra="forbid"):
    name: str
    host: V1Host
    mode: tuple[Literal["url"], V1Url] | tuple[Literal["cert"], V1Cert]
    disable_sni: Literal[True, None] = None
