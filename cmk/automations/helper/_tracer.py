#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
from pathlib import Path
from typing import Final

from cmk import trace
from cmk.ccc.site import get_omd_config, omd_site
from cmk.trace.export import exporter_from_config, init_span_processor

TRACER_SERVICE_NAME: Final = "automation_helper"

TRACER = trace.get_tracer()


def configure_tracer(omd_root: Path) -> None:
    omd_config = get_omd_config(omd_root)
    namespace = trace.service_namespace_from_config("", omd_config)
    instance_id = omd_site()
    config = trace.trace_send_config(omd_config)

    init_span_processor(
        trace.init_tracing(
            service_namespace=namespace,
            service_name=TRACER_SERVICE_NAME,
            service_instance_id=instance_id,
        ),
        exporter_from_config(
            exporter_log_level=logging.ERROR,
            config=config,
        ),
    )
