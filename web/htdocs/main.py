#!/usr/bin/python
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

import defaults, config

import urlparse
import re

def page_index():
    default_start_url = config.user.get("start_url") or config.start_url
    start_url = html.var("start_url", default_start_url).strip()

    # Prevent redirecting to absolute URL which could be used to redirect
    # users to compromised pages.
    # Also prevent using of "javascript:" URLs which could used to inject code
    parsed = urlparse.urlparse(start_url)

    # Don't allow the user to set a URL scheme
    if parsed.scheme != "":
        start_url = default_start_url

    # Don't allow the user to set a network location
    if parsed.netloc != "":
        start_url = default_start_url

    # Don't allow bad characters in path
    if not re.match("[/a-z0-9_\.-]*$", parsed.path):
        start_url = default_start_url

    if "%s" in config.page_heading:
        heading = config.page_heading % (config.site(defaults.omd_site).get('alias', _("Multisite")))
    else:
        heading = config.page_heading

    html.write('<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Frameset//EN" "http://www.w3.org/TR/html4/frameset.dtd">\n'
               '<html><head>\n')
    html.default_html_headers()
    html.write("""<title>%s</title>
</head>
<frameset cols="280,*" frameborder="0" framespacing="0" border="0">
    <frame src="side.py" name="side" noresize scrolling="no">
    <frame src="%s" name="main" noresize>
</frameset>
</html>
""" % (html.attrencode(heading), html.attrencode(start_url)))

# This function does almost nothing. It just makes sure that
# a livestatus-connection is built up, since connect_to_livestatus()
# handles the _site_switch variable.
def ajax_switch_site():
    html.live
