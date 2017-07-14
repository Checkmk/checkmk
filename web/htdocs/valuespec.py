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

# FIXME: Cleanups
# - Change all class to be "new style" classes
# - Consolidate ListChoice and DualListChoice to use the same class
#   and rename to better name
# - Consolidate RadioChoice and DropdownChoice to use same class
#   and rename to better name
# - Checkbox
#   -> rename to Boolean
#   -> Add alternative rendering "dropdown"

import math, os, time, re, sre_constants, urlparse, forms, tempfile
import base64
import hashlib
import socket
from lib import *
import cmk.defines as defines
from Crypto.PublicKey import RSA

try:
    import simplejson as json
except ImportError:
    import json

def type_name(v):
    try:
        return type(v).__name__
    except:
        return html.attrencode(type(v))

# Abstract base class of all value declaration classes.
class ValueSpec(object):
    def __init__(self, **kwargs):
        super(ValueSpec, self).__init__()
        self._title         = kwargs.get("title")
        self._help          = kwargs.get("help")
        if "default_value" in kwargs:
            self._default_value = kwargs.get("default_value")
        self._validate      = kwargs.get("validate")

        # debug display allows to view the class name of a certain element in the gui.
        # If set False, then the corresponding div is present, but hidden.
        self.debug_display = False


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
    # fulfills also data validation.
    def canonical_value(self):
        return None

    # Return a default value for this variable. This
    # is optional and only used in the value editor
    # for same cases where the default value is known.
    def default_value(self):
        try:
            if type(self._default_value) == type(lambda:True):
                return self._default_value()
            else:
                return self._default_value
        except:
            return self.canonical_value()

    # Creates a text-representation of the value that can be
    # used in tables and other contextes. It is to be read
    # by the user and need not to be parsable.
    # The function may assume that the type of the value is valid.
    #
    # In the current implementation this function is only used to
    # render the object for html code. So it is allowed to add
    # html code for better layout in the GUI.
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
        self.custom_validate(value, varprefix)

    # Needed for implementation of customer validation
    # functions that are configured by the user argument
    # validate = .... Problem: this function must be
    # called by *every* validate_value() function in all
    # subclasses - explicitely.
    def custom_validate(self, value, varprefix):
        if self._validate:
            self._validate(value, varprefix)


    def classtype_info(self):
        superclass = " ".join(base.__name__ for base in self.__class__.__bases__)
        if not self.debug_display:
            return
        html.div("Check_MK-Type: %s %s" % (superclass, type(self).__name__), class_="legend")




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
        elif type(value) == unicode:
            return value
        else:
            return str(value)

    def from_html_vars(self, varprefix):
        return self._value

    def validate_datatype(self, value, varprefix):
        if not self._value == value:
            raise MKUserError(varprefix, _("Invalid value, must be '%r' but is '%r'") %
                                                                    (self._value, value))

    def validate_value(self, value, varprefix):
        self.validate_datatype(value, varprefix)
        ValueSpec.custom_validate(self, value, varprefix)

# Time in seconds
class Age(ValueSpec):
    def __init__(self, **kwargs):
        ValueSpec.__init__(self, **kwargs)
        self._label    = kwargs.get("label")
        self._minvalue = kwargs.get("minvalue")
        self._display  = kwargs.get("display", ["days", "hours", "minutes", "seconds"])

    def canonical_value(self):
        if self._minvalue:
            return self._minvalue
        else:
            return 0

    def render_input(self, varprefix, value):
        self.classtype_info()
        days,    rest    = divmod(value, 60*60*24)
        hours,   rest    = divmod(rest,   60*60)
        minutes, seconds = divmod(rest,      60)

        html.open_div()
        if self._label:
            html.write(self._label + " ")

        takeover = 0
        first = True
        for uid, title, value, tkovr_fac in [ ("days",    _("days"),  days,    24),
                                              ("hours",   _("hours"), hours,   60),
                                              ("minutes", _("mins"),  minutes, 60),
                                              ("seconds", _("secs"),  seconds, 60) ]:
            if uid in self._display:
                value += takeover
                takeover = 0
                html.number_input(varprefix + "_" + uid, value, 3 if first else 2)
                html.write(" %s " % title)
                first = False
            else:
                takeover = (takeover + value) * tkovr_fac
        html.close_div()

    def from_html_vars(self, varprefix):
        # TODO: Validate for correct numbers!
        return (
               saveint(html.var(varprefix + '_days',    0)) * 3600 * 24
             + saveint(html.var(varprefix + '_hours',   0)) * 3600
             + saveint(html.var(varprefix + '_minutes', 0)) * 60
             + saveint(html.var(varprefix + '_seconds', 0))
        )

    def value_to_text(self, value):
        days,    rest    = divmod(value, 60*60*24)
        hours,   rest    = divmod(rest,   60*60)
        minutes, seconds = divmod(rest,      60)
        parts = []
        for title, count in [
            ( _("days"), days, ),
            ( _("hours"), hours, ),
            ( _("minutes"), minutes, ),
            ( _("seconds"), seconds, )]:
            if count:
                parts.append("%d %s" % (count, title))

        if parts:
            return " ".join(parts)
        else:
            return _("no time")


    def validate_datatype(self, value, varprefix):
        if type(value) != int:
            raise MKUserError(varprefix, _("The value %r has type %s, but must be of type int") %
                        (value, type_name(value)))

    def validate_value(self, value, varprefix):
        if self._minvalue != None and value < self._minvalue:
            raise MKUserError(varprefix, _("%s is too low. The minimum allowed value is %s.") % (
                                     value, self._minvalue))

# Editor for a single integer
class Integer(ValueSpec):
    def __init__(self, **kwargs):
        ValueSpec.__init__(self, **kwargs)
        self._size           = kwargs.get("size", 5)
        # TODO: inconsistency with default_value. All should be named with underscore
        self._minvalue       = kwargs.get("minvalue")
        self._maxvalue       = kwargs.get("maxvalue")
        self._label          = kwargs.get("label")
        self._unit           = kwargs.get("unit", "")
        self._thousand_sep   = kwargs.get("thousand_sep")
        self._display_format = kwargs.get("display_format", "%d")
        self._align          = kwargs.get("align", "left")

        if "size" not in kwargs and "maxvalue" in kwargs and kwargs["maxvalue"] != None:
            self._size = 1 + int(math.log10(self._maxvalue)) + \
               (3 if type(self._maxvalue) == float else 0)

    def canonical_value(self):
        if self._minvalue:
            return self._minvalue
        else:
            return 0

    def render_input(self, varprefix, value, convfunc = saveint):
        self.classtype_info()
        if self._label:
            html.write(self._label)
            html.nbsp()
        if self._align == "right":
            style = "text-align: right;"
        else:
            style = ""
        if value == "": # This is needed for ListOfIntegers
            html.text_input(varprefix, "", "number", size = self._size, style = style)
        else:
            html.number_input(varprefix, self._display_format % convfunc(value), size = self._size, style = style)
        if self._unit:
            html.nbsp()
            html.write(self._unit)

    def from_html_vars(self, varprefix):
        try:
            return int(html.var(varprefix))
        except:
            raise MKUserError(varprefix,
                  _("The text <b><tt>%s</tt></b> is not a valid integer number.") % html.var(varprefix))

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
        if type(value) not in [ int, long ]:
            raise MKUserError(varprefix, _("The value %r has the wrong type %s, but must be of type int")
            % (value, type_name(value)))

    def validate_value(self, value, varprefix):
        if self._minvalue != None and value < self._minvalue:
            raise MKUserError(varprefix, _("%s is too low. The minimum allowed value is %s.") % (
                                     value, self._minvalue))
        if self._maxvalue != None and value > self._maxvalue:
            raise MKUserError(varprefix, _("%s is too high. The maximum allowed value is %s.") % (
                                     value, self._maxvalue))
        ValueSpec.custom_validate(self, value, varprefix)

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
        self.classtype_info()
        exp, count = self.get_exponent(value)
        html.number_input(varprefix + '_size', count, size = self._size)
        html.nbsp()
        choices = [ (str(nr), name) for (nr, name) in enumerate(self._names) ]
        html.select(varprefix + '_unit', choices, str(exp))

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
        super(TextAscii, self).__init__(**kwargs)
        self._label         = kwargs.get("label")
        self._size          = kwargs.get("size", 25) # also possible: "max"
        self._try_max_width = kwargs.get("try_max_width", False) # If set, uses calc(100%-10px)
        self._cssclass      = kwargs.get("cssclass", "text")
        self._strip         = kwargs.get("strip", True)
        self._attrencode    = kwargs.get("attrencode", True)
        self._allow_empty   = kwargs.get("allow_empty", _("none"))
        self._empty_text    = kwargs.get("empty_text", "")
        self._read_only     = kwargs.get("read_only")
        self._none_is_empty = kwargs.get("none_is_empty", False)
        self._forbidden_chars = kwargs.get("forbidden_chars", "")
        self._regex         = kwargs.get("regex")
        self._regex_error   = kwargs.get("regex_error",
            _("Your input does not match the required format."))
        self._minlen        = kwargs.get('minlen', None)
        if type(self._regex) == str:
            self._regex = re.compile(self._regex)
        self._prefix_buttons = kwargs.get("prefix_buttons", [])
        self._onkeyup        = kwargs.get("onkeyup")
        self._autocomplete   = kwargs.get("autocomplete", True)

    def canonical_value(self):
        return ""

    def render_input(self, varprefix, value, hidden=False):
        self.classtype_info()
        if value == None:
            value = ""
        else:
            value = "%s" % value

        if self._label:
            html.write(self._label)
            html.nbsp()

        if self._prefix_buttons:
            html.open_div(style="white-space: nowrap;")

        if hidden:
            type_ = "password"
        else:
            type_ = "text"

        attrs = {}
        if self._onkeyup:
            attrs["onkeyup"] = self._onkeyup

        html.text_input(varprefix, value,
            size=self._size,
            try_max_width=self._try_max_width,
            read_only=self._read_only,
            cssclass=self._cssclass,
            type=type_,
            attrs=attrs,
            autocomplete="off" if not self._autocomplete else None,
        )
        if self._prefix_buttons:
            self.render_buttons()
            html.close_div()

    def render_buttons(self):
        html.nbsp()
        for icon, textfunc, help in self._prefix_buttons:
            try:
                text = textfunc()
            except:
                text = textfunc
            html.icon_button("#", help, icon, onclick="vs_textascii_button(this, '%s', 'prefix');" % text)


    def value_to_text(self, value):
        if not value:
            return self._empty_text
        else:
            if self._attrencode:
                return html.attrencode(value)
            else:
                return value

    def from_html_vars(self, varprefix):
        value = html.var(varprefix, "")
        if self._strip:
            value = value.strip()
        if self._none_is_empty and not value:
            return None
        else:
            return value

    def validate_datatype(self, value, varprefix):
        if self._none_is_empty and value == None:
            return

        if type(value) != str:
            raise MKUserError(varprefix, _("The value must be of type str, but it has type %s") %
                                                                    type_name(value))

    def validate_value(self, value, varprefix):
        try:
            unicode(value)
        except:
            raise MKUserError(varprefix, _("Non-ASCII characters are not allowed here."))
        if self._forbidden_chars:
            for c in self._forbidden_chars:
                if c in value:
                    raise MKUserError(varprefix, _("The character <tt>%s</tt> is not allowed here.") % c)
        if self._none_is_empty and value == "":
            raise MKUserError(varprefix, _("An empty value must be represented with None here."))
        if not self._allow_empty and value.strip() == "":
            raise MKUserError(varprefix, _("An empty value is not allowed here."))
        if value and self._regex:
            if not self._regex.match(value):
                raise MKUserError(varprefix, self._regex_error)

        if self._minlen != None and len(value) < self._minlen:
            raise MKUserError(varprefix, _("You need to provide at least %d characters.") % self._minlen)

        ValueSpec.custom_validate(self, value, varprefix)


class TextUnicode(TextAscii):
    def __init__(self, **kwargs):
        TextAscii.__init__(self, **kwargs)

    def from_html_vars(self, varprefix):
        return html.get_unicode_input(varprefix, "").strip()

    def validate_datatype(self, value, varprefix):
        if type(value) not in [ str, unicode ]:
            raise MKUserError(varprefix, _("The value must be of type str or unicode, but it has type %s") %
                                                                                type_name(value))


# Internal ID as used in many places (for contact names, group name,
# an so on)
class ID(TextAscii):
    def __init__(self, **kwargs):
        TextAscii.__init__(self, **kwargs)
        self._regex = re.compile('^[a-zA-Z_][-a-zA-Z0-9_]*$')
        self._regex_error = _("An identifier must only consist of letters, digits, dash and "
                              "underscore and it must start with a letter or underscore.")


# Same as the ID class, but allowing unicode objects
class UnicodeID(TextUnicode):
    def __init__(self, **kwargs):
        TextUnicode.__init__(self, **kwargs)
        self._regex = re.compile(r'^[\w][-\w0-9_]*$', re.UNICODE)
        self._regex_error = _("An identifier must only consist of letters, digits, dash and "
                              "underscore and it must start with a letter or underscore.")


class UserID(TextUnicode):
    def __init__(self, **kwargs):
        TextUnicode.__init__(self, **kwargs)
        self._regex = re.compile(r'^[\w][-\w0-9_\.@]*$', re.UNICODE)
        self._regex_error = _("An identifier must only consist of letters, digits, dash, dot, "
                              "at and underscore. But it must start with a letter or underscore.")


class RegExp(TextAscii):
    infix    = "infix"
    prefix   = "prefix"
    complete = "complete"

    def __init__(self, mode, **kwargs):
        self._mode           = mode
        self._case_sensitive = kwargs.get("case_sensitive", True)

        TextAscii.__init__(self,
            attrencode = True,
            cssclass = self._css_classes(),
            **kwargs
        )

        self._mingroups = kwargs.get("mingroups", 0)
        self._maxgroups = kwargs.get("maxgroups")


    def help(self):
        help_text = []

        default_help_text = TextAscii.help(self)
        if default_help_text != None:
            help_text.append(default_help_text + "<br><br>")

        help_text.append(_("The text entered here is handled as a regular expression pattern."))

        if self._mode == RegExp.infix:
            help_text.append(_("The pattern is applied as infix search. Add a leading <tt>^</tt> "
                               "to make it match from the beginning and/or a tailing <tt>$</tt> "
                               "to match till the end of the text."))
        elif self._mode == RegExp.prefix:
            help_text.append(_("The pattern is matched from the beginning. Add a tailing "
                               "<tt>$</tt> to change it to a whole text match."))
        elif self._mode == RegExp.complete:
            help_text.append(_("The pattern is matching the whole text. You can add <tt>.*</tt> "
                               "in front or at the end of your pattern to make it either a prefix "
                               "or infix search."))

        if self._case_sensitive == True:
            help_text.append(_("The match is performed case sensitive."))
        elif self._case_sensitive == False:
            help_text.append(_("The match is performed case insensitive."))

        help_text.append(
            _("Please note that any backslashes need to be escaped using a backslash, "
              "for example you need to insert <tt>C:\\\\windows\\\\</tt> if you want to match "
              "<tt>c:\windows\</tt>.")
        )

        return " ".join(help_text)


    def _css_classes(self):
        classes = [ "text", "regexp" ]

        if self._case_sensitive == True:
            classes.append("case_sensitive")
        elif self._case_sensitive == False:
            classes.append("case_insensitive")

        if self._mode != None:
            classes.append(self._mode)

        return " ".join(classes)


    def validate_value(self, value, varprefix):
        TextAscii.validate_value(self, value, varprefix)

        # Check if the string is a valid regex
        try:
            compiled = re.compile(value)
        except sre_constants.error, e:
            raise MKUserError(varprefix, _('Invalid regular expression: %s') % e)

        if compiled.groups < self._mingroups:
            raise MKUserError(varprefix, _("Your regular expression containes <b>%d</b> groups. "
                 "You need at least <b>%d</b> groups.") % (compiled.groups, self._mingroups))
        if self._maxgroups != None and compiled.groups > self._maxgroups:
            raise MKUserError(varprefix, _("Your regular expression containes <b>%d</b> groups. "
                 "It must have at most <b>%d</b> groups.") % (compiled.groups, self._maxgroups))

        ValueSpec.custom_validate(self, value, varprefix)


class RegExpUnicode(TextUnicode, RegExp):
    def __init__(self, **kwargs):
        TextUnicode.__init__(self, attrencode = True, **kwargs)
        RegExp.__init__(self, **kwargs)

    def validate_value(self, value, varprefix):
        TextUnicode.validate_value(self, value, varprefix)
        RegExp.validate_value(self, value, varprefix)
        ValueSpec.custom_validate(self, value, varprefix)


