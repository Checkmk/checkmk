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
# ails.  You should have  received  a copy of the  GNU  General Public
# License along with GNU Make; see the file  COPYING.  If  not,  write
# to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
# Boston, MA 02110-1301 USA.

# Notes for future rewrite:
#
# - Make clear which functions return values and which write out values
#   render_*, add_*, write_* (e.g. icon() -> outputs directly,
#                                  render_icon() -> returns icon
#                                  render_icon() -> returns icon
#
# - Order of arguments:
#   e.g. icon(help, icon) -> change and make help otional?
#
# - Fix names of message() show_error() show_warning()
#
# - change naming of html.attrencode() to html.render()
#
# - General rules:
# 1. values of type str that are passed as arguments or
#    return values or are stored in datastructures most not contain
#    non-Ascii characters! UTF-8 encoding must just be used in
#    the last few CPU cycles before outputting. Conversion from
#    input to str or unicode must happen as early as possible,
#    directly when reading from file or URL.

import time, os, pwd, urllib, random, re, __builtin__

from lib import *
# Python 2.3 does not have 'set' in normal namespace.
# But it can be imported from 'sets'
try:
    set()
except NameError:
    from sets import Set as set

# Only parse variable adhering to the following regular expressions
varname_regex = re.compile('^[\w\d_.%+-\\\*]+$')

# Information about uri
class InvalidUserInput(Exception):
    def __init__(self, varname, text):
        self.varname = varname
        self.text = text

# This is a simple class which wraps a string provided by the caller
# to make html.attrencode() know that this string should not be
# encoded, html.attrencode() will then return the unmodified value.
#
# This way we can implement encodings while still allowing HTML code
# processing for some special cases. This is useful when one needs
# to print out HTML tables in messages or help texts.
class HTML:
    def __init__(self, value):
        self.value = value

__builtin__.HTML = HTML

