#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import re
from typing import Annotated

from pydantic import Base64Bytes, BaseModel, StringConstraints

REGEX_HOST_NAME = re.compile(r"^\w[-0-9a-zA-Z_.]*$", re.ASCII)
Host = Annotated[str, StringConstraints(pattern=REGEX_HOST_NAME)]


class MonitoringData(BaseModel):
    # TODO: Host may be not needed here as it's part of the endpoint path
    host: Host
    payload: Base64Bytes
    version: int = 1