class EmailAddress(TextAscii):
    def __init__(self, **kwargs):
        kwargs.setdefault("size", 40)
        TextAscii.__init__(self, **kwargs)
        # The "new" top level domains are very unlimited in length. Theoretically they can be
        # up to 63 chars long. But currently the longest is 24 characters. Check this out with:
        # wget -qO - http://data.iana.org/TLD/tlds-alpha-by-domain.txt | tail -n+2 | wc -L
        self._regex = re.compile('^[A-Z0-9._%+-]+@(localhost|[A-Z0-9.-]+\.[A-Z]{2,24})$', re.I)
        self._make_clickable = kwargs.get("make_clickable", False)

    def value_to_text(self, value):
        if not value:
            return TextAscii.value_to_text(self, value)
        elif self._make_clickable:
            # TODO: This is a workaround for a bug. This function needs to return str objects right now.
            return "%s" % html.render_a(   HTML(value)   , href="mailto:%s" % value)
        else:
            return value


class EmailAddressUnicode(TextUnicode, EmailAddress):
    def __init__(self, **kwargs):
        TextUnicode.__init__(self, **kwargs)
        EmailAddress.__init__(self, **kwargs)
        self._regex = re.compile(r'^[$\w._%+-]+@(localhost|[\w.-]+\.[\w]{2,24})$', re.I | re.UNICODE)

    def validate_value(self, value, varprefix):
        TextUnicode.validate_value(self, value, varprefix)
        EmailAddress.validate_value(self, value, varprefix)
        ValueSpec.custom_validate(self, value, varprefix)


# Network as used in routing configuration, such as
# "10.0.0.0/8" or "192.168.56.1"
class IPv4Network(TextAscii):
    def __init__(self, **kwargs):
        kwargs.setdefault("size", 18)
        TextAscii.__init__(self, **kwargs)

    def validate_value(self, value, varprefix):
        if "/" in value:
            try:
                network, bits = value.split("/")
                bits = int(bits)
            except:
                raise MKUserError(varprefix, _("Please use the syntax X.X.X.X/YY"))
        else:
            network = value
            bits = 32

        if bits < 0 or bits > 32:
            raise MKUserError(varprefix, _("Invalid number of bits. Must be in range 1 ... 32"))

        if value.count(".") != 3:
            raise MKUserError(varprefix, _("The network must contain three dots"))

        octets = self.validate_ipaddress(network, varprefix)

        # Make sure that non-network bits are zero
        l = (octets[0] << 24) + (octets[1] << 16) + (octets[2] << 8) + (octets[3])
        for b in range(bits, 32):
            if l & (2 ** (31-b)) != 0:
                raise MKUserError(varprefix, _("Please make sure that only the %d non-network bits are non-zero") % bits)

        ValueSpec.custom_validate(self, value, varprefix)


    def validate_ipaddress(self, value, varprefix):
        try:
            octets = map(int, value.split("."))
            if len(octets) != 4:
                raise MKUserError(varprefix, _("Please specify four octets (X.X.X.X/YY)"))
            for o in octets:
                if o < 0 or o > 255:
                    raise MKUserError(varprefix, _("Invalid octet %d (must be in range 1 ... 255)") % o)
            return octets
        except MKUserError:
            raise
        except:
            raise MKUserError(varprefix, _("Invalid IP address syntax"))


class IPv4Address(IPv4Network):
    def __init__(self, **kwargs):
        kwargs.setdefault("size", 16)
        IPv4Network.__init__(self, **kwargs)

    def validate_value(self, value, varprefix):
        self.validate_ipaddress(value, varprefix)
        ValueSpec.custom_validate(self, value, varprefix)


class TextAsciiAutocomplete(TextAscii):
    def __init__(self, completion_ident, completion_params, **kwargs):
        kwargs["onkeyup"] = "vs_autocomplete(this, %s, %s, %s);%s" % \
                            (json.dumps(completion_ident),
                             json.dumps(completion_params),
                             json.dumps(kwargs.get("onkeyup")),
                             kwargs.get("onkeyup", ""))
        kwargs["autocomplete"] = False
        super(TextAsciiAutocomplete, self).__init__(**kwargs)


    @classmethod
    def idents(cls):
        idents = {}
        for type_class in cls.__subclasses__(): # pylint: disable=no-member
            idents[type_class.ident] = type_class
        return idents


    @classmethod
    def ajax_handler(cls):
        ident = html.var("ident")
        if not ident:
            raise MKUserError("ident", _("You need to set the \"%s\" parameter.") % "ident")

        if ident not in cls.idents():
            raise MKUserError("ident", _("Invalid ident: %s") % ident)

        raw_params = html.var("params")
        if not raw_params:
            raise MKUserError("params", _("You need to set the \"%s\" parameter.") % "params")

        try:
            params = json.loads(raw_params)
        except json.JSONDecodeError, e:
            raise MKUserError("params", _("Invalid parameters: %s") % e)

        value = html.var("value")
        if value is None:
            raise MKUserError("params", _("You need to set the \"%s\" parameter.") % "value")

        result_data = cls.idents()[ident].autocomplete_choices(value, params)

        # Check for correct result_data format
        assert type(result_data) == list
        if result_data:
            assert type(result_data[0]) in [list, tuple]
            assert len(result_data[0]) == 2

        html.write(json.dumps(result_data))


# Renders an input field for entering a host name while providing
# an auto completion dropdown field
class MonitoredHostname(TextAsciiAutocomplete):
    ident = "hostname"

    def __init__(self, from_active_config=False, **kwargs):
        super(MonitoredHostname, self).__init__("hostname", {
            # Autocomplete from active config via livestatus or WATO world
            "from_active_config": from_active_config,
        }, **kwargs)


    # called by the webservice with the current input fiel value and
    # the completions_params to get the list of choices
    @classmethod
    def autocomplete_choices(cls, value, params):
        if params["from_active_config"]:
            return cls._get_choices_via_livestatus(value)
        else:
            return cls._get_choices_via_wato(value)


    @classmethod
    def _get_choices_via_livestatus(cls, value):
        import sites

        query = (
            "GET hosts\n"
            "Columns: host_name\n"
            "Filter: host_name ~~ %s" % lqencode(value)
        )
        hosts = sorted(sites.live().query_column_unique(query))

        return [ (h, h) for h in hosts ]


    @classmethod
    def _get_choices_via_wato(cls, value):
        raise NotImplementedError()



# A host name with or without domain part. Also allow IP addresses
class Hostname(TextAscii):
    def __init__(self, **kwargs):
        TextAscii.__init__(self, **kwargs)
        self._regex = re.compile('^[-0-9a-zA-Z_.]+$')
        self._regex_error = _("Please enter a valid hostname or IPv4 address. "
                              "Only letters, digits, dash, underscore and dot are allowed.")
        if "allow_empty" not in kwargs:
            self._allow_empty = False



# Use this for all host / ip address input fields!
class HostAddress(TextAscii):
    def __init__(self, **kwargs):
        TextAscii.__init__(self, **kwargs)
        self._allow_host_name    = kwargs.get("allow_host_name",    True)
        self._allow_ipv4_address = kwargs.get("allow_ipv4_address", True)
        self._allow_ipv6_address = kwargs.get("allow_ipv6_address", True)


    def validate_value(self, value, varprefix):
        if value and self._allow_host_name and self._is_valid_host_name(value):
            pass
        elif value and self._allow_ipv4_address and self._is_valid_ipv4_address(value):
            pass
        elif value and self._allow_ipv6_address and self._is_valid_ipv6_address(value):
            pass
        elif not self._allow_empty:
            raise MKUserError(varprefix, _("Invalid host address. You need to specify the address "
                                           "either as %s.") % ", ".join(self._allowed_type_names()))

        ValueSpec.custom_validate(self, value, varprefix)


    def _is_valid_host_name(self, hostname):
        # http://stackoverflow.com/questions/2532053/validate-a-hostname-string/2532344#2532344
        if len(hostname) > 255:
            return False

        if hostname[-1] == ".":
            hostname = hostname[:-1] # strip exactly one dot from the right, if present

        # must be not all-numeric, so that it can't be confused with an IPv4 address.
        # Host names may start with numbers (RFC 1123 section 2.1) but never the final part,
        # since TLDs are alphabetic.
        if re.match(r"[\d.]+$", hostname):
            return False

        allowed = re.compile("(?!-)[A-Z\d-]{1,63}(?<!-)$", re.IGNORECASE)
        return all(allowed.match(x) for x in hostname.split("."))


    def _is_valid_ipv4_address(self, address):
        # http://stackoverflow.com/questions/319279/how-to-validate-ip-address-in-python/4017219#4017219
        try:
            socket.inet_pton(socket.AF_INET, address)
        except AttributeError: # no inet_pton here, sorry
            try:
                socket.inet_aton(address)
            except socket.error:
                return False

            return address.count('.') == 3

        except socket.error: # not a valid address
            return False

        return True


    def _is_valid_ipv6_address(self, address):
        # http://stackoverflow.com/questions/319279/how-to-validate-ip-address-in-python/4017219#4017219
        try:
            socket.inet_pton(socket.AF_INET6, address)
        except socket.error: # not a valid address
            return False
        return True


    def _allowed_type_names(self):
        allowed = []
        if self._allow_host_name:
            allowed.append(_("Host- or DNS name"))

        if self._allow_ipv4_address:
            allowed.append(_("IPv4 address"))

        if self._allow_ipv6_address:
            allowed.append(_("IPv6 address"))

        return allowed



class AbsoluteDirname(TextAscii):
    def __init__(self, **kwargs):
        TextAscii.__init__(self, **kwargs)
        self._regex = re.compile('^(/|(/[^/]+)+)$')
        self._regex_error = _("Please enter a valid absolut pathname with / as a path separator.")


# Valuespec for a HTTP or HTTPS Url, that
# automatically adds http:// to the value if no protocol has
# been specified
class HTTPUrl(TextAscii):
    def __init__(self, **kwargs):
        kwargs.setdefault("size", 64)
        TextAscii.__init__(self, **kwargs)
        self._target = kwargs.get("target")

    def validate_value(self, value, varprefix):
        TextAscii.validate_value(self, value, varprefix)
        if value:
            if not value.startswith("http://") and not value.startswith("https://"):
                raise MKUserError(varprefix, _("The URL must begin with http:// or https://"))
        ValueSpec.custom_validate(self, value, varprefix)

    def from_html_vars(self, varprefix):
        value = TextAscii.from_html_vars(self, varprefix)
        if value:
            if not "://" in value:
                value = "http://" + value
        return value

    def value_to_text(self, url):
        if not url.startswith("http://") and not url.startswith("https://"):
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
        return html.render_a(text, href=url, target=self._target if self._target else None)

def CheckMKVersion(**args):
    args = args.copy()
    args["regex"] = "[0-9]+\.[0-9]+\.[0-9]+([bpi][0-9]+|i[0-9]+p[0-9]+)?$"
    args["regex_error"] = _("This is not a valid Check_MK version number")
    return TextAscii(**args)


class TextAreaUnicode(TextUnicode):
    def __init__(self, **kwargs):
        TextUnicode.__init__(self, **kwargs)
        self._cols = kwargs.get("cols", 60)
        self._try_max_width = kwargs.get("try_max_width", False) # If set, uses calc(100%-10px)
        self._rows = kwargs.get("rows", 20)  # Allowed: "auto" -> Auto resizing
        self._minrows = kwargs.get("minrows", 0) # Minimum number of initial rows when "auto"
        self._monospaced = kwargs.get("monospaced", False) # select TT font

    def value_to_text(self, value):
        if self._monospaced:
            # TODO: This is a workaround for a bug. This function needs to return str objects right now.
            return "%s" % html.render_pre(   HTML(value)   , class_="ve_textarea")
        else:
            return html.attrencode(value).replace("\n", "<br>")

    def render_input(self, varprefix, value):
        self.classtype_info()
        if value == None:
            value = "" # should never happen, but avoids exception for invalid input
        if self._rows == "auto":
            func = 'valuespec_textarea_resize(this);'
            attrs = { "onkeyup" : func, "onmousedown" : func, "onmouseup" : func, "onmouseout" : func }
            if html.has_var(varprefix):
                rows = len(html.var(varprefix).splitlines())
            else:
                rows = len(value.splitlines())
            rows = max(rows, self._minrows)
        else:
            attrs = {}
            rows = self._rows

        if self._monospaced:
            attrs["class"] = "tt"

        if self._prefix_buttons:
            html.open_div(style="white-space: nowrap;")

        html.text_area(varprefix, value, rows=rows, cols=self._cols,
                       attrs = attrs, try_max_width=self._try_max_width)
        if self._prefix_buttons:
            self.render_buttons()
            html.close_div()


    # Overridded because we do not want to strip() here and remove '\r'
    def from_html_vars(self, varprefix):
        text = html.get_unicode_input(varprefix, "").replace('\r', '')
        if text and not text.endswith("\n"):
            text += "\n" # force newline at end
        return text

# A variant of TextAscii() that validates a path to a filename that
# lies in an existing directory.
# TODO: Rename the valuespec here to ExistingFilename or somehting similar
class Filename(TextAscii):
    def __init__(self, **kwargs):
        TextAscii.__init__(self, **kwargs)
        if "size" not in kwargs:
            self._size = 60
        if "default" in kwargs:
            self._default_path = kwargs["default"]
        else:
            self._default_path = "/tmp/foo"
        if "trans_func" in kwargs:
            self._trans_func = kwargs["trans_func"]
        else:
            self._trans_func = None

    def canonical_value(self):
        return self._default_path

    def validate_value(self, value, varprefix):
        # The transformation function only changes the value for validation. This is
        # usually a function which is later also used within the code which uses
        # this variable to e.g. replace macros
        if self._trans_func:
            value = self._trans_func(value)

        if len(value) == 0:
            raise MKUserError(varprefix, _("Please enter a filename."))

        if value[0] != "/":
            raise MKUserError(varprefix, _("Sorry, only absolute filenames are allowed. "
                                           "Your filename must begin with a slash."))
        if value[-1] == "/":
            raise MKUserError(varprefix, _("Your filename must not end with a slash."))

        dir = value.rsplit("/", 1)[0]
        if not os.path.isdir(dir):
            raise MKUserError(varprefix, _("The directory %s does not exist or is not a directory.") % dir)

        # Write permissions to the file cannot be checked here since we run with Apache
        # permissions and the file might be created with Nagios permissions (on OMD this
        # is the same, but for others not)

        ValueSpec.custom_validate(self, value, varprefix)



class ListOfStrings(ValueSpec):
    def __init__(self, **kwargs):
        ValueSpec.__init__(self, **kwargs)
        if "valuespec" in kwargs:
            self._valuespec = kwargs.get("valuespec")
        elif "size" in kwargs:
            self._valuespec = TextAscii(size=kwargs["size"])
        else:
            self._valuespec = TextAscii()
        self._vertical = kwargs.get("orientation", "vertical") == "vertical"
        self._allow_empty = kwargs.get("allow_empty", True)
        self._empty_text  = kwargs.get("empty_text", "")
        self._max_entries = kwargs.get("max_entries")


    def help(self):
        help_text = ValueSpec.help(self)

        field_help = self._valuespec.help()
        if help_text and field_help:
            return help_text + " " + field_help
        elif field_help:
            return field_help
        else:
            return help_text


    def render_input(self, vp, value):
        self.classtype_info()
        # Form already submitted?
        if html.has_var(vp + "_0"):
            value = self.from_html_vars(vp)
            # Remove variables from URL, so that they do not appear
            # in hidden_fields()
            nr = 0
            while html.has_var(vp + "_%d" % nr):
                html.del_var(vp + "_%d" % nr)
                nr += 1

        html.open_div(id_=vp, class_=["listofstrings", "vertical" if self._vertical else "horizontal"])

        for nr, s in enumerate(value + [""]):
            html.open_div()
            self._valuespec.render_input(vp + "_%d" % nr, s)
            html.close_div()
        html.close_div()
        html.div('', style="clear:left;")
        html.help(self.help())
        html.javascript("list_of_strings_init('%s');" % vp)

    def canonical_value(self):
        return []

    def value_to_text(self, value):
        if not value:
            return self._empty_text

        if self._vertical:
            # TODO: This is a workaround for a bug. This function needs to return str objects right now.
            s = map(lambda v: html.render_tr(html.render_td(HTML(self._valuespec.value_to_text(v)))), value)
            return "%s" % html.render_table(HTML().join(s))
        else:
            return ", ".join([ self._valuespec.value_to_text(v) for v in value ])

    def from_html_vars(self, vp):
        value = []
        nr = 0
        while True:
            varname = vp + "_%d" % nr
            if not html.has_var(varname):
                break
            if html.var(varname, "").strip():
                value.append(self._valuespec.from_html_vars(varname))
            nr += 1
        return value

    def validate_datatype(self, value, vp):
        if type(value) != list:
            raise MKUserError(vp, _("Expected data type is list, but your type is %s.") %
                                                                        type_name(value))
        for nr, s in enumerate(value):
            self._valuespec.validate_datatype(s, vp + "_%d" % nr)

    def validate_value(self, value, vp):
        if len(value) == 0 and not self._allow_empty:
            if self._empty_text:
                msg = self._empty_text
            else:
                msg = _("Please specify at least one value")
            raise MKUserError(vp + "_0", msg)

        if self._max_entries != None and len(value) > self._max_entries:
            raise MKUserError(vp + "_%d" % self._max_entries,
                  _("You can specify at most %d entries") % self._max_entries)

        if self._valuespec:
            for nr, s in enumerate(value):
                self._valuespec.validate_value(s, vp + "_%d" % nr)
        ValueSpec.custom_validate(self, value, vp)



