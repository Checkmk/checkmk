#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import dataclasses

from cmk.agent_receiver.lib.config import get_config
from cmk.agent_receiver.relay.lib.shared_types import Version
from cmk.ccc.version import omd_version


@dataclasses.dataclass
class GetVersionHandler:
    def process(self) -> Version:
        # Remove the last part of the version (edition)
        version = ".".join(omd_version(get_config().omd_root).split(".")[:-1])
        return Version(version)
