#!/usr/bin/python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2009             mk@mathias-kettner.de |
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

import time, cgi
from lib import *

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
    return cgi.escape(value, True)

def urlencode_vars(vars):
    output = ""
    for varname, value in vars:
	if output != "":
	    output += "&"
	output += varname
	output += "="
	output += urlencode(value)
    return output

def urlencode(value):
    ret = ""
    for c in value:
        if c == " ":
            c = "+"
        elif ord(c) <= 32 or ord(c) > 127 or c in [ '+', '"', "'", "=", "&", ":", "%" ]:
            c = "%%%02x" % ord(c)
        ret += c
    return ret


class html:
    def __init__(self, req):
        self.req = req
        self.user_errors = {}
        self.focus_object = None
	self.global_vars = []
        
    def write(self, text):
        self.req.write(text)

    def heading(self, text):
	self.write("<h2>%s</h2>\n" % text)

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

    def begin_form(self, name, action = None):
	if action == None:
	    action = self.req.myfile + ".py"
        self.current_form = name
        self.write("<form name=%s class=%s action=\"%s\" method=GET>\n" %
                   (name, name, action))
	self.hidden_field("filled_in", "on")
	self.hidden_fields(self.global_vars)

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

    def hidden_fields(self, varlist = None):
        if varlist != None:
            for var in varlist:
                value = self.req.vars.get(var, "")
                self.hidden_field(var, value)
        else: # add *all* get variables
            for var, value in self.req.vars.items():
                self.hidden_field(var, value)

    def add_global_vars(self, varnames):
	self.global_vars += varnames
            
    # [('varname1', value1), ('varname2', value2) ]
    def makeuri(self, addvars):
	vars = [ (v, self.var(v)) for v in self.req.vars if not v.startswith("_") ]
        return self.req.myfile + ".py?" + urlencode_vars(vars + addvars)

    def button(self, varname, title, cssclass=""):
        self.write("<input type=submit name=\"%s\" id=\"%s\" value=\"%s\" class=\"%s\">\n" % \
                   ( varname, varname, title, cssclass))

    def buttonlink(self, href, text):
	self.write("<a href=\"%s\" class=button>%s</a>" % (href, text))

    def number_input(self, varname, deflt = ""):
	self.text_input(varname, str(deflt), "number")

    def text_input(self, varname, default_value = "", cssclass = "text"):
        value = self.req.vars.get(varname, default_value)
        error = self.user_errors.get(varname)
        html = ""
        if error:
            html = "<x class=inputerror>"
        html += "<input type=text class=%s value=\"%s\" name=\"%s\">" % (cssclass, attrencode(value), varname)
        if error:
            html += "</x>"
            self.set_focus(self.current_form, varname)
        self.write(html)

    def sorted_select(self, varname, options, deflt=""):
        # Sort according to display texts, not keys
	swapped = [ (disp, key) for key, disp in options ]
	swapped.sort()
	swapped = [ (key, disp) for disp, key in swapped ]
	html.select(self, varname, swapped, deflt)

    def select(self, varname, options, deflt=""):
	current = self.var(varname, deflt)
        self.write("<select name=\"%s\" size=\"1\">\n" % varname)
        for value, text in options:
            if value == current:
                sel = " selected"
            else:
                sel = ""
            self.write("<option value=\"%s\"%s>%s</option>\n" % (value, sel, text))
        self.write("</select>\n")

    def checkbox(self, varname, deflt):
	value = self.req.vars.get(varname, deflt)
	if value != "":
	    checked = " CHECKED"
	else:
	    checked = ""
	self.write("<input type=checkbox name=%s%s>" % (varname, checked))

    def datetime_input(self, varname, default_value):
        try:
            t = self.get_datetime_input(varname)
        except:
            t = default_value
        
        br = time.localtime(t)
        self.date_input(varname + "_date", br.tm_year, br.tm_mon, br.tm_mday)
        self.write(" ")
        self.time_input(varname + "_time", br.tm_hour, br.tm_min)

    def time_input(self, varname, hours, mins):
        error = self.user_errors.get(varname)
        if error:
            self.write("<x class=inputerror>")
        self.write("<input type=text size=5 class=time name=%s value=\"%02d:%02d\">" %
                   (varname, hours, mins))
        if error:
            self.write("</x>")

    def date_input(self, varname, year, month, day):
        error = self.user_errors.get(varname)
        if error:
            self.write("<x class=inputerror>")
        self.write("<input type=text size=10 class=date name=%s value=\"%04d-%02d-%02d\">" %
                   (varname, year, month, day))
        if error:
            self.write("</x>")

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


    def header(self, title=''):
        if not self.req.header_sent:
            self.req.write(
    '''<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN" "http://www.w3.org/TR/html4/loose.dtd">
    <html><head>
    <meta http-equiv="Content-Type" content="text/html; charset=utf-8">
    <title>%s</title>
    <link rel="stylesheet" type="text/css" href="check_mk.css">
    </head>
    <body>
    <h1>%s</h1>
    ''' % (title, title))
            self.req.header_sent = True

    def show_error(self, msg):
        self.write("<div class=error>%s</div>\n" % msg)

    def message(self, msg):
	self.write("<div class=success>%s</div>\n" % msg)

    def confirm(self, msg):
        if not self.has_var("_do_confirm"):
            self.write("<div class=really>%s" % msg)
            self.begin_form("confirm")
            self.hidden_fields()
            self.button("_do_confirm", "Yes!", "really")
            self.end_form()
            self.write("</div>")
            return False
	else:
	    return True

    def footer(self):
        if self.req.header_sent:
            if self.focus_object:
                formname, varname = self.focus_object
                obj = formname + "." + varname
                self.req.write("<script language=\"javascript\" type=\"text/javascript\">\n"
                               "<!--\n"
                               "document.%s.focus();\n"
                               "document.%s.select();\n"
                               "// -->\n"
                               "</script>\n" % (obj, obj))


	    if type(self.req.user) == str:
	       login_text = "Logged in as <b>%s</b>" % self.req.user
	    else:
	       login_text = "not logged in"
            self.req.write("<table class=footer><tr>"
                           "<td class=left>&copy; <a href=\"http://mathias-kettner.de\">Mathias Kettner</a></td>"
                           "<td class=middle>This is part of <a href=\"http://mathias-kettner.de/check_mk\">Check_MK</a> version %s</td>"
                           "<td class=right>%s</td></tr></table>"
                           % (self.req.defaults["check_mk_version"], login_text))
            self.req.write("</body></html>\n")


    def set_focus(self, formname, varname):
        self.focus_object = (formname, varname)

    def has_var(self, varname):
        return varname in self.req.vars
    
    def var(self, varname, deflt = None):
        return self.req.vars.get(varname, deflt)

    def set_var(self, varname, value):
	self.req.vars[varname] = value