class ListOfIntegers(ListOfStrings):
    def __init__(self, **kwargs):
        int_args = {}
        for key in [ "minvalue", "maxvalue" ]:
            if key in kwargs:
                int_args[key] = kwargs[key]
        int_args["display_format"] = "%s"
        int_args["convfunc"] = lambda x: x if x == '' else saveint(x)
        int_args["minvalue"] = 17
        int_args["default_value"] = 34
        valuespec = Integer(**int_args)
        kwargs["valuespec"] = valuespec
        ListOfStrings.__init__(self, **kwargs)

# Generic list-of-valuespec ValueSpec with Javascript-based
# add/delete/move
class ListOf(ValueSpec):
    def __init__(self, valuespec, **kwargs):
        ValueSpec.__init__(self, **kwargs)
        self._valuespec     = valuespec
        self._magic         = kwargs.get("magic", "@!@")
        self._rowlabel      = kwargs.get("row_label")
        self._add_label     = kwargs.get("add_label", _("Add new element"))
        self._del_label     = kwargs.get("del_label", _("Delete this entry"))
        self._movable       = kwargs.get("movable", True)
        self._totext        = kwargs.get("totext") # pattern with option %d
        self._text_if_empty = kwargs.get("text_if_empty", _("No entries"))
        self._allow_empty   = kwargs.get("allow_empty", True)
        self._empty_text    = kwargs.get("empty_text") # complain text if empty
        if not self._empty_text:
            self._empty_text = _("Please specify at least one entry")

    def del_button(self, vp, nr):
        js = "valuespec_listof_delete(this, '%s', '%s')" % (vp, nr)
        html.icon_button("#", self._del_label, "delete", onclick=js)

    def move_button(self, vp, nr, where):
        js = "valuespec_listof_move(this, '%s', '%s', '%s')" % (vp, nr, where)
        where_name = {
            "up" : _("up"),
            "down" : _("down"),
        }
        html.empty_icon_button() # needed as placeholder
        html.icon_button("#", _("Move this entry %s") % (where_name[where]),
           where, onclick=js, style = "display:none" if not self._movable else '')

    # Implementation idea: we render our element-valuespec
    # once in a hidden div that is not evaluated. All occurances
    # of a magic string are replaced with the actual number
    # of entry, while beginning with 1 (this makes visual
    # numbering in labels, etc. possible). The current number
    # of entries is stored in the hidden variable 'varprefix'
    def render_input(self, varprefix, value):
        self.classtype_info()

        # Beware: the 'value' is only the default value in case the form
        # has not yet been filled in. In the complain phase we must
        # ignore 'value' but reuse the input from the HTML variables -
        # even if they are not syntactically correct. Calling from_html_vars
        # here is *not* an option since this might not work in case of
        # a wrong user input.

        # Render reference element for cloning
        html.open_table(id_="%s_prototype" % varprefix, style="display:none;")
        html.open_tr()
        html.open_td(class_="vlof_buttons")

        html.hidden_field(varprefix + "_indexof_" + self._magic, "",
                          add_var=True, class_="index") # reconstruct order after moving stuff
        self.del_button(varprefix, self._magic)
        if self._movable:
            self.move_button(varprefix, self._magic, "up")
            self.move_button(varprefix, self._magic, "down")
        html.close_td()
        html.open_td(class_="vlof_content")
        self._valuespec.render_input(
            varprefix + "_" + self._magic,
            self._valuespec.default_value())
        html.close_td()
        html.close_tr()
        html.close_table()

        # In the 'complain' phase, where the user already saved the
        # form but the validation failed, we must not display the
        # original 'value' but take the value from the HTML variables.
        if html.has_var("%s_count" % varprefix):
            filled_in = True
            count = len(self.get_indexes(varprefix))
            value = [None] * count # dummy for the loop
        else:
            filled_in = False
            count = len(value)

        html.hidden_field('%s_count' % varprefix,
            str(count),
            id = '%s_count' % varprefix,
            add_var = True)

        # Actual table of currently existing entries
        html.open_table(id_="%s_table" % varprefix, class_=["valuespec_listof"])

        for nr, v in enumerate(value):
            html.open_tr()
            html.open_td(class_="vlof_buttons")
            html.hidden_field(varprefix + "_indexof_%d" % (nr+1), "",
                              add_var=True, class_="index") # reconstruct order after moving stuff
            self.del_button(varprefix, nr+1)
            if self._movable:
                self.move_button(varprefix, nr+1, "up") # visibility fixed by javascript
                self.move_button(varprefix, nr+1, "down")
            html.close_td()
            html.open_td(class_="vlof_content")
            self._valuespec.render_input(varprefix + "_%d" % (nr+1), v)
            html.close_td()
            html.close_tr()
        html.close_table()
        html.br()
        html.jsbutton(varprefix + "_add", self._add_label,
            "valuespec_listof_add('%s', '%s')" % (varprefix, self._magic))
        html.javascript("valuespec_listof_fixarrows(document.getElementById('%s_table').childNodes[0]);" % varprefix)


    def canonical_value(self):
        return []


    def value_to_text(self, value):
        if self._totext:
            if "%d" in self._totext:
                return self._totext % len(value)
            else:
                return self._totext
        elif not value:
            return self._text_if_empty
        else:
            # TODO: This is a workaround for a bug. This function needs to return str objects right now.
            s = map(lambda v: html.render_tr(html.render_td(   HTML(self._valuespec.value_to_text(v))    )), value)
            return "%s" % html.render_table(HTML().join(s))


    def get_indexes(self, varprefix):
        count = int(html.var(varprefix + "_count", 0))
        n = 1
        indexes = {}
        while n <= count:
            indexof = html.var(varprefix + "_indexof_%d" % n)
            # for deleted entries, we have removed the whole row, therefore indexof is None
            if indexof != None:
                indexes[int(indexof)] = n
            n += 1
        return indexes

    def from_html_vars(self, varprefix):
        indexes = self.get_indexes(varprefix)
        value = []
        k = indexes.keys()
        k.sort()
        for i in k:
            val = self._valuespec.from_html_vars(varprefix + "_%d" % indexes[i])
            value.append(val)
        return value

    def validate_datatype(self, value, varprefix):
        if type(value) != list:
            raise MKUserError(varprefix, _("The type must be list, but is %s") % type_name(value))
        for n, v in enumerate(value):
            self._valuespec.validate_datatype(v, varprefix + "_%d" % (n+1))

    def validate_value(self, value, varprefix):
        if not self._allow_empty and len(value) == 0:
            raise MKUserError(varprefix, self._empty_text)
        for n, v in enumerate(value):
            self._valuespec.validate_value(v, varprefix + "_%d" % (n+1))
        ValueSpec.custom_validate(self, value, varprefix)


# A generic valuespec where the user can choose from a list of sub-valuespecs.
# Each sub-valuespec can be added only once
class ListOfMultiple(ValueSpec):
    def __init__(self, choices, **kwargs):
        ValueSpec.__init__(self, **kwargs)
        self._choices = choices
        self._choice_dict = dict(choices)
        self._size = kwargs.get("size")
        self._add_label = kwargs.get("add_label", _("Add element"))
        self._del_label = kwargs.get("del_label", _("Delete this entry"))
        self._delete_style = kwargs.get("delete_style", "default") # or "filter"

    def del_button(self, varprefix, ident):
        js = "vs_listofmultiple_del('%s', '%s')" % (varprefix, ident)
        html.icon_button("#", self._del_label, "delete", onclick=js)

    def render_input(self, varprefix, value):
        self.classtype_info()
        # Beware: the 'value' is only the default value in case the form
        # has not yet been filled in. In the complain phase we must
        # ignore 'value' but reuse the input from the HTML variables -
        # even if they are not syntactically correct. Calling from_html_vars
        # here is *not* an option since this might not work in case of
        # a wrong user input.

        # Special styling for filters
        extra_css = "filter" if self._delete_style == "filter" else None

        # In the 'complain' phase, where the user already saved the
        # form but the validation failed, we must not display the
        # original 'value' but take the value from the HTML variables.
        if html.var("%s_active" % varprefix):
            value = self.from_html_vars(varprefix)

        # Save all selected items
        html.hidden_field('%s_active' % varprefix,
            ';'.join([ k for k in value.keys() if k in self._choice_dict]),
            id = '%s_active' % varprefix, add_var = True)

        # Actual table of currently existing entries
        html.open_table(id_="%s_table" % varprefix, class_=["valuespec_listof", extra_css])

        def render_content():
            html.open_td( class_=["vlof_content", extra_css])
            vs.render_input(prefix, value.get(ident))
            html.close_td()

        def render_del():
            html.open_td(class_=["vlof_buttons", extra_css])
            self.del_button(varprefix, ident)
            html.close_td()

        for ident, vs in self._choices:
            cls = 'unused' if ident not in value else ''
            prefix = varprefix + '_' + ident
            html.open_tr(id_="%s_row" % prefix, class_=cls)
            if self._delete_style == "filter":
                render_content()
                render_del()
            else:
                render_del()
                render_content()
            html.close_tr()
        html.close_table()
        html.br()

        choosable = [('', '')] + [ (ident, vs.title()) for ident, vs in self._choices ]
        attrs = {}
        if self._size != None:
            attrs["style"] = "width: %dex" % self._size
        if self._delete_style == "filter":
            attrs["class"] = "vlof_filter"
        html.select(varprefix + '_choice', choosable, attrs=attrs)
        html.javascript('vs_listofmultiple_init(\'%s\');' % varprefix)
        html.jsbutton(varprefix + '_add', self._add_label, "vs_listofmultiple_add('%s')" % varprefix)

    def canonical_value(self):
        return {}

    def value_to_text(self, value):
        table_content = HTML()
        for ident, val in value:
            vs = self._choice_dict[ident]
            # TODO: This is a workaround for a bug. This function needs to return str objects right now.
            table_content += html.render_tr(html.render_td(vs.title())\
                                          + html.render_td(    HTML(vs.value_to_text(val))    ))
        return "%s" % html.render_table(table_content)

    def from_html_vars(self, varprefix):
        value = {}
        active = html.var('%s_active' % varprefix).strip()
        if not active:
            return value

        for ident in active.split(';'):
            vs = self._choice_dict[ident]
            value[ident] = vs.from_html_vars(varprefix + '_' + ident)
        return value

    def validate_datatype(self, value, varprefix):
        if type(value) != dict:
            raise MKUserError(varprefix, _("The type must be dict, but is %s") % type_name(value))
        for ident, val in value.items():
            self._choice_dict[ident].validate_datatype(val, varprefix + '_' + ident)

    def validate_value(self, value, varprefix):
        for ident, val in value.items():
            self._choice_dict[ident].validate_value(val, varprefix + '_' + ident)
        ValueSpec.custom_validate(self, value, varprefix)


# Same but for floating point values
class Float(Integer):
    def __init__(self, **kwargs):
        Integer.__init__(self, **kwargs)
        self._decimal_separator = kwargs.get("decimal_separator", ".")
        self._display_format = kwargs.get("display_format", "%.2f")
        self._allow_int = kwargs.get("allow_int", False)

    def render_input(self, varprefix, value):
        self.classtype_info()
        Integer.render_input(self, varprefix, value, convfunc = savefloat)

    def canonical_value(self):
        return float(Integer.canonical_value(self))

    def value_to_text(self, value):
        return Integer.value_to_text(self, value).replace(".", self._decimal_separator)

    def from_html_vars(self, varprefix):
        try:
            return float(html.var(varprefix))
        except:
            raise MKUserError(varprefix,
            _("The text <b><tt>%s</tt></b> is not a valid floating point number.") % html.var(varprefix))

    def validate_datatype(self, value, varprefix):
        if type(value) == float:
            return

        if type(value) in [ int, long ] and self._allow_int:
            return

        raise MKUserError(varprefix, _("The value %r has type %s, but must be of type float%s") %
             (value, type_name(value),  _(" or int") if self._allow_int else ''))


class Percentage(Float):
    def __init__(self, **kwargs):
        Float.__init__(self, **kwargs)
        if "minvalue" not in kwargs:
            self._minvalue = 0.0
        if "maxvalue" not in kwargs:
            self._maxvalue = 101.0
        if "unit" not in kwargs:
            self._unit = "%"
        if "display_format" not in kwargs:
            self._display_format = "%.1f"

        self._allow_int = kwargs.get("allow_int", False)

    def value_to_text(self, value):
        return (self._display_format + "%%") % value

    def validate_datatype(self, value, varprefix):
        if self._allow_int:
            if type(value) not in [ int, float ]:
                raise MKUserError(varprefix, _("The value %r has type %s, but must be either float or int")
                                % (value, type_name(value)))
        else:
            Float.validate_datatype(self, value, varprefix)


class Checkbox(ValueSpec):
    def __init__(self, **kwargs):
        ValueSpec.__init__(self, **kwargs)
        self._label = kwargs.get("label")
        self._true_label = kwargs.get("true_label", _("on"))
        self._false_label = kwargs.get("false_label", _("off"))
        self._onclick = kwargs.get("onclick")

    def canonical_value(self):
        return False

    def render_input(self, varprefix, value):
        self.classtype_info()
        html.checkbox(varprefix, value, label = self._label, onclick=self._onclick)

    def value_to_text(self, value):
        return self._true_label if value else self._false_label

    def from_html_vars(self, varprefix):
        if html.var(varprefix):
            return True
        else:
            return False

    def validate_datatype(self, value, varprefix):
        if type(value) != bool:
            raise MKUserError(varprefix, _("The value %r has type %s, but must be of type bool") %
                    (value, type_name(value)))

