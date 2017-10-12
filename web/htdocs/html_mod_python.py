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
from lib import make_utf8, MKGeneralException, MKException
from log import logger
import htmllib
import os, time, config, weblib, re
import mobile
import cmk.paths

# Is used to end the HTTP request processing from deeper code levels
class FinalizeRequest(Exception):
    def __init__(self, code = None):
        self.status = code or apache.OK
        super(FinalizeRequest, self).__init__(code)


class html_mod_python(htmllib.html):

    # The constructor must not rely on "config.", because the configuration
    # is not loaded yet. Earliest place is self.init_modes() where config
    # is loaded.
    def __init__(self, req, fields):
        htmllib.html.__init__(self)

        self.enable_request_timeout()

        req.content_type = "text/html; charset=UTF-8"
        req.header_sent = False

        # All URIs end in .py. We strip away the .py and get the
        # name of the page.
        self.myfile = req.uri.split("/")[-1][:-3]

        self.req = req
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
        self.set_output_format(self.var("output_format", "html").lower())


    def client_request_timeout(self):
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

        #if config.guitests_enabled:
        #    self.init_guitests()
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


    def request_uri(self):
        return self.req.uri


    def set_user_id(self, user_id):
        super(html_mod_python, self).set_user_id(user_id)
        # TODO: Shouldn't this be moved to some other place?
        self.help_visible = config.user.load_file("help", False)  # cache for later usage


    # Finish the HTTP request short before handing over to mod_python
    def finalize(self):
        self.disable_request_timeout()
        #self.finalize_guitests()


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
            logger.debug('%s' % e)

    def get_button_counts(self):
        return config.user.load_file("buttoncounts", {})

    def top_heading(self, title):
        if not isinstance(config.user, config.LoggedInNobody):
            login_text = "<b>%s</b> (%s" % (config.user.id, "+".join(config.user.role_ids))
            if self.enable_debug:
                if config.user.language():
                    login_text += "/%s" % config.user.language()
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


    def http_redirect(self, url):
        self.set_http_header('Location', url)
        raise apache.SERVER_RETURN, apache.HTTP_MOVED_TEMPORARILY


    # Used in htmllib
    def url_prefix(self):
        return config.url_prefix()


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
            if self.var("limit", "soft") == "soft" and config.user.may("general.ignore_soft_limit"):
                text += '<a href="%s">%s</a>' % \
                             (self.makeuri([("limit", "hard")]), _('Repeat query and allow more results.'))
            elif self.var("limit") == "hard" and config.user.may("general.ignore_hard_limit"):
                text += '<a href="%s">%s</a>' % \
                             (self.makeuri([("limit", "none")]), _('Repeat query without limit.'))
            text += " " + _("<b>Note:</b> the shown results are incomplete and do not reflect the sort order.")
            self.show_warning(text)
            del rows[limit:]
            return False
        return True


    def load_transids(self, lock = False):
        return config.user.load_file("transids", [], lock)

    def save_transids(self, used_ids):
        if config.user.id:
            config.user.save_file("transids", used_ids)

    def save_tree_states(self):
        config.user.save_file("treestates", self.treestates)


    def load_tree_states(self):
        if self.treestates == None:
            self.treestates = config.user.load_file("treestates", {})


    def add_custom_style_sheet(self):
        for css in self.plugin_stylesheets():
            self.write('<link rel="stylesheet" type="text/css" href="css/%s">\n' % css)

        if config.custom_style_sheet:
            self.write('<link rel="stylesheet" type="text/css" href="%s">\n' % config.custom_style_sheet)

        if cmk.is_managed_edition():
            import gui_colors
            gui_colors.GUIColors().render_html()


    def plugin_stylesheets(self):
        plugin_stylesheets = set([])
        for dir in [ cmk.paths.web_dir + "/htdocs/css", cmk.paths.local_web_dir + "/htdocs/css" ]:
            if os.path.exists(dir):
                for fn in os.listdir(dir):
                    if fn.endswith(".css"):
                        plugin_stylesheets.add(fn)
        return plugin_stylesheets


    def css_filename_for_browser(self, css):
        rel_path = "/share/check_mk/web/htdocs/" + css + ".css"
        if os.path.exists(cmk.paths.omd_root + rel_path) or \
            os.path.exists(cmk.paths.omd_root + "/local" + rel_path):
            return '%s-%s.css' % (css, cmk.__version__)


    # Make the browser load specified javascript files. We have some special handling here:
    # a) files which can not be found shal not be loaded
    # b) in OMD environments, add the Check_MK version to the version (prevents update problems)
    # c) load the minified javascript when not in debug mode
    def javascript_filename_for_browser(self, jsname):
        filename_for_browser = None
        rel_path = "/share/check_mk/web/htdocs/js"
        if self.enable_debug:
            min_parts = [ "", "_min" ]
        else:
            min_parts = [ "_min", "" ]

        for min_part in min_parts:
            path_pattern = cmk.paths.omd_root + "%s" + rel_path + "/" + jsname + min_part + ".js"
            if os.path.exists(path_pattern % "") or os.path.exists(path_pattern % "/local"):
                filename_for_browser = 'js/%s%s-%s.js' % (jsname, min_part, cmk.__version__)
                break

        return filename_for_browser


    def detect_icon_path(self, icon_name):
        # Detect whether or not the icon is available as images/icon_*.png
        # or images/icons/*.png. When an icon is available as internal icon,
        # always use this one
        is_internal = False
        rel_path = "share/check_mk/web/htdocs/images/icon_"+icon_name+".png"
        if os.path.exists(cmk.paths.omd_root+"/"+rel_path):
            is_internal = True
        elif os.path.exists(cmk.paths.omd_root+"/local/"+rel_path):
            is_internal = True

        if is_internal:
            return "images/icon_%s.png" % icon_name
        else:
            return "images/icons/%s.png" % icon_name
