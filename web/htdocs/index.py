#!/usr/bin/python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2010             mk@mathias-kettner.de |
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
import htmllib, livestatus, os, pprint, config
from lib import *

def load_config(req):
    # read in check_mk's defaults file. That contains all
    # installation settings (paths, etc.)

    # First read installation settings (written during setup.sh)
    defaults = {}
    try:
        # The "options" are set in the Apache configuration
        # with the directive "PythonOption"
        defaults_path = req.get_options().get(
            "defaults_path", "/usr/share/check_mk/modules/defaults")
        for line in file(defaults_path):
            try:
                var, value = line.split('=', 1)
                defaults[var.strip()] = eval(value)
            except:
                pass

    except Exception, e:
        raise MKConfigError("Cannot read %s: %s" % (defaults_path, e))

    # Store installation settings in config module
    config.set_defaults(defaults)
    config.load_config()

def read_get_vars(req):
    req.vars = {}
    if req.args:
        req.rawvars = util.parse_qs(req.args, True)
        for (key,values) in req.rawvars.items():
            if len(values) >= 1:
                req.vars[key] = values[-1]

def connect_to_livestatus(html):
    html.site_status = {}
    # site_status keeps a dictionary for each site with the following
    # keys:
    # "state"              --> "online", "offline", "disabled"
    # "exception"          --> An error exception in case of "offline"
    # "livestatus_version" --> Version of sites livestatus if "online"
    # "program_version"    --> Version of Nagios if "online"

    # If there is only one site (non-multisite), than
    # user cannot enable/disable. 
    if config.is_multisite():
	# do not contact those sites the user has disabled
	# also honor HTML-variables for switching off sites
	# right now. This is generally done by the variable
	# _site_switch=sitename1:on,sitename2:off,...
	enabled_sites = {}
	switch_var = html.var("_site_switch")
	if switch_var:
	    for info in switch_var.split(","):
		sitename, onoff = info.split(":")	
		d = config.user_siteconf.get(sitename, {})
		if onoff == "on":
		    d["disabled"] = False
		else:
		    d["disabled"] = True
		config.user_siteconf[sitename] = d
	    config.save_site_config()

	# Make a list of all non-disables sites
	for sitename, site in config.allsites().items():
	    siteconf = config.user_siteconf.get(sitename, {})
	    if siteconf.get("disabled", False):
		html.site_status[sitename] = { "state" : "disabled", "site" : site } 
	    else:
		html.site_status[sitename] = { "state" : "offline", "site" : site }
		enabled_sites[sitename] = site
		
	# Now connect to enabled sites with keepalive-connection
	html.live = livestatus.MultiSiteConnection(enabled_sites)

	# Fetch status of sites by querying the version of Nagios and livestatus
	html.live.set_prepend_site(True)
        for sitename, v1, v2 in html.live.query("GET status\nColumns: livestatus_version program_version"):
	    html.site_status[sitename].update({ "state" : "online", "livestatus_version": v1, "program_version" : v2 })
	html.live.set_prepend_site(False)

	# Get exceptions in case of dead sites
	for sitename, deadinfo in html.live.dead_sites().items():
	    html.site_status[sitename]["exception"] = deadinfo["exception"]

    else:
	html.live = livestatus.SingleSiteConnection("unix:" + config.defaults["livestatus_unix_socket"])
	html.site_status = { '': { "state" : "offline", "site" : config.site('') } }
        v1, v2 = html.live.query_row("GET status\nColumns: livestatus_version program_version")
	html.site_status[''].update({ "state" : "online", "livestatus_version": v1, "program_version" : v2 })

    # If multiadmin is retricted to data user is a nagios contact for,
    # we need to set an AuthUser: header for livestatus
    if not config.may("see_all"):
	html.live.set_auth_user('read', config.user)

    # User wants to do action?
    if not config.may("act_all"):
	html.live.set_auth_user('action', config.user)

    # Default auth domain is read. Please set to None to switch off authorization
    html.live.set_auth_domain('read')

# This function does nothing. The sites have already
# been reconfigured according to the variable _site_switch,
# because that variable is processed by connect_to_livestatus()
def ajax_switch_site(html):
    pass 

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
        load_config(req)
	if html.var("debug"): # Debug flag may be set via URL
	    config.debug = True
        from lib import * # declarations of exceptions

	if not req.user or type(req.user) != str:
	    raise MKConfigError("You are not logged in. This should never happen. Please "
		    "review your Apache configuration. Check_MK Multisite requires HTTP login.")
	    
        # Set all permissions, read site config, and similar stuff
	config.login(html.req.user)

	# User allowed to login at all?
        if not config.may("use"):
	    reason = "Not Authorized.  You are logged in as <b>%s</b>. Your role is <b>%s</b>:" % (config.user, config.role_name)
            reason += "If you think this is an error, " \
                       "please ask your administrator to add your login into multisite.mk"
            raise MKConfigError(reason)

        # General access allowed. Now connect to livestatus
	connect_to_livestatus(html)

        # Module containing the actual pages
	import page_logwatch
	import views
	import sidebar

	pagehandlers = { "index"               : page_index,
			 "edit_views"          : views.page_edit_views,
			 "edit_view"           : views.page_edit_view,
			 "export_views"        : views.ajax_export,
			 "view"                : views.page_view,
			 "logwatch"            : page_logwatch.page,
			 "sidebar"             : sidebar.page_sidebar, # embedded
			 "side"                : sidebar.page_side,    # replacement for side.php
			 "sidebar_config"      : sidebar.page_configure, 
			 "switch_site"         : ajax_switch_site,
			 "sidebar_snapin"      : sidebar.ajax_snapin,
			 "sidebar_openclose"   : sidebar.ajax_openclose,
			 "switch_master_state" : sidebar.ajax_switch_masterstate,
			 "add_bookmark"        : sidebar.ajax_add_bookmark,
			 "del_bookmark"        : sidebar.ajax_del_bookmark,
			 "edit_bookmark"       : sidebar.page_edit_bookmark,
	}

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

    except livestatus.MKLivestatusNotFoundError, e:
	html.header("Data not found")
	html.show_error("The following query produced no output:\n<pre>\n%s</pre>\n" % \
		e.query)
	html.footer()

    except livestatus.MKLivestatusException, e:
	html.header("Livestatus problem")
	html.show_error("Livestatus problem: %s" % e)
	html.footer()
	
    except Exception, e:
	if config.debug:
            html.live = None
	    raise
        html.header("Internal Error")
	url = html.makeuri([("debug", "1")])
        html.show_error("Internal error: %s (<a href=\"%s\">Retry with debug mode</a>)" % (e, url))
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



