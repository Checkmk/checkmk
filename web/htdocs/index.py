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
import sys, os, pprint
from lib import *
import livestatus
import defaults, config, htmllib

# Load page handlers
pagehandlers = {}
pagehandlers_dir = defaults.web_dir + "/plugins/pages"
for fn in os.listdir(pagehandlers_dir):
    if fn.endswith(".py"):
        execfile(pagehandlers_dir + "/" + fn)

if defaults.omd_root:
    local_module_path = defaults.omd_root + "/local/share/check_mk/web/htdocs"
    if local_module_path not in sys.path:
        sys.path[0:0] = [ local_module_path, defaults.web_dir + "/htdocs" ]
    local_pagehandlers_dir = defaults.omd_root + "/local/share/check_mk/web/plugins/pages"
    if os.path.exists(local_pagehandlers_dir):
        for fn in os.listdir(local_pagehandlers_dir):
            if fn.endswith(".py"):
                execfile(local_pagehandlers_dir + "/" + fn)

def read_get_vars(req):
    def parse_vars(vars):
        req.rawvars = util.parse_qs(vars, True)
        for (key,values) in req.rawvars.items():
            if len(values) >= 1:
                req.vars[key] = values[-1]
                req.multivars[key] = values

    req.multivars = {}
    req.vars = {}
    if req.args:
        parse_vars(req.args)
    postvars = req.read()
    if postvars:
        parse_vars(postvars)

def connect_to_livestatus(html):
    html.site_status = {}
    # site_status keeps a dictionary for each site with the following
    # keys:
    # "state"              --> "online", "disabled", "down", "unreach", "dead" or "waiting"
    # "exception"          --> An error exception in case of down, unreach, dead or waiting
    # "status_host_state"  --> host state of status host (0, 1, 2 or None)
    # "livestatus_version" --> Version of sites livestatus if "online"
    # "program_version"    --> Version of Nagios if "online"

    # If there is only one site (non-multisite), than
    # user cannot enable/disable.
    if config.is_multisite():
        # do not contact those sites the user has disabled.
        # Also honor HTML-variables for switching off sites
        # right now. This is generally done by the variable
        # _site_switch=sitename1:on,sitename2:off,...
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

        # Make lists of enabled and disabled sites
        enabled_sites = {}
        disabled_sites = {}

        for sitename, site in config.allsites().items():
            siteconf = config.user_siteconf.get(sitename, {})
            if siteconf.get("disabled", False):
                html.site_status[sitename] = { "state" : "disabled", "site" : site }
                disabled_sites[sitename] = site
            else:
                html.site_status[sitename] = { "state" : "dead", "site" : site }
                enabled_sites[sitename] = site

        html.live = livestatus.MultiSiteConnection(enabled_sites, disabled_sites)

        # Fetch status of sites by querying the version of Nagios and livestatus
        html.live.set_prepend_site(True)
        for sitename, v1, v2 in html.live.query("GET status\nColumns: livestatus_version program_version"):
            html.site_status[sitename].update({ "state" : "online", "livestatus_version": v1, "program_version" : v2 })
        html.live.set_prepend_site(False)

        # Get exceptions in case of dead sites
        for sitename, deadinfo in html.live.dead_sites().items():
            html.site_status[sitename]["exception"] = deadinfo["exception"]
            shs = deadinfo.get("status_host_state")
            html.site_status[sitename]["status_host_state"] = shs
            statename = { 1:"down", 2:"unreach", 3:"waiting", }.get(shs, "unknown")
            html.site_status[sitename]["state"] = statename

    else:
        html.live = livestatus.SingleSiteConnection("unix:" + defaults.livestatus_unix_socket)
        html.site_status = { '': { "state" : "dead", "site" : config.site('') } }
        v1, v2 = html.live.query_row("GET status\nColumns: livestatus_version program_version")
        html.site_status[''].update({ "state" : "online", "livestatus_version": v1, "program_version" : v2 })

    # If multiadmin is retricted to data user is a nagios contact for,
    # we need to set an AuthUser: header for livestatus
    if not config.may("see_all"):
        html.live.set_auth_user('read',   config.user)
        html.live.set_auth_user('action', config.user)

    # Default auth domain is read. Please set to None to switch off authorization
    html.live.set_auth_domain('read')


def handler(req):
    req.content_type = "text/html; charset=UTF-8"
    req.header_sent = False

    # All URIs end in .py. We strip away the .py and get the
    # name of the page.
    req.myfile = req.uri.split("/")[-1][:-3]

    # Create an object that contains all data about the request and
    # helper functions for creating valid HTML. Parse URI and
    # store results in the request object for later usage.
    html = htmllib.html(req)
    req.uriinfo = htmllib.uriinfo(req)

    try:
        read_get_vars(req)

        # Prepare output format
        output_format = html.var("output_format", "html")
        html.set_output_format(output_format)

        config.load_config() # load multisite.mk
        if html.var("debug"): # Debug flag may be set via URL
            config.debug = True

        if not req.user or type(req.user) != str:
            raise MKConfigError("You are not logged in. This should never happen. Please "
                    "review your Apache configuration. Check_MK Multisite requires HTTP login.")

        # Set all permissions, read site config, and similar stuff
        config.login(html.req.user)

        # User allowed to login at all?
        if not config.may("use"):
            reason = "Not Authorized.  You are logged in as <b>%s</b>. Your role is <b>%s</b>:" % (config.user, config.role)
            reason += "If you think this is an error, " \
                       "please ask your administrator to add your login into multisite.mk"
            raise MKAuthException(reason)

        # General access allowed. Now connect to livestatus
        connect_to_livestatus(html)

        handler = pagehandlers.get(req.myfile, page_not_found)
        handler(html)

    except MKUserError, e:
        html.header("Invalid User Input")
        html.show_error(str(e))
        html.footer()

    except MKAuthException, e:
        html.header("Permission denied")
        html.show_error(str(e))
        html.footer()

    except MKConfigError, e:
        html.header("Configuration Error")
        html.show_error(str(e))
        html.footer()
        apache.log_error("Configuration error: %s" % (e,), apache.APLOG_ERR)

    except MKGeneralException, e:
        html.header("Error")
        html.show_error(str(e))
        html.footer()
        apache.log_error("Error: %s" % (e,), apache.APLOG_ERR)

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

def page_not_found(html):
    html.header("Page not found")
    html.show_error("This page was not found. Sorry.")
    html.footer()
