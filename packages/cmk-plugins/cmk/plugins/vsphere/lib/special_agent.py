#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from enum import StrEnum
from typing import Literal


class QueryType(StrEnum):
    #: Queried host is a vCenter
    VCENTER = "vcenter"
    #: Queried host is a ESXi host (vCenter integrated)
    HOST_SYSTEM = "host_system"
    #: Queried host is a ESXi host (Standalone / not vCenter integrated)
    STANDALONE = "standalone"


InfoSelection = Literal["hostsystem", "virtualmachine", "datastore", "counters", "licenses"]
