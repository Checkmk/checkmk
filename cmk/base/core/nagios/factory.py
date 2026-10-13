#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import assert_never

from cmk.base.configlib.loaded_config import BaseConfig
from cmk.core_client import CoreClient, NagiosClient
from cmk.monitoring_config.internal import MonitoringConfigBuilder
from cmk.utils import paths


def create_core(loaded_config: BaseConfig) -> tuple[MonitoringConfigBuilder, CoreClient]:
    match loaded_config.monitoring_core:
        case "nagios":
            from cmk.base.core.nagios import make_nagios_config_builder

            return (
                make_nagios_config_builder(),
                NagiosClient(
                    objects_file=paths.nagios_objects_file,
                    init_script=paths.nagios_startscript,
                    config_file=paths.nagios_config_file,
                    binary_file=paths.nagios_binary,
                    cleanup_base=paths.omd_root,
                ),
            )
        case "cmc":
            raise RuntimeError("The Microcore is not available in this edition")
        case other_core:
            assert_never(other_core)
