#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# FIXME: Cleanups
# - Consolidate ListChoice and DualListChoice to use the same class
#   and rename to better name
# - Consolidate ListOf and ListOfStrings
# - Checkbox
#   -> rename to Boolean
#   -> Add alternative rendering "dropdown"
# - Some reordering, e.g. move specific valuspecs / factories to the bottom of
#   the file
# - Refactor "orientation" argument to use some Enum, similar to Labels.World

from __future__ import division
import abc
import base64
from enum import Enum
import hashlib
import ipaddress
import json
import logging
import math
import numbers
import os
import re
import io
import socket
import sre_constants
import sys
import time
from typing import (  # pylint: disable=unused-import
    Any, Callable, Dict, Generic, List, Optional as _Optional, Pattern, Set, SupportsFloat, Text,
    Tuple as _Tuple, Type, TypeVar, Union, Sequence,
)

if sys.version_info[:2] >= (3, 0) and sys.version_info[:2] <= (3, 7):
    from typing_extensions import Protocol
else:
    from typing import Protocol  # pylint: disable=no-name-in-module

import uuid
from PIL import Image  # type: ignore[import]

try:
    # Python has a totally braindead history of changes in this area:
    #   * In the dark ages: Hmmm, one can't subclass dict, so we have to provide UserDict.
    #   * Python 2.2: Well, now we can subclass dict, but let's keep UserDict.
    #   * Python 2.3: Actually, DictMixin might often be a better idea.
    #   * Python 2.6: It is recommended to use collections.MutableMapping instead of DictMixin.
    #   * Python 3.0: UserDict is gone...
    #   * Python 3.3: Let's just move the ABCs from collections to collections.abc, keeping the old stuff for now.
    #   * Python 3.8: To *really* annoy people, let's nuke the ABCs from collection! >:-)
    from collections.abc import MutableMapping  # type: ignore[import]
except ImportError:
    from collections import MutableMapping

import six
from Cryptodome.PublicKey import RSA

import cmk.utils.log
import cmk.utils.paths
import cmk.utils.defines as defines
from cmk.utils.encoding import ensure_unicode
from cmk.utils.type_defs import Seconds  # pylint: disable=unused-import

import cmk.gui.forms as forms
import cmk.gui.utils as utils
import cmk.gui.escaping as escaping
from cmk.gui.i18n import _
from cmk.gui.pages import page_registry, Page, AjaxPage
from cmk.gui.globals import html
from cmk.gui.htmllib import HTML
from cmk.gui.htmllib import Choices  # pylint: disable=unused-import
from cmk.gui.exceptions import MKUserError, MKGeneralException

import livestatus

seconds_per_day = 86400

# Some arbitrary object for checking whether or not default_value was set
DEF_VALUE = object()

ValueSpecValidateFunc = Callable[[Any, str], None]
ValueSpecHelp = Union[Text, HTML, Callable[[], Union[Text, HTML]]]

C = TypeVar('C', bound='Comparable')


# Look, mom, we finally have Haskell type classes! :-D Naive version requiring
# only <, hopefully some similar class will make it into typing soon...
class Comparable(Protocol):
    @abc.abstractmethod
    def __lt__(self, other):
        # type: (C, C) -> bool
        pass


# NOTE: Bounds are inclusive!
class Bounds(Generic[C]):
    def __init__(self, lower, upper):
        # type: (_Optional[C], _Optional[C]) -> None
        super(Bounds, self).__init__()
        self.__lower = lower
        self.__upper = upper

    def lower(self, default):
        # type: (C) -> C
        return default if self.__lower is None else self.__lower

    def validate_value(self, value, varprefix):
        # type: (C, str) -> None
        if self.__lower is not None and value < self.__lower:
            raise MKUserError(
                varprefix,
                _("%s is too low. The minimum allowed value is %s.") % (value, self.__lower))
        if self.__upper is not None and self.__upper < value:
            raise MKUserError(
                varprefix,
                _("%s is too high. The maximum allowed value is %s.") % (value, self.__upper))


class ValueSpec(object):
    """Abstract base class of all value declaration classes"""

    # TODO: Remove **kwargs once all valuespecs have been changed
    # TODO: Cleanup help argument redefined-builtin
    def __init__(  # pylint: disable=redefined-builtin
        self,
        title=None,  # type: _Optional[Text]
        help=None,  # type: _Optional[ValueSpecHelp]
        default_value=DEF_VALUE,  # type: Any
        validate=None,  # type: _Optional[ValueSpecValidateFunc]
        **kwargs):
        super(ValueSpec, self).__init__()
        self._title = title
        self._help = help
        if default_value is not DEF_VALUE:
            self._default_value = default_value
        self._validate = validate

    def title(self):
        # type: () -> _Optional[Text]
        return self._title

    def help(self):
        # type: () -> Union[Text, HTML, None]
        if callable(self._help):
            return self._help()

        if isinstance(self._help, HTML):
            return self._help

        if self._help is None:
            return None

        assert isinstance(self._help, six.string_types)
        return ensure_unicode(self._help)

    def render_input(self, varprefix, value):
        # type: (str, Any) -> None
        """Create HTML-form elements that represent a given
        value and let the user edit that value

        The varprefix is prepended to the HTML variable names and is needed in
        order to make the variable unique in case that another Value of the same
        type is being used as well.  The function may assume that the type of the
        value is valid."""
        pass

    def set_focus(self, varprefix):
        # type: (str) -> None
        """Sets the input focus (cursor) into the most promiment field of the
        HTML code previously rendered with render_input()"""
        html.set_focus(varprefix)

    def canonical_value(self):
        # type: () -> Any
        """Create a canonical, minimal, default value that matches the datatype
        of the value specification and fulfills also data validation."""
        return None

    def default_value(self):
        # type: () -> Any
        """Return a default value for this variable

        This is optional and only used in the value editor for same cases where
        the default value is known."""
        try:
            if callable(self._default_value):
                return self._default_value()
            return self._default_value
        except Exception:
            return self.canonical_value()

    # TODO: Rename to value_to_html?
    def value_to_text(self, value):
        # type: (Any) -> Text
        """Creates a text-representation of the value that can be
        used in tables and other contextes

        It is to be read by the user and need not to be parsable.  The function
        may assume that the type of the value is valid.

        In the current implementation this function is only used to render the
        object for html code. So it is allowed to add html code for better
        layout in the GUI."""
        return repr(value)

    def value_to_json(self, value):
        raise NotImplementedError()

    def value_from_json(self, json_value):
        raise NotImplementedError()

    def from_html_vars(self, varprefix):
        # type: (str) -> Any
        """Create a value from the current settings of the HTML variables

        This function must also check the validity and may raise a MKUserError
        in case of invalid set variables."""
        return None

    def validate_value(self, value, varprefix):
        # type: (Any, str) -> None
        """Check if a given value is a valid structure for the current valuespec

        The validation is done in 3 phases:

        1. validate_datatype : Ensure the python data type is as expected
        2. _validate_value   : Valuespec type specific validations
        3. self._validate    : instance specific validations
        """
        # TODO: Would be really good to enable this to prevent unexpected data
        # types being written to the configuration. For the moment we can not
        # enable this because of the Web API: When using JSON as request_format
        # the JSON modules decodes all strings to unicode strings which are not
        # accepted by some attribute valuespecs which base on e.g. TextAscii.
        # This should be solved during Python3 transformation where we will
        # finally make a huge switch to unicode strings in many places.
        # TODO: Cleanup all external direct calls to validate_datatype() once this is
        #       being enabled.
        #self.validate_datatype(value, varprefix)
        self._validate_value(value, varprefix)
        if self._validate:
            self._validate(value, varprefix)

    def validate_datatype(self, value, varprefix):
        # type: (Any, str) -> None
        """Check if a given value matches the datatype of described by this class."""
        pass

    def _validate_value(self, value, varprefix):
        # type: (Any, str) -> None
        """Override this method to implement custom validation functions for sub-valuespec types

        This function should assume that the data type is valid (either because
        it has been returned by from_html_vars() or because it has been checked
        with validate_datatype())."""
        pass


class FixedValue(ValueSpec):
    """A fixed non-editable value, e.g. to be used in 'Alternative'"""
    def __init__(  # pylint: disable=redefined-builtin
        self,
        value,  # type: Any
        totext=None,  # type: Text
        title=None,  # type: _Optional[Text]
        help=None,  # type: _Optional[ValueSpecHelp]
        default_value=DEF_VALUE,  # type: Any
        validate=None,  # type: _Optional[ValueSpecValidateFunc]
    ):
        super(FixedValue, self).__init__(title=title,
                                         help=help,
                                         default_value=default_value,
                                         validate=validate)
        self._value = value
        self._totext = totext

    def canonical_value(self):
        # type: () -> Any
        return self._value

    def render_input(self, varprefix, value):
        # type: (str, Any) -> None
        html.write(self.value_to_text(value))

    def value_to_text(self, value):
        # type: (Any) -> Text
        if self._totext is not None:
            return self._totext
        if isinstance(value, six.text_type):
            return value
        return ensure_unicode(value)

    def from_html_vars(self, varprefix):
        # type: (str) -> Any
        return self._value

    def validate_datatype(self, value, varprefix):
        # type: (Any, str) -> None
        if not self._value == value:
            raise MKUserError(varprefix,
                              _("Invalid value, must be '%r' but is '%r'") % (self._value, value))


class Age(ValueSpec):
    """Time in seconds"""
    def __init__(  # pylint: disable=redefined-builtin
        self,
        label=None,  # type: _Optional[Text]
        minvalue=None,  # type: _Optional[Seconds]
        maxvalue=None,  # type: _Optional[Seconds]
        display=None,  # type: _Optional[List[str]]
        title=None,  # type: _Optional[Text]
        help=None,  # type: _Optional[ValueSpecHelp]
        default_value=DEF_VALUE,  # type: Any
        validate=None,  # type: _Optional[ValueSpecValidateFunc]
        cssclass=None,  # type: _Optional[str]
    ):
        super(Age, self).__init__(title=title,
                                  help=help,
                                  default_value=default_value,
                                  validate=validate)
        self._label = label
        self._bounds = Bounds[Seconds](minvalue, maxvalue)
        self._display = display if display is not None else \
            ["days", "hours", "minutes", "seconds"]
        self._cssclass = cssclass

    def canonical_value(self):
        # type: () -> Seconds
        return self._bounds.lower(0)

    def render_input(self, varprefix, value):
        # type: (str, Seconds) -> None
        days, rest = divmod(value, 60 * 60 * 24)
        hours, rest = divmod(rest, 60 * 60)
        minutes, seconds = divmod(rest, 60)

        html.open_div(class_=["vs_age", self._cssclass])
        if self._label:
            html.write(self._label + " ")

        takeover = 0
        for uid, title, val, tkovr_fac in [("days", _("days"), days, 24),
                                           ("hours", _("hours"), hours, 60),
                                           ("minutes", _("mins"), minutes, 60),
                                           ("seconds", _("secs"), seconds, 60)]:
            if uid in self._display:
                val += takeover
                takeover = 0
                html.text_input(varprefix + "_" + uid,
                                default_value=str(val),
                                size=4,
                                cssclass="number")
                html.write(" %s " % title)
            else:
                takeover = (takeover + val) * tkovr_fac
        html.close_div()

    def from_html_vars(self, varprefix):
        # type: (str) -> Seconds
        # TODO: Validate for correct numbers!
        return (html.request.get_integer_input_mandatory(varprefix + '_days', 0) * 3600 * 24 +
                html.request.get_integer_input_mandatory(varprefix + '_hours', 0) * 3600 +
                html.request.get_integer_input_mandatory(varprefix + '_minutes', 0) * 60 +
                html.request.get_integer_input_mandatory(varprefix + '_seconds', 0))

    def value_to_text(self, value):
        # type: (Seconds) -> Text
        days, rest = divmod(value, 60 * 60 * 24)
        hours, rest = divmod(rest, 60 * 60)
        minutes, seconds = divmod(rest, 60)
        parts = []
        for title, count in [
            (_("days"), days),
            (_("hours"), hours),
            (_("minutes"), minutes),
            (_("seconds"), seconds),
        ]:
            if count:
                parts.append("%d %s" % (count, title))

        if parts:
            return " ".join(parts)
        return _("no time")

    def value_to_json(self, value):
        return value

    def value_from_json(self, json_value):
        return json_value

    def validate_datatype(self, value, varprefix):
        # type: (Seconds, str) -> None
        if not isinstance(value, int):
            raise MKUserError(
                varprefix,
                _("The value %r has type %s, but must be of type int") % (value, _type_name(value)))

    def _validate_value(self, value, varprefix):
        # type: (Seconds, str) -> None
        self._bounds.validate_value(value, varprefix)


class NumericRenderer(object):
    def __init__(
        self,
        size,  # type: _Optional[int]
        maxvalue,  # type: _Optional[SupportsFloat]
        label,  # type: _Optional[Text]
        unit,  # type: Text
        thousand_sep,  # type: _Optional[Text]
        align,  # type: str
    ):
        super(NumericRenderer, self).__init__()
        if size is not None:
            self._size = size
        elif maxvalue is not None:
            self._size = (4 if isinstance(maxvalue, float) else 1) + int(math.log10(maxvalue))
        else:
            self._size = 5
        self._label = label
        self._unit = unit
        self._thousand_sep = thousand_sep
        self._align = align

    def text_input(self, varprefix, text):
        # type: (str, Text) -> None
        html.text_input(varprefix,
                        default_value=text,
                        cssclass="number",
                        size=self._size,
                        style="text-align: right;" if self._align == "right" else "")

    def render_input(self, varprefix, text):
        # type: (str, Text) -> None
        if self._label:
            html.write(self._label)
            html.nbsp()
        self.text_input(varprefix, text)
        if self._unit:
            html.nbsp()
            html.write(self._unit)

    def format_text(self, text):
        # type: (Text) -> Text
        if self._thousand_sep:
            sepped = text[:((len(text) + 3 - 1) % 3) + 1]
            for pos in range(len(sepped), len(text), 3):
                sepped += self._thousand_sep + text[pos:pos + 3]
            text = sepped
        if self._unit:
            text += "&nbsp;" + self._unit
        return text


class Integer(ValueSpec):
    """Editor for a single integer"""
    def __init__(  # pylint: disable=redefined-builtin
        self,
        size=None,  # type: _Optional[int]
        minvalue=None,  # type: _Optional[int]
        maxvalue=None,  # type: _Optional[int]
        label=None,  # type: _Optional[Text]
        unit="",  # type: Text
        thousand_sep=None,  # type: _Optional[Text]
        display_format="%d",  # type: Text
        align="left",  # type: str
        # ValueSpec
        title=None,  # type: _Optional[Text]
        help=None,  # type: _Optional[ValueSpecHelp]
        default_value=DEF_VALUE,  # type: Any
        validate=None,  # type: _Optional[ValueSpecValidateFunc]
    ):
        super(Integer, self).__init__(title=title,
                                      help=help,
                                      default_value=default_value,
                                      validate=validate)
        self._bounds = Bounds[int](minvalue, maxvalue)
        self._renderer = NumericRenderer(size=size,
                                         maxvalue=maxvalue,
                                         label=label,
                                         unit=unit,
                                         thousand_sep=thousand_sep,
                                         align=align)
        self._display_format = display_format

    def canonical_value(self):
        # type: () -> int
        return self._bounds.lower(0)

    def render_input(self, varprefix, value):
        # type: (str, int) -> None
        self._renderer.render_input(varprefix, self._render_value(value))

    def _render_value(self, value):
        # type: (int) -> Text
        return self._display_format % utils.saveint(value)

    def from_html_vars(self, varprefix):
        # type: (str) -> int
        return html.request.get_integer_input_mandatory(varprefix)

    def value_to_text(self, value):
        # type: (int) -> Text
        return self._renderer.format_text(self._render_value(value))

    def validate_datatype(self, value, varprefix):
        # type: (int, str) -> None
        if isinstance(value, numbers.Integral):
            return
        raise MKUserError(
            varprefix,
            _("The value %r has the wrong type %s, but must be of type int") %
            (value, _type_name(value)))

    def _validate_value(self, value, varprefix):
        # type: (int, str) -> None
        self._bounds.validate_value(value, varprefix)


class Filesize(Integer):
    """Filesize in Byte, KByte, MByte, Gigabyte, Terabyte"""
    _names = [u'Byte', u'KByte', u'MByte', u'GByte', u'TByte']

    def get_exponent(self, value):
        # type: (int) -> _Tuple[int, int]
        for exp, count in ((exp, 1024**exp) for exp in reversed(range(len(self._names)))):
            if value == 0:
                return 0, 0
            if value % count == 0:
                return exp, int(value / count)  # fixed: true-division
        raise ValueError("Invalid value: %r" % value)

    def render_input(self, varprefix, value):
        # type: (str, int) -> None
        exp, count = self.get_exponent(value)
        self._renderer.text_input(varprefix + '_size', str(count))
        html.nbsp()
        choices = [(str(nr), name) for (nr, name) in enumerate(self._names)]  # type: Choices
        html.dropdown(varprefix + '_unit', choices, deflt=str(exp))

    def from_html_vars(self, varprefix):
        # type: (str) -> int
        try:
            return html.request.get_integer_input_mandatory(varprefix + '_size') * (
                1024**html.request.get_integer_input_mandatory(varprefix + '_unit'))
        except Exception:
            raise MKUserError(varprefix + '_size', _("Please enter a valid integer number"))

    # TODO: Cleanup this hierarchy problem
    def value_to_text(self, value):  # type: ignore[override]
        # type: (int) -> Text
        exp, count = self.get_exponent(value)
        return "%s %s" % (count, self._names[exp])


class TextAscii(ValueSpec):
    """Editor for a line of text"""

    # TODO: Cleanup attrencode attribute
    def __init__(  # pylint: disable=redefined-builtin
        self,
        label=None,  # type: _Optional[Text]
        size=25,  # type: Union[int, str]
        try_max_width=False,  # type: bool
        cssclass="text",  # type: str
        strip=True,  # type: bool
        attrencode=True,  # type: bool
        allow_empty=True,  # type: bool
        empty_text="",  # type: Text
        read_only=False,  # type: bool
        forbidden_chars="",  # type: Text
        regex=None,  # type: Union[None, str, Pattern[str]]
        regex_error=None,  # type: _Optional[Text]
        minlen=None,  # type: _Optional[int]
        onkeyup=None,  # type: _Optional[Text]
        autocomplete=True,  # type: bool
        hidden=False,  # type: bool
        # ValueSpec
        title=None,  # type: _Optional[Text]
        help=None,  # type: _Optional[ValueSpecHelp]
        default_value=DEF_VALUE,  # type: Any
        validate=None,  # type: _Optional[ValueSpecValidateFunc]
    ):
        super(TextAscii, self).__init__(title=title,
                                        help=help,
                                        default_value=default_value,
                                        validate=validate)
        self._label = label
        self._size = size  # also possible: "max"
        self._try_max_width = try_max_width  # If set, uses calc(100%-10px)
        self._cssclass = cssclass
        self._strip = strip
        self._attrencode = attrencode
        self._allow_empty = allow_empty
        self._empty_text = empty_text
        self._read_only = read_only
        self._forbidden_chars = forbidden_chars
        if isinstance(regex, str):
            self._regex = re.compile(regex)  # type: _Optional[Pattern[str]]
        else:
            self._regex = regex
        self._regex_error = regex_error if regex_error is not None else \
            _("Your input does not match the required format.")
        self._minlen = minlen
        self._onkeyup = onkeyup
        self._autocomplete = autocomplete
        self._hidden = hidden

    def canonical_value(self):
        # type: () -> str
        return ""

    def render_input(self, varprefix, value):
        # type: (str, _Optional[str]) -> None
        if self._label:
            html.write(self._label)
            html.nbsp()

        html.text_input(
            varprefix,
            default_value="%s" % value if value is not None else "",
            size=self._size,
            try_max_width=self._try_max_width,
            read_only=self._read_only,
            cssclass=self._cssclass,
            type_="password" if self._hidden else "text",
            autocomplete="off" if not self._autocomplete else None,
            onkeyup=self._onkeyup if self._onkeyup else None,
        )

    def value_to_text(self, value):
        # type: (str) -> Text
        if not value:
            return self._empty_text

        if self._attrencode:
            return escaping.escape_attribute(value)
        return ensure_unicode(value)

    def from_html_vars(self, varprefix):
        # type: (str) -> str
        value = html.request.get_str_input_mandatory(varprefix, "")

        if self._strip and value:
            value = value.strip()

        return value

    def validate_datatype(self, value, varprefix):
        # type: (str, str) -> None
        if not isinstance(value, str):
            raise MKUserError(
                varprefix,
                _("The value must be of type str, but it has type %s") % _type_name(value))

    def _validate_value(self, value, varprefix):
        # type: (str, str) -> None
        try:
            six.text_type(value)
        except UnicodeDecodeError:
            raise MKUserError(varprefix, _("Non-ASCII characters are not allowed here."))

        if self._forbidden_chars:
            for c in self._forbidden_chars:
                if c in value:
                    raise MKUserError(varprefix,
                                      _("The character <tt>%s</tt> is not allowed here.") % c)

        if not self._allow_empty and value.strip() == "":
            raise MKUserError(varprefix, _("An empty value is not allowed here."))
        if value and self._regex:
            if not self._regex.match(value):
                raise MKUserError(varprefix, self._regex_error)

        if self._minlen is not None and len(value) < self._minlen:
            raise MKUserError(varprefix,
                              _("You need to provide at least %d characters.") % self._minlen)


class UUID(TextAscii):
    """Documentation for UUID

    """
    def from_html_vars(self, varprefix):
        # type: (str) -> str
        value = html.request.get_str_input_mandatory(varprefix, "")
        if not value:
            value = str(uuid.uuid4())
        return value

    def render_input(self, varprefix, value):
        # type: (str, _Optional[str]) -> None
        html.hidden_field(varprefix, value, add_var=True)


class TextUnicode(TextAscii):
    # TODO: Once we switched to Python 3 we can merge the unicode and non unicode class
    def from_html_vars(self, varprefix):  # type: ignore[override]
        # type: (str) -> Text
        return html.request.get_unicode_input_mandatory(varprefix, "").strip()

    def validate_datatype(self, value, varprefix):
        # type: (Text, str) -> None
        if not isinstance(value, six.string_types):
            raise MKUserError(
                varprefix,
                _("The value must be of type str or unicode, but it has type %s") %
                _type_name(value))


# TODO: Cleanup kwargs
def ID(**kwargs):
    """Internal ID as used in many places (for contact names, group name, an so on)"""
    return TextAscii(regex=re.compile('^[a-zA-Z_][-a-zA-Z0-9_]*$'),
                     regex_error=_("An identifier must only consist of letters, digits, dash and "
                                   "underscore and it must start with a letter or underscore."),
                     **kwargs)


# TODO: Cleanup kwargs
def UnicodeID(**kwargs):
    """Same as the ID class, but allowing unicode objects"""
    return TextUnicode(regex=re.compile(r'^[\w][-\w0-9_]*$', re.UNICODE),
                       regex_error=_("An identifier must only consist of letters, digits, dash and "
                                     "underscore and it must start with a letter or underscore."),
                       **kwargs)


# TODO: Cleanup kwargs
def UserID(**kwargs):
    return TextUnicode(regex=re.compile(r'^[\w][-\w0-9_\.@]*$', re.UNICODE),
                       regex_error=_(
                           "An identifier must only consist of letters, digits, dash, dot, "
                           "at and underscore. But it must start with a letter or underscore."),
                       **kwargs)


