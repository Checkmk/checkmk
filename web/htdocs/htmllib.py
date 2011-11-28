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

from mod_python import Cookie
import time, cgi, config, os, defaults, pwd, urllib, weblib
from lib import *
# Python 2.3 does not have 'set' in normal namespace.
# But it can be imported from 'sets'
try:
    set()
except NameError:
    from sets import Set as set

# Information about uri
class InvalidUserInput(Exception):
    def __init__(self, varname, text):
        self.varname = varname
        self.text = text


class uriinfo:
    def __init__(self, req):
        self.req = req

    # URI aus Dateiname und Variablen rekonstruieren
    # TODO: URI-Encode von Variablen!
    def geturi(self):
        uri = self.req.myfile + ".py"
        if len(self.req.vars):
            uri += "?" + urlencode(self.req.vars.items())
        return uri

    # [('varname1', value1), ('varname2', value2) ]
    def makeuri(self, addvars):
        return self.req.myfile + ".py?" + urlencode_vars(self.req.vars.items() + addvars)

    # Liste von Hidden-Felder erzeugen aus aktueller URI
    def hiddenfields(self, omit=[]):
        return ''.join([ '<input type=hidden name="%s" value="%s">\n' % i \
                         for i in self.req.vars.items() \
                         if i[0] not in omit ])


# Encode HTML attributes: replace " with &quot;, also replace
# < and >. This code is slow. 
def attrencode(value):
    if type(value) == int:
        return str(value)
    new = ""
    for c in value:
        if c == '"':
            new += "&quot;"
        elif c == '<':
            new += "&lt;"
        elif c == '>':
            new += "&gt;"
        else:
            new += c
    return new

# This function returns a str object, never unicode!
# Beware: this code is crucial for the performance of Multisite!
# Changing from the self coded urlencode to urllib.quote
# is saving more then 90% of the total HTML generating time
# on more complex pages!
def urlencode_vars(vars):
    output = ""
    for varname, value in vars:
        if output != "":
            output += "&"

	if type(value) == int:
	    value = str(value)
        elif type(value) == unicode:
            value = value.encode("utf-8")
        
        output += varname
        output += "="
        try:
            # urllib is not able to encode non-Ascii characters. Yurks
            output += urllib.quote(value)
        except:
            output += urlencode(value) # slow but working

    return output

def urlencode(value):
    if type(value) == unicode:
        value = value.encode("utf-8")
    elif value == None:
        return ""
    ret = ""
    for c in value:
        if c == " ":
            c = "+"
        elif ord(c) <= 32 or ord(c) > 127 or c in [ '+', '"', "'", "=", "&", ":", "%" ]:
            c = "%%%02x" % ord(c)
        ret += c
    return ret

def urldecode(value):
    return urllib.unquote_plus(value)

def u8(c):
    if ord(c) > 127:
        return "&#%d;" % ord(c)
    else:
        return c

def utf8_to_entities(text):
    if type(text) != unicode:
        return text
    else:
        return text.encode("utf-8")

    # Old code is soooooooo slow...
    n = ""
    for c in text:
        n += u8(c)
    return n

# remove all HTML-tags
def strip_tags(ht):
    while True:
        x = ht.find('<')
        if x == -1:
            break
        y = ht.find('>', x)
        if y == -1:
            break
        ht = ht[0:x] + ht[y+1:]
    return ht


