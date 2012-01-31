#!/usr/bin/python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2012             mk@mathias-kettner.de |
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

import math, os, time, re, urlparse
from lib import *

# Abstract base class of all value declaration classes.
class ValueSpec:
    def __init__(self, **kwargs):
        self._title         = kwargs.get("title")
        self._help          = kwargs.get("help")
        if "default_value" in kwargs:
            self._default_value = kwargs.get("default_value")

    def title(self):
        return self._title

    def help(self):
        return self._help

    # Create HTML-form elements that represent a given
    # value and let the user edit that value. The varprefix
    # is prepended to the HTML variable names and is needed
    # in order to make the variable unique in case that another
    # Value of the same type is being used as well.
    # The function may assume that the type of the value is valid.
    def render_input(self, varprefix, value):
        pass

    # Sets the input focus (cursor) into the most promiment
    # field of the HTML code previously rendered with render_input()
    def set_focus(self, varprefix):
        html.set_focus(varprefix)

    # Create a canonical, minimal, default value that
    # matches the datatype of the value specification and
    # fullfills also data validation.
    def canonical_value(self):
        return None

    # Return a default value for this variable. This
    # is optional and only used in the value editor
    # for same cases where the default value is known.
    def default_value(self):
        try:
            return self._default_value
        except:
            return self.canonical_value()

    # Creates a text-representation of the value that can be
    # used in tables and other contextes. It is to be read
    # by the user and need not to be parsable.
    # The function may assume that the type of the value is valid.
    def value_to_text(self, value):
        return repr(value)

    # Create a value from the current settings of the
    # HTML variables. This function must also check the validity
    # and may raise a MKUserError in case of invalid set variables.
    def from_html_vars(self, varprefix):
        return None

    # Check if a given value matches the
    # datatype of described by this class. This method will
    # be used by cmk -X on the command line in order to
    # validate main.mk (some happy day in future)
    def validate_datatype(self, value, varprefix):
        pass

    # Check if a given value is within the ranges that are
    # allowed for this type of value. This function should
    # assume that the data type is valid (either because it
    # has been returned by from_html_vars() or because it has
    # been checked with validate_datatype()).
    def validate_value(self, value, varprefix):
        pass

# A fixed non-editable value, e.g. to be use in "Alternative"
class FixedValue(ValueSpec):
    def __init__(self, value, **kwargs):
        ValueSpec.__init__(self, **kwargs)
        self._value = value
        self._totext = kwargs.get("totext")

    def canonical_value(self):
        return self._value

    def render_input(self, varprefix, value):
        html.write(self.value_to_text(value))

    def value_to_text(self, value):
        if self._totext != None:
            return self._totext
        else:
            return str(value)

    def from_html_vars(self, varprefix):
        return self._value

    def validate_datatype(self, value, varprefix):
        if not self._value == value:
            raise MKUserError(varprefix, _("Invalid value, must be '%r' but is '%r'" % (self._value, value)))

    def validate_value(self, value, varprefix):
        self.validate_datatype(value, varprefix)

# Time in seconds
class Age(ValueSpec):
    def __init__(self, **kwargs):
        ValueSpec.__init__(self, **kwargs)
        self._label    = kwargs.get("label")

    def canonical_value(self):
        return 0

    def render_input(self, varprefix, value):
        days,    rest    = divmod(value, 60*60*24)
        hours,   rest    = divmod(rest,   60*60)
        minutes, seconds = divmod(rest,      60)

        html.write("<div>")
        html.number_input(varprefix+'_days', days, 2)
        html.write(_("days"))
        html.number_input(varprefix+'_hour', hours, 2)
        html.write(_("hours"))
        html.number_input(varprefix+'_minutes', minutes, 2)
        html.write(_("min"))
        html.number_input(varprefix+'_seconds', seconds, 2)
        html.write(_("sec"))
        html.write("</div>")

    def from_html_vars(self, varprefix):
            return (saveint(html.var(varprefix+'_hour'))*3600) + (saveint(html.var(varprefix+'_minutes'))*60) + saveint(html.var(varprefix+'_seconds'))

    def value_to_text(self, value):
        days,    rest    = divmod(value, 60*60*24)
        hours,   rest    = divmod(rest,   60*60)
        minutes, seconds = divmod(rest,      60)
        return "%sd %sh %sm %ss" % (days, hours, minutes, seconds)

    def validate_datatype(self, value, varprefix):
        if type(value) != int:
            raise MKUserError(varprefix, _("The value has type %s, but must be of type int") % (type(value)))


