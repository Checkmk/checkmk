#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import cmk.gui.escaping as escaping
import cmk.gui.pages
import cmk.gui.config as config
import cmk.gui.utils as utils
from cmk.gui.globals import html


@cmk.gui.pages.register("index")
def page_index():
    # type: () -> None
    html.write(
        '<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Frameset//EN" "http://www.w3.org/TR/html4/frameset.dtd">\n'
        '<html><head>\n')
    html.default_html_headers()
    html.write("""<title>%s</title>
</head>
<frameset cols="280,*" frameborder="0" framespacing="0" border="0">
    <frame src="side.py" name="side" noresize scrolling="no">
    <frame src="%s" name="main" noresize>
</frameset>
</html>
""" % (escaping.escape_attribute(
        config.get_page_heading()), escaping.escape_attribute(_get_start_url())))


def _get_start_url():
    # type: () -> str
    default_start_url = config.user.get_attribute("start_url", config.start_url) or config.start_url
    if not utils.is_allowed_url(default_start_url):
        default_start_url = "dashboard.py"

    return html.get_url_input("start_url", default_start_url)
