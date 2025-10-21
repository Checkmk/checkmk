#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Literal, NotRequired, TypedDict
from urllib.parse import urlparse
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


def _convert_url_to_explicit_proxy(url: str) -> ProxyConfigSpec:
    parts = urlparse(url)
    proxy_dict = ProxyConfigSpec(
        scheme=parts.scheme,
        proxy_server_name=parts.hostname or "",
        port=parts.port or 0,
    )
    if parts.username and parts.password:
        proxy_dict["auth"] = ProxyAuthSpec(
            user=parts.username,
            password=(
                "cmk_postprocessed",
                "explicit_password",
                (f"uuid{uuid4()}", parts.password),
            ),
        )

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

        case "cmk_postprocessed", "explicit_proxy", str(url):
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
            raise TypeError(f"Could not migrate {model!r} to Internal Proxy.\n")