# Editor for a single integer
class Integer(ValueSpec):
    def __init__(self, **kwargs):
        ValueSpec.__init__(self, **kwargs)
        self._size           = kwargs.get("size", 5)
        self._minvalue       = kwargs.get("minvalue")
        self._maxvalue       = kwargs.get("maxvalue")
        self._label          = kwargs.get("label")
        self._unit           = kwargs.get("unit", "")
        self._thousand_sep   = kwargs.get("thousand_sep")
        self._display_format = kwargs.get("display_format", "%d")
        
        if "size" not in kwargs and "maxvalue" in kwargs:
            self._size = 1 + int(math.log10(self._maxvalue))

    def canonical_value(self):
        if self._minvalue:
            return self._minvalue
        else:
            return 0

    def render_input(self, varprefix, value):
        if self._label:
            html.write(self._label)
            html.write("&nbsp;")
        html.number_input(varprefix, str(value), size = self._size)
        if self._unit:
            html.write("&nbsp;")
            html.write(self._unit)

    def from_html_vars(self, varprefix):
        try:
            return int(html.var(varprefix))
        except:
            raise MKUserError(varprefix,
                  _("The text <b><tt>%s</tt></b> is not a valid integer number." % html.var(varprefix)))

    def value_to_text(self, value):
        text = self._display_format % value
        if self._thousand_sep:
            sepped = ""
            rest = text
            while len(rest) > 3:
                sepped = self._thousand_sep + rest[-3:] + sepped
                rest = rest[:-3]
            sepped = rest + sepped
            text = sepped

        if self._unit:
            text += "&nbsp;" + self._unit
        return text

    def validate_datatype(self, value, varprefix):
        if type(value) != int:
            raise MKUserError(varprefix, _("The value has type %s, but must be of type int") % (type(value)))

    def validate_value(self, value, varprefix):
        if self._minvalue != None and value < self._minvalue:
            raise MKUserError(varprefix, _("%s is too low. The minimum allowed value is %s." % (
                                     value, self._minvalue)))
        if self._maxvalue != None and value > self._maxvalue:
            raise MKUserError(varprefix, _("%s is too high. The maximum allowed value is %s." % (
                                     value, self._maxvalue)))
# Filesize in Byte,Kbyte,Mbyte,Gigatbyte, Terrabyte
class Filesize(Integer):
    def __init__(self, **kwargs):
        Integer.__init__(self, **kwargs)
        self._names = [ 'Byte', 'KByte', 'MByte', 'GByte', 'TByte', ]


    def get_exponent(self, value):
        for exp, unit_name in list(enumerate(self._names))[::-1]: 
            if value == 0:
               return 0,0
            if value % (1024 ** exp) == 0:
                return exp, value / (1024 ** exp)

    def render_input(self, varprefix, value):
        exp, count = self.get_exponent(value) 
        html.number_input(varprefix + '_size', count, size = self._size)
        html.write("&nbsp;")
        html.select(varprefix + '_unit', enumerate(self._names), exp)

    def from_html_vars(self, varprefix):  
        try:
            return int(html.var(varprefix + '_size')) * (1024 ** int(html.var(varprefix + '_unit')))
        except:
            raise MKUserError(varprefix + '_size', _("Please enter a valid integer number"))

    def value_to_text(self, value):
        exp, count = self.get_exponent(value) 
        return "%s %s" %  (count, self._names[exp]) 


# Editor for a line of text
class TextAscii(ValueSpec):
    def __init__(self, **kwargs):
        ValueSpec.__init__(self, **kwargs)
        self._size     = kwargs.get("size", 30)
        self._strip    = kwargs.get("strip", True)
        self._allow_empty = kwargs.get("allow_empty", True)
        self._regex = kwargs.get("regex")
        self._regex_error = kwargs.get("regex_error",
                _("Your input odes not match the required format."))
        if type(self._regex) == str:
            self._regex = re.compile(self._regex)

    def canonical_value(self):
        return ""

    def render_input(self, varprefix, value):
        html.text_input(varprefix, str(value), size = self._size)

    def value_to_text(self, value):
        return value

    def from_html_vars(self, varprefix):
        value = html.var(varprefix, "")
        if self._strip:
            return value.strip()
        else:
            return value()

    def validate_datatype(self, value, varprefix):
        if type(value) != str:
            raise MKUserError(varprefix, _("The value must be of type str, but it has type %s") % type(value))

    def validate_value(self, value, varprefix):
        if not self._allow_empty and value.strip() == "":
            raise MKUserError(varprefix, _("An empty value is not allowed here."))
        if value and self._regex:
            if not self._regex.match(value):
                raise MKUserError(varprefix, self._regex_error)


class EmailAddress(TextAscii):
    def __init__(self, **kwargs):
        TextAscii.__init__(self, **kwargs)
        self._regex = re.compile('^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,4}$', re.I)

    def value_to_text(self, value):
        return '<a href="mailto:%s">%s</a>' % (value, value)

