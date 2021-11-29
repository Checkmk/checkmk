#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from enum import Enum
from typing import Mapping, NamedTuple, Optional

from pydantic import BaseModel


class PairingBody(BaseModel):
    csr: str


class RegistrationWithHNBody(BaseModel):
    uuid: str
    host_name: str


class RegistrationWithLabelsBody(BaseModel):
    uuid: str
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
