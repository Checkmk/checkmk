#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import asyncio
import base64
from typing import NewType

from cmk.agent_receiver.lib.config import get_config

B64SiteInternalSecret = NewType("B64SiteInternalSecret", str)


def internal_credentials() -> B64SiteInternalSecret:
    config = get_config()
    return B64SiteInternalSecret(
        base64.b64encode(config.internal_secret_path.read_bytes()).decode("ascii")
    )


async def async_internal_credentials() -> B64SiteInternalSecret:
    # Use asyncio thread pool to avoid blocking the event loop, similar to aiofiles
    loop = asyncio.get_running_loop()
    content = await loop.run_in_executor(None, internal_credentials)
    return content