# Valuespec for a HTTP Url (not HTTPS), that
# automatically adds http:// to the value
class HTTPUrl(TextAscii):
    def __init__(self, **kwargs):
        TextAscii.__init__(self, **kwargs)
        self._target= kwargs.get("target")

    def validate_value(self, value, varprefix):
        TextAscii.validate_value(self, value, varprefix)
        if value:
            if not value.startswith("http://"):
                raise MKUserError(varprefix, _("The URL must begin with http://"))

    def from_html_vars(self, varprefix):
        value = TextAscii.from_html_vars(self, varprefix)
        if value:
            if not "://" in value:
                value = "http://" + value
        return value

    def value_to_text(self, url):
        if not url.startswith("http://"):
            url = "http://" + url
        try:
            parts = urlparse.urlparse(url)
            if parts.path in [ '', '/' ]:
                text = parts.netloc
            else:
                text = url[7:]
        except:
            text = url[7:]

        # Remove trailing / if the url does not contain
        # any path component
        return '<a %shref="%s">%s</a>' % (
            (self._target and 'target="%s" ' % self._target or ""),
            url, text)


class TextUnicode(TextAscii):
    def __init__(self, **kwargs):
        TextAscii.__init__(self, **kwargs)

    def render_input(self, varprefix, value):
        html.text_input(varprefix, value, size = self._size)

    def from_html_vars(self, varprefix):
        return html.var_utf8(varprefix, "").strip()

    def validate_datatype(self, value, varprefix):
        if type(value) not in [ str, unicode ]:
            raise MKUserError(varprefix, _("The value must be of type str or unicode, but it has type %s") % type(value))

class TextAreaUnicode(TextUnicode):
    def __init__(self, **kwargs):
        TextUnicode.__init__(self, **kwargs)
        self._cols = kwargs.get("cols", 60)
        self._rows = kwargs.get("rows", 20)

    def value_to_text(self, value):
        return "<pre class=ve_textarea>%s</pre>" % value

    def render_input(self, varprefix, value):
        html.text_area(varprefix, value, rows=self._rows, cols=self._cols)

    # Overridded because we do not want to strip() here and remove '\r'
    def from_html_vars(self, varprefix):
        return html.var_utf8(varprefix, "").replace('\r', '')

# A variant of TextAscii() that validates a path to a filename that
# lies in an existing directory.
class Filename(TextAscii):
    def __init__(self, **kwargs):
        TextAscii.__init__(self, **kwargs)
        if "default" in kwargs:
            self._default_path = kwargs["default"]
        else:
            self._default_path = "/tmp/foo"

    def canonical_value(self):
        return self._default_path

    def validate_value(self, value, varprefix):
        if len(value) == 0:
            raise MKUserError(varprefix, _("Please enter a filename."))

        if value[0] != "/":
            raise MKUserError(varprefix, _("Sorry, only absolute filenames are allowed. "
                                           "Your filename must begin with a slash."))
        if value[-1] == "/":
            raise MKUserError(varprefix, _("Your filename must not end with a slash."))

        dir = value.rsplit("/", 1)[0]
        if not os.path.isdir(dir):
            raise MKUserError(varprefix, _("The directory %s does not exist or is not a directory." % dir))

        # Write permissions to the file cannot be checked here since we run with Apache
        # permissions and the file might be created with Nagios permissions (on OMD this
        # is the same, but for others not)

class ListOfStrings(ValueSpec):
    def __init__(self, **kwargs):
        ValueSpec.__init__(self, **kwargs)
        self._valuespec = kwargs.get("valuespec", TextAscii())
        self._vertical = kwargs.get("orientation", "vertical") == "vertical"

    def render_input(self, vp, value):
        # Form already submitted?
        if html.has_var(vp + "_0"):
            value = self.from_html_vars(vp)
            # Remove variables from URL, so that they do not appear
            # in hidden_fields()
            nr = 0
            while html.has_var(vp + "_%d" % nr):
                html.del_var(vp + "_%d" % nr)
                nr += 1
        html.write('<table border=0 cellspacing=0 cellpadding=0 id="%s">' % vp)
        if not self._vertical:
            html.write('<tr>')
        
        for nr, s in enumerate(value + [""]):
            if self._vertical:
                html.write('<tr>')
            html.write('<td>')
            self._valuespec.render_input(vp + "_%d" % nr, s)
            html.write('</td>')
            if self._vertical:
                html.write('</tr>')

        if not self._vertical:
            html.write('</tr>')
        html.write('</table>')
        html.javascript("list_of_strings_init('%s');" % vp);

    def canonical_value(self):
        return []

    def value_to_text(self, value):
        return ", ".join([self._valuespec.value_to_text(v) for v in value])

    def from_html_vars(self, vp):
        value = []
        nr = 0
        while html.has_var(vp + "_%d" % nr):
            s = html.var(vp + "_%d" % nr).strip()
            if s:
                value.append(s)
            nr += 1
        return value

    def validate_datatype(self, value, vp):
        if type(value) != list:
            raise MKUserError(varprefix, _("Expected data type is "
            "list, but your type is %s." % type(value)))
        for nr, s in enumerate(value):
            self._valuespec.validate_datatype(s, vp + "_%d" % nr)

    def validate_value(self, value, vp):
        for nr, s in enumerate(value):
            self._valuespec.validate_value(s, vp + "_%d" % nr)

