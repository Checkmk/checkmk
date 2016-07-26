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

from mod_python import Cookie, util, apache
from lib import make_utf8, MKGeneralException
import htmllib
import os, time, config, weblib, re
import defaults
import livestatus
import mobile

# Is used to end the HTTP request processing from deeper code levels
class FinalizeRequest(Exception):
    def __init__(self, code = None):
        self.status = code or apache.OK


class html_mod_python(htmllib.html):

    # The constructor must not rely on "config.", because the configuration
    # is not loaded yet. Earliest place is self.init_modes() where config
    # is loaded.
    def __init__(self, req, fields):
        req.content_type = "text/html; charset=UTF-8"
        req.header_sent = False

        # All URIs end in .py. We strip away the .py and get the
        # name of the page.
        self.myfile = req.uri.split("/")[-1][:-3]

        self.req = req
        htmllib.html.__init__(self)
        self.user = req.user
        if fields:
            self.fields = fields
        else:
            self.fields = util.FieldStorage(self.req, keep_blank_values = 1)
        self.read_get_vars()
        self.read_cookies()

        # Disable caching for all our pages as they are mostly dynamically generated,
        # user related and are required to be up-to-date on every refresh
        self.set_http_header("Cache-Control", "no-cache")

        self.init_mobile()
        self.set_output_format(self.var("output_format", "html"))


    # The web servers configured request timeout (Timeout in case of apache)
    def request_timeout(self):
        return int(self.req.server.timeout)


    def request_method(self):
        return self.req.method


    def remote_ip(self):
        return self.req.connection.remote_ip


    def is_ssl_request(self):
        return self.get_request_header('X-Forwarded-Proto') == 'https'


    def get_user_agent(self):
        return self.req.headers_in.get('User-Agent', '')


    def get_referer(self):
        return self.req.headers_in.get('Referer', '')


    def guitest_fake_login(self, user_id):
        config.login(user_id)
        self.user = user_id


    def verify_not_using_threaded_mpm(self):
        if apache.mpm_query(apache.AP_MPMQ_IS_THREADED) != 0:
            raise MKGeneralException(
                _("You are trying to Check_MK together with a threaded Apache multiprocessing module (MPM). "
                  "Check_MK is only working with the prefork module. Please change the MPM module to make "
                  "Check_MK work."))


    # Initializes the operation mode of the html() object. This is called
    # after the ChecK_MK GUI configuration has been loaded, so it is safe
    # to rely on the config.
    def init_modes(self):
        self.verify_not_using_threaded_mpm()

        if config.guitests_enabled:
            self.init_guitests()
        self.init_screenshot_mode()
        self.init_debug_mode()
        self.set_buffering(config.buffered_http_stream)


    def init_debug_mode(self):
        # Debug flag may be set via URL to override the configuration
        if self.var("debug"):
            config.debug = True
        self.enable_debug = config.debug


    # Enabling the screenshot mode omits the fancy background and
    # makes it white instead.
    def init_screenshot_mode(self):
        if self.var("screenshotmode", config.screenshotmode):
            self.screenshotmode = True


    def init_mobile(self):
        if self.has_var("mobile"):
            self.mobile = bool(self.var("mobile"))
            # Persist the explicitly set state in a cookie to have it maintained through further requests
            self.set_cookie("mobile", str(int(self.mobile)))

        elif self.has_cookie("mobile"):
            self.mobile = self.cookie("mobile", "0") == "1"

        else:
            self.mobile = mobile.is_mobile(self.get_user_agent())

        # Redirect to mobile GUI if we are a mobile device and
        # the URL is /
        if self.myfile == "index" and self.mobile:
            self.myfile = "mobile"


    # Install magic "live" object that connects to livestatus
    # on-the-fly
    def __getattr__(self, varname):
        if varname not in [ "live", "site_status" ]:
            raise AttributeError("html instance has no attribute '%s'" % varname)

        connect_to_livestatus()
        if varname == "live":
            return self.live
        else:
            return self.site_status


    def request_uri(self):
        return self.req.uri


    def login(self, user_id):
        self.user = user_id


    def is_logged_in(self):
        # Form based authentication always provides unicode strings, but the basic
        # authentication of mod_python provides regular strings.
        return self.user and type(self.user) in [ str, unicode ]


    def load_help_visible(self):
        try:
            self.help_visible = config.load_user_file("help", False)  # cache for later usage
        except:
            pass

    # Finish the HTTP request short before handing over to mod_python
    def finalize(self, is_error=False):
        self.live = None # disconnects from livestatus
        self.finalize_guitests()


    def get_request_header(self, key, deflt=None):
        return self.req.headers_in.get(key, deflt)


    def set_cookie(self, varname, value, expires = None):
        # httponly tells the browser not to make this cookie available to Javascript.
        # But it is only available from Python 2.6+. Be compatible.
        try:
            c = Cookie.Cookie(varname, make_utf8(value), path='/', httponly=True)
        except AttributeError:
            c = Cookie.Cookie(varname, make_utf8(value), path='/')

        if self.is_ssl_request():
            c.secure = True

        if expires is not None:
            c.expires = expires

        self.set_http_header("Set-Cookie", str(c))

    def del_cookie(self, varname):
        self.set_cookie(varname, '', time.time() - 60)

    def read_cookies(self):
        self.cookies = Cookie.get_cookies(self.req)

    def read_get_vars(self):
        self.parse_field_storage(self.fields)

    def lowlevel_write(self, text):
        if self.io_error:
            return

        try:
            if self.buffering:
                self.req.write(text, 0)
            else:
                self.req.write(text)
        except IOError, e:
            # Catch writing problems to client, prevent additional writes
            self.io_error = True
            self.log('%s' % e)

    def get_button_counts(self):
        return config.load_user_file("buttoncounts", {})

    def top_heading(self, title):
        if self.is_logged_in():
            login_text = "<b>%s</b> (%s" % (config.user_id, "+".join(config.user_role_ids))
            if self.enable_debug:
                if config.get_language():
                    login_text += "/%s" % config.get_language()
            login_text += ')'
        else:
            login_text = _("not logged in")
        self.top_heading_left(title)

        self.write('<td style="min-width:240px" class=right><span id=headinfo></span>%s &nbsp; ' % login_text)
        if config.pagetitle_date_format:
            self.write(' &nbsp; <b id=headerdate format="%s"></b>' % config.pagetitle_date_format)
        self.write(' <b id=headertime></b>')
        self.javascript('update_header_timer()')
        self.top_heading_right()

    def log(self, *args):
        from lib import logger, LOG_NOTICE
        for arg in args:
            if type(arg) in (str, unicode):
                text = arg
            else:
                text = repr(arg)
            logger(LOG_NOTICE, text)

    def http_redirect(self, url):
        self.set_http_header('Location', url)
        raise apache.SERVER_RETURN, apache.HTTP_MOVED_TEMPORARILY

    # When setting err_headers_out, don't set headers_out because setting
    # err_headers_out is also setting headers_out within mod_python. Otherwise
    # we would send out duplicate HTTP headers which might cause bugs.
    def set_http_header(self, key, val):
        self.req.err_headers_out.add(key, val)

    def set_content_type(self, ty):
        self.req.content_type = ty

    def check_limit(self, rows, limit):
        count = len(rows)
        if limit != None and count >= limit + 1:
            text = _("Your query produced more than %d results. ") % limit
            if self.var("limit", "soft") == "soft" and config.may("general.ignore_soft_limit"):
                text += '<a href="%s">%s</a>' % \
                             (self.makeuri([("limit", "hard")]), _('Repeat query and allow more results.'))
            elif self.var("limit") == "hard" and config.may("general.ignore_hard_limit"):
                text += '<a href="%s">%s</a>' % \
                             (self.makeuri([("limit", "none")]), _('Repeat query without limit.'))
            text += " " + _("<b>Note:</b> the shown results are incomplete and do not reflect the sort order.")
            self.show_warning(text)
            del rows[limit:]
            return False
        return True


    def load_transids(self, lock = False):
        return config.load_user_file("transids", [], lock)

    def save_transids(self, used_ids, unlock = False):
        if config.user_id:
            config.save_user_file("transids", used_ids, unlock)

    def save_tree_states(self):
        config.save_user_file("treestates", self.treestates)

    def load_tree_states(self):
        if self.treestates == None:
            self.treestates = config.load_user_file("treestates", {})

    def add_custom_style_sheet(self):
        for css in self.plugin_stylesheets():
           self.write('<link rel="stylesheet" type="text/css" href="css/%s">\n' % css)
        if config.custom_style_sheet:
            self.write('<link rel="stylesheet" type="text/css" href="%s">\n' % config.custom_style_sheet)

    def plugin_stylesheets(self):
        global plugin_stylesheets
        try:
            return plugin_stylesheets
        except:
            plugins_paths = [ defaults.web_dir + "/htdocs/css" ]
            if defaults.omd_root:
                plugins_paths.append(defaults.omd_root + "/local/share/check_mk/web/htdocs/css")
            plugin_stylesheets = set([])
            for dir in plugins_paths:
                if os.path.exists(dir):
                    for fn in os.listdir(dir):
                        if fn.endswith(".css"):
                            plugin_stylesheets.add(fn)
            return plugin_stylesheets



