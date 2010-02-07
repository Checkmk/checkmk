#!/usr/bin/python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2009             mk@mathias-kettner.de |
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
# ails.  You should have  received  a copy of the  GNU  General Public
# License along with GNU Make; see the file  COPYING.  If  not,  write
# to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
# Boston, MA 02110-1301 USA.

from mod_python import apache,util
from urllib import urlencode
import htmllib, transfer
from lib import *

def read_checkmk_defaults(req):
    # read in check_mk's defaults file. That contains all
    # installation settings (paths, etc.)

    req.defaults = {}
    try:
        # The "options" are set in the Apache configuration
        # with the directive "PythonOption"
        defaults_path = req.get_options().get(
            "defaults_path", "/usr/share/check_mk/modules/defaults")
        for line in file(defaults_path):
            try:
                var, value = line.split('=', 1)
                req.defaults[var.strip()] = eval(value)
            except:
                pass
        transfer.check_mk_path = req.defaults.get("modules_dir", "/usr/share/check_mk/modules")
        transfer.defaults_path = defaults_path
        global check_mk
        import check_mk

    except Exception, e:
        raise MKConfigError("Cannot import check_mk.py (defaults path <tt>%s</tt>): %s" % (defaults_path, e))

def read_get_vars(req):
    req.vars = {}
    if req.args:
        req.rawvars = util.parse_qs(req.args, True)
        for (key,values) in req.rawvars.items():
            if len(values) >= 1:
                req.vars[key] = values[-1]


def handler(req):
    req.content_type = "text/html"
    req.header_sent = False


    # Die Datei main.py wird mit beliebigen Namen aufgerufen, die
    # alle auf .py enden, und die es garnicht geben muss!
    req.myfile = req.uri.split("/")[-1][:-3]


    # Verzweigen je nach Name der Seite, 'main' ist Default

    html = htmllib.html(req)
    req.uriinfo = htmllib.uriinfo(req)

    try:
        read_get_vars(req)
        read_checkmk_defaults(req)

	import page_multiadmin
	import page_logwatch
	import views
	import sidebar

        if not check_mk.is_allowed_to_view(req.user):
            html.header("Not Authorized")

            if type(req.user) == str:
                login_text = "logged in as <b>%s</b>" % req.user
            else:
                login_text = "not logged in"

            html.write("<h1 class=error>You are not authorized</h1>\n")
	    html.show_error("You are %s and not "
                       "authorized to use check_mk's web pages. If you think this is an error, "
                       "please ask your administrator to add your login into the list "
                       " <tt>main.mk:multiadmin_users</tt>"% login_text)
            html.footer()
        else:

            pagehandlers = { "index"        : page_index,
                             "filter"       : page_multiadmin.page,
			     "siteoverview" : page_multiadmin.page_siteoverview,
			     "edit_views"   : views.page_edit_views,
			     "edit_view"    : views.page_edit_view,
			     "view"         : views.page_view,
                             "logwatch"     : page_logwatch.page,
			     "side_views"   : sidebar.page_views, }

            handler = pagehandlers.get(req.myfile, page_index)
            handler(html)

    except MKUserError, e:
        html.header("Invalid User Input")
        html.show_error(e)
        html.footer()

    except MKConfigError, e:
        html.header("Configuration Error")
        html.show_error(e)
        html.footer()
        apache.log_error("Configuration error: %s" % (e,), apache.APLOG_ERR)

    except Exception, e:
	if check_mk.multiadmin_debug:
	    raise
        html.header("Internal Error")
        html.show_error("Internal error: %s" % e)
        html.footer()
        apache.log_error("Internal error: %s" % (e,), apache.APLOG_ERR)

    views.disconnect_from_livestatus() # HACK.
    return apache.OK
    

def page_index(html):
    html.header("Check_MK Overview")
    html.write('''
<ul>
<li><a href="http://mathias-kettner.de/check_mk.html">Homepage of Check_mk</a></li>
<li><a href="filter.py">Filter and Actions</a></li>
<li><a href="edit_views.py">Experimental: Edit user views</a></li>
<li><a href="logwatch.py">Logwatch</a></li>
</ul>
''')
    html.footer()

