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

import config
import lib

def page_index():
    if "%s" in config.page_heading:
        heading = config.page_heading % (config.site(config.omd_site()).get('alias', _("Multisite")))
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
""" % (html.attrencode(heading), html.attrencode(_get_start_url())))


def _get_start_url():
    start_url = html.var_utf8("start_url", config.user.get_attribute("start_url") or config.start_url).strip()
    # Prevent redirecting to absolute URL which could be used to redirect
    # users to compromised pages.
    if lib.is_allowed_url(start_url):
        return start_url
    else:
        return "dashboard.py"
