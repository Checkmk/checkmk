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

def attrencode(value):
    if type(value) in [str, unicode]:
        return cgi.escape(value)
    else:
        return cgi.escape(str(value), True)

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
        y = ht.find('>')
        ht = ht[0:x] + ht[y+1:]
    return ht


class html:
    def __init__(self, req):
        self.req = req
        self.user_errors = {}
        self.focus_object = None
        self.global_vars = []
        self.browser_reload = 0
        self.browser_redirect = ''
        self.events = set([]) # currently used only for sounds
        self.header_sent = False
        self.output_format = "html"
        self.status_icons = {}

    def set_output_format(self, f):
        self.output_format = f

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

    def begin_form(self, name, action = None, method = "GET"):
        self.form_vars = []
        if action == None:
            action = self.req.myfile + ".py"
        self.current_form = name
        if method.lower() == "post":
            enctype = ' enctype="multipart/form-data"'
        else:
            enctype = ''
        self.write("<form name=%s class=%s action=\"%s\" method=%s%s>\n" %
                   (name, name, action, method, enctype))
        self.hidden_field("filled_in", "on")
        self.hidden_field("_transid", str(self.current_transid()))
        self.hidden_fields(self.global_vars)
        self.form_name = name

    def end_form(self):
        self.write("</form>\n")

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
    def makeuri(self, addvars):
        vars = [ (v, self.var(v)) for v in self.req.vars if not v.startswith("_") ]
        return self.req.myfile + ".py?" + urlencode_vars(vars + addvars)

    def makeuri_contextless(self, vars):
        return self.req.myfile + ".py?" + urlencode_vars(vars)

    def button(self, varname, title, cssclass=""):
        self.write("<input type=submit name=\"%s\" id=\"%s\" value=\"%s\" class=\"%s\">\n" % \
                   ( varname, varname, title, cssclass))

    def buttonlink(self, href, text, add_transid=False, obj_id='', style=''):
        if add_transid:
            href += "&_transid=%d" % self.current_transid()
        if obj_id:
            obj_id = ' id=%s' % obj_id
        if style:
            style = ' style="%s"' % style
        self.write("<a href=\"%s\" class=button%s%s>%s</a>" % (href, obj_id, style, text))

    def jsbutton(self, varname, text, onclick, style=''):
        if style:
            style = ' style="%s"' % style
        self.write("<input type=button name=%s id=%s onclick=\"%s\" class=button%s value=\"%s\" />" % (varname, varname, onclick, style, text))

    def begin_context_buttons(self):
        self.write("<table class=contextlinks><tr><td>\n")

    def end_context_buttons(self):
        self.write("</td></tr></table>\n")

    def context_button(self, title, url, hot=False):
        self.write('<div class="contextlink%s" ' % (hot and " hot" or ""))
        self.write(r'''onmouseover='this.style.backgroundImage="url(\"images/contextlink%s_hi.png\")";' ''' % (hot and "_hot" or ""))
        self.write(r'''onmouseout='this.style.backgroundImage="url(\"images/contextlink%s.png\")";' ''' % (hot and "_hot" or ""))
        self.write('>')
        self.write('<a href="%s">%s</a></div>' % (url, title))

    def number_input(self, varname, deflt = "", size=8):
        self.text_input(varname, str(deflt), "number", size=size)

    def text_input(self, varname, default_value = "", cssclass = "text", **args):
        if default_value == None:
            default_value = ""
        addprops = ""
        if "size" in args:
            addprops += " size=%d" % args["size"]

        value = self.req.vars.get(varname, default_value)
        error = self.user_errors.get(varname)
        html = ""
        if error:
            html = "<x class=inputerror>"
        html += "<input type=text class=%s value=\"%s\" name=\"%s\"%s>" % (cssclass, attrencode(value), varname, addprops)
        if error:
            html += "</x>"
            self.set_focus(varname)
        self.write(html)
        self.form_vars.append(varname)

    def text_area(self, varname, rows):
        value = self.req.vars.get(varname, "")
        self.write("<textarea name=\"%s\">%s</textarea>\n" % (varname, value))
        self.form_vars.append(varname)

    def sorted_select(self, varname, options, deflt="", onchange=None):
        # Sort according to display texts, not keys
        swapped = [ (disp, key) for key, disp in options ]
        swapped.sort()
        swapped = [ (key, disp) for disp, key in swapped ]
        html.select(self, varname, swapped, deflt, onchange)

    def select(self, varname, options, deflt="", onchange=None):
        current = self.var(varname, deflt)
        onchange_code = onchange and " onchange=\"%s\"" % (onchange) or ""
        self.write("<select%s name=\"%s\" id=\"%s\" size=\"1\">\n" % (onchange_code, varname, varname))
        for value, text in options:
            if value == None: value = ""
            sel = value == current and " selected" or ""
            self.write("<option value=\"%s\"%s>%s</option>\n" % (value, sel, text))
        self.write("</select>\n")
        if varname:
            self.form_vars.append(varname)

    def radiobutton(self, varname, value, checked, text):
        checked_text = checked and " checked" or ""
        self.write("<input type=radio name=%s value=\"%s\"%s> %s\n" %
                      (varname, value, checked_text, text))
        self.form_vars.append(varname)

    def checkbox(self, varname, deflt="", cssclass = ''):
        error = self.user_errors.get(varname)
        if error:
            html = "<x class=inputerror>"
        value = self.req.vars.get(varname, deflt)
        if value != "" and value != False:
            checked = " CHECKED"
        else:
            checked = ""
        if cssclass:
            cssclass = ' class="%s"' % cssclass
        self.write("<input type=checkbox name=\"%s\"%s%s>" % (varname, checked, cssclass))
        self.form_vars.append(varname)
        if error:
            html += "</x>"

    def datetime_input(self, varname, default_value):
        try:
            t = self.get_datetime_input(varname)
        except:
            t = default_value

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
                              "Please specify a date and time")

        try:
            br = time.strptime(d + " " + t, "%Y-%m-%d %H:%M")
        except:
            raise MKUserError([varname + "_date", varname + "_time"],
                              "Please enter the date/time in the format YYYY-MM-DD HH:MM")
        return int(time.mktime(br))

    def get_time_input(self, varname, what):
        t = self.var(varname)
        if not t:
            raise MKUserError(varname, "Please specify %s" % what)

        try:
            h, m = t.split(":")
            m = int(m)
            h = int(h)
            if m < 0 or m > 59 or h < 0:
                raise Exception()
        except:
            raise MKUserError(varname, "Please enter the time in the format HH:MM")
        return m * 60 + h * 3600

    def upload_file(self, varname):
        error = self.user_errors.get(varname)
        if error:
            self.write("<x class=inputerror>")
        self.write('<input type="file" name="%s">' % varname)
        if error:
            self.write("</x>")
        self.form_vars.append(varname)

    def html_head(self, title):
        if not self.req.header_sent:
            self.req.write(
                u'''<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN" "http://www.w3.org/TR/html4/loose.dtd">
                <html><head>
                <meta http-equiv="Content-Type" content="text/html; charset=utf-8">
                <title>''')
            # Ich versteh mit dem drecks UTF-8 bald garnix mehr...
            # self.req.write(title.encode("utf-8"))
            self.req.write(title)
            self.req.write('''</title>
                <link rel="stylesheet" type="text/css" href="check_mk.css">''')
            if config.custom_style_sheet:
               self.req.write('                <link rel="stylesheet" type="text/css" href="%s">' % config.custom_style_sheet)
            self.req.write('''
                <script type='text/javascript' src='js/check_mk.js'></script>
                <script type='text/javascript' src='js/hover.js'></script>
            ''')

            if self.browser_reload != 0:
                if self.browser_redirect != '':
                    self.req.write("<script type=\"text/javascript\">setReload(%s, '%s')</script>\n" %
                                                                  (self.browser_reload, self.browser_redirect))
                else:
                    self.req.write("<script type=\"text/javascript\">setReload(%s)</script>\n" % self.browser_reload)


            self.req.write("</head>\n")
            self.req.header_sent = True

    def html_foot(self):
        self.write("</html>\n")

    def set_browser_reload(self, secs):
        self.browser_reload = secs

    def set_browser_redirect(self, secs, url):
        self.browser_reload   = secs
        self.browser_redirect = url

    def header(self, title=''):
        if self.output_format == "html":
            if not self.header_sent:
                self.html_head(title)
                self.write("<body class=main>")
                self.header_sent = True
                self.top_heading(title)

    def top_heading(self, title):
        if type(self.req.user) == str:
            login_text = "<b>%s</b> (%s)" % (config.user, config.role)
        else:
            login_text = "not logged in"
        self.write("<table class=header><tr><td class=left>%s</td><td class=right>"
                   "%s &nbsp; &nbsp; <b class=headertime>%s</b> <img src=\"images/mk_logo_small.gif\" /></td></tr></table>" %
                   (title, login_text, time.strftime("%H:%M")))
        self.write("<hr class=header>\n")


    def body_start(self, title=''):
        self.html_head(title)
        self.write("<body class=main>")

    def bottom_focuscode(self):
        if self.focus_object:
            formname, varname = self.focus_object
            obj = formname + "." + varname
            self.req.write("<script language=\"javascript\" type=\"text/javascript\">\n"
                           "<!--\n"
                           "document.%s.focus();\n"
                           "document.%s.select();\n"
                           "// -->\n"
                           "</script>\n" % (obj, obj))

    def bottom_footer(self):
        if self.req.header_sent:
            self.bottom_focuscode()
            corner_text = ""
            if self.browser_reload:
                corner_text += "refresh: %d secs" % self.browser_reload
            si = self.render_status_icons()
            self.req.write("<table class=footer><tr>"
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
        for img, tooltip in self.status_icons.items():
            h += '<img class=statusicon src="images/status_%s.png" title="%s">' % (img, tooltip)
        return h

    def show_error(self, msg):
        if self.output_format == "html":
            self.write("<div class=error>%s</div>\n" % msg)
        else:
            self.write("ERROR: ")
            self.write(strip_tags(msg))
            self.write("\n")

    def show_warning(self, msg):
        if self.output_format == "html":
            self.write("<div class=warning>%s</div>\n" % msg)
        else:
            self.write("WARNING: ")
            self.write(strip_tags(msg))
            self.write("\n")

    def message(self, msg):
        if self.output_format == "html":
            self.write("<div class=success>%s</div>\n" % msg)
        else:
            self.write("MESSAGE: ")
            self.write(strip_tags(msg))
            self.write("\n")

    def check_limit(self, rows, limit):
        count = len(rows)
        if limit != None and count >= limit + 1:
            text = "Your query produced more then %d results. " % limit
            if self.var("limit", "soft") == "soft" and config.may("ignore_soft_limit"):
                text += '<a href="%s">Repeat query and allow more results.</a>' % self.makeuri([("limit", "hard")])
            elif self.var("limit") == "hard" and config.may("ignore_hard_limit"):
                text += '<a href="%s">Repeat query without limit.</a>' % self.makeuri([("limit", "none")])
            self.show_warning(text)
            del rows[limit:]
            return False
        return True

    def confirm(self, msg):
        if self.var("_do_actions") == "No":
            return # user has pressed "No"
        if not self.has_var("_do_confirm"):
            self.write("<div class=really>%s" % msg)
            self.begin_form("confirm", None, "POST")
            self.hidden_fields(add_action_vars = True)
            self.button("_do_confirm", "Yes!", "really")
            self.button("_do_actions", "No", "")
            self.end_form()
            self.write("</div>")
            return False
        else:
            return self.check_transaction()

    def do_actions(self):
        return self.var("_do_actions") not in [ "", None, "No" ]

    def set_focus(self, varname):
        self.focus_object = (self.form_name, varname)

    def has_var(self, varname):
        return varname in self.req.vars

    def var(self, varname, deflt = None):
        return self.req.vars.get(varname, deflt)

    def var_utf8(self, varname, deflt = None):
        return self.req.vars.get(varname, deflt).decode("utf-8")

    def set_var(self, varname, value):
        self.req.vars[varname] = value

    def del_var(self, varname):
        del self.req.vars[varname]

    def javascript(self, code):
        self.write("<script language=\"javascript\">\n%s\n</script>\n" % code)

    def reload_sidebar(self):
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

    def register_event(self, name):
        self.events.add(name)

    def has_event(self, name):
        return name in self.events

    def play_sound(self, url):
        self.write('<object type="audio/x-wav" data="%s" height="0" width="0">'
                  '<param name="filename" value="%s">'
                  '<param name="autostart" value="true"><param name="playcount" value="1"></object>' % (url, url))
        if config.debug:
            self.write("Booom (%s)" % url)

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

    def begin_foldable_container(self, treename, id, isopen, title):
        # try to get persistet state of tree
        tree_state = weblib.get_tree_states(treename)
        if id in tree_state:
            isopen = tree_state[id] == "on"

        img_num = isopen and "90" or "00"
        onclick = ' onclick="toggle_foldable_container(\'%s\', \'%s\')"' % (treename, id)
        onclick += ' onmouseover="this.style.cursor=\'pointer\';" '
        onclick += ' onmouseout="this.style.cursor=\'auto\';" '
        
        self.write('<img align=absbottom class="treeangle" id="treeimg.%s.%s" '
                   'src="images/tree_%s.png" %s>' % 
                (treename, id, img_num, onclick))
        self.write('<b class="treeangle title" class=treeangle %s>%s</b><br>' % 
                 (onclick, title))
        self.write('<ul class="treeangle" style="display: %s" id="tree.%s.%s">' % 
             ((not isopen) and "none" or "",  treename, id))
    
    def end_foldable_container(self):
        self.write("</ul>")