# A type-save dropdown choice. Parameters:
# help_separator: if you set this to a character, e.g. "-", then
# value_to_texg will omit texts from the character up to the end of
# a choices name.
# Note: The list of choices may contain 2-tuples or 3-tuples.
# The format is (value, text {, icon} )
# choices may also be a function that returns - when called
# wihtout arguments - such a tuple list. That way the choices
# can by dynamically computed
class DropdownChoice(ValueSpec):
    def __init__(self, **kwargs):
        ValueSpec.__init__(self, **kwargs)
        self._choices            = kwargs["choices"]
        self._help_separator     = kwargs.get("help_separator")
        self._label              = kwargs.get("label")
        self._prefix_values      = kwargs.get("prefix_values", False)
        self._sorted             = kwargs.get("sorted", False)
        self._empty_text         = kwargs.get("empty_text", _("There are no elements defined for this selection yet."))
        self._invalid_choice     = kwargs.get("invalid_choice", "replace") # also possible: "complain"
        self._invalid_choice_title = kwargs.get("invalid_choice_title", _("Element does not exist anymore"))
        self._invalid_choice_error = kwargs.get("invalid_choice_error",
            _("The selected element is not longer available. Please select something else."))
        self._no_preselect       = kwargs.get("no_preselect", False)
        self._no_preselect_value = kwargs.get("no_preselect_value", None)
        self._no_preselect_title = kwargs.get("no_preselect_title", "") # if not preselected
        self._no_preselect_error = kwargs.get("no_preselect_error", _("Please make a selection"))
        self._on_change          = kwargs.get("on_change")

    def choices(self):
        result = []
        if type(self._choices) == list:
            result = self._choices
        else:
            result = self._choices()

        if self._no_preselect:
            return [(self._no_preselect_value, self._no_preselect_title)] + result
        else:
            return result

    def canonical_value(self):
        choices = self.choices()
        if len(choices) > 0:
            return choices[0][0]
        else:
            return None

    def render_input(self, varprefix, value):
        self.classtype_info()
        if self._label:
            html.write("%s " % self._label)
        # Convert values from choices to keys
        defval = "0"
        options = []
        for n, entry in enumerate(self.choices()):
            if self._prefix_values:
                entry = (entry[0], "%s - %s" % entry)
            options.append((str(n),) + entry[1:])
            if entry[0] == value:
                defval = str(n)

        # In complain mode: Use the value received from the HTML variable
        if self._invalid_choice == "complain" and value != None and self._value_is_invalid(value):
            defval = value
            options.append((defval, self._get_invalid_choice_title(value)))

        if value == None and not options:
            html.write(self._empty_text)
            return

        if len(options) == 0:
            html.write(self._empty_text)
        elif len(options[0]) == 3:
            html.icon_select(varprefix, options, defval)
        else:
            if not self._sorted:
                html.select(varprefix, options, defval, onchange=self._on_change)
            else:
                html.sorted_select(varprefix, options, defval, onchange=self._on_change)


    def _get_invalid_choice_title(self, value):
        if "%s" in self._invalid_choice_title:
            return self._invalid_choice_title % value
        else:
            return self._invalid_choice_title


    def value_to_text(self, value):
        for entry in self.choices():
            val, title = entry[:2]
            if value == val:
                if self._help_separator:
                    return title.split(self._help_separator, 1)[0].strip()
                else:
                    return title
        return html.attrencode(self._get_invalid_choice_title(value))


    def from_html_vars(self, varprefix):
        sel = html.var(varprefix)
        choices = self.choices()
        for n, entry in enumerate(choices):
            val = entry[0]
            if sel == str(n):
                return val

        if self._invalid_choice == "replace":
            return self.default_value() # garbled URL or len(choices) == 0
        else:
            return sel

    def validate_value(self, value, varprefix):
        if self._no_preselect and value == self._no_preselect_value:
            raise MKUserError(varprefix, self._no_preselect_error)

        if self._invalid_choice == "complain" and self._value_is_invalid(value):
            if value != None:
                raise MKUserError(varprefix, self._invalid_choice_error)
            else:
                raise MKUserError(varprefix, _("There is no element available to choose from."))

        ValueSpec.custom_validate(self, value, varprefix)

    def validate_datatype(self, value, varprefix):
        choices = self.choices()
        if not choices and value == None:
            return

        for val, title in choices:
            if val == value:
                return

        #raise MKUserError(varprefix, _("Invalid value %s, must be in %s") %
        #    (value, ", ".join([v for (v,t) in choices])))

    def _value_is_invalid(self, value):
        for entry in self.choices():
            if entry[0] == value:
                return False
        return True


# Special conveniance variant for monitoring states
class MonitoringState(DropdownChoice):
    def __init__(self, **kwargs):
        choices = [ ( 0, _("OK")),
                    ( 1, _("WARN")),
                    ( 2, _("CRIT")),
                    ( 3, _("UNKNOWN")) ]
        kwargs.setdefault("default_value", 0)
        DropdownChoice.__init__(self, choices=choices, **kwargs)

# A Dropdown choice where the elements are ValueSpecs.
# The currently selected ValueSpec will be displayed.
# The text representations of the ValueSpecs will be used as texts.
# A ValueSpec of None is also allowed and will return
# the value None. It is also allowed to leave out the
# value spec for some of the choices (which is the same as
# using None).
# The resulting value is either a single value (if no
# value spec is defined for the selected entry) or a pair
# of (x, y) where x is the value of the selected entry and
# y is the value of the valuespec assigned to that entry.
# choices is a list of triples: [ ( value, title, vs ), ... ]
class CascadingDropdown(ValueSpec):
    def __init__(self, **kwargs):
        ValueSpec.__init__(self, **kwargs)

        if type(kwargs["choices"]) == list:
            self._choices = self.normalize_choices(kwargs["choices"])
        else:
            self._choices = kwargs["choices"] # function, store for later

        self._separator = kwargs.get("separator", ", ")
        self._sorted = kwargs.get("sorted", True)
        self._orientation = kwargs.get("orientation", "vertical") # or horizontal
        if kwargs.get("encoding", "tuple") == "list":
            self._encoding_type = list
        else:
            self._encoding_type = tuple

        self._no_elements_text = kwargs.get("no_elements_text",
                _("There are no elements defined for this selection"))

        self._no_preselect       = kwargs.get("no_preselect", False)
        self._no_preselect_value = kwargs.get("no_preselect_value", None)
        self._no_preselect_title = kwargs.get("no_preselect_title", "") # if not preselected
        self._no_preselect_error = kwargs.get("no_preselect_error", _("Please make a selection"))


    def normalize_choices(self, choices):
        new_choices = []
        for entry in choices:
            if len(entry) == 2: # plain entry with no sub-valuespec
                entry = entry + (None,) # normlize to three entries
            new_choices.append(entry)
        return new_choices


    def choices(self):
        if type(self._choices) == list:
            result = self._choices
        else:
            result = self.normalize_choices(self._choices())

        if self._no_preselect:
            result = [(self._no_preselect_value, self._no_preselect_title, None)] \
                     + result

        return result


    def canonical_value(self):
        choices = self.choices()
        if not choices:
            return None

        if choices[0][2]:
            return self._encoding_type((choices[0][0], choices[0][2].canonical_value()))
        else:
            return choices[0][0]

    def default_value(self):
        try:
            return self._default_value
        except:
            choices = self.choices()
            if not choices:
                return None

            if choices[0][2]:
                return self._encoding_type((choices[0][0], choices[0][2].default_value()))
            else:
                return choices[0][0]

    def render_input(self, varprefix, value):
        self.classtype_info()
        def_val = '0'
        options = []
        choices = self.choices()
        if not choices:
            html.write(self._no_elements_text)
            return

        for nr, (val, title, vs) in enumerate(choices):
            options.append((str(nr), title))
            # Determine the default value for the select, so the
            # the dropdown pre-selects the line corresponding with value.
            # Note: the html.select() with automatically show the modified
            # selection, if the HTML variable varprefix_sel aleady
            # exists.
            if value == val or (
                type(value) == self._encoding_type and value[0] == val):
                def_val = str(nr)

        vp = varprefix + "_sel"
        onchange="valuespec_cascading_change(this, '%s', %d);" % (varprefix, len(choices))
        if self._sorted:
            html.select(vp, options, def_val, onchange=onchange)
        else:
            html.sorted_select(vp, options, def_val, onchange=onchange)

        # make sure, that the visibility is done correctly, in both
        # cases:
        # 1. Form painted for the first time (no submission yet, vp missing in URL)
        # 2. Form already submitted -> honor URL variable vp for visibility
        cur_val = html.var(vp)

        if self._orientation == "vertical":
            html.br()
        else:
            html.nbsp()
        for nr, (val, title, vs) in enumerate(choices):
            if vs:
                vp = varprefix + "_%d" % nr
                # Form already submitted once (and probably in complain state)
                if cur_val != None:
                    try:
                        def_val_2 = vs.from_html_vars(vp)
                    except MKUserError:
                        def_val_2 = vs.default_value()
                    if cur_val == str(nr):
                        disp = ""
                    else:
                        disp = "none"
                else: # form painted the first time
                    if value == val \
                       or (type(value) == self._encoding_type and value[0] == val):
                        def_val_2 = value[1]
                        disp = ""
                    else:
                        def_val_2 = vs.default_value()
                        disp = "none"
                html.open_span(id_="%s_%s_sub" % (varprefix, nr), style="display:%s;" % disp)
                html.help(vs.help())
                vs.render_input(vp, def_val_2)
                html.close_span()

    def value_to_text(self, value):
        choices = self.choices()
        for val, title, vs in choices:
            if (vs and value and value[0] == val) or \
               (value == val):
                if not vs:
                    return title
                else:
                    return title + self._separator + \
                       vs.value_to_text(value[1])
        return "" # Nothing selected? Should never happen

    def from_html_vars(self, varprefix):
        choices = self.choices()

        # No choices and "no elements text" is shown: The html var is
        # not present and no choice can be made. So fallback to default
        # value and let the validation methods lead to an error message.
        if not choices:
            return self.default_value()

        try:
            sel = int(html.var(varprefix + "_sel"))
        except:
            sel = 0
        val, title, vs = choices[sel]
        if vs:
            val = self._encoding_type((val, vs.from_html_vars(varprefix + "_%d" % sel)))
        return val

    def validate_datatype(self, value, varprefix):
        choices = self.choices()
        for nr, (val, title, vs) in enumerate(choices):
            if value == val or (
                type(value) == self._encoding_type and value[0] == val):
                if vs:
                    if type(value) != self._encoding_type or len(value) != 2:
                        raise MKUserError(varprefix + "_sel",
                             _("Value must be a %s with two elements.") % self._encoding_type.__name__)
                    vs.validate_datatype(value[1], varprefix + "_%d" % nr)
                return
        raise MKUserError(varprefix, _("Value %r is not allowed here.") % value)

    def validate_value(self, value, varprefix):
        if self._no_preselect and value == self._no_preselect_value:
            raise MKUserError(varprefix, self._no_preselect_error)

        choices = self.choices()
        for nr, (val, title, vs) in enumerate(choices):
            if value == val or (
                type(value) == self._encoding_type and value[0] == val):
                if vs:
                    vs.validate_value(value[1], varprefix + "_%d" % nr)
                ValueSpec.custom_validate(self, value, varprefix)
                return
        raise MKUserError(varprefix, _("Value %r is not allowed here.") % (value, ))



# The same logic as the dropdown choice, but rendered
# as a group of radio buttons.
# columns == None or unset -> separate with "&nbsp;"
class RadioChoice(DropdownChoice):
    def __init__(self, **kwargs):
        DropdownChoice.__init__(self, **kwargs)
        self._columns = kwargs.get("columns")
        # Allow orientation as corner cases of columns
        orientation = kwargs.get("orientation")
        if orientation == "vertical":
            self._columns = 1
        elif orientation == "horizontal":
            self._columns = 9999999

    def render_input(self, varprefix, value):
        self.classtype_info()
        html.begin_radio_group()
        if self._columns != None:
            html.open_table(class_=["radiochoice"])
            html.open_tr()

        if self._sorted:
            choices = self._choices[:]
            choices.sort(cmp=lambda a,b: cmp(a[1], b[1]))
        else:
            choices = self._choices
        for n, entry in enumerate(choices):
            if self._columns != None:
                html.open_td()
            if len(entry) > 2 and entry[2] != None: # icon!
                label = html.render_icon(entry[2], entry[1])
            else:
                label = entry[1]
            html.radiobutton(varprefix, str(n), value == entry[0], label)
            if len(entry) > 3 and entry[3]:
                html.open_p()
                html.write(entry[3])
                html.close_p()
            if self._columns != None:
                html.close_td()
                if (n+1) % self._columns == 0 and (n+1) < len(self._choices):
                    html.tr('')
            else:
                html.nbsp()
        if self._columns != None:
            mod = len(self._choices) % self._columns
            if mod:
                for td_counter in range(self._columns - mod - 1):
                    html.td('')
            html.close_tr()
            html.close_table()
        html.end_radio_group()



# A list of checkboxes representing a list of values
class ListChoice(ValueSpec):
    def __init__(self, **kwargs):
        ValueSpec.__init__(self, **kwargs)
        self._choices = kwargs.get("choices")
        self._columns = kwargs.get("columns", 1)
        self._allow_empty = kwargs.get("allow_empty", True)
        self._loaded_at = None
        self._render_function = kwargs.get("render_function",
                  lambda id, val: val)
        self._toggle_all = kwargs.get("toggle_all", False)
        self._render_orientation = kwargs.get("render_orientation", "horizontal") # other: vertical
        self._no_elements_text = kwargs.get("no_elements_text",
                _("There are no elements defined for this selection"))

    # In case of overloaded functions with dynamic elements
    def load_elements(self):
        if self._choices != None:
            if type(self._choices) == list:
                self._elements = self._choices
            else:
                self._elements = self._choices()
            return

        if self._loaded_at != id(html):
            self._elements = self.get_elements()
            self._loaded_at = id(html) # unique for each query!

    def get_elements(self):
        raise NotImplementedError()

    def canonical_value(self):
        return []


    def _draw_listchoice(self, varprefix, value, elements, columns, toggle_all):

        if self._toggle_all:
            html.a(_("Check / Uncheck all"), href="javascript:vs_list_choice_toggle_all('%s')" % varprefix)

        html.open_table(id_="%s_tbl" % varprefix, class_=["listchoice"])
        for nr, (key, title) in enumerate(elements):
            if nr % self._columns == 0:
                if nr > 0:
                    html.close_tr()
                html.open_tr()
            html.open_td()
            html.checkbox("%s_%d" % (varprefix, nr), key in value, label = title)
            html.close_td()
        html.close_tr()
        html.close_table()


    def render_input(self, varprefix, value):
        self.classtype_info()
        self.load_elements()
        if not self._elements:
            html.write(self._no_elements_text)
            return

        self._draw_listchoice(varprefix, value, self._elements, self._columns, self._toggle_all)

        # Make sure that at least one variable with the prefix is present
        html.hidden_field(varprefix, "1", add_var=True)

    def value_to_text(self, value):
        self.load_elements()
        d = dict(self._elements)
        texts = [ self._render_function(v, d.get(v,v)) for v in value ]
        if self._render_orientation == "horizontal":
            return ", ".join(texts)
        else:
            # TODO: This is a workaround for a bug. This function needs to return str objects right now.
            return "%s" % html.render_table(html.render_tr(html.render_td(html.render_br().join(    map(lambda x: HTML(x), texts)  ))))
            #OLD: return "<table><tr><td>" + "<br>".join(texts) + "</td></tr></table>"

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
            raise MKUserError(varprefix, _("The datatype must be list, but is %s") % type_name(value))
        d = dict(self._elements)
        for v in value:
            if v not in d:
                raise MKUserError(varprefix, _("%s is not an allowed value") % v)

    def validate_value(self, value, varprefix):
        if not self._allow_empty and not value:
            raise MKUserError(varprefix, _('You have to select at least one element.'))
        ValueSpec.custom_validate(self, value, varprefix)

# A alternative way of editing list choices
class MultiSelect(ListChoice):
    def __init__(self, **kwargs):
        ListChoice.__init__(self, **kwargs)

    def _render_field(self, name, choices, selected=None):
        if selected is None:
            selected = []
        html.open_select(multiple="", name=name)
        for key, title in choices:
            html.option(title, value=key, selected='' if key in selected else None)

        html.close_select()

    def render_input(self, varprefix, value):
        self.classtype_info()
        self.load_elements()
        self._render_field(varprefix, self._elements, value)

    def from_html_vars(self, varprefix):
        self.load_elements()
        value = []
        hv = html.list_var(varprefix)
        for key, title in self._elements:
            if key in hv:
                value.append(key)
        return value