class RegExp(TextAscii):
    infix = "infix"
    prefix = "prefix"
    complete = "complete"

    def __init__(  # pylint: disable=redefined-builtin
        self,
        mode,  # type: str
        case_sensitive=True,  # type: bool
        mingroups=0,  # type: int
        maxgroups=None,  # type: _Optional[int]
        # TextAscii
        label=None,  # type: _Optional[Text]
        size=25,  # type: Union[int, str]
        try_max_width=False,  # type: bool
        cssclass="text",  # type: str
        strip=True,  # type: bool
        attrencode=True,  # type: bool
        allow_empty=True,  # type: bool
        empty_text="",  # type: Text
        read_only=False,  # type: bool
        forbidden_chars="",  # type: Text
        regex=None,  # type: Union[None, str, Pattern[str]]
        regex_error=None,  # type: _Optional[Text]
        minlen=None,  # type: _Optional[int]
        onkeyup=None,  # type: _Optional[Text]
        autocomplete=True,  # type: bool
        hidden=False,  # type: bool
        # From ValueSpec
        title=None,  # type: _Optional[Text]
        help=None,  # type: _Optional[ValueSpecHelp]
        default_value=DEF_VALUE,  # type: Any
        validate=None,  # type: _Optional[ValueSpecValidateFunc]
    ):
        super(RegExp, self).__init__(
            label=label,
            size=size,
            try_max_width=try_max_width,
            cssclass=self._css_classes(case_sensitive, mode),
            strip=strip,
            attrencode=attrencode,
            allow_empty=allow_empty,
            empty_text=empty_text,
            read_only=read_only,
            forbidden_chars=forbidden_chars,
            regex=regex,
            regex_error=regex_error,
            minlen=minlen,
            onkeyup=onkeyup,
            autocomplete=autocomplete,
            hidden=hidden,
            title=title,
            help=help,
            default_value=default_value,
            validate=validate,
        )

        self._mode = mode
        self._case_sensitive = case_sensitive
        self._mingroups = mingroups
        self._maxgroups = maxgroups

    def help(self):
        # type: () -> Union[Text, HTML, None]
        help_text = []  # type: List[Union[Text, HTML]]

        default_help_text = super(RegExp, self).help()
        if default_help_text is not None:
            help_text.append(default_help_text + "<br><br>")

        help_text.append(_("The text entered here is handled as a regular expression pattern."))

        if self._mode == RegExp.infix:
            help_text.append(
                _("The pattern is applied as infix search. Add a leading <tt>^</tt> "
                  "to make it match from the beginning and/or a tailing <tt>$</tt> "
                  "to match till the end of the text."))
        elif self._mode == RegExp.prefix:
            help_text.append(
                _("The pattern is matched from the beginning. Add a tailing "
                  "<tt>$</tt> to change it to a whole text match."))
        elif self._mode == RegExp.complete:
            help_text.append(
                _("The pattern is matching the whole text. You can add <tt>.*</tt> "
                  "in front or at the end of your pattern to make it either a prefix "
                  "or infix search."))

        if self._case_sensitive is True:
            help_text.append(_("The match is performed case sensitive."))
        elif self._case_sensitive is False:
            help_text.append(_("The match is performed case insensitive."))

        help_text.append(
            _("Read more about [cms_regexes|regular expression matching in Checkmk] in our user manual."
             ))

        return u" ".join(u"%s" % h for h in help_text)

    def _css_classes(self, case_sensitive, mode):
        classes = ["text", "regexp"]

        if case_sensitive is True:
            classes.append("case_sensitive")
        elif case_sensitive is False:
            classes.append("case_insensitive")

        if mode is not None:
            classes.append(mode)

        return " ".join(classes)

    def _validate_value(self, value, varprefix):
        super(RegExp, self)._validate_value(value, varprefix)

        # Check if the string is a valid regex
        try:
            compiled = re.compile(value)
        except sre_constants.error as e:
            raise MKUserError(varprefix, _('Invalid regular expression: %s') % e)

        if compiled.groups < self._mingroups:
            raise MKUserError(
                varprefix,
                _("Your regular expression containes <b>%d</b> groups. "
                  "You need at least <b>%d</b> groups.") % (compiled.groups, self._mingroups))
        if self._maxgroups is not None and compiled.groups > self._maxgroups:
            raise MKUserError(
                varprefix,
                _("Your regular expression containes <b>%d</b> groups. "
                  "It must have at most <b>%d</b> groups.") % (compiled.groups, self._maxgroups))


# TODO: Cleanup this multiple inheritance
class RegExpUnicode(TextUnicode, RegExp):
    pass


class EmailAddress(TextUnicode):
    def __init__(  # pylint: disable=redefined-builtin
        self,
        make_clickable=False,  # type: bool
        # TextAscii
        label=None,  # type: _Optional[Text]
        size=40,  # type: Union[int, str]
        try_max_width=False,  # type: bool
        cssclass="text",  # type: str
        strip=True,  # type: bool
        attrencode=True,  # type: bool
        allow_empty=True,  # type: bool
        empty_text="",  # type: Text
        read_only=False,  # type: bool
        forbidden_chars="",  # type: Text
        regex_error=None,  # type: _Optional[Text]
        minlen=None,  # type: _Optional[int]
        onkeyup=None,  # type: _Optional[Text]
        autocomplete=True,  # type: bool
        hidden=False,  # type: bool
        # From ValueSpec
        title=None,  # type: _Optional[Text]
        help=None,  # type: _Optional[ValueSpecHelp]
        default_value=DEF_VALUE,  # type: Any
        validate=None,  # type: _Optional[ValueSpecValidateFunc]
    ):
        super(EmailAddress, self).__init__(
            label=label,
            size=size,
            try_max_width=try_max_width,
            cssclass=cssclass,
            strip=strip,
            attrencode=attrencode,
            allow_empty=allow_empty,
            empty_text=empty_text,
            read_only=read_only,
            forbidden_chars=forbidden_chars,
            # According to RFC5322 an email address is defined as:
            #     address = name-addr / addr-spec / group
            # We only allow the dot-atom of addr-spec here:
            #     addr-spec = (dot-atom / quoted-string / obs-local-part) "@" domain
            #     dot-atom = [CFWS] 1*atext *("." 1*atext) [CFWS]
            #     atext = ALPHA / DIGIT / "!" / "#" /  ; Printable US-ASCII
            #             "$" / "%" / "&" / "'"        ;  characters not including
            #             "&" / "'" / "*" / "+"        ;  specials. Used for atoms.
            #             "-" / "/" / "=" / "?"
            #             "^" / "_" / "`" / "{"
            #             "|" / "}" / "~"
            # with the additional extension of atext to the addr-spec as specified
            # by RFC6531:
            #     atext   =/  UTF8-non-ascii
            # Furthermore we do not allow comments inside CFWS and any leading or
            # trailing whitespace in the address is removed.
            #
            # The domain part of addr-spec is defined as:
            #     domain = dot-atom / domain-literal / obs-domain
            # We only allow dot-atom with a restricted character of [A-Z0-9.-] and a
            # length of 2-24 for the top level domain here. Although top level domains
            # may be longer the longest top level domain currently in use is 24
            # characters wide. Check this out with:
            #     wget -qO - http://data.iana.org/TLD/tlds-alpha-by-domain.txt | tail -n+2 | wc -L
            #
            # Note that the current regex allows multiple subsequent "." which are
            # not allowed by RFC5322.
            regex=re.compile(r"^[\w.!#$%&'*+-=?^`{|}~]+@(localhost|[\w.-]+\.[\w]{2,24})$",
                             re.I | re.UNICODE),
            regex_error=regex_error,
            minlen=minlen,
            onkeyup=onkeyup,
            autocomplete=autocomplete,
            hidden=hidden,
            title=title,
            help=help,
            default_value=default_value,
            validate=validate,
        )
        self._make_clickable = make_clickable

    def value_to_text(self, value):
        # type: (str) -> Text
        if not value:
            return super(EmailAddress, self).value_to_text(value)
        if self._make_clickable:
            # TODO: This is a workaround for a bug. This function needs to return str objects right now.
            return "%s" % html.render_a(HTML(value), href="mailto:%s" % value)
        return value


def IPNetwork(  # pylint: disable=redefined-builtin
    ip_class=None,  # type: Union[Type[ipaddress.IPv4Address], Type[ipaddress.IPv6Address]]
    # TextAscii
    allow_empty=True,  # type: bool
    size=34,  # type: Union[int, str]
    # From ValueSpec
    title=None,  # type: _Optional[Text]
    help=None,  # type: _Optional[ValueSpecHelp]
    default_value=DEF_VALUE,  # type: Any
):
    # type: (...) -> TextAscii
    """Same as IPv4Network, but allowing both IPv4 and IPv6"""
    if ip_class is None:
        ip_class = ipaddress.IPv4Address

    def _validate_value(value, varprefix):
        # type: (str, str) -> None

        this_ip_class = ipaddress.IPv4Address if ip_class is None else ip_class
        try:
            this_ip_class(ensure_unicode(value))
        except ValueError as e:
            raise MKUserError(varprefix, _("Invalid address: %s") % e)

    return TextAscii(
        validate=_validate_value,
        allow_empty=allow_empty,
        size=size,
        title=title,
        help=help,
        default_value=default_value,
    )


def IPv4Network(  # pylint: disable=redefined-builtin
    title=None,  # type: _Optional[Text]
    help=None  # type: _Optional[ValueSpecHelp]
):
    # type: (...) -> TextAscii
    """Network as used in routing configuration, such as '10.0.0.0/8' or '192.168.56.1'"""
    return IPNetwork(ip_class=ipaddress.IPv4Interface, size=18, title=title, help=help)


def IPv4Address(  # pylint: disable=redefined-builtin
    # TextAscii
    allow_empty=True,  # type: bool
    # From ValueSpec
    title=None,  # type: _Optional[Text]
    help=None,  # type: _Optional[ValueSpecHelp]
    default_value=DEF_VALUE,  # type: Any
):
    # type: (...) -> TextAscii
    return IPNetwork(
        ip_class=ipaddress.IPv4Address,
        size=16,
        title=title,
        help=help,
        default_value=default_value,
        allow_empty=allow_empty,
    )


class TextAsciiAutocomplete(TextAscii):
    ident = ""

    def __init__(  # pylint: disable=redefined-builtin
        self,
        completion_ident,  # type: Text
        completion_params,  # type: Dict[Text, Any]
        # TextAscii
        label=None,  # type: _Optional[Text]
        size=40,  # type: Union[int, str]
        try_max_width=False,  # type: bool
        cssclass="text",  # type: str
        strip=True,  # type: bool
        attrencode=True,  # type: bool
        allow_empty=True,  # type: bool
        empty_text="",  # type: Text
        read_only=False,  # type: bool
        forbidden_chars="",  # type: Text
        regex=None,  # type: Union[None, str, Pattern[str]]
        regex_error=None,  # type: _Optional[Text]
        minlen=None,  # type: _Optional[int]
        onkeyup=None,  # type: _Optional[Text]
        hidden=False,  # type: bool
        # From ValueSpec
        title=None,  # type: _Optional[Text]
        help=None,  # type: _Optional[ValueSpecHelp]
        default_value=DEF_VALUE,  # type: Any
        validate=None,  # type: _Optional[ValueSpecValidateFunc]
    ):
        onkeyup = "cmk.valuespecs.autocomplete(this, %s, %s, %s);%s" % \
                            (json.dumps(completion_ident),
                             json.dumps(completion_params),
                             json.dumps(onkeyup), onkeyup)
        super(TextAsciiAutocomplete, self).__init__(
            label=label,
            size=size,
            try_max_width=try_max_width,
            cssclass=cssclass,
            strip=strip,
            attrencode=attrencode,
            allow_empty=allow_empty,
            empty_text=empty_text,
            read_only=read_only,
            forbidden_chars=forbidden_chars,
            regex=regex,
            regex_error=regex_error,
            minlen=minlen,
            onkeyup=onkeyup,
            autocomplete=False,
            hidden=hidden,
            title=title,
            help=help,
            default_value=default_value,
            validate=validate,
        )

    @classmethod
    def idents(cls):
        # type: () -> Dict[str, Type[TextAsciiAutocomplete]]
        idents = {}
        for type_class in cls.__subclasses__():
            idents[type_class.ident] = type_class
        return idents

    @classmethod
    def ajax_handler(cls):
        # type: () -> None
        ident = html.request.var("ident")
        if not ident:
            raise MKUserError("ident", _("You need to set the \"%s\" parameter.") % "ident")

        if ident not in cls.idents():
            raise MKUserError("ident", _("Invalid ident: %s") % ident)

        raw_params = html.request.var("params")
        if not raw_params:
            raise MKUserError("params", _("You need to set the \"%s\" parameter.") % "params")

        try:
            params = json.loads(raw_params)
        except ValueError as e:  # Python 3: json.JSONDecodeError
            raise MKUserError("params", _("Invalid parameters: %s") % e)

        value = html.request.var("value")
        if value is None:
            raise MKUserError("params", _("You need to set the \"%s\" parameter.") % "value")

        result_data = cls.idents()[ident].autocomplete_choices(value, params)

        # Check for correct result_data format
        assert isinstance(result_data, list)
        if result_data:
            assert isinstance(result_data[0], (list, tuple))
            assert len(result_data[0]) == 2

        html.write(json.dumps(result_data))

    #@abc.abstractclassmethod
    @classmethod
    def autocomplete_choices(cls, value, params):
        # type: (str, Dict) -> Choices
        raise NotImplementedError()


# TODO: Cleanup kwargs
class MonitoredHostname(TextAsciiAutocomplete):
    """Hostname input with dropdown completion

    Renders an input field for entering a host name while providing an auto completion dropdown field.
    Fetching the choices from the current live config via livestatus"""
    ident = "monitored_hostname"

    def __init__(self, **kwargs):
        super(MonitoredHostname, self).__init__(completion_ident=self.ident,
                                                completion_params={},
                                                **kwargs)

    @classmethod
    def autocomplete_choices(cls, value, params):
        # type: (str, Dict) -> Choices
        """Return the matching list of dropdown choices
        Called by the webservice with the current input field value and the completions_params to get the list of choices"""
        import cmk.gui.sites as sites

        query = ("GET hosts\n"
                 "Columns: host_name\n"
                 "Filter: host_name ~~ %s" % livestatus.lqencode(value))
        hosts = sorted(sites.live().query_column_unique(query))

        return [(h, h) for h in hosts]


@page_registry.register_page("ajax_vs_autocomplete")
class PageVsAutocomplete(Page):
    def page(self):
        # type: () -> None
        html.set_output_format("json")
        # TODO: Move ajax_handler to this class? Should we also move the autocomplete_choices()?
        TextAsciiAutocomplete.ajax_handler()


def Hostname(  # pylint: disable=redefined-builtin
    # TextAscii
    allow_empty=False,
    # ValueSpec
    title=None,  # type: _Optional[Text]
    help=None,  # type: _Optional[ValueSpecHelp]
    default_value=DEF_VALUE,  # type: Any
):
    """A host name with or without domain part. Also allow IP addresses"""
    return TextAscii(
        regex=re.compile('^[-0-9a-zA-Z_.]+$'),
        regex_error=_("Please enter a valid hostname or IPv4 address. "
                      "Only letters, digits, dash, underscore and dot are allowed."),
        allow_empty=allow_empty,
        title=title,
        help=help,
        default_value=default_value,
    )


class HostAddress(TextAscii):
    """Use this for all host / ip address input fields!"""
    def __init__(  # pylint: disable=redefined-builtin
        self,
        allow_host_name=True,  # type: bool
        allow_ipv4_address=True,  # type: bool
        allow_ipv6_address=True,  # type: bool
        # TextAscii
        label=None,  # type: _Optional[Text]
        size=64,  # type: Union[int, str]
        try_max_width=False,  # type: bool
        cssclass="text",  # type: str
        strip=True,  # type: bool
        attrencode=True,  # type: bool
        allow_empty=True,  # type: bool
        empty_text="",  # type: Text
        read_only=False,  # type: bool
        forbidden_chars="",  # type: Text
        regex=None,  # type: Union[None, str, Pattern[str]]
        regex_error=None,  # type: _Optional[Text]
        minlen=None,  # type: _Optional[int]
        onkeyup=None,  # type: _Optional[Text]
        autocomplete=True,  # type: bool
        hidden=False,  # type: bool
        # ValueSpec
        title=None,  # type: _Optional[Text]
        help=None,  # type: _Optional[ValueSpecHelp]
        default_value=DEF_VALUE,  # type: Any
        validate=None,  # type: _Optional[ValueSpecValidateFunc]
    ):
        super(HostAddress, self).__init__(
            label=label,
            size=size,
            try_max_width=try_max_width,
            cssclass=cssclass,
            strip=strip,
            attrencode=attrencode,
            allow_empty=allow_empty,
            empty_text=empty_text,
            read_only=read_only,
            forbidden_chars=forbidden_chars,
            regex=regex,
            regex_error=regex_error,
            minlen=minlen,
            onkeyup=onkeyup,
            autocomplete=autocomplete,
            hidden=hidden,
            title=title,
            help=help,
            default_value=default_value,
            validate=validate,
        )
        self._allow_host_name = allow_host_name
        self._allow_ipv4_address = allow_ipv4_address
        self._allow_ipv6_address = allow_ipv6_address

    def _validate_value(self, value, varprefix):
        # type: (str, str) -> None
        if value and self._allow_host_name and self._is_valid_host_name(value):
            pass
        elif value and self._allow_ipv4_address and self._is_valid_ipv4_address(value):
            pass
        elif value and self._allow_ipv6_address and self._is_valid_ipv6_address(value):
            pass
        elif not self._allow_empty:
            raise MKUserError(
                varprefix,
                _("Invalid host address. You need to specify the address "
                  "either as %s.") % ", ".join(self._allowed_type_names()))

    def _is_valid_host_name(self, hostname):
        # type: (str) -> bool
        # http://stackoverflow.com/questions/2532053/validate-a-hostname-string/2532344#2532344
        if len(hostname) > 255:
            return False

        if hostname[-1] == ".":
            hostname = hostname[:-1]  # strip exactly one dot from the right, if present

        # must be not all-numeric, so that it can't be confused with an IPv4 address.
        # Host names may start with numbers (RFC 1123 section 2.1) but never the final part,
        # since TLDs are alphabetic.
        if re.match(r"[\d.]+$", hostname):
            return False

        allowed = re.compile(r"(?!-)[A-Z_\d-]{1,63}(?<!-)$", re.IGNORECASE)
        return all(allowed.match(x) for x in hostname.split("."))

    def _is_valid_ipv4_address(self, address):
        # type: (str) -> bool
        # http://stackoverflow.com/questions/319279/how-to-validate-ip-address-in-python/4017219#4017219
        try:
            socket.inet_pton(socket.AF_INET, address)
        except AttributeError:  # no inet_pton here, sorry
            try:
                socket.inet_aton(address)
            except socket.error:
                return False

            return address.count('.') == 3

        except socket.error:  # not a valid address
            return False

        return True

    def _is_valid_ipv6_address(self, address):
        # type: (str) -> bool
        # http://stackoverflow.com/questions/319279/how-to-validate-ip-address-in-python/4017219#4017219
        try:
            address = address.split('%')[0]
            socket.inet_pton(socket.AF_INET6, address)
        except socket.error:  # not a valid address
            return False
        return True

    def _allowed_type_names(self):
        # type: () -> List[Text]
        allowed = []  # type: List[Text]
        if self._allow_host_name:
            allowed.append(_("Host- or DNS name"))

        if self._allow_ipv4_address:
            allowed.append(_("IPv4 address"))

        if self._allow_ipv6_address:
            allowed.append(_("IPv6 address"))

        return allowed


def AbsoluteDirname(  # pylint: disable=redefined-builtin
    # TextAscii
    allow_empty=True,  # type: bool
    size=25,  # type: Union[int, str]
    # ValueSpec
    title=None,  # type: _Optional[Text]
    help=None,  # type: _Optional[ValueSpecHelp]
    default_value=DEF_VALUE,  # type: Any
    validate=None,  # type: _Optional[ValueSpecValidateFunc]
):
    # type: (...) -> TextAscii
    return TextAscii(
        regex=re.compile('^(/|(/[^/]+)+)$'),
        regex_error=_("Please enter a valid absolut pathname with / as a path separator."),
        allow_empty=allow_empty,
        size=size,
        title=title,
        help=help,
        default_value=default_value,
        validate=validate,
    )


class Url(TextAscii):
    def __init__(  # pylint: disable=redefined-builtin
        self,
        default_scheme,  # type: str
        allowed_schemes,  # type: List[str]
        show_as_link=False,  # type: bool
        target=None,  # type: _Optional[str]
        # TextAscii
        label=None,  # type: _Optional[Text]
        size=64,  # type: Union[int, str]
        try_max_width=False,  # type: bool
        cssclass="text",  # type: str
        strip=True,  # type: bool
        attrencode=True,  # type: bool
        allow_empty=True,  # type: bool
        empty_text="",  # type: Text
        read_only=False,  # type: bool
        forbidden_chars="",  # type: Text
        regex=None,  # type: Union[None, str, Pattern[str]]
        regex_error=None,  # type: _Optional[Text]
        minlen=None,  # type: _Optional[int]
        onkeyup=None,  # type: _Optional[Text]
        autocomplete=True,  # type: bool
        hidden=False,  # type: bool
        # ValueSpec
        title=None,  # type: _Optional[Text]
        help=None,  # type: _Optional[ValueSpecHelp]
        default_value=DEF_VALUE,  # type: Any
        validate=None,  # type: _Optional[ValueSpecValidateFunc]
    ):
        super(Url, self).__init__(
            label=label,
            size=size,
            try_max_width=try_max_width,
            cssclass=cssclass,
            strip=strip,
            attrencode=attrencode,
            allow_empty=allow_empty,
            empty_text=empty_text,
            read_only=read_only,
            forbidden_chars=forbidden_chars,
            regex=regex,
            regex_error=regex_error,
            minlen=minlen,
            onkeyup=onkeyup,
            autocomplete=autocomplete,
            hidden=hidden,
            title=title,
            help=help,
            default_value=default_value,
            validate=validate,
        )
        self._default_scheme = default_scheme
        self._allowed_schemes = allowed_schemes
        self._show_as_link = show_as_link
        self._link_target = target

    def _validate_value(self, value, varprefix):
        # type: (str, str) -> None
        assert value is not None
        super(Url, self)._validate_value(value, varprefix)

        if self._allow_empty and value == "":
            return

        parts = six.moves.urllib.parse.urlparse(value)
        if not parts.scheme or not parts.netloc:
            raise MKUserError(varprefix, _("Invalid URL given"))

        if parts.scheme not in self._allowed_schemes:
            raise MKUserError(
                varprefix,
                _("Invalid URL scheme. Must be one of: %s") % ", ".join(self._allowed_schemes))

    def from_html_vars(self, varprefix):
        # type: (str) -> str
        value = super(Url, self).from_html_vars(varprefix)
        if value and "://" not in value:
            value = self._default_scheme + "://" + value
        return value

    def value_to_text(self, value):
        # type: (str) -> Text
        if not any(value.startswith(scheme + "://") for scheme in self._allowed_schemes):
            value = self._default_scheme + "://" + value

        try:
            parts = six.moves.urllib.parse.urlparse(value)
            if parts.path in ['', '/']:
                text = parts.netloc
            else:
                text = parts.netloc + parts.path
        except Exception:
            text = value[7:]

        # Remove trailing / if the url does not contain any path component
        if self._show_as_link:
            return u"%s" % html.render_a(
                text, href=value, target=self._link_target if self._link_target else None)

        return value


def HTTPUrl(  # pylint: disable=redefined-builtin
    show_as_link=True,  # type: bool
    # Url
    regex=None,  # type: Union[None, str, Pattern[str]]
    regex_error=None,  # type: _Optional[Text]
    # TextAscii
    allow_empty=True,  # type: bool
    size=80,  # type: Union[int, str]
    # ValueSpec
    title=None,  # type: _Optional[Text]
    help=None,  # type: _Optional[ValueSpecHelp]
    default_value=DEF_VALUE,  # type: Any
):
    """Valuespec for a HTTP or HTTPS Url, that automatically adds http:// to the value if no scheme has been specified"""
    return Url(
        allowed_schemes=["http", "https"],
        default_scheme="http",
        regex=regex,
        regex_error=regex_error,
        show_as_link=show_as_link,
        allow_empty=allow_empty,
        size=size,
        title=title,
        help=help,
        default_value=default_value,
    )


def CheckMKVersion(
    # ValueSpec
    title=None,  # type: _Optional[Text]
    default_value=DEF_VALUE,  # type: Any
):
    return TextAscii(
        regex=r"[0-9]+\.[0-9]+\.[0-9]+([bpi][0-9]+|i[0-9]+p[0-9]+)?$",
        regex_error=_("This is not a valid Checkmk version number"),
        title=title,
        default_value=default_value,
    )


