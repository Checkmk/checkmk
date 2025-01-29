#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import re
import socket
from collections.abc import Iterable

from cmk.rulesets.v1 import Help, Message, Title
from cmk.rulesets.v1.form_specs import String
from cmk.rulesets.v1.form_specs.validators import ValidationError


class HostAddressValidator:
    def __init__(
        self,
        allow_host_name: bool = True,
        allow_ipv4_address: bool = True,
        allow_ipv6_address: bool = True,
        allow_empty: bool = True,
    ):
        self._allow_host_name = allow_host_name
        self._allow_ipv4_address = allow_ipv4_address
        self._allow_ipv6_address = allow_ipv6_address
        self._allow_empty = allow_empty

    def __call__(self, value: str) -> None:
        if value and self._allow_host_name and self._is_valid_host_name(value):
            return

        if value and self._allow_ipv4_address and self._is_valid_ipv4_address(value):
            return

        if value and self._allow_ipv6_address and self._is_valid_ipv6_address(value):
            return

        if value == "" and self._allow_empty:
            return

        # No support for...
        # ", ".join(self._allowed_type_names()),
        list_of_messages: list[Message] = list(self._allowed_type_names())
        full_message = Message("")
        for idx, message in enumerate(list_of_messages):
            full_message += (
                message + Message(", ") if idx < len(list_of_messages) - 1 else Message("")
            )

        raise ValidationError(full_message)

    def _is_valid_host_name(self, hostname: str) -> bool:
        # http://stackoverflow.com/questions/2532053/validate-a-hostname-string/2532344#2532344
        if len(hostname) > 255:
            return False

        if hostname[-1] == ".":
            hostname = hostname[:-1]  # strip exactly one dot from the right, if present

        # must be not all-numeric, so that it can't be confused with an IPv4 address.
        # Host names may start with numbers (RFC 1123 section 2.1) but never the final part,
        # since TLDs are alphabetic.
        if re.match(r"[\d.]+$", hostname):
            return False

        allowed = re.compile(r"(?!-)[A-Z_\d-]{1,63}(?<!-)$", re.IGNORECASE)
        return all(allowed.match(x) for x in hostname.split("."))

    def _is_valid_ipv4_address(self, address: str) -> bool:
        # http://stackoverflow.com/questions/319279/how-to-validate-ip-address-in-python/4017219#4017219
        try:
            socket.inet_pton(socket.AF_INET, address)
        except AttributeError:  # no inet_pton here, sorry
            try:
                socket.inet_aton(address)
            except OSError:
                return False

            return address.count(".") == 3

        except OSError:  # not a valid address
            return False

        return True

    def _is_valid_ipv6_address(self, address: str) -> bool:
        # http://stackoverflow.com/questions/319279/how-to-validate-ip-address-in-python/4017219#4017219
        try:
            address = address.split("%")[0]
            socket.inet_pton(socket.AF_INET6, address)
        except OSError:  # not a valid address
            return False
        return True

    def _allowed_type_names(self) -> Iterable[Message]:
        allowed: list[Message] = []
        if self._allow_host_name:
            allowed.append(Message("Host- or DNS name"))

        if self._allow_ipv4_address:
            allowed.append(Message("IPv4 address"))

        if self._allow_ipv6_address:
            allowed.append(Message("IPv6 address"))

        return allowed


def create_host_address(
    title: Title | None = None,
    help_text: Help | None = None,
    allow_host_name: bool = True,
    allow_ipv4_address: bool = True,
    allow_ipv6_address: bool = True,
    allow_empty: bool = True,
) -> String:
    validator = HostAddressValidator(
        allow_host_name=allow_host_name,
        allow_ipv4_address=allow_ipv4_address,
        allow_ipv6_address=allow_ipv6_address,
        allow_empty=allow_empty,
    )

    return String(title=title, help_text=help_text, custom_validate=[validator])
