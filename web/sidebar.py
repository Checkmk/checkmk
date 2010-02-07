#!/usr/bin/python

import check_mk, livestatus, htmllib
from lib import *

def page_views(html):
    html.html_head("Check_MK Live Views")
    html.write("<body class=side>Dies ist der Inhalt</body>")
    html.html_foot()