class TextAreaUnicode(TextUnicode):
    def __init__(  # pylint: disable=redefined-builtin
        self,
        cols=60,  # type: int
        rows=20,  # type: Union[int, str]
        minrows=0,  # type: int
        monospaced=False,  # type: bool
        # TextAscii
        label=None,  # type: _Optional[Text]
        size=64,  # type: Union[int, str]
        try_max_width=False,  # type: bool
        cssclass="text",  # type: str
        strip=True,  # type: bool
        attrencode=True,  # type: bool
        allow_empty=True,  # type: bool
        empty_text="",  # type: Text
        read_only=False,  # type: bool
        forbidden_chars="",  # type: Text
        regex=None,  # type: Union[None, str, Pattern[str]]
        regex_error=None,  # type: _Optional[Text]
        minlen=None,  # type: _Optional[int]
        onkeyup=None,  # type: _Optional[Text]
        autocomplete=True,  # type: bool
        hidden=False,  # type: bool
        # ValueSpec
        title=None,  # type: _Optional[Text]
        help=None,  # type: _Optional[ValueSpecHelp]
        default_value=DEF_VALUE,  # type: Any
        validate=None,  # type: _Optional[ValueSpecValidateFunc]
    ):
        super(TextAreaUnicode, self).__init__(
            label=label,
            size=size,
            try_max_width=try_max_width,
            cssclass=cssclass,
            strip=strip,
            attrencode=attrencode,
            allow_empty=allow_empty,
            empty_text=empty_text,
            read_only=read_only,
            forbidden_chars=forbidden_chars,
            regex=regex,
            regex_error=regex_error,
            minlen=minlen,
            onkeyup=onkeyup,
            autocomplete=autocomplete,
            hidden=hidden,
            title=title,
            help=help,
            default_value=default_value,
            validate=validate,
        )
        self._cols = cols
        self._try_max_width = try_max_width
        self._rows = rows  # Allowed: "auto" -> Auto resizing
        self._minrows = minrows  # Minimum number of initial rows when "auto"
        self._monospaced = monospaced  # select TT font

    def value_to_text(self, value):
        # type: (Text) -> Text
        if self._monospaced:
            # TODO: This is a workaround for a bug. This function needs to return str objects right now.
            return "%s" % html.render_pre(HTML(value), class_="ve_textarea")
        return escaping.escape_attribute(value).replace("\n", "<br>")

    # TODO: Once we switched to Python 3 we can merge the unicode and non unicode class
    def render_input(self, varprefix, value):  # type: ignore[override]
        # type: (str, Text) -> None
        if value is None:
            value = ""  # should never happen, but avoids exception for invalid input
        if self._rows == "auto":
            func = 'cmk.valuespecs.textarea_resize(this);'
            attrs = {"onkeyup": func, "onmousedown": func, "onmouseup": func, "onmouseout": func}
            if html.request.has_var(varprefix):
                rows = len(self.from_html_vars(varprefix).splitlines())
            else:
                rows = len(value.splitlines())
            rows = max(rows, self._minrows)
        else:
            attrs = {}
            assert isinstance(self._rows, int)
            rows = self._rows

        if self._monospaced:
            attrs["class"] = "tt"

        html.text_area(varprefix,
                       value,
                       rows=rows,
                       cols=self._cols,
                       try_max_width=self._try_max_width,
                       **attrs)

    # Overridden because we do not want to strip() here and remove '\r'
    # TODO: Once we switched to Python 3 we can merge the unicode and non unicode class
    def from_html_vars(self, varprefix):  # type: ignore[override]
        # type: (str) -> Text
        text = html.request.get_unicode_input_mandatory(varprefix, "").replace('\r', '')
        if text and not text.endswith("\n"):
            text += "\n"  # force newline at end
        return text


# TODO: Rename the valuespec here to ExistingFilename or somehting similar
# TODO: Change to factory?
class Filename(TextAscii):
    """A variant of TextAscii() that validates a path to a filename that lies in an existing directory."""

    # TODO: Cleanup default / default_value?
    def __init__(  # pylint: disable=redefined-builtin
        self,
        default="/tmp/foo",  # type: str
        trans_func=None,  # type: _Optional[Callable[[str], str]]
        # TextAscii
        label=None,  # type: _Optional[Text]
        size=60,  # type: Union[int, str]
        try_max_width=False,  # type: bool
        cssclass="text",  # type: str
        strip=True,  # type: bool
        attrencode=True,  # type: bool
        allow_empty=True,  # type: bool
        empty_text="",  # type: Text
        read_only=False,  # type: bool
        forbidden_chars="",  # type: Text
        regex=None,  # type: Union[None, str, Pattern[str]]
        regex_error=None,  # type: _Optional[Text]
        minlen=None,  # type: _Optional[int]
        onkeyup=None,  # type: _Optional[Text]
        autocomplete=True,  # type: bool
        hidden=False,  # type: bool
        # ValueSpec
        title=None,  # type: _Optional[Text]
        help=None,  # type: _Optional[ValueSpecHelp]
        default_value=DEF_VALUE,  # type: Any
        validate=None,  # type: _Optional[ValueSpecValidateFunc]
    ):
        super(Filename, self).__init__(
            label=label,
            size=size,
            try_max_width=try_max_width,
            cssclass=cssclass,
            strip=strip,
            attrencode=attrencode,
            allow_empty=allow_empty,
            empty_text=empty_text,
            read_only=read_only,
            forbidden_chars=forbidden_chars,
            regex=regex,
            regex_error=regex_error,
            minlen=minlen,
            onkeyup=onkeyup,
            autocomplete=autocomplete,
            hidden=hidden,
            title=title,
            help=help,
            default_value=default_value,
            validate=validate,
        )
        self._default_path = default
        self._trans_func = trans_func

    def canonical_value(self):
        # type: () -> str
        return self._default_path

    def _validate_value(self, value, varprefix):
        # type: (str, str) -> None
        # The transformation function only changes the value for validation. This is
        # usually a function which is later also used within the code which uses
        # this variable to e.g. replace macros
        if self._trans_func:
            value = self._trans_func(value)

        if len(value) == 0:
            raise MKUserError(varprefix, _("Please enter a filename."))

        if value[0] != "/":
            raise MKUserError(
                varprefix,
                _("Sorry, only absolute filenames are allowed. "
                  "Your filename must begin with a slash."))
        if value[-1] == "/":
            raise MKUserError(varprefix, _("Your filename must not end with a slash."))

        directory = value.rsplit("/", 1)[0]
        if not os.path.isdir(directory):
            raise MKUserError(
                varprefix,
                _("The directory %s does not exist or is not a directory.") % directory)

        # Write permissions to the file cannot be checked here since we run with Apache
        # permissions and the file might be created with Nagios permissions (on OMD this
        # is the same, but for others not)


class ListOfStrings(ValueSpec):
    def __init__(  # pylint: disable=redefined-builtin
        self,
        # ListOfStrings
        valuespec=None,  # type: _Optional[ValueSpec]
        size=25,  # type: Union[str, int]
        orientation="vertical",  # type: Text
        allow_empty=True,  # type: bool
        empty_text="",  # type: Text
        max_entries=None,  # type: _Optional[int]
        separator="",  # type: Text
        split_on_paste=True,  # type: bool
        split_separators=";",  # type: Text
        # ValueSpec
        title=None,  # type: _Optional[Text]
        help=None,  # type: _Optional[ValueSpecHelp]
        default_value=DEF_VALUE,  # type: Any
        validate=None,  # type: _Optional[ValueSpecValidateFunc]
    ):
        super(ListOfStrings, self).__init__(title=title,
                                            help=help,
                                            default_value=default_value,
                                            validate=validate)

        self._valuespec = valuespec if valuespec is not None else TextAscii(size=size)
        self._vertical = orientation == "vertical"
        self._allow_empty = allow_empty
        self._empty_text = empty_text
        self._max_entries = max_entries
        self._separator = separator  # in case of float

        self._split_on_paste = split_on_paste
        self._split_separators = split_separators

    def help(self):
        # type: () -> Union[Text, HTML, None]
        help_texts = [
            super(ListOfStrings, self).help(),
            self._valuespec.help(),
        ]

        if self._split_on_paste:
            help_texts.append(
                _("You may paste a text from your clipboard which contains several "
                  "parts separated by \"%s\" characters into the last input field. The text will "
                  "then be split by these separators and the single parts are added into dedicated "
                  "input fields.") % self._split_separators)

        return u" ".join(u"%s" % t for t in help_texts if t)

    def render_input(self, varprefix, value):
        # type: (str, List[str]) -> None
        # Form already submitted?
        if html.request.has_var(varprefix + "_0"):
            value = self.from_html_vars(varprefix)
            # Remove variables from URL, so that they do not appear
            # in hidden_fields()
            nr = 0
            while html.request.has_var(varprefix + "_%d" % nr):
                html.request.del_var(varprefix + "_%d" % nr)
                nr += 1

        class_ = ["listofstrings"]
        if self._vertical:
            class_.append("vertical")
        else:
            class_.append("horizontal")
        html.open_div(id_=varprefix, class_=class_)

        for nr, s in enumerate(value + [""]):
            html.open_div()
            self._valuespec.render_input(varprefix + "_%d" % nr, s)
            if self._vertical != "vertical" and self._separator:
                html.nbsp()
                html.write(self._separator)
                html.nbsp()
            html.close_div()
        html.close_div()
        html.div('', style="clear:left;")
        html.javascript("cmk.valuespecs.list_of_strings_init(%s, %s, %s);" %
                        (json.dumps(varprefix), json.dumps(
                            self._split_on_paste), json.dumps(self._split_separators)))

    def canonical_value(self):
        # type: () -> List[str]
        return []

    def value_to_text(self, value):
        # type: (List[str]) -> Text
        if not value:
            return self._empty_text

        if self._vertical:
            # TODO: This is a workaround for a bug. This function needs to return str objects right now.
            s = [
                html.render_tr(html.render_td(HTML(self._valuespec.value_to_text(v))))
                for v in value
            ]
            return "%s" % html.render_table(HTML().join(s))
        return u", ".join([self._valuespec.value_to_text(v) for v in value])

    def from_html_vars(self, varprefix):
        # type: (str) -> List[str]
        value = []  # type: List[str]
        nr = 0
        while True:
            varname = varprefix + "_%d" % nr
            if not html.request.has_var(varname):
                break
            if html.request.get_str_input_mandatory(varname, "").strip():
                value.append(self._valuespec.from_html_vars(varname))
            nr += 1
        return value

    def validate_datatype(self, value, varprefix):
        # type: (List[str], str) -> None
        if not isinstance(value, list):
            raise MKUserError(
                varprefix,
                _("Expected data type is list, but your type is %s.") % _type_name(value))
        for nr, s in enumerate(value):
            self._valuespec.validate_datatype(s, varprefix + "_%d" % nr)

    def _validate_value(self, value, varprefix):
        # type: (List[str], str) -> None
        if len(value) == 0 and not self._allow_empty:
            if self._empty_text:
                msg = self._empty_text
            else:
                msg = _("Please specify at least one value")
            raise MKUserError(varprefix + "_0", msg)

        if self._max_entries is not None and len(value) > self._max_entries:
            raise MKUserError(varprefix + "_%d" % self._max_entries,
                              _("You can specify at most %d entries") % self._max_entries)

        if self._valuespec:
            for nr, s in enumerate(value):
                self._valuespec.validate_value(s, varprefix + "_%d" % nr)


# TODO: Spread use of this valuespec
def NetworkPort(title, default_value=DEF_VALUE):
    # type: (_Optional[Text], Union[object, int]) -> Integer
    return Integer(
        title=title,
        minvalue=1,
        maxvalue=65535,
        default_value=default_value,
    )


def ListOfNetworkPorts(title, default_value):
    # type: (_Optional[Text], List[int]) -> ListOfStrings
    return ListOfStrings(
        valuespec=NetworkPort(title=_("Port")),
        title=title,
        orientation="horizontal",
        default_value=default_value,
    )


class ListOf(ValueSpec):
    """Generic list-of-valuespec ValueSpec with Javascript-based add/delete/move"""
    class Style(Enum):
        REGULAR = "regular"
        FLOATING = "floating"

    def __init__(  # pylint: disable=redefined-builtin
        self,
        valuespec,  # type: ValueSpec
        magic="@!@",  # type: str
        add_label=None,  # type: _Optional[Text]
        del_label=None,  # type: _Optional[Text]
        movable=True,  # type: bool
        style=None,  # type: _Optional[ListOf.Style]
        totext=None,  # type: _Optional[Text]
        text_if_empty=None,  # type: _Optional[Text]
        allow_empty=True,  # type: bool
        empty_text=None,  # type: _Optional[Text]
        sort_by=None,  # type: _Optional[int]
        title=None,  # type: _Optional[Text]
        help=None,  # type: _Optional[ValueSpecHelp]
        default_value=DEF_VALUE,  # type: Any
        validate=None,  # type: _Optional[ValueSpecValidateFunc]
    ):
        super(ListOf, self).__init__(title=title,
                                     help=help,
                                     default_value=default_value,
                                     validate=validate)
        self._valuespec = valuespec
        self._magic = magic
        self._add_label = add_label if add_label else _("Add new element")
        self._del_label = del_label if del_label else _("Delete this entry")
        self._movable = movable
        self._style = style or ListOf.Style.REGULAR
        self._totext = totext  # pattern with option %d
        self._text_if_empty = text_if_empty if text_if_empty is not None else _("No entries")
        self._allow_empty = allow_empty
        self._empty_text = empty_text if empty_text is not None else \
            _("Please specify at least one entry")

        # Makes a sort button visible that can be used to sort the list in the GUI
        # (without submitting the form). But this currently only works for list of
        # tuples that contain input field elements directly. The value of sort_by
        # refers to the index of the sort values in the tuple
        self._sort_by = sort_by

    # Implementation idea: we render our element-valuespec
    # once in a hidden div that is not evaluated. All occurances
    # of a magic string are replaced with the actual number
    # of entry, while beginning with 1 (this makes visual
    # numbering in labels, etc. possible). The current number
    # of entries is stored in the hidden variable 'varprefix'
    def render_input(self, varprefix, value):
        # type: (str, List[Any]) -> None
        html.open_div(class_=["valuespec_listof", self._style.value])

        # Beware: the 'value' is only the default value in case the form
        # has not yet been filled in. In the complain phase we must
        # ignore 'value' but reuse the input from the HTML variables -
        # even if they are not syntactically correct. Calling from_html_vars
        # here is *not* an option since this might not work in case of
        # a wrong user input.

        # Render reference element for cloning
        self._show_reference_entry(varprefix, self._magic, self._valuespec.default_value())

        # In the 'complain' phase, where the user already saved the
        # form but the validation failed, we must not display the
        # original 'value' but take the value from the HTML variables.
        if html.request.has_var("%s_count" % varprefix):
            count = len(self.get_indexes(varprefix))
            value = [None] * count  # dummy for the loop
        else:
            count = len(value)

        html.hidden_field('%s_count' % varprefix,
                          str(count),
                          id_='%s_count' % varprefix,
                          add_var=True)

        self._show_entries(varprefix, value)

        html.close_div()

        if count:
            html.javascript("cmk.valuespecs.listof_update_indices(%s)" % json.dumps(varprefix))

    def _show_entries(self, varprefix, value):
        # type: (str, List[Any]) -> None
        if self._style == ListOf.Style.REGULAR:
            self._show_current_entries(varprefix, value)
            html.br()
            self._list_buttons(varprefix)

        elif self._style == ListOf.Style.FLOATING:
            html.open_table()
            html.open_tbody()
            html.open_tr()
            html.open_td()
            self._list_buttons(varprefix)
            html.close_td()
            html.open_td()
            self._show_current_entries(varprefix, value)
            html.close_td()
            html.close_tr()
            html.close_tbody()
            html.close_table()

        else:
            raise NotImplementedError()

    def _list_buttons(self, varprefix):
        # type: (str) -> None
        html.jsbutton(
            varprefix + "_add", self._add_label, "cmk.valuespecs.listof_add(%s, %s, %s)" %
            (json.dumps(varprefix), json.dumps(self._magic), json.dumps(self._style.value)))

        if self._sort_by is not None:
            html.jsbutton(
                varprefix + "_sort", _("Sort"), "cmk.valuespecs.listof_sort(%s, %s, %s)" %
                (json.dumps(varprefix), json.dumps(self._magic), json.dumps(self._sort_by)))

    def _show_reference_entry(self, varprefix, index, value):
        # type: (str, str, Any) -> None
        if self._style == ListOf.Style.REGULAR:
            html.open_table(style="display:none;")
            html.open_tbody(id_="%s_prototype" % varprefix, class_="vlof_prototype")

            self._show_entry(varprefix, index, value)

            html.close_tbody()
            html.close_table()

        elif self._style == ListOf.Style.FLOATING:
            html.open_div(id_="%s_prototype" % varprefix,
                          class_="vlof_prototype",
                          style="display:none;")

            self._show_entry(varprefix, index, value)

            html.close_div()

        else:
            raise NotImplementedError()

    def _show_current_entries(self, varprefix, value):
        # type: (str, Any) -> None
        if self._style == ListOf.Style.REGULAR:
            html.open_table(class_=["valuespec_listof"])
            html.open_tbody(id_="%s_container" % varprefix)

            for nr, v in enumerate(value):
                self._show_entry(varprefix, "%d" % (nr + 1), v)

            html.close_tbody()
            html.close_table()

        elif self._style == ListOf.Style.FLOATING:
            html.open_div(id_="%s_container" % varprefix,
                          class_=["valuespec_listof_floating_container"])

            for nr, v in enumerate(value):
                self._show_entry(varprefix, "%d" % (nr + 1), v)

            html.close_div()

        else:
            raise NotImplementedError()

    def _show_entry(self, varprefix, index, value):
        # type: (str, str, Any) -> None
        entry_id = "%s_entry_%s" % (varprefix, index)

        if self._style == ListOf.Style.REGULAR:
            html.open_tr(id_=entry_id)
            self._show_entry_cell(varprefix, index, value)
            html.close_tr()

        elif self._style == ListOf.Style.FLOATING:
            html.open_table(id_=entry_id)
            html.open_tbody()
            html.open_tr()
            self._show_entry_cell(varprefix, index, value)
            html.close_tr()
            html.close_tbody()
            html.close_table()

        else:
            raise NotImplementedError()

    def _show_entry_cell(self, varprefix, index, value):
        # type: (str, str, Any) -> None
        html.open_td(class_="vlof_buttons")

        html.hidden_field(varprefix + "_indexof_" + index, "", add_var=True,
                          class_="index")  # reconstruct order after moving stuff
        html.hidden_field(varprefix + "_orig_indexof_" + index,
                          "",
                          add_var=True,
                          class_="orig_index")
        if self._movable:
            html.element_dragger_js("tr",
                                    drop_handler="cmk.valuespecs.listof_drop_handler",
                                    handler_args={
                                        "cur_index": index,
                                        "varprefix": varprefix
                                    })
        self._del_button(varprefix, index)
        html.close_td()
        html.open_td(class_="vlof_content")
        self._valuespec.render_input(varprefix + "_" + index, value)
        html.close_td()

    def _del_button(self, vp, nr):
        # type: (str, str) -> None
        js = "cmk.valuespecs.listof_delete(%s, %s)" % (json.dumps(vp), json.dumps(nr))
        html.icon_button("#", self._del_label, "delete", onclick=js)

    def canonical_value(self):
        # type: () -> List[Any]
        return []

    def value_to_text(self, value):
        # type: (List[Any]) -> Text
        if self._totext:
            if "%d" in self._totext:
                return self._totext % len(value)
            return self._totext
        if not value:
            return self._text_if_empty

        # TODO: This is a workaround for a bug. This function needs to return str objects right now.
        s = [html.render_tr(html.render_td(HTML(self._valuespec.value_to_text(v)))) for v in value]
        return "%s" % html.render_table(HTML().join(s))

    def get_indexes(self, varprefix):
        # type: (str) -> Dict[int, int]
        count = html.request.get_integer_input_mandatory(varprefix + "_count", 0)
        n = 1
        indexes = {}
        while n <= count:
            indexof = html.request.var(varprefix + "_indexof_%d" % n)
            # for deleted entries, we have removed the whole row, therefore indexof is None
            if indexof is not None:
                indexes[int(indexof)] = n
            n += 1
        return indexes

    def from_html_vars(self, varprefix):
        # type: (str) -> List[Any]
        indexes = self.get_indexes(varprefix)
        value = []
        k = sorted(indexes.keys())
        for i in k:
            val = self._valuespec.from_html_vars(varprefix + "_%d" % indexes[i])
            value.append(val)
        return value

    def validate_datatype(self, value, varprefix):
        # type: (List[Any], str) -> None
        if not isinstance(value, list):
            raise MKUserError(varprefix, _("The type must be list, but is %s") % _type_name(value))
        for n, v in enumerate(value):
            self._valuespec.validate_datatype(v, varprefix + "_%d" % (n + 1))

    def _validate_value(self, value, varprefix):
        # type: (List[Any], str) -> None
        if not self._allow_empty and len(value) == 0:
            raise MKUserError(varprefix, self._empty_text)
        for n, v in enumerate(value):
            self._valuespec.validate_value(v, varprefix + "_%d" % (n + 1))


class ListOfMultiple(ValueSpec):
    """A generic valuespec where the user can choose from a list of sub-valuespecs.
    Each sub-valuespec can be added only once
    """
    def __init__(  # pylint: disable=redefined-builtin
        self,
        choices,  # type: List[_Tuple[str, ValueSpec]]
        choice_page_name,  # type: str
        page_request_vars=None,  # type: Dict[Text, Any]
        size=None,  # type: _Optional[int]
        add_label=None,  # type: _Optional[Text]
        del_label=None,  # type: _Optional[Text]
        delete_style="default",  # type: str
        title=None,  # type: _Optional[Text]
        help=None,  # type: _Optional[ValueSpecHelp]
        default_value=DEF_VALUE,  # type: Any
        validate=None,  # type: _Optional[ValueSpecValidateFunc]
    ):
        super(ListOfMultiple, self).__init__(title=title,
                                             help=help,
                                             default_value=default_value,
                                             validate=validate)
        self._choices = choices
        self._choice_dict = dict(choices)
        self._choice_page_name = choice_page_name
        self._page_request_vars = page_request_vars or {}
        self._size = size
        self._add_label = add_label if add_label is not None else _("Add element")
        self._del_label = del_label if del_label is not None else _("Delete this entry")
        self._delete_style = delete_style  # or "filter"

    def del_button(self, varprefix, ident):
        # type: (str, str) -> None
        js = "cmk.valuespecs.listofmultiple_del(%s, %s)" % (json.dumps(varprefix),
                                                            json.dumps(ident))
        html.icon_button("#", self._del_label, "delete", onclick=js)

    def render_input(self, varprefix, value):
        # type: (str, Dict[str, Any]) -> None
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
        if html.request.var("%s_active" % varprefix):
            value = self.from_html_vars(varprefix)

        # Save all selected items
        html.hidden_field('%s_active' % varprefix,
                          ';'.join([k for k in value.keys() if k in self._choice_dict]),
                          id_='%s_active' % varprefix,
                          add_var=True)

        # Actual table of currently existing entries
        html.open_table(id_="%s_table" % varprefix, class_=["valuespec_listof", extra_css])
        html.open_tbody()

        for ident, _vs in self._choices:
            if ident in value:
                self.show_choice_row(varprefix, ident, value)

        html.close_tbody()
        html.close_table()

        choices = [('', u'')]  # type: Choices
        choices += [(ident, vs.title() or u"") for ident, vs in self._choices]
        html.dropdown(varprefix + '_choice',
                      choices,
                      style="width: %dex" % self._size if self._size is not None else None,
                      class_="vlof_filter" if self._delete_style == "filter" else None)
        html.javascript('cmk.valuespecs.listofmultiple_init(%s);' % json.dumps(varprefix))
        html.jsbutton(
            varprefix + '_add',
            self._add_label,
            "cmk.valuespecs.listofmultiple_add(%s, %s, %s)" % (
                json.dumps(varprefix),  #
                json.dumps(self._choice_page_name),
                json.dumps(self._page_request_vars)))

    def show_choice_row(self, varprefix, ident, value):
        # type: (str, str, Dict[str, Any]) -> None
        prefix = varprefix + '_' + ident
        html.open_tr(id_="%s_row" % prefix)
        if self._delete_style == "filter":
            self._show_del_button(varprefix, ident)
            self._show_content(varprefix, ident, value)
        else:
            self._show_del_button(varprefix, ident)
            self._show_content(varprefix, ident, value)
        html.close_tr()

    def _show_content(self, varprefix, ident, value):
        # type: (str, str, Dict[str, Any]) -> None
        prefix = varprefix + '_' + ident
        html.open_td(class_=["vlof_content"])
        self._choice_dict[ident].render_input(prefix, value.get(ident))
        html.close_td()

    def _show_del_button(self, varprefix, ident):
        # type: (str, str) -> None
        html.open_td(class_=["vlof_buttons"])
        self.del_button(varprefix, ident)
        html.close_td()

    def canonical_value(self):
        # type: () -> Dict[str, Any]
        return {}

    def value_to_text(self, value):
        # type: (Dict[str, Any]) -> Text
        table_content = HTML()
        for ident, val in value:
            vs = self._choice_dict[ident]
            # TODO: This is a workaround for a bug. This function needs to return str objects right now.
            table_content += html.render_tr(
                html.render_td(vs.title()) + html.render_td(HTML(vs.value_to_text(val))))
        return "%s" % html.render_table(table_content)

    def from_html_vars(self, varprefix):
        # type: (str) -> Dict[str, Any]
        value = {}  # type: Dict[str, Any]
        active = html.request.get_str_input_mandatory('%s_active' % varprefix).strip()
        if not active:
            return value

        for ident in active.split(';'):
            vs = self._choice_dict[ident]
            value[ident] = vs.from_html_vars(varprefix + '_' + ident)
        return value

    def validate_datatype(self, value, varprefix):
        # type: (Dict[str, Any], str) -> None
        if not isinstance(value, dict):
            raise MKUserError(varprefix, _("The type must be dict, but is %s") % _type_name(value))
        for ident, val in value.items():
            self._choice_dict[ident].validate_datatype(val, varprefix + '_' + ident)

    def _validate_value(self, value, varprefix):
        # type: (Dict[str, Any], str) -> None
        for ident, val in value.items():
            self._choice_dict[ident].validate_value(val, varprefix + '_' + ident)