# Build up a connection to livestatus.
# Note: this functions was previously in index.py. But now it
# moved to html_mod_python, since we do not want to connect to
# livestatus always but just when it is needed.
def connect_to_livestatus():
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
        if config.may("sidesnap.sitestatus"):
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
            # Convert livestatus-proxy links into UNIX socket
            s = site["socket"]
            if type(s) == tuple and s[0] == "proxy":
                site["socket"] = "unix:" + defaults.livestatus_unix_socket + "proxy/" + sitename
                site["cache"] = s[1].get("cache", True)
            else:
                site["cache"] = False

            if siteconf.get("disabled", False):
                html.site_status[sitename] = { "state" : "disabled", "site" : site }
                disabled_sites[sitename] = site
            else:
                html.site_status[sitename] = { "state" : "dead", "site" : site }
                enabled_sites[sitename] = site

        html.live = livestatus.MultiSiteConnection(enabled_sites, disabled_sites)

        # Fetch status of sites by querying the version of Nagios and livestatus
        # This may be cached by a proxy for up to the next configuration reload.
        html.live.set_prepend_site(True)
        for sitename, v1, v2, ps, num_hosts, num_services in html.live.query(
              "GET status\n"
              "Cache: reload\n"
              "Columns: livestatus_version program_version program_start num_hosts num_services"):
            html.site_status[sitename].update({
                "state" : "online",
                "livestatus_version": v1,
                "program_version" : v2,
                "program_start" : ps,
                "num_hosts" : num_hosts,
                "num_services" : num_services,
            })
        html.live.set_prepend_site(False)

        # Get exceptions in case of dead sites
        for sitename, deadinfo in html.live.dead_sites().items():
            html.site_status[sitename]["exception"] = deadinfo["exception"]
            shs = deadinfo.get("status_host_state")
            html.site_status[sitename]["status_host_state"] = shs
            if shs == None:
                statename = "dead"
            else:
                statename = { 1:"down", 2:"unreach", 3:"waiting", }.get(shs, "unknown")
            html.site_status[sitename]["state"] = statename

    else:
        html.live = livestatus.SingleSiteConnection("unix:" + defaults.livestatus_unix_socket)
        html.live.set_timeout(3) # default timeout is 3 seconds
        html.site_status = { '': { "state" : "dead", "site" : config.site('') } }
        v1, v2, ps = html.live.query_row("GET status\nColumns: livestatus_version program_version program_start")
        html.site_status[''].update({ "state" : "online", "livestatus_version": v1, "program_version" : v2, "program_start" : ps })

    # If Multisite is retricted to data user is a nagios contact for,
    # we need to set an AuthUser: header for livestatus
    use_livestatus_auth = True
    if html.output_format == 'html':
        if config.may("general.see_all") and not config.user.get("force_authuser"):
            use_livestatus_auth = False
    else:
        if config.may("general.see_all") and not config.user.get("force_authuser_webservice"):
            use_livestatus_auth = False

    if use_livestatus_auth == True:
        html.live.set_auth_user('read',   config.user_id)
        html.live.set_auth_user('action', config.user_id)


    # May the user see all objects in BI aggregations or only some?
    if not config.may("bi.see_all"):
        html.live.set_auth_user('bi', config.user_id)

    # Default auth domain is read. Please set to None to switch off authorization
    html.live.set_auth_domain('read')

