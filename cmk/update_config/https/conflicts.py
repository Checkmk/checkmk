#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import enum
import re
from collections.abc import Mapping, Sequence
from contextlib import suppress
from dataclasses import dataclass
from typing import Literal

from pydantic import HttpUrl, ValidationError

from cmk.update_config.https.conflict_options import (
    AdditionalHeaders,
    CantConstructURL,
    CantDisableSNIWithHTTPS,
    CantHaveRegexAndString,
    CantPostData,
    Config,
    ConflictType,
    ExpectResponseHeader,
    HTTP10NotSupported,
    MethodUnavailable,
    OnlyStatusCodesAllowed,
    SSLIncompatible,
    V1ChecksRedirectResponse,
)
from cmk.update_config.https.v1_scheme import V1Cert, V1Host, V1Url, V1Value


def _migrate_header(header: str) -> dict[str, str] | None:
    match header.split(":", 1):
        case [name, value]:
            return {"header_name": name, "header_value": value.strip()}
    return None


MACROS = {
    "$HOSTNAME$",
    "$HOSTADDRESS$",
    "$HOSTALIAS$",
    "$HOST_TAGS$",
    "$_HOSTTAGS$",
    "$HOST__TAG_site$",
    "$_HOST_TAG_site$",
    "$HOST__TAG_address_family$",
    "$_HOST_TAG_address_family$",
    "$HOST__TAG_ip-v4$",
    "$_HOST_TAG_ip-v4$",
    "$HOST__TAG_agent$",
    "$_HOST_TAG_agent$",
    "$HOST__TAG_tcp$",
    "$_HOST_TAG_tcp$",
    "$HOST__TAG_checkmk-agent$",
    "$_HOST_TAG_checkmk-agent$",
    "$HOST__TAG_piggyback$",
    "$_HOST_TAG_piggyback$",
    "$HOST__TAG_snmp_ds$",
    "$_HOST_TAG_snmp_ds$",
    "$HOST__TAG_criticality$",
    "$_HOST_TAG_criticality$",
    "$HOST__TAG_networking$",
    "$_HOST_TAG_networking$",
    "$HOST__LABEL_cmk/site$",
    "$_HOST_LABEL_cmk/site$",
    "$HOST__LABELSOURCE_cmk/site$",
    "$_HOST_LABELSOURCE_cmk/site$",
    "$HOST_ADDRESS_4$",
    "$_HOSTADDRESS_4$",
    "$HOST_ADDRESS_6$",
    "$_HOSTADDRESS_6$",
    "$HOST_ADDRESS_FAMILY$",
    "$_HOSTADDRESS_FAMILY$",
    "$HOST_ADDRESSES_4$",
    "$_HOSTADDRESSES_4$",
    "$HOST_ADDRESSES_6$",
    "$_HOSTADDRESSES_6$",
    "$HOST_FILENAME$",
    "$_HOSTFILENAME$",
    "$USER1$",
    "$USER2$",
    "$USER3$",
    "$USER4$",
}


class MigratableUrl(V1Url):
    def migrate_expect_response(self) -> None | list[int]:
        if self.expect_response is None:
            return None
        return _migrate_expect_response(self.expect_response)

    def migrate_add_headers(self) -> None | list[dict[str, str]]:
        if self.add_headers is None:
            return None

        return [
            migrated
            for header in self.add_headers
            if (migrated := _migrate_header(header)) is not None
        ]

    def migrate_expect_response_header(self) -> None | dict[str, str]:
        if self.expect_response_header is None:
            return None
        if "\r\n" in self.expect_response_header.strip("\r\n"):
            return None
        return _migrate_header(self.expect_response_header.strip("\r\n"))

    def migrate_expect_regex(self) -> None | tuple[str, object]:
        if self.expect_regex is None:
            return None
        return (
            "regex",
            {
                "regex": self.expect_regex.regex,
                "case_insensitive": self.expect_regex.case_insensitive,
                "multiline": self.expect_regex.multiline,
                "invert": self.expect_regex.crit_if_found,
            },
        )

    def migrate_expect_string(self) -> None | tuple[str, object]:
        return None if self.expect_string is None else ("string", self.expect_string)

    def migrate_to_send_data(self) -> None | dict[str, dict[str, object]]:
        if self.post_data is None:
            return None
        return {
            "send_data": {
                "content": self.post_data.data,
                "content_type": ("custom", self.post_data.content_type),
            }
        }


def _migrate_expect_response(response: list[str]) -> list[int]:
    result = []
    for item in response:
        if (status := re.search(r"\d{3}", item)) is not None:
            result.append(int(status.group()))
    return result


class MigratableCert(V1Cert):
    pass


class MigrateableHost(V1Host):
    address: tuple[Literal["direct"], str] | None = None


def _build_url(scheme: str, host: str, port: int | None, path: str) -> str:
    port_suffix = f":{port}" if port is not None else ""
    return f"{scheme}://{host}{port_suffix}{path}"


class MigratableValue(V1Value):
    host: MigrateableHost
    mode: tuple[Literal["url"], MigratableUrl] | tuple[Literal["cert"], MigratableCert]

    def url(self) -> str:
        scheme = "https" if self.uses_https() else "http"
        path = self.mode[1].uri or "" if isinstance(self.mode[1], MigratableUrl) else ""
        if isinstance(self.host.address, tuple):
            hostname = self.host.virthost or self.host.address[1]
        else:
            hostname = self.host.virthost or "$HOSTADDRESS$"
        return _build_url(scheme, hostname, self.host.port, path)