class ABCPageListOfMultipleGetChoice(six.with_metaclass(abc.ABCMeta, AjaxPage)):
    @abc.abstractmethod
    def _get_choices(self, request):
        # type: (Dict[Text, Text]) -> List[_Tuple[str, ValueSpec]]
        raise NotImplementedError()

    def page(self):
        # type: () -> Dict
        request = html.get_request()
        vs = ListOfMultiple(self._get_choices(request), "unused_dummy_page")
        with html.plugged():
            vs.show_choice_row(six.ensure_str(request["varprefix"]),
                               six.ensure_str(request["ident"]), {})
            return {"html_code": html.drain()}


class Float(ValueSpec):
    """Same as Integer, but for floating point values"""
    def __init__(  # pylint: disable=redefined-builtin
        self,
        decimal_separator=".",  # type: Text
        allow_int=False,  # type: bool
        # Integer
        size=None,  # type: _Optional[int]
        minvalue=None,  # type: _Optional[float]
        maxvalue=None,  # type: _Optional[float]
        label=None,  # type: _Optional[Text]
        unit="",  # type: Text
        thousand_sep=None,  # type: _Optional[Text]
        display_format="%.2f",  # type: Text
        align="left",  # type: str
        # ValueSpec
        title=None,  # type: _Optional[Text]
        help=None,  # type: _Optional[ValueSpecHelp]
        default_value=DEF_VALUE,  # type: Any
        validate=None,  # type: _Optional[ValueSpecValidateFunc]
    ):
        super(Float, self).__init__(title=title,
                                    help=help,
                                    default_value=default_value,
                                    validate=validate)
        self._bounds = Bounds[float](minvalue, maxvalue)
        self._renderer = NumericRenderer(size=size,
                                         maxvalue=maxvalue,
                                         label=label,
                                         unit=unit,
                                         thousand_sep=thousand_sep,
                                         align=align)
        self._display_format = display_format
        self._decimal_separator = decimal_separator
        self._allow_int = allow_int

    def canonical_value(self):
        # type: () -> float
        return self._bounds.lower(0.0)

    def render_input(self, varprefix, value):
        # type: (str, float) -> None
        self._renderer.render_input(varprefix, self._render_value(value))

    def _render_value(self, value):
        # type: (float) -> Text
        return self._display_format % utils.savefloat(value)

    def from_html_vars(self, varprefix):
        # type: (str) -> float
        return html.request.get_float_input_mandatory(varprefix)

    def value_to_text(self, value):
        # type: (float) -> Text
        txt = self._renderer.format_text(self._render_value(value))
        return txt.replace(".", self._decimal_separator)

    def validate_datatype(self, value, varprefix):
        # type: (float, str) -> None
        if isinstance(value, float):
            return
        if isinstance(value, numbers.Integral) and self._allow_int:
            return
        raise MKUserError(
            varprefix,
            _("The value %r has type %s, but must be of type float%s") %
            (value, _type_name(value), _(" or int") if self._allow_int else ''))

    def validate_value(self, value, varprefix):
        # type: (float, str) -> None
        self._bounds.validate_value(value, varprefix)


class Percentage(Float):
    def __init__(  # pylint: disable=redefined-builtin
        self,
        # Float
        decimal_separator=".",  # type: Text
        allow_int=False,  # type: bool
        # Integer
        size=None,  # type: _Optional[int]
        minvalue=0.0,  # type: Union[None, int, float]
        maxvalue=101.0,  # type: Union[None, int, float]
        label=None,  # type: _Optional[Text]
        unit="%",  # type: Text
        thousand_sep=None,  # type: _Optional[Text]
        display_format="%.1f",  # type: Text
        align="left",  # type: str
        # ValueSpec
        title=None,  # type: _Optional[Text]
        help=None,  # type: _Optional[ValueSpecHelp]
        default_value=DEF_VALUE,  # type: Any
        validate=None,  # type: _Optional[ValueSpecValidateFunc]
    ):
        super(Percentage, self).__init__(decimal_separator=decimal_separator,
                                         allow_int=allow_int,
                                         size=size,
                                         minvalue=minvalue,
                                         maxvalue=maxvalue,
                                         label=label,
                                         unit=unit,
                                         thousand_sep=thousand_sep,
                                         display_format=display_format,
                                         align=align,
                                         title=title,
                                         help=help,
                                         default_value=default_value,
                                         validate=validate)

    def value_to_text(self, value):
        # type: (float) -> Text
        return (self._display_format + "%%") % value

    def validate_datatype(self, value, varprefix):
        # type: (float, str) -> None
        if self._allow_int:
            if not isinstance(value, (int, float)):
                raise MKUserError(
                    varprefix,
                    _("The value %r has type %s, but must be either float or int") %
                    (value, _type_name(value)))
        else:
            super(Percentage, self).validate_datatype(value, varprefix)


class Checkbox(ValueSpec):
    def __init__(  # pylint: disable=redefined-builtin
        self,
        label=None,  # type: _Optional[Text]
        true_label=None,  # type: _Optional[Text]
        false_label=None,  # type: _Optional[Text]
        onclick=None,  # type: _Optional[Text]
        title=None,  # type: _Optional[Text]
        help=None,  # type: _Optional[ValueSpecHelp]
        default_value=DEF_VALUE,  # type: Any
        validate=None,  # type: _Optional[ValueSpecValidateFunc]
    ):
        super(Checkbox, self).__init__(title=title,
                                       help=help,
                                       default_value=default_value,
                                       validate=validate)
        self._label = label
        self._true_label = true_label if true_label is not None else _("on")
        self._false_label = false_label if false_label is not None else _("off")
        self._onclick = onclick

    def canonical_value(self):
        # type: () -> bool
        return False

    def render_input(self, varprefix, value):
        # type: (str, bool) -> None
        html.checkbox(varprefix, value, label=self._label, onclick=self._onclick)

    def value_to_text(self, value):
        # type: (bool) -> Text
        return self._true_label if value else self._false_label

    def from_html_vars(self, varprefix):
        # type: (str) -> bool
        return bool(html.request.var(varprefix))

    def validate_datatype(self, value, varprefix):
        # type: (bool, str) -> None
        if not isinstance(value, bool):
            raise MKUserError(
                varprefix,
                _("The value %r has type %s, but must be of type bool") %
                (value, _type_name(value)))


DropdownChoiceValue = Any  # TODO: Can we be more specific?
DropdownChoiceEntry = _Tuple[DropdownChoiceValue, Text]
DropdownChoices = Union[List[DropdownChoiceEntry], Callable[[], List[DropdownChoiceEntry]]]


class DropdownChoice(ValueSpec):
    """A type-safe dropdown choice

    Parameters:
    help_separator: if you set this to a character, e.g. "-", then
    value_to_text will omit texts from the character up to the end of
    a choices name.
    choices may also be a function that returns - when called
    without arguments - such a tuple list. That way the choices
    can by dynamically computed"""

    # TODO: Cleanup redefined builtin sorted
    def __init__(  # pylint: disable=redefined-builtin
        self,
        # DropdownChoice
        choices,  # type: DropdownChoices
        sorted=False,  # type: bool
        label=None,  # type: _Optional[Text]
        help_separator=None,  # type: Text
        prefix_values=False,  # type: bool
        empty_text=None,  # type: _Optional[Text]
        invalid_choice="complain",  # type: _Optional[str]
        invalid_choice_title=None,  # type: _Optional[Text]
        invalid_choice_error=None,  # type: _Optional[Text]
        no_preselect=False,  # type: bool
        no_preselect_value=None,  # type: Any
        no_preselect_title="",  # type: Text
        no_preselect_error=None,  # type: Text
        on_change=None,  # type: Text
        read_only=False,  # type: bool
        encode_value=True,  # type: bool
        # ValueSpec
        title=None,  # type: _Optional[Text]
        help=None,  # type: _Optional[ValueSpecHelp]
        default_value=DEF_VALUE,  # type: Any
        validate=None,  # type: _Optional[ValueSpecValidateFunc]
    ):
        super(DropdownChoice, self).__init__(title=title,
                                             help=help,
                                             default_value=default_value,
                                             validate=validate)
        self._choices = choices
        self._help_separator = help_separator
        self._label = label
        self._prefix_values = prefix_values
        self._sorted = sorted
        self._empty_text = (empty_text if empty_text is not None else
                            _("There are no elements defined for this selection yet."))
        self._invalid_choice = invalid_choice
        self._invalid_choice_title = (invalid_choice_title if invalid_choice_title is not None else
                                      _("Element '%r' does not exist anymore"))
        self._invalid_choice_error = (
            invalid_choice_error if invalid_choice_error is not None else
            _("The selected element is not longer available. Please select something else."))
        self._no_preselect = no_preselect
        self._no_preselect_value = no_preselect_value
        self._no_preselect_title = no_preselect_title
        self._no_preselect_error = (no_preselect_error if no_preselect_error is not None else
                                    _("Please make a selection"))
        self._on_change = on_change
        self._read_only = read_only
        self._encode_value = encode_value

    def choices(self):
        # type: () -> List[DropdownChoiceEntry]
        if callable(self._choices):
            result = self._choices()
        else:
            result = self._choices
        if self._no_preselect:
            return [(self._no_preselect_value, self._no_preselect_title)] + result
        return result

    def canonical_value(self):
        # type: () -> DropdownChoiceValue
        choices = self.choices()
        if len(choices) > 0:
            return choices[0][0]
        return None

    def render_input(self, varprefix, value):
        # type: (str, DropdownChoiceValue) -> None
        if self._label:
            html.write("%s " % self._label)

        choices = self.choices()
        defval = choices[0][0] if choices else None
        options = []
        for entry in choices:
            if self._prefix_values:
                entry = (entry[0], "%s - %s" % entry)

            options.append(entry)
            if entry[0] == value:
                defval = entry[0]

        # In complain mode: Use the value received from the HTML variable
        if self._invalid_choice == "complain" and value is not None and self._value_is_invalid(
                value):
            defval = value
            options.append((defval, self._get_invalid_choice_title(value)))

        if value is None and not options:
            html.write(self._empty_text)
            return

        if len(options) == 0:
            html.write(self._empty_text)
            return

        html.dropdown(varprefix,
                      self._options_for_html(options),
                      deflt=self._option_for_html(defval),
                      onchange=self._on_change,
                      ordered=self._sorted,
                      read_only=self._read_only)

    def _get_invalid_choice_title(self, value):
        # type: (DropdownChoiceValue) -> Text
        if "%s" in self._invalid_choice_title or "%r" in self._invalid_choice_title:
            return self._invalid_choice_title % (value,)
        return self._invalid_choice_title

    def value_to_text(self, value):
        # type: (DropdownChoiceValue) -> Text
        for val, title in self.choices():
            if value == val:
                if self._help_separator:
                    return escaping.escape_attribute(
                        title.split(self._help_separator, 1)[0].strip())
                return escaping.escape_attribute(title)
        return escaping.escape_attribute(self._get_invalid_choice_title(value))

    def value_to_json(self, value):
        return value

    def value_from_json(self, json_value):
        return json_value

    def from_html_vars(self, varprefix):
        # type: (str) -> DropdownChoiceValue
        choices = self.choices()

        for val, _title in choices:
            if self._is_selected_option_from_html(varprefix, val):
                return val

        if self._invalid_choice == "replace":
            return self.default_value()  # garbled URL or len(choices) == 0
        if not choices:
            raise MKUserError(varprefix, self._empty_text)
        raise MKUserError(varprefix, self._invalid_choice_error)

    def _is_selected_option_from_html(self, varprefix, val):
        # type: (str, DropdownChoiceValue) -> bool
        selected_value = html.request.var(varprefix)
        return selected_value == self._option_for_html(val)

    def _option_for_html(self, value):
        # type: (DropdownChoiceValue) -> DropdownChoiceValue
        if self._encode_value:
            return self.option_id(value)
        return value

    def _options_for_html(self, orig_options):
        # type: (List[DropdownChoiceEntry]) -> List[_Tuple[DropdownChoiceValue, Text]]
        return [(self._option_for_html(val), title) for val, title in orig_options]

    @staticmethod
    def option_id(val):
        # type: () -> str
        return "%s" % hashlib.sha256(six.ensure_binary(repr(val))).hexdigest()

    def _validate_value(self, value, varprefix):
        # type: (DropdownChoiceValue, str) -> None
        if self._no_preselect and value == self._no_preselect_value:
            raise MKUserError(varprefix, self._no_preselect_error)

        if self._invalid_choice == "complain" and self._value_is_invalid(value):
            if value is not None:
                raise MKUserError(varprefix, self._invalid_choice_error)
            raise MKUserError(varprefix, self._empty_text)

    def _value_is_invalid(self, value):
        # type: (DropdownChoiceValue) -> bool
        return all(value != val for val, _title in self.choices())


# TODO: Rename to ServiceState() or something like this
def MonitoringState(**kwargs):
    """Special convenience variant for monitoring states"""
    kwargs.setdefault("default_value", 0)
    return DropdownChoice(choices=[
        (0, _("OK")),
        (1, _("WARN")),
        (2, _("CRIT")),
        (3, _("UNKNOWN")),
    ],
                          **kwargs)


def HostState(**kwargs):
    kwargs.setdefault("default_value", 0)
    return DropdownChoice(choices=[
        (0, _("UP")),
        (1, _("DOWN")),
        (2, _("UNREACHABLE")),
    ], **kwargs)


CascadingDropdownChoiceElementValue = Union[None, Text, str, bool, int]
CascadingDropdownChoiceValue = Union[CascadingDropdownChoiceElementValue,
                                     _Tuple[CascadingDropdownChoiceElementValue, Any]]
CascadingDropdownCleanChoice = _Tuple[CascadingDropdownChoiceElementValue, Text,
                                      _Optional[ValueSpec]]
CascadingDropdownShortChoice = _Tuple[CascadingDropdownChoiceElementValue, Text]
CascadingDropdownChoice = Union[CascadingDropdownShortChoice, CascadingDropdownCleanChoice]
CascadingDropdownChoices = Union[List[CascadingDropdownChoice],
                                 Callable[[], List[CascadingDropdownChoice]]]


def _normalize_choices(choices):
    # type: (List[CascadingDropdownChoice]) -> List[CascadingDropdownCleanChoice]
    return [(c[0], c[1], _sub_valuespec(c)) for c in choices]


def _sub_valuespec(choice):
    # type: (CascadingDropdownChoice) -> _Optional[ValueSpec]
    if len(choice) == 2:
        return None
    if len(choice) == 3:
        # NOTE: mypy is too dumb to figure out tuple lengths, so we use the funny "+ 0" below. Fragile...
        vs = choice[2 + 0]
        if vs is None or isinstance(vs, ValueSpec):
            return vs
    raise Exception("invalid CascadingDropdownChoice %r" % (choice,))


class CascadingDropdown(ValueSpec):
    """A Dropdown choice where the elements are ValueSpecs.

    The currently selected ValueSpec will be displayed.  The text
    representations of the ValueSpecs will be used as texts.  A ValueSpec of
    None is also allowed and will return the value None. It is also allowed to
    leave out the value spec for some of the choices (which is the same as
    using None).

    The resulting value is either a single value (if no value spec is defined
    for the selected entry) or a pair of (x, y) where x is the value of the
    selected entry and y is the value of the valuespec assigned to that entry.
    choices is a list of triples: [ ( value, title, vs ), ... ]
    """
    class Render(Enum):
        normal = "normal"
        foldable = "foldable"

    def __init__(  # pylint: disable=redefined-builtin
        self,
        choices,  # type: CascadingDropdownChoices
        label=None,  # type: _Optional[Text]
        separator=", ",  # type: Text
        sorted=True,  # type: bool
        orientation="vertical",  # type: Text
        render=None,  # type: _Optional[CascadingDropdown.Render]
        no_elements_text=None,  # type: _Optional[Text]
        no_preselect=False,  # type: bool
        no_preselect_value=None,  # type: _Optional[Any]
        no_preselect_title="",  # type: Text
        no_preselect_error=None,  # type: _Optional[Text]
        render_sub_vs_page_name=None,  # type: _Optional[Text]
        render_sub_vs_request_vars=None,  # type: _Optional[Dict]
        # ValueSpec
        title=None,  # type: _Optional[Text]
        help=None,  # type: _Optional[ValueSpecHelp]
        default_value=DEF_VALUE,  # type: Any
        validate=None,  # type: _Optional[ValueSpecValidateFunc]
    ):
        super(CascadingDropdown, self).__init__(title=title,
                                                help=help,
                                                default_value=default_value,
                                                validate=validate)

        if isinstance(choices, list):
            self._choices = _normalize_choices(
                choices
            )  # type: Union[List[CascadingDropdownCleanChoice], Callable[[], List[CascadingDropdownChoice]]]
        else:
            # function, store for later
            self._choices = choices

        self._label = label
        self._separator = separator
        self._sorted = sorted
        self._orientation = orientation  # or horizontal
        self._render = render if render is not None else CascadingDropdown.Render.normal

        self._no_elements_text = no_elements_text if no_elements_text is not None else _(
            "There are no elements defined for this selection")

        self._no_preselect = no_preselect
        self._no_preselect_value = no_preselect_value
        self._no_preselect_title = no_preselect_title  # if not preselected
        self._no_preselect_error = no_preselect_error if no_preselect_error is not None else _(
            "Please make a selection")

        # When given, this ajax page is called to render the input fields of a cascaded valuespec
        # once the user selected this choice in case it was initially hidden.
        self._render_sub_vs_page_name = render_sub_vs_page_name
        self._render_sub_vs_request_vars = render_sub_vs_request_vars or {}

    def choices(self):
        # type: () -> List[CascadingDropdownCleanChoice]
        if isinstance(self._choices, list):
            result = self._choices  # type: List[CascadingDropdownCleanChoice]
        else:
            result = _normalize_choices(self._choices())

        if self._no_preselect:
            choice = (self._no_preselect_value, self._no_preselect_title, None
                     )  # type: CascadingDropdownCleanChoice
            result = [choice] + result

        return result

    def canonical_value(self):
        # type: () -> CascadingDropdownChoiceValue
        choices = self.choices()
        if not choices:
            return None

        if choices[0][2] is not None:
            return choices[0][0], choices[0][2].canonical_value()
        return choices[0][0]

    def default_value(self):
        # type: () -> CascadingDropdownChoiceValue
        try:
            return self._default_value
        except Exception:
            choices = self.choices()
            if not choices:
                return None

            if choices[0][2] is not None:
                return choices[0][0], choices[0][2].default_value()
            return choices[0][0]

    def render_input(self, varprefix, value):
        # type: (str, CascadingDropdownChoiceValue) -> None
        def_val = '0'
        options = []  # type: Choices
        choices = self.choices()
        if not choices:
            html.write(self._no_elements_text)
            return

        for nr, (val, title, vs) in enumerate(choices):
            options.append((str(nr), title))
            # Determine the default value for the select, so the
            # the dropdown pre-selects the line corresponding with value.
            # Note: the html.dropdown() with automatically show the modified
            # selection, if the HTML variable varprefix_sel aleady
            # exists.
            if value == val or (isinstance(value, tuple) and value[0] == val):
                def_val = str(nr)

        vp = varprefix + "_sel"
        onchange = "cmk.valuespecs.cascading_change(this, '%s', %d);" % (varprefix, len(choices))
        html.dropdown(vp,
                      options,
                      deflt=def_val,
                      onchange=onchange,
                      ordered=self._sorted,
                      label=self._label)

        # make sure, that the visibility is done correctly, in both
        # cases:
        # 1. Form painted for the first time (no submission yet, vp missing in URL)
        # 2. Form already submitted -> honor URL variable vp for visibility
        cur_val = html.request.var(vp)

        if self._orientation == "vertical":
            html.br()
        else:
            html.nbsp()

        for nr, (val, title, vs) in enumerate(choices):
            if not vs:
                continue

            vp = "%s_%d" % (varprefix, nr)
            if cur_val is not None:
                # Form already submitted once (and probably in complain state)
                show = nr == int(cur_val)

                def_val_2 = vs.default_value()
                # Only try to get the current value for the currently selected choice
                if show:
                    try:
                        def_val_2 = vs.from_html_vars(vp)
                    except MKUserError:
                        pass  # Fallback to default value here

            else:
                # Form painted the first time
                if nr == int(def_val):
                    # This choice is the one choosen by the given value
                    if isinstance(value, tuple) and len(value) == 2:
                        def_val_2 = value[1]
                    else:
                        def_val_2 = vs.default_value()

                    show = True
                else:
                    def_val_2 = vs.default_value()
                    show = False

            if not self._render_sub_vs_page_name or show:
                html.open_span(id_="%s_sub" % vp, style="display:%s;" % ("" if show else "none"))
                self.show_sub_valuespec(vp, vs, def_val_2)
                html.close_span()
            else:
                self._show_sub_valuespec_container(vp, val, def_val_2)

    def show_sub_valuespec(self, varprefix, vs, value):
        # type: (str, ValueSpec, Any) -> None
        html.help(vs.help())
        vs.render_input(varprefix, value)

    def _show_sub_valuespec_container(self, varprefix, choice_id, value):
        # type: (str, CascadingDropdownChoiceElementValue, Any) -> None
        html.span("", id_="%s_sub" % varprefix)

        request_vars = {
            "varprefix": varprefix,
            "choice_id": repr(choice_id),
            "encoded_value": repr(value),
        }
        request_vars.update(self._render_sub_vs_request_vars)

        html.javascript("cmk.valuespecs.add_cascading_sub_valuespec_parameters(%s, %s);" %
                        (json.dumps(varprefix),
                         json.dumps({
                             "page_name": self._render_sub_vs_page_name,
                             "request_vars": request_vars,
                         })))

    def value_to_text(self, value):
        # type: (CascadingDropdownChoiceValue) -> Text
        choices = self.choices()
        for val, title, vs in choices:
            if not vs:  # Handle choices without nested valuespec
                if value == val:
                    return title
                continue

            assert isinstance(value, tuple)

            if not value:
                continue

            if value[0] != val:
                continue  # Skip not selected choices

            rendered_value = vs.value_to_text(value[1])
            if not rendered_value:
                return title

            if self._render == CascadingDropdown.Render.foldable:
                with html.plugged():
                    html.begin_foldable_container("foldable_cascading_dropdown",
                                                  id_=hashlib.sha256(six.ensure_binary(
                                                      repr(value))).hexdigest(),
                                                  isopen=False,
                                                  title=title,
                                                  indent=False)
                    html.write(vs.value_to_text(value[1]))
                    html.end_foldable_container()
                return html.drain()

            return title + self._separator + vs.value_to_text(value[1])

        return u""  # Nothing selected? Should never happen

    def value_to_json(self, value):
        choices = self.choices()

        for ident, _title, vs in choices:
            # Determine the default value for the select, so the
            # the dropdown pre-selects the line corresponding with value.
            # Note: the html.dropdown() with automatically show the modified
            # selection, if the HTML variable varprefix_sel aleady
            # exists.

            # Simple text match
            if isinstance(value, str) and value == ident:
                return value

            if not vs:
                continue

            try:
                vs.validate_datatype(value[1], "")
                return [ident, vs.value_to_json(value[1])]
            except Exception:  # TODO: fix exc
                continue

    def value_from_json(self, json_value):
        choices = self.choices()

        for ident, _title, vs in choices:
            if json_value == ident:
                return json_value

            if not vs:
                continue

            try:
                value = vs.value_from_json(json_value[1])
                vs.validate_datatype(value, "")
                return (ident, value)
            except Exception:  # TODO: fix exc
                continue

    def from_html_vars(self, varprefix):
        # type: (str) -> CascadingDropdownChoiceValue
        choices = self.choices()

        # No choices and "no elements text" is shown: The html var is
        # not present and no choice can be made. So fallback to default
        # value and let the validation methods lead to an error message.
        if not choices:
            return self.default_value()

        sel = html.request.get_integer_input_mandatory(varprefix + "_sel", 0)
        choice_val, _title, vs = choices[sel]
        if vs:
            return choice_val, vs.from_html_vars(varprefix + "_%d" % sel)
        return choice_val

    def validate_datatype(self, value, varprefix):
        # type: (CascadingDropdownChoiceValue, str) -> None
        choices = self.choices()
        for nr, (val, _title, vs) in enumerate(choices):
            if value == val or (isinstance(value, tuple) and value[0] == val):
                if vs:
                    if not isinstance(value, tuple) or len(value) != 2:
                        raise MKUserError(varprefix + "_sel",
                                          _("Value must be a tuple with two elements."))
                    vs.validate_datatype(value[1], varprefix + "_%d" % nr)
                return
        raise MKUserError(varprefix + "_sel", _("Value %r is not allowed here.") % value)

    def _validate_value(self, value, varprefix):
        # type: (CascadingDropdownChoiceValue, str) -> None
        if self._no_preselect and value == self._no_preselect_value:
            raise MKUserError(varprefix + "_sel", self._no_preselect_error)

        choices = self.choices()
        for nr, (val, _title, vs) in enumerate(choices):
            if value == val or (isinstance(value, tuple) and value[0] == val):
                if vs:
                    assert isinstance(value, tuple)
                    vs.validate_value(value[1], varprefix + "_%d" % nr)
                return
        raise MKUserError(varprefix + "_sel", _("Value %r is not allowed here.") % (value,))


