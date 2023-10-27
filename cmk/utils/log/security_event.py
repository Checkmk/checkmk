#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import json
import logging
from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum

import cmk.utils.paths
from cmk.utils.jsontype import JsonSerializable
from cmk.utils.log import init_dedicated_logging


@dataclass
class SecurityEvent:
    """A security event that can be logged"""

    Domain = Enum("Domain", ["auth"])

    summary: str
    details: Mapping[str, JsonSerializable]
    domain: Domain


def log_security_event(event: SecurityEvent) -> None:
    """Log a security event"""

    # initialize if not already initialized
    if not _root_logger().handlers:
        init_dedicated_logging(
            logging.INFO,
            target_logger=_root_logger(),
            log_file=cmk.utils.paths.security_log_file,
            formatter=logging.Formatter("%(asctime)s [%(name)s %(process)d] %(message)s"),
        )

    _root_logger().getChild(event.domain.name).info(
        json.dumps(
            {
                "summary": event.summary,
                "details": event.details,
            }
        )
    )


def _root_logger() -> logging.Logger:
    return logging.getLogger("cmk_security")