# Same but for floating point values
class Float(Integer):
    def __init__(self, **kwargs):
        Integer.__init__(self, **kwargs)

    def canonical_value(self):
        return float(Integer.canonical_value(self))

    def from_html_vars(self, varprefix):
        try:
            return float(html.var(varprefix))
        except:
            raise MKUserError(varprefix,
            _("The text <b><tt>%s</tt></b> is not a valid floating point number." % html.var(varprefix)))

    def validate_datatype(self, value, varprefix):
        if type(value) != float:
            raise MKUserError(varprefix, _("The value has type %s, but must be of type float") % (type(value)))


class Percentage(Float):
    def __init__(self, **kwargs):
        Integer.__init__(self, **kwargs)
        if "min_value" not in kwargs:
            self._minvalue = 0.0
        if "max_value" not in kwargs:
            self._maxvalue = 101.0
        if "unit" not in kwargs:
            self._unit = "%"

    def value_to_text(self, value):
        return "%.1f%%" % value


class Checkbox(ValueSpec):
    def __init__(self, **kwargs):
        ValueSpec.__init__(self, **kwargs)
        self._label = kwargs.get("label")

    def canonical_value(self):
        return False

    def render_input(self, varprefix, value):
        html.checkbox(varprefix, value, label = self._label)

    def value_to_text(self, value):
        return value and _("on") or _("off")

    def from_html_vars(self, varprefix):
        if html.var(varprefix):
            return True
        else:
            return False

    def validate_datatype(self, value, varprefix):
        if type(value) != bool:
            raise MKUserError(varprefix, _("The value has type %s, but must be either True or False") % (type(value)))

# A type-save dropdown choice. Parameters:
# help_separator: if you set this to a character, e.g. "-", then
# value_to_text will omit texts from the character up to the end of
# a choices name.
# Note: The list of choices may contain 2-tuples or 3-tuples.
# The format is (value, text {, icon} )
class DropdownChoice(ValueSpec):
    def __init__(self, **kwargs):
        ValueSpec.__init__(self, **kwargs)
        self._choices = kwargs["choices"]
        self._help_separator = kwargs.get("help_separator")

    def canonical_value(self):
        return self._choices[0][0]

    def render_input(self, varprefix, value):
        # Convert values from choices to keys
        defval = "0"
        options = []
        for n, entry in enumerate(self._choices):
            options.append((str(n),) + entry[1:])
            if entry[0] == value:
                defval = str(n)
        if len(options[0]) == 3:
            html.icon_select(varprefix, options, defval)
        else:
            html.select(varprefix, options, defval)

    def value_to_text(self, value):
        for entry in self._choices:
            val, title = entry[:2]
            if value == val:
                if self._help_separator:
                    return title.split(self._help_separator, 1)[0].strip()
                else:
                    return title

    def from_html_vars(self, varprefix):
        sel = html.var(varprefix)
        for n, entry in enumerate(self._choices):
            val = entry[0]
            if sel == str(n):
                return val
        return self._choices[0][0] # can only happen if user garbled URL

    def validate_datatype(self, value, varprefix):
        for val, title in self._choices:
            if val == value:
                return
        raise MKUserError(varprefix, _("Invalid value %s, must be in %s") %
            ", ".join([v for (v,t) in self._choices]))

