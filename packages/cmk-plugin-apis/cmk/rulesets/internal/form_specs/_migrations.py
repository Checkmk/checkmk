#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Literal, NamedTuple, NotRequired, TypedDict
from urllib.parse import unquote, urlsplit
from uuid import uuid4


class ProxyAuthSpec(TypedDict):
    user: str
    password: tuple[
        Literal["cmk_postprocessed"],
        Literal["explicit_password", "stored_password"],
        tuple[str, str],
    ]


class ProxyConfigSpec(TypedDict):
    scheme: str
    proxy_server_name: str
    port: int
    auth: NotRequired[ProxyAuthSpec]


_DEFAULT_PORTS = {
    "http": 80,
    "https": 443,
    "socks4": 1080,
    "socks4a": 1080,
    "socks5": 1080,
    "socks5h": 1080,
}


class ParsedProxyUrl(NamedTuple):
    proxy: ProxyConfigSpec
    credentials: tuple[str, str] | None


class LenientProxyUrl(NamedTuple):
    parsed: ParsedProxyUrl
    is_complete: bool


def parse_proxy_url_leniently(url: str) -> LenientProxyUrl:
    """Parse a proxy URL into its structured form and credentials, best effort

    A URL without scheme is treated as an HTTP proxy, a URL without port uses the default
    port of its scheme. Credentials are percent-decoded, since the structured form stores
    them as typed and the URL built from it encodes them again, so it means the same as the
    original URL. Proxy clients only use scheme, host and port, so a path, query or fragment
    is dropped. ``is_complete`` is False when the URL cannot be represented in the structured
    form (unknown scheme, missing or invalid host or port, or a password without a user); the
    proxy then carries port 0, which the form rejects, so the user completes it when editing.
    """
    parts = urlsplit(url.strip() if "://" in url else f"http://{url.strip()}")
    host = parts.hostname or ""
    try:
        port = parts.port
    except ValueError:
        port = 0
    default_port = _DEFAULT_PORTS.get(parts.scheme)
    has_credentials = parts.username is not None or parts.password is not None
    is_complete = (
        default_port is not None
        and bool(host)
        and port != 0
        and (not has_credentials or bool(parts.username))
    )
    return LenientProxyUrl(
        parsed=ParsedProxyUrl(
            proxy=ProxyConfigSpec(
                scheme=parts.scheme,
                proxy_server_name=f"[{host}]" if ":" in host else host,
                port=(port or default_port or 0) if is_complete else 0,
            ),
            credentials=(
                (unquote(parts.username or ""), unquote(parts.password or ""))
                if has_credentials
                else None
            ),
        ),
        is_complete=is_complete,
    )


def parse_proxy_url(url: str) -> ParsedProxyUrl | None:
    """Split a proxy URL into the structured proxy configuration and its credentials

    Returns None if the URL cannot be represented in the structured form. See
    ``parse_proxy_url_leniently`` for how the URL is parsed.

    >>> parse_proxy_url("http://user:p%40ss@proxy.lan:3128")
    ParsedProxyUrl(proxy={'scheme': 'http', 'proxy_server_name': 'proxy.lan', 'port': 3128}, credentials=('user', 'p@ss'))
    >>> parse_proxy_url("proxy.lan").proxy
    {'scheme': 'http', 'proxy_server_name': 'proxy.lan', 'port': 80}
    """
    result = parse_proxy_url_leniently(url)
    return result.parsed if result.is_complete else None


def _explicit_password_auth(user: str, password: str) -> ProxyAuthSpec:
    return ProxyAuthSpec(
        user=user,
        password=("cmk_postprocessed", "explicit_password", (f"uuid{uuid4()}", password)),
    )


def _convert_url_to_explicit_proxy(url: str) -> ProxyConfigSpec:
    # A URL that cannot be fully represented keeps what it can, with port 0, so the user
    # completes the form when editing it. The credentials, if any, are always kept.
    proxy_dict, credentials = parse_proxy_url_leniently(url).parsed
    if credentials is not None:
        proxy_dict["auth"] = _explicit_password_auth(*credentials)
    return proxy_dict


def migrate_to_internal_proxy(
    model: object,
) -> (
    tuple[
        Literal["cmk_postprocessed"],
        Literal["environment_proxy", "no_proxy", "stored_proxy"],
        str,
    ]
    | tuple[
        Literal["cmk_postprocessed"],
        Literal["explicit_proxy"],
        ProxyConfigSpec,
    ]
):
    """
    Transform a previous proxy configuration to a model of the `InternalProxy` FormSpec.
    Previous configurations are transformed in the following way:

        ("global", <stored-proxy-id>) -> ("cmk_postprocessed", "stored_proxy", <stored-proxy-id>)
        ("environment", "environment") -> ("cmk_postprocessed", "environment_proxy", "")
        ("url", <str>) -> ("cmk_postprocessed", "explicit_proxy", <ProxyConfigSpec>)
        ("cmk_postprocessed", "explicit_proxy", <str>) -> ("cmk_postprocessed", "explicit_proxy", <ProxyConfigSpec>)
        ("no_proxy", None) -> ("cmk_postprocessed", "no_proxy", "")

    Args:
        model: Old value presented to the consumers to be migrated
    """

    match model:
        case "global", str(stored_proxy_id):
            return "cmk_postprocessed", "stored_proxy", stored_proxy_id
        case "cmk_postprocessed", "stored_proxy", str(stored_proxy_id):
            return "cmk_postprocessed", "stored_proxy", stored_proxy_id

        case "environment", "environment":
            return "cmk_postprocessed", "environment_proxy", ""
        case "cmk_postprocessed", "environment_proxy", str():
            return "cmk_postprocessed", "environment_proxy", ""

        case "no_proxy", None:
            return "cmk_postprocessed", "no_proxy", ""
        case "cmk_postprocessed", "no_proxy", str():
            return "cmk_postprocessed", "no_proxy", ""

        case ("url", str(url)) | ("cmk_postprocessed", "explicit_proxy", str(url)):
            return (
                "cmk_postprocessed",
                "explicit_proxy",
                _convert_url_to_explicit_proxy(url),
            )
        case "cmk_postprocessed", "explicit_proxy", {
            "scheme": str(scheme),
            "proxy_server_name": str(proxy_server_name),
            "port": int(port),
            "auth": {
                "user": str(user),
                "password": (
                    "cmk_postprocessed",
                    "explicit_password" | "stored_password" as pw_type,
                    (str(part1), str(part2)),
                ),
            },
        }:
            return (
                "cmk_postprocessed",
                "explicit_proxy",
                ProxyConfigSpec(
                    scheme=scheme,
                    proxy_server_name=proxy_server_name,
                    port=port,
                    auth=ProxyAuthSpec(
                        user=user, password=("cmk_postprocessed", pw_type, (part1, part2))
                    ),
                ),
            )
        case "cmk_postprocessed", "explicit_proxy", {
            "scheme": str(scheme),
            "proxy_server_name": str(proxy_server_name),
            "port": int(port),
        }:
            return (
                "cmk_postprocessed",
                "explicit_proxy",
                ProxyConfigSpec(
                    scheme=scheme,
                    proxy_server_name=proxy_server_name,
                    port=port,
                ),
            )

        case _:
            # The value is not part of the message, since it may contain credentials
            raise TypeError(
                f"Could not migrate a value of type {type(model).__name__} to Internal Proxy."
            )