ListChoiceChoiceValue = Union[Text, str, int]
ListChoiceChoicePairs = Sequence[_Tuple[ListChoiceChoiceValue, Text]]
ListChoiceChoices = Union[None, ListChoiceChoicePairs, Callable[[], ListChoiceChoicePairs],
                          Dict[ListChoiceChoiceValue, Text]]


class ListChoice(ValueSpec):
    """A list of checkboxes representing a list of values"""
    @staticmethod
    def dict_choices(choices):
        return [("%s" % type_id, "%d - %s" % (type_id, type_name))
                for (type_id, type_name) in sorted(choices.items())]

    def __init__(  # pylint: disable=redefined-builtin
        self,
        # ListChoice
        choices=None,  # type: ListChoiceChoices
        columns=1,  # type: int
        allow_empty=True,  # type: bool
        empty_text=None,  # type: _Optional[Text]
        render_function=None,  # type: _Optional[Callable[[Text, Text], Text]]
        toggle_all=False,  # type: bool
        # TODO: Rename to "orientation" to be in line with other valuespecs
        render_orientation="horizontal",  # type: Text
        no_elements_text=None,  # type: _Optional[Text]
        # ValueSpec
        title=None,  # type: _Optional[Text]
        help=None,  # type: _Optional[ValueSpecHelp]
        default_value=DEF_VALUE,  # type: Any
        validate=None,  # type: _Optional[ValueSpecValidateFunc]
    ):
        super(ListChoice, self).__init__(title=title,
                                         help=help,
                                         default_value=default_value,
                                         validate=validate)
        self._choices = choices
        self._columns = columns
        self._allow_empty = allow_empty
        self._empty_text = empty_text if empty_text is not None else _("(nothing selected)")
        self._loaded_at = None  # type: _Optional[int]
        self._render_function = render_function if render_function is not None else (
            lambda id, val: val)
        self._toggle_all = toggle_all
        self._render_orientation = render_orientation  # other: vertical
        self._no_elements_text = no_elements_text if no_elements_text is not None else \
            _("There are no elements defined for this selection")

    # In case of overloaded functions with dynamic elements
    def load_elements(self):
        if self._choices is None:
            if self._loaded_at != id(html):
                self._elements = self.get_elements()
                self._loaded_at = id(html)  # unique for each query!
        elif isinstance(self._choices, Sequence):
            self._elements = self._choices
        elif isinstance(self._choices, dict):
            self._elements = self.dict_choices(self._choices)
        elif callable(self._choices):
            self._elements = self._choices()
        else:
            raise ValueError("illegal type for choices")

    def get_elements(self):
        raise NotImplementedError()

    def canonical_value(self):
        return []

    def _draw_listchoice(self, varprefix, value, elements, columns, toggle_all):

        if self._toggle_all:
            html.a(_("Check / Uncheck all"),
                   href="javascript:cmk.valuespecs.list_choice_toggle_all('%s')" % varprefix)

        html.open_table(id_="%s_tbl" % varprefix, class_=["listchoice"])
        for nr, (key, title) in enumerate(elements):
            if nr % self._columns == 0:
                if nr > 0:
                    html.close_tr()
                html.open_tr()
            html.open_td()
            html.checkbox("%s_%d" % (varprefix, nr), key in value, label=title)
            html.close_td()
        html.close_tr()
        html.close_table()

    def render_input(self, varprefix, value):
        self.load_elements()
        if not self._elements:
            html.write(self._no_elements_text)
            return

        self._draw_listchoice(varprefix, value, self._elements, self._columns, self._toggle_all)

        # Make sure that at least one variable with the prefix is present
        html.hidden_field(varprefix, "1", add_var=True)

    def value_to_text(self, value):
        if not value:
            return self._empty_text

        self.load_elements()
        d = dict(self._elements)
        texts = [self._render_function(v, d.get(v, v)) for v in value]
        if self._render_orientation == "horizontal":
            return ", ".join(texts)

        # TODO: This is a workaround for a bug. This function needs to return str objects right now.
        return "%s" % html.render_table(
            html.render_tr(html.render_td(html.render_br().join(HTML(x) for x in texts))))
        #OLD: return "<table><tr><td>" + "<br>".join(texts) + "</td></tr></table>"

    def from_html_vars(self, varprefix):
        self.load_elements()
        return [
            key  #
            for nr, (key, _title) in enumerate(self._elements)
            if html.get_checkbox("%s_%d" % (varprefix, nr))
        ]

    def validate_datatype(self, value, varprefix):
        if not isinstance(value, list):
            raise MKUserError(varprefix,
                              _("The datatype must be list, but is %s") % _type_name(value))

    def _validate_value(self, value, varprefix):
        if not self._allow_empty and not value:
            raise MKUserError(varprefix, _('You have to select at least one element.'))
        self.load_elements()
        for v in value:
            if self._value_is_invalid(v):
                raise MKUserError(varprefix, _("%s is not an allowed value") % v)

    def _value_is_invalid(self, value):
        # type: (ListChoiceChoiceValue) -> bool
        return all(value != val for val, _title in self._elements)


class DualListChoice(ListChoice):
    """Implements a choice of items which is realized with two ListChoices
    select fields.

    One contains every unselected item and the other one contains the selected
    items.  Optionally you can have the user influence the order of the entries
    by simply clicking them in a certain order.  If that feature is not being
    used, then the original order of the elements is kept.

    Beware: the keys in this choice are not type safe.  They can only be
    strings. They must not contain | or other dangerous characters. We should
    fix this and make it this compatible to DropdownChoice()
    """
    def __init__(  # pylint: disable=redefined-builtin
        self,
        # DualListChoice
        autoheight=False,  # type: bool
        custom_order=False,  # type: bool
        instant_add=False,  # type: bool
        enlarge_active=False,  # type: bool
        rows=None,  # type: _Optional[int]
        size=None,  # type: _Optional[int]
        # ListChoice
        choices=None,  # type: ListChoiceChoices
        columns=1,  # type: int
        allow_empty=True,  # type: bool
        empty_text=None,  # type: _Optional[Text]
        render_function=None,  # type: _Optional[Callable[[Text, Text], Text]]
        toggle_all=False,  # type: bool
        # TODO: Rename to "orientation" to be in line with other valuespecs
        render_orientation="horizontal",  # type: Text
        no_elements_text=None,  # type: _Optional[Text]
        # ValueSpec
        title=None,  # type: _Optional[Text]
        help=None,  # type: _Optional[ValueSpecHelp]
        default_value=DEF_VALUE,  # type: Any
        validate=None,  # type: _Optional[ValueSpecValidateFunc]
    ):
        super(DualListChoice, self).__init__(choices=choices,
                                             columns=columns,
                                             allow_empty=allow_empty,
                                             empty_text=empty_text,
                                             render_function=render_function,
                                             toggle_all=toggle_all,
                                             render_orientation=render_orientation,
                                             no_elements_text=no_elements_text,
                                             title=title,
                                             help=help,
                                             default_value=default_value,
                                             validate=validate)
        self._autoheight = autoheight
        self._custom_order = custom_order
        self._instant_add = instant_add
        self._enlarge_active = enlarge_active
        if rows is not None:
            self._rows = rows
            self._autoheight = False
        else:
            self._rows = 5
        self._size = size  # Total width in ex

    def render_input(self, varprefix, value):
        self.load_elements()
        if not self._elements:
            html.write_text(_("There are no elements for selection."))
            return

        # Use values from HTTP request in complain mode
        if value is None:
            value = self.from_html_vars(varprefix)

        selected = []
        unselected = []
        if self._custom_order:
            edict = dict(self._elements)
            allowed_keys = edict.keys()
            for v in value:
                if v in allowed_keys:
                    selected.append((v, edict[v]))

            for v, _name in self._elements:
                if v not in value:
                    unselected.append((v, edict[v]))
        else:
            for e in self._elements:
                if e[0] in value:
                    selected.append(e)
                else:
                    unselected.append(e)

        select_func = 'cmk.valuespecs.duallist_switch(\'unselected\', \'%s\', %d);' % (
            varprefix, 1 if self._custom_order else 0)
        unselect_func = 'cmk.valuespecs.duallist_switch(\'selected\', \'%s\', %d);' % (
            varprefix, 1 if self._custom_order else 0)

        html.open_table(class_=["vs_duallist"],
                        style="width: %dpx;" % (self._size * 6.4) if self._size else None)

        html.open_tr()
        html.open_td(class_="head")
        html.write_text(_('Available'))
        if not self._instant_add:
            html.a(">", href="javascript:%s;" % select_func, class_=["control", "add"])
        html.close_td()

        html.open_td(class_="head")
        html.write_text(_('Selected'))
        if not self._instant_add:
            html.a("<", href="javascript:%s;" % unselect_func, class_=["control", "del"])
        html.close_td()
        html.close_tr()

        html.open_tr()
        for suffix, choices, select_func in [
            ("unselected", unselected, select_func),
            ("selected", selected, unselect_func),
        ]:

            onchange_func = select_func if self._instant_add else ''
            if self._enlarge_active:
                onchange_func = 'cmk.valuespecs.duallist_enlarge(%s, %s);' % (json.dumps(suffix),
                                                                              json.dumps(varprefix))

            html.open_td()
            html.dropdown(
                "%s_%s" % (varprefix, suffix),
                choices,
                deflt='',
                ordered=self._custom_order,
                multiple="multiple",
                style='height:auto' if self._autoheight else "height: %dpx" % (self._rows * 16),
                ondblclick=select_func if not self._instant_add else '',
                onchange=onchange_func,
            )

            html.close_td()
        html.close_tr()

        html.close_table()
        html.hidden_field(varprefix,
                          '|'.join([k for k, v in selected]),
                          id_=varprefix,
                          add_var=True)

    def _validate_value(self, value, varprefix):
        try:
            super(DualListChoice, self)._validate_value(value, varprefix)
        except MKUserError as e:
            v = "" if e.varname is None else e.varname
            raise MKUserError(v + "_selected", e.message)

    def from_html_vars(self, varprefix):
        self.load_elements()
        value = []  # type: List
        selection_str = html.request.var(varprefix, '')
        if selection_str is None:
            return value
        selected = selection_str.split('|')
        if self._custom_order:
            edict = dict(self._elements)
            allowed_keys = edict.keys()
            for v in selected:
                if v in allowed_keys:
                    value.append(v)
        else:
            for key, _title in self._elements:
                if key in selected:
                    value.append(key)
        return value


class OptionalDropdownChoice(DropdownChoice):
    """A type-safe dropdown choice with one extra field that
    opens a further value spec for entering an alternative
    Value."""
    def __init__(  # pylint: disable=redefined-builtin
        self,
        explicit,  # type: ValueSpec
        choices,  # type: DropdownChoices
        otherlabel=None,  # type: _Optional[Text]
        # DropdownChoice
        sorted=False,  # type: bool
        label=None,  # type: _Optional[Text]
        help_separator=None,  # type: Text
        prefix_values=False,  # type: bool
        empty_text=None,  # type: _Optional[Text]
        invalid_choice="complain",  # type: _Optional[str]
        invalid_choice_title=None,  # type: _Optional[Text]
        invalid_choice_error=None,  # type: _Optional[Text]
        no_preselect=False,  # type: bool
        no_preselect_value=None,  # type: Any
        no_preselect_title="",  # type: Text
        no_preselect_error=None,  # type: Text
        on_change=None,  # type: Text
        read_only=False,  # type: bool
        encode_value=True,  # type: bool
        # ValueSpec
        title=None,  # type: _Optional[Text]
        help=None,  # type: _Optional[ValueSpecHelp]
        default_value=DEF_VALUE,  # type: Any
        validate=None,  # type: _Optional[ValueSpecValidateFunc]
    ):
        super(OptionalDropdownChoice, self).__init__(choices=choices,
                                                     sorted=sorted,
                                                     label=label,
                                                     help_separator=help_separator,
                                                     prefix_values=prefix_values,
                                                     empty_text=empty_text,
                                                     invalid_choice=invalid_choice,
                                                     invalid_choice_title=invalid_choice_title,
                                                     invalid_choice_error=invalid_choice_error,
                                                     no_preselect=no_preselect,
                                                     no_preselect_value=no_preselect_value,
                                                     no_preselect_title=no_preselect_title,
                                                     no_preselect_error=no_preselect_error,
                                                     on_change=on_change,
                                                     read_only=read_only,
                                                     encode_value=encode_value,
                                                     title=title,
                                                     help=help,
                                                     default_value=default_value,
                                                     validate=validate)

        self._explicit = explicit
        self._otherlabel = otherlabel if otherlabel is not None else _("Other")

    def canonical_value(self):
        return self._explicit.canonical_value()

    def value_is_explicit(self, value):
        return value not in [c[0] for c in self.choices()]

    def render_input(self, varprefix, value):
        defval = "other"
        options = []  # type: List[_Tuple[Union[None, str, Text], Text]]
        for n, (val, title) in enumerate(self.choices()):
            options.append((str(n), title))
            if val == value:
                defval = str(n)
        if self._sorted:
            options.sort(key=lambda x: x[1])
        options.append(("other", self._otherlabel))
        html.dropdown(
            varprefix,
            options,
            deflt=defval,  # style="float:left;",
            onchange="cmk.valuespecs.toggle_dropdown(this, '%s_ex');" % varprefix)
        if html.request.has_var(varprefix):
            div_is_open = html.request.var(varprefix) == "other"
        else:
            div_is_open = self.value_is_explicit(value)

        html.open_span(id_="%s_ex" % varprefix,
                       style=["white-space: nowrap;", None if div_is_open else "display:none;"])
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
        sel = html.request.var(varprefix)
        if sel == "other":
            return self._explicit.from_html_vars(varprefix + "_ex")

        for n, (val, _title) in enumerate(choices):
            if sel == str(n):
                return val
        return choices[0][0]  # can only happen if user garbled URL

    def _validate_value(self, value, varprefix):
        if self.value_is_explicit(value):
            self._explicit.validate_value(value, varprefix)

    def validate_datatype(self, value, varprefix):
        for val, _title in self.choices():
            if val == value:
                return
        self._explicit.validate_datatype(value, varprefix + "_ex")


def round_date(t):
    return int(int(t) / seconds_per_day) * seconds_per_day


def today():
    return round_date(time.time())


# TODO: Cleanup kwargs
def Weekday(**kwargs):
    return DropdownChoice(choices=sorted(defines.weekdays().items()), **kwargs)


