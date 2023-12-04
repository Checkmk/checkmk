#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

import dataclasses

from ._filters import RediscoveryParameters


@dataclasses.dataclass(frozen=True)
class DiscoveryCheckParameters:
    commandline_only: bool
    check_interval: int
    severity_new_services: int
    severity_vanished_services: int
    severity_changed_service_labels: int
    severity_changed_service_params: int
    severity_new_host_labels: int
    rediscovery: RediscoveryParameters