# Implements a choice of items which is realized with
# two ListChoices select fields. One contains all available
# items and one contains all selected items.
# Optionally you can have the user influance the order of
# the entries by simply clicking them in a certain order.
# If that feature is not being used, then the original order
# of the elements is always being kept.
# TODO: Beware: the keys in this choice are not type safe.
# They can only be strings. They must not contain | or other
# dangerous characters. We should fix this and make it this
# compatible to DropdownChoice()
class DualListChoice(ListChoice):
    def __init__(self, **kwargs):
        super(DualListChoice, self).__init__(**kwargs)
        self._autoheight = kwargs.get("autoheight", False)
        self._custom_order = kwargs.get("custom_order", False)
        self._instant_add = kwargs.get("instant_add", False)
        self._enlarge_active = kwargs.get("enlarge_active", False)
        if "rows" in kwargs:
            self._rows = kwargs.get("rows", 5)
            self._autoheight = False
        else:
            self._rows = 5
        self._size = kwargs.get("size") # Total width in ex


    def render_input(self, varprefix, value):
        self.classtype_info()

        self.load_elements()
        if not self._elements:
            html.write(_("There are no elements for selection."))
            return

        selected   = []
        unselected = []
        if self._custom_order:
            edict = dict(self._elements)
            allowed_keys = edict.keys()
            for v in value:
                if v in allowed_keys:
                    selected.append((v, edict[v]))

            for v, name in self._elements:
                if v not in value:
                    unselected.append((v, edict[v]))
        else:
            for e in self._elements:
                if e[0] in value:
                    selected.append(e)
                else:
                    unselected.append(e)

        select_func   = 'vs_duallist_switch(\'unselected\', \'%s\', %d);' % (varprefix, 1 if self._custom_order else 0)
        unselect_func = 'vs_duallist_switch(\'selected\', \'%s\', 1);' % varprefix

        html.open_table(class_=["vs_duallist"], style = "width: %dpx;" % (self._size * 6.4) if self._size else None)

        html.open_tr()
        html.open_td(class_="head")
        html.write(_('Available'))
        if not self._instant_add:
            html.a(">", href="javascript:%s;" % select_func, class_=["control", "add"])
        html.close_td()

        html.open_td(class_="head")
        html.write(_('Selected'))
        if not self._instant_add:
            html.a("<", href="javascript:%s;" % unselect_func, class_=["control", "del"])
        html.close_td()
        html.close_tr()

        onchange_unselected = select_func if self._instant_add else ''
        onchange_selected   = unselect_func if self._instant_add else ''
        if self._enlarge_active:
            onchange_selected   = 'vs_duallist_enlarge(\'selected\', \'%s\');' % varprefix
            onchange_unselected = 'vs_duallist_enlarge(\'unselected\', \'%s\');' % varprefix

        func = html.select if self._custom_order else html.sorted_select
        attrs = {
            'multiple'   : 'multiple',
            'style'      : 'height:auto' if self._autoheight else "height: %dpx" % (self._rows * 16),
            'ondblclick' : select_func if not self._instant_add else '',
        }

        html.open_tr()
        html.open_td()
        func(varprefix + '_unselected', unselected, attrs = attrs, onchange = onchange_unselected)
        html.close_td()
        html.open_td()
        func(varprefix + '_selected', selected, attrs = attrs, onchange = onchange_selected)
        html.close_td()
        html.close_tr()

        html.close_table()
        html.hidden_field(varprefix, '|'.join([k for k, v in selected]), id = varprefix, add_var = True)


    def validate_value(self, value, varprefix):
        try:
            ListChoice.validate_value(self, value, varprefix)
        except MKUserError, e:
            raise MKUserError(e.varname + "_selected", e.message)


    def from_html_vars(self, varprefix):
        self.load_elements()
        selected = html.var(varprefix, '').split('|')
        value = []
        if self._custom_order:
            edict = dict(self._elements)
            allowed_keys = edict.keys()
            for v in selected:
                if v in allowed_keys:
                    value.append(v)
        else:
            for key, title in self._elements:
                if key in selected:
                    value.append(key)
        return value


# A type-save dropdown choice with one extra field that
# opens a further value spec for entering an alternative
# Value.
class OptionalDropdownChoice(DropdownChoice):
    def __init__(self, **kwargs):
        DropdownChoice.__init__(self, **kwargs)
        self._explicit = kwargs["explicit"]
        self._otherlabel = kwargs.get("otherlabel", _("Other"))

    def canonical_value(self):
        return self._explicit.canonical_value()

    def value_is_explicit(self, value):
        return value not in [ c[0] for c in self.choices() ]

    def render_input(self, varprefix, value):
        self.classtype_info()
        defval = "other"
        options = []
        for n, (val, title) in enumerate(self.choices()):
            options.append((str(n), title))
            if val == value:
                defval = str(n)
        if self._sorted:
            options.sort(cmp = lambda a,b: cmp(a[1], b[1]))
        options.append(("other", self._otherlabel))
        html.select(varprefix, options, defval, # attrs={"style":"float:left;"},
                    onchange="valuespec_toggle_dropdown(this, '%s_ex');" % varprefix )
        if html.has_var(varprefix):
            div_is_open = html.var(varprefix) == "other"
        else:
            div_is_open = self.value_is_explicit(value)

        html.open_span(id_="%s_ex" % varprefix, style=["white-space: nowrap;", None if div_is_open else "display:none;"])
        html.nbsp()

        if defval == "other":
            input_value = value
        else:
            input_value = self._explicit.default_value()
        html.help(self._explicit.help())
        self._explicit.render_input(varprefix + "_ex", input_value)
        html.close_span()

    def value_to_text(self, value):
        for val, title in self.choices():
            if val == value:
                return title
        return self._explicit.value_to_text(value)

    def from_html_vars(self, varprefix):
        choices = self.choices()
        sel = html.var(varprefix)
        if sel == "other":
            return self._explicit.from_html_vars(varprefix + "_ex")

        for n, (val, title) in enumerate(choices):
            if sel == str(n):
                return val
        return choices[0][0] # can only happen if user garbled URL

    def validate_value(self, value, varprefix):
        if self.value_is_explicit(value):
            self._explicit.validate_value(value, varprefix)
        # else valid_datatype already has made the job
        ValueSpec.custom_validate(self, value, varprefix)

    def validate_datatype(self, value, varprefix):
        for val, title in self.choices():
            if val == value:
                return
        self._explicit.validate_datatype(value, varprefix + "_ex")


# Input of date with optimization for nearby dates
# in the future. Useful for example for alarms. The
# date is represented by a UNIX timestamp where the
# seconds are silently ignored.
def round_date(t):
    return int(t) / seconds_per_day * seconds_per_day

def today():
    return round_date(time.time())

class Weekday(DropdownChoice):
    def __init__(self, **kwargs):
        kwargs['choices'] = sorted(defines.weekdays().items())
        DropdownChoice.__init__(self, **kwargs)


class RelativeDate(OptionalDropdownChoice):
    def __init__(self, **kwargs):
        choices = [
            (0, _("today")),
            (1, _("tomorrow"))
        ]
        weekday = time.localtime(today()).tm_wday
        for w in range(2, 7):
            wd = (weekday + w) % 7
            choices.append((w, defines.weekday_name(wd)))
        for w in range(0, 7):
            wd = (weekday + w) % 7
            if w < 2:
                title = _(" next week")
            else:
                title = _(" in %d days") % (w + 7)
            choices.append((w + 7, defines.weekday_name(wd) + title))

        kwargs['choices']    = choices
        kwargs['explicit']   = Integer()
        kwargs['otherlabel'] = _("in ... days")

        OptionalDropdownChoice.__init__(self, **kwargs)

        if "default_days" in kwargs:
            self._default_value = kwargs["default_days"] * seconds_per_day + today()
        else:
            self._default_value = today()

    def canonical_value(self):
        return self._default_value

    def render_input(self, varprefix, value):
        self.classtype_info()
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
        ValueSpec.custom_validate(self, value, varprefix)

# A ValueSpec for editing a date. The date is
# represented as a UNIX timestamp x where x % seconds_per_day
# is zero (or will be ignored if non-zero), as long as
# include_time is not set to True
class AbsoluteDate(ValueSpec):
    def __init__(self, **kwargs):
        ValueSpec.__init__(self, **kwargs)
        self._show_titles = kwargs.get("show_titles", True)
        self._label = kwargs.get("label")
        self._include_time = kwargs.get("include_time", False)
        self._format = kwargs.get("format", "%F %T" if self._include_time else "%F")
        self._default_value = kwargs.get("default_value", None)
        self._allow_empty = kwargs.get('allow_empty', False)
        # The default is that "None" means show current date/time in the
        # input fields. This option changes the input fields to be empty by default
        # and makes the value able to be None when no time is set.
        # FIXME: Shouldn't this be the default?
        self._none_means_empty = kwargs.get("none_means_empty", False)

    def default_value(self):
        if self._default_value != None:
            return self._default_value
        else:
            if self._allow_empty:
                return None

            if self._include_time:
                return time.time()
            else:
                return today()

    def canonical_value(self):
        return self.default_value()

    def split_date(self, value):
        if self._none_means_empty and value == None:
            return (None,) * 6
        lt = time.localtime(value)
        return lt.tm_year, lt.tm_mon, lt.tm_mday, \
               lt.tm_hour, lt.tm_min, lt.tm_sec


    def render_input(self, varprefix, value):

        self.classtype_info()

        if self._label:
            html.write("%s" % self._label)
            html.nbsp()

        year, month, day, hour, mmin, sec = self.split_date(value)
        values = [ ("_year",  year,  4),
                   ("_month", month, 2),
                   ("_day",   day,   2)]
        if self._include_time:
            values += [ None,
                       ("_hour", hour, 2),
                       ("_min",  mmin, 2),
                       ("_sec",  sec,  2)]

        if not self._show_titles:
            titles = [_("Year"), _("Month"), _("Day")]
            if self._include_time:
                titles += ['', _("Hour"), _("Minute"), _("Sec.")]

            html.open_table(class_=["vs_date"])

            html.open_tr()
            map(html.th, titles)
            html.close_tr()

            html.open_tr()
            for val in values:
                html.open_td()
                html.nbsp() if val is None else\
                    html.number_input(varprefix + val[0], val[1], size=val[2])
                html.close_td()
            html.close_tr()

            html.close_table()

        else:
            for count, val in enumerate(values):
                if count > 0:
                    html.write(" ")
                html.nbsp() if val is None else\
                    html.number_input(varprefix + val[0], val[1], size=val[2])


    def set_focus(self, varprefix):
        html.set_focus(varprefix + "_year")


    def value_to_text(self, value):
        return time.strftime(self._format, time.localtime(value))


    def from_html_vars(self, varprefix):
        parts = []
        entries = [
            ("year",  _("year"),  1970, 2038),
            ("month", _("month"),    1,   12),
            ("day",   _("day"),      1,   31)
        ]

        if self._include_time:
            entries += [
                ("hour", _("hour"), 0, 23),
                ("min",  _("min"),  0, 59),
                ("sec",  _("sec"),  0, 59),
            ]

        for what, title, mmin, mmax in entries:
            try:
                varname = varprefix + "_" + what
                part = int(html.var(varname))
            except:
                if self._allow_empty:
                    return None
                else:
                    raise MKUserError(varname, _("Please enter a valid number"))
            if part < mmin or part > mmax:
                raise MKUserError(varname, _("The value for %s must be between %d and %d") %
                                                                        (title, mmin, mmax))
            parts.append(part)

        # Construct broken time from input fields. Assume no-dst
        parts += [0] * (3 if self._include_time else 6)
        # Convert to epoch
        epoch = time.mktime(tuple(parts))
        # Convert back to localtime in order to know DST setting
        localtime = time.localtime(epoch)
        # Enter DST setting of that time
        parts[-1] = localtime.tm_isdst
        # Convert to epoch again
        return time.mktime(tuple(parts))

    def validate_datatype(self, value, varprefix):
        if value == None and self._allow_empty:
            return
        if type(value) not in [ int, float ]:
            raise MKUserError(varprefix, _("The type of the timestamp must be int or float, but is %s") %
                              type_name(value))

    def validate_value(self, value, varprefix):
        if (not self._allow_empty and value == None) or value < 0 or int(value) > (2**31-1):
            return MKUserError(varprefix, _("%s is not a valid UNIX timestamp") % value)
        ValueSpec.custom_validate(self, value, varprefix)


# Valuespec for entering times like 00:35 or 16:17. Currently
# no seconds are supported. But this could easily be added.
# The value itself is stored as a pair of integers, a.g.
# (0, 35) or (16, 17). If the user does not enter a time
# the vs will return None.
class Timeofday(ValueSpec):
    def __init__(self, **kwargs):
        ValueSpec.__init__(self, **kwargs)
        self._allow_24_00 = kwargs.get("allow_24_00", False)
        self._allow_empty = kwargs.get("allow_empty", True)

    def canonical_value(self):
        if self._allow_empty:
            return None
        else:
            return (0, 0)

    def render_input(self, varprefix, value):
        self.classtype_info()
        text = ("%02d:%02d" % value) if value else ''
        html.text_input(varprefix, text, size = 5)

    def value_to_text(self, value):
        if value == None:
            return ""
        else:
            return "%02d:%02d" % value

    def from_html_vars(self, varprefix):
        # Fully specified
        text = html.var(varprefix, "").strip()
        if not text:
            return None

        if re.match("^(24|[0-1][0-9]|2[0-3]):[0-5][0-9]$", text):
            return tuple(map(int, text.split(":")))

        # only hours
        try:
            b = int(text)
            return (b, 0)
        except:
            raise MKUserError(varprefix,
                   _("Invalid time format '<tt>%s</tt>', please use <tt>24:00</tt> format.") % text)

    def validate_datatype(self, value, varprefix):
        if self._allow_empty and value == None:
            return

        if type(value) != tuple:
            raise MKUserError(varprefix, _("The datatype must be tuple, but ist %s") % type_name(value))

        if len(value) != 2:
            raise MKUserError(varprefix, _("The tuple must contain two elements, but you have %d") % len(value))

        for x in value:
            if type(x) != int:
                raise MKUserError(varprefix, _("All elements of the tuple must be of type int, you have %s") % type_name(x))

    def validate_value(self, value, varprefix):
        if not self._allow_empty and value == None:
            raise MKUserError(varprefix, _("Please enter a time."))
        if self._allow_24_00:
            max_value = (24, 0)
        else:
            max_value = (23, 59)
        if value > max_value:
            raise MKUserError(varprefix, _("The time must not be greater than %02d:%02d.") % max_value)
        elif value[0] < 0 or value[1] < 0 or value[0] > 24 or value[1] > 59:
            raise MKUserError(varprefix, _("Hours/Minutes out of range"))
        ValueSpec.custom_validate(self, value, varprefix)


# Range like 00:15 - 18:30
class TimeofdayRange(ValueSpec):
    def __init__(self, **kwargs):
        ValueSpec.__init__(self, **kwargs)
        self._allow_empty = kwargs.get("allow_empty", True)
        self._bounds = (
            Timeofday(allow_empty = self._allow_empty,
                      allow_24_00 = True),
            Timeofday(allow_empty = self._allow_empty,
                      allow_24_00 = True),
        )

    def canonical_value(self):
        if self._allow_empty:
            return None
        else:
            return (0, 0), (24, 0)

    def render_input(self, varprefix, value):
        self.classtype_info()
        if value == None:
            value = (None, None)
        self._bounds[0].render_input(varprefix + "_from", value[0])
        html.nbsp()
        html.write("-")
        html.nbsp()
        self._bounds[1].render_input(varprefix + "_until", value[1])

    def value_to_text(self, value):
        if value == None:
            return ""
        else:
            return self._bounds[0].value_to_text(value[0]) + "-" + \
                   self._bounds[1].value_to_text(value[1])

    def from_html_vars(self, varprefix):
        from_value = self._bounds[0].from_html_vars(varprefix + "_from")
        until_value = self._bounds[1].from_html_vars(varprefix + "_until")
        if (from_value == None) != (until_value == None):
            raise MKUserError(varprefix + "_from", _("Please leave either both from and until empty or enter two times."))
        if from_value == None:
            return None
        else:
            return (from_value, until_value)

    def validate_datatype(self, value, varprefix):
        if self._allow_empty and value == None:
            return

        if type(value) != tuple:
            raise MKUserError(varprefix, _("The datatype must be tuple, but ist %s") % type_name(value))

        if len(value) != 2:
            raise MKUserError(varprefix, _("The tuple must contain two elements, but you have %d") % len(value))

        self._bounds[0].validate_datatype(value[0], varprefix + "_from")
        self._bounds[1].validate_datatype(value[1], varprefix + "_until")

    def validate_value(self, value, varprefix):
        if value == None:
            if self._allow_empty:
                return
            else:
                raise MKUserError(varprefix + "_from", _("Please enter a valid time of day range"))
            return

        self._bounds[0].validate_value(value[0], varprefix + "_from")
        self._bounds[1].validate_value(value[1], varprefix + "_until")
        if value[0] > value[1]:
            raise MKUserError(varprefix + "_until", _("The <i>from</i> time must not be later then the <i>until</i> time."))
        ValueSpec.custom_validate(self, value, varprefix)

# TODO: Move to cmklib
month_names = [
  _("January"),   _("February"), _("March"),    _("April"),
  _("May"),       _("June"),     _("July"),     _("August"),
  _("September"), _("October"),  _("November"), _("December")
]


class TimeHelper(object):
    @staticmethod
    def round(timestamp, unit):
        time_s = list(time.localtime(timestamp))
        time_s[3] = time_s[4] = time_s[5] = 0
        time_s[8] = -1
        if unit == 'd':
            return time.mktime(time_s)
        elif unit == 'w':
            days = time_s[6]       # 0 based
        elif unit == 'm':
            days = time_s[2] - 1   # 1 based
        elif unit == 'y':
            days = time_s[7] - 1   # 1 based
        else:
            raise MKGeneralException("invalid time unit %s" % unit)

        return TimeHelper.round(time.mktime(time_s) - days * 86400 + 3600, 'd')

    @staticmethod
    def add(timestamp, count, unit):
        if unit == 'h':
            return timestamp + 3600 * count
        elif unit == 'd':
            return timestamp + 86400 * count
        elif unit == 'w':
            return timestamp + (7 * 86400) * count
        elif unit == 'm':
            time_s = list(time.localtime(timestamp))
            years, months = divmod(abs(count), 12)

            if count < 0:
                years *= -1
                months *= -1

            time_s[0] += years
            time_s[1] += months
            if time_s[1] <= 0:
                time_s[0] -= 1
                time_s[1] = 12 - time_s[1]
            time_s[8] = -1
            return time.mktime(time_s)
        elif unit == 'y':
            time_s = list(time.localtime(timestamp))
            time_s[0] += count
            return time.mktime(time_s)
        else:
            MKGeneralException("invalid time unit %s" % unit)