# The same logic as the dropdown choice, but rendered
# as a group of radio buttons.
# columns == None or unset -> separate with "&nbsp;"
class RadioChoice(DropdownChoice):
    def __init__(self, **kwargs):
        DropdownChoice.__init__(self, **kwargs)
        self._columns = kwargs.get("columns")

    def render_input(self, varprefix, value):
        html.begin_radio_group()
        if self._columns != None:
            html.write("<table class=radiochoice>")
            html.write("<tr>")

        for n, entry in enumerate(self._choices):
            if self._columns != None:
                html.write("<td>")
            if len(entry) > 2: # icon!
                label = '<img class=icon align=absmiddle src="images/icon_%s.png" title="%s">' % \
                        ( entry[2], entry[1].encode("utf-8"))
            else:
                label = entry[1]
            html.radiobutton(varprefix, str(n), value == entry[0], label)
            if self._columns != None:
                html.write("</td>")
                if (n+1) % self._columns == 0 and (n+1) < len(self._choices)-1:
                    html.write("<tr></tr>") 
            else:
                html.write("&nbsp;")
        if self._columns != None:
            mod = len(self._choices) % self._columns
            if mod:
                html.write("<td></td>" * (self._columns - mod - 1))
            html.write("</tr></table>")
        html.end_radio_group()



# A list of checkboxes representing a list of values
class ListChoice(ValueSpec):
    def __init__(self, **kwargs):
        ValueSpec.__init__(self, **kwargs)
        self._choices = kwargs.get("choices")
        self._columns = kwargs.get("columns", 1)
        self._loaded_at = None
        self._render_function = kwargs.get("render_function", 
                  lambda id, val: val)

    # In case of overloaded functions with dynamic elements
    def load_elements(self):
        if self._choices:
            self._elements = self._choices
            return

        if self._loaded_at != id(html):
            self._elements = self.get_elements()
            self._loaded_at = id(html) # unique for each query!

    def canonical_value(self):
        return []

    def render_input(self, varprefix, value):
        self.load_elements()
        html.write("<table>")
        for nr, (key, title) in enumerate(self._elements):
            if nr % self._columns == 0:
                if nr > 0:
                    html.write("</tr>")
                html.write("<tr>")
            html.write("<td>")
            html.checkbox("%s_%d" % (varprefix, nr), key in value)
            html.write("&nbsp;%s</td>\n" % title)
        html.write("</tr></table>")

    def value_to_text(self, value):
        self.load_elements()
        d = dict(self._elements)
        return ", ".join([ self._render_function(v, d.get(v,v)) for v in value ])

    def from_html_vars(self, varprefix):
        self.load_elements()
        value = []

        for nr, (key, title) in enumerate(self._elements):
            if html.get_checkbox("%s_%d" % (varprefix, nr)):
                value.append(key)
        return value

    def validate_datatype(self, value, varprefix):
        self.load_elements()
        if type(value) != list:
            raise MKUserError(varprefix, _("The datatype must be list, but is %s") % type(value))
        d = dict(self._elements)
        for v in value:
            if v not in d:
                raise MKUserError(varprefix, _("%s is not an allowed value") % v)



# A type-save dropdown choice with one extra field that
# opens a further value spec for entering an alternative
# Value.
class OptionalDropdownChoice(ValueSpec):
    def __init__(self, **kwargs):
        ValueSpec.__init__(self, **kwargs)
        self._choices = kwargs["choices"]
        self._explicit = kwargs["explicit"]
        self._otherlabel = kwargs.get("otherlabel", _("Other"))

    def canonical_value(self):
        return self._explicit.canonical_value()

    def value_is_explicit(self, value):
        return value not in [ c[0] for c in self._choices ]

    def render_input(self, varprefix, value):
        defval = "other"
        options = []
        for n, (val, title) in enumerate(self._choices):
            options.append((str(n), title))
            if val == value:
                defval = str(n)
        options.append(("other", self._otherlabel))
        html.select(varprefix, options, defval, # attrs={"style":"float:left;"},
                    onchange="valuespec_toggle_dropdown(this, '%s_ex');" % varprefix )
        if html.form_submitted():
            div_is_open = html.var(varprefix) == "other"
        else:
            div_is_open = self.value_is_explicit(value)

        html.write('<span id="%s_ex" style="white-space: nowrap; %s">' % (
            varprefix, not div_is_open and "display: none;" or ""))
        html.write("&nbsp;")
        self._explicit.render_input(varprefix + "_ex", value)
        html.write("</span>")

    def value_to_text(self, value):
        for val, title in self._choices:
            if val == value:
                return title
        return self._explicit.value_to_text(value)

    def from_html_vars(self, varprefix):
        sel = html.var(varprefix)
        if sel == "other":
            return self._explicit.from_html_vars(varprefix + "_ex")

        for n, (val, title) in enumerate(self._choices):
            if sel == str(n):
                return val
        return self._choices[0][0] # can only happen if user garbled URL

    def validate_value(self, value, varprefix):
        if self.value_is_explicit(value):
            self._explicit.validate_value(value, varprefix)
        # else valid_datatype already has made the job

    def validate_datatype(self, value, varprefix):
        for val, title in self._choices:
            if val == value:
                return
        self._explicit.validate_datatype(self, value, varprefix + "_ex")


