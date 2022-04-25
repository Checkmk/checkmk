#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import signal
from types import FrameType
from typing import Optional

from cmk.gui.ctx_stack import request_local_attr
from cmk.gui.exceptions import RequestTimeout
from cmk.gui.i18n import _


class TimeoutManager:
    """Request timeout handling

    The system apache process will end the communication with the client after
    the timeout configured for the proxy connection from system apache to site
    apache. This is done in /omd/sites/[site]/etc/apache/proxy-port.conf file
    in the "timeout=x" parameter of the ProxyPass statement.

    The regular request timeout configured here should always be lower to make
    it possible to abort the page processing and send a helpful answer to the
    client.

    It is possible to disable the applications request timeout (temoporarily)
    or totally for specific calls, but the timeout to the client will always
    be applied by the system webserver. So the client will always get a error
    page while the site apache continues processing the request (until the
    first try to write anything to the client) which will result in an
    exception.
    """

    def enable_timeout(self, duration: int) -> None:
        def handle_request_timeout(signum: int, frame: Optional[FrameType]) -> None:
            raise RequestTimeout(
                _(
                    "Your request timed out after %d seconds. This issue may be "
                    "related to a local configuration problem or a request which works "
                    "with a too large number of objects. But if you think this "
                    "issue is a bug, please send a crash report."
                )
                % duration
            )

        signal.signal(signal.SIGALRM, handle_request_timeout)
        signal.alarm(duration)

    def disable_timeout(self) -> None:
        signal.alarm(0)


timeout_manager: TimeoutManager = request_local_attr("timeout_manager")
