#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import override

from uvicorn.protocols.http.h11_impl import H11Protocol

from cmk.maps.backend.core.sse import manager


class StreamClosingProtocol(H11Protocol):
    """Ends the open map streams as soon as the server starts to shut down.

    The server asks every open connection to shut down and then waits for them,
    but a stream only ends with its client.
    """

    @override
    def shutdown(self) -> None:
        manager.close_all()
        super().shutdown()
