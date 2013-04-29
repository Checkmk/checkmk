#!/usr/bin/python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2013             mk@mathias-kettner.de |
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

from mod_python import Cookie, apache
import time, cgi, config, os, defaults, pwd, urllib, weblib, random
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
        if self.req.vars:
            uri += "?" + urlencode(self.req.vars.items())
        return uri

    # [('varname1', value1), ('varname2', value2) ]
    def makeuri(self, addvars):
        v = self.req.vars.items() + addvars
        if v:
            return self.req.myfile + ".py?" + urlencode_vars(v)
        else:
            return self.req.myfile + ".py"

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
    output = []
    for varname, value in vars:
	if type(value) == int:
	    value = str(value)
        elif type(value) == unicode:
            value = value.encode("utf-8")

        try:
            # urllib is not able to encode non-Ascii characters. Yurks
            output.append(varname + '=' + urllib.quote(value))
        except:
            output.append(varname + '=' + urlencode(value)) # slow but working

    return '&'.join(output)

def urlencode(value):
    if type(value) == unicode:
        value = value.encode("utf-8")
    elif value == None:
        return ""
    ret = ""
    for c in value:
        if c == " ":
            c = "+"
        elif ord(c) <= 32 or ord(c) > 127 or c in [ '#', '+', '"', "'", "=", "&", ":", "%" ]:
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

