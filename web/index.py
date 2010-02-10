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
import htmllib, transfer, livestatus, os
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

def read_site_config(html):
    user = html.req.user
    path = check_mk.multisite_config_dir + "/" + user + "/siteconfig.mk"
    html.user_siteconf = {}
    if os.path.exists(path):
	html.user_siteconf = eval(file(path).read())

def connect_to_livestatus(html):
    html.site_status = {}
    # If there is only one site (non-multisite), than
    # user cannot enable/disable. 
    if check_mk.is_multisite():
	# do not contact those sites the user has disabled
	enabled_sites = {}
	for sitename, site in check_mk.sites().items():
	    siteconf = html.user_siteconf.get(sitename, {})
	    if not siteconf.get("disabled", False):
		enabled_sites[sitename] = site
	# Now connect to enabled sites with keepalive-connection
	html.live = livestatus.MultiSiteConnection(enabled_sites)

	# Fetch status of sites by querying the version of Nagios and livestatus
	html.live.set_prepend_site(True)
        for sitename, v1, v2 in html.live.query("GET status\nColumns: livestatus_version program_version"):
	    html.site_status[sitename] = { "livestatus_version": v1, "program_version" : v2 }
	html.live.set_prepend_site(False)

	# Get exceptions in case of dead sites
	for sitename, deadinfo in html.live.dead_sites().items():
	    status = html.site_status.get(sitename, {})
	    status["exception"] = deadinfo["exception"]
	    html.site_status[sitename] = status
    else:
	html.live = livestatus.SingleSiteConnection("unix:" + check_mk.livestatus_unix_socket)


def handler(req):
    req.content_type = "text/html"
    req.header_sent = False

    # All URIs end in .py. We strip away the .py and get the
    # name of the page.
    req.myfile = req.uri.split("/")[-1][:-3]

    # Create object that contains all data about the request and
    # helper functions for creating valid HTML. Parse URI and
    # store results in the request object for later usage.
    html = htmllib.html(req)
    req.uriinfo = htmllib.uriinfo(req)

    try:
        read_get_vars(req)
        read_checkmk_defaults(req)

        # These pages may only be used with HTTP authentication turned on.
	if not req.user or type(req.user) != str:
	    raise MKConfigError("You are not logged in. This should never happen. Please "
		    "review your Apache configuration.")

	# in main.mk you can configure "multiadmin_users": a whitelist of users.
        if not check_mk.is_allowed_to_view(req.user):
	    reason = "Not Authorized.  You are logged in as <b>%s</b>. " % req.user
            reason += "If you think this is an error, " \
                       "please ask your administrator to add your login into the list " \
                       " <tt>main.mk:multiadmin_users</tt>"
            raise MKConfigError(reason)

	# Read in users's configuration of sites. This is needed only
	# for multisite installations. The user may switch off certain
	# sites he is not interested in.
	read_site_config(html)

        # General access allowed. Now connect to livestatus
	connect_to_livestatus(html)

	# If multiadmin is retricted to data user is a nagios contact for,
	# we need to set an AuthUser: header for livestatus
	if check_mk.multiadmin_restrict and \
	    req.user not in check_mk.multiadmin_unrestricted_users:
		html.live.set_auth_user('read', req.user)

	# User wants to do action?
	if check_mk.multiadmin_restrict_actions or check_mk.multiadmin_restrict:
	    if req.user not in check_mk.multiadmin_unrestricted_action_users:
		html.live.set_auth_user('action', req.user)

        # Default auth domain is read. Please set to None to switch off authorization
	html.live.set_auth_domain('read')

	# Now branch to a function creating HTML code
	import page_multiadmin
	import page_logwatch
	import views
	import sidebar

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
            html.live = None
	    raise
        html.header("Internal Error")
        html.show_error("Internal error: %s" % e)
        html.footer()
        apache.log_error("Internal error: %s" % (e,), apache.APLOG_ERR)

    # Disconnect from livestatus!
    html.live = None
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



