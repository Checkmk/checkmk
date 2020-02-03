#!/usr/bin/env python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2014             mk@mathias-kettner.de |
# +------------------------------------------------------------------+
#
# This file is part of Check_MK.
# The official homepage is at http://mathias-kettner.de/check_mk.
#
# check_mk is free software;  you can redistribute it and/or modify it
# under the  terms of the  GNU General Public License  as published by
# the Free Software Foundation in version 2.  check_mk is  distributed
# in the hope that it will be useful, but WITHOUT ANY WARRANTY;  with-
# out even the implied warranty of  MERCHANTABILITY  or  FITNESS FOR A
# PARTICULAR PURPOSE. See the  GNU General Public License for more de-
# tails. You should have  received  a copy of the  GNU  General Public
# License along with GNU Make; see the file  COPYING.  If  not,  write
# to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
# Boston, MA 02110-1301 USA.

import signal
from cmk.gui.exceptions import RequestTimeout
from cmk.gui.i18n import _


class TimeoutManager(object):
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
    def enable_timeout(self, duration):
        def handle_request_timeout(signum, frame):
            raise RequestTimeout(
                _("Your request timed out after %d seconds. This issue may be "
                  "related to a local configuration problem or a request which works "
                  "with a too large number of objects. But if you think this "
                  "issue is a bug, please send a crash report.") % duration)

        signal.signal(signal.SIGALRM, handle_request_timeout)
        signal.alarm(duration)

    def disable_timeout(self):
        signal.alarm(0)