# Input of date with optimization for nearby dates
# in the future. Useful for example for alarms. The 
# date is represented by a UNIX timestamp where the
# seconds are silently ignored.
def round_date(t):
    return int(t) / seconds_per_day * seconds_per_day

def today():
    return round_date(time.time())

seconds_per_day = 86400

weekdays = {
   0: _("Monday"),
   1: _("Tuesday"),
   2: _("Wednesday"),
   3: _("Thursday"),
   4: _("Friday"),
   5: _("Saturday"),
   6: _("Sunday"),
}

class RelativeDate(OptionalDropdownChoice):
    def __init__(self, **kwargs):
        ValueSpec.__init__(self, **kwargs)
        self._choices = [
          (0, _("today")),
          (1, _("tomorrow"))]
        weekday = time.localtime(today()).tm_wday
        for w in range(2, 7):
            wd = (weekday + w) % 7
            self._choices.append((w, weekdays[wd]))
        for w in range(0, 7):
            wd = (weekday + w) % 7
            if w < 2:
                title = _(" next week")
            else:
                title = _(" in %d days") % (w + 7)
            self._choices.append((w + 7, weekdays[wd] + title))
        self._explicit = Integer()
        self._otherlabel = _("in ... days")
        if "default_days" in kwargs:
            self._default_value = kwargs["default_days"] * seconds_per_day + today()
        else:
            self._default_value = today()

    def canonical_value(self):
        return self._default_value

    def render_input(self, varprefix, value):
        reldays = (round_date(value) - today()) / seconds_per_day
        OptionalDropdownChoice.render_input(self, varprefix, reldays)

    def value_to_text(self, value):
        reldays = (round_date(value) - today()) / seconds_per_day
        if reldays == -1:
            return _("yesterday")
        elif reldays == -2:
            return _("two days ago")
        elif reldays < 0:
            return _("%d days ago") % -reldays
        elif reldays < len(self._choices):
            return self._choices[reldays][1]
        else:
            return _("in %d days") % reldays

    def from_html_vars(self, varprefix):
        reldays = OptionalDropdownChoice.from_html_vars(self, varprefix)
        return today() + reldays * seconds_per_day

    def validate_datatype(self, value, varprefix):
        if type(value) not in [ float, int ]:
            raise MKUserError(varprefix, _("Date must be a number value"))

    def validate_value(self, value, varprefix):
        pass




# Make a configuration value optional, i.e. it may be None.
# The user has a checkbox for activating the option. Example:
# debug_log: it is either None or set to a filename.
class Optional(ValueSpec):
    def __init__(self, valuespec, **kwargs):
        ValueSpec.__init__(self, **kwargs)
        self._valuespec = valuespec
        self._label = kwargs.get("label")
        self._negate = kwargs.get("negate", False)
        self._none_label = kwargs.get("none_label", _("(unset)"))
        self._sameline = kwargs.get("sameline", False)

    def canonical_value(self):
        return None

    def render_input(self, varprefix, value):
        div_id = "option_" + varprefix
        if html.has_var(varprefix + "_use"):
            checked = html.get_checkbox(varprefix + "_use")
        else:
            checked = self._negate != (value != None)
        html.write("<span>")

        if self._label:
            label = self._label
        elif self.title():
            label = _(self.title())
        elif self._negate:
            label = _(" Ignore this option")
        else:
            label = _(" Activate this option")

        html.checkbox(varprefix + "_use" , checked,
                      onclick="valuespec_toggle_option(this, %r, %r)" %
                         (div_id, self._negate and 1 or 0),
                      label = label)

        if self._sameline:
            html.write("&nbsp;")
        else:
            html.write("<br><br>")
        html.write("</span>")
        html.write('<span id="%s" display: %s">' % (
                div_id, checked == self._negate and "none" or ""))
        if value == None:
            value = self._valuespec.default_value()
        if self._valuespec.title():
            html.write(self._valuespec.title() + " ")
        self._valuespec.render_input(varprefix + "_value", value)
        html.write('</span>\n')

    def value_to_text(self, value):
        if value == None:
            return self._none_label
        else:
            return self._valuespec.value_to_text(value)

    def from_html_vars(self, varprefix):
        if html.get_checkbox(varprefix + "_use") != self._negate:
            return self._valuespec.from_html_vars(varprefix + "_value")
        else:
            return None

    def validate_datatype(self, value, varprefix):
        if value != None:
            self._valuespec.validate_datatype(value, varprefix + "_value")

    def validate_value(self, value, varprefix):
        if value != None:
            self._valuespec.validate_value(value, varprefix + "_value")