class Timerange(CascadingDropdown):
    def __init__(self, **kwargs):
        self._title         = _('Time range')
        self._allow_empty   = kwargs.get("allow_empty", False)
        self._include_time  = kwargs.get("include_time", False)
        self._fixed_choices = kwargs.get("choices", [])
        kwargs['choices']   = self._prepare_choices
        CascadingDropdown.__init__(self, **kwargs)


    def _prepare_choices(self):
        choices = list(self._fixed_choices)

        if self._allow_empty:
            choices += [ (None, '') ]

        choices += self._get_graph_timeranges() + [
            ( "d0",  _("Today") ),
            ( "d1",  _("Yesterday") ),

            ( "w0",  _("This week") ),
            ( "w1",  _("Last week") ),

            ( "m0",  _("This month") ),
            ( "m1",  _("Last month") ),

            ( "y0",  _("This year") ),
            ( "y1",  _("Last year") ),

            ( "age", _("The last..."), Age() ),
            ( "date", _("Date range"),
                Tuple(
                    orientation = "horizontal",
                    title_br = False,
                    elements = [
                        AbsoluteDate(title = _("From:")),
                        AbsoluteDate(title = _("To:")),
            ])),
        ]

        if self._include_time:
            choices += [
                ( "time", _("Date & time range"),
                    Tuple(
                        orientation = "horizontal",
                        title_br = False,
                        elements = [
                            AbsoluteDate(
                                title = _("From:"),
                                include_time = True,
                            ),
                            AbsoluteDate(
                                title = _("To:"),
                                include_time = True,
                            ),
                        ],
                    ),
                )
            ]
        return choices



    def _get_graph_timeranges(self):
        try:
            import config # FIXME
            return [ (('age', timerange_attrs["duration"]), timerange_attrs['title'])
                     for timerange_attrs in config.graph_timeranges ]

        except AttributeError: # only available in cee
            return [ ( "4h",   _("The last 4 hours")),
                     ( "25h",  _("The last 25 hours")),
                     ( "8d",   _("The last 8 days")),
                     ( "35d",  _("The last 35 days")),
                     ( "400d", _("The last 400 days")), ]


    def compute_range(self, rangespec):
        if rangespec == None:
            rangespec = "4h"

        # Compatibility with previous versions
        elif rangespec[0] == "pnp_view":
            rangespec = {
                1: "4h",
                2: "25h",
                3: "8d",
                4: "35d",
                5: "400d"
            }.get(rangespec[1], "4h")

        now = time.time()

        if rangespec[0] == 'age':
            from_time = now - rangespec[1]
            until_time = now
            title = _("The last ") + Age().value_to_text(rangespec[1])
            return (from_time, until_time), title

        elif rangespec[0] in [ 'date', 'time' ]:
            from_time, until_time = rangespec[1]
            if from_time > until_time:
                raise MKUserError("avo_rangespec_9_0_year", _("The end date must be after the start date"))
            if rangespec[0] == 'date':
                # add 25 hours, then round to 00:00 of that day. This accounts for
                # daylight-saving time
                until_time = TimeHelper.round(TimeHelper.add(until_time, 25, 'h'), 'd')
            title = AbsoluteDate().value_to_text(from_time) + " ... " + \
                    AbsoluteDate().value_to_text(until_time)
            return (from_time, until_time), title

        else:
            until_time = now
            if rangespec[0].isdigit(): # 4h, 400d
                count = int(rangespec[:-1])
                from_time = TimeHelper.add(now, count * -1, rangespec[-1])
                unit_name = {
                    'd': "days",
                    'h': "hours"
                }[rangespec[-1]]
                title = _("Last %d %s") % (count, unit_name)
                return (from_time, now), title

            year, month = time.localtime(now)[:2]
            # base time is current time rounded down to the nearest unit (day, week, ...)
            from_time = TimeHelper.round(now, rangespec[0])
            # derive titles from unit ()
            titles = {
                'd': (_("Today"),     _("Yesterday")),
                'w': (_("This week"), _("Last week")),
                'y': (str(year),      str(year - 1)),
                'm': ("%s %d" % (month_names[month - 1], year),
                      "%s %d" % (month_names[(month + 10) % 12], year - int(month == 1))),
            }[rangespec[0]]

            if rangespec[1] == '0':
                return (from_time, now), titles[0]
            else: # last (previous)
                prev_time = TimeHelper.add(from_time, -1, rangespec[0])
                # add one hour to the calculated time so that if dst started in that period,
                # we don't round down a whole day
                prev_time = TimeHelper.round(prev_time + 3600, 'd')
                return (prev_time, from_time), titles[1]


# A selection of various date formats
def DateFormat(**args):
    args.setdefault("title", _("Date format"))
    args.setdefault("default_value", "%Y-%m-%d")
    args["choices"] = [
        ("%Y-%m-%d", "1970-12-18"),
        ("%d.%m.%Y", "18.12.1970"),
        ("%m/%d/%Y", "12/18/1970"),
        ("%d.%m.",   "18.12."),
        ("%m/%d",    "12/18"),
    ]
    return DropdownChoice(**args)


def TimeFormat(**args):
    args.setdefault("title", _("Time format"))
    args.setdefault("default_value", "%H:%M:%S")
    args["choices"] = [
        ("%H:%M:%S",    "18:27:36"),
        ("%l:%M:%S %p", "12:27:36 PM"),
        ("%H:%M",       "18:27"),
        ("%l:%M %p",    "6:27 PM"),
        ("%H",          "18"),
        ("%l %p",      "6 PM"),
    ]
    return DropdownChoice(**args)



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
        self._none_value = kwargs.get("none_value", None)
        self._sameline = kwargs.get("sameline", False)
        self._indent = kwargs.get("indent", True)

    def canonical_value(self):
        return self._none_value

    def render_input(self, varprefix, value):
        self.classtype_info()
        div_id = "option_" + varprefix
        checked = html.get_checkbox(varprefix + "_use")
        if checked == None:
            if self._negate:
                checked = value == self._none_value
            else:
                checked = value != self._none_value

        html.open_span()

        if self._label is not None:
            label = self._label
        elif self.title():
            label = self.title()
        elif self._negate:
            label = _(" Ignore this option")
        else:
            label = _(" Activate this option")

        html.checkbox(varprefix + "_use" , checked,
                      onclick="valuespec_toggle_option(this, %r, %r)" %
                         (div_id, 1 if self._negate else 0),
                      label = label)

        if self._sameline:
            html.nbsp()
        else:
            html.br()
        html.close_span()

        if self._indent:
            indent = 40
        else:
            indent = 0

        html.open_span(id_=div_id, style=["margin-left: %dpx;" % indent,
                                          "display:none;" if checked == self._negate else None])
        if value == self._none_value:
            value = self._valuespec.default_value()
        if self._valuespec.title():
            html.write(self._valuespec.title() + " ")
        self._valuespec.render_input(varprefix + "_value", value)
        html.close_span()

    def value_to_text(self, value):
        if value == self._none_value:
            return self._none_label
        else:
            return self._valuespec.value_to_text(value)

    def from_html_vars(self, varprefix):
        checkbox_checked = html.get_checkbox(varprefix + "_use") == True # not None or False
        if checkbox_checked != self._negate:
            return self._valuespec.from_html_vars(varprefix + "_value")
        else:
            return self._none_value

    def validate_datatype(self, value, varprefix):
        if value != self._none_value:
            self._valuespec.validate_datatype(value, varprefix + "_value")

    def validate_value(self, value, varprefix):
        if value != self._none_value:
            self._valuespec.validate_value(value, varprefix + "_value")
        ValueSpec.custom_validate(self, value, varprefix)

# Makes a configuration value optional, while displaying the current
# value as text with a checkbox in front of it. When the checkbox is being checked,
# the text hides and the encapsulated valuespec is being shown.
class OptionalEdit(Optional):
    def __init__(self, valuespec, **kwargs):
        Optional.__init__(self, valuespec, **kwargs)
        self._label = ''

    def render_input(self, varprefix, value):
        self.classtype_info()
        div_id = "option_" + varprefix
        checked = html.get_checkbox(varprefix + "_use")
        if checked == None:
            if self._negate:
                checked = True
            else:
                checked = False

        html.open_span()

        if self._label is not None:
            label = self._label
        elif self.title():
            label = self.title()
        elif self._negate:
            label = _(" Ignore this option")
        else:
            label = _(" Activate this option")

        html.checkbox(varprefix + "_use" , checked,
                      onclick="valuespec_toggle_option(this, %r, %r);valuespec_toggle_option(this, %r, %r)" %
                         (div_id + '_on', 1 if self._negate else 0,
                          div_id + '_off', 0 if self._negate else 1),
                      label = label)

        html.nbsp()
        html.close_span()

        if value == None:
            value = self._valuespec.default_value()

        html.open_span(id_="%s_off" % div_id, style="display:none;" if checked != self._negate else None)
        html.write(value)
        html.close_span()

        html.open_span(id_="%s_on" % div_id, style="display:none;" if checked == self._negate else None)
        if self._valuespec.title():
            html.write(self._valuespec.title() + " ")
        self._valuespec.render_input(varprefix + "_value", value)
        html.close_span()

    def from_html_vars(self, varprefix):
        return self._valuespec.from_html_vars(varprefix + "_value")

# Handle case when there are several possible allowed formats
# for the value (e.g. strings, 4-tuple or 6-tuple like in SNMP-Communities)
# The different alternatives must have different data types that can
# be distinguished with validate_datatype.
class Alternative(ValueSpec):
    def __init__(self, **kwargs):
        ValueSpec.__init__(self, **kwargs)
        self._elements = kwargs["elements"]
        self._match = kwargs.get("match") # custom match function, returns index in elements
        self._style = kwargs.get("style", "radio") # alternative: "dropdown"
        self._show_alternative_title = kwargs.get("show_alternative_title")
        self._on_change = kwargs.get("on_change") # currently only working for style="dropdown"
        self._orientation = kwargs.get("orientation", "vertical") # or horizontal: for style="dropdown"

    # Return the alternative (i.e. valuespec)
    # that matches the datatype of a given value. We assume
    # that always one matches. No error handling here.
    # This may also tranform the input value in case it gets
    # "decorated" in the from_html_vars function
    def matching_alternative(self, value):
        if self._match:
            return self._elements[self._match(value)], value

        for vs in self._elements:
            try:
                vs.validate_datatype(value, "")
                return vs, value
            except:
                pass

        return None, value

    def render_input(self, varprefix, value):
        self.classtype_info()
        if self._style == "radio":
            self.render_input_radio(varprefix, value)
        else:
            self.render_input_dropdown(varprefix, value)

    def render_input_dropdown(self, varprefix, value):
        mvs, value = self.matching_alternative(value)
        options = []
        sel_option = html.var(varprefix + "_use")
        for nr, vs in enumerate(self._elements):
            if not sel_option and vs == mvs:
                sel_option = str(nr)
            options.append((str(nr), vs.title()))
        onchange="valuespec_cascading_change(this, '%s', %d);" % (varprefix, len(options))
        if self._on_change:
            onchange += self._on_change
        if self._orientation == "horizontal":
            html.open_table()
            html.open_tr()
            html.open_td()
        html.select(varprefix + "_use", options, sel_option, onchange)
        if self._orientation == "vertical":
            html.write("<br><br>")

        for nr, vs in enumerate(self._elements):
            if str(nr) == sel_option:
                disp = ""
                cur_val = value
            else:
                disp = "none"
                cur_val = vs.default_value()

            if self._orientation == "horizontal":
                html.close_td()
                html.open_td()
            html.open_span(id_="%s_%s_sub" % (varprefix, nr), style="display:%s" % disp)
            html.help(vs.help())
            vs.render_input(varprefix + "_%d" % nr, cur_val)
            html.close_span()

        if self._orientation == "horizontal":
            html.close_td()
            html.close_tr()
            html.close_table()

    def render_input_radio(self, varprefix, value):
        mvs, value = self.matching_alternative(value)
        for nr, vs in enumerate(self._elements):
            if html.has_var(varprefix + "_use"):
                checked = html.var(varprefix + "_use") == str(nr)
            else:
                checked = vs == mvs

            html.help(vs.help())
            title = vs.title()
            if not title and nr:
                html.nbsp()
                html.nbsp()

            html.radiobutton(varprefix + "_use", str(nr), checked, title)
            if title:
                html.open_ul()
            if vs == mvs:
                val = value
            else:
                val = vs.default_value()
            vs.render_input(varprefix + "_%d" % nr, val)
            if title:
                html.close_ul()

    def set_focus(self, varprefix):
        # TODO: Set focus to currently active option
        pass

    def canonical_value(self):
        return self._elements[0].canonical_value()

    def default_value(self):
        try:
            if type(self._default_value) == type(lambda:True):
                return self._default_value()
            else:
                return self._default_value
        except:
            return self._elements[0].default_value()

    def value_to_text(self, value):
        vs, value = self.matching_alternative(value)
        if vs:
            output = ""
            if self._show_alternative_title and vs.title():
                output = "%s<br>" % vs.title()
            return output + vs.value_to_text(value)
        else:
            return _("invalid:") + " " + html.attrencode(str(value))

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
        vs, value = self.matching_alternative(value)
        for nr, v in enumerate(self._elements):
            if vs == v:
                vs.validate_value(value, varprefix + "_%d" % nr)
        ValueSpec.custom_validate(self, value, varprefix)