class html:
    def __init__(self, req):
        self.req = req
        self.user_errors = {}
        self.focus_object = None
        self.global_vars = []
        self.render_headfoot = True
        self.browser_reload = 0
        self.browser_redirect = ''
        self.events = set([]) # currently used only for sounds
        self.header_sent = False
        self.output_format = "html"
        self.status_icons = {}
        self.link_target = None
        self.form_name = None
        self.form_vars = []
        self.context_buttons_open = False

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

    def set_output_format(self, f):
        self.output_format = f

    def set_link_target(self, framename):
        self.link_target = framename

    def write(self, text):
        if type(text) == unicode:
	    text = text.encode("utf-8")
        self.req.write(text)

    def heading(self, text):
        self.write("<h2>%s</h2>\n" % text)

    def rule(self):
        self.write("<hr/>")

    def age_text(self, timedif):
        timedif = int(timedif)
        if timedif < 120:
            return "%d sec" % timedif

        minutes = timedif / 60
        if minutes < 120:
            return "%d min" % minutes

        hours = minutes / 60
        if hours < 48:
            return "%d hrs" % hours

        days = hours / 24
        return "%d days" % days

    def begin_form(self, name, action = None, method = "GET", onsubmit = None, add_transid = True):
        self.form_vars = []
        if action == None:
            action = self.req.myfile + ".py"
        self.current_form = name
        if method.lower() == "post":
            enctype = ' enctype="multipart/form-data"'
        else:
            enctype = ''
        if onsubmit:
            onsubmit = ' onsubmit="%s"' % onsubmit
        else:
            onsubmit = ''
        self.write("<form name=%s class=%s action=\"%s\" method=%s%s%s>\n" %
                   (name, name, action, method, enctype, onsubmit))
        self.hidden_field("filled_in", name)
        if add_transid:
            self.hidden_field("_transid", str(self.current_transid()))
        self.hidden_fields(self.global_vars)
        self.form_name = name

    def end_form(self):
        self.write("</form>\n")

    def form_submitted(self):
        return self.has_var("filled_in")

    def add_user_error(self, varname, message):
        if type(varname) == list:
            for v in varname:
                self.add_user_error(v, message)
        else:
            self.user_errors[varname] = message

    def has_users_errors(self):
        return len(self.user_errors) > 0

    def hidden_field(self, var, value):
        if value != None:
            self.write("<input type=hidden name=%s value=\"%s\">\n" % (var, attrencode(value)))

    # Beware: call this method just before end_form(). It will
    # add all current non-underscored HTML variables as hiddedn
    # field to the form - *if* they are not used in any input
    # field. (this is the reason why you must not add any further
    # input fields after this method has been called).
    def hidden_fields(self, varlist = None, **args):
        add_action_vars = args.get("add_action_vars", False)
        if varlist != None:
            for var in varlist:
                value = self.req.vars.get(var, "")
                self.hidden_field(var, value)
        else: # add *all* get variables, that are not set by any input!
            for var, value in self.req.vars.items():
                if var not in self.form_vars and \
                    (var[0] != "_" or add_action_vars):
                    self.hidden_field(var, value)

    def add_global_vars(self, varnames):
        self.global_vars += varnames

    # [('varname1', value1), ('varname2', value2) ]
    def makeuri(self, addvars, remove_prefix = None):
        vars = [ (v, self.var(v)) for v in self.req.vars if not v.startswith("_") ]
        if remove_prefix != None:
            vars = [ i for i in vars if not i[0].startswith(remove_prefix) ]
        return self.req.myfile + ".py?" + urlencode_vars(vars + addvars)

    def makeactionuri(self, addvars):
        return self.makeuri(addvars + [("_transid", self.current_transid())])

    def makeuri_contextless(self, vars):
        return self.req.myfile + ".py?" + urlencode_vars(vars)

    def button(self, varname, title, cssclass=""):
        self.write("<input type=submit name=\"%s\" id=\"%s\" value=\"%s\" class=\"%s\">\n" % \
                   ( varname, varname, title, cssclass))

    def buttonlink(self, href, text, add_transid=False, obj_id='', style='', title='', disabled=''):
        if add_transid:
            href += "&_transid=%d" % self.current_transid()
        if obj_id:
            obj_id = ' id=%s' % obj_id
        if style:
            style = ' style="%s"' % style
        if title:
            title = ' title="%s"' % title
        if disabled:
            title = ' disabled="%s"' % disabled

        self.write('<input%s%s%s%s value="%s" class=buttonlink type=button onclick="location.href=\'%s\'">' % \
                (obj_id, style, title, disabled, text, href))
        # self.write("<a href=\"%s\" class=button%s%s>%s</a>" % (href, obj_id, style, text))

    def jsbutton(self, varname, text, onclick, style=''):
        if style:
            style = ' style="%s"' % style
        self.write("<input type=button name=%s id=%s onclick=\"%s\" "
                   "class=button%s value=\"%s\" />" % (varname, varname, onclick, style, text))

    def begin_context_buttons(self):
        self.context_button_hidden = False
        self.write("<table class=contextlinks><tr><td>\n")
        self.context_buttons_open = True

    def end_context_buttons(self):
        if self.context_buttons_open:
            if self.context_button_hidden:
                self.write('<div title="%s" id=toggle class="contextlink short" ' 
                      % _("Show all buttons"))
                self.context_button_hover_code("_short")
                self.write("><a onclick='unhide_context_buttons(this);' href='#'>...</a></div>")
            self.write("</td></tr></table>\n")
        self.context_buttons_open = False

    def context_button(self, title, url, icon=None, hot=False, id=None, bestof=None):
        display = ""
        if bestof:
            counts = config.load_user_file("buttoncounts", {})
            weights = counts.items()
            weights.sort(cmp = lambda a,b: cmp(a[1],  b[1]))
            best = dict(weights[-bestof:])
            if id not in best:
                display="none"
                self.context_button_hidden = True

        if not self.context_buttons_open:
            self.begin_context_buttons()

        if icon:
            title = '<img src="images/icon_%s.png">%s' % (icon, title)
        if id:
            idtext = " id='%s'" % id
        else:
            idtext = ""
        self.write('<div%s style="display: %s" class="contextlink%s" ' % (idtext, display, hot and " hot" or ""))
        self.context_button_hover_code(hot and "_hot" or "")
        self.write('>')
        self.write('<a href="%s"' % url)
        if bestof:
            self.write(' onmousedown="count_context_button(this); document.location=this.href; " ')
        self.write('>%s</a></div>' % title)

    def context_button_hover_code(self, what):
        self.write(r'''onmouseover='this.style.backgroundImage="url(\"images/contextlink%s_hi.png\")";' ''' % what)
        self.write(r'''onmouseout='this.style.backgroundImage="url(\"images/contextlink%s.png\")";' ''' % what)

    def number_input(self, varname, deflt = "", size=8):
        self.text_input(varname, str(deflt), "number", size=size)

    def text_input(self, varname, default_value = "", cssclass = "text", **args):
        if default_value == None:
            default_value = ""
        addprops = ""
        if "size" in args:
            addprops += " size=%d" % (args["size"] + 1)
        if "id" in args:
            addprops += " id='%s'" % args["id"]
        if "type" in args:
            mytype = args["type"]
        else:
            mytype = "text"
        if "autocomplete" in args:
            addprops += " autocomplete=\"%s\"" % args["autocomplete"]


        value = self.req.vars.get(varname, default_value)
        error = self.user_errors.get(varname)
        html = ""
        if error:
            html = "<x class=inputerror>"
        html += "<input type=%s class=%s value=\"%s\" name=\"%s\"%s>" % \
                     (mytype, cssclass, attrencode(value), varname, addprops)
        if error:
            html += "</x>"
            self.set_focus(varname)
        self.write(html)
        self.form_vars.append(varname)

    def password_input(self, varname, default_value = "", size=12, **args):
        self.text_input(varname, default_value, type="password", size = size, **args)

    def text_area(self, varname, deflt="", rows=4, cols=30):
        value = self.req.vars.get(varname, deflt)
        error = self.user_errors.get(varname)
        if error:
            self.write("<x class=inputerror>")
        
        self.write("<textarea rows=%d cols=%d name=\"%s\">%s</textarea>\n" % (
            rows, cols, varname, attrencode(value)))
        if error:
            self.write("</x>")
            self.set_focus(varname)
        self.form_vars.append(varname)

    def sorted_select(self, varname, options, deflt="", onchange=None, attrs = {}):
        # Sort according to display texts, not keys
        sorted = options[:]
        sorted.sort(lambda a,b: cmp(a[1].lower(), b[1].lower()))
        html.select(self, varname, sorted, deflt, onchange, attrs)

    def select(self, varname, options, deflt="", onchange=None, attrs = {}):
        current = self.var(varname, deflt)
        onchange_code = onchange and " onchange=\"%s\"" % (onchange) or ""

        attributes = ' ' + ' '.join([ '%s="%s"' % (k, v) for k, v in attrs.iteritems() ])

        self.write("<select%s name=\"%s\" id=\"%s\" size=\"1\"%s>\n" %
                             (onchange_code, varname, varname, attributes))
        for value, text in options:
            if value == None: value = ""
            sel = value == current and " selected" or ""
            self.write("<option value=\"%s\"%s>%s</option>\n" % (value, sel, text))
        self.write("</select>\n")
        if varname:
            self.form_vars.append(varname)

    def radiobutton(self, varname, value, checked, text):
        if self.has_var(varname):
            checked = self.var(varname) == value
        checked_text = checked and " checked" or ""
        self.write("<input type=radio name=%s value=\"%s\"%s> %s\n" %
                      (varname, value, checked_text, text))
        self.form_vars.append(varname)

    def checkbox(self, varname, deflt=False, cssclass = '', onclick = None, add_attr = []):
        error = self.user_errors.get(varname)
        if error:
            html = "<x class=inputerror>"
        # Problem with checkboxes: The browser will add the variable
        # only to the URL if the box is checked. So in order to detect
        # wether we should add the default value, we need to detect
        # if the form is printed for the first time. This is the
        # case if "filled_in" is not set.
        value = self.get_checkbox(varname)
        if value == None: # form not yet filled in
             value = deflt

        checked = value and " CHECKED" or ""
        if cssclass:
            cssclass = ' class="%s"' % cssclass
        onclick_code = onclick and " onclick=\"%s\"" % (onclick) or ""
        self.write("<input type=checkbox name=\"%s\"%s%s%s%s>" %
                        (varname, checked, cssclass, onclick_code, " ".join(add_attr)))
        self.form_vars.append(varname)
        if error:
            html += "</x>"

    # Get value of checkbox. Return True, False or None. None means
    # that no form has been submitted. The problem here is the distintion
    # between False and None. The browser does not set the variables for
    # Checkboxes that are not checked :-(
    def get_checkbox(self, varname, form_name = None):
        if self.has_var(varname):
            return not not self.var(varname)
        elif not self.has_var("filled_in") or ( # no form filled in
            self.form_name != None and self.var("filled_in") != self.form_name): # wrong form filled in
            return None
        else:
            # Form filled in but variable missing -> Checkbox not checked
            return False

    def datetime_input(self, varname, default_value):
        try:
            t = self.get_datetime_input(varname)
        except:
            t = default_value

        if varname in self.user_errors:
            self.add_user_error(varname + "_date", self.user_errors[varname])
            self.add_user_error(varname + "_time", self.user_errors[varname])
            self.set_focus(varname + "_date")

        br = time.localtime(t)
        self.date_input(varname + "_date", br.tm_year, br.tm_mon, br.tm_mday)
        self.write(" ")
        self.time_input(varname + "_time", br.tm_hour, br.tm_min)
        self.form_vars.append(varname + "_date")
        self.form_vars.append(varname + "_time")

    def time_input(self, varname, hours, mins):
        error = self.user_errors.get(varname)
        if error:
            self.write("<x class=inputerror>")
        self.write("<input type=text size=5 class=time name=%s value=\"%02d:%02d\">" %
                   (varname, hours, mins))
        if error:
            self.write("</x>")
        self.form_vars.append(varname)

    def date_input(self, varname, year, month, day):
        error = self.user_errors.get(varname)
        if error:
            self.write("<x class=inputerror>")
        self.write("<input type=text size=10 class=date name=%s value=\"%04d-%02d-%02d\">" %
                   (varname, year, month, day))
        if error:
            self.write("</x>")
        self.form_vars.append(varname)

    def get_datetime_input(self, varname):
        t = self.var(varname + "_time")
        d = self.var(varname + "_date")
        if not t or not d:
            raise MKUserError([varname + "_date", varname + "_time"],
                              _("Please specify a date and time."))

        try:
            br = time.strptime(d + " " + t, "%Y-%m-%d %H:%M")
        except:
            raise MKUserError([varname + "_date", varname + "_time"],
                              _("Please enter the date/time in the format YYYY-MM-DD HH:MM."))
        return int(time.mktime(br))

    def get_time_input(self, varname, what):
        t = self.var(varname)
        if not t:
            raise MKUserError(varname, _("Please specify %s.") % what)

        try:
            h, m = t.split(":")
            m = int(m)
            h = int(h)
            if m < 0 or m > 59 or h < 0:
                raise Exception()
        except:
            raise MKUserError(varname, _("Please enter the time in the format HH:MM."))
        return m * 60 + h * 3600

    def upload_file(self, varname):
        error = self.user_errors.get(varname)
        if error:
            self.write("<x class=inputerror>")
        self.write('<input type="file" name="%s">' % varname)
        if error:
            self.write("</x>")
        self.form_vars.append(varname)

    def html_head(self, title, add_js = True):
        if not self.req.header_sent:
            self.write(
                u'''<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN" "http://www.w3.org/TR/html4/loose.dtd">
                <html><head>
                <meta http-equiv="Content-Type" content="text/html; charset=utf-8">
                <title>''')
            # Ich versteh mit dem drecks UTF-8 bald garnix mehr...
            # self.req.write(title.encode("utf-8"))
            self.write(title)
            self.write('''</title>
                <link rel="stylesheet" type="text/css" href="check_mk.css">''')
    
            # If the variable _link_target is set, then all links in this page
            # should be targetted to the HTML frame named by _link_target. This
            # is e.g. useful in the dash-board
            if self.link_target:
                self.write('<base target="%s">' % self.link_target)

            # Load all style sheets in htdocs/css
            for css in self.plugin_stylesheets():
               self.write('                <link rel="stylesheet" type="text/css" href="css/%s">' % css)

            if config.custom_style_sheet:
               self.write('                <link rel="stylesheet" type="text/css" href="%s">' % config.custom_style_sheet)

            if add_js:
                self.write('''
                <script type='text/javascript' src='js/check_mk.js'></script>
                <script type='text/javascript' src='js/hover.js'></script>
                ''')

            if self.browser_reload != 0:
                if self.browser_redirect != '':
                    self.write("<script type=\"text/javascript\">setReload(%s, '%s')</script>\n" %
                                                                  (self.browser_reload, self.browser_redirect))
                else:
                    self.write("<script type=\"text/javascript\">setReload(%s)</script>\n" % self.browser_reload)


            self.write("</head>\n")
            self.req.header_sent = True

    def html_foot(self):
        self.write("</html>\n")

    def set_render_headfoot(self, render):
        self.render_headfoot = render

    def set_browser_reload(self, secs):
        self.browser_reload = secs

    def set_browser_redirect(self, secs, url):
        self.browser_reload   = secs
        self.browser_redirect = url

    def header(self, title='', **args):
        if self.output_format == "html":
            if not self.header_sent:
                self.html_head(title, **args)
                self.write('<body class="main %s">' % self.var("_body_class", ""))
                self.header_sent = True
                if self.render_headfoot:
                    self.top_heading(title)

    def top_heading(self, title):
        if type(self.req.user) == str:
            login_text = "<b>%s</b> (%s)" % (config.user_id, "+".join(config.user_role_ids))
        else:
            login_text = _("not logged in")
        self.write("<table class=header><tr><td class=left>%s</td><td class=right>"
                   "%s &nbsp; &nbsp; <b id=headertime>%s</b> <a href=\"http://mathias-kettner.de\"><img src=\"images/mk_logo_small.gif\"/></a></td></tr></table>" %
                   (title, login_text, time.strftime("%H:%M")))
        self.write("<hr class=header>\n")
        if config.debug:
            self.write("<div class=urldebug>%s</div>" % self.makeuri([]))


    def body_start(self, title=''):
        self.html_head(title)
        self.write('<body class="main %s">' % self.var("_body_class", ""))

    def bottom_focuscode(self):
        if self.focus_object:
            formname, varname = self.focus_object
            obj = formname + "." + varname
            self.write("<script language=\"javascript\" type=\"text/javascript\">\n"
                           "<!--\n"
                           "if(document.%s) {"
                           "    document.%s.focus();\n"
                           "    document.%s.select();\n"
                           "}\n"
                           "// -->\n"
                           "</script>\n" % (obj, obj, obj))

    def bottom_footer(self):
        if self.req.header_sent:
            self.bottom_focuscode()
            corner_text = ""
            if self.browser_reload:
                corner_text += _("refresh: %d secs") % self.browser_reload
            if self.render_headfoot:
                si = self.render_status_icons()
                self.write("<table class=footer><tr>"
                           "<td class=left>%s</td>"
                           "<td class=middle></td>"
                           "<td class=right>%s</td></tr></table>"
                               % (si, corner_text))

    def body_end(self):
        self.write("</body></html>\n")

    def footer(self):
        if self.output_format == "html":
            self.bottom_footer()
            self.body_end()

    def add_status_icon(self, img, tooltip):
        self.status_icons[img] = tooltip

    def render_status_icons(self):
        h = ""
        if True: # self.req.method == "GET":
            h += '<a target="_blank" href="%s"><img class=statusicon src="images/status_frameurl.png" title="URL to this frame"></a>\n' % \
                 self.makeuri([])
            h += '<a target="_blank" href="%s"><img class=statusicon src="images/status_pageurl.png" title="URL to this page including sidebar"></a>\n' % \
                 ("index.py?" + urlencode_vars([("start_url", self.makeuri([]))]))
        for img, tooltip in self.status_icons.items():
            h += '<img class=statusicon src="images/status_%s.png" title="%s">\n' % (img, tooltip)
        return h

    def show_error(self, msg):
        if self.output_format == "html":
            self.write("<div class=error>%s</div>\n" % msg)
        else:
            self.write(_("ERROR: "))
            self.write(strip_tags(msg))
            self.write("\n")

    def show_warning(self, msg):
        if self.output_format == "html":
            self.write("<div class=warning>%s</div>\n" % msg)
        else:
            self.write(_("WARNING: "))
            self.write(strip_tags(msg))
            self.write("\n")

    def message(self, msg):
        if self.output_format == "html":
            self.write("<div class=success>%s</div>\n" % msg)
        else:
            self.write(_("MESSAGE: "))
            self.write(strip_tags(msg))
            self.write("\n")

    def check_limit(self, rows, limit):
        count = len(rows)
        if limit != None and count >= limit + 1:
            text = _("Your query produced more than %d results. ") % limit
            if self.var("limit", "soft") == "soft" and config.may("ignore_soft_limit"):
                text += '<a href="%s">%s</a>' % \
                             (self.makeuri([("limit", "hard")]), _('Repeat query and allow more results.'))
            elif self.var("limit") == "hard" and config.may("ignore_hard_limit"):
                text += '<a href="%s">%s</a>' % \
                             (self.makeuri([("limit", "none")]), _('Repeat query without limit.'))
            self.show_warning(text)
            del rows[limit:]
            return False
        return True

    def do_actions(self):
        return self.var("_do_actions") not in [ "", None, "No" ]

    def set_focus(self, varname):
        self.focus_object = (self.form_name, varname)

    def has_var(self, varname):
        return varname in self.req.vars

    def var(self, varname, deflt = None):
        return self.req.vars.get(varname, deflt)

    def var_utf8(self, varname, deflt = None):
        val = self.req.vars.get(varname, deflt)
        if val == None:
            return val
        else:
            return val.decode("utf-8")

    def set_var(self, varname, value):
        if value == None:
            self.del_var(varname)
        else:
            self.req.vars[varname] = value

    def del_var(self, varname):
        if varname in self.req.vars:
            del self.req.vars[varname]

    def javascript(self, code):
        self.write("<script language=\"javascript\">\n%s\n</script>\n" % code)

    def javascript_file(self, name):
        self.write('<script type="text/javascript" src="js/%s.js"></script>\n' % name)

    def reload_sidebar(self):
        if not self.has_var("_ajaxid"):
            self.javascript("parent.frames[0].location.reload();");

    # Get next transaction id for that user
    def current_transid(self):
        user = self.req.user
        dir = defaults.var_dir + "/web/" + user
        try:
            os.makedirs(dir)
        except:
            pass

        path = dir + "/transid.mk"
        try:
            return int(file(path).read())
        except:
            return 0

    def increase_transid(self):
        current = self.current_transid()
        config.save_user_file("transid", current + 1)

    # Checks wether the current page is a reload or an original real submit
    def transaction_valid(self):
        if not self.var("_transid"):
            return False
        transid = int(self.var("_transid"))
        current = self.current_transid()
        return transid == current or transid == -1

    # called by page functions in order to check, if this was
    # a reload or the original form submission. Increases the
    # transid of the user, if the latter was the case
    def check_transaction(self):
        if self.transaction_valid():
            self.increase_transid()
            return True
        else:
            return False

    def confirm(self, msg):
        if self.var("_do_actions") == "No":
            return # user has pressed "No"               # None --> "No"
        if not self.has_var("_do_confirm"):
            self.write("<div class=really>%s" % msg)
            self.begin_form("confirm", None, "POST")
            self.hidden_fields(add_action_vars = True)
            self.button("_do_confirm", _("Yes!"), "really")
            self.button("_do_actions", _("No"), "")
            self.end_form()
            self.write("</div>")
            return False                                # False --> "Dialog shown, no answer yet"
        else:
            return self.check_transaction() and True or None # True: "Yes", None --> Browser reload

    def register_event(self, name):
        self.events.add(name)

    def has_event(self, name):
        return name in self.events

    def play_sound(self, url):
        self.write('<object type="audio/x-wav" data="%s" height="0" width="0">\n'
                  '<param name="filename" value="%s">\n'
                  '<param name="src" value="%s">\n'
                  '<param name="autostart" value="true">\n'
                  '<param name="playcount" value="1">\n'
                  '</object>\n' % (url, url, url))
        if config.debug:
            self.write("(playing sound %s)" % url)

    def apache_user(self):
        return pwd.getpwuid( os.getuid() )[ 0 ]

    def omd_mode(self):
        # Load mod_python env into regular environment
        os.environ.update(self.req.subprocess_env)

        omd_mode = None
        omd_site = None
        if 'OMD_SITE' in os.environ:
            omd_site = os.environ['OMD_SITE']
            omd_mode = 'shared'
            if omd_site == self.apache_user():
                omd_mode = 'own'
        return (omd_mode, omd_site)

    def begin_foldable_container(self, treename, id, isopen, title, indent = True): 
        # try to get persistet state of tree
        tree_state = weblib.get_tree_states(treename)

        if id in tree_state:
            isopen = tree_state[id] == "on"

        img_num = isopen and "90" or "00"
        onclick = ' onclick="toggle_foldable_container(\'%s\', \'%s\')"' % (treename, id)
        onclick += ' onmouseover="this.style.cursor=\'pointer\';" '
        onclick += ' onmouseout="this.style.cursor=\'auto\';" '
        
        if indent == "form":
            self.write('<table id="topic_%s" style="display: ''"  class="form nomargin"><tr ><td class=title>' % id.encode("utf-8"))
        self.write('<img align=absbottom class="treeangle" id="treeimg.%s.%s" '
                   'src="images/tree_%s.png" %s>' % 
                (treename, id, img_num, onclick))
        if title.startswith('<'): # custom HTML code
            self.write(title)
            if indent != "form":
                self.write("<br>")
        else:
            self.write('<b class="treeangle title" class=treeangle %s>%s</b><br>' % 
                     (onclick, title))

        indent_style = "padding-left: %dpx; " % (indent == True and 15 or 0)
        if indent == "form":
            self.write("</td></tr></table>")
            indent_style += "margin: 0; "
        self.write('<ul class="treeangle" style="%s display: %s" id="tree.%s.%s">' % 
             (indent_style, (not isopen) and "none" or "",  treename, id))

    def end_foldable_container(self):
        self.write("</ul>")

    def debug(self, *x):
        import pprint
        for element in x:
            self.write("<pre>%s</pre>\n" % pprint.pformat(element))

    def debug_vars(self):
        self.write('<table onmouseover="this.style.display=\'none\';" class=debug_vars>')
        self.write("<tr><th colspan=2>POST / GET Variables</th></tr>")
        for name, value in sorted(self.req.vars.items()):
            self.write("<tr><td class=left>%s</td><td class=right>%s</td></tr>\n" % (name, value))
        self.write("</ul>")

    # Needs to set both, headers_out and err_headers_out to be sure to send
    # the header on all responses
    def set_http_header(self, key, val):
        self.req.headers_out.add(key, val)
        self.req.err_headers_out.add(key, val)

    def has_cookie(self, varname):
        return varname in self.req.cookies

    def cookie(self, varname, deflt):
        try:
            return self.req.cookies[varname].value
        except:
            return deflt

    def set_cookie(self, varname, value, expires = None):
        c = Cookie.Cookie(varname, value, path = defaults.url_prefix)
        if expires is not None:
            c.expires = expires

        if not self.req.headers_out.has_key("Set-Cookie"):
            self.req.headers_out.add("Cache-Control", 'no-cache="set-cookie"')
            self.req.err_headers_out.add("Cache-Control", 'no-cache="set-cookie"')

        self.req.headers_out.add("Set-Cookie", str(c))
        self.req.err_headers_out.add("Set-Cookie", str(c))

    def del_cookie(self, varname):
        self.set_cookie(varname, '', time.time() - 60)
