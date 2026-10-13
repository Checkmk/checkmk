#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

from cmk.ccc.hostaddress import HostName
from cmk.utils.misc import pnp_cleanup
from cmk.utils.servicename import ServiceName


class Paths:
    def __init__(self, omd_root: Path) -> None:
        self.predictions_dir = omd_root / "var/check_mk/prediction"

    def service_dir(self, host_name: HostName, service_name: ServiceName) -> Path:
        return self.predictions_dir / host_name / pnp_cleanup(service_name)