# Edit a n-tuple (with fixed size) of values
class Tuple(ValueSpec):
    def __init__(self, **kwargs):
        ValueSpec.__init__(self, **kwargs)
        self._elements = kwargs["elements"]
        self._show_titles = kwargs.get("show_titles", True)
        self._orientation = kwargs.get("orientation", "vertical") # also: horizontal, float
        self._separator = kwargs.get("separator", " ") # in case of float
        self._title_br = kwargs.get("title_br", True)

    def canonical_value(self):
        return tuple([x.canonical_value() for x in self._elements])

    def default_value(self):
        return tuple([x.default_value() for x in self._elements])

    def render_input(self, varprefix, value):
        self.classtype_info()
        if self._orientation != "float":
            html.open_table(class_=["valuespec_tuple"])
            if self._orientation == "horizontal":
                html.open_tr()

        for no, element in enumerate(self._elements):
            try:
                val = value[no]
            except:
                val = element.default_value()
            vp = varprefix + "_" + str(no)
            if self._orientation == "vertical":
                html.open_tr()
            elif self._orientation == "float":
                html.write(self._separator)

            if self._show_titles:
                elem_title = element.title()
                if elem_title:
                    title = element.title()[0].upper() + element.title()[1:]
                else:
                    title = ""
                if self._orientation == "vertical":
                    html.open_td(class_="tuple_left")
                    html.write(title)

                    html.help(element.help())
                    html.close_td()
                elif self._orientation == "horizontal":
                    html.open_td(class_="tuple_td")
                    html.open_span(class_=["title"])
                    html.write(title)

                    html.help(element.help())
                    html.close_span()
                    if self._title_br:
                        html.br()
                    else:
                        html.write(" ")
                else:
                    html.write(" ")
                    html.help(element.help())

            if self._orientation == "vertical":
                html.open_td(class_="tuple_right")

            element.render_input(vp, val)
            if self._orientation != "float":
                html.close_td()
                if self._orientation == "vertical":
                    html.close_tr()
        if self._orientation == "horizontal":
            html.close_tr()
        if self._orientation != "float":
            html.close_table()

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
        ValueSpec.custom_validate(self, value, varprefix)

    def validate_datatype(self, value, varprefix):
        if type(value) != tuple:
            raise MKUserError(varprefix,
            _("The datatype must be a tuple, but is %s") % type_name(value))
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
        self._empty_text = kwargs.get("empty_text", _("(no parameters)"))
        # Optionally a text can be specified to be shown by value_to_text()
        # when the value equal the default value of the value spec. Normally
        # the default values are shown.
        self._default_text = kwargs.get("default_text", None)
        self._required_keys = kwargs.get("required_keys", [])
        self._ignored_keys = kwargs.get("ignored_keys", [])
        self._default_keys = kwargs.get("default_keys", []) # keys present in default value
        if "optional_keys" in kwargs:
            ok = kwargs["optional_keys"]
            if type(ok) == list:
                self._required_keys = \
                    [ e[0] for e in self._get_elements() if e[0] not in ok ]
                self._optional_keys = True
            elif ok:
                self._optional_keys = True
            else:
                self._optional_keys = False
        else:
            self._optional_keys = True
        if "hidden_keys" in kwargs:
            self._hidden_keys = kwargs["hidden_keys"]
        else:
            self._hidden_keys = []

        self._columns = kwargs.get("columns", 1) # possible: 1 or 2
        self._render = kwargs.get("render", "normal") # also: "form" -> use forms.section()
        self._form_narrow = kwargs.get("form_narrow", False) # used if render == "form"
        self._form_isopen = kwargs.get("form_isopen", True) # used if render == "form"
        self._headers = kwargs.get("headers") # "sup" -> small headers in oneline mode
        self._migrate = kwargs.get("migrate") # value migration from old tuple version
        self._indent = kwargs.get("indent", True)

    def migrate(self, value):
        if self._migrate:
            return self._migrate(value)
        else:
            return value

    def _get_elements(self):
        if type(self._elements) == type(lambda: None):
            return self._elements()
        elif type(self._elements) == list:
            return self._elements
        else:
            return []

    # Additional variale form allows to specify the rendering
    # style right now
    def render_input(self, varprefix, value, form=None):
        self.classtype_info()
        value = self.migrate(value)
        if type(value) != dict:
            value = {} # makes code simpler in complain phase
        if form == True:
            self.render_input_form(varprefix, value)
        elif self._render == "form" and form == None:
            self.render_input_form(varprefix, value)
        elif self._render == "form_part" and form == None:
            self.render_input_form(varprefix, value, as_part=True)
        else:
            self.render_input_normal(varprefix, value, self._render == "oneline")

    def render_input_normal(self, varprefix, value, oneline = False):
        headers_sup = oneline and self._headers == "sup"
        if headers_sup or not oneline:
            html.open_table(class_=["dictionary"])
        if headers_sup:
            html.open_tr()
        for param, vs in self._get_elements():
            if param in self._hidden_keys:
                continue
            if not oneline:
                html.open_tr()
                html.open_td(class_="dictleft")

            div_id = varprefix + "_d_" + param
            vp     = varprefix + "_p_" + param
            colon_printed = False
            if self._optional_keys and param not in self._required_keys:
                visible = html.get_checkbox(vp + "_USE")
                if visible == None:
                    visible = param in value
                label = vs.title()
                if self._columns == 2:
                    label += ":"
                    colon_printed = True
                html.checkbox(vp + "_USE", param in value,
                              onclick="valuespec_toggle_option(this, %r)" % div_id,
                              label=label)
            else:
                visible = True
                if vs.title():
                    if headers_sup:
                        html.open_td()
                        html.open_b(class_=["header"])
                    html.write(" %s" % vs.title())
                    if oneline:
                        if self._headers == "sup":
                            html.close_b()
                            html.br()
                        else:
                            html.write(": ")

            if self._columns == 2:
                if vs.title() and not colon_printed:
                    html.write(':')
                html.help(vs.help())
                if not oneline:
                    html.close_td()
                    html.open_td(class_="dictright")

            else:
                if not oneline:
                    html.br()

            html.open_div(id_= div_id,
                          class_=["dictelement", "indent" if (self._indent and self._columns == 1) else None],
                          style= "display:none;" if not visible else
                                ("display:inline-block;" if oneline else None))

            if self._columns == 1:
                html.help(vs.help())
            # Remember: in complain mode we do not render 'value' (the default value),
            # but re-display the values from the HTML variables. We must not use 'value'
            # in that case.
            if type(value) == dict:
                vs.render_input(vp, value.get(param, vs.default_value()))
            else:
                vs.render_input(vp, None)
            html.close_div()
            if not oneline:
                html.close_td()
                html.close_tr()
            elif headers_sup:
                html.close_td()

        if not oneline:
            html.close_table()
        elif oneline and self._headers == "sup":
            html.close_tr()
            html.close_table()

    def render_input_form(self, varprefix, value, as_part=False):
        if self._headers:
            for header, sections in self._headers:
                self.render_input_form_header(varprefix, value, header, sections, as_part)
        else:
            self.render_input_form_header(varprefix, value, self.title() or _("Properties"), None, as_part)

        if not as_part:
            forms.end()

    def render_input_form_header(self, varprefix, value, title, sections, as_part):
        if not as_part:
            forms.header(title, isopen=self._form_isopen, narrow=self._form_narrow)

        for param, vs in self._get_elements():
            if param in self._hidden_keys:
                continue

            if sections and param not in sections:
                continue

            div_id = varprefix + "_d_" + param
            vp     = varprefix + "_p_" + param
            if self._optional_keys and param not in self._required_keys:
                visible = html.get_checkbox(vp + "_USE")
                if visible == None:
                    visible = param in value
                checkbox_code = html.render_checkbox(vp + "_USE", deflt=visible,
                                    onclick="valuespec_toggle_option(this, %r)" % div_id)
                forms.section(vs.title(), checkbox=checkbox_code)
            else:
                visible = True
                forms.section(vs.title())

            html.open_div(id_=div_id, style="display:none;" if not visible else None)
            html.help(vs.help())
            vs.render_input(vp, value.get(param, vs.default_value()))
            html.close_div()

    def set_focus(self, varprefix, key=None):
        elements = self._get_elements()
        if elements:
            if key == None:
                elements[0][1].set_focus(varprefix + "_p_" + elements[0][0])
            else:
                for element_key, element_vs in elements:
                    if element_key == key:
                        element_vs.set_focus(varprefix + "_p_" + key)

    def canonical_value(self):
        return dict([
            (name, vs.canonical_value())
             for (name, vs)
             in self._get_elements()
             if name in self._required_keys or not self._optional_keys])

    def default_value(self):
        def_val = {}
        for name, vs in self._get_elements():
            if name in self._required_keys or not self._optional_keys or name in self._default_keys:
                def_val[name] = vs.default_value()

        return def_val

    def value_to_text(self, value):
        value = self.migrate(value)
        oneline = self._render == "oneline"
        if not value:
            return self._empty_text

        if self._default_text and value == self.default_value():
            return self._default_text

        elem = self._get_elements()
        s = '' if oneline else HTML()
        for param, vs in elem:
            if param in value:
                # TODO: This is a workaround for a bug. This function needs to return str objects right now.
                text = HTML(vs.value_to_text(value[param]))
                if oneline:
                    if param != elem[0][0]:
                        s += ", "
                    s += "%s: %s" % (vs.title(), text)
                else:
                    s += html.render_tr(html.render_td("%s:&nbsp;" % vs.title(), class_="title") + html.render_td(text))
        if not oneline:
            s = html.render_table(s)
        return "%s" % s

    def from_html_vars(self, varprefix):
        value = {}
        for param, vs in self._get_elements():
            vp = varprefix + "_p_" + param
            if not self._optional_keys \
                or param in self._required_keys \
                or html.get_checkbox(vp + "_USE"):
                value[param] = vs.from_html_vars(vp)
        return value

    def validate_datatype(self, value, varprefix):
        value = self.migrate(value)

        if type(value) != dict:
            raise MKUserError(varprefix, _("The type must be a dictionary, but it is a %s") % type_name(value))

        for param, vs in self._get_elements():
            if param in value:
                vp = varprefix + "_p_" + param
                try:
                    vs.validate_datatype(value[param], vp)
                except MKUserError, e:
                    raise MKUserError(e.varname, _("%s: %s") % (vs.title(), e))
            elif not self._optional_keys or param in self._required_keys:
                raise MKUserError(varprefix, _("The entry %s is missing") % vs.title())

        # Check for exceeding keys
        allowed_keys = [ p for (p,v) in self._get_elements() ]
        if self._ignored_keys:
            allowed_keys += self._ignored_keys
        for param in value.keys():
            if param not in allowed_keys:
                raise MKUserError(varprefix, _("Undefined key '%s' in the dictionary. Allowed are %s.") %
                        (param, ", ".join(allowed_keys)))

    def validate_value(self, value, varprefix):
        value = self.migrate(value)

        for param, vs in self._get_elements():
            if param in value:
                vp = varprefix + "_p_" + param
                vs.validate_value(value[param], vp)
            elif not self._optional_keys or param in self._required_keys:
                raise MKUserError(varprefix, _("The entry %s is missing") % vs.title())
        ValueSpec.custom_validate(self, value, varprefix)


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
        self._label = kwargs.get("label")
        self._empty_text = kwargs.get("empty_text", _("There are no elements defined for this selection yet."))

    def load_elements(self):
        if self._loaded_at != id(html):
            self._elements = self.get_elements()
            self._loaded_at = id(html) # unique for each query!

    def get_elements(self):
        raise NotImplementedError()

    def canonical_value(self):
        self.load_elements()
        if len(self._elements) > 0:
            return self._elements.keys()[0]

    def render_input(self, varprefix, value):
        self.classtype_info()
        self.load_elements()
        if len(self._elements) == 0:
            html.write(self._empty_text)
        else:
            if self._label:
                html.write("%s" % self._label)
                html.nbsp()
            html.sorted_select(varprefix, self._elements.items(), value)

    def value_to_text(self, value):
        self.load_elements()
        return self._elements.get(value, value)

    def from_html_vars(self, varprefix):
        return html.var(varprefix)

    def validate_value(self, value, varprefix):
        self.load_elements()
        if len(self._elements) == 0:
            raise MKUserError(varprefix, _("You cannot save this rule.") + ' ' + self._empty_text)
        if value not in self._elements:
            raise MKUserError(varprefix, _("%s is not an existing element in this selection.") % (value,))
        ValueSpec.custom_validate(self, value, varprefix)

    def validate_datatype(self, value, varprefix):
        self.load_elements()
        # When no elements exists the default value is None and e.g. in wato.mode_edit_rule()
        # handed over to validate_datatype() before rendering the input form. Disable the
        # validation in this case to prevent validation errors. A helpful message is shown
        # during render_input()
        if len(self._elements) == 0 and value == None:
            return

        if type(value) != str:
            raise MKUserError(varprefix, _("The datatype must be str (string), but is %s") % type_name(value))


class AutoTimestamp(FixedValue):
    def __init__(self, **kwargs):
        FixedValue.__init__(self, **kwargs)

    def canonical_value(self):
        return time.time()

    def from_html_vars(self, varprefix):
        return time.time()

    def value_to_text(self, value):
        return time.strftime("%F %T", time.localtime(value))

    def validate_datatype(self, value, varprefix):
        if type(value) not in [ int, float ]:
            return MKUserError(varprefix, _("Invalid datatype of timestamp: must be int or float."))

# Fully transparant VS encapsulating a vs in a foldable
# container.
class Foldable(ValueSpec):
    def __init__(self, valuespec, **kwargs):
        ValueSpec.__init__(self, **kwargs)
        self._valuespec = valuespec
        self._open = kwargs.get("open", False)
        self._title_function = kwargs.get("title_function", None)

    def render_input(self, varprefix, value):
        self.classtype_info()
        try:
            title_value = value
            if html.form_submitted():
                try:
                    title_value = self._valuespec.from_html_vars(varprefix)
                except:
                    pass
            title = self._title_function(title_value)
        except:
            title = self._valuespec.title()
            if not title:
                title = _("(no title)")
        html.begin_foldable_container("valuespec_foldable", varprefix, self._open,
                       title, False)
        html.help(self._valuespec.help())
        self._valuespec.render_input(varprefix, value)
        html.end_foldable_container()

    def set_focus(self, varprefix):
        self._valuespec.set_focus(varprefix)

    def canonical_value(self):
        return self._valuespec.canonical_value()

    def default_value(self):
        return self._valuespec.default_value()

    def value_to_text(self, value):
        return self._valuespec.value_to_text(value)

    def from_html_vars(self, varprefix):
        return self._valuespec.from_html_vars(varprefix)

    def validate_datatype(self, value, varprefix):
        self._valuespec.validate_datatype(value, varprefix)

    def validate_value(self, value, varprefix):
        self._valuespec.validate_value(value, varprefix)
        ValueSpec.custom_validate(self, value, varprefix)


# Transforms the value from one representation to
# another while being completely transparent to the user.
# forth: function that converts a value into the representation
#        needed by the encapsulated vs
# back:  function that converts a value created by the encapsulated
#        vs back to the outer representation

class Transform(ValueSpec):
    def __init__(self, valuespec, **kwargs):
        ValueSpec.__init__(self, **kwargs)
        self._valuespec = valuespec
        self._back = kwargs.get("back")
        self._forth = kwargs.get("forth")

    def forth(self, value):
        if self._forth:
            return self._forth(value)
        else:
            return value

    def back(self, value):
        if self._back:
            return self._back(value)
        else:
            return value

    def title(self):
        if self._title:
            return self._title
        else:
            return self._valuespec.title()

    def help(self):
        if self._help:
            return self._help
        else:
            return self._valuespec.help()

    def render_input(self, varprefix, value):
        self.classtype_info()
        self._valuespec.render_input(varprefix, self.forth(value))

    def set_focus(self, *args):
        self._valuespec.set_focus(*args)

    def canonical_value(self):
        return self.back(self._valuespec.canonical_value())

    def default_value(self):
        return self.back(self._valuespec.default_value())

    def value_to_text(self, value):
        return self._valuespec.value_to_text(self.forth(value))

    def from_html_vars(self, varprefix):
        return self.back(self._valuespec.from_html_vars(varprefix))

    def validate_datatype(self, value, varprefix):
        self._valuespec.validate_datatype(self.forth(value), varprefix)

    def validate_value(self, value, varprefix):
        self._valuespec.validate_value(self.forth(value), varprefix)
        ValueSpec.custom_validate(self, value, varprefix)

class LDAPDistinguishedName(TextUnicode):
    def __init__(self, **kwargs):
        TextUnicode.__init__(self, **kwargs)
        self.enforce_suffix = kwargs.get('enforce_suffix')

    def validate_value(self, value, varprefix):
        TextAscii.validate_value(self, value, varprefix)

        # Check whether or not the given DN is below a base DN
        if self.enforce_suffix and value and not value.lower().endswith(self.enforce_suffix.lower()):
            raise MKUserError(varprefix, _('Does not ends with "%s".') % self.enforce_suffix)
        ValueSpec.custom_validate(self, value, varprefix)


class Password(TextAscii):
    def __init__(self, **kwargs):
        self._is_stored_plain = kwargs.get("is_stored_plain", True)
        self._autocomplete = kwargs.get("autocomplete", False)

        if self._is_stored_plain:
            plain_help = _("The password entered here is stored in plain text within the "
                           "monitoring site. This usually needed because the monitoring "
                           "process needs to have access to the unencrypted password "
                           "because it needs to submit it to authenticate with remote systems. ")

            if "help" in kwargs:
                kwargs["help"] += "<br><br>" + plain_help
            else:
                kwargs["help"] = plain_help

        TextAscii.__init__(self, attrencode = True, **kwargs)

    def render_input(self, varprefix, value):
        self.classtype_info()
        if value == None:
            value = ""

        if self._label:
            html.write(self._label)
            html.nbsp()

        kwargs = {
            "size": self._size,
        }

        if self._autocomplete == False:
            kwargs["autocomplete"] = "new-password"

        html.password_input(varprefix, str(value), **kwargs)


    def password_plaintext_warning(self):
        if self._is_stored_plain:
            html.span(_("<br>Please note that Check_MK needs this password in clear"
                        "<br>text during normal operation and thus stores it unencrypted"
                        "<br>on the Check_MK server."))


    def value_to_text(self, value):
        if value == None:
            return _("none")
        else:
            return '******'



class PasswordSpec(Password):
    def __init__(self, **kwargs):
        self._hidden = kwargs.get('hidden', False)
        if self._hidden:
            kwargs["type"] = "password"
        Password.__init__(self, **kwargs)


    def render_input(self, varprefix, value):
        self.classtype_info()
        TextAscii.render_input(self, varprefix, value, hidden=self._hidden)
        if not value:
            html.icon_button("#", _(u"Randomize password"), "random",
                onclick="vs_passwordspec_randomize(this);")
        if self._hidden:
            html.icon_button("#", _(u"Show/Hide password"), "showhide",
                             onclick="vs_toggle_hidden(this);")

        self.password_plaintext_warning()