class RelativeDate(OptionalDropdownChoice):
    """Input of date with optimization for nearby dates in the future

    Useful for example for alarms. The date is represented by a UNIX timestamp
    where the seconds are silently ignored."""
    def __init__(self, **kwargs):
        choices = [
            (0, _("today")),
            (1, _("tomorrow")),
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

        kwargs['choices'] = choices
        kwargs['explicit'] = Integer()
        kwargs['otherlabel'] = _("in ... days")

        super(RelativeDate, self).__init__(**kwargs)

        if "default_days" in kwargs:
            self._default_value = kwargs["default_days"] * seconds_per_day + today()
        else:
            self._default_value = today()

    def canonical_value(self):
        return self._default_value

    def render_input(self, varprefix, value):
        reldays = int((round_date(value) - today()) / seconds_per_day)  # fixed: true-division
        super(RelativeDate, self).render_input(varprefix, reldays)

    def value_to_text(self, value):
        reldays = int((round_date(value) - today()) / seconds_per_day)  # fixed: true-division
        if reldays == -1:
            return _("yesterday")
        if reldays == -2:
            return _("two days ago")
        if reldays < 0:
            return _("%d days ago") % -reldays
        choices = self.choices()  # TODO: Is this correct with no_preselect?
        if reldays < len(choices):
            return choices[reldays][1]
        return _("in %d days") % reldays

    def from_html_vars(self, varprefix):
        reldays = super(RelativeDate, self).from_html_vars(varprefix)
        return today() + reldays * seconds_per_day

    def validate_datatype(self, value, varprefix):
        if not isinstance(value, (int, float)):
            raise MKUserError(varprefix, _("Date must be a number value"))


class AbsoluteDate(ValueSpec):
    """A ValueSpec for editing a date

    The date is represented as a UNIX timestamp x where x % seconds_per_day is
    zero (or will be ignored if non-zero), as long as include_time is not set
    to True"""
    def __init__(self, **kwargs):
        super(AbsoluteDate, self).__init__(**kwargs)
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
        self._submit_form_name = kwargs.get("submit_form_name")

    def default_value(self):
        if self._default_value is not None:
            return self._default_value

        if self._allow_empty:
            return None

        if self._include_time:
            return time.time()
        return today()

    def canonical_value(self):
        return self.default_value()

    def split_date(self, value):
        # type: (_Optional[float]) -> _Tuple[_Optional[int], _Optional[int], _Optional[int], _Optional[int], _Optional[int], _Optional[int]]
        if self._none_means_empty and value is None:
            return None, None, None, None, None, None
        lt = time.localtime(value)
        return lt.tm_year, lt.tm_mon, lt.tm_mday, lt.tm_hour, lt.tm_min, lt.tm_sec

    def render_input(self, varprefix, value):
        # type: (Any, Any) -> None
        if self._label:
            html.write("%s" % self._label)
            html.nbsp()

        year, month, day, hour, mmin, sec = self.split_date(value)
        values = [
            ("_year", year, 6),
            ("_month", month, 3),
            ("_day", day, 3),
        ]  # type: List[_Optional[_Tuple[str, _Optional[int], int]]]
        if self._include_time:
            values += [
                None,
                ("_hour", hour, 2),
                ("_min", mmin, 2),
                ("_sec", sec, 2),
            ]

        if self._show_titles:
            titles = [_("Year"), _("Month"), _("Day")]
            if self._include_time:
                titles += ['', _("Hour"), _("Minute"), _("Sec.")]

            html.open_table(class_=["vs_date"])

            html.open_tr()
            for t in titles:
                html.th(t)
            html.close_tr()

            html.open_tr()
            for val in values:
                html.open_td()
                if val is None:
                    html.nbsp()
                else:
                    html.text_input(
                        varprefix + val[0],
                        default_value=str(val[1]) if val[1] else "",
                        size=val[2],
                        cssclass="number",
                        submit=self._submit_form_name,
                    )
                html.close_td()
            html.close_tr()

            html.close_table()

        else:
            for count, val in enumerate(values):
                if count > 0:
                    html.write_text(" ")
                if val is None:
                    html.nbsp()
                else:
                    html.text_input(
                        varprefix + val[0],
                        default_value=str(val[1]),
                        size=val[2],
                        cssclass="number",
                        submit=self._submit_form_name,
                    )

    def set_focus(self, varprefix):
        html.set_focus(varprefix + "_year")

    def value_to_text(self, value):
        return time.strftime(self._format, time.localtime(value))

    def value_to_json(self, value):
        return value

    def value_from_json(self, json_value):
        return json_value

    # TODO: allow_empty is a *very* bad idea typing-wise! We are poisoned by Optional... :-P
    def from_html_vars(self, varprefix):
        # type: (str) -> _Optional[float]
        parts = []
        entries = [
            ("year", _("year"), 1970, 2038),
            ("month", _("month"), 1, 12),
            ("day", _("day"), 1, 31),
        ]

        if self._include_time:
            entries += [
                ("hour", _("hour"), 0, 23),
                ("min", _("min"), 0, 59),
                ("sec", _("sec"), 0, 59),
            ]

        for what, title, mmin, mmax in entries:
            try:
                varname = varprefix + "_" + what
                part_str = html.request.var(varname, "")
                if part_str is None:
                    raise ValueError()
                part = int(part_str)
            except ValueError:
                if self._allow_empty:
                    return None
                raise MKUserError(varname, _("Please enter a valid number"))
            if part < mmin or part > mmax:
                raise MKUserError(
                    varname,
                    _("The value for %s must be between %d and %d") % (title, mmin, mmax))
            parts.append(part)

        # Construct broken time from input fields. Assume no-dst
        parts += [0] * (3 if self._include_time else 6)
        # Convert to epoch
        epoch = time.mktime((
            parts[0],  # tm_year
            parts[1],  # tm_mon
            parts[2],  # tm_mday
            parts[3],  # tm_hour
            parts[4],  # tm_min
            parts[5],  # tm_sec
            parts[6],  # tm_wday
            parts[7],  # tm_yday
            parts[8],  # tm_isdst
        ))
        # Convert back to localtime in order to know DST setting
        localtime = time.localtime(epoch)
        # Enter DST setting of that time
        parts[-1] = localtime.tm_isdst
        # Convert to epoch again
        return time.mktime((
            parts[0],  # tm_year
            parts[1],  # tm_mon
            parts[2],  # tm_mday
            parts[3],  # tm_hour
            parts[4],  # tm_min
            parts[5],  # tm_sec
            parts[6],  # tm_wday
            parts[7],  # tm_yday
            parts[8],  # tm_isdst
        ))

    def validate_datatype(self, value, varprefix):
        if value is None and self._allow_empty:
            return
        if not isinstance(value, (int, float)):
            raise MKUserError(
                varprefix,
                _("The type of the timestamp must be int or float, but is %s") % _type_name(value))

    def _validate_value(self, value, varprefix):
        if (not self._allow_empty and value is None) or value < 0 or int(value) > (2**31 - 1):
            return MKUserError(varprefix, _("%s is not a valid UNIX timestamp") % value)


TimeofdayValue = _Tuple[int, int]


class Timeofday(ValueSpec):
    """Valuespec for entering times like 00:35 or 16:17

    Currently no seconds are supported. But this could easily be added.  The
    value itself is stored as a pair of integers, a.g.  (0, 35) or (16, 17). If
    the user does not enter a time the vs will return None.
    """
    def __init__(  # pylint: disable=redefined-builtin
        self,
        allow_24_00=False,  # type: bool
        allow_empty=True,  # type: bool
        # ValueSpec
        title=None,  # type: _Optional[Text]
        help=None,  # type: _Optional[ValueSpecHelp]
        default_value=DEF_VALUE,  # type: Any
        validate=None,  # type: _Optional[ValueSpecValidateFunc]
    ):
        super(Timeofday, self).__init__(title=title,
                                        help=help,
                                        default_value=default_value,
                                        validate=validate)
        self._allow_24_00 = allow_24_00
        self._allow_empty = allow_empty

    def canonical_value(self):
        # type: () -> _Optional[TimeofdayValue]
        if self._allow_empty:
            return None
        return (0, 0)

    def render_input(self, varprefix, value):
        # type: (str, _Optional[TimeofdayValue]) -> None
        text = ("%02d:%02d" % value) if value else ''
        html.text_input(varprefix, text, size=5)

    def value_to_text(self, value):
        # type: (_Optional[TimeofdayValue]) -> Text
        if value is None:
            return u""
        return u"%02d:%02d" % value

    def from_html_vars(self, varprefix):
        # type: (str) -> _Optional[TimeofdayValue]
        # Fully specified
        text = html.request.get_str_input_mandatory(varprefix, "").strip()
        if not text:
            return None

        if re.match("^(24|[0-1][0-9]|2[0-3]):[0-5][0-9]$", text):
            hours, minutes = text.split(":")
            return int(hours), int(minutes)

        # only hours
        try:
            b = int(text)
            return (b, 0)
        except Exception:
            raise MKUserError(
                varprefix,
                _("Invalid time format '<tt>%s</tt>', please use <tt>24:00</tt> format.") % text)

    def validate_datatype(self, value, varprefix):
        # type: (_Optional[TimeofdayValue], str) -> None
        if self._allow_empty and value is None:
            return

        if not isinstance(value, tuple):
            raise MKUserError(varprefix,
                              _("The datatype must be tuple, but ist %s") % _type_name(value))

        if len(value) != 2:
            raise MKUserError(
                varprefix,
                _("The tuple must contain two elements, but you have %d") % len(value))

        for x in value:
            if not isinstance(x, int):
                raise MKUserError(
                    varprefix,
                    _("All elements of the tuple must be of type int, you have %s") % _type_name(x))

    def _validate_value(self, value, varprefix):
        # type: (_Optional[TimeofdayValue], str) -> None
        if not self._allow_empty and value is None:
            raise MKUserError(varprefix, _("Please enter a time."))

        if value is None:
            return

        if self._allow_24_00:
            max_value = (24, 0)
        else:
            max_value = (23, 59)

        if value > max_value:
            raise MKUserError(varprefix,
                              _("The time must not be greater than %02d:%02d.") % max_value)
        if value[0] < 0 or value[1] < 0 or value[0] > 24 or value[1] > 59:
            raise MKUserError(varprefix, _("Hours/Minutes out of range"))


TimeofdayRangeValue = _Tuple[_Tuple[int, int], _Tuple[int, int]]


class TimeofdayRange(ValueSpec):
    """Range like 00:15 - 18:30"""
    def __init__(  # pylint: disable=redefined-builtin
        self,
        allow_empty=True,  # type: bool
        # ValueSpec
        title=None,  # type: _Optional[Text]
        help=None,  # type: _Optional[ValueSpecHelp]
        default_value=DEF_VALUE,  # type: Any
        validate=None,  # type: _Optional[ValueSpecValidateFunc]
    ):
        super(TimeofdayRange, self).__init__(title=title,
                                             help=help,
                                             default_value=default_value,
                                             validate=validate)
        self._allow_empty = allow_empty
        self._bounds = (
            Timeofday(allow_empty=self._allow_empty, allow_24_00=True),
            Timeofday(allow_empty=self._allow_empty, allow_24_00=True),
        )

    def canonical_value(self):
        # type: () -> _Optional[TimeofdayRangeValue]
        if self._allow_empty:
            return None
        return (0, 0), (24, 0)

    def render_input(self, varprefix, value):
        # type: (str, _Optional[TimeofdayRangeValue]) -> None
        self._bounds[0].render_input(varprefix + "_from", value[0] if value is not None else None)
        html.nbsp()
        html.write_text("-")
        html.nbsp()
        self._bounds[1].render_input(varprefix + "_until", value[1] if value is not None else None)

    def value_to_text(self, value):
        # type: (_Optional[TimeofdayRangeValue]) -> Text
        if value is None:
            return u""

        return six.ensure_text(self._bounds[0].value_to_text(value[0]) + "-" +
                               self._bounds[1].value_to_text(value[1]))

    def from_html_vars(self, varprefix):
        # type: (str) -> _Optional[TimeofdayRangeValue]
        from_value = self._bounds[0].from_html_vars(varprefix + "_from")
        until_value = self._bounds[1].from_html_vars(varprefix + "_until")
        if (from_value is None) != (until_value is None):
            raise MKUserError(
                varprefix + "_from",
                _("Please leave either both from and until empty or enter two times."))
        if from_value is None:
            return None
        if until_value is None:
            return None
        return (from_value, until_value)

    def validate_datatype(self, value, varprefix):
        # type: (_Optional[TimeofdayRangeValue], str) -> None
        if self._allow_empty and value is None:
            return

        if not isinstance(value, tuple):
            raise MKUserError(varprefix,
                              _("The datatype must be tuple, but ist %s") % _type_name(value))

        if len(value) != 2:
            raise MKUserError(
                varprefix,
                _("The tuple must contain two elements, but you have %d") % len(value))

        self._bounds[0].validate_datatype(value[0], varprefix + "_from")
        self._bounds[1].validate_datatype(value[1], varprefix + "_until")

    def _validate_value(self, value, varprefix):
        # type: (_Optional[TimeofdayRangeValue], str) -> None
        if value is None:
            if self._allow_empty:
                return
            raise MKUserError(varprefix + "_from", _("Please enter a valid time of day range"))

        self._bounds[0].validate_value(value[0], varprefix + "_from")
        self._bounds[1].validate_value(value[1], varprefix + "_until")
        if value[0] > value[1]:
            raise MKUserError(
                varprefix + "_until",
                _("The <i>from</i> time must not be later then the <i>until</i> time."))


# TODO: We should *really* nuke that code below and use time/datetime.
class TimeHelper(object):
    @staticmethod
    def round(timestamp, unit):
        lt = time.localtime(timestamp)
        time_s = time.struct_time((
            lt.tm_year,
            lt.tm_mon,
            lt.tm_mday,
            0,  # tm_hour
            0,  # tm_min
            0,  # tm_sec
            lt.tm_wday,
            lt.tm_yday,
            -1,  # tm_isdst
        ))

        if unit == 'd':
            return time.mktime(time_s)
        if unit == 'w':
            days = time_s.tm_wday  # 0 based
        elif unit == 'm':
            days = time_s.tm_mday - 1  # 1 based
        elif unit == 'y':
            days = time_s.tm_yday - 1  # 1 based
        else:
            raise MKGeneralException("invalid time unit %s" % unit)

        return TimeHelper.round(time.mktime(time_s) - days * 86400 + 3600, 'd')

    @staticmethod
    def add(timestamp, count, unit):
        if unit == 'h':
            return timestamp + 3600 * count
        if unit == 'd':
            return timestamp + 86400 * count
        if unit == 'w':
            return timestamp + (7 * 86400) * count
        if unit == 'm':
            time_s = time.localtime(timestamp)
            years, months = divmod(abs(count), 12)
            if count < 0:
                years *= -1
                months *= -1
            return time.mktime((
                time_s.tm_year + years + (-1 if time_s.tm_mon <= 0 else 0),
                time_s.tm_mon + months + (12 if time_s.tm_mon <= 0 else 0),
                time_s.tm_mday,
                time_s.tm_hour,
                time_s.tm_min,
                time_s.tm_sec,
                time_s.tm_wday,
                time_s.tm_yday,
                -1,  # tm_isdst
            ))
        if unit == 'y':
            time_s = time.localtime(timestamp)
            return time.mktime((
                time_s.tm_year + count,
                time_s.tm_mon,
                time_s.tm_mday,
                time_s.tm_hour,
                time_s.tm_min,
                time_s.tm_sec,
                time_s.tm_wday,
                time_s.tm_yday,
                time_s.tm_isdst,
            ))
        MKGeneralException("invalid time unit %s" % unit)


class Timerange(CascadingDropdown):
    def __init__(  # pylint: disable=redefined-builtin
        self,
        allow_empty=False,  # type: bool
        include_time=False,  # type: bool
        choices=None,  # type: Union[None, List[CascadingDropdownChoice], Callable[[], List[CascadingDropdownChoice]]]
        # CascadingDropdown
        # TODO: Make this more specific
        label=None,  # type: _Optional[Text]
        separator=", ",  # type: Text
        sorted=False,  # type: bool
        orientation="vertical",  # type: Text
        render=None,  # type: _Optional[CascadingDropdown.Render]
        no_elements_text=None,  # type: _Optional[Text]
        no_preselect=False,  # type: bool
        no_preselect_value=None,  # type: _Optional[Any]
        no_preselect_title="",  # type: Text
        no_preselect_error=None,  # type: _Optional[Text]
        render_sub_vs_page_name=None,  # type: _Optional[Text]
        render_sub_vs_request_vars=None,  # type: _Optional[Dict]
        # ValueSpec
        title=None,  # type: _Optional[Text]
        help=None,  # type: _Optional[ValueSpecHelp]
        default_value=DEF_VALUE,  # type: Any
        validate=None,  # type: _Optional[ValueSpecValidateFunc]
    ):
        super(Timerange, self).__init__(
            choices=self._prepare_choices,
            label=label,
            separator=separator,
            sorted=sorted,
            orientation=orientation,
            render=render,
            no_elements_text=no_elements_text,
            no_preselect=no_preselect,
            no_preselect_value=no_preselect_value,
            no_preselect_title=no_preselect_title,
            no_preselect_error=no_preselect_error,
            render_sub_vs_page_name=render_sub_vs_page_name,
            render_sub_vs_request_vars=render_sub_vs_request_vars,
            title=title,
            help=help,
            default_value=default_value,
            validate=validate,
        )
        self._title = title if title is not None else _('Time range')
        self._allow_empty = allow_empty
        self._include_time = include_time
        self._fixed_choices = choices

    def _prepare_choices(self):
        # type: () -> List[CascadingDropdownChoice]
        # TODO: We have dispatching code like this all over place...
        if self._fixed_choices is None:
            choices = []  # type: List[CascadingDropdownChoice]
        elif isinstance(self._fixed_choices, list):
            choices = list(self._fixed_choices)
        elif callable(self._fixed_choices):
            choices = self._fixed_choices()
        else:
            raise ValueError("invalid type for choices")

        if self._allow_empty:
            choices += [(None, '', None)]

        choices += self._get_graph_timeranges() + [
            ("d0", _("Today")),
            ("d1", _("Yesterday")),
            ("w0", _("This week")),
            ("w1", _("Last week")),
            ("m0", _("This month")),
            ("m1", _("Last month")),
            ("y0", _("This year")),
            ("y1", _("Last year")),
            ("age", _("The last..."), Age()),
            ("date", _("Date range"),
             Tuple(orientation="horizontal",
                   title_br=False,
                   elements=[
                       AbsoluteDate(title=_("From:")),
                       AbsoluteDate(title=_("To:")),
                   ])),
        ]

        if self._include_time:
            choices += [("time", _("Date & time range"),
                         Tuple(orientation="vertical",
                               title_br=False,
                               elements=[
                                   AbsoluteDate(
                                       title=_("From:"),
                                       include_time=True,
                                   ),
                                   AbsoluteDate(
                                       title=_("To:"),
                                       include_time=True,
                                   ),
                               ]))]
        return choices

    def _get_graph_timeranges(self):
        try:
            import cmk.gui.config as config  # FIXME
            return [(('age', timerange_attrs["duration"]), timerange_attrs['title'])
                    for timerange_attrs in config.graph_timeranges]

        except AttributeError:  # only available in cee
            return [
                ("4h", _("The last 4 hours")),
                ("25h", _("The last 25 hours")),
                ("8d", _("The last 8 days")),
                ("35d", _("The last 35 days")),
                ("400d", _("The last 400 days")),
            ]

    def compute_range(self, rangespec):
        def _month_edge_days(now, day_id):
            # type: (float, Text) -> _Tuple[_Tuple[float, float], Text]
            # base time is current time rounded down to month
            from_time = TimeHelper.round(now, 'm')
            if day_id == 'f1':
                from_time = TimeHelper.add(from_time, -1, 'm')
            if day_id == 'l1':
                from_time -= 3600 * 24
            end_time = from_time + 3600 * 24
            return (from_time, end_time), time.strftime("%d/%m/%Y", time.localtime(from_time))

        if rangespec is None:
            rangespec = "4h"

        # Compatibility with previous versions
        elif rangespec[0] == "pnp_view":
            rangespec = {
                1: "4h",
                2: "25h",
                3: "8d",
                4: "35d",
                5: "400d",
            }.get(rangespec[1], "4h")

        now = time.time()

        if rangespec[0] == 'age':
            from_time = now - rangespec[1]
            until_time = now
            title = _("The last ") + Age().value_to_text(rangespec[1])
            return (from_time, until_time), title
        if rangespec[0] == 'next':
            from_time = now
            until_time = now + rangespec[1]
            title = _("The next ") + Age().value_to_text(rangespec[1])
            return (from_time, until_time), title
        if rangespec[0] == 'until':
            return (now, rangespec[1]), AbsoluteDate().value_to_text(rangespec[1])

        if rangespec[0] in ['date', 'time']:
            from_time, until_time = rangespec[1]
            if from_time > until_time:
                raise MKUserError("avo_rangespec_9_0_year",
                                  _("The end date must be after the start date"))
            if rangespec[0] == 'date':
                # add 25 hours, then round to 00:00 of that day. This accounts for
                # daylight-saving time
                until_time = TimeHelper.round(TimeHelper.add(until_time, 25, 'h'), 'd')
            title = AbsoluteDate().value_to_text(from_time) + " ... " + \
                    AbsoluteDate().value_to_text(until_time)
            return (from_time, until_time), title

        until_time = now
        if rangespec[0].isdigit():  # 4h, 400d
            count = int(rangespec[:-1])
            from_time = TimeHelper.add(now, count * -1, rangespec[-1])
            unit_name = {'d': "days", 'h': "hours"}[rangespec[-1]]
            title = _("Last %d %s") % (count, unit_name)
            return (from_time, now), title

        year, month = time.localtime(now)[:2]

        if rangespec in ['f0', 'f1', 'l1']:
            return _month_edge_days(now, rangespec)

        # base time is current time rounded down to the nearest unit (day, week, ...)
        from_time = TimeHelper.round(now, rangespec[0])
        # derive titles from unit ()
        titles = {
            'd': (_("Today"), _("Yesterday")),
            'w': (_("This week"), _("Last week")),
            'y': (str(year), None),
            'm': ("%s %d" % (defines.month_name(month - 1), year), None),
        }[rangespec[0]]

        if rangespec[1] == '0':
            return (from_time, now), titles[0]

        # last (previous)
        prev_time = TimeHelper.add(from_time, -1 * int(rangespec[1:]), rangespec[0])
        # add one hour to the calculated time so that if dst started in that period,
        # we don't round down a whole day
        prev_time = TimeHelper.round(prev_time + 3600, 'd')

        # This only works for Months, but those are the only defaults in Forecast Graphs
        # Language localization to system language not CMK GUI language
        if prev_time > from_time:
            from_time, prev_time = prev_time, from_time
        prev_time_str = time.strftime("%B %Y", time.localtime(prev_time))
        end_time_str = time.strftime("%B %Y", time.localtime(from_time - 1))
        if prev_time_str != end_time_str:
            prev_time_str += " - " + end_time_str
        if rangespec[0] == "y":
            prev_time_str = time.strftime("%Y", time.localtime(prev_time))

        return (prev_time, from_time), titles[1] or prev_time_str


# TODO: Cleanup kwargs
def DateFormat(**kwargs):
    """A selection of various date formats"""
    kwargs.setdefault("title", _("Date format"))
    kwargs.setdefault("default_value", "%Y-%m-%d")
    return DropdownChoice(choices=[
        ("%Y-%m-%d", "1970-12-18"),
        ("%d.%m.%Y", "18.12.1970"),
        ("%m/%d/%Y", "12/18/1970"),
        ("%d.%m.", "18.12."),
        ("%m/%d", "12/18"),
    ],
                          **kwargs)


# TODO: Cleanup kwargs
def TimeFormat(**kwargs):
    kwargs.setdefault("title", _("Time format"))
    kwargs.setdefault("default_value", "%H:%M:%S")
    return DropdownChoice(choices=[
        ("%H:%M:%S", "18:27:36"),
        ("%l:%M:%S %p", "12:27:36 PM"),
        ("%H:%M", "18:27"),
        ("%l:%M %p", "6:27 PM"),
        ("%H", "18"),
        ("%l %p", "6 PM"),
    ],
                          **kwargs)


class Optional(ValueSpec):
    """Make a configuration value optional, i.e. it may be None.

    The user has a checkbox for activating the option. Example:
    debug_log: it is either None or set to a filename."""
    def __init__(  # pylint: disable=redefined-builtin
        self,
        valuespec,  # type: ValueSpec
        label=None,  # type: _Optional[Text]
        negate=False,  # type: bool
        none_label=None,  # type: _Optional[Text]
        none_value=None,  # type: Any
        sameline=False,  # type: bool
        indent=True,  # type: bool
        allow_empty=True,  # type: bool
        # ValueSpec
        title=None,  # type: _Optional[Text]
        help=None,  # type: _Optional[ValueSpecHelp]
        default_value=DEF_VALUE,  # type: Any
        validate=None,  # type: _Optional[ValueSpecValidateFunc]
    ):
        super(Optional, self).__init__(title=title,
                                       help=help,
                                       default_value=default_value,
                                       validate=validate)
        self._valuespec = valuespec
        self._label = label
        self._negate = negate
        self._none_label = none_label if none_label is not None else _("(unset)")
        self._none_value = none_value
        self._sameline = sameline
        self._indent = indent

    def canonical_value(self):
        return self._none_value

    def render_input(self, varprefix, value):
        div_id = "option_" + varprefix
        checked = html.get_checkbox(varprefix + "_use")
        if checked is None:
            if self._negate:
                checked = value == self._none_value
            else:
                checked = value != self._none_value

        html.open_span()
        html.checkbox("%s_use" % varprefix,
                      checked,
                      label=self._get_label(),
                      onclick="cmk.valuespecs.toggle_option(this, %s, %r)" %
                      (json.dumps(div_id), 1 if self._negate else 0))
        if self._sameline:
            html.nbsp()
        else:
            html.br()
        html.close_span()

        if self._indent:
            indent = 40
        else:
            indent = 0

        html.open_span(id_=div_id,
                       style=[
                           "margin-left: %dpx;" % indent,
                           "display:none;" if checked == self._negate else None
                       ])
        if value == self._none_value:
            value = self._valuespec.default_value()
        if self._valuespec.title():
            the_title = self._valuespec.title()
            html.write(("???" if the_title is None else the_title) + " ")
        self._valuespec.render_input(varprefix + "_value", value)
        html.close_span()

    def _get_label(self):
        # type: () -> Text
        if self._label is not None:
            return self._label
        t = self.title()
        if t:
            return t
        if self._negate:
            return _(" Ignore this option")
        return _(" Activate this option")

    def value_to_text(self, value):
        if value == self._none_value:
            return self._none_label
        return self._valuespec.value_to_text(value)

    def from_html_vars(self, varprefix):
        checkbox_checked = html.get_checkbox(varprefix + "_use") is True  # not None or False
        if checkbox_checked != self._negate:
            return self._valuespec.from_html_vars(varprefix + "_value")
        return self._none_value

    def validate_datatype(self, value, varprefix):
        if value != self._none_value:
            self._valuespec.validate_datatype(value, varprefix + "_value")

    def _validate_value(self, value, varprefix):
        if value != self._none_value:
            self._valuespec.validate_value(value, varprefix + "_value")


class Alternative(ValueSpec):
    """Handle case when there are several possible allowed formats
    for the value (e.g. strings, 4-tuple or 6-tuple like in SNMP-Communities)
    The different alternatives must have different data types that can
    be distinguished with validate_datatype."""
    def __init__(  # pylint: disable=redefined-builtin
        self,
        elements,  # type: List[ValueSpec]
        match=None,  # type: _Optional[Callable[[Any], int]]
        style="radio",  # type: Text
        show_alternative_title=False,  # type: bool
        on_change=None,  # type: _Optional[Text]
        orientation="vertical",  # type: Text
        # ValueSpec
        title=None,  # type: _Optional[Text]
        help=None,  # type: _Optional[ValueSpecHelp]
        default_value=DEF_VALUE,  # type: Any
        validate=None,  # type: _Optional[ValueSpecValidateFunc]
    ):
        super(Alternative, self).__init__(title=title,
                                          help=help,
                                          default_value=default_value,
                                          validate=validate)
        self._elements = elements
        self._match = match  # custom match function, returns index in elements
        self._style = style  # alternative: "dropdown"
        self._show_alternative_title = show_alternative_title
        self._on_change = on_change  # currently only working for style="dropdown"
        self._orientation = orientation  # or horizontal: for style="dropdown"

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
            except Exception:
                pass

        return None, value

    def render_input(self, varprefix, value):
        if self._style == "radio":
            self.render_input_radio(varprefix, value)
        else:
            self.render_input_dropdown(varprefix, value)

    # TODO: The None cases below look very fishy...
    def render_input_dropdown(self, varprefix, value):
        mvs, value = self.matching_alternative(value)
        options = []  # type: List[_Tuple[Union[None, str, Text], Text]]
        sel_option = html.request.var(varprefix + "_use")
        for nr, vs in enumerate(self._elements):
            if not sel_option and vs == mvs:
                sel_option = str(nr)
            the_title = vs.title()
            options.append((str(nr), "???" if the_title is None else the_title))
        onchange = u"cmk.valuespecs.cascading_change(this, '%s', %d);" % (varprefix, len(options))
        if self._on_change:
            onchange += self._on_change
        if self._orientation == "horizontal":
            html.open_table()
            html.open_tr()
            html.open_td()
        html.dropdown(varprefix + "_use",
                      options,
                      deflt=("???" if sel_option is None else sel_option),
                      onchange=onchange)
        if self._orientation == "vertical":
            html.br()
            html.br()

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
            if html.request.has_var(varprefix + "_use"):
                checked = html.request.var(varprefix + "_use") == str(nr)
            else:
                checked = vs == mvs

            html.help(vs.help())
            title = vs.title()
            if not title and nr:
                html.nbsp()
                html.nbsp()

            html.radiobutton(varprefix + "_use", str(nr), checked,
                             None if title is None else six.ensure_str(title))
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
            if isinstance(self._default_value, type(lambda: True)):
                return self._default_value()
            return self._default_value
        except Exception:
            return self._elements[0].default_value()

    def value_to_text(self, value):
        vs, value = self.matching_alternative(value)
        if vs:
            output = ""
            if self._show_alternative_title and vs.title():
                output = "%s<br>" % vs.title()
            return output + vs.value_to_text(value)
        return _("invalid:") + " " + escaping.escape_attribute(str(value))

    def from_html_vars(self, varprefix):
        nr = html.request.get_integer_input_mandatory(varprefix + "_use")
        vs = self._elements[nr]
        return vs.from_html_vars(varprefix + "_%d" % nr)

    def validate_datatype(self, value, varprefix):
        for vs in self._elements:
            try:
                vs.validate_datatype(value, "")
                return
            except Exception:
                pass
        raise MKUserError(
            varprefix,
            _("The data type of the value does not match any of the "
              "allowed alternatives."))

    def _validate_value(self, value, varprefix):
        vs, value = self.matching_alternative(value)
        for nr, v in enumerate(self._elements):
            if vs == v:
                vs.validate_value(value, varprefix + "_%d" % nr)


class Tuple(ValueSpec):
    """Edit a n-tuple (with fixed size) of values"""
    def __init__(  # pylint: disable=redefined-builtin
        self,
        elements,  # type: List[ValueSpec]
        show_titles=True,  # type: bool
        orientation="vertical",  # type: str
        separator=" ",  # type: Text
        title_br=True,  # type: bool
        title=None,  # type: _Optional[Text]
        help=None,  # type: _Optional[ValueSpecHelp]
        default_value=DEF_VALUE,  # type: Any
        validate=None,  # type: _Optional[ValueSpecValidateFunc]
    ):
        super(Tuple, self).__init__(title=title,
                                    help=help,
                                    default_value=default_value,
                                    validate=validate)
        self._elements = elements
        self._show_titles = show_titles
        self._orientation = orientation  # also: horizontal, float
        self._separator = separator  # in case of float
        self._title_br = title_br

    def canonical_value(self):
        return tuple([x.canonical_value() for x in self._elements])

    def default_value(self):
        return tuple([x.default_value() for x in self._elements])

    def render_input(self, varprefix, value):
        if self._orientation != "float":
            html.open_table(class_=["valuespec_tuple", self._orientation])
            if self._orientation == "horizontal":
                html.open_tr()

        for no, element in enumerate(self._elements):
            try:
                val = value[no]
            except (TypeError, IndexError):
                val = element.default_value()
            vp = varprefix + "_" + str(no)
            if self._orientation == "vertical":
                html.open_tr()
            elif self._orientation == "float":
                html.write(self._separator)

            if self._show_titles:
                elem_title = element.title()
                if elem_title:
                    title = elem_title[0].upper() + elem_title[1:]
                else:
                    title = ""
                if self._orientation == "vertical":
                    html.open_td(class_="tuple_left")
                    html.write(title)

                    html.close_td()
                elif self._orientation == "horizontal":
                    html.open_td(class_="tuple_td")
                    html.open_span(class_=["title"])
                    html.write(title)

                    html.close_span()
                    if self._title_br:
                        html.br()
                    else:
                        html.write_text(" ")
                else:
                    html.write_text(" ")

            else:
                if self._orientation == "horizontal":
                    html.open_td(class_="tuple_td")

            if self._orientation == "vertical":
                html.open_td(class_="tuple_right")

            html.help(element.help())
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
        return "" + ", ".join(
            [element.value_to_text(val) for (element, val) in zip(self._elements, value)]) + ""

    def value_to_json(self, value):
        json_value = []
        for idx, element in enumerate(self._elements):
            json_value.append(element.value_to_json(value[idx]))
        return json_value

    def value_from_json(self, json_value):
        real_value = []
        for idx, element in enumerate(self._elements):
            real_value.append(element.value_from_json(json_value[idx]))
        return tuple(real_value)

    def from_html_vars(self, varprefix):
        value = []
        for no, element in enumerate(self._elements):
            vp = varprefix + "_" + str(no)
            value.append(element.from_html_vars(vp))
        return tuple(value)

    def _validate_value(self, value, varprefix):
        for no, (element, val) in enumerate(zip(self._elements, value)):
            vp = varprefix + "_" + str(no)
            element.validate_value(val, vp)

    def validate_datatype(self, value, varprefix):
        if not isinstance(value, tuple):
            raise MKUserError(varprefix,
                              _("The datatype must be a tuple, but is %s") % _type_name(value))
        if len(value) != len(self._elements):
            raise MKUserError(
                varprefix,
                _("The number of elements in the tuple must be exactly %d.") % len(self._elements))

        for no, (element, val) in enumerate(zip(self._elements, value)):
            vp = varprefix + "_" + str(no)
            element.validate_datatype(val, vp)


DictionaryEntry = _Tuple[str, ValueSpec]
DictionaryElements = Union[List[DictionaryEntry], Callable[[], List[DictionaryEntry]]]


class Dictionary(ValueSpec):
    # TODO: Cleanup ancient "migrate"
    def __init__(  # pylint: disable=redefined-builtin
        self,
        elements,  # type: DictionaryElements
        empty_text=None,  # type: _Optional[Text]
        default_text=None,  # type: _Optional[Text]
        optional_keys=True,  # type: Union[bool, List[str]]
        required_keys=None,  # type: _Optional[List[str]]
        ignored_keys=None,  # type: _Optional[List[str]]
        default_keys=None,  # type: _Optional[List[str]]
        hidden_keys=None,  # type: _Optional[List[str]]
        columns=1,  # type: int
        render="normal",  # type: str
        form_narrow=False,  # type: bool
        form_isopen=True,  # type: bool
        headers=None,  # type: Union[None, str, List[Union[_Tuple[Text, List[str]], _Tuple[Text, str, List[str]]]]]
        migrate=None,  # type: Callable[[_Tuple], Dict]
        indent=True,  # type: bool
        # ValueSpec
        title=None,  # type: _Optional[Text]
        help=None,  # type: _Optional[ValueSpecHelp]
        default_value=DEF_VALUE,  # type: Any
        validate=None,  # type: _Optional[ValueSpecValidateFunc]
    ):
        super(Dictionary, self).__init__(title=title,
                                         help=help,
                                         default_value=default_value,
                                         validate=validate)
        self._elements = elements
        self._empty_text = empty_text if empty_text is not None else _("(no parameters)")

        # Optionally a text can be specified to be shown by value_to_text()
        # when the value equal the default value of the value spec. Normally
        # the default values are shown.
        self._default_text = default_text
        self._required_keys = required_keys or []
        self._ignored_keys = ignored_keys or []
        self._default_keys = default_keys or []  # keys present in default value
        self._hidden_keys = hidden_keys or []

        if isinstance(optional_keys, list) and optional_keys:
            self._required_keys = [e[0] for e in self._get_elements() if e[0] not in optional_keys]
            self._optional_keys = True
        elif optional_keys:
            self._optional_keys = True
        else:
            self._optional_keys = False

        self._columns = columns  # possible: 1 or 2
        self._render = render  # also: "form" -> use forms.section()
        self._form_narrow = form_narrow  # used if render == "form"
        self._form_isopen = form_isopen  # used if render == "form"
        self._headers = headers  # "sup" -> small headers in oneline mode
        self._migrate = migrate  # value migration from old tuple version
        self._indent = indent

    def migrate(self, value):
        if self._migrate:
            return self._migrate(value)
        return value

    def _get_elements(self):
        if callable(self._elements):
            return self._elements()
        if isinstance(self._elements, list):
            return self._elements
        return []

    def render_input_as_form(self, varprefix, value):
        self._render_input(varprefix, value, "form")

    def render_input(self, varprefix, value):
        self._render_input(varprefix, value, self._render)

    def _render_input(self, varprefix, value, render):
        value = self.migrate(value)
        if not isinstance(value, MutableMapping):
            value = {}  # makes code simpler in complain phase

        if render == "form":
            self._render_input_form(varprefix, value)
        elif render == "form_part":
            self._render_input_form(varprefix, value, as_part=True)
        else:
            self._render_input_normal(varprefix,
                                      value,
                                      oneline=render == "oneline",
                                      small_headers=self._headers == "sup",
                                      two_columns=self._columns == 2)

    def _render_input_normal(self, varprefix, value, oneline, small_headers, two_columns):
        if not oneline or small_headers:
            html.open_table(class_=["dictionary"])
        if oneline and small_headers:
            html.open_tr()
        for param, vs in self._get_elements():
            if param in self._hidden_keys:
                continue
            if not oneline:
                html.open_tr()
                html.open_td(class_="dictleft")

            div_id = varprefix + "_d_" + param
            vp = varprefix + "_p_" + param
            colon_printed = False
            if self._optional_keys and param not in self._required_keys:
                checkbox_varname = vp + "_USE"
                visible = html.get_checkbox(checkbox_varname)
                if visible is None:
                    visible = param in value
                label = vs.title()
                if two_columns:
                    label += ":"
                    colon_printed = True
                html.checkbox(checkbox_varname,
                              visible,
                              label=label,
                              onclick="cmk.valuespecs.toggle_option(this, %s)" % json.dumps(div_id))
            else:
                visible = True
                if vs.title():
                    if oneline and small_headers:
                        html.open_td()
                        html.open_b(class_=["header"])
                    html.write(" %s" % vs.title())
                    if oneline and small_headers:
                        html.close_b()
                        html.br()
                    if oneline and not small_headers:
                        html.write_text(": ")

            if two_columns:
                if vs.title() and not colon_printed:
                    html.write_text(':')
                html.help(vs.help())
                if not oneline:
                    html.close_td()
                    html.open_td(class_="dictright")

            else:
                if not oneline:
                    html.br()

            html.open_div(
                id_=div_id,
                class_=["dictelement", "indent" if (self._indent and not two_columns) else None],
                style="display:none;" if not visible else
                ("display:inline-block;" if oneline else None))

            if not two_columns:
                html.help(vs.help())
            # Remember: in complain mode we do not render 'value' (the default value),
            # but re-display the values from the HTML variables. We must not use 'value'
            # in that case.
            the_value = value.get(param, vs.default_value()) if isinstance(value, dict) else None
            vs.render_input(vp, the_value)
            html.close_div()
            if not oneline or small_headers:
                html.close_td()
            if not oneline:
                html.close_tr()

        if oneline and small_headers:
            html.close_tr()
        if not oneline or small_headers:
            html.close_table()

    def _render_input_form(self, varprefix, value, as_part=False):
        headers = self._headers if self._headers else [(six.ensure_text(self.title() or
                                                                        _("Properties")), [])]
        for header, css, section_elements in map(self._normalize_header, headers):
            self.render_input_form_header(varprefix,
                                          value,
                                          header,
                                          section_elements,
                                          as_part,
                                          css=css)
        if not as_part:
            forms.end()

    @staticmethod
    def _normalize_header(header):
        if isinstance(header, tuple):
            if len(header) == 2:
                return header[0], None, header[1]
            if len(header) == 3:
                return header[0], header[1], header[2]
            raise ValueError("invalid header tuple length")
        raise ValueError("invalid header type")

    def render_input_form_header(self, varprefix, value, title, section_elements, as_part, css):
        if not as_part:
            forms.header(title, isopen=self._form_isopen, narrow=self._form_narrow)

        for param, vs in self._get_elements():
            if param in self._hidden_keys:
                continue

            if section_elements and param not in section_elements:
                continue

            div_id = varprefix + "_d_" + param
            vp = varprefix + "_p_" + param
            if self._optional_keys and param not in self._required_keys:
                visible = html.get_checkbox(vp + "_USE")
                if visible is None:
                    visible = param in value
                checkbox_code = html.render_checkbox(
                    vp + "_USE",
                    deflt=visible,
                    onclick="cmk.valuespecs.toggle_option(this, %s)" % json.dumps(div_id))
                forms.section(vs.title(), checkbox=checkbox_code, css=css)
            else:
                visible = True
                forms.section(vs.title(), css=css)

            html.open_div(id_=div_id, style="display:none;" if not visible else None)
            html.help(vs.help())
            vs.render_input(vp, value.get(param, vs.default_value()))
            html.close_div()

    def set_focus(self, varprefix):
        elements = self._get_elements()
        if elements:
            elements[0][1].set_focus(varprefix + "_p_" + elements[0][0])

    def canonical_value(self):
        return {
            name: vs.canonical_value()
            for (name, vs) in self._get_elements()
            if name in self._required_keys or not self._optional_keys
        }

    def default_value(self):
        return {
            name: vs.default_value()
            for name, vs in self._get_elements()
            if name in self._required_keys or not self._optional_keys or name in self._default_keys
        }

    def value_to_text(self, value):
        value = self.migrate(value)
        oneline = self._render == "oneline"
        if not value:
            return self._empty_text

        if self._default_text and value == self.default_value():
            return self._default_text

        elem = self._get_elements()
        return self._value_to_text_oneline(
            elem, value) if oneline else self._value_to_text_multiline(elem, value)

    def _value_to_text_oneline(self, elem, value):
        s = ''
        for param, vs in elem:
            if param in value:
                if param != elem[0][0]:
                    s += ", "
                s += "%s: %s" % (vs.title(), self._funny_workaround(vs, value[param]))
        return s

    def _value_to_text_multiline(self, elem, value):
        s = HTML()
        for param, vs in elem:
            if param in value:
                s += html.render_tr(
                    html.render_td("%s:&nbsp;" % vs.title(), class_="title") +
                    html.render_td(self._funny_workaround(vs, value[param])))
        return str(html.render_table(s))

    def _funny_workaround(self, vs, value):
        # TODO: This is a workaround for a bug. This function needs to return str objects right now.
        return HTML(vs.value_to_text(value))

    def value_to_json(self, value):
        json_value = {}
        for param, vs in self._get_elements():
            json_value[param] = vs.value_to_json(value[param])
        return json_value

    def value_from_json(self, json_value):
        real_value = {}
        for param, vs in self._get_elements():
            real_value[param] = vs.value_from_json(json_value[param])
        return real_value

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

        if not isinstance(value, dict):
            raise MKUserError(
                varprefix,
                _("The type must be a dictionary, but it is a %s") % _type_name(value))

        for param, vs in self._get_elements():
            if param in value:
                vp = varprefix + "_p_" + param
                try:
                    vs.validate_datatype(value[param], vp)
                except MKUserError as e:
                    raise MKUserError(e.varname, _("%s: %s") % (vs.title(), e))
            elif not self._optional_keys or param in self._required_keys:
                raise MKUserError(varprefix, _("The entry %s is missing") % vs.title())

        # Check for exceeding keys
        allowed_keys = [p for p, _v in self._get_elements()]
        if self._ignored_keys:
            allowed_keys += self._ignored_keys
        for param in value.keys():
            if param not in allowed_keys:
                raise MKUserError(
                    varprefix,
                    _("Undefined key '%s' in the dictionary. Allowed are %s.") %
                    (param, ", ".join(allowed_keys)))

    def _validate_value(self, value, varprefix):
        value = self.migrate(value)

        for param, vs in self._get_elements():
            if param in value:
                vp = varprefix + "_p_" + param
                vs.validate_value(value[param], vp)
            elif not self._optional_keys or param in self._required_keys:
                raise MKUserError(varprefix, _("The entry %s is missing") % vs.title())


# TODO: Cleanup this and all call sites. Replace it with some kind of DropdownChoice
# based valuespec
class ElementSelection(ValueSpec):
    """Base class for selection of a Nagios element out of a given list that must be loaded from a file.

    Example: GroupSelection. Child class must define
    a function get_elements() that returns a dictionary
    from element keys to element titles."""
    def __init__(  # pylint: disable=redefined-builtin
        self,
        label=None,  # type: _Optional[Text]
        empty_text=None,  # type: _Optional[Text]
        # ValueSpec
        title=None,  # type: _Optional[Text]
        help=None,  # type: _Optional[ValueSpecHelp]
        default_value=DEF_VALUE,  # type: Any
        validate=None,  # type: _Optional[ValueSpecValidateFunc]
    ):
        super(ElementSelection, self).__init__(title=title,
                                               help=help,
                                               default_value=default_value,
                                               validate=validate)
        self._loaded_at = None  # type: _Optional[int]
        self._label = label
        self._empty_text = empty_text if empty_text is not None else \
            _("There are no elements defined for this selection yet.")

    def load_elements(self):
        if self._loaded_at != id(html):
            self._elements = self.get_elements()
            self._loaded_at = id(html)  # unique for each query!

    def get_elements(self):
        raise NotImplementedError()

    def canonical_value(self):
        self.load_elements()
        if len(self._elements) > 0:
            return list(self._elements.keys())[0]

    def render_input(self, varprefix, value):
        self.load_elements()
        if len(self._elements) == 0:
            html.write(self._empty_text)
        else:
            if self._label:
                html.write("%s" % self._label)
                html.nbsp()
            html.dropdown(varprefix, self._elements.items(), deflt=value, ordered=True)

    def value_to_text(self, value):
        self.load_elements()
        return escaping.escape_attribute(self._elements.get(value, value))

    def from_html_vars(self, varprefix):
        return html.request.var(varprefix)

    def _validate_value(self, value, varprefix):
        self.load_elements()
        if len(self._elements) == 0:
            raise MKUserError(varprefix, _("You cannot save this rule.") + ' ' + self._empty_text)
        if value not in self._elements:
            raise MKUserError(varprefix,
                              _("%s is not an existing element in this selection.") % (value,))

    def validate_datatype(self, value, varprefix):
        self.load_elements()
        # When no elements exists the default value is None and e.g. in wato.mode_edit_rule()
        # handed over to validate_datatype() before rendering the input form. Disable the
        # validation in this case to prevent validation errors. A helpful message is shown
        # during render_input()
        if len(self._elements) == 0 and value is None:
            return

        if not isinstance(value, str):
            raise MKUserError(varprefix,
                              _("The datatype must be str (string), but is %s") % _type_name(value))


class AutoTimestamp(FixedValue):
    def canonical_value(self):
        # type: () -> float
        return time.time()

    def from_html_vars(self, varprefix):
        # type: (str) -> float
        return time.time()

    def value_to_text(self, value):
        # type: (float) -> Text
        return time.strftime("%F %T", time.localtime(value))

    def validate_datatype(self, value, varprefix):
        # type: (float, str) -> None
        if not isinstance(value, (int, float)):
            return MKUserError(varprefix, _("Invalid datatype of timestamp: must be int or float."))


class Foldable(ValueSpec):
    """Fully transparant VS encapsulating a vs in a foldable container"""
    def __init__(self, valuespec, title_function=None, **kwargs):  # pylint: disable=redefined-builtin
        # type: (ValueSpec, _Optional[Callable[[Any], Text]], **Any) -> None
        super(Foldable, self).__init__(**kwargs)
        self._valuespec = valuespec
        self._title_function = title_function

    def render_input(self, varprefix, value):
        # type: (str, Any) -> None
        html.begin_foldable_container(
            treename="valuespec_foldable",
            id_=varprefix,
            isopen=False,
            title=self._get_title(varprefix, value),
            indent=False,
        )
        html.help(self._valuespec.help())
        self._valuespec.render_input(varprefix, value)
        html.end_foldable_container()

    def _get_title(self, varprefix, value):
        # type: (str, Any) -> Text
        if self._title_function:
            title_value = value
            if html.form_submitted():
                try:
                    title_value = self._valuespec.from_html_vars(varprefix)
                except Exception:
                    pass
            return self._title_function(title_value)

        title = self._valuespec.title()
        if not title:
            title = _("(no title)")
        return title

    def set_focus(self, varprefix):
        # type: (str) -> None
        self._valuespec.set_focus(varprefix)

    def canonical_value(self):
        # type: () -> Any
        return self._valuespec.canonical_value()

    def default_value(self):
        # type: () -> Any
        return self._valuespec.default_value()

    def value_to_text(self, value):
        # type: (Any) -> Text
        return self._valuespec.value_to_text(value)

    def from_html_vars(self, varprefix):
        # type: (str) -> Any
        return self._valuespec.from_html_vars(varprefix)

    def validate_datatype(self, value, varprefix):
        # type: (Any, str) -> None
        self._valuespec.validate_datatype(value, varprefix)

    def _validate_value(self, value, varprefix):
        # type: (Any, str) -> None
        self._valuespec.validate_value(value, varprefix)


class Transform(ValueSpec):
    """Transforms the value from one representation to another while being
    completely transparent to the user

    forth: function that converts a value into the representation
           needed by the encapsulated vs
    back:  function that converts a value created by the encapsulated
           vs back to the outer representation"""
    def __init__(  # pylint: disable=redefined-builtin
        self,
        valuespec,  # type: ValueSpec
        back=None,  # type: _Optional[Callable[[Any], Any]]
        forth=None,  # type: _Optional[Callable[[Any], Any]]
        title=None,  # type: _Optional[Text]
        help=None,  # type: _Optional[ValueSpecHelp]
        default_value=DEF_VALUE,  # type: Any
        validate=None,  # type: _Optional[ValueSpecValidateFunc]
    ):
        super(Transform, self).__init__(title=title,
                                        help=help,
                                        default_value=default_value,
                                        validate=validate)
        self._valuespec = valuespec
        self._back = back
        self._forth = forth

    def forth(self, value):
        # type: (Any) -> Any
        if self._forth:
            return self._forth(value)
        return value

    def back(self, value):
        # type: (Any) -> Any
        if self._back:
            return self._back(value)
        return value

    def title(self):
        # type: () -> _Optional[Text]
        if self._title:
            return self._title
        return self._valuespec.title()

    def help(self):
        # type: () -> Union[Text, HTML, None]
        transform_help = super(Transform, self).help()
        if transform_help:
            return transform_help
        return self._valuespec.help()

    def render_input(self, varprefix, value):
        # type: (str, Any) -> None
        self._valuespec.render_input(varprefix, self.forth(value))

    def render_input_as_form(self, varprefix, value):
        # type: (str, Dict[str, Any]) -> None
        if not isinstance(self._valuespec, Dictionary):
            raise NotImplementedError()
        self._valuespec.render_input_as_form(varprefix, self.forth(value))

    def set_focus(self, varprefix):
        # type: (str) -> None
        self._valuespec.set_focus(varprefix)

    def canonical_value(self):
        # type: () -> Any
        return self.back(self._valuespec.canonical_value())

    def default_value(self):
        # type: () -> Any
        return self.back(self._valuespec.default_value())

    def value_to_text(self, value):
        # type: (Any) -> Text
        return self._valuespec.value_to_text(self.forth(value))

    def from_html_vars(self, varprefix):
        # type: (str) -> Any
        return self.back(self._valuespec.from_html_vars(varprefix))

    def validate_datatype(self, value, varprefix):
        # type: (Any, str) -> None
        self._valuespec.validate_datatype(self.forth(value), varprefix)

    def _validate_value(self, value, varprefix):
        # type: (Any, str) -> None
        self._valuespec.validate_value(self.forth(value), varprefix)


# TODO: Change to factory, cleanup kwargs
class LDAPDistinguishedName(TextUnicode):
    def __init__(self, enforce_suffix=None, **kwargs):
        # type: (_Optional[str], **Any) -> None
        super(LDAPDistinguishedName, self).__init__(**kwargs)
        self.enforce_suffix = enforce_suffix

    def _validate_value(self, value, varprefix):
        # type: (str, str) -> None
        super(LDAPDistinguishedName, self)._validate_value(value, varprefix)

        # Check whether or not the given DN is below a base DN
        if self.enforce_suffix and value and not value.lower().endswith(
                self.enforce_suffix.lower()):
            raise MKUserError(varprefix, _('Does not ends with "%s".') % self.enforce_suffix)


class Password(TextAscii):
    # TODO: Cleanup kwargs
    def __init__(self, is_stored_plain=True, **kwargs):
        # type: (bool, **Any) -> None
        self._is_stored_plain = is_stored_plain
        kwargs.setdefault("autocomplete", False)

        if self._is_stored_plain:
            plain_help = _("The password entered here is stored in plain text within the "
                           "monitoring site. This usually needed because the monitoring "
                           "process needs to have access to the unencrypted password "
                           "because it needs to submit it to authenticate with remote systems. ")

            if "help" in kwargs:
                kwargs["help"] += "<br><br>" + plain_help
            else:
                kwargs["help"] = plain_help

        super(Password, self).__init__(attrencode=True, **kwargs)

    def render_input(self, varprefix, value):
        # type: (str, _Optional[str]) -> None
        if value is None:
            value = ""

        if self._label:
            html.write(self._label)
            html.nbsp()

        html.password_input(
            varprefix,
            str(value),
            size=self._size,
            autocomplete="new-password" if self._autocomplete is False else None,
        )

    def password_plaintext_warning(self):
        # type: () -> None
        if self._is_stored_plain:
            html.span(
                _("<br>Please note that Check_MK needs this password in clear"
                  "<br>text during normal operation and thus stores it unencrypted"
                  "<br>on the Check_MK server."))

    def value_to_text(self, value):
        # type: (_Optional[Text]) -> Text
        if value is None:
            return _("none")
        return u'******'


class PasswordSpec(Password):
    # TODO: Cleanup kwargs
    def __init__(self, hidden=True, **kwargs):
        # type: (bool, **Any) -> None
        super(PasswordSpec, self).__init__(hidden=hidden, **kwargs)

    def render_input(self, varprefix, value):
        # type: (str, _Optional[str]) -> None
        super(PasswordSpec, self).render_input(varprefix, value)
        if not value:
            html.icon_button("#",
                             _("Randomize password"),
                             "random",
                             onclick="cmk.valuespecs.passwordspec_randomize(this);")
        if self._hidden:
            html.icon_button("#",
                             _("Show/Hide password"),
                             "showhide",
                             onclick="cmk.valuespecs.toggle_hidden(this);")

        self.password_plaintext_warning()


class FileUpload(ValueSpec):
    def __init__(self, **kwargs):
        super(FileUpload, self).__init__(**kwargs)
        self._allow_empty = kwargs.get('allow_empty', True)
        self._allowed_extensions = kwargs.get('allowed_extensions')
        self._allow_empty_content = kwargs.get('allow_empty_content', True)

    def canonical_value(self):
        if self._allow_empty:
            return None
        return ''

    def _validate_value(self, value, varprefix):
        if not value:
            raise MKUserError(varprefix, _('Please select a file.'))

        file_name, _mime_type, content = value

        if not self._allow_empty and (content == '' or file_name == ''):
            raise MKUserError(varprefix, _('Please select a file.'))

        if not self._allow_empty_content and len(content) == 0:
            raise MKUserError(varprefix,
                              _('The selected file is empty. Please select a non-empty file.'))
        if self._allowed_extensions is not None:
            matched = False
            for extension in self._allowed_extensions:
                if file_name.endswith(extension):
                    matched = True
                    break
            if not matched:
                raise MKUserError(
                    varprefix,
                    _("Invalid file name extension. Allowed are: %s") %
                    ", ".join(self._allowed_extensions))

    def render_input(self, varprefix, value):
        html.upload_file(varprefix)

    def from_html_vars(self, varprefix):
        return html.request.uploaded_file(varprefix)


class ImageUpload(FileUpload):
    def __init__(self, max_size=None, show_current_image=False, **kwargs):
        self._max_size = max_size
        self._show_current_image = show_current_image
        super(ImageUpload, self).__init__(**kwargs)

    def render_input(self, varprefix, value):
        if self._show_current_image and value:
            html.open_table()
            html.open_tr()
            html.td(_("Current image:"))
            html.td(
                html.render_img("data:image/png;base64,%s" %
                                six.ensure_str(base64.b64encode(six.ensure_binary(value)))))
            html.close_tr()
            html.open_tr()
            html.td(_("Upload new:"))
            html.open_td()
            super(ImageUpload, self).render_input(varprefix, value)
            html.close_td()
            html.close_tr()
            html.close_table()
        else:
            super(ImageUpload, self).render_input(varprefix, value)

    def _validate_value(self, value, varprefix):
        if not value:
            raise MKUserError(varprefix, _('Please choose a PNG image.'))

        file_name, mime_type, content = value

        if not file_name.endswith('.png') \
           or mime_type != 'image/png' \
           or not content.startswith('\x89PNG'):
            raise MKUserError(varprefix, _('Please choose a PNG image.'))

        try:
            im = Image.open(io.BytesIO(content))
        except IOError:
            raise MKUserError(varprefix, _('Please choose a valid PNG image.'))

        if self._max_size:
            w, h = im.size
            max_w, max_h = self._max_size
            if w > max_w or h > max_h:
                raise MKUserError(varprefix, _('Maximum image size: %dx%dpx') % (max_w, max_h))


class UploadOrPasteTextFile(Alternative):
    def __init__(self, **kwargs):
        file_title = kwargs.pop("file_title", _("File"))
        allow_empty = kwargs.pop("allow_empty", True)
        kwargs["elements"] = [
            FileUpload(title=_("Upload %s") % file_title, allow_empty=allow_empty),
            TextAreaUnicode(title=_("Content of %s") % file_title,
                            allow_empty=allow_empty,
                            cols=80,
                            rows="auto"),
        ]

        if kwargs.pop("default_mode", "text") == "upload":
            kwargs["match"] = lambda *args: 0
        else:
            kwargs["match"] = lambda *args: 1

        kwargs.setdefault("style", "dropdown")
        super(UploadOrPasteTextFile, self).__init__(**kwargs)

    def from_html_vars(self, varprefix):
        value = super(UploadOrPasteTextFile, self).from_html_vars(varprefix)
        # Convert textarea value to format of upload field
        if not isinstance(value, tuple):
            value = (None, None, value)
        return value


class ABCTextOrRegExp(six.with_metaclass(abc.ABCMeta, Alternative)):
    #@classmethod
    @abc.abstractmethod
    def _text_valuespec_class(self):
        # type: () -> Type[ValueSpec]
        raise NotImplementedError()

    #@classmethod
    @abc.abstractmethod
    def _regex_valuespec_class(self):
        # type: () -> Type[ValueSpec]
        raise NotImplementedError()

    def __init__(self, **kwargs):
        allow_empty = kwargs.pop("allow_empty", True)

        if "text_valuespec" in kwargs:
            vs_text = kwargs.pop("text_valuespec")
        else:
            vs_text = self._text_valuespec_class()(
                title=_("Explicit match"),
                allow_empty=allow_empty,
            )

        vs_regex = self._regex_valuespec_class()(
            mode=RegExp.prefix,
            title=_("Regular expression match"),
            allow_empty=allow_empty,
        )

        kwargs.update({
            "elements": [
                vs_text,
                Transform(
                    vs_regex,
                    forth=lambda v: v[1:],  # strip of "~"
                    back=lambda v: "~" + v,  # add "~"
                ),
            ],
            # Use RegExp field when value is prefixed with "~"
            "match": lambda v: 1 if v and v[0] == "~" else 0,
            "style": "dropdown",
            "orientation": "horizontal",
        })

        super(ABCTextOrRegExp, self).__init__(**kwargs)


class TextOrRegExp(ABCTextOrRegExp):
    @classmethod
    def _text_valuespec_class(cls):
        return TextAscii

    @classmethod
    def _regex_valuespec_class(cls):
        return RegExp


class TextOrRegExpUnicode(ABCTextOrRegExp):
    @classmethod
    def _text_valuespec_class(cls):
        return TextUnicode

    @classmethod
    def _regex_valuespec_class(cls):
        return RegExpUnicode


class Labels(ValueSpec):
    """Valuespec to render and input a collection of object labels"""
    class World(Enum):
        CONFIG = "config"
        CORE = "core"

    class Source(Enum):
        EXPLICIT = "explicit"
        RULESET = "ruleset"
        DISCOVERED = "discovered"

    def __init__(  # pylint: disable=redefined-builtin
        self,
        world,  # type: Labels.World
        label_source=None,  # type: Labels.Source
        max_labels=None,  # type: _Optional[int]
        # ValueSpec
        title=None,  # type: _Optional[Text]
        help=None,  # type: _Optional[ValueSpecHelp]
        default_value=DEF_VALUE,  # type: Any
        validate=None,  # type: _Optional[ValueSpecValidateFunc]
    ):
        super(Labels, self).__init__(title=title,
                                     help=help,
                                     default_value=default_value,
                                     validate=validate)
        self._world = world
        # Set this source to mark the labels that have no explicit label source set
        self._label_source = label_source
        # Set to positive integer to limit the number of labels to add to this field
        self._max_labels = max_labels

    def help(self):
        # type: () -> Union[Text, HTML, None]
        h = super(Labels, self).help()
        return (u"" if h is None else h) + _(
            "Labels need to be in the format <tt>[KEY]:[VALUE]</tt>. For example <tt>os:windows</tt>."
        )

    def canonical_value(self):
        return {}

    def from_html_vars(self, varprefix):
        labels = {}  # type: Dict[str, Any]

        try:
            decoded_labels = json.loads(html.request.get_unicode_input(varprefix) or "[]")
        except ValueError as e:
            raise MKUserError(varprefix, _("Failed to parse labels: %s") % e)

        for entry in decoded_labels:
            label_id, label_value = [p.strip() for p in entry["value"].split(":", 1)]
            if label_id in labels:
                raise MKUserError(
                    varprefix,
                    _("A label key can be used only once per object. "
                      "The Label key \"%s\" is used twice.") % label_id)
            labels[label_id] = label_value

        return labels

    def _validate_value(self, value, varprefix):
        for k, v in value.items():
            if not isinstance(k, six.text_type):
                raise MKUserError(
                    varprefix,
                    _("The label ID %r is of type %s, but should be %s") %
                    (k, type(k), six.text_type))
            if not isinstance(v, six.text_type):
                raise MKUserError(
                    varprefix,
                    _("The label value %r is of type %s, but should be %s") %
                    (k, type(v), six.text_type))

    def value_to_text(self, value):
        from cmk.gui.view_utils import render_labels
        label_sources = {k: self._label_source.value for k in value.keys()
                        } if self._label_source else {}
        return render_labels(value, "host", with_links=False, label_sources=label_sources)

    def render_input(self, varprefix, value):
        html.help(self.help())
        # tagify outputs a warning for value of "[]" right now
        # see: https://github.com/yairEO/tagify/pull/275
        labels = _encode_labels_for_tagify(value.items())
        html.text_input(varprefix,
                        default_value=ensure_unicode(json.dumps(labels)) if labels else "",
                        cssclass="labels",
                        placeholder=_("Add some label"),
                        data_world=self._world.value,
                        data_max_labels=self._max_labels)


def SingleLabel(world, label_source=None, **kwargs):
    """Input element for a single label"""
    return Labels(world, label_source=label_source, max_labels=1, **kwargs)


@page_registry.register_page("ajax_autocomplete_labels")
class PageAutocompleteLabels(AjaxPage):
    """Return all known labels to support tagify label input dropdown completion"""
    def page(self):
        request = html.get_request()
        return _encode_labels_for_tagify(
            self._get_labels(Labels.World(request["world"]), request["search_label"]))

    def _get_labels(self, world, search_label):
        if world == Labels.World.CONFIG:
            return self._get_labels_from_config(search_label)

        if world == Labels.World.CORE:
            return self._get_labels_from_core(search_label)

        raise NotImplementedError()

    def _get_labels_from_config(self, search_label):
        return []  # TODO: Implement me

    # TODO: Provide information about the label source
    # Would be better to optimize this kind of query somehow. The best we can
    # do without extending livestatus is to use the Cache header for liveproxyd
    def _get_labels_from_core(self, search_label):
        import cmk.gui.sites as sites
        query = (
            "GET services\n"  #
            "Cache: reload\n"  #
            "Columns: host_labels labels\n")

        labels = set()  # type: Set
        for row in sites.live().query(query):
            labels.update(row[0].items())
            labels.update(row[1].items())

        return list(labels)


def _encode_labels_for_tagify(labels):
    return [{"value": "%s:%s" % e} for e in labels]


class IconSelector(ValueSpec):
    def __init__(self, **kwargs):
        super(IconSelector, self).__init__(**kwargs)
        self._allow_empty = kwargs.get('allow_empty', True)
        self._empty_img = kwargs.get('emtpy_img', 'empty')

        self._exclude = [
            'trans',
            'empty',
        ]

    @classmethod
    def categories(cls):
        import cmk.gui.config as config  # FIXME: Clean this up. But how?
        return config.wato_icon_categories

    @classmethod
    def category_alias(cls, category_name):
        return dict(cls.categories()).get(category_name, category_name)

    # All icons within the images/icons directory have the ident of a category
    # witten in the PNG meta data. For the default images we have done this scripted.
    # During upload of user specific icons, the meta data is added to the images.
    def available_icons(self, only_local=False):
        dirs = [
            os.path.join(cmk.utils.paths.omd_root, "local/share/check_mk/web/htdocs/images/icons"),
        ]
        if not only_local:
            dirs.append(
                os.path.join(cmk.utils.paths.omd_root, "share/check_mk/web/htdocs/images/icons"))

        valid_categories = dict(self.categories()).keys()

        #
        # Read all icons from the icon directories
        #
        icons = {}
        for directory in dirs:
            try:
                files = os.listdir(directory)
            except OSError:
                continue

            for file_name in files:
                file_path = directory + "/" + file_name
                if file_name[-4:] == '.png' and os.path.isfile(file_path):

                    # extract the category from the meta data
                    try:
                        im = Image.open(file_path)
                    except IOError as e:
                        if "%s" % e == "cannot identify image file":
                            continue  # Silently skip invalid files
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
        by_cat = {}  # type: Dict[str, List[str]]
        for icon_name, category_name in icons.items():
            by_cat.setdefault(category_name, [])
            by_cat[category_name].append(icon_name)

        icon_categories = []
        for category_name, category_alias in self.categories():
            if category_name in by_cat:
                icon_categories.append((category_name, category_alias, by_cat[category_name]))
        return icon_categories

    def render_icon(self, icon_name, onclick='', title='', id_=''):
        if not icon_name:
            icon_name = self._empty_img

        icon = html.render_icon(icon_name, title=title, middle=True, id_=id_)
        if onclick:
            icon = html.render_a(icon, href="javascript:void(0)", onclick=onclick)

        return icon

    def render_input(self, varprefix, value):
        # Handle complain phase with validation errors correctly and get the value
        # from the HTML vars
        if value is None:
            value = html.request.var(varprefix + "_value")

        if not value:
            value = self._empty_img

        html.hidden_field(varprefix + "_value", value or '', varprefix + "_value", add_var=True)

        if value:
            content = self.render_icon(value, '', _('Choose another Icon'), id_=varprefix + '_img')
        else:
            content = _('Select an Icon')

        html.popup_trigger(
            content,
            varprefix + '_icon_selector',
            'icon_selector',
            url_vars=[
                ('value', value),
                ('varprefix', varprefix),
                ('allow_empty', '1' if self._allow_empty else '0'),
                ('back', html.makeuri([])),
            ],
            resizable=True,
        )

    def render_popup_input(self, varprefix, value):
        html.open_div(class_="icons", id_="%s_icons" % varprefix)

        icons = self.available_icons()
        available_icons = self.available_icons_by_category(icons)
        active_category = icons.get(value, available_icons[0][0])

        # Render tab navigation
        html.open_ul()
        for category_name, category_alias, icons in available_icons:
            html.open_li(class_="active" if active_category == category_name else None)
            html.a(category_alias,
                   href="javascript:cmk.valuespecs.iconselector_toggle(\'%s\', \'%s\')" %
                   (varprefix, category_name),
                   id_="%s_%s_nav" % (varprefix, category_name),
                   class_="%s_nav" % varprefix)
            html.close_li()
        html.close_ul()

        # Now render the icons grouped by category
        empty = ['empty'] if self._allow_empty else []
        for category_name, category_alias, icons in available_icons:
            html.open_div(id_="%s_%s_container" % (varprefix, category_name),
                          class_=["icon_container", "%s_container" % varprefix],
                          style="display:none;" if active_category != category_name else None)

            for icon in empty + sorted(icons):
                html.open_a(
                    href=None,
                    class_="icon",
                    onclick='cmk.valuespecs.iconselector_select(event, \'%s\', \'%s\')' %
                    (varprefix, icon),
                    title=icon,
                )

                html.write_html(self.render_icon(icon, id_=varprefix + '_i_' + icon, title=icon))

                html.span(icon)

                html.close_a()

            html.close_div()

        html.open_div(class_="buttons")

        html.jsbutton("_toggle_names",
                      _("Toggle names"),
                      onclick="cmk.valuespecs.iconselector_toggle_names(event, %s)" %
                      json.dumps(varprefix))

        import cmk.gui.config as config  # FIXME: Clean this up. But how?
        if config.user.may('wato.icons'):
            back_param = '&back=' + html.urlencode(
                html.get_url_input('back')) if html.request.has_var('back') else ''
            html.buttonlink('wato.py?mode=icons' + back_param, _('Manage'))

        html.close_div()

        html.close_div()

    def from_html_vars(self, varprefix):
        icon = html.request.var(varprefix + '_value')
        if icon == 'empty':
            return None
        return icon

    def value_to_text(self, value):
        # TODO: This is a workaround for a bug. This function needs to return str objects right now.
        return "%s" % self.render_icon(value)

    def validate_datatype(self, value, varprefix):
        if value is not None and not isinstance(value, str):
            raise MKUserError(varprefix, _("The type is %s, but should be str") % type(value))

    def _validate_value(self, value, varprefix):
        if not self._allow_empty and not value:
            raise MKUserError(varprefix, _("You need to select an icon."))

        if value and value not in self.available_icons():
            raise MKUserError(varprefix, _("The selected icon image does not exist."))


# TODO: Cleanup kwargs
def ListOfTimeRanges(**kwargs):
    return ListOf(TimeofdayRange(allow_empty=True,),
                  movable=False,
                  add_label=_("Add time range"),
                  del_label=_("Delete time range"),
                  style=ListOf.Style.FLOATING,
                  magic="#!#",
                  **kwargs)


# Kept for compatibility reasons (removed in 1.6)
TimeofdayRanges = ListOfTimeRanges


# TODO: Cleanup kwargs
def Fontsize(**kwargs):
    kwargs.setdefault("title", _("Font size"))
    kwargs.setdefault("default_value", 10)
    return Float(size=5, unit=_("pt"), **kwargs)


class Color(ValueSpec):
    def __init__(self, **kwargs):
        kwargs["regex"] = "#[0-9]{3,6}"
        kwargs["regex_error"] = _("The color needs to be given in hex format.")
        super(Color, self).__init__(**kwargs)
        self._on_change = kwargs.get("on_change")
        self._allow_empty = kwargs.get("allow_empty", True)

    def render_input(self, varprefix, value):
        if not value:
            value = "#FFFFFF"

        # Holds the actual value for form submission
        html.hidden_field(varprefix + "_value", value or '', varprefix + "_value", add_var=True)

        indicator = html.render_div('',
                                    id_="%s_preview" % varprefix,
                                    class_="cp-preview",
                                    style="background-color:%s" % value)

        html.popup_trigger(indicator,
                           varprefix + '_popup',
                           cssclass="colorpicker",
                           onclose=self._on_change,
                           content_body="cmk.popup_menu.generate_colorpicker_body(this, %s, %s)" %
                           (json.dumps(varprefix), json.dumps(value)))

    def from_html_vars(self, varprefix):
        color = html.request.var(varprefix + '_value')
        if color == '':
            return None
        return color

    def value_to_text(self, value):
        return value

    def validate_datatype(self, value, varprefix):
        if value is not None and not isinstance(value, str):
            raise MKUserError(varprefix, _("The type is %s, but should be str") % type(value))

    def _validate_value(self, value, varprefix):
        if not self._allow_empty and not value:
            raise MKUserError(varprefix, _("You need to select a color."))


def GraphColor(title, default_value):
    return Alternative(
        title=title,
        style="dropdown",
        elements=[
            FixedValue(
                "default",
                title=_("Use default color"),
                totext=_("Use default color of the theme or medium"),
            ),
            Color(title=_("Use the following color")),
        ],
        default_value=default_value,
    )


class SSHKeyPair(ValueSpec):
    def render_input(self, varprefix, value):
        if value:
            html.write(_("Fingerprint: %s") % self.value_to_text(value))
            html.hidden_field(varprefix, self._encode_key_for_url(value), add_var=True)
        else:
            html.write(_("Key pair will be generated when you save."))

    def value_to_text(self, value):
        return self._get_key_fingerprint(value)

    def from_html_vars(self, varprefix):
        if html.request.has_var(varprefix):
            return self._decode_key_from_url(html.request.var(varprefix))
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
        public_key = pubkey.exportKey('OpenSSH')
        return (private_key, public_key)

    @classmethod
    def _get_key_fingerprint(cls, value):
        _private_key, public_key = value
        key = base64.b64decode(public_key.strip().split()[1].encode('ascii'))
        fp_plain = hashlib.md5(key).hexdigest()
        return ':'.join(a + b for a, b in zip(fp_plain[::2], fp_plain[1::2]))


# TODO: Cleanup kwargs
def SchedulePeriod(from_end=True, **kwargs):
    if from_end:
        from_end_choice = [
            ("month_end", _("At the end of every month at day"),
             Integer(minvalue=1, maxvalue=28, unit=_("from the end"))),
        ]  # type: List[CascadingDropdownChoice]
    else:
        from_end_choice = []

    dwm = [
        ("day", _("Every day"), None),
        ("week", _("Every week on..."), Weekday(title=_("Day of the week"))),
        ("month_begin", _("At the beginning of every month at day"), Integer(minvalue=1,
                                                                             maxvalue=28)),
    ]  # type:  List[CascadingDropdownChoice]
    return CascadingDropdown(title=_("Period"),
                             orientation="horizontal",
                             choices=dwm + from_end_choice,
                             **kwargs)


class CAorCAChain(UploadOrPasteTextFile):
    def __init__(self, **args):
        args.setdefault("title", _("Certificate Chain (Root / Intermediate Certificate)"))
        args.setdefault("file_title", _("CRT/PEM File"))
        super(CAorCAChain, self).__init__(**args)

    def from_html_vars(self, varprefix):
        value = Alternative.from_html_vars(self, varprefix)
        if isinstance(value, tuple):
            value = value[2]  # FileUpload sends (filename, mime-type, content)
        return value

    def _validate_value(self, value, varprefix):
        try:
            self.analyse_cert(value)
        except Exception as e:
            raise MKUserError(varprefix, _("Invalid certificate file: %s") % e)

    def analyse_cert(self, value):
        from OpenSSL import crypto  # type: ignore[import]
        cert = crypto.load_certificate(crypto.FILETYPE_PEM, value)
        titles = {
            "C": _("Country"),
            "ST": _("State or Province Name"),
            "L": _("Locality Name"),
            "O": _("Organization Name"),
            "CN": _("Common Name"),
        }
        cert_info = {}  # type: Dict[str, Dict]
        for what, x509 in [
            ("issuer", cert.get_issuer()),
            ("subject", cert.get_subject()),
        ]:
            cert_info[what] = {}
            for key, val in x509.get_components():
                if key in titles:
                    cert_info[what][titles[key]] = val.decode("utf8")
        return cert_info

    def value_to_text(self, value):
        cert_info = self.analyse_cert(value)
        text = u"<table>"
        for what, title in [
            ("issuer", _("Issuer")),
            ("subject", _("Subject")),
        ]:
            text += u"<tr><td>%s:</td><td>" % title
            for title1, val in sorted(cert_info[what].items()):
                text += u"%s: %s<br>" % (title1, val)
            text += u"</tr>"
        text += u"</table>"
        return text


# TODO: Cleanup kwargs
def ListOfCAs(**args):
    args.setdefault("title", _("CAs to accept"))
    args.setdefault(
        "help",
        _("Only accepting HTTPS connections with a server which certificate "
          "is signed with one of the CAs that are listed here. That way it is guaranteed "
          "that it is communicating only with the authentic update server. "
          "If you use self signed certificates for you server then enter that certificate "
          "here."))
    args.setdefault("add_label", _("Add new CA certificate or chain"))
    args.setdefault(
        "empty_text",
        _("You need to enter at least one CA. Otherwise no SSL connection can be made."))
    args.setdefault("allow_empty", False)
    return ListOf(CAorCAChain(), movable=False, **args)


# TODO: Change to factory, Cleanup kwargs
class SiteChoice(DropdownChoice):
    def __init__(self, **kwargs):
        kwargs.setdefault("title", _("Site"))
        kwargs.setdefault("default_value", self._site_default_value)
        kwargs.setdefault("invalid_choice_error",
                          _("The configured site is not known to this site."))

        kwargs.update({
            "choices": self._site_choices,
            "invalid_choice": "complain",
            "invalid_choice_title": _("Unknown site (%s)"),
        })

        super(SiteChoice, self).__init__(**kwargs)

    def _site_default_value(self):
        import cmk.gui.config as config
        if config.is_wato_slave_site():
            return False

        default_value = config.site_attribute_default_value()
        if default_value:
            return default_value
        return self.canonical_value()

    def _site_choices(self):
        import cmk.gui.config as config  # FIXME
        return config.site_attribute_choices()


# TODO: Cleanup kwargs
def LogLevelChoice(**kwargs):
    kwargs.setdefault("default_value", logging.INFO)
    return DropdownChoice(choices=[
        (logging.CRITICAL, _("Critical")),
        (logging.ERROR, _("Error")),
        (logging.WARNING, _("Warning")),
        (logging.INFO, _("Informational")),
        (cmk.utils.log.VERBOSE, _("Verbose")),
        (logging.DEBUG, _("Debug")),
    ],
                          **kwargs)


def rule_option_elements(disabling=True):
    # type: (bool) -> List[DictionaryEntry]
    elements = [
        ("description",
         TextUnicode(
             title=_("Description"),
             help=_("A description or title of this rule"),
             size=80,
         )),
        ("comment", RuleComment()),
        ("docu_url", DocumentationURL()),
    ]  # type: List[DictionaryEntry]
    if disabling:
        elements += [
            ("disabled",
             Checkbox(
                 title=_("Rule activation"),
                 help=_("Disabled rules are kept in the configuration but are not applied."),
                 label=_("do not apply this rule"),
             )),
        ]
    return elements


class RuleComment(TextAreaUnicode):
    def __init__(self):
        # type: () -> None
        super(RuleComment, self).__init__(
            title=_("Comment"),
            help=_("An optional comment that may be used to explain the purpose of this object. "
                   "The comment is only visible in this dialog and may help other users "
                   "understanding the intentions of the configured attributes."),
            rows=4,
            cols=80,
        )

    # TODO: Once we switched to Python 3 we can merge the unicode and non unicode class
    def render_input(self, varprefix, value):  # type: ignore[override]
        # type: (str, Text) -> None
        html.open_div(style="white-space: nowrap;")

        super(RuleComment, self).render_input(varprefix, value)

        import cmk.gui.config as config  # FIXME
        date_and_user = "%s %s: " % (time.strftime("%F", time.localtime()), config.user.id)

        html.nbsp()
        html.icon_button(None,
                         title=_("Prefix date and your name to the comment"),
                         icon="insertdate",
                         onclick="cmk.valuespecs.rule_comment_prefix_date_and_user(this, '%s');" %
                         date_and_user)
        html.close_div()


def DocumentationURL():
    # type: () -> TextAscii
    return TextAscii(
        title=_("Documentation URL"),
        help=HTML(
            _("An optional URL pointing to documentation or any other page. This will be displayed "
              "as an icon %s and open a new page when clicked. "
              "You can use either global URLs (beginning with <tt>http://</tt>), absolute local urls "
              "(beginning with <tt>/</tt>) or relative URLs (that are relative to <tt>check_mk/</tt>)."
             ) % html.render_icon("url")),
        size=80,
    )


def _type_name(v):
    try:
        return type(v).__name__
    except Exception:
        return escaping.escape_attribute(str(type(v)))