# Handle case when there are several possible allowed formats
# for the value (e.g. strings, 4-tuple or 6-tuple like in SNMP-Communities)
# The different alternatives must have different data types that can
# be distinguished with validate_datatype.
class Alternative(ValueSpec):
    def __init__(self, **kwargs):
        ValueSpec.__init__(self, **kwargs)
        self._elements = kwargs["elements"]

    # Return the alternative (i.e. valuespec)
    # that matches the datatype of a given value. We assume
    # that always one matches. No error handling here.
    def matching_alternative(self, value):
        for vs in self._elements:
            try:
                vs.validate_datatype(value, "")
                return vs
            except:
                pass

    def render_input(self, varprefix, value):
        mvs = self.matching_alternative(value)
        for nr, vs in enumerate(self._elements):
            if html.has_var(varprefix + "_use"):
                checked = html.var(varprefix + "_use") == str(nr)
            else:
                checked = vs == mvs

            title = vs.title()
            html.radiobutton(varprefix + "_use", str(nr), checked, title)
            if title:
                html.write("<ul>")
            if vs == mvs:
                val = value
            else:
                val = vs.canonical_value()
            vs.render_input(varprefix + "_%d" % nr, val)
            if title:
                html.write("</ul>\n")

    def set_focus(self, varprefix):
        # TODO: Set focus to currently active option
        pass

    def canonical_value(self):
        return self._elements[0].canonical_value()

    def value_to_text(self, value):
        vs = self.matching_alternative(value)
        if vs:
            return vs.value_to_text(value)
        else:
            return _("invalid:") + " " + str(value)

    def from_html_vars(self, varprefix):
        nr = int(html.var(varprefix + "_use"))
        vs = self._elements[nr]
        return vs.from_html_vars(varprefix + "_%d" % nr)

    def validate_datatype(self, value, varprefix):
        for vs in self._elements:
            try:
                vs.validate_datatype(value, "")
                return
            except:
                pass
        raise MKUserError(varprefix,
            _("The data type of the value does not match any of the "
              "allowed alternatives."))

    def validate_value(self, value, varprefix):
        vs = self.matching_alternative(value)
        for nr, v in enumerate(self._elements):
            if vs == v:
                vs.validate_value(value, varprefix + "_%d" % nr)


# Edit a n-tuple (with fixed size) of values
class Tuple(ValueSpec):
    def __init__(self, **kwargs):
        ValueSpec.__init__(self, **kwargs)
        self._elements = kwargs["elements"]
        self._show_titles = kwargs.get("show_titles", True)

    def canonical_value(self):
        return tuple([x.canonical_value() for x in self._elements])

    def render_input(self, varprefix, value):
        html.write('<table class="valuespec_tuple">')
        for no, (element, val) in enumerate(zip(self._elements, value)):
            vp = varprefix + "_" + str(no)
            if element.help():
                help = "<br><i>%s</i>" % element.help()
            else:
                help = ""
            html.write("<tr>")
            if self._show_titles:
                title = element.title()[0].upper() + element.title()[1:]
                html.write("<td class=left>%s:%s</td>" % (title, help))
            html.write("<td class=right>")
            element.render_input(vp, val)
            html.write("</td></tr>")
        html.write("</table>")

    def set_focus(self, varprefix):
        self._elements[0].set_focus(varprefix + "_0")

    def value_to_text(self, value):
        return "" + ", ".join([ element.value_to_text(val)
                         for (element, val)
                         in zip(self._elements, value)]) + ""

    def from_html_vars(self, varprefix):
        value = []
        for no, element in enumerate(self._elements):
            vp = varprefix + "_" + str(no)
            value.append(element.from_html_vars(vp))
        return tuple(value)

    def validate_value(self, value, varprefix):
        for no, (element, val) in enumerate(zip(self._elements, value)):
            vp = varprefix + "_" + str(no)
            element.validate_value(val, vp)

    def validate_datatype(self, value, varprefix):
        if type(value) != tuple:
            raise MKUserError(varprefix,
            _("The datatype must be a tuple, but is %s") % type(value))
        if len(value) != len(self._elements):
            raise MKUserError(varprefix,
            _("The number of elements in the tuple must be exactly %d.") % len(self._elements))

        for no, (element, val) in enumerate(zip(self._elements, value)):
            vp = varprefix + "_" + str(no)
            element.validate_datatype(val, vp)