@dataclass(frozen=True)
class ForMigration:
    value: MigratableValue
    config: Config


@dataclass(frozen=True)
class Conflict:
    type_: ConflictType
    mode_fields: Sequence[str] = ()
    host_fields: Sequence[str] = ()
    disable_sni: bool = False
    cant_load: bool = False

    def render(self) -> str:
        name = self.type_.value
        if self.type_ in (ConflictType.cant_migrate_proxy, ConflictType.cant_have_regex_and_string):
            return f"{name}, no automatic migration possible."
        return name


class UrlType(enum.Enum):
    VALID = "valid"
    INVALID = "invalid"


def _classify(url: str) -> UrlType:
    with suppress(ValidationError):
        HttpUrl(url=url)
        return UrlType.VALID
    return UrlType.INVALID


def detect_conflicts(config: Config, rule_value: Mapping[str, object]) -> Conflict | ForMigration:
    try:
        value = V1Value.model_validate(rule_value)
    except ValidationError:
        return Conflict(
            type_=ConflictType.invalid_value,
            cant_load=True,
        )
    if isinstance(value.host.address, tuple) and value.host.address[0] == "proxy":
        return Conflict(
            type_=ConflictType.cant_migrate_proxy,
            host_fields=["address"],
        )
    if (
        config.http_1_0_not_supported is HTTP10NotSupported.skip
        and not value.uses_https()
        and value.host.virthost is None
    ):
        return Conflict(
            type_=ConflictType.http_1_0_not_supported,
            host_fields=["virthost"],
        )
    mode = value.mode[1]
    if isinstance(mode, V1Url):
        if config.add_headers_incompatible is AdditionalHeaders.skip and any(
            ":" not in header for header in mode.add_headers or []
        ):
            return Conflict(
                type_=ConflictType.add_headers_incompatible,
                mode_fields=["add_headers"],
            )
        if config.ssl_incompatible is SSLIncompatible.skip and mode.ssl in [
            "ssl_1",
            "ssl_2",
            "ssl_3",
            "ssl_1_1",
        ]:
            return Conflict(
                type_=ConflictType.ssl_incompatible,
                mode_fields=["ssl"],
            )
        if (
            config.expect_response_header is ExpectResponseHeader.skip
            and mode.expect_response_header is not None
        ):
            if "\r\n" in mode.expect_response_header.strip("\r\n"):
                return Conflict(
                    type_=ConflictType.expect_response_header,
                    mode_fields=["expect_response_header"],
                )
            if ":" not in mode.expect_response_header:
                return Conflict(
                    type_=ConflictType.expect_response_header,
                    mode_fields=["expect_response_header"],
                )
        if (
            config.cant_have_regex_and_string is CantHaveRegexAndString.skip
            and mode.expect_regex is not None
            and mode.expect_string is not None
        ):
            return Conflict(
                type_=ConflictType.cant_have_regex_and_string,
                mode_fields=["expect_regex", "expect_string"],
            )
        if config.method_unavailable is MethodUnavailable.skip and mode.method in [
            "OPTIONS",
            "TRACE",
            "CONNECT",
            "CONNECT_POST",
            "PROPFIND",
        ]:
            return Conflict(
                type_=ConflictType.method_unavailable,
                mode_fields=["method"],
            )
        if (
            config.cant_post_data is CantPostData.skip
            and mode.post_data is not None
            and mode.method in ("GET", "DELETE", "HEAD")
        ):
            return Conflict(
                type_=ConflictType.cant_post_data,
                mode_fields=["method", "post_data"],
            )
        migrated_expect_response = _migrate_expect_response(mode.expect_response or [])
        if config.only_status_codes_allowed is OnlyStatusCodesAllowed.skip and (
            len(migrated_expect_response) != len(mode.expect_response or [])
        ):
            return Conflict(
                type_=ConflictType.only_status_codes_allowed,
                mode_fields=["expect_response"],
            )
        if (
            config.cant_disable_sni_with_https is CantDisableSNIWithHTTPS.skip
            and value.uses_https()
            and value.disable_sni
        ):
            return Conflict(
                type_=ConflictType.cant_disable_sni_with_https,
                mode_fields=["ssl"],
                disable_sni=True,
            )
        if (
            config.v1_checks_redirect_response is V1ChecksRedirectResponse.skip
            and migrated_expect_response
            and mode.onredirect in ["follow", "sticky", "stickyport"]
        ):
            return Conflict(
                type_=ConflictType.v1_checks_redirect_response,
                mode_fields=["onredirect", "expect_response"],
            )
    elif (
        config.cant_disable_sni_with_https is CantDisableSNIWithHTTPS.skip
        and value.disable_sni  # Cert mode is always https
    ):
        return Conflict(
            type_=ConflictType.cant_disable_sni_with_https,
            disable_sni=True,
        )

    migratable_value = MigratableValue.model_validate(value.model_dump())
    if config.cant_construct_url is CantConstructURL.skip:
        url = migratable_value.url()
        if _classify(url) is UrlType.INVALID:
            return Conflict(
                type_=ConflictType.cant_construct_url,
                host_fields=["address", "uri", "virthost"],
            )
        if any(macro in url for macro in MACROS):
            return Conflict(
                type_=ConflictType.cant_construct_url,
                host_fields=["address", "uri", "virthost"],
            )
    return ForMigration(value=migratable_value, config=config)
