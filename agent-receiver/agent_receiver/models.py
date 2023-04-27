#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import re
import socket
from enum import Enum
from typing import Mapping, NamedTuple, Optional
from uuid import UUID

from fastapi import HTTPException
from pydantic import BaseModel, validator


class PairingBody(BaseModel):
    csr: str


class PairingResponse(BaseModel):
    root_cert: str
    client_cert: str


def _is_valid_host_name(hostname: str) -> bool:
    # duplicated from cmk.gui.valuespec
    # http://stackoverflow.com/questions/2532053/validate-a-hostname-string/2532344#2532344
    if not hostname or len(hostname) > 255:
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


def _is_valid_ipv4_address(address: str) -> bool:
    # duplicated from cmk.gui.valuespec
    # http://stackoverflow.com/questions/319279/how-to-validate-ip-address-in-python/4017219#4017219
    try:
        socket.inet_pton(socket.AF_INET, address)
    except AttributeError:  # no inet_pton here, sorry
        try:
            socket.inet_aton(address)
        except socket.error:
            return False

        return address.count(".") == 3

    except socket.error:  # not a valid address
        return False

    return True


def _is_valid_ipv6_address(address: str) -> bool:
    # duplicated from cmk.gui.valuespec
    # http://stackoverflow.com/questions/319279/how-to-validate-ip-address-in-python/4017219#4017219
    try:
        address = address.split("%")[0]
        socket.inet_pton(socket.AF_INET6, address)
    except socket.error:  # not a valid address
        return False
    return True


def _is_valid_hostname_or_ip(uri: str) -> bool:
    """Check if the given URI is a valid hostname or IP address

    Some examples (see unit tests for more):
    >>> _is_valid_hostname_or_ip("test.checkmk.com")
    True
    >>> _is_valid_hostname_or_ip("127.0.0.1")
    True
    >>> _is_valid_hostname_or_ip("2606:2800:220:1:248:1893:25c8:1946")
    True
    >>> _is_valid_hostname_or_ip("::1")
    True
    >>> _is_valid_hostname_or_ip("my/../host")
    False
    """
    return _is_valid_host_name(uri) or _is_valid_ipv4_address(uri) or _is_valid_ipv6_address(uri)


class RegistrationWithHNBody(BaseModel):
    uuid: UUID
    host_name: str

    @validator("host_name")
    @classmethod
    def valid_hostname(cls, v):
        if not _is_valid_hostname_or_ip(v):
            raise HTTPException(
                status_code=400,
                detail=f"Invalid hostname: '{v}'",
            )
        return v


class RegistrationWithLabelsBody(BaseModel):
    uuid: UUID
    agent_labels: Mapping[str, str]


class RegistrationStatusEnum(Enum):
    NEW = "new"
    PENDING = "pending"
    DECLINED = "declined"
    READY = "ready"
    DISCOVERABLE = "discoverable"


class RegistrationData(NamedTuple):
    status: RegistrationStatusEnum
    message: Optional[str]


class HostTypeEnum(Enum):
    PULL = "pull-agent"
    PUSH = "push-agent"


class RegistrationStatus(BaseModel):
    hostname: Optional[str] = None
    status: Optional[RegistrationStatusEnum] = None
    type: Optional[HostTypeEnum] = None
    message: Optional[str] = None
