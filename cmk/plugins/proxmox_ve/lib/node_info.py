#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Sequence
from enum import StrEnum

from pydantic import BaseModel


class NodeStatus(StrEnum):
    ONLINE = "online"
    OFFLINE = "offline"
    UNKNOWN = "unknown"


class SubscriptionStatus(StrEnum):
    NEW = "new"
    NOTFOUND = "notfound"
    ACTIVE = "active"
    INVALID = "invalid"
    EXPIRED = "expired"
    SUSPENDED = "suspended"


class SubscriptionInfo(BaseModel, frozen=True):
    status: SubscriptionStatus
    next_due_date: str | None = None


class SectionNodeInfo(BaseModel, frozen=True):
    status: NodeStatus
    lxc: Sequence[str]
    qemu: Sequence[str]
    version: str
    subscription: SubscriptionInfo