class html:
    def __init__(self):
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
        self.var_stash = []
        self.context_buttons_open = False
        self.mobile = False
        self.buffering = True
        self.transformations = []
        self.final_javascript_code = ""
        self.auto_id = 0
        self.have_help = False
        self.plugged = False
        self.keybindings = []
        self.keybindings_enabled = True
        self.io_error = False
        self.enable_debug = False
        self.screenshotmode = False
        self.help_visible = False
        self.treestates = {}
        self.treestates_for_id = None
        self.caches = {}
        self.new_transids = []
        self.ignore_transids = False
        self.current_transid = None
        self.page_context = {}

        # Time measurement
        self.times            = {}
        self.start_time       = time.time()
        self.last_measurement = self.start_time

    RETURN = 13
    SHIFT = 16
    CTRL = 17
    ALT = 18
    BACKSPACE = 8
    F1 = 112

    def set_page_context(self, c):
        self.page_context = c

    def set_buffering(self, b):
        self.buffering = b

    def push_transformation(self, tf):
        self.transformations.append(tf)

    def pop_transformation(self):
        del self.transformations[-1]

    def some_id(self):
        self.auto_id += 1
        return "id_%d" % self.auto_id

    def set_output_format(self, f):
        self.output_format = f

    def set_link_target(self, framename):
        self.link_target = framename

    def write(self, text):
        for tf in self.transformations:
            text = tf(text)

        if self.plugged:
            self.plugged_text += text
        else:
            # encode when really writing out the data. Not when writing plugged,
            # because the plugged code will be handled somehow by our code. We
            # only encode when leaving the pythonic world.
            if type(text) == unicode:
	        text = text.encode("utf-8")

            self.lowlevel_write(text)

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
        self.flush()
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

    def in_form(self):
        return self.form_name != None

    def begin_form(self, name, action = None, method = "GET",
                   onsubmit = None, add_transid = True):
        self.form_vars = []
        if action == None:
            action = self.myfile + ".py"
        self.current_form = name
        if method.lower() == "post":
            enctype = ' enctype="multipart/form-data"'
        else:
            enctype = ''
        if onsubmit:
            onsubmit = ' onsubmit="%s"' % self.attrencode(onsubmit)
        else:
            onsubmit = ''
        enc_name = self.attrencode(name)
        self.write('<form id="form_%s" name="%s" class="%s" action="%s" method="%s"%s%s>\n' %
                   (enc_name, enc_name, enc_name, self.attrencode(action), self.attrencode(method),
                    enctype, onsubmit))
        self.hidden_field("filled_in", name)
        if add_transid:
            self.hidden_field("_transid", str(self.get_transid()))
        self.hidden_fields(self.global_vars)
        self.form_name = name

    def end_form(self):
        self.write("</form>\n")
        self.form_name = None

    def form_submitted(self, form_name=None):
        if form_name:
            return self.var("filled_in") == form_name
        else:
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
            id = id and ' id="%s"' % self.attrencode(id) or ''
            self.write("<input type=\"hidden\" name=\"%s\" value=\"%s\"%s />" %
                                (self.attrencode(var), self.attrencode(value), id))
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
                value = self.vars.get(var, "")
                self.hidden_field(var, value)
        else: # add *all* get variables, that are not set by any input!
            for var, value in self.vars.items():
                if var not in self.form_vars and \
                    (var[0] != "_" or add_action_vars): # and var != "filled_in":
                    self.hidden_field(var, value)

    def add_global_vars(self, varnames):
        self.global_vars += varnames

    # [('varname1', value1), ('varname2', value2) ]
    def makeuri(self, addvars, remove_prefix=None, filename=None, delvars=None):
        new_vars = [ nv[0] for nv in addvars ]
        vars = [ (v, self.var(v))
                 for v in self.vars
                 if v[0] != "_" and v not in new_vars and (not delvars or v not in delvars) ]
        if remove_prefix != None:
            vars = [ i for i in vars if not i[0].startswith(remove_prefix) ]
        vars = vars + addvars
        if filename == None:
            filename = self.urlencode(self.myfile) + ".py"
        if vars:
            return filename + "?" + self.urlencode_vars(vars)
        else:
            return filename

    def makeactionuri(self, addvars):
        return self.makeuri(addvars + [("_transid", self.get_transid())])

    def makeuri_contextless(self, vars, filename=None):
        if not filename:
	    filename = self.myfile + ".py"
        if vars:
            return filename + "?" + self.urlencode_vars(vars)
        else:
            return filename

    def image_button(self, varname, title, cssclass = ''):
        if not self.mobile:
            self.write('<label for="%s" class="image_button">' % self.attrencode(varname))
        self.raw_button(varname, title, cssclass)
        if not self.mobile:
            self.write('</label>')

    def button(self, *args):
        self.image_button(*args)

    def raw_button(self, varname, title, cssclass=""):
        self.write("<input onfocus=\"if (this.blur) this.blur();\" "
                   "type=\"submit\" name=\"%s\" id=\"%s\" value=\"%s\" "
                   "class=\"%s\" />\n" % \
                   ( varname, varname, title, cssclass))


    def buttonlink(self, href, text, add_transid=False, obj_id='', style='', title='', disabled=''):
        if add_transid:
            href += "&_transid=%s" % self.get_transid()
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
            self.write('<label for="%s" class="image_button">' % obj_id)
        self.write('<input%s%s%s%s value="%s" class="buttonlink" type="button" onclick="location.href=\'%s\'" />\n' % \
                (obj_id, style, title, disabled, text, href))
        if not self.mobile:
            self.write('</label>')

    def icon(self, help, icon):
       self.write(self.render_icon(icon, help))

    def render_icon(self, icon, help="", middle=True):
        align = middle and ' align=absmiddle' or ''
        title = help and ' title="%s"' % self.attrencode(help) or ""
        if "/" in icon or "." in icon:
            src = "images/" + icon
        else:
            src = "images/icon_%s.png" % icon
        return '<img src="%s" class=icon%s%s />' % (src, align, title)

    def empty_icon(self):
        self.write('<img class=icon src="images/trans.png" />')

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
                   '</a>' % (id, onclick, style, target, cssclass, url, self.attrencode(help), icon))

    def empty_icon_button(self):
        self.write('<img class="iconbutton trans" src="images/trans.png">')

    def disabled_icon_button(self, icon):
        self.write('<img class="iconbutton" align=absmiddle src="images/icon_%s.png">' % icon)

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

    def context_button(self, title, url, icon=None, hot=False, id=None, bestof=None, hover_title='', fkey=None):
        title = self.attrencode(title)
        display = "block"
        if bestof:
            counts = self.get_button_counts()
            weights = counts.items()
            weights.sort(cmp = lambda a,b: cmp(a[1],  b[1]))
            best = dict(weights[-bestof:])
            if id not in best:
                display="none"
                self.context_button_hidden = True

        if not self.context_buttons_open:
            self.begin_context_buttons()

        if icon:
            title = '<img src="images/icon_%s.png">%s' % (self.attrencode(icon), self.attrencode(title))
        if id:
            idtext = " id='%s'" % self.attrencode(id)
        else:
            idtext = ""
        self.write('<div%s style="display:%s" class="contextlink%s%s" ' %
            (idtext, display, hot and " hot" or "", (fkey and self.keybindings_enabled) and " button" or ""))
        self.context_button_hover_code(hot and "_hot" or "")
        self.write('>')
        self.write('<a href="%s"' % self.attrencode(url))
        if hover_title:
            self.write(' title="%s"' % self.attrencode(hover_title))
        if bestof:
            self.write(' onclick="count_context_button(this); " ')
        if fkey and self.keybindings_enabled:
            title += '<div class=keysym>F%d</div>' % fkey
            self.add_keybinding([html.F1 + (fkey - 1)], "document.location='%s';" % self.attrencode(url))
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

    def text_input(self, varname, default_value = "", cssclass = "text", label = None, id = None,
                   submit = None, attrs = {}, **args):
        if default_value == None:
            default_value = ""
        addprops = ""
        add_style = ""
        if "size" in args and args["size"]:
            if args["size"] == "max":
                add_style = "width: 100%; "
            else:
                addprops += " size=\"%d\"" % (args["size"] + 1)
                if not args.get('omit_css_width', False) and "width:" not in args.get("style", "") and not self.mobile:
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
        if args.get("read_only"):
            addprops += " readonly"

        if submit != None:
            if not id:
                id = "ti_%s" % varname
            self.final_javascript('document.getElementById("%s").onkeydown = '
                             'function(e) { if (!e) e = window.event; textinput_enter_submit(e, "%s"); };'
                             % (id, submit))

        value = self.vars.get(varname, default_value)
        error = self.user_errors.get(varname)
        html = ""
        if error:
            html = "<x class=\"inputerror\">"
        if label:
            if not id:
                id = "ti_%s" % varname
            html += '<label for="%s">%s</label>' % (id, label)

        if id:
            addprops += ' id="%s"' % id

        attributes = ' ' + ' '.join([ '%s="%s"' % (k, v) for k, v in attrs.iteritems() ])
        html += "<input type=\"%s\" class=\"%s\" value=\"%s\" name=\"%s\"%s%s />\n" % \
                     (mytype, cssclass, self.attrencode(value), varname, addprops, attributes)
        if error:
            html += "</x>"
            self.set_focus(varname)
        self.write(html)
        self.form_vars.append(varname)

    def password_input(self, varname, default_value = "", size=12, **args):
        self.text_input(varname, default_value, type="password", size = size, **args)

    def text_area(self, varname, deflt="", rows=4, cols=30, attrs = {}):
        value = self.var(varname, deflt)
        error = self.user_errors.get(varname)
        if error:
            self.write("<x class=inputerror>")

        attributes = ' ' + ' '.join([ '%s="%s"' % (k, v) for k, v in attrs.iteritems() ])
        self.write("<textarea rows=%d cols=%d name=\"%s\"%s>%s</textarea>\n" % (
            rows, cols, varname, attributes, self.attrencode(value)))
        if error:
            self.write("</x>")
            self.set_focus(varname)
        self.form_vars.append(varname)

    def sorted_select(self, varname, choices, deflt="", onchange=None, attrs = {}):
        # Sort according to display texts, not keys
        sorted = choices[:]
        sorted.sort(lambda a,b: cmp(a[1].lower(), b[1].lower()))
        self.select(varname, sorted, deflt, onchange, attrs)

    # Choices is a list pairs of (key, title). They keys of the choices
    # and the default value must be of type None, str or unicode.
    def select(self, varname, choices, deflt="", onchange=None, attrs = {}):
        current = self.var_utf8(varname, deflt)
        onchange_code = onchange and " onchange=\"%s\"" % (onchange) or ""
        attrs.setdefault('size', 1)
        attributes = ' ' + ' '.join([ '%s="%s"' % (k, v) for k, v in attrs.iteritems() ])

        self.write("<select%s name=\"%s\" id=\"%s\"%s>\n" %
                             (onchange_code, varname, varname, attributes))
        for value, text in choices:
            if value == None:
                value = ""
            sel = value == current and " selected" or ""
            self.write("<option value=\"%s\"%s>%s</option>\n" %
                (self.attrencode(value), sel, self.attrencode(text)))
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
                       'value=\"%s\"%s>%s</option>\n' %
                        (icon, self.attrencode(value), sel, self.attrencode(text)))
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
            id = "rb_%s_%s" % (varname, self.attrencode(value))
            idtxt = ' id="%s"' % id
        else:
            idtxt = ""
        self.write("<input type=radio name=%s value=\"%s\"%s%s>\n" %
                      (varname, self.attrencode(value), checked_text, idtxt))
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
            form_name == None or \
            form_name in self.list_var("filled_in"))


    # Get value of checkbox. Return True, False or None. None means
    # that no form has been submitted. The problem here is the distintion
    # between False and None. The browser does not set the variables for
    # Checkboxes that are not checked :-(
    def get_checkbox(self, varname, form_name = None):
        if self.has_var(varname):
            return not not self.var(varname)
        elif not self.form_filled_in(form_name):
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
                        submit=submit, omit_css_width = True)

    def date_input(self, varname, year, month, day, submit=None):
        self.text_input(varname, "%04d-%02d-%02d" % (year, month, day),
                        cssclass="date", size=10, submit=submit, omit_css_width = True)

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

    def html_head(self, title, javascripts = [], stylesheets = ["pages"], force=False):
        if not self.header_sent or force:
            self.write(
                u'''<!DOCTYPE HTML>
<html><head>
<meta http-equiv="Content-Type" content="text/html; charset=utf-8" />\n''')
            self.write('<title>')
            self.write(self.attrencode(title))
            self.write('</title>\n')
            self.write('<meta http-equiv="X-UA-Compatible" content="IE=edge" />')

            # If the variable _link_target is set, then all links in this page
            # should be targetted to the HTML frame named by _link_target. This
            # is e.g. useful in the dash-board
            if self.link_target:
                self.write('<base target="%s">\n' % self.attrencode(self.link_target))

            # Load all specified style sheets and all user style sheets in htdocs/css
            for css in [ "check_mk" ] + stylesheets + [ 'ie' ]:
                if defaults.omd_root:
                    fname = '%s-%s.css' % (css, defaults.check_mk_version)
                else:
                    fname = '%s.css' % css

                if css == 'ie':
                    self.write('<!--[if IE]>\n')
                self.write('<link rel="stylesheet" type="text/css" href="%s" />\n' % fname)
                if css == 'ie':
                    self.write('<![endif]-->\n')

            self.add_custom_style_sheet()

            # Load specified Javascript files
            for js in [ "checkmk", "hover" ] + javascripts:
                if defaults.omd_root:
                    fname = 'js/%s-%s.js' % (js, defaults.check_mk_version)
                else:
                    fname = 'js/%s.js' % js
                self.write('<script type="text/javascript" src="%s"></script>\n' % fname)

            if self.browser_reload != 0:
                if self.browser_redirect != '':
                    self.write("<script type=\"text/javascript\">setReload(%s, '%s')</script>\n" %
                                                                  (self.browser_reload, self.browser_redirect))
                else:
                    self.write("<script type=\"text/javascript\">setReload(%s)</script>\n" % self.browser_reload)


            self.write("</head>\n")
            self.header_sent = True

    def html_foot(self):
        self.write("</html>\n")

    def set_render_headfoot(self, render):
        self.render_headfoot = render

    def set_browser_reload(self, secs):
        self.browser_reload = secs

    def http_redirect(self, url):
        raise MKGeneralException("http_redirect not implemented")

    def set_browser_redirect(self, secs, url):
        self.browser_reload   = secs
        self.browser_redirect = url

    def immediate_browser_redirect(self, secs, url):
        self.javascript("setReload(%s, '%s');" % (secs, url))

    def body_css_classes(self):
        body_classes = [ "main" ]
        if self.var("_body_class"):
            body_classes.append(self.var("_body_class"))
        if self.screenshotmode:
            body_classes.append("screenshotmode")
        return " ".join(body_classes)

    def body_start(self, title='', **args):
        self.html_head(title, **args)
        self.write('<body class="%s">' % self.body_css_classes())

    def header(self, title='', **args):
        if self.output_format == "html":
            if not self.header_sent:
                self.body_start(title, **args)
                self.header_sent = True
                if self.render_headfoot:
                    self.top_heading(title)

    def top_heading_left(self, title):
        self.write('<table class=header><tr><td width="*" class=heading>')
        self.write('<a href="#" onfocus="if (this.blur) this.blur();" '
                   'onclick="this.innerHTML=\'%s\'; document.location.reload();">%s</a></td>' %
                   (_("Reloading..."), self.attrencode(title)))

    def top_heading_right(self):
        cssclass = self.help_visible and "active" or "passive"
        self.write('<a id=helpbutton class=%s href="#" onclick="help_toggle();" style="display: none"></a>' %
            cssclass)
        self.write("%s</td></tr></table>" %
                   _("<a href=\"http://mathias-kettner.de\"><img src=\"images/logo_mk_small.png\"/></a>"))
        self.write("<hr class=header>\n")
        if self.enable_debug:
            self.dump_get_vars()

    def dump_get_vars(self):
        self.begin_foldable_container("html", "debug_vars", True, _("GET/POST variables of this page"))
        self.debug_vars(hide_with_mouse = False)
        self.end_foldable_container()

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
        if self.header_sent:
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
        if self.keybindings_enabled and self.keybindings:
            self.javascript("var keybindings = %r;\n"
                            "document.body.onkeydown = keybindings_keydown;\n"
                            "document.body.onkeyup = keybindings_keyup;\n"
                            "document.body.onfocus = keybindings_focus;\n" % self.keybindings)
        if self.final_javascript_code:
            self.javascript(self.final_javascript_code)
        self.write("</body></html>\n")

        # Hopefully this is the correct place to performe some "finalization" tasks.
        self.store_new_transids()

    def footer(self):
        if self.output_format == "html":
            self.bottom_footer()
            self.body_end()


    def add_status_icon(self, img, tooltip, url = None):
        if url:
            self.status_icons[img] = tooltip, url
        else:
            self.status_icons[img] = tooltip

    def render_status_icons(self):
        h = '<a target="_top" href="%s"><img class=statusicon src="images/status_frameurl.png" title="%s"></a>\n' % \
             (self.makeuri([]), _("URL to this frame"))
        h += '<a target="_top" href="%s"><img class=statusicon src="images/status_pageurl.png" title="%s"></a>\n' % \
             ("index.py?" + self.urlencode_vars([("start_url", self.makeuri([]))]), _("URL to this page including sidebar"))

        if self.myfile == "view" and self.var('mode') != 'availability':
            h += '<a target="_top" href="%s">' \
                 '<img class=statusicon src="images/status_download_csv.png" title="%s"></a>\n' % \
                 (self.makeuri([("output_format", "csv_export")]), _("Export as CSV"))

        if self.myfile == "view":
            mode_name = self.var('mode') == "availability" and "availability" or "view"

            encoded_vars = {}
            for k, v in self.page_context.items():
                if v == None:
                    v = ''
                elif type(v) == unicode:
                    v = v.encode('utf-8')
                encoded_vars[k] = v

            h += '<div class="visualadd"><a class="visualadd" href="javascript:void(0)" ' \
                 'onclick="toggle_add_to_visual(event, this, \'%s\', %s, {\'name\': \'%s\'})">' \
                 '<img class=statusicon src="images/status_add_dashlet.png" title="%s"></a></div>\n' % \
                 (mode_name, self.attrencode(repr(encoded_vars)), self.var('view_name'), _("Add this view to..."))

        for img, tooltip in self.status_icons.items():
            if type(tooltip) == tuple:
                tooltip, url = tooltip
                h += '<a target="_top" href="%s"><img class=statusicon src="images/status_%s.png" title="%s"></a>\n' % \
                     (url, img, tooltip)
            else:
                h += '<img class=statusicon src="images/status_%s.png" title="%s">\n' % (img, tooltip)

        if self.times:
            self.measure_time('body')
            h += '<div class=execution_times>'
            entries = self.times.items()
            entries.sort()
            for name, duration in entries:
                h += "<div>%s: %.1fms</div>" % (name, duration * 1000)
            h += '</div>'
        return h

    def show_exception(self, e):
        details = \
              'Check_MK Version: ' + defaults.check_mk_version + '\r\n' \
            + 'Page: ' + self.myfile + '.py\r\n\r\n' \
            + 'GET/POST-Variables:\r\n' \
            + '\r\n'.join([ ' '+n+'='+v for n, v in sorted(self.vars.items()) ]) + '\r\n' \
            + '\r\n' \
            + format_exception()

        mail_body = \
                 "Dear Check_MK Developer team,\r\n\r\n" \
               + "I hereby send you a report of a crash in the Check_MK Web GUI:\r\n\r\n" \
               + details + "\r\n" \
               + "\r\n\r\nWith best regards,\r\n\r\n"

        self.begin_context_buttons()
        mailto_url = self.makeuri_contextless([
            ("subject", "Check_MK GUI Crash Report - " + defaults.check_mk_version),
            ("body", mail_body)], filename="mailto:feedback@check-mk.org")
        self.context_button(_("Submit Report"), mailto_url, "email")
        self.end_context_buttons()

        self.write("<div class=error>")
        self.write("<b>%s:</b>\n%s<br><br>" % (_('Internal error'), self.attrencode(e)))

        self.begin_foldable_container("html", "exc_details", False, _("Details"))
        self.write('<div class=log_output>')
        self.write("<pre>%s</pre>" % details)
        self.write('</div>')
        self.end_foldable_container()
        self.write("</div>")

    def show_error(self, msg):
        self.message(msg, 'error')

    def show_warning(self, msg):
        self.message(msg, 'warning')

    # obj might be either a string (str or unicode) or an exception object
    def message(self, obj, what='message'):
        if what == 'message':
            cls    = 'success'
            prefix = _('MESSAGE')
        elif what == 'warning':
            cls    = 'warning'
            prefix = _('WARNING')
        else:
            cls    = 'error'
            prefix = _('ERROR')

        # Only strip off some tags. We allow some simple tags like
        # <b>, <tt>, <i> to be part of the exception message. The tags
        # are escaped first and then fixed again after attrencode.
        msg = self.attrencode(obj)
        msg = re.sub(r'&lt;(/?)(b|tt|i|br(?: /)?|pre|a|sup|p|li|ul|ol)&gt;', r'<\1\2>', msg)
        # Also repair link definitions
        msg = re.sub(r'&lt;a href=&quot;(.*)&quot;&gt;', r'<a href="\1">', msg)

        if self.output_format == "html":
            if self.mobile:
                self.write('<center>')
            self.write("<div class=%s>%s</div>\n" % (cls, msg))
            if self.mobile:
                self.write('</center>')
        else:
            self.write('%s: %s\n' % (prefix, self.strip_tags(msg)))

    def show_localization_hint(self):
        url = "wato.py?mode=edit_configvar&varname=user_localizations"
        self.message(HTML("<sup>*</sup>" +
            _("These texts may be localized depending on the users' "
              "language. You can configure the localizations "
              "<a href=\"%s\">in the global settings</a>.") % url))

    # Embed help box, whose visibility is controlled by a global
    # button in the page.
    def help(self, text):
        if text and text.strip():
            self.have_help = True
            self.write('<div class=help style="display: %s">' % (
                        not self.help_visible and "none" or "block"))
            self.write(text.strip())
            self.write('</div>')

    def do_actions(self):
        return self.var("_do_actions") not in [ "", None, _("No") ]

    def set_focus(self, varname):
        self.focus_object = (self.form_name, varname)

    def debug_vars(self, prefix=None, hide_with_mouse=True):
        if hide_with_mouse:
            hover = ' onmouseover="this.style.display=\'none\';"'
        else:
            hover = ""
        self.write('<table %s class=debug_vars>' % hover)
        self.write("<tr><th colspan=2>POST / GET Variables</th></tr>")
        for name, value in sorted(self.vars.items()):
            if not prefix or name.startswith(prefix):
                self.write("<tr><td class=left>%s</td><td class=right>%s</td></tr>\n" %
                    (self.attrencode(name), self.attrencode(value)))
        self.write("</table>")

    def var(self, varname, deflt = None):
        return self.vars.get(varname, deflt)

    def has_var(self, varname):
        return varname in self.vars

    # Checks if a variable with a given prefix is present
    def has_var_prefix(self, prefix):
        for varname in self.vars:
            if varname.startswith(prefix):
                return True
        return False

    def var_utf8(self, varname, deflt = None):
        val = self.vars.get(varname, deflt)
        if val != None and type(val) != unicode:
            return val.decode("utf-8")
        else:
            return val

    # Return all values of a variable that possible occurs more
    # than once in the URL. note: self.listvars does contain those
    # variable only, if the really occur more than once.
    def list_var(self, varname):
        if varname in self.listvars:
            return self.listvars[varname]
        elif varname in self.vars:
            return [self.vars[varname]]
        else:
            return []

    # Adds a variable to listvars and also set it
    def add_var(self, varname, value):
        self.listvars.setdefault(varname, [])
        self.listvars[varname].append(value)
        self.vars[varname] = value

    def set_var(self, varname, value):
        if value == None:
            self.del_var(varname)
        else:
            self.vars[varname] = value

    def del_var(self, varname):
        if varname in self.vars:
            del self.vars[varname]
        if varname in self.listvars:
            del self.listvars[varname]

    def del_all_vars(self, prefix = None):
        if not prefix:
            self.vars = {}
            self.listvars = {}
        else:
            self.vars = dict([(k,v) for (k,v) in self.vars.iteritems() if not k.startswith(prefix)])
            self.listvars = dict([(k,v) for (k,v) in self.listvars.iteritems() if not k.startswith(prefix)])

    def stash_vars(self):
        self.var_stash.append(self.vars.copy())

    def unstash_vars(self):
        self.vars = self.var_stash.pop()

    def javascript(self, code):
        self.write("<script language=\"javascript\">\n%s\n</script>\n" % code)

    def final_javascript(self, code):
        self.final_javascript_code += code + "\n"

    def javascript_file(self, name):
        self.write('<script type="text/javascript" src="js/%s.js"></script>\n' % name)

    def reload_sidebar(self):
        if not self.has_var("_ajaxid"):
            self.javascript("reload_sidebar()")

    def set_ignore_transids(self):
        self.ignore_transids = True

    # Compute a (hopefully) unique transaction id. This is generated during rendering
    # of a form or an action link, stored in a user specific file for later validation,
    # sent to the users browser via HTML code, then submitted by the user together
    # with the action (link / form) and then validated if it is a known transid. When
    # it is a known transid, it will be used and invalidated. If the id is not known,
    # the action will not be processed.
    def fresh_transid(self):
        transid = "%d/%d" % (int(time.time()), random.getrandbits(32))
        self.new_transids.append(transid)
        return transid

    def get_transid(self):
        if not self.current_transid:
            self.current_transid = self.fresh_transid()
        return self.current_transid

    # Marks a transaction ID as used. This is done by saving
    # it in a user specific settings file "transids.mk". At this
    # time we remove all entries from that list that are older
    # than one week.
    def store_new_transids(self):
        if self.new_transids:
            valid_ids = self.load_transids(lock = True)
            cleared_ids = []
            now = time.time()
            for valid_id in valid_ids:
                timestamp, rand = valid_id.split("/")
                if now - int(timestamp) < 86400: # one day
                    cleared_ids.append(valid_id)
            self.save_transids(cleared_ids + self.new_transids, unlock = True)

    # Remove the used transid from the list of valid ones
    def invalidate_transid(self, used_id):
        valid_ids = self.load_transids(lock = True)
        try:
            valid_ids.remove(used_id)
        except ValueError:
            return
        self.save_transids(valid_ids, unlock = True)

    # Checks, if the current transaction is valid, i.e. in case of
    # browser reload a browser reload, the form submit should not
    # be handled  a second time.. The HTML variable _transid must be present.
    #
    # In case of automation users (authed by _secret in URL): If it is empty
    # or -1, then it's always valid (this is used for webservice calls).
    # This was also possible for normal users, but has been removed to preven
    # security related issues.
    def transaction_valid(self):
        if not self.has_var("_transid"):
            return False

        id = self.var("_transid")
        if self.ignore_transids and (not id or id == '-1'):
            return True # automation

        if '/' not in id:
            return False

        # Normal user/password auth user handling
        timestamp, rand = id.split("/", 1)

        # If age is too old (one week), it is always
        # invalid:
        now = time.time()
        if now - int(timestamp) >= 604800: # 7 * 24 hours
            return False

        # Now check, if this id is a valid one
        return id in self.load_transids()

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

    # The confirm dialog is normally not a dialog which need to be protected
    # by a transid itselfs. It is only a intermediate step to the real action
    # But there are use cases where the confirm dialog is used during rendering
    # a normal page, for example when deleting a dashlet from a dashboard. In
    # such cases, the transid must be added by the confirm dialog.
    def confirm(self, msg, method="POST", action=None, add_transid=False):
        if self.var("_do_actions") == _("No"):
            # User has pressed "No", now invalidate the unused transid
            self.check_transaction()
            return # None --> "No"
        if not self.has_var("_do_confirm"):
            if self.mobile:
                self.write('<center>')
            self.write("<div class=really>%s" % msg)
            self.begin_form("confirm", method=method, action=action, add_transid=add_transid)
            self.hidden_fields(add_action_vars = True)
            self.button("_do_confirm", _("Yes!"), "really")
            self.button("_do_actions", _("No"), "")
            self.end_form()
            self.write("</div>")
            if self.mobile:
                self.write('</center>')
            return False # False --> "Dialog shown, no answer yet"
        else:
            # Now check the transaction
            return self.check_transaction() and True or None # True: "Yes", None --> Browser reload of "yes" page

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
        if self.enable_debug:
            self.write("(playing sound %s)" % url)

    def apache_user(self):
        return pwd.getpwuid( os.getuid() )[ 0 ]


    def debug(self, *x):
        import pprint
        for element in x:
            self.lowlevel_write("<pre>%s</pre>\n" % self.attrencode(pprint.pformat(element)))


    def has_cookie(self, varname):
        return varname in self.cookies

    def get_cookie_names(self):
        return self.cookies.keys()

    def cookie(self, varname, deflt):
        try:
            return self.cookies[varname].value
        except:
            return deflt

    # Keyboard control
    def add_keybinding(self, keylist, jscode):
        self.keybindings.append([keylist, jscode])

    def add_keybindings(self, bindings):
        self.keybindings += bindings

    def disable_keybindings(self):
        self.keybindings_enabled = False

    # From here: Former not class functions

    # Encode HTML attributes: replace " with &quot;, also replace
    # < and >. This code is slow. Works on str and unicode without
    # changing the type. Also works on things that can be converted
    # with %s.
    def attrencode(self, value):
        ty = type(value)
        if ty == int:
            return str(value)
        elif isinstance(value, HTML):
            return value.value # This is HTML code which must not be escaped
        elif ty not in [str, unicode]: # also possible: type Exception!
            value = "%s" % value # Note: this allows Unicode. value might not have type str now

        return value.replace('"', "&quot;").replace("<", "&lt;").replace(">", "&gt;")

    # This function returns a str object, never unicode!
    # Beware: this code is crucial for the performance of Multisite!
    # Changing from the self coded urlencode to urllib.quote
    # is saving more then 90% of the total HTML generating time
    # on more complex pages!
    def urlencode_vars(self, vars):
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
                output.append(varname + '=' + self.urlencode(value)) # slow but working

        return '&'.join(output)

    def urlencode(self, value):
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

    # Escape a variable name so that it only uses allowed charachters for URL variables
    def varencode(self, varname):
        if varname == None:
            return "None"
        if type(varname) == int:
            return varname

        ret = ""
        for c in varname:
            if not c.isdigit() and not c.isalnum() and c != "_":
                ret += "%%%02x" % ord(c)
            else:
                ret += c
        return ret

    def u8(self, c):
        if ord(c) > 127:
            return "&#%d;" % ord(c)
        else:
            return c

    def utf8_to_entities(self, text):
        if type(text) != unicode:
            return text
        else:
            return text.encode("utf-8")

    # remove all HTML-tags
    def strip_tags(self, ht):
        if type(ht) not in [str, unicode]:
            return ht
        while True:
            x = ht.find('<')
            if x == -1:
                break
            y = ht.find('>', x)
            if y == -1:
                break
            ht = ht[0:x] + ht[y+1:]
        return ht

    def strip_scripts(self, ht):
        while True:
            x = ht.find('<script')
            if x == -1:
                break
            y = ht.find('</script>')
            if y == -1:
                break
            ht = ht[0:x] + ht[y+9:]
        return ht

    def begin_foldable_container(self, treename, id, isopen, title, indent=True, first=False, icon=None, fetch_url=None):
        self.folding_indent = indent

        if self.user:
            isopen = self.foldable_container_is_open(treename, id, isopen)

        img_num = isopen and "90" or "00"
        onclick = ' onclick="toggle_foldable_container(\'%s\', \'%s\', \'%s\')"' % (
               treename, id, fetch_url and fetch_url or '');
        onclick += ' onmouseover="this.style.cursor=\'pointer\';" '
        onclick += ' onmouseout="this.style.cursor=\'auto\';" '

        if indent == "nform":
            self.write('<tr class=heading><td id="nform.%s.%s" %s colspan=2>' % (treename, id, onclick))
            if icon:
                self.write('<img class="treeangle title" src="images/icon_%s.png">' % icon)
            else:
                self.write('<img align=absbottom class="treeangle nform" src="images/tree_%s.png">' % (
                        isopen and "90" or "00"))
            self.write('%s</td></tr>' % title)
        else:
            if not icon:
                self.write('<img align=absbottom class="treeangle" id="treeimg.%s.%s" '
                           'src="images/tree_%s.png" %s>' %
                        (treename, id, img_num, onclick))
            if title.startswith('<'): # custom HTML code
                self.write(title)
                if indent != "form":
                    self.write("<br>")
            else:
                self.write('<b class="treeangle title" class=treeangle %s>' % onclick)
                if icon:
                    self.write('<img class="treeangle title" src="images/icon_%s.png">' % icon)
                self.write('%s</b><br>' % title)

            indent_style = "padding-left: %dpx; " % (indent == True and 15 or 0)
            if indent == "form":
                self.write("</td></tr></table>")
                indent_style += "margin: 0; "
            self.write('<ul class="treeangle %s" style="%s" id="tree.%s.%s">' %
                 (isopen and "open" or "closed", indent_style,  treename, id))

        # give caller information about current toggling state (needed for nform)
        return isopen

    def foldable_container_is_open(self, treename, id, isopen):
        # try to get persisted state of tree
        tree_state = self.get_tree_states(treename)

        if id in tree_state:
            isopen = tree_state[id] == "on"
        return isopen

    def end_foldable_container(self):
        if self.folding_indent != "nform":
            self.write("</ul>")

    def get_tree_states(self, tree):
        self.load_tree_states()
        return self.treestates.get(tree, {})

    def set_tree_state(self, tree, key, val):
        self.load_tree_states()

        if tree not in self.treestates:
            self.treestates[tree] = {}

        self.treestates[tree][key] = val

    def set_tree_states(self, tree, val):
        self.load_tree_states()
        self.treestates[tree] = val

    def parse_field_storage(self, fields, handle_uploads_as_file_obj = False):
        self.vars     = {}
        self.listvars = {} # for variables with more than one occurrance
        self.uploads  = {}

        for field in fields.list:
            varname = field.name

            # To prevent variours injections, we only allow a defined set
            # of characters to be used in variables
            if not varname_regex.match(varname):
                continue

            # put uploaded file infos into separate storage
            if field.filename is not None:
                if handle_uploads_as_file_obj:
                    value = field.file
                else:
                    value = field.value
                self.uploads[varname] = (field.filename, field.type, value)

            else: # normal variable
                # Multiple occurrance of a variable? Store in extra list dict
                if varname in self.vars:
                    if varname in self.listvars:
                        self.listvars[varname].append(field.value)
                    else:
                        self.listvars[varname] = [ self.vars[varname], field.value ]
                # In the single-value-store the last occurrance of a variable
                # has precedence. That makes appending variables to the current
                # URL simpler.
                self.vars[varname] = field.value

    def uploaded_file(self, varname, default = None):
        return self.uploads.get(varname, default)

    #
    # Per request caching
    #
    def set_cache(self, name, value):
        self.caches[name] = value

    def is_cached(self, name):
        return name in self.caches

    def get_cached(self, name):
        return self.caches.get(name)

    def measure_time(self, name):
        self.times.setdefault(name, 0.0)
        now = time.time()
        elapsed = now - self.last_measurement
        self.times[name] += elapsed
        self.last_measurement = now

