from mod_python import Cookie, util, apache
import htmllib
import os, time, config, weblib
import defaults

class html_mod_python(htmllib.html):

    def __init__(self, req):

        # All URIs end in .py. We strip away the .py and get the
        # name of the page.
        self.myfile = req.uri.split("/")[-1][:-3]
        self.req = req
        htmllib.html.__init__(self)
        self.user = req.user
        self.read_get_vars()
        self.read_cookies()
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
        self.vars = {}
        self.listvars = {} # for variables with more than one occurrance
        fields = util.FieldStorage(self.req, keep_blank_values = 1)
        for field in fields.list:
            varname = field.name
            value = field.value
            # Multiple occurrance of a variable? Store in extra list dict
            if varname in self.vars:
                if varname in self.listvars:
                    self.listvars[varname].append(value)
                else:
                    self.listvars[varname] = [ self.vars[varname], value ]
            # In the single-value-store the last occurrance of a variable
            # has precedence. That makes appending variables to the current
            # URL simpler.
            self.vars[varname] = value


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


    def load_transids(self):
        return config.load_user_file("transids", [])

    def save_transids(self, used_ids):
        config.save_user_file("transids", used_ids)

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



