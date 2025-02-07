#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import enum
import re
from collections.abc import Mapping
from contextlib import suppress
from dataclasses import dataclass
from ipaddress import AddressValueError, IPv6Address, NetmaskValueError
from typing import Literal, LiteralString

from pydantic import HttpUrl, ValidationError

from cmk.update_config.http.v1_scheme import V1Cert, V1Url, V1Value


class MigratableUrl(V1Url):
    def migrate_expect_response(self) -> None | list[int]:
        if self.expect_response is None:
            return None
        return _migrate_expect_response(self.expect_response)


def _migrate_expect_response(response: list[str]) -> list[int]:
    result = []
    for item in response:
        if (status := re.search(r"\d{3}", item)) is not None:
            result.append(int(status.group()))
        else:
            raise ValueError(f"Invalid status code: {item}")
    return result


class MigratableCert(V1Cert):
    pass


class MigratableValue(V1Value):
    mode: tuple[Literal["url"], MigratableUrl] | tuple[Literal["cert"], MigratableCert]


@dataclass(frozen=True)
class Conflict:
    type_: LiteralString
    mode_fields: list[str]
    host_fields: list[str]


class HostType(enum.Enum):
    IPV6 = enum.auto()
    EMBEDDABLE = enum.auto()
    INVALID = enum.auto()


def _classify(host: str) -> HostType:
    with suppress(ValidationError):
        HttpUrl(url=f"http://{host}")
        return HostType.EMBEDDABLE
    with suppress(AddressValueError, NetmaskValueError):
        IPv6Address(host)
        return HostType.IPV6
    return HostType.INVALID


def _migratable_url_params(url_params: MigratableUrl) -> bool:
    if (
        url_params.expect_response_header is not None
        and "\r\n" in url_params.expect_response_header.strip("\r\n")
    ):
        # TODO: Redirects behave differently in V1 and V2.
        return False
    if url_params.expect_regex is not None and url_params.expect_string is not None:
        return False
    if url_params.post_data is not None and url_params.method in ("GET", "DELETE", "HEAD"):
        return False
    try:
        _migrate_expect_response(url_params.expect_response or [])
    except ValueError:
        return False
    return True


def detect_conflicts(
    rule_value: Mapping[str, object],
) -> Conflict | MigratableValue | ValidationError:
    try:
        value = V1Value.model_validate(rule_value)
    except ValidationError as e:
        # TODO: some validation errors need to be conflicts. Eventually V1Value needs to allow every
        # value that can be loaded via the ruleset.
        return e
    mode = value.mode[1]
    if isinstance(mode, V1Url):
        if any(":" not in header for header in mode.add_headers or []):
            return Conflict(
                type_="add_headers_incompatible",
                mode_fields=["add_headers"],
                host_fields=[],
            )
    return MigratableValue.model_validate(value.model_dump())


def migratable(rule_value: Mapping[str, object]) -> bool:
    value = detect_conflicts(rule_value)
    if not isinstance(value, MigratableValue):
        return False
    address = value.host.address[1]
    if isinstance(address, str):
        type_ = _classify(address)
        if type_ is not HostType.EMBEDDABLE:
            # This might have some issues, since customers can put a port, uri, and really mess with
            # us in a multitude of ways.
            return False
    else:
        type_ = _classify(address.address)
        if type_ is not HostType.EMBEDDABLE:
            # We have the same issue as above.
            return False
        return False  # TODO: We don't have a address, if proxy is specified because of the HOSTADDRESS-url conflict.
    if value.disable_sni:
        return False
    if isinstance(value.mode[1], V1Cert):
        return True
    return _migratable_url_params(value.mode[1])