def strip_scripts(ht):
    while True:
        x = ht.find('<script')
        if x == -1:
            break
        y = ht.find('</script>')
        if y == -1:
            break
        ht = ht[0:x] + ht[y+9:]
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
        self.mobile = False
        self.buffering = True
        self.transformations = []
        self.final_javascript_code = ""
        self.auto_id = 0
        self.have_help = False
        self.plugged = False
        self.io_error = False

    def set_buffering(self, b):
        self.buffering = b

    def push_transformation(self, tf):
        self.transformations.append(tf)

    def pop_transformation(self):
        del self.transformations[-1]

    def some_id(self):
        self.auto_id += 1
        return "id_%d" % self.auto_id

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
        for tf in self.transformations:
            text = tf(text)

        if type(text) == unicode:
	    text = text.encode("utf-8")

        if self.plugged:
            self.plugged_text += text
        else:
            self.lowlevel_write(text)

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

    def plug(self):
        self.plugged = True
        self.plugged_text = ''

    def flush(self):
        if self.plugged:
            self.lowlevel_write(self.plugged_text)
            self.plugged_text = ''

    def drain(self):
        if self.plugged:
            t = self.plugged_text
            self.plugged_text = ''
            return t
        else:
            return ''

    def unplug(self):
        self.plugged = False

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

    def begin_form(self, name, action = None, method = "GET",
                   onsubmit = None, add_transid = True):
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
        self.write('<form id="form_%s" name="%s" class="%s" action="%s" method="%s"%s%s>\n' %
                   (name, name, name, action, method, enctype, onsubmit))
        self.hidden_field("filled_in", name)
        if add_transid:
            self.hidden_field("_transid", str(self.fresh_transid()))
        self.hidden_fields(self.global_vars)
        self.form_name = name

    def end_form(self):
        self.write("</form>\n")
        self.form_name = None

    def form_submitted(self):
        return self.has_var("filled_in")

    def add_user_error(self, varname, message):
        if type(varname) == list:
            for v in varname:
                self.add_user_error(v, message)
        else:
            self.user_errors[varname] = message

    def has_user_errors(self):
        return len(self.user_errors) > 0

    def show_user_errors(self):
        if self.has_user_errors():
            self.write('<div class=error>\n')
            self.write('<br>'.join(self.user_errors.values()))
            self.write('</div>\n')

    def hidden_field(self, var, value, id = None, add_var = False):
        if value != None:
            id = id and ' id="%s"' % id or ''
            self.write("<input type=hidden name=\"%s\" value=\"%s\"%s>" % (attrencode(var), attrencode(value), id))
            if add_var:
                self.add_form_var(var)

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
                    (var[0] != "_" or add_action_vars): # and var != "filled_in":
                    self.hidden_field(var, value)

    def add_global_vars(self, varnames):
        self.global_vars += varnames

    # [('varname1', value1), ('varname2', value2) ]
    def makeuri(self, addvars, remove_prefix = None, filename=None):
        vars = [ (v, self.var(v)) for v in self.req.vars if v[0] != "_" ]
        if remove_prefix != None:
            vars = [ i for i in vars if not i[0].startswith(remove_prefix) ]
        vars = vars + addvars
        if filename == None:
            filename = self.req.myfile + ".py"
        if vars:
            return filename + "?" + urlencode_vars(vars)
        else:
            return filename

    def makeactionuri(self, addvars):
        return self.makeuri(addvars + [("_transid", self.fresh_transid())])

    def makeuri_contextless(self, vars):
        if vars:
            return self.req.myfile + ".py?" + urlencode_vars(vars)
        else:
            return self.req.myfile + ".py"

    def image_button(self, varname, title, cssclass = ''):
        if not self.mobile:
            self.write('<label for="%s" class=image_button>' % varname)
        self.raw_button(varname, title, cssclass)
        if not self.mobile:
            self.write('</label>')

    def button(self, *args):
        self.image_button(*args)

    def raw_button(self, varname, title, cssclass=""):
        self.write("<input onfocus=\"if (this.blur) this.blur();\" "
                   "type=submit name=\"%s\" id=\"%s\" value=\"%s\" "
                   "class=\"%s\">\n" % \
                   ( varname, varname, title, cssclass))


    def buttonlink(self, href, text, add_transid=False, obj_id='', style='', title='', disabled=''):
        if add_transid:
            href += "&_transid=%s" % self.fresh_transid()
        if not obj_id:
            obj_id = self.some_id()
        obj_id = ' id=%s' % obj_id
        if style:
            style = ' style="%s"' % style
        if title:
            title = ' title="%s"' % title
        if disabled:
            title = ' disabled="%s"' % disabled

        if not self.mobile:
            self.write('<label for="%s" class=image_button>' % obj_id)
        self.write('<input%s%s%s%s value="%s" class=buttonlink type=button onclick="location.href=\'%s\'">' % \
                (obj_id, style, title, disabled, text, href))
        if not self.mobile:
            self.write('</label>')

    def icon(self, help, icon):
       self.write('<img align=absmiddle class=icon title="%s" src="images/icon_%s.png">' % (
        help, icon))

    def empty_icon(self):
        self.write('<img class=icon src="images/trans.png">')

    def icon_button(self, url, help, icon, id="", onclick="", style="", target="", cssclass=""):
        if id:
            id = "id='%s' " % id

        if onclick:
            onclick = 'onclick="%s" ' % onclick
            url = "javascript:void(0)"

        if style:
            style = 'style="%s" ' % style

        if target:
            target = 'target="%s" ' % target

        if cssclass:
            cssclass = 'class="%s" ' % cssclass

        self.write('<a %s%s%s%s%sonfocus="if (this.blur) this.blur();" href="%s">'
                   '<img align=absmiddle class=iconbutton title="%s" '
                   'src="images/button_%s_lo.png" '
                   'onmouseover=\"hilite_icon(this, 1)\" '
                   'onmouseout=\"hilite_icon(this, 0)\">'
                   '</a>' % (id, onclick, style, target, cssclass, url, help, icon))

    def empty_icon_button(self):
        self.write('<img class="iconbutton trans" src="images/trans.png">')

    def jsbutton(self, varname, text, onclick, style=''):
        if style:
            style = ' style="%s"' % style
        self.write("<input type=button name=%s id=%s onclick=\"%s\" "
                   "class=button%s value=\"%s\" />" % (varname, varname, onclick, style, text))

    def begin_context_buttons(self):
        if not self.context_buttons_open:
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

    def context_button(self, title, url, icon=None, hot=False, id=None, bestof=None, hover_title=''):
        display = "block"
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
        self.write('<div%s style="display:%s" class="contextlink%s" ' % (idtext, display, hot and " hot" or ""))
        self.context_button_hover_code(hot and "_hot" or "")
        self.write('>')
        self.write('<a href="%s"' % url)
        if hover_title:
            self.write(' title="%s"' % hover_title)
        if bestof:
            self.write(' onmousedown="count_context_button(this); document.location=this.href; " ')
        self.write('>%s</a></div>\n' % title)

    def context_button_hover_code(self, what):
        self.write(r'''onmouseover='this.style.backgroundImage="url(\"images/contextlink%s_hi.png\")";' ''' % what)
        self.write(r'''onmouseout='this.style.backgroundImage="url(\"images/contextlink%s.png\")";' ''' % what)

    def number_input(self, varname, deflt = "", size=8, style="", submit=None):
        self.text_input(varname, str(deflt), "number", size=size, style=style, submit=submit)


    # Needed if input elements are put into forms without the helper
    # functions of us.
    def add_form_var(self, varname):
        self.form_vars.append(varname)

    def text_input(self, varname, default_value = "", cssclass = "text", label = None, id = None, submit = None, **args):
        if default_value == None:
            default_value = ""
        addprops = ""
        add_style = ""
        if "size" in args and args["size"]:
            addprops += " size=%d" % (args["size"] + 1)
            if "width:" not in args.get("style", "") and not self.mobile:
                add_style = "width: %d.8ex; " % args["size"]

        if "type" in args:
            mytype = args["type"]
        else:
            mytype = "text"
        if "autocomplete" in args:
            addprops += " autocomplete=\"%s\"" % args["autocomplete"]
        if args.get("style"):
            addprops += " style=\"%s%s\"" % (add_style, args["style"])
        elif add_style:
            addprops += " style=\"%s\"" % add_style

        if submit != None:
            if not id:
                id = "ti_%s" % varname
            self.final_javascript('document.getElementById("%s").onkeydown = '
                             'function(e) { if (!e) e = window.event; textinput_enter_submit(e, "%s"); };'
                             % (id, submit))

        value = self.req.vars.get(varname, default_value)
        error = self.user_errors.get(varname)
        html = ""
        if error:
            html = "<x class=inputerror>"
        if label:
            if not id:
                id = "ti_%s" % varname
            html += '<label for="%s">%s</label>' % (id, label)

        if id:
            addprops += " id='%s'" % id

        html += "<input type=%s class=%s value=\"%s\" name=\"%s\"%s>" % \
                     (mytype, cssclass, attrencode(value), varname, addprops)
        if error:
            html += "</x>"
            self.set_focus(varname)
        self.write(html)
        self.form_vars.append(varname)

    def password_input(self, varname, default_value = "", size=12, **args):
        self.text_input(varname, default_value, type="password", size = size, **args)

    def text_area(self, varname, deflt="", rows=4, cols=30, attrs = {}):
        value = self.req.vars.get(varname, deflt)
        error = self.user_errors.get(varname)
        if error:
            self.write("<x class=inputerror>")

        attributes = ' ' + ' '.join([ '%s="%s"' % (k, v) for k, v in attrs.iteritems() ])
        self.write("<textarea rows=%d cols=%d name=\"%s\"%s>%s</textarea>\n" % (
            rows, cols, varname, attributes, attrencode(value)))
        if error:
            self.write("</x>")
            self.set_focus(varname)
        self.form_vars.append(varname)

    def sorted_select(self, varname, options, deflt="", onchange=None, attrs = {}):
        # Sort according to display texts, not keys
        sorted = options[:]
        sorted.sort(lambda a,b: cmp(a[1].lower(), b[1].lower()))
        self.select(varname, sorted, deflt, onchange, attrs)

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

    def icon_select(self, varname, options, deflt=""):
        current = self.var(varname, deflt)
        self.write("<select class=icon name=\"%s\" id=\"%s\" size=\"1\">\n" %
                    (varname, varname))
        for value, text, icon in options:
            if value == None: value = ""
            sel = value == current and " selected" or ""
            self.write('<option style="background-image:url(images/icon_%s.png);" '
                       'value=\"%s\"%s>%s</option>\n' % (icon, value, sel, text))
        self.write("</select>\n")
        if varname:
            self.form_vars.append(varname)

    def begin_radio_group(self, horizontal=False):
        if self.mobile:
            if horizontal:
	        add = 'data-type="horizontal" '
	    else:
	        add = ''
            self.write('<fieldset %s data-role="controlgroup">' % add)

    def end_radio_group(self):
        if self.mobile:
            self.write('</fieldset>')

    def radiobutton(self, varname, value, checked, label):
        if self.has_var(varname):
            checked = self.var(varname) == value
        checked_text = checked and " checked" or ""
        if label:
            id = "rb_%s_%s" % (varname, value)
            idtxt = ' id="%s"' % id
        else:
            idtxt = ""
        self.write("<input type=radio name=%s value=\"%s\"%s%s>\n" %
                      (varname, value, checked_text, idtxt))
        if label:
            self.write('<label for="%s">%s</label>\n' % (id, label))
        self.form_vars.append(varname)

    def begin_checkbox_group(self, horizonal=False):
	self.begin_radio_group(horizonal)

    def end_checkbox_group(self):
        self.end_radio_group()

    def checkbox(self, varname, deflt=False, cssclass = '', onclick = None, label=None, id=None, add_attr = None):
        if add_attr == None:
            add_attr = [] # do not use [] as default element, it will be a global variable!
        error = self.user_errors.get(varname)
        if error:
            self.write("<x class=inputerror>")

        self.write("<span class=checkbox>")
        # Problem with checkboxes: The browser will add the variable
        # only to the URL if the box is checked. So in order to detect
        # wether we should add the default value, we need to detect
        # if the form is printed for the first time. This is the
        # case if "filled_in" is not set.
        value = self.get_checkbox(varname)
        if value == None: # form not yet filled in
             value = deflt

        checked = value and " CHECKED " or ""
        if cssclass:
            cssclass = ' class="%s"' % cssclass
        onclick_code = onclick and " onclick=\"%s\"" % (onclick) or ""
        if label and not id:
            id = "cb_" + varname
        if id:
            add_attr.append('id="%s"' % id)
        add_attr_code = ''
        if add_attr:
            add_attr_code = ' ' + ' '.join(add_attr)
        self.write("<input type=checkbox name=\"%s\"%s%s%s%s>\n" %
                        (varname, checked, cssclass, onclick_code, add_attr_code))
        self.form_vars.append(varname)
        if label:
            self.write('<label for="%s">%s</label>\n' % (id, label))
        self.write("</span>")
        if error:
            self.write("</x>")

    # Check if the current form is currently filled in (i.e. we display
    # the form a second time while showing value typed in at the first
    # time and complaining about invalid user input)
    def form_filled_in(self, form_name = None):
        if form_name == None:
            form_name = self.form_name

        return self.has_var("filled_in") and (
            self.form_name == None or \
            self.form_name in self.list_var("filled_in"))


    # Get value of checkbox. Return True, False or None. None means
    # that no form has been submitted. The problem here is the distintion
    # between False and None. The browser does not set the variables for
    # Checkboxes that are not checked :-(
    def get_checkbox(self, varname, form_name = None):
        if self.has_var(varname):
            return not not self.var(varname)
        elif not self.form_filled_in():
            return None
        else:
            # Form filled in but variable missing -> Checkbox not checked
            return False

    def datetime_input(self, varname, default_value, submit=None):
        try:
            t = self.get_datetime_input(varname)
        except:
            t = default_value

        if varname in self.user_errors:
            self.add_user_error(varname + "_date", self.user_errors[varname])
            self.add_user_error(varname + "_time", self.user_errors[varname])
            self.set_focus(varname + "_date")

        br = time.localtime(t)
        self.date_input(varname + "_date", br.tm_year, br.tm_mon, br.tm_mday, submit=submit)
        self.write(" ")
        self.time_input(varname + "_time", br.tm_hour, br.tm_min, submit=submit)
        self.form_vars.append(varname + "_date")
        self.form_vars.append(varname + "_time")

    def time_input(self, varname, hours, mins, submit=None):
        self.text_input(varname, "%02d:%02d" % (hours, mins), cssclass="time", size=5,
                        submit=submit)

    def date_input(self, varname, year, month, day, submit=None):
        self.text_input(varname, "%04d-%02d-%02d" % (year, month, day),
                        cssclass="date", size=11, submit=submit)

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

    def html_head(self, title, javascripts = [], stylesheets = ["pages"]):
        if not self.req.header_sent:
            self.write(
                u'''<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN" "http://www.w3.org/TR/html4/loose.dtd">
<html><head>
<meta http-equiv="Content-Type" content="text/html; charset=utf-8">\n''')
            self.write('<title>')
            self.write(title)
            self.write('</title>\n')

            # If the variable _link_target is set, then all links in this page
            # should be targetted to the HTML frame named by _link_target. This
            # is e.g. useful in the dash-board
            if self.link_target:
                self.write('<base target="%s">\n' % self.link_target)

            # Load all specified style sheets and all user style sheets in htdocs/css
            for css in [ "check_mk" ] + stylesheets:
                self.write('<link rel="stylesheet" type="text/css" href="%s.css">\n' % css)
            self.write('<!--[if IE]>\n'
                       '<link rel="stylesheet" href="ie.css" type="text/css" />\n'
                       '<![endif]-->\n')

            for css in self.plugin_stylesheets():
               self.write('<link rel="stylesheet" type="text/css" href="css/%s">\n' % css)

            if config.custom_style_sheet:
               self.write('<link rel="stylesheet" type="text/css" href="%s">\n' % config.custom_style_sheet)

            # Load specified Javascript files
            for js in [ "checkmk", "hover" ] + javascripts:
                self.write('<script type="text/javascript" src="js/%s.js"></script>\n' % js)

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

    def immediate_browser_redirect(self, secs, url):
        self.javascript("setReload(%s, '%s');" % (secs, url))

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
            login_text = "<b>%s</b> (%s" % (config.user_id, "+".join(config.user_role_ids))
            if config.debug:
                if config.get_language():
                    login_text += "/%s" % config.get_language()
            login_text += ')'
        else:
            login_text = _("not logged in")
        self.write('<table class=header><tr><td width="*" class=heading>')
        self.write('<a href="#" onfocus="if (this.blur) this.blur();" '
                   'onclick="this.innerHTML=\'%s\'; document.location.reload();">%s</a></td>' %
                   (_("Reloading..."), title))
        self.write('<td style="min-width:240px" class=right><span id=headinfo></span>%s &nbsp; <b id=headertime>%s</b>' %
                   (login_text, time.strftime("%H:%M")))
        try:
            self.help_visible = config.load_user_file("help", False)  # cache for later usage
        except:
            self.help_visible = False

        cssclass = self.help_visible and "active" or "passive"
        self.write('<a id=helpbutton class=%s href="#" onclick="help_toggle();" style="display: none"></a>' %
            cssclass)
        self.write("%s</td></tr></table>" %
                   _("<a href=\"http://mathias-kettner.de\"><img src=\"images/mk_logo_small.gif\"/></a>"))
        self.write("<hr class=header>\n")
        if config.debug:
            self.write("<div class=urldebug>%s</div>" % self.makeuri([]))

    def body_start(self, title='', **args):
        self.html_head(title, **args)
        self.write('<body class="main %s">' % self.var("_body_class", ""))

    def bottom_focuscode(self):
        if self.focus_object:
            formname, varname = self.focus_object
            obj = formname + "." + varname
            self.write("<script language=\"javascript\" type=\"text/javascript\">\n"
                           "<!--\n"
                           "if (document.%s) {"
                           "    document.%s.focus();\n"
                           "    document.%s.select();\n"
                           "}\n"
                           "// -->\n"
                           "</script>\n" % (obj, obj, obj))

    def bottom_footer(self):
        if self.req.header_sent:
            self.bottom_focuscode()
            corner_text = ""
            corner_text += '<div style="display: %s" id=foot_refresh>%s</div>' % (
                (self.browser_reload and "inline-block" or "none",
                 _("refresh: <div id=foot_refresh_time>%s</div> secs") % self.browser_reload))
            if self.render_headfoot:
                si = self.render_status_icons()
                self.write("<table class=footer><tr>"
                           "<td class=left>%s</td>"
                           "<td class=middle></td>"
                           "<td class=right>%s</td></tr></table>"
                               % (si, corner_text))

    def body_end(self):
        if self.have_help:
            self.javascript("help_enable();")
        if self.final_javascript_code:
            self.javascript(self.final_javascript_code);
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
            h += '<a target="_top" href="%s"><img class=statusicon src="images/status_frameurl.png" title="%s"></a>\n' % \
                 (self.makeuri([]), _("URL to this frame"))
            h += '<a target="_top" href="%s"><img class=statusicon src="images/status_pageurl.png" title="%s"></a>\n' % \
                 ("index.py?" + urlencode_vars([("start_url", self.makeuri([]))]), _("URL to this page including sidebar"))
        for img, tooltip in self.status_icons.items():
            h += '<img class=statusicon src="images/status_%s.png" title="%s">\n' % (img, tooltip)
        return h

    def show_error(self, msg):
        if self.mobile:
            self.write('<center>')
        if self.output_format == "html":
            self.write("<div class=error>%s</div>\n" % msg)
        else:
            self.write(_("ERROR: "))
            self.write(strip_tags(msg))
            self.write("\n")
        if self.mobile:
            self.write('</center>')

    def show_warning(self, msg):
        if self.mobile:
            self.write('<center>')
        if self.output_format == "html":
            self.write("<div class=warning>%s</div>\n" % msg)
        else:
            self.write(_("WARNING: "))
            self.write(strip_tags(msg))
            self.write("\n")
        if self.mobile:
            self.write('</center>')

    def message(self, msg):
        if self.mobile:
            self.write('<center>')
        if self.output_format == "html":
            self.write("<div class=success>%s</div>\n" % msg)
        else:
            self.write(_("MESSAGE: "))
            self.write(strip_tags(msg))
            self.write("\n")
        if self.mobile:
            self.write('</center>')

    # Embed help box, whose visibility is controlled by a global
    # button in the page.
    def help(self, text):
        if text and text.strip():
            self.have_help = True
            self.write('<div class=help style="display: %s">' % (
                        not self.help_visible and "none" or "block"))
            self.write(text.strip())
            self.write('</div>')

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

    def do_actions(self):
        return self.var("_do_actions") not in [ "", None, _("No") ]

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

    # Return all values of a variable that possible occurs more
    # than once in the URL. note: req.listvars does contain those
    # variable only, if the really occur more than once.
    def list_var(self, varname):
        if varname in self.req.listvars:
            return self.req.listvars[varname]
        elif varname in self.req.vars:
            return [self.req.vars[varname]]
        else:
            return []

    # Adds a variable to listvars and also set it
    def add_var(self, varname, value):
        self.req.listvars.setdefault(varname, [])
        self.req.listvars[varname].append(value)
        self.req.vars[varname] = value

    def set_var(self, varname, value):
        if value == None:
            self.del_var(varname)
        else:
            self.req.vars[varname] = value

    def del_var(self, varname):
        if varname in self.req.vars:
            del self.req.vars[varname]
        if varname in self.req.listvars:
            del self.req.listvars[varname]

    def javascript(self, code):
        self.write("<script language=\"javascript\">\n%s\n</script>\n" % code)

    def final_javascript(self, code):
        self.final_javascript_code += code + "\n"

    def javascript_file(self, name):
        self.write('<script type="text/javascript" src="js/%s.js"></script>\n' % name)

    def reload_sidebar(self):
        if not self.has_var("_ajaxid"):
            self.javascript("if(parent && parent.frames[0]) parent.frames[0].location.reload();");

    # Compute a (hopefully) unique transaction id
    def fresh_transid(self):
        return "%d/%d" % (int(time.time()), random.getrandbits(32))

    # Marks a transaction ID as used. This is done by saving
    # it in a user specific settings file "transids.mk". At this
    # time we remove all entries from that list that are older
    # then one week.
    def invalidate_transid(self, id):
        used_ids = config.load_user_file("transids", [])
        new_ids = []
        now = time.time()
        for used_id in used_ids:
            timestamp, rand = used_id.split("/")
            if now - int(timestamp) < 604800: # 7 * 24 hours
                new_ids.append(used_id)
        used_ids.append(id)
        config.save_user_file("transids", used_ids)

    # Checks, if the current transaction is valid, i.e. now
    # browser reload. The HTML variable _transid must be present.
    # If it is empty or -1, then it's always valid (this is used
    # for webservice calls).
    def transaction_valid(self):
        if not self.has_var("_transid"):
            return False
        id = self.var("_transid")
        if not id or id == "-1":
            return True # automation
        timestamp, rand = id.split("/")

        # If age is too old (one week), it is always
        # invalid:
        now = time.time()
        if now - int(timestamp) >= 604800: # 7 * 24 hours
            return False

        # Now check, if this id is not yet invalidated
        return id not in config.load_user_file("transids", [])

    # Checks, if the current page is a transation, i.e. something
    # that is secured by a transid (such as a submitted form)
    def is_transaction(self):
        return self.has_var("_transid")

    # called by page functions in order to check, if this was
    # a reload or the original form submission. Increases the
    # transid of the user, if the latter was the case.
    # There are three return codes:
    # True:  -> positive confirmation by the user
    # False: -> not yet confirmed, question is being shown
    # None:  -> a browser reload or a negative confirmation
    def check_transaction(self):
        if self.transaction_valid():
            id = self.var("_transid")
            if id and id != "-1":
                self.invalidate_transid(id)
            return True
        else:
            return False

    def confirm(self, msg, method="POST", action=None):
        if self.var("_do_actions") == _("No"):
            return # user has pressed "No"               # None --> "No"
        if not self.has_var("_do_confirm"):
            if self.mobile:
                self.write('<center>')
            self.write("<div class=really>%s" % msg)
            self.begin_form("confirm", method=method, action=action)
            self.hidden_fields(add_action_vars = True)
            self.button("_do_confirm", _("Yes!"), "really")
            self.button("_do_actions", _("No"), "")
            self.end_form()
            self.write("</div>")
            if self.mobile:
                self.write('</center>')
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

    def begin_foldable_container(self, treename, id, isopen, title, indent = True, first = False):
        self.folding_indent = indent
        # try to get persisted state of tree
        tree_state = weblib.get_tree_states(treename)

        if id in tree_state:
            isopen = tree_state[id] == "on"

        img_num = isopen and "90" or "00"
        onclick = ' onclick="toggle_foldable_container(\'%s\', \'%s\')"' % (treename, id)
        onclick += ' onmouseover="this.style.cursor=\'pointer\';" '
        onclick += ' onmouseout="this.style.cursor=\'auto\';" '

        if indent == "nform":
            self.write('<tr class=heading><td id="nform.%s.%s" %s colspan=2>' % (treename, id, onclick))
            self.write('%s</td></tr>' % title)
        else:
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
            self.write('<ul class="treeangle %s" style="%s" id="tree.%s.%s">' %
                 (isopen and "open" or "closed", indent_style,  treename, id))

        # give caller information about current toggling state (needed for nform)
        return isopen

    def end_foldable_container(self):
        if self.folding_indent != "nform":
            self.write("</ul>")

    def debug(self, *x):
        import pprint
        for element in x:
            self.lowlevel_write("<pre>%s</pre>\n" % pprint.pformat(element))

    # Debug logging directly to apache error_log
    # Even if this is for debugging purpose, set the log-level to WARN in all cases
    # since the apache in OMD sites has LogLevel set to "warn" by default which would
    # suppress messages generated here. Again, this is only for debugging during
    # development, so this should be no problem for regular users.
    def log(self, msg):
        if type(msg) != str:
            msg = repr(msg)
        self.req.log_error(msg, apache.APLOG_WARNING)

    def debug_vars(self):
        self.lowlevel_write('<table onmouseover="this.style.display=\'none\';" class=debug_vars>')
        self.lowlevel_write("<tr><th colspan=2>POST / GET Variables</th></tr>")
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

    def get_cookie_names(self):
        return self.req.cookies.keys()

    def cookie(self, varname, deflt):
        try:
            return self.req.cookies[varname].value
        except:
            return deflt

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