class Dictionary(ValueSpec):
    def __init__(self, **kwargs):
        ValueSpec.__init__(self, **kwargs)
        self._elements = kwargs["elements"]
        self._optional_keys = kwargs.get("optional_keys", True)
        self._columns = kwargs.get("columns", 1) # possible: 1 or 2

    def render_input(self, varprefix, value):
        html.write("<table class=dictionary>")
        for param, vs in self._elements:
            html.write("<tr><td class=dictleft>")
            vp = varprefix + "_" + param
            div_id = vp
            if self._optional_keys:
                visible = html.get_checkbox(vp + "_USE")
                if visible == None:
                    visible = param in value
                html.checkbox(vp + "_USE", param in value,
                              onclick="valuespec_toggle_option(this, %r)" % div_id)
            else:
                visible = True

            html.write(" %s" % vs.title())
            if self._columns == 2:
                html.write(':')
                if vs.help():
                    html.write("<ul class=help>%s</ul>" % vs.help())
                html.write('</td><td class=dictright>')
            else:
                html.write("<br>")

            html.write('<div class=dictelement id="%s" style="display: %s">' % (
                div_id, not visible and "none" or ""))
            if self._columns == 1 and vs.help():
                html.write("<ul class=help>%s</ul>" % vs.help())
            vs.render_input(vp, value.get(param, vs.canonical_value()))
            html.write("</div></td></tr>")
        html.write("</table>")

    def set_focus(self, varprefix):
        self._elements[0][1].set_focus(varprefix + self._elements[0][0])

    def canonical_value(self):
        if self._optional_keys:
            return {}
        else:
            return dict([
                (name, vs.canonical_value()) for (name, vs) in self._elements])

    def value_to_text(self, value):
        parts = []
        for param, vs in self._elements:
            if param in value:
                parts.append("%s: %s" % (vs.title(), vs.value_to_text(value[param])))
        return ", ".join(parts)

    def from_html_vars(self, varprefix):
        value = {}
        for param, vs in self._elements:
            vp = varprefix + "_" + param
            if not self._optional_keys or html.get_checkbox(vp + "_USE"):
                value[param] = vs.from_html_vars(vp)
        return value

    def validate_datatype(self, value, varprefix):
        if type(value) != dict:
            raise MKUserError(varprefix, _("The type must be a dictionary, but it is a %s") % type(value))

        for param, vs in self._elements:
            if param in value:
                vp = varprefix + "_" + param
                vs.validate_datatype(value[param], vp)
            elif not self._optional_keys:
                raise MKUserError(varprefix, _("The entry %s is missing") % vp.title())

        # Check for exceeding keys
        allowed_keys = [ p for (p,v) in self._elements ]
        for param in value.keys():
            if param not in allowed_keys:
                raise MKUserError(varprefix, _("Undefined key '%s' in the dictionary. Allowed are %s.") %
                        ", ".join(allowed_keys))

    def validate_value(self, value, varprefix):
        for param, vs in self._elements:
            if param in value:
                vp = varprefix + "_" + param
                vs.validate_value(value[param], vp)
            elif not self._optional_keys:
                raise MKUserError(varprefix, _("The entry %s is missing") % vp.title())


# Base class for selection of a Nagios element out
# of a given list that must be loaded from a file.
# Examples: GroupSelection, TimeperiodSelection. Child
# class must define a function get_elements() that
# returns a dictionary from element keys to element
# titles.
class ElementSelection(ValueSpec):
    def __init__(self, **kwargs):
        ValueSpec.__init__(self, **kwargs)
        self._loaded_at = None

    def load_elements(self):
        if self._loaded_at != id(html):
            self._elements = self.get_elements()
            self._loaded_at = id(html) # unique for each query!

    def canonical_value(self):
        self.load_elements()
        if len(self._elements) > 0:
            return self._elements.keys()[0]
        else:
            raise MKUserError(None,
              _("There are not defined any elements for this selection yet."))

    def render_input(self, varprefix, value):
        self.load_elements()
        if len(self._elements) == 0:
            html.write(_("There are not defined any elements for this selection yet."))
        else:
            html.sorted_select(varprefix, self._elements.items(), value)

    def value_to_text(self, value):
        self.load_elements()
        return self._elements.get(value, value)

    def from_html_vars(self, varprefix):
        return html.var(varprefix)

    def validate_value(self, value, varprefix):
        self.load_elements()
        if len(self._elements) == 0:
            raise MKUserError(varprefix,
              _("You cannot save this rule. There are not defined any elements for this selection yet."))
        if value not in self._elements:
            raise MKUserError(varprefix, _("%s is not an existing element in this selection.") % (value,))

    def validate_datatype(self, value, varprefix):
        if type(value) != str:
            raise MKUserError(varprefix, _("The datatype must be str (string), but is %s") % type(value))


class AutoTimestamp(FixedValue):
    def __init__(self, **kwargs):
        ValueSpec.__init__(self, **kwargs)
        self._value = time.time()

    def value_to_text(self, value):
        return time.strftime("%F %T", time.localtime(value))
