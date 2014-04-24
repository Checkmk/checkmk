from mod_python import Cookie, util, apache
import htmllib
import os, time, config, weblib, re
import defaults
import livestatus

class html_mod_python(htmllib.html):

    def __init__(self, req, fields):

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


    def load_help_visible(self):
        try:
            self.help_visible = config.load_user_file("help", False)  # cache for later usage
        except:
            pass

    def set_cookie(self, varname, value, expires = None):
        c = Cookie.Cookie(varname, value, path = '/')
        if expires is not None:
            c.expires = expires

        if not self.req.headers_out.has_key("Set-Cookie"):
            self.req.headers_out.add("Cache-Control", 'no-cache="set-cookie"')
            self.req.err_headers_out.add("Cache-Control", 'no-cache="set-cookie"')

        self.req.headers_out.add("Set-Cookie", str(c))
        self.req.err_headers_out.add("Set-Cookie", str(c))

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
        if type(self.user) == str:
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
        self.write("<script language=\"javascript\" type=\"text/javascript\">updateHeaderTime()</script>")
        self.top_heading_right()

    def omd_mode(self):
        # Load mod_python env into regular environment
        for k, v in self.req.subprocess_env.items():
            os.environ[k] = v

        omd_mode = None
        omd_site = None
        if 'OMD_SITE' in os.environ:
            omd_site = os.environ['OMD_SITE']
            omd_mode = 'shared'
            if omd_site == self.apache_user():
                omd_mode = 'own'
        return (omd_mode, omd_site)


    # Debug logging directly to apache error_log
    # Even if this is for debugging purpose, set the log-level to WARN in all cases
    # since the apache in OMD sites has LogLevel set to "warn" by default which would
    # suppress messages generated here. Again, this is only for debugging during
    # development, so this should be no problem for regular users.
    def log(self, msg):
        if type(msg) != str:
            msg = repr(msg)
        self.req.log_error(msg, apache.APLOG_WARNING)

    def http_redirect(self, url):
        self.set_http_header('Location', url)
        raise apache.SERVER_RETURN, apache.HTTP_MOVED_TEMPORARILY

    # Needs to set both, headers_out and err_headers_out to be sure to send
    # the header on all responses
    def set_http_header(self, key, val):
        self.req.headers_out.add(key, val)
        self.req.err_headers_out.add(key, val)

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
        if self.id is not self.treestates_for_id:
            self.treestates = config.load_user_file("treestates", {})
            self.treestates_for_id = self.id

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