class PasswordFromStore(CascadingDropdown):
    def __init__(self, *args, **kwargs):
        kwargs["choices"] = [
            ("password", _("Password"), Password(
                allow_empty = kwargs.get("allow_empty", True),
            )),
            ("store", _("Stored password"), DropdownChoice(
                choices = self._password_choices,
                sorted = True,
                invalid_choice = "complain",
                invalid_choice_title = _("Password does not exist or using not permitted"),
                invalid_choice_error = _("The configured password has either be removed or you "
                                         "are not permitted to use this password. Please choose "
                                         "another one."),
            )),
        ]
        kwargs["orientation"] = "horizontal"

        CascadingDropdown.__init__(self, *args, **kwargs)


    def _password_choices(self):
        import wato
        return [ (ident, pw["title"]) for ident, pw
                 in wato.PasswordStore().usable_passwords().items() ]



def IndividualOrStoredPassword(*args, **kwargs):
    return Transform(
        PasswordFromStore(*args, **kwargs),
        forth = lambda v: ("password", v) if type(v) != tuple else v,
    )


class FileUpload(ValueSpec):
    def __init__(self, **kwargs):
        ValueSpec.__init__(self, **kwargs)
        self._allow_empty = kwargs.get('allow_empty', True)
        self._allowed_extensions = kwargs.get('allowed_extensions')
        self._allow_empty_content = kwargs.get('allow_empty_content', True)


    def canonical_value(self):
        if self._allow_empty:
            return None
        else:
            return ''


    def validate_value(self, value, varprefix):
        file_name, mime_type, content = value

        if not self._allow_empty and (content == '' or file_name == ''):
            raise MKUserError(varprefix, _('Please select a file.'))

        if not self._allow_empty_content and len(content) == 0:
            raise MKUserError(varprefix, _('The selected file is empty. Please select a non-empty file.')
)
        if self._allowed_extensions != None:
            matched = False
            for extension in self._allowed_extensions:
                if file_name.endswith(extension):
                    matched = True
                    break
            if not matched:
                raise MKUserError(varprefix, _("Invalid file name extension. Allowed are: %s")
                                  % ", ".join(self._allowed_extensions))

        self.custom_validate(value, varprefix)


    def render_input(self, varprefix, value):
        self.classtype_info()
        html.upload_file(varprefix)


    def from_html_vars(self, varprefix):
        # returns a triple of (filename, mime-type, content)
        return html.uploaded_file(varprefix)



class ImageUpload(FileUpload):
    def __init__(self, max_size=None, *args, **kwargs):
        self._max_size = max_size
        FileUpload.__init__(self, *args, **kwargs)


    def validate_value(self, value, varprefix):
        from PIL import Image
        from StringIO import StringIO

        file_name, mime_type, content = value

        if file_name[-4:] != '.png' \
           or mime_type != 'image/png' \
           or not content.startswith('\x89PNG'):
            raise MKUserError(varprefix, _('Please choose a PNG image.'))

        try:
            im = Image.open(StringIO(content))
        except IOError:
            raise MKUserError(varprefix, _('Please choose a valid PNG image.'))

        if self._max_size:
            w, h = im.size
            max_w, max_h = self._max_size
            if w > max_w or h > max_h:
                raise MKUserError(varprefix, _('Maximum image size: %dx%dpx') % (max_w, max_h))

        ValueSpec.custom_validate(self, value, varprefix)



class UploadOrPasteTextFile(Alternative):
    def __init__(self, **kwargs):
        file_title = kwargs.get("file_title", _("File"))
        allow_empty = kwargs.get("allow_empty", True)
        kwargs["elements"] = [
            FileUpload(
                title = _("Upload %s") % file_title,
                allow_empty = allow_empty),
            TextAreaUnicode(
                title = _("Content of %s") % file_title,
                allow_empty = allow_empty,
                cols = 80,
                rows = "auto"),
        ]

        if kwargs.get("default_mode", "text") == "upload":
            kwargs["match"] = lambda *args: 0
        else:
            kwargs["match"] = lambda *args: 1

        kwargs.setdefault("style", "dropdown")
        Alternative.__init__(self, **kwargs)


    def from_html_vars(self, varprefix):
        value = Alternative.from_html_vars(self, varprefix)
        # Convert textarea value to format of upload field
        if type(value) != tuple:
            value = (None, None, value)
        return value



class IconSelector(ValueSpec):
    _categories = [
        ('logos',   _('Logos')),
        ('parts',   _('Parts')),
        ('misc',    _('Misc')),
    ]

    def __init__(self, **kwargs):
        ValueSpec.__init__(self, **kwargs)
        self._allow_empty = kwargs.get('allow_empty', True)
        self._empty_img   = kwargs.get('emtpy_img', 'empty')

        self._exclude = [
            'trans',
            'empty',
        ]

    @classmethod
    def category_alias(cls, category_name):
        categories = dict(cls._categories)
        return dict(cls._categories).get(category_name, category_name)

    # All icons within the images/icons directory have the ident of a category
    # witten in the PNG meta data. For the default images we have done this scripted.
    # During upload of user specific icons, the meta data is added to the images.
    def available_icons(self, only_local=False):
        dirs = [
            os.path.join(cmk.paths.omd_root, "local/share/check_mk/web/htdocs/images/icons"),
        ]
        if not only_local:
            dirs.append(os.path.join(cmk.paths.omd_root, "share/check_mk/web/htdocs/images/icons"))

        valid_categories = dict(self._categories).keys()

        from PIL import Image

        #
        # Read all icons from the icon directories
        #
        icons = {}
        for dir in dirs:
            try:
                files = os.listdir(dir)
            except OSError:
                continue

            for file_name in files:
                file_path = dir + "/" + file_name
                if file_name[-4:] == '.png' and os.path.isfile(file_path):

                    # extract the category from the meta data
                    try:
                        im = Image.open(file_path)
                    except IOError, e:
                        if "%s" % e == "cannot identify image file":
                            continue # Silently skip invalid files
                        else:
                            raise

                    category = im.info.get('Comment')
                    if category not in valid_categories:
                        category = 'misc'

                    icon_name = file_name[:-4]
                    icons[icon_name] = category

        for exclude in self._exclude:
            try:
                del icons[exclude]
            except KeyError:
                pass

        return icons

    def available_icons_by_category(self, icons):
        by_cat = {}
        for icon_name, category_name in icons.items():
            by_cat.setdefault(category_name, [])
            by_cat[category_name].append(icon_name)

        icon_categories = []
        for category_name, category_alias in self._categories:
            if category_name in by_cat:
                icon_categories.append((category_name, category_alias, by_cat[category_name]))
        return icon_categories

    def render_icon(self, icon_name, onclick = '', title = '', id = ''):
        if not icon_name:
            icon_name = self._empty_img

        icon = html.render_icon(icon_name, help=title, middle=True, id=id)
        if onclick:
            icon = html.render_a(icon, href="javascript:void(0)", onclick=onclick)

        return icon

    def render_input(self, varprefix, value):
        self.classtype_info()
        if not value:
            value = self._empty_img

        html.hidden_field(varprefix + "_value", value or '', varprefix + "_value", add_var = True)

        if value:
            content = self.render_icon(value, '', _('Choose another Icon'), id = varprefix + '_img')
        else:
            content = _('Select an Icon')
        html.popup_trigger(content, varprefix + '_icon_selector', 'icon_selector',
                           url_vars = [
                                ('value',       value),
                                ('varprefix',   varprefix),
                                ('allow_empty', '1' if self._allow_empty else '0'),
                                ('back',        html.makeuri([])),
                            ])

    def render_popup_input(self, varprefix, value):
        html.open_div(class_=["icons"])

        icons = self.available_icons()
        available_icons = self.available_icons_by_category(icons)
        active_category = icons.get(value, available_icons[0][0])

        # Render tab navigation
        html.open_ul()
        for category_name, category_alias, icons in available_icons:
            html.open_li(class_="active" if active_category == category_name else None)
            # TODO: TEST
            html.a(category_alias, href="javascript:vs_iconselector_toggle(\'%s\', \'%s\')" % (varprefix, category_name),
                                   id_="%s_%s_nav" % (varprefix, category_name), class_="%s_nav" % varprefix)
            html.close_li()
        html.close_ul()

        # Now render the icons grouped by category
        empty = ['empty'] if self._allow_empty else []
        for category_name, category_alias, icons in available_icons:
            html.open_div(id_="%s_%s_container" % (varprefix, category_name),
                          class_=["%s_container" % varprefix],
                          style="display:none;" if active_category != category_name else None)

            for nr, icon in enumerate(empty + icons):
                html.write(self.render_icon(icon,
                    onclick = 'vs_iconselector_select(event, \'%s\', \'%s\')' % (varprefix, icon),
                    title = _('Choose this icon'), id = varprefix + '_i_' + icon))
            html.close_div()

        import config# FIXME: Clean this up. But how?
        if config.omd_site() and config.user.may('wato.icons'):
            back_param = '&back='+html.urlencode(html.var('back')) if html.has_var('back') else ''
            html.buttonlink('wato.py?mode=icons' + back_param, _('Manage'))

        html.close_div()

    def from_html_vars(self, varprefix):
        icon = html.var(varprefix + '_value')
        if icon == 'empty':
            return None
        else:
            return icon

    def value_to_text(self, value):
        # TODO: This is a workaround for a bug. This function needs to return str objects right now.
        return "%s" % self.render_icon(value)

    def validate_datatype(self, value, varprefix):
        if value is not None and type(value) != str:
            raise MKUserError(varprefix, _("The type is %s, but should be str") % type(value))

    def validate_value(self, value, varprefix):
        if not self._allow_empty and not value:
            raise MKUserError(varprefix, _("You need to select an icon."))

        if value and value not in self.available_icons():
            raise MKUserError(varprefix, _("The selected icon image does not exist."))


class TimeofdayRanges(Transform):
    def __init__(self, **args):
        self._count = args.get("count", 3)
        Transform.__init__(
            self,
            Tuple(
                elements = [ TimeofdayRange(allow_empty=True, allow_24_00=True) for x in range(self._count) ],
                orientation = "float",
                separator = " &nbsp; ",
            ),
            forth = lambda outter: tuple((outter + [None]*self._count)[0:self._count]),
            back = lambda inner: [ x for x in inner if x != None ],
            **args
        )


class Color(ValueSpec):
    def __init__(self, **kwargs):
        kwargs["regex"] = "#[0-9]{3,6}"
        kwargs["regex_error"] = _("The color needs to be given in hex format.")
        ValueSpec.__init__(self, **kwargs)
        self._on_change = kwargs.get("on_change")
        self._allow_empty = kwargs.get("allow_empty", True)


    def render_input(self, varprefix, value):
        self.classtype_info()
        if not value:
            value = "#FFFFFF"

        html.javascript_file("js/colorpicker.js")

        # Holds the actual value for form submission
        html.hidden_field(varprefix + "_value", value or '', varprefix + "_value", add_var = True)

        indicator = html.render_div('', id_="%s_preview" % varprefix,
                                        class_="cp-preview",
                                        style="background-color:%s" % value)

        # FIXME: Rendering with HTML class causes bug in html popup_trigger function.
        #        Reason is HTML class and the escaping.
        menu_content = "<div id=\"%s_picker\" class=\"cp-small\"></div>" % varprefix
        menu_content += "<script language=\"javascript\">" \
            "ColorPicker(document.getElementById(\"%s_picker\")," \
            "            function(hex, hsv, rgb) {" \
            "               document.getElementById(\"%s_value\").value = hex;" \
            "               document.getElementById(\"%s_preview\").style.backgroundColor = hex;" \
            "}).setHex(\"%s\");</script>" % (varprefix, varprefix, varprefix, value)

        html.popup_trigger(indicator, varprefix + '_popup',
                           menu_content=menu_content,
                           cssclass="colorpicker",
                           onclose=self._on_change)



    def from_html_vars(self, varprefix):
        color = html.var(varprefix + '_value')
        if color == '':
            return None
        else:
            return color


    def value_to_text(self, value):
        return value


    def validate_datatype(self, value, varprefix):
        if value is not None and type(value) != str:
            raise MKUserError(varprefix, _("The type is %s, but should be str") % type(value))


    def validate_value(self, value, varprefix):
        if not self._allow_empty and not value:
            raise MKUserError(varprefix, _("You need to select a color."))



class SSHKeyPair(ValueSpec):
    def __init__(self, **kwargs):
        ValueSpec.__init__(self, **kwargs)


    def render_input(self, varprefix, value):
        self.classtype_info()
        if value:
            html.write(_("Fingerprint: %s") % self.value_to_text(value))
            html.hidden_field(varprefix, self._encode_key_for_url(value), add_var=True)
        else:
            html.write(_("Key pair will be generated when you save."))


    def value_to_text(self, value):
        return self._get_key_fingerprint(value)


    def from_html_vars(self, varprefix):
        if html.has_var(varprefix):
            return self._decode_key_from_url(html.var(varprefix))
        else:
            return self._generate_ssh_key(varprefix)

    @staticmethod
    def _encode_key_for_url(value):
        return "|".join(value)


    @staticmethod
    def _decode_key_from_url(text):
        return text.split("|")


    @classmethod
    def _generate_ssh_key(cls, varprefix):
        key = RSA.generate(4096)
        private_key = key.exportKey('PEM')
        pubkey = key.publickey()
        public_key  = pubkey.exportKey('OpenSSH')
        return (private_key, public_key)


    @classmethod
    def _get_key_fingerprint(cls, value):
        private_key, public_key = value
        key = base64.b64decode(public_key.strip().split()[1].encode('ascii'))
        fp_plain = hashlib.md5(key).hexdigest()
        return ':'.join(a+b for a,b in zip(fp_plain[::2], fp_plain[1::2]))



class SchedulePeriod(CascadingDropdown):
    def __init__(self, from_end=True, **kwargs):
        if from_end:
            from_end_choice = [
                ("month_end", _("At the end of every month at day"),
                  Integer(minvalue=1, maxvalue=28, unit=_("from the end"))),
            ]
        else:
            from_end_choice = []

        CascadingDropdown.__init__(self,
            title = _("Period"),
            orientation = "horizontal",
            choices = [
                ( "day",   _("Every day"), ),
                ( "week",  _("Every week on..."),
                  Weekday(title = _("Day of the week"))),
                ( "month_begin", _("At the beginning of every month at day"),
                  Integer(minvalue=1, maxvalue=28)),
            ] + from_end_choice
        )



class CAorCAChain(UploadOrPasteTextFile):
    def __init__(self, **args):
        args.setdefault("title", _("Certificate Chain (Root / Intermediate Certificate)"))
        args.setdefault("file_title", _("CRT/PEM File"))
        UploadOrPasteTextFile.__init__(self, **args)


    def from_html_vars(self, varprefix):
        value = Alternative.from_html_vars(self, varprefix)
        if type(value) == tuple:
            value = value[2] # FileUpload sends (filename, mime-type, content)
        return value


    def validate_value(self, value, varprefix):
        try:
            self.analyse_cert(value)
        except Exception, e:
            # FIXME TODO: Cleanup this general exception catcher
            raise MKUserError(varprefix, _("Invalid certificate file"))


    def analyse_cert(self, value):
        from OpenSSL import crypto
        cert = crypto.load_certificate(crypto.FILETYPE_PEM, value)
        titles = {
            "C"  : _("Country"),
            "ST" : _("State or Province Name"),
            "L"  : _("Locality Name"),
            "O"  : _("Organization Name"),
            "CN" : _("Common Name"),
        }
        cert_info = {}
        for what, x509, title in [
            ( "issuer", cert.get_issuer(), _("Issuer") ),
            ( "subject", cert.get_subject(), _("Subject") ),
        ]:
            cert_info[what] = {}
            for key, val in x509.get_components():
                if key in titles:
                    cert_info[what][titles[key]] = val.decode("utf8")
        return cert_info


    def value_to_text(self, value):
        cert_info = self.analyse_cert(value)
        text = "<table>"
        for what, title in [
            ( "issuer", _("Issuer") ),
            ( "subject", _("Subject") ),
        ]:
            text += "<tr><td>%s:</td><td>" % title
            for title, value in sorted(cert_info[what].items()):
                text += "%s: %s<br>" % (title, value)
            text += "</tr>"
        text += "</table>"
        return text



# Move this to wato.py or valuespec.py as soon as we need this at least
# once again somewhere
def ListOfCAs(**args):
    args.setdefault("title", _("CAs to accept"))
    args.setdefault("help", _("Only accepting HTTPS connections with a server which certificate "
                 "is signed with one of the CAs that are listed here. That way it is guaranteed "
                 "that it is communicating only with the authentic update server. "
                 "If you use self signed certificates for you server then enter that certificate "
                 "here."))
    args.setdefault("add_label", _("Add new CA certificate or chain"))
    args.setdefault("empty_text", _("You need to enter at least one CA. Otherwise no SSL connection can be made."))
    args.setdefault("allow_empty", False)
    return ListOf(
        CAorCAChain(),
        movable = False,
        **args
    )
