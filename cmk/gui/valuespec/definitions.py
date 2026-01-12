#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
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
import abc
import base64
import datetime
import hashlib
import ipaddress
import itertools
import json
import logging
import math
import numbers
import re
import socket
import time
import urllib.parse
import uuid
import warnings
from collections.abc import (
    Callable,
    Collection,
    Container,
    Iterable,
    Mapping,
    MutableMapping,
    Sequence,
)
from enum import Enum
from pathlib import Path
from re import Pattern
from typing import (
    Any,
    cast,
    Final,
    Generic,
    Literal,
    NamedTuple,
    Protocol,
    SupportsFloat,
    TypeAlias,
    TypeVar,
)

import dateutil.parser
from dateutil.relativedelta import relativedelta
from dateutil.tz import tzlocal

from livestatus import SiteId

import cmk.ccc.plugin_registry
from cmk.ccc.exceptions import MKGeneralException
from cmk.ccc.version import Version

import cmk.utils.log
import cmk.utils.paths
import cmk.utils.regex
from cmk.utils import dateutils
from cmk.utils.hostaddress import HostAddress as HostAddressType
from cmk.utils.images import CMKImage, ImageType
from cmk.utils.labels import AndOrNotLiteral, LabelSources
from cmk.utils.regex import RegexFutureWarning
from cmk.utils.render import SecondsRenderer
from cmk.utils.urls import is_allowed_url
from cmk.utils.user import UserId

from cmk.gui import forms, site_config, user_sites, utils
from cmk.gui.config import active_config
from cmk.gui.exceptions import MKUserError
from cmk.gui.htmllib.foldable_container import foldable_container
from cmk.gui.htmllib.generator import HTMLWriter
from cmk.gui.htmllib.html import html
from cmk.gui.htmllib.tag_rendering import HTMLTagAttributes
from cmk.gui.http import request, UploadedFile
from cmk.gui.i18n import _
from cmk.gui.logged_in import user
from cmk.gui.type_defs import (
    _Icon,
    ChoiceGroup,
    ChoiceId,
    Choices,
    ChoiceText,
    GroupedChoices,
    Icon,
)
from cmk.gui.utils import escaping
from cmk.gui.utils.autocompleter_config import AutocompleterConfig, ContextAutocompleterConfig
from cmk.gui.utils.encrypter import Encrypter
from cmk.gui.utils.html import HTML
from cmk.gui.utils.labels import (
    encode_labels_for_http,
    get_labels_from_config,
    get_labels_from_core,
    label_help_text,
    LABEL_REGEX,
    LabelType,
    parse_label_groups_from_http_vars,
    parse_labels_value,
)
from cmk.gui.utils.output_funnel import output_funnel
from cmk.gui.utils.popups import MethodAjax, MethodColorpicker
from cmk.gui.utils.speaklater import LazyString
from cmk.gui.utils.theme import theme
from cmk.gui.utils.urls import makeuri, urlencode
from cmk.gui.view_utils import render_labels

from cmk.crypto import certificate, keys
from cmk.crypto.hash import HashAlgorithm

seconds_per_day = 86400


class Sentinel:
    pass


# Some arbitrary object for checking whether or not default_value was set
DEF_VALUE = Sentinel()

T = TypeVar("T")

# A value which can be delayed.
# NOTE: Due to the use of Union below, we can't have Callables as values.
# NOTE: No caching, so it's different from e.g. Scheme's delay/force.
Promise: TypeAlias = T | Callable[[], T]


# NOTE: This helper function should be used everywhere instead of dispatching on
# callable() all over the place, but there is currently a bug in mypy, which would
# result in a return type of "object". :-/ https://github.com/python/mypy/issues/6751
def force(p: Promise[T]) -> T:
    return p() if callable(p) else p


ValueSpecValidateFunc = Callable[[T, str], None]
ValueSpecDefault = Promise[Sentinel | T]
ValueSpecText = str | HTML
ValueSpecHelp = Promise[ValueSpecText]
# TODO: redefine after https://github.com/python/mypy/pull/13516 is released
JSONValue = Any

C = TypeVar("C", bound="Comparable")


# Look, mom, we finally have Haskell type classes! :-D Naive version requiring
# only <, hopefully some similar class will make it into typing soon...
class Comparable(Protocol):
    @abc.abstractmethod
    def __lt__(self: C, other: C) -> bool:
        pass


# NOTE: Bounds are inclusive!
class Bounds(Generic[C]):
    def __init__(self, lower: C | None, upper: C | None) -> None:
        super().__init__()
        self._lower = lower
        self._upper = upper

    def lower(self, default: C) -> C:
        return default if self._lower is None else self._lower

    def validate_value(
        self,
        value: C,
        varprefix: str,
        *,
        message_lower: str | None = None,
        message_upper: str | None = None,
        formatter: Callable[[C], ValueSpecText] = str,
    ) -> None:
        if self._lower is not None and value < self._lower:
            raise MKUserError(
                varprefix,
                (
                    _("{actual} is too low. The minimum allowed value is {bound}.")
                    if message_lower is None
                    else message_lower
                ).format(actual=formatter(value), bound=formatter(self._lower)),
            )
        if self._upper is not None and self._upper < value:
            raise MKUserError(
                varprefix,
                (
                    _("{actual} is too high. The maximum allowed value is {bound}.")
                    if message_upper is None
                    else message_upper
                ).format(actual=formatter(value), bound=formatter(self._upper)),
            )

    def transform_value(self, value: C) -> C:
        if self._lower is not None and value < self._lower:
            return self._lower
        if self._upper is not None and self._upper < value:
            return self._upper
        return value


class ValueSpec(abc.ABC, Generic[T]):
    """Abstract base class of all value declaration classes"""

    # TODO: Cleanup help argument redefined-builtin
    def __init__(  # pylint: disable=redefined-builtin
        self,
        title: str | None = None,
        label: str | None = None,
        help: ValueSpecHelp | None = None,
        default_value: ValueSpecDefault[T] = DEF_VALUE,
        validate: ValueSpecValidateFunc[T] | None = None,
    ):
        super().__init__()
        self._title = title
        self._label = label
        self._help = help
        self._default_value = default_value
        self._validate = validate

    def title(self) -> str | None:
        return self._title

    def label(self) -> str | None:
        return self._label

    def help(self) -> str | HTML | None:
        if callable(self._help):
            return self._help()

        if isinstance(self._help, HTML):
            return self._help

        if self._help is None:
            return None

        if isinstance(self._help, LazyString):
            return str(self._help)

        if not isinstance(self._help, str):
            raise ValueError(self._help)
        return self._help

    def allow_empty(self) -> bool:
        """Whether the valuespec is allowed to be left empty."""
        return True

    def render_input(self, varprefix: str, value: T) -> None:
        """Create HTML-form elements that represent a given
        value and let the user edit that value

        The varprefix is prepended to the HTML variable names and is needed in
        order to make the variable unique in case that another Value of the same
        type is being used as well.  The function may assume that the type of the
        value is valid."""

    def set_focus(self, varprefix: str) -> None:
        """Sets the input focus (cursor) into the most promiment field of the
        HTML code previously rendered with render_input()"""
        html.set_focus(varprefix)

    # TODO: Investigate: The Optional here does not really fit the doc string. What to do with this?
    @abc.abstractmethod
    def canonical_value(self) -> T:
        """Create a canonical, minimal, default value that matches the datatype
        of the value specification and fulfills also data validation."""
        raise NotImplementedError()

    def default_value(self) -> T:
        """Return a default value for this variable

        This is optional and only used in the value editor for same cases where
        the default value is known."""
        if callable(self._default_value):
            value = self._default_value()
        else:
            value = self._default_value

        if isinstance(value, Sentinel):
            return self.canonical_value()
        return value

    def value_to_html(self, value: T) -> ValueSpecText:
        """Creates a HTML-representation of the value that can be
        used in tables and other contextes

        It is to be read by the user and need not to be parsable.  The function
        may assume that the type of the value is valid."""
        return repr(value)

    @abc.abstractmethod
    def mask(self, value: T) -> T:
        """Obscure any sensitive information in the provided value

        Container-like ValueSpecs must recurse over their items, allow these to mask their
        values. Other ValueSpecs that don't have a need for masking sensitive information
        can simply return the input value."""
        raise NotImplementedError()

    @abc.abstractmethod
    def value_to_json(self, value: T) -> JSONValue:
        raise NotImplementedError()

    @abc.abstractmethod
    def value_from_json(self, json_value: JSONValue) -> T:
        raise NotImplementedError()

    @abc.abstractmethod
    def from_html_vars(self, varprefix: str) -> T:
        """Create a value from the current settings of the HTML variables

        This function must also check the validity and may raise a MKUserError
        in case of invalid set variables."""
        raise NotImplementedError()

    def validate_value(self, value: T, varprefix: str) -> None:
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
        # accepted by some attribute valuespecs which base on e.g. TextInput.
        # This should be solved during Python3 transformation where we will
        # finally make a huge switch to unicode strings in many places.
        # TODO: Cleanup all external direct calls to validate_datatype() once this is
        #       being enabled.
        # self.validate_datatype(value, varprefix)
        self._validate_value(value, varprefix)
        if self._validate:
            self._validate(value, varprefix)

    # TODO: Better signature: def (value: object, varprefix: builtins.str) -> _VT
    # Remember: Parse, don't validate!
    def validate_datatype(self, value: T, varprefix: str) -> None:
        """Check if a given value matches the datatype of described by this class."""

    def _validate_value(self, value: T, varprefix: str) -> None:
        """Override this method to implement custom validation functions for sub-valuespec types

        This function should assume that the data type is valid (either because
        it has been returned by from_html_vars() or because it has been checked
        with validate_datatype())."""

    # FIXME: The signature seem to be utter nonsense...
    def transform_value(self, value: T) -> T:
        """Transform the given value with the valuespecs transform logic and give it back"""
        return value

    def has_show_more(self) -> bool:
        """If valuespec contains any show more elements"""
        return False


# TODO: T should be bound to JSONValue
class FixedValue(ValueSpec[T]):
    """A fixed non-editable value, e.g. to be used in 'Alternative'"""

    def __init__(  # pylint: disable=redefined-builtin
        self,
        value: T,
        totext: str | HTML | None = None,
        title: str | None = None,
        help: ValueSpecHelp | None = None,
        default_value: ValueSpecDefault[T] = DEF_VALUE,
        validate: ValueSpecValidateFunc[T] | None = None,
    ):
        super().__init__(title=title, help=help, default_value=default_value, validate=validate)
        self._value = value
        self._totext = totext

    def canonical_value(self) -> T:
        return self._value

    def render_input(self, varprefix: str, value: T) -> None:
        html.span(self.value_to_html(value), class_="vs_fixed_value")

    def value_to_html(self, value: T) -> ValueSpecText:
        if self._totext is not None:
            return self._totext
        if isinstance(value, str):
            return value
        return str(value)

    def mask(self, value: T) -> T:
        return value

    def value_to_json(self, value: T) -> JSONValue:
        return value

    def value_from_json(self, json_value: JSONValue) -> T:
        return json_value

    def from_html_vars(self, varprefix: str) -> T:
        return self._value

    def validate_datatype(self, value: T, varprefix: str) -> None:
        if not self._value == value:
            raise MKUserError(
                varprefix,
                _("Invalid value, must be '%r' but is '%r'") % (self._value, value),
            )


class Age(ValueSpec[int]):
    """Time in seconds"""

    def __init__(  # pylint: disable=redefined-builtin
        self,
        label: str | None = None,
        footer: str | None = None,
        minvalue: int | None = None,
        maxvalue: int | None = None,
        display: (Container[Literal["days", "hours", "minutes", "seconds"]] | None) = None,
        title: str | None = None,
        help: ValueSpecHelp | None = None,
        default_value: ValueSpecDefault[int] = DEF_VALUE,
        validate: ValueSpecValidateFunc[int] | None = None,
        cssclass: str | None = None,
    ):
        super().__init__(
            title=title,
            label=label,
            help=help,
            default_value=default_value,
            validate=validate,
        )
        self._label = label
        self._footer = footer
        self._bounds = Bounds[int](minvalue, maxvalue)
        self._display = display if display is not None else ["days", "hours", "minutes", "seconds"]
        self._cssclass = [] if cssclass is None else [cssclass]

    def canonical_value(self) -> int:
        return self._bounds.lower(0)

    def render_input(self, varprefix: str, value: int) -> None:
        days, rest = divmod(value, 60 * 60 * 24)
        hours, rest = divmod(rest, 60 * 60)
        minutes, seconds = divmod(rest, 60)

        html.open_div(class_=["vs_age"] + self._cssclass)
        if self._label:
            html.span(self._label, class_="vs_floating_text")

        takeover = 0
        for uid, title, val, tkovr_fac in [
            ("days", _("days"), days, 24),
            ("hours", _("hours"), hours, 60),
            ("minutes", _("mins"), minutes, 60),
            ("seconds", _("secs"), seconds, 60),
        ]:
            if uid in self._display:
                val += takeover
                takeover = 0
                html.text_input(
                    varprefix + "_" + uid,
                    default_value=str(val),
                    size=4,
                    cssclass="number",
                )
                html.write_text_permissive(" %s " % title)
            else:
                takeover = (takeover + val) * tkovr_fac

        if self._footer:
            html.span(self._footer, class_=["vs_floating_text", "vs_age_footer"])

        html.close_div()

    def from_html_vars(self, varprefix: str) -> int:
        # TODO: Validate for correct numbers!
        return (
            request.get_integer_input_mandatory(varprefix + "_days", 0) * 3600 * 24
            + request.get_integer_input_mandatory(varprefix + "_hours", 0) * 3600
            + request.get_integer_input_mandatory(varprefix + "_minutes", 0) * 60
            + request.get_integer_input_mandatory(varprefix + "_seconds", 0)
        )

    def mask(self, value: int) -> int:
        return value

    def value_to_html(self, value: int) -> ValueSpecText:
        if value == 0:
            return _("no time")
        return SecondsRenderer.detailed_str(value)

    def value_to_json(self, value: int) -> JSONValue:
        return value

    def value_from_json(self, json_value: JSONValue) -> int:
        return json_value

    def validate_datatype(self, value: int, varprefix: str) -> None:
        if not isinstance(value, int):
            raise MKUserError(
                varprefix,
                _("The value %r has type %s, but must be of type int") % (value, type_name(value)),
            )

    def _validate_value(self, value: int, varprefix: str) -> None:
        self._bounds.validate_value(value, varprefix)

    def transform_value(self, value: int) -> int:
        return self._bounds.transform_value(value)


class TimeSpan(ValueSpec[float]):
    """Time in float seconds"""

    def __init__(  # pylint: disable=redefined-builtin
        self,
        label: str | None = None,
        footer: str | None = None,
        minvalue: float | None = None,
        maxvalue: float | None = None,
        display: (
            Container[Literal["days", "hours", "minutes", "seconds", "milliseconds"]] | None
        ) = None,
        title: str | None = None,
        help: ValueSpecHelp | None = None,
        default_value: ValueSpecDefault[float] = DEF_VALUE,
        validate: ValueSpecValidateFunc[float] | None = None,
        cssclass: str | None = None,
    ):
        super().__init__(
            title=title,
            label=label,
            help=help,
            default_value=default_value,
            validate=validate,
        )
        self._label = label
        self._footer = footer
        self._bounds = Bounds[float](minvalue, maxvalue)
        self._display = (
            display
            if display is not None
            else ["days", "hours", "minutes", "seconds", "milliseconds"]
        )
        self._cssclass = [] if cssclass is None else [cssclass]

    def canonical_value(self) -> float:
        return self._bounds.lower(0)

    def render_input(self, varprefix: str, value: float) -> None:
        days, rest = divmod(value, 60 * 60 * 24)
        hours, rest = divmod(rest, 60 * 60)
        minutes, seconds = divmod(rest, 60)
        seconds_whole, seconds_frac = divmod(seconds, 1)

        html.open_div(class_=["vs_age"] + self._cssclass)
        if self._label:
            html.span(self._label, class_="vs_floating_text")

        takeover = 0.0
        for uid, title, val, tkovr_fac in [
            ("days", _("days"), int(days), 24),
            ("hours", _("hours"), int(hours), 60),
            ("minutes", _("mins"), int(minutes), 60),
            ("seconds", _("s"), int(seconds_whole), 1),
            ("milliseconds", _("ms"), seconds_frac * 1000, 0.001),
        ]:
            if uid in self._display:
                val += takeover
                takeover = 0
                html.text_input(
                    varprefix + "_" + uid,
                    default_value=str(round(val)),
                    size=4,
                    cssclass="number",
                )
                html.write_text_permissive(" %s " % title)
            else:
                takeover = (takeover + val) * tkovr_fac

        if self._footer:
            html.span(self._footer, class_=["vs_floating_text", "vs_age_footer"])

        html.close_div()

    def from_html_vars(self, varprefix: str) -> float:
        # TODO: Validate for correct numbers!
        return (
            request.get_integer_input_mandatory(varprefix + "_days", 0) * 3600 * 24
            + request.get_integer_input_mandatory(varprefix + "_hours", 0) * 3600
            + request.get_integer_input_mandatory(varprefix + "_minutes", 0) * 60
            + request.get_integer_input_mandatory(varprefix + "_seconds", 0)
            + request.get_integer_input_mandatory(varprefix + "_milliseconds", 0) / 1000.0
        )

    def mask(self, value: float) -> float:
        return value

    def value_to_html(self, value: float) -> ValueSpecText:
        if value == 0:
            return _("no time (zero)")
        _whole_seconds, frac = divmod(value, 1.0)
        return SecondsRenderer.detailed_str(int(value)) + (
            f" {round(frac * 1000)} ms" if frac else ""
        )

    def value_to_json(self, value: float) -> JSONValue:
        return value

    def value_from_json(self, json_value: JSONValue) -> float:
        return json_value

    def validate_datatype(self, value: float, varprefix: str) -> None:
        if not isinstance(value, float):
            raise MKUserError(
                varprefix,
                _("The value %r has type %s, but must be of type float")
                % (value, type_name(value)),
            )

    def _validate_value(self, value: float, varprefix: str) -> None:
        self._bounds.validate_value(value, varprefix)

    def transform_value(self, value: float) -> float:
        return self._bounds.transform_value(value)


class NumericRenderer:
    def __init__(
        self,
        size: int | None,
        maxvalue: SupportsFloat | None,
        label: str | None,
        unit: str,
        align: Literal["left", "right"],
    ):
        super().__init__()
        if size is not None:
            self._size = size
        elif maxvalue is not None:
            self._size = (4 if isinstance(maxvalue, float) else 1) + int(math.log10(maxvalue))
        else:
            self._size = 5
        self._label = label
        self._unit = unit
        self._align = align

    def text_input(self, varprefix: str, text: str) -> None:
        html.text_input(
            varprefix,
            default_value=text,
            cssclass="number",
            size=self._size,
            style="text-align: right;" if self._align == "right" else "",
        )

    def render_input(self, varprefix: str, value: str) -> None:
        if self._label:
            html.span(self._label, class_="vs_floating_text")
        self.text_input(varprefix, value)
        if self._unit:
            html.span(self._unit, class_="vs_floating_text")

    def format_text(self, text: str) -> str:
        if self._unit:
            text += " %s" % self._unit
        return text


class Integer(ValueSpec[int]):
    """Editor for a single integer"""

    def __init__(  # pylint: disable=redefined-builtin
        self,
        size: int | None = None,
        minvalue: int | None = None,
        maxvalue: int | None = None,
        label: str | None = None,
        unit: str = "",
        display_format: str = "%d",
        align: Literal["left", "right"] = "left",
        # ValueSpec
        title: str | None = None,
        help: ValueSpecHelp | None = None,
        default_value: ValueSpecDefault[int] = DEF_VALUE,
        validate: ValueSpecValidateFunc[int] | None = None,
    ):
        super().__init__(
            title=title,
            label=label,
            help=help,
            default_value=default_value,
            validate=validate,
        )
        self._bounds = Bounds[int](minvalue, maxvalue)
        self._renderer = NumericRenderer(
            size=size,
            maxvalue=maxvalue,
            label=label,
            unit=unit,
            align=align,
        )
        self._display_format = display_format

    def canonical_value(self) -> int:
        return self._bounds.lower(0)

    def render_input(self, varprefix: str, value: int | None) -> None:
        # This is needed for displaying the "empty field" when using Integer valuespecs in
        # ListOfStrings()
        if value is None:
            text: str = ""
        else:
            text = self._render_value(value)

        self._renderer.render_input(varprefix, text)

    def _render_value(self, value: int) -> str:
        return self._display_format % value

    def from_html_vars(self, varprefix: str) -> int:
        return request.get_integer_input_mandatory(varprefix)

    def mask(self, value: int) -> int:
        return value

    def value_to_html(self, value: int) -> ValueSpecText:
        return self._renderer.format_text(self._render_value(value))

    def value_to_json(self, value: int) -> JSONValue:
        return value

    def value_from_json(self, json_value: JSONValue) -> int:
        return int(json_value)

    def validate_datatype(self, value: int, varprefix: str) -> None:
        if isinstance(value, numbers.Integral):
            return
        raise MKUserError(
            varprefix,
            _("The value %r has the wrong type %s, but must be of type int")
            % (value, type_name(value)),
        )

    def _validate_value(self, value: int, varprefix: str) -> None:
        self._bounds.validate_value(value, varprefix)


class Filesize(Integer):
    """Filesize in byte, kibi byte, mibi byte, gibi byte, tibi byte"""

    _names = ["Byte", "KiB", "MiB", "GiB", "TiB"]

    def get_exponent(self, value: int) -> tuple[int, int]:
        for exp, count in ((exp, 1024**exp) for exp in reversed(range(len(self._names)))):
            if value == 0:
                return 0, 0
            if value % count == 0:
                return exp, int(value / count)  # fixed: true-division
        raise ValueError("Invalid value: %r" % value)

    def render_input(self, varprefix: str, value: int | None) -> None:
        # The value type is only Optional to be compatible with the base class
        if value is None:
            raise TypeError(value)
        exp, count = self.get_exponent(value)
        self._renderer.text_input(varprefix + "_size", str(count))
        html.nbsp()
        choices: Choices = [(str(nr), name) for (nr, name) in enumerate(self._names)]
        html.dropdown(varprefix + "_unit", choices, deflt=str(exp))

    def from_html_vars(self, varprefix: str) -> int:
        return int(
            request.get_float_input_mandatory(varprefix + "_size")
            * (1024 ** request.get_integer_input_mandatory(varprefix + "_unit"))
        )

    def value_to_html(self, value: int) -> ValueSpecText:
        exp, count = self.get_exponent(value)
        return f"{count} {self._names[exp]}"

    def value_to_json(self, value: int) -> JSONValue:
        return value

    def value_from_json(self, json_value: JSONValue) -> int:
        return json_value


class LegacyBinaryUnit(Enum):
    Byte = 1
    KB = 1000
    MB = 1000**2
    GB = 1000**3
    TB = 1000**4
    PB = 1000**5
    EB = 1000**6
    ZB = 1000**7
    YB = 1000**8
    RB = 1000**9
    QB = 1000**10
    KiB = 1024
    MiB = 1024**2
    GiB = 1024**3
    TiB = 1024**4
    PiB = 1024**5
    EiB = 1024**6
    ZiB = 1024**7
    YiB = 1024**8
    RiB = 1024**9
    QiB = 1024**10


class LegacyDataSize(Integer):
    """A variant of the Filesize valuespec that allows the configuration of the selectable units"""

    def __init__(  # pylint: disable=redefined-builtin
        self,
        units: Sequence[LegacyBinaryUnit] | None = None,
        label: str | None = None,
        title: str | None = None,
        help: ValueSpecHelp | None = None,
        default_value: ValueSpecDefault[int] = DEF_VALUE,
        validate: ValueSpecValidateFunc[int] | None = None,
    ):
        super().__init__(
            title=title,
            help=help,
            label=label,
            default_value=default_value,
            validate=validate,
        )
        self._units = (
            units
            if units is not None
            else [
                LegacyBinaryUnit.Byte,
                LegacyBinaryUnit.KB,
                LegacyBinaryUnit.MB,
                LegacyBinaryUnit.GB,
                LegacyBinaryUnit.TB,
                LegacyBinaryUnit.KiB,
                LegacyBinaryUnit.MiB,
                LegacyBinaryUnit.GiB,
                LegacyBinaryUnit.TiB,
            ]
        )

    def _scale_value(self, value: int) -> tuple[LegacyBinaryUnit, str]:
        sorted_units = sorted(self._units, key=lambda x: x.value)
        for unit in reversed(sorted_units):
            if value == 0:
                return sorted_units[0], "0"
            scaled, remainder = divmod(value, unit.value)
            if remainder == 0:
                return unit, f"{scaled}"

        # "0.5 GB" for instance.
        # This might in fact change the value slightly, and/or look ugly.
        # Try to do better in the native implementation.
        # Compare to TimeSpan, which is an analogous construct when seen from cmk.rulesets.v1,
        # but quite different in rendering / UX currently.
        return (u := sorted_units[-1]), f"{value / u.value!r}"

    def render_input(self, varprefix: str, value: int | None) -> None:
        # This is utterly inconsistent with what TimeSpan does :-(

        # The value type is only Optional to be compatible with the base class
        if value is None:
            raise TypeError(value)
        selected_unit, scaled_value = self._scale_value(value)
        self._renderer.text_input(varprefix + "_size", scaled_value)
        html.nbsp()
        choices: Choices = [(str(unit.value), unit.name) for unit in self._units]
        html.dropdown(varprefix + "_unit", choices, deflt=str(selected_unit.value))

    def from_html_vars(self, varprefix: str) -> int:
        return int(
            request.get_float_input_mandatory(varprefix + "_size")
            * (request.get_integer_input_mandatory(varprefix + "_unit"))
        )

    def value_to_html(self, value: int) -> ValueSpecText:
        selected_unit, scaled_value = self._scale_value(value)
        return f"{scaled_value} {selected_unit.name}"

    def value_to_json(self, value: int) -> JSONValue:
        return value

    def value_from_json(self, json_value: JSONValue) -> int:
        return json_value


class TextInput(ValueSpec[str]):
    """Editor for a line of text"""

    def __init__(  # pylint: disable=redefined-builtin
        self,
        label: str | None = None,
        size: int | Literal["max"] = 25,
        try_max_width: bool = False,
        cssclass: str = "text",
        strip: bool = True,
        allow_empty: bool = True,
        empty_text: str = "",
        read_only: bool = False,
        forbidden_chars: str = "",
        regex: None | str | Pattern[str] = None,
        regex_error: str | None = None,
        minlen: int | None = None,
        maxlen: int | None = None,
        oninput: str | None = None,
        autocomplete: str | None = None,
        placeholder: str | None = None,
        # ValueSpec
        title: str | None = None,
        help: ValueSpecHelp | None = None,
        default_value: ValueSpecDefault[str] = DEF_VALUE,
        validate: ValueSpecValidateFunc[str] | None = None,
    ):
        super().__init__(
            title=title,
            label=label,
            help=help,
            default_value=default_value,
            validate=validate,
        )
        self._label = label
        self._size = size  # also possible: "max"
        self._try_max_width = try_max_width  # If set, uses calc(100%-10px)
        self._cssclass = cssclass
        self._strip = strip
        self._allow_empty = allow_empty
        self._empty_text = empty_text
        self._read_only = read_only
        self._forbidden_chars = forbidden_chars
        if isinstance(regex, str):
            self._regex: Pattern[str] | None = re.compile(regex)
        else:
            self._regex = regex
        self._regex_error = (
            regex_error
            if regex_error is not None
            else _("Your input does not match the required format.")
        )
        self._minlen = minlen
        self._maxlen = maxlen
        self._oninput = oninput
        self._placeholder = placeholder
        self._autocomplete = autocomplete

    def allow_empty(self) -> bool:
        return self._allow_empty

    def canonical_value(self) -> str:
        return ""

    def render_input(self, varprefix: str, value: str | None) -> None:
        if self._label:
            html.span(self._label, class_="vs_floating_text")

        html.text_input(
            varprefix,
            default_value="%s" % value if value is not None else "",
            size=self._get_size(),
            try_max_width=self._try_max_width,
            read_only=self._read_only,
            cssclass=self._cssclass,
            type_="text",
            autocomplete=self._autocomplete,
            oninput=self._oninput if self._oninput else None,
            placeholder=self._placeholder,
        )

    def _get_size(self) -> int | Literal["max"]:
        """
        2.3: This is needed to make sure that the new rulespec API can
        handle the input size. There is no size parameter in the new API.
        If no placeholder is set, the old default size of 25 is used.
        """
        if self._size == "max":
            return self._size
        if self._placeholder and self._size <= (placeholder_size := len(self._placeholder)):
            return placeholder_size
        return self._size

    def mask(self, value: str) -> str:
        return value

    def value_to_html(self, value: str) -> ValueSpecText:
        if not value:
            return self._empty_text
        return value

    def from_html_vars(self, varprefix: str) -> str:
        value = request.get_str_input_mandatory(varprefix, "")
        if self._strip and value:
            value = value.strip()
        return value

    def validate_datatype(self, value: str, varprefix: str) -> None:
        if not isinstance(value, str):
            raise MKUserError(
                varprefix,
                _("The value must be of type str, but it has type %s") % type_name(value),
            )

    def _validate_value(self, value: str, varprefix: str) -> None:
        if self._forbidden_chars:
            for c in self._forbidden_chars:
                if c in value:
                    raise MKUserError(
                        varprefix,
                        _("The character <tt>%s</tt> is not allowed here.") % c,
                    )

        if not self._allow_empty and (value == "" or (self._strip and value.strip() == "")):
            raise MKUserError(
                varprefix,
                self._empty_text or _("An empty value is not allowed here."),
            )
        if value and self._regex:
            if not self._regex.match(value):
                raise MKUserError(varprefix, self._regex_error)

        if self._minlen is not None and len(value) < self._minlen:
            raise MKUserError(
                varprefix,
                _("You need to provide at least %d characters.") % self._minlen,
            )
        if self._maxlen is not None and len(value) > self._maxlen:
            raise MKUserError(
                varprefix,
                _("You must not provide more than %d characters.") % self._maxlen,
            )

    def value_to_json(self, value: str) -> JSONValue:
        return value

    def value_from_json(self, json_value: JSONValue) -> str:
        return json_value


TextAscii = TextInput  # alias added in 2.1.0 for compatibility
TextUnicode = TextInput  # alias added in 2.1.0 for compatibility


class UUID(TextInput):
    """Documentation for UUID"""

    def from_html_vars(self, varprefix: str) -> str:
        value = request.get_str_input_mandatory(varprefix, "")
        if not value:
            value = str(uuid.uuid4())
        return value

    def render_input(self, varprefix: str, value: str | None) -> None:
        html.hidden_field(varprefix, value, add_var=True)


def ID(  # pylint: disable=redefined-builtin
    label: str | None = None,
    size: int | Literal["max"] = 25,
    try_max_width: bool = False,
    cssclass: str = "text",
    strip: bool = True,
    allow_empty: bool = True,
    empty_text: str = "",
    read_only: bool = False,
    forbidden_chars: str = "",
    minlen: int | None = None,
    maxlen: int | None = None,
    oninput: str | None = None,
    autocomplete: str | None = None,
    placeholder: str | None = None,
    # ValueSpec
    title: str | None = None,
    help: ValueSpecHelp | None = None,
    default_value: ValueSpecDefault[str] = DEF_VALUE,
    validate: ValueSpecValidateFunc[str] | None = None,
) -> TextInput:
    """Internal ID as used in many places (for contact names, group name, an so on)"""
    regex_requirement_message = _(
        "An identifier must only consist of letters, digits, dash and "
        "underscore and it must start with a letter or underscore."
    )
    return TextInput(
        label=label,
        size=size,
        try_max_width=try_max_width,
        cssclass=cssclass,
        strip=strip,
        allow_empty=allow_empty,
        empty_text=empty_text,
        read_only=read_only,
        forbidden_chars=forbidden_chars,
        regex=cmk.utils.regex.regex(cmk.utils.regex.REGEX_ID, re.ASCII),
        regex_error=regex_requirement_message,
        minlen=minlen,
        maxlen=maxlen,
        oninput=oninput,
        autocomplete=autocomplete,
        placeholder=placeholder,
        title=title,
        help=help or regex_requirement_message,
        default_value=default_value,
        validate=validate,
    )


def UserID(  # pylint: disable=redefined-builtin
    label: str | None = None,
    size: int | Literal["max"] = 25,
    try_max_width: bool = False,
    cssclass: str = "text",
    strip: bool = True,
    allow_empty: bool = True,
    empty_text: str = "",
    read_only: bool = False,
    forbidden_chars: str = "",
    minlen: int | None = None,
    maxlen: int | None = None,
    oninput: str | None = None,
    autocomplete: str | None = None,
    placeholder: str | None = None,
    # ValueSpec
    title: str | None = None,
    help: ValueSpecHelp | None = None,
    default_value: ValueSpecDefault[str] = DEF_VALUE,
) -> TextInput:
    """Internal ID as used in many places (for contact names, group name, an so on)"""

    def _validate(userid_str: str, varprefix: str) -> None:
        try:
            UserId(userid_str)
            if userid_str.strip() == "":
                raise ValueError("Empty Value not allowed")
        except ValueError as exception:
            raise MKUserError(
                varprefix,
                _(
                    "An identifier must only consist of letters, digits, dollar, underscore, dash, "
                    "dot, plus, and at. It must start with a letter, digit, dollar, or underscore."
                ),
            ) from exception

    return TextInput(
        label=label,
        size=size,
        try_max_width=try_max_width,
        cssclass=cssclass,
        strip=strip,
        allow_empty=allow_empty,
        empty_text=empty_text,
        read_only=read_only,
        forbidden_chars=forbidden_chars,
        minlen=minlen,
        maxlen=maxlen,
        oninput=oninput,
        autocomplete=autocomplete,
        placeholder=placeholder,
        title=title,
        help=help,
        default_value=default_value,
        validate=_validate,
    )


class RegExp(TextInput):
    # TODO: Make this an enum
    infix: Literal["infix"] = "infix"
    prefix: Literal["prefix"] = "prefix"
    complete: Literal["complete"] = "complete"

    def __init__(  # pylint: disable=redefined-builtin
        self,
        mode: Literal["infix", "prefix", "complete"],
        case_sensitive: bool = True,
        mingroups: int = 0,
        maxgroups: int | None = None,
        # TextInput
        label: str | None = None,
        size: int | Literal["max"] = 25,
        try_max_width: bool = False,
        cssclass: str = "text",
        strip: bool = True,
        allow_empty: bool = True,
        empty_text: str = "",
        read_only: bool = False,
        forbidden_chars: str = "",
        regex: None | str | Pattern[str] = None,
        regex_error: str | None = None,
        minlen: int | None = None,
        maxlen: int | None = None,
        oninput: str | None = None,
        autocomplete: str | None = None,
        placeholder: str | None = None,
        # From ValueSpec
        title: str | None = None,
        help: ValueSpecHelp | None = None,
        default_value: ValueSpecDefault[str] = DEF_VALUE,
        validate: ValueSpecValidateFunc[str] | None = None,
    ):
        super().__init__(
            label=label,
            size=size,
            try_max_width=try_max_width,
            cssclass=self._css_classes(case_sensitive, mode),
            strip=strip,
            allow_empty=allow_empty,
            empty_text=empty_text,
            read_only=read_only,
            forbidden_chars=forbidden_chars,
            regex=regex,
            regex_error=regex_error,
            minlen=minlen,
            maxlen=maxlen,
            oninput=oninput,
            autocomplete=autocomplete,
            title=title,
            help=help,
            default_value=default_value,
            validate=validate,
            placeholder=placeholder,
        )

        self._mode = mode
        self._case_sensitive = case_sensitive
        self._mingroups = mingroups
        self._maxgroups = maxgroups

    def help(self) -> str | HTML | None:
        help_text: list[str | HTML] = []

        default_help_text = super().help()
        if default_help_text is not None:
            help_text.append(
                escaping.escape_to_html_permissive(str(default_help_text), escape_links=False)
                + HTMLWriter.render_br()
                + HTMLWriter.render_br()
            )

        help_text.append(_("The text entered here is handled as a regular expression pattern."))

        if self._mode == RegExp.infix:
            help_text.append(
                _(
                    "The pattern is applied as infix search. Add a leading <tt>^</tt> "
                    "to make it match from the beginning and/or a tailing <tt>$</tt> "
                    "to match till the end of the text."
                )
            )
        elif self._mode == RegExp.prefix:
            help_text.append(
                _(
                    "The pattern is matched from the beginning. Add a tailing "
                    "<tt>$</tt> to change it to a whole text match."
                )
            )
        elif self._mode == RegExp.complete:
            help_text.append(
                _(
                    "The pattern is matching the whole text. You can add <tt>.*</tt> "
                    "in front or at the end of your pattern to make it either a prefix "
                    "or infix search."
                )
            )

        if self._case_sensitive is True:
            help_text.append(_("The match is case sensitive."))
        elif self._case_sensitive is False:
            help_text.append(_("The match is case insensitive."))

        help_text.append(
            _("Read more about [regexes|regular expression matching in Checkmk] in our user guide.")
        )

        return " ".join("%s" % h for h in help_text)

    def _css_classes(self, case_sensitive: bool, mode: str | None) -> str:
        classes = ["text", "regexp"]

        if case_sensitive is True:
            classes.append("case_sensitive")
        elif case_sensitive is False:
            classes.append("case_insensitive")

        if mode is not None:
            classes.append(mode)

        return " ".join(classes)

    def _validate_value(self, value: str, varprefix: str) -> None:
        super()._validate_value(value, varprefix)

        # Check if the string is a valid regex
        try:
            with warnings.catch_warnings(action="error", category=FutureWarning):
                compiled = re.compile(value)

        except FutureWarning as e:
            warnings.warn(f"{e} in {value}", RegexFutureWarning)
            compiled = re.compile(value)

        except re.error as e:
            raise MKUserError(varprefix, _("Invalid regular expression: %s") % e)

        if compiled.groups < self._mingroups:
            raise MKUserError(
                varprefix,
                _(
                    "Your regular expression containes <b>%d</b> groups. "
                    "You need at least <b>%d</b> groups."
                )
                % (compiled.groups, self._mingroups),
            )
        if self._maxgroups is not None and compiled.groups > self._maxgroups:
            raise MKUserError(
                varprefix,
                _(
                    "Your regular expression containes <b>%d</b> groups. "
                    "It must have at most <b>%d</b> groups."
                )
                % (compiled.groups, self._maxgroups),
            )


RegExpUnicode = RegExp  # alias added in 2.1.0 for compatibility


class EmailAddress(TextInput):
    def __init__(  # pylint: disable=redefined-builtin
        self,
        make_clickable: bool = False,
        # TextInput
        label: str | None = None,
        size: int | Literal["max"] = 40,
        try_max_width: bool = False,
        cssclass: str = "text",
        strip: bool = True,
        allow_empty: bool = True,
        empty_text: str = "",
        read_only: bool = False,
        forbidden_chars: str = "",
        regex_error: str | None = None,
        minlen: int | None = None,
        maxlen: int | None = None,
        oninput: str | None = None,
        autocomplete: str | None = None,
        # From ValueSpec
        title: str | None = None,
        help: ValueSpecHelp | None = None,
        default_value: ValueSpecDefault[str] = DEF_VALUE,
        validate: ValueSpecValidateFunc[str] | None = None,
    ):
        super().__init__(
            label=label,
            size=size,
            try_max_width=try_max_width,
            cssclass=cssclass,
            strip=strip,
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
            regex=re.compile(
                r"^[\w.!#$%&'*+-=?^`{|}~]+@(localhost|[\w.-]+\.[\w]{2,24})$",
                re.I | re.UNICODE,
            ),
            regex_error=regex_error,
            minlen=minlen,
            maxlen=maxlen,
            oninput=oninput,
            autocomplete=autocomplete,
            title=title,
            help=help,
            default_value=default_value,
            validate=validate,
        )
        self._make_clickable = make_clickable

    def value_to_html(self, value: str) -> ValueSpecText:
        if not value:
            return super().value_to_html(value)
        if self._make_clickable:
            return HTMLWriter.render_a(value, href="mailto:%s" % value)
        return value


def IPNetwork(  # pylint: disable=redefined-builtin
    ip_class: None | type[ipaddress.IPv4Network] | type[ipaddress.IPv6Network] = None,
    # TextInput
    allow_empty: bool = True,
    size: int | Literal["max"] = 34,
    # From ValueSpec
    title: str | None = None,
    help: ValueSpecHelp | None = None,
    default_value: ValueSpecDefault[str] = DEF_VALUE,
) -> TextInput:
    """Same as IPv4Network, but allowing both IPv4 and IPv6"""

    def _try(
        cls: type[ipaddress.IPv4Network] | type[ipaddress.IPv6Network], value: str
    ) -> Exception | None:
        try:
            cls(value)
            return None
        except ValueError as exc:
            return exc

    def _validate_value(value: str, varprefix: str) -> None:
        if ip_class is None:
            if (e4 := _try(ipaddress.IPv4Network, value)) is not None and (
                e6 := _try(ipaddress.IPv6Network, value)
            ) is not None:
                raise MKUserError(
                    varprefix,
                    _("Invalid host or network address. IPv4: %s, IPv6: %s") % (e4, e6),
                )
        elif issubclass(ip_class, ipaddress.IPv4Network):
            if (e4 := _try(ipaddress.IPv4Network, value)) is not None:
                raise MKUserError(varprefix, _("Invalid IPv4 address: %s") % e4)
        elif (e6 := _try(ipaddress.IPv6Network, value)) is not None:
            raise MKUserError(varprefix, _("Invalid IPv6 address: %s") % e6)

    return TextInput(
        validate=_validate_value,
        allow_empty=allow_empty,
        size=size,
        title=title,
        help=help,
        default_value=default_value,
    )


def IPv4Network(  # pylint: disable=redefined-builtin
    title: str | None = None, help: ValueSpecHelp | None = None
) -> TextInput:
    """Network as used in routing configuration, such as '10.0.0.0/8' or '192.168.56.1'"""
    return IPNetwork(ip_class=ipaddress.IPv4Network, size=18, title=title, help=help)


def IPAddress(  # pylint: disable=redefined-builtin
    ip_class: type[ipaddress.IPv4Address] | type[ipaddress.IPv6Address] | None = None,
    size: int | Literal["max"] = 34,
    title: str | None = None,
    help: ValueSpecHelp | None = None,
    default_value: ValueSpecDefault[str] = DEF_VALUE,
    allow_empty: bool = True,
) -> TextInput:
    """The IP address allowing for both IPv4 and IPv6."""

    def _try(
        cls: type[ipaddress.IPv4Address] | type[ipaddress.IPv6Address], value: str
    ) -> Exception | None:
        try:
            cls(value)
            return None
        except ValueError as exc:
            return exc

    def _validate_value(value: str, varprefix: str) -> None:
        if ip_class is None:
            if (e4 := _try(ipaddress.IPv4Address, value)) is not None and (
                e6 := _try(ipaddress.IPv6Address, value)
            ) is not None:
                raise MKUserError(
                    varprefix,
                    _("Invalid host or IP address. IPv4: %s, IPv6: %s") % (e4, e6),
                )
        elif issubclass(ip_class, ipaddress.IPv4Address):
            if (e4 := _try(ipaddress.IPv4Address, value)) is not None:
                raise MKUserError(varprefix, _("Invalid IPv4 address: %s") % e4)
        elif (e6 := _try(ipaddress.IPv6Address, value)) is not None:
            raise MKUserError(varprefix, _("Invalid IPv6 address: %s") % e6)

    return TextInput(
        validate=_validate_value,
        size=size,
        title=title,
        help=help,
        default_value=default_value,
        allow_empty=allow_empty,
    )


def IPv4Address(  # pylint: disable=redefined-builtin
    title: str | None = None,
    help: ValueSpecHelp | None = None,
    default_value: ValueSpecDefault[str] = DEF_VALUE,
) -> TextInput:
    return IPAddress(
        ip_class=ipaddress.IPv4Address,
        size=16,
        title=title,
        help=help,
        default_value=default_value,
    )


def _validate_hostname(text: str | None, varprefix: str) -> None:
    # MonitoredHostname accepts also Nones
    if text is None:
        return

    try:
        HostAddressType(text)
    except ValueError as exception:
        raise MKUserError(
            varprefix,
            _(
                "Please enter a valid host name or IPv4 address. "
                "Only letters, digits, dash, underscore and dot are allowed."
            ),
        ) from exception


def Hostname(  # pylint: disable=redefined-builtin
    # TextInput
    allow_empty: bool = False,
    # ValueSpec
    title: str | None = None,
    help: ValueSpecHelp | None = None,
    default_value: ValueSpecDefault[str] = DEF_VALUE,
    size: int = 38,
) -> TextInput:
    """A host name with or without domain part. Also allow IP addresses"""
    return TextInput(
        size=size,
        allow_empty=allow_empty,
        title=title,
        help=help,
        default_value=default_value,
        validate=_validate_hostname,
    )


class HostAddress(TextInput):
    """Use this for all host / ip address input fields!"""

    def __init__(  # pylint: disable=redefined-builtin
        self,
        allow_host_name: bool = True,
        allow_ipv4_address: bool = True,
        allow_ipv6_address: bool = True,
        # TextInput
        label: str | None = None,
        size: int | Literal["max"] = 64,
        try_max_width: bool = False,
        cssclass: str = "text",
        strip: bool = True,
        allow_empty: bool = True,
        empty_text: str = "",
        read_only: bool = False,
        forbidden_chars: str = "",
        regex: None | str | Pattern[str] = None,
        regex_error: str | None = None,
        minlen: int | None = None,
        maxlen: int | None = None,
        oninput: str | None = None,
        autocomplete: str | None = None,
        # ValueSpec
        title: str | None = None,
        help: ValueSpecHelp | None = None,
        default_value: ValueSpecDefault[str] = DEF_VALUE,
        validate: ValueSpecValidateFunc[str] | None = None,
    ):
        super().__init__(
            label=label,
            size=size,
            try_max_width=try_max_width,
            cssclass=cssclass,
            strip=strip,
            allow_empty=allow_empty,
            empty_text=empty_text,
            read_only=read_only,
            forbidden_chars=forbidden_chars,
            regex=regex,
            regex_error=regex_error,
            minlen=minlen,
            maxlen=maxlen,
            oninput=oninput,
            autocomplete=autocomplete,
            title=title,
            help=help,
            default_value=default_value,
            validate=validate,
        )
        self._allow_host_name = allow_host_name
        self._allow_ipv4_address = allow_ipv4_address
        self._allow_ipv6_address = allow_ipv6_address

    def _validate_value(self, value: str, varprefix: str) -> None:
        if value and self._allow_host_name and self._is_valid_host_name(value):
            return

        if value and self._allow_ipv4_address and self._is_valid_ipv4_address(value):
            return

        if value and self._allow_ipv6_address and self._is_valid_ipv6_address(value):
            return

        if value == "" and self._allow_empty:
            return

        raise MKUserError(
            varprefix,
            _("Invalid host address. You need to specify the address either as %s.")
            % ", ".join(self._allowed_type_names()),
        )

    def _is_valid_host_name(self, hostname: str) -> bool:
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

    def _is_valid_ipv4_address(self, address: str) -> bool:
        # http://stackoverflow.com/questions/319279/how-to-validate-ip-address-in-python/4017219#4017219
        try:
            socket.inet_pton(socket.AF_INET, address)
        except AttributeError:  # no inet_pton here, sorry
            try:
                socket.inet_aton(address)
            except OSError:
                return False

            return address.count(".") == 3

        except OSError:  # not a valid address
            return False

        return True

    def _is_valid_ipv6_address(self, address: str) -> bool:
        # http://stackoverflow.com/questions/319279/how-to-validate-ip-address-in-python/4017219#4017219
        try:
            address = address.split("%")[0]
            socket.inet_pton(socket.AF_INET6, address)
        except OSError:  # not a valid address
            return False
        return True

    def _allowed_type_names(self) -> Iterable[str]:
        allowed: list[str] = []
        if self._allow_host_name:
            allowed.append(_("Host- or DNS name"))

        if self._allow_ipv4_address:
            allowed.append(_("IPv4 address"))

        if self._allow_ipv6_address:
            allowed.append(_("IPv6 address"))

        return allowed


def AbsoluteDirname(  # pylint: disable=redefined-builtin
    # TextInput
    allow_empty: bool = True,
    size: int | Literal["max"] = 25,
    # ValueSpec
    title: str | None = None,
    help: ValueSpecHelp | None = None,
    default_value: ValueSpecDefault[str] = DEF_VALUE,
    validate: ValueSpecValidateFunc[str] | None = None,
) -> TextInput:
    return TextInput(
        regex=re.compile("^(/|(/[^/]+)+)$"),
        regex_error=_("Please enter a valid absolut pathname with / as a path separator."),
        allow_empty=allow_empty,
        size=size,
        title=title,
        help=help,
        default_value=default_value,
        validate=validate,
    )


class Url(TextInput):
    def __init__(  # pylint: disable=redefined-builtin
        self,
        default_scheme: str,
        allowed_schemes: Collection[str],
        show_as_link: bool = False,
        target: str | None = None,
        # TextInput
        label: str | None = None,
        size: int | Literal["max"] = 64,
        try_max_width: bool = False,
        cssclass: str = "text",
        strip: bool = True,
        allow_empty: bool = True,
        empty_text: str = "",
        read_only: bool = False,
        forbidden_chars: str = "",
        regex: None | str | Pattern[str] = None,
        regex_error: str | None = None,
        minlen: int | None = None,
        maxlen: int | None = None,
        oninput: str | None = None,
        autocomplete: str | None = None,
        placeholder: str | None = None,
        # ValueSpec
        title: str | None = None,
        help: ValueSpecHelp | None = None,
        default_value: ValueSpecDefault[str] = DEF_VALUE,
        validate: ValueSpecValidateFunc[str] | None = None,
    ):
        super().__init__(
            label=label,
            size=size,
            try_max_width=try_max_width,
            cssclass=cssclass,
            strip=strip,
            allow_empty=allow_empty,
            empty_text=empty_text,
            read_only=read_only,
            forbidden_chars=forbidden_chars,
            regex=regex,
            regex_error=regex_error,
            minlen=minlen,
            maxlen=maxlen,
            oninput=oninput,
            autocomplete=autocomplete,
            placeholder=placeholder,
            title=title,
            help=help,
            default_value=default_value,
            validate=validate,
        )
        self._default_scheme = default_scheme
        self._allowed_schemes = allowed_schemes
        self._show_as_link = show_as_link
        self._link_target = target

    def _validate_value(self, value: str, varprefix: str) -> None:
        if value is None:
            raise TypeError(value)
        super()._validate_value(value, varprefix)

        if self._allow_empty and value == "":
            return

        parts = urllib.parse.urlparse(value)
        if not parts.scheme or not parts.netloc:
            raise MKUserError(varprefix, _("Invalid URL given"))

        if parts.scheme not in self._allowed_schemes:
            raise MKUserError(
                varprefix,
                _("Invalid URL scheme. Must be one of: %s") % ", ".join(self._allowed_schemes),
            )
        if not is_allowed_url(value, cross_domain=True, schemes=self._allowed_schemes):
            raise MKUserError(varprefix, _("Invalid URL given"))

    def from_html_vars(self, varprefix: str) -> str:
        value = super().from_html_vars(varprefix)
        if value and "://" not in value:
            value = self._default_scheme + "://" + value
        return value

    def value_to_html(self, value: str) -> ValueSpecText:
        if not any(value.startswith(scheme + "://") for scheme in self._allowed_schemes):
            value = self._default_scheme + "://" + value

        try:
            parts = urllib.parse.urlparse(value)
            if parts.path in ["", "/"]:
                text = parts.netloc
            else:
                text = parts.netloc + parts.path
        except Exception:
            text = value[7:]

        # Remove trailing / if the url does not contain any path component
        if self._show_as_link:
            return HTMLWriter.render_a(
                text,
                href=value,
                target=self._link_target if self._link_target else None,
            )

        return value


def HTTPUrl(  # pylint: disable=redefined-builtin
    show_as_link: bool = True,
    # Url
    regex: None | str | Pattern[str] = None,
    regex_error: str | None = None,
    # TextInput
    allow_empty: bool = True,
    size: int | Literal["max"] = 80,
    # ValueSpec
    title: str | None = None,
    help: ValueSpecHelp | None = None,
    default_value: ValueSpecDefault[str] = DEF_VALUE,
    validate: ValueSpecValidateFunc[str] | None = None,
) -> Url:
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
        validate=validate,
    )


def HTTPSUrl(  # pylint: disable=redefined-builtin
    show_as_link: bool = True,
    # Url
    regex: None | str | Pattern[str] = None,
    regex_error: str | None = None,
    # TextInput
    allow_empty: bool = True,
    size: int | Literal["max"] = 80,
    # ValueSpec
    title: str | None = None,
    help: ValueSpecHelp | None = None,
    default_value: ValueSpecDefault[str] = DEF_VALUE,
    validate: ValueSpecValidateFunc[str] | None = None,
) -> Url:
    """Valuespec for a HTTPS Url, that automatically adds https:// to the value if no scheme has been specified"""
    return Url(
        allowed_schemes=["https"],
        default_scheme="https",
        regex=regex,
        regex_error=regex_error,
        show_as_link=show_as_link,
        allow_empty=allow_empty,
        size=size,
        title=title,
        help=help,
        default_value=default_value,
        validate=validate,
    )


class CheckmkVersionInput(TextInput):
    def _validate_value(self, value: str, varprefix: str) -> None:
        try:
            Version.from_str(value)
        except ValueError:
            raise MKUserError(varprefix, _("%s is not a valid version number.") % value)

        super()._validate_value(value, varprefix)


class TextAreaUnicode(TextInput):
    def __init__(  # pylint: disable=redefined-builtin
        self,
        cols: int = 60,
        rows: int | Literal["auto"] = 20,
        minrows: int = 0,
        monospaced: bool = False,
        # TextInput
        label: str | None = None,
        size: int | Literal["max"] = 64,
        try_max_width: bool = False,
        cssclass: str = "text",
        strip: bool = True,
        allow_empty: bool = True,
        empty_text: str = "",
        read_only: bool = False,
        forbidden_chars: str = "",
        regex: None | str | Pattern[str] = None,
        regex_error: str | None = None,
        minlen: int | None = None,
        maxlen: int | None = None,
        oninput: str | None = None,
        autocomplete: str | None = None,
        # ValueSpec
        title: str | None = None,
        help: ValueSpecHelp | None = None,
        default_value: ValueSpecDefault[str] = DEF_VALUE,
        validate: ValueSpecValidateFunc[str] | None = None,
    ):
        super().__init__(
            label=label,
            size=size,
            try_max_width=try_max_width,
            cssclass=cssclass,
            strip=strip,
            allow_empty=allow_empty,
            empty_text=empty_text,
            read_only=read_only,
            forbidden_chars=forbidden_chars,
            regex=regex,
            regex_error=regex_error,
            minlen=minlen,
            maxlen=maxlen,
            oninput=oninput,
            autocomplete=autocomplete,
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

    def value_to_html(self, value: str) -> ValueSpecText:
        if self._monospaced:
            return HTMLWriter.render_pre(value, class_="ve_textarea")
        return value.replace("\n", "<br>")

    def render_input(self, varprefix: str, value: str | None) -> None:
        if value is None:
            value = ""  # should never happen, but avoids exception for invalid input
        if self._rows == "auto":
            func = "cmk.valuespecs.textarea_resize(this);"
            attrs = {
                "onkeyup": func,
                "onmousedown": func,
                "onmouseup": func,
                "onmouseout": func,
            }
            if request.has_var(varprefix):
                rows = len(self.from_html_vars(varprefix).splitlines())
            else:
                rows = len(value.splitlines())
            rows = max(rows, self._minrows)
        else:
            attrs = {}
            rows = self._rows

        if self._monospaced:
            attrs["class"] = "tt"

        html.text_area(
            varprefix,
            value,
            rows=rows,
            cols=self._cols,
            try_max_width=self._try_max_width,
            **attrs,
        )

    # Overridden because we do not want to strip() here and remove '\r'
    def from_html_vars(self, varprefix: str) -> str:
        text = request.get_str_input_mandatory(varprefix, "").replace("\r", "")
        if text and not text.endswith("\n"):
            text += "\n"  # force newline at end
        return text


# TODO: Rename the valuespec here to ExistingFilename or somehting similar
# TODO: Change to factory?
class Filename(TextInput):
    """A variant of TextInput() that validates a path to a filename that lies in an existing directory."""

    # TODO: Cleanup default / default_value?
    def __init__(  # pylint: disable=redefined-builtin
        self,
        default: str = "/tmp/foo",  # nosec B108 # BNS:13b2c8
        trans_func: Callable[[str], str] | None = None,
        # TextInput
        label: str | None = None,
        size: int | Literal["max"] = 60,
        try_max_width: bool = False,
        cssclass: str = "text",
        strip: bool = True,
        allow_empty: bool = True,
        empty_text: str = "",
        read_only: bool = False,
        forbidden_chars: str = "",
        regex: None | str | Pattern[str] = None,
        regex_error: str | None = None,
        minlen: int | None = None,
        maxlen: int | None = None,
        oninput: str | None = None,
        autocomplete: str | None = None,
        # ValueSpec
        title: str | None = None,
        help: ValueSpecHelp | None = None,
        default_value: ValueSpecDefault[str] = DEF_VALUE,
        validate: ValueSpecValidateFunc[str] | None = None,
    ):
        super().__init__(
            label=label,
            size=size,
            try_max_width=try_max_width,
            cssclass=cssclass,
            strip=strip,
            allow_empty=allow_empty,
            empty_text=empty_text,
            read_only=read_only,
            forbidden_chars=forbidden_chars,
            regex=regex,
            regex_error=regex_error,
            minlen=minlen,
            maxlen=maxlen,
            oninput=oninput,
            autocomplete=autocomplete,
            title=title,
            help=help,
            default_value=default_value,
            validate=validate,
        )
        self._default_path = default
        self._trans_func = trans_func

    def canonical_value(self) -> str:
        return self._default_path

    def _validate_value(self, value: str, varprefix: str) -> None:
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
                _(
                    "Sorry, only absolute filenames are allowed. "
                    "Your filename must begin with a slash."
                ),
            )
        if value[-1] == "/":
            raise MKUserError(varprefix, _("Your filename must not end with a slash."))

        directory = Path(value).parent
        if not directory.is_dir():
            raise MKUserError(
                varprefix,
                _("The directory %s does not exist or is not a directory.") % directory,
            )

        # Write permissions to the file cannot be checked here since we run with Apache
        # permissions and the file might be created with Nagios permissions (on OMD this
        # is the same, but for others not)


class ListOfStrings(ValueSpec[Sequence[str]]):
    def __init__(  # pylint: disable=redefined-builtin
        self,
        # ListOfStrings
        valuespec: ValueSpec[str] | None = None,
        size: int | Literal["max"] = 25,
        orientation: Literal["vertical", "horizontal"] = "vertical",
        allow_empty: bool = True,
        empty_text: str = "",
        max_entries: int | None = None,
        separator: str = "",
        split_on_paste: bool = True,
        split_separators: str = ";",
        # ValueSpec
        title: str | None = None,
        help: ValueSpecHelp | None = None,
        default_value: ValueSpecDefault[Sequence[str]] = DEF_VALUE,
        validate: ValueSpecValidateFunc[Sequence[str]] | None = None,
    ):
        super().__init__(title=title, help=help, default_value=default_value, validate=validate)

        self._valuespec: ValueSpec[str] = (
            valuespec if valuespec is not None else TextInput(size=size)
        )
        self._vertical = orientation == "vertical"
        self._allow_empty = allow_empty
        self._empty_text = empty_text
        self._max_entries = max_entries
        self._separator = separator  # in case of float

        self._split_on_paste = split_on_paste
        self._split_separators = split_separators

    def help(self) -> str | HTML | None:
        help_texts = [
            super().help(),
            self._valuespec.help(),
        ]

        if self._split_on_paste:
            help_texts.append(
                _(
                    "You may paste a text from your clipboard which contains several "
                    'parts separated by "%s" characters into the last input field. The text will '
                    "then be split by these separators and the single parts are added into dedicated "
                    "input fields."
                )
                % self._split_separators
            )

        return " ".join("%s" % t for t in help_texts if t)

    def allow_empty(self) -> bool:
        return self._allow_empty

    def render_input(self, varprefix: str, value: Sequence[str]) -> None:
        # Form already submitted?
        if request.has_var(varprefix + "_0"):
            value = self.from_html_vars(varprefix)
            # Remove variables from URL, so that they do not appear
            # in hidden_fields()
            nr = 0
            while request.has_var(varprefix + "_%d" % nr):
                request.del_var(varprefix + "_%d" % nr)
                nr += 1

        class_ = ["listofstrings"]
        if self._vertical:
            class_.append("vertical")
        else:
            class_.append("horizontal")
        html.open_div(id_=varprefix, class_=class_)

        elements: list[str | None] = []
        elements += value
        elements.append(None)
        for nr, s in enumerate(elements):
            html.open_div()
            # FIXME: Typing chaos ahead! TextInput.render_input *can* handle None as its
            # 2nd argument, but this is not the case for a ValueSpec[str] in general!
            self._valuespec.render_input(varprefix + "_%d" % nr, s)  # type: ignore[arg-type]
            if not self._vertical and self._separator:
                html.nbsp()
                html.write_text_permissive(self._separator)
                html.nbsp()
            html.close_div()
        html.close_div()
        html.div("", style="clear:left;")
        html.javascript(
            "cmk.valuespecs.list_of_strings_init(%s, %s, %s);"
            % (
                json.dumps(varprefix),
                json.dumps(self._split_on_paste),
                json.dumps(self._split_separators),
            )
        )

    def canonical_value(self) -> Sequence[str]:
        return []

    def value_to_html(self, value: Sequence[str]) -> ValueSpecText:
        if not value:
            return self._empty_text

        if self._vertical:
            s = [
                HTMLWriter.render_tr(HTMLWriter.render_td(self._valuespec.value_to_html(v)))
                for v in value
            ]
            return HTMLWriter.render_table(HTML.empty().join(s))
        return HTML.without_escaping(", ").join(self._valuespec.value_to_html(v) for v in value)

    def from_html_vars(self, varprefix: str) -> Sequence[str]:
        list_prefix = varprefix + "_"
        return [
            self._valuespec.from_html_vars(varname)
            for varname, value in request.itervars()
            if varname.startswith(list_prefix)
            and varname[len(list_prefix) :].isdigit()
            and value is not None
            and value.strip()
        ]

    def validate_datatype(self, value: Sequence[str], varprefix: str) -> None:
        if not isinstance(value, list):
            raise MKUserError(
                varprefix,
                _("Expected data type is list, but your type is %s.") % type_name(value),
            )
        for nr, s in enumerate(value):
            self._valuespec.validate_datatype(s, varprefix + "_%d" % nr)

    def _validate_value(self, value: Sequence[str], varprefix: str) -> None:
        if len(value) == 0 and not self._allow_empty:
            if self._empty_text:
                msg = self._empty_text
            else:
                msg = _("Please specify at least one value")
            raise MKUserError(varprefix + "_0", msg)

        if self._max_entries is not None and len(value) > self._max_entries:
            raise MKUserError(
                varprefix + "_%d" % self._max_entries,
                _("You can specify at most %d entries") % self._max_entries,
            )

        for nr, s in enumerate(value):
            self._valuespec.validate_value(s, varprefix + "_%d" % nr)

    def has_show_more(self) -> bool:
        return self._valuespec.has_show_more()

    def mask(self, value: Sequence[str]) -> Sequence[str]:
        return [self._valuespec.mask(e) for e in value]

    def value_to_json(self, value: Sequence[str]) -> JSONValue:
        return [self._valuespec.value_to_json(e) for e in value]

    def value_from_json(self, json_value: JSONValue) -> Sequence[str]:
        return [self._valuespec.value_from_json(e) for e in json_value]

    def transform_value(self, value: Sequence[str]) -> Sequence[str]:
        return [self._valuespec.transform_value(v) for v in value]


def NetworkPort(  # pylint: disable=redefined-builtin
    title: str | None = None,
    size: int | None = None,
    help: str | None = None,
    minvalue: int = 0,
    maxvalue: int = 65535,
    label: str | None = None,
    default_value: ValueSpecDefault[int] = DEF_VALUE,
) -> Integer:
    return Integer(
        title=title,
        help=help,
        minvalue=minvalue,
        maxvalue=maxvalue,
        default_value=default_value,
        label=label,
    )


# FIXME: Using a ListOfStrings for a list of ints is fundamentally wrong! Perhaps we should use ListOf here.
def ListOfNetworkPorts(title: str | None, default_value: Sequence[int]) -> ListOfStrings:
    return ListOfStrings(
        valuespec=cast(ValueSpec[str], NetworkPort(title=_("Port"))),
        title=title,
        orientation="horizontal",
        default_value=cast(Sequence[str], default_value),
    )


ListOfModel = Sequence[T]


class ListOf(ValueSpec[ListOfModel[T]]):
    """Generic list-of-valuespec ValueSpec with Javascript-based add/delete/move"""

    class Style(Enum):
        REGULAR = "regular"
        FLOATING = "floating"

    def __init__(  # pylint: disable=redefined-builtin
        self,
        valuespec: ValueSpec[T],
        magic: str = "@!@",
        add_label: str | None = None,
        del_label: str | None = None,
        movable: bool = True,
        # https://github.com/python/cpython/issues/90015
        style: "ListOf.Style | None" = None,
        totext: str | None = None,
        text_if_empty: str | None = None,
        allow_empty: bool = True,
        empty_text: str | None = None,
        sort_by: int | None = None,
        first_element_vs: ValueSpec[T] | None = None,
        add_icon: Icon | None = None,
        ignore_complain: bool = False,
        # ValueSpec
        title: str | None = None,
        help: ValueSpecHelp | None = None,
        default_value: ValueSpecDefault[ListOfModel[T]] = DEF_VALUE,
        validate: ValueSpecValidateFunc[ListOfModel[T]] | None = None,
    ):
        super().__init__(title=title, help=help, default_value=default_value, validate=validate)
        self._valuespec = valuespec
        self._magic = magic
        self._add_label = add_label if add_label else _("Add new element")
        self._del_label = del_label if del_label else _("Delete this entry")
        self._movable = movable
        self._style = style or ListOf.Style.REGULAR
        self._totext = totext  # pattern with option %d
        self._text_if_empty = text_if_empty if text_if_empty is not None else _("No entries")
        self._allow_empty = allow_empty
        self._empty_text = (
            empty_text if empty_text is not None else _("Please specify at least one entry")
        )

        # Makes a sort button visible that can be used to sort the list in the GUI
        # (without submitting the form). But this currently only works for list of
        # tuples that contain input field elements directly. The value of sort_by
        # refers to the index of the sort values in the tuple
        self._sort_by = sort_by
        self._first_element_vs = first_element_vs
        self._add_icon = add_icon
        self._ignore_complain = ignore_complain

    def help(self) -> str | HTML | None:
        return " ".join(str(t) for t in [super().help(), self._valuespec.help()] if t)

    def allow_empty(self) -> bool:
        return self._allow_empty

    # Implementation idea: we render our element-valuespec
    # once in a hidden div that is not evaluated. All occurances
    # of a magic string are replaced with the actual number
    # of entry, while beginning with 1 (this makes visual
    # numbering in labels, etc. possible). The current number
    # of entries is stored in the hidden variable 'varprefix'
    def render_input(self, varprefix: str, value: ListOfModel[T]) -> None:
        html.open_div(class_=["valuespec_listof", self._style.value])

        # Beware: the 'value' is only the default value in case the form
        # has not yet been filled in. In the complain phase we must
        # ignore 'value' but reuse the input from the HTML variables -
        # even if they are not syntactically correct. Calling from_html_vars
        # here is *not* an option since this might not work in case of
        # a wrong user input.

        # Render reference element for cloning
        # FIXME: self._valuespec.default_value() can be None!
        self._show_reference_entry(varprefix, self._magic, self._valuespec.default_value())

        # In the 'complain' phase, where the user already saved the
        # form but the validation failed, we must not display the
        # original 'value' but take the value from the HTML variables.
        if request.has_var("%s_count" % varprefix):
            count = len(self.get_indexes(varprefix))
            if not self._ignore_complain:
                # FIXME: Using None here is completely wrong!
                value = [None] * count  # type: ignore[list-item]  # dummy for the loop
        else:
            count = len(value)

        html.hidden_field(
            "%s_count" % varprefix, str(count), id_="%s_count" % varprefix, add_var=True
        )

        self._show_entries(varprefix, value)

        html.close_div()

        if count:
            html.javascript(
                "cmk.valuespecs.listof_update_indices(%s)" % json.dumps(varprefix),
                data_cmk_execute_after_replace="",
            )

    def _show_entries(self, varprefix: str, value: ListOfModel[T]) -> None:
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

    def _list_buttons(self, varprefix: str) -> None:
        onclick: str = f"cmk.valuespecs.listof_add({json.dumps(varprefix)}, {json.dumps(self._magic)}, {json.dumps(self._style.value)})"
        if self._add_icon:
            html.open_a(
                id_=varprefix + "_add",
                class_=["vlof_add_button"],
                href="javascript:void(0)",
                onclick=onclick,
                target="",
            )
            html.icon(self._add_icon)
            html.span(self._add_label)
            html.close_a()
        else:
            html.jsbutton(
                varname=varprefix + "_add",
                text=self._add_label,
                onclick=onclick,
            )

        if self._sort_by is not None:
            html.jsbutton(
                varprefix + "_sort",
                _("Sort"),
                f"cmk.valuespecs.listof_sort({json.dumps(varprefix)}, {json.dumps(self._magic)}, {json.dumps(self._sort_by)})",
            )

    def _show_reference_entry(self, varprefix: str, index: str, value: T) -> None:
        if self._style == ListOf.Style.REGULAR:
            html.open_table(style="display:none;")

            html.open_tbody(id_="%s_prototype" % varprefix, class_="vlof_prototype")
            self._show_entry(varprefix, index, value)
            html.close_tbody()

            # In case there is a specific first element vs, render another prototype for the first
            # element. This makes sure that adding an element works as expected also if the added
            # element is the first one - i.e. when there is no element given before.
            if self._first_element_vs:
                html.open_tbody(id_="%s_first_elem_prototype" % varprefix, class_="vlof_prototype")
                self._show_entry(varprefix, f"{index}_first_elem", value)
                html.close_tbody()

            html.close_table()

        elif self._style == ListOf.Style.FLOATING:
            html.open_div(
                id_="%s_prototype" % varprefix,
                class_="vlof_prototype",
                style="display:none;",
            )

            self._show_entry(varprefix, index, value)

            html.close_div()

        else:
            raise NotImplementedError()

    def _show_current_entries(self, varprefix: str, value: ListOfModel[T]) -> None:
        if self._style == ListOf.Style.REGULAR:
            html.open_table(class_=["valuespec_listof"])
            html.open_tbody(id_="%s_container" % varprefix)

            for nr, v in enumerate(value):
                self._show_entry(varprefix, "%d" % (nr + 1), v)

            html.close_tbody()
            html.close_table()

        elif self._style == ListOf.Style.FLOATING:
            html.open_div(
                id_="%s_container" % varprefix,
                class_=["valuespec_listof_floating_container"],
            )

            for nr, v in enumerate(value):
                self._show_entry(varprefix, "%d" % (nr + 1), v)

            html.close_div()

        else:
            raise NotImplementedError()

    def _show_entry(self, varprefix: str, index: str, value: T) -> None:
        entry_id = f"{varprefix}_entry_{index}"

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

    def _show_entry_cell(self, varprefix: str, index: str, value: T) -> None:
        html.open_td(class_="vlof_buttons")

        html.hidden_field(
            varprefix + "_indexof_" + index, "", add_var=True, class_=["index"]
        )  # reconstruct order after moving stuff
        html.hidden_field(
            varprefix + "_orig_indexof_" + index,
            "",
            add_var=True,
            class_=["orig_index"],
        )
        if self._movable:
            html.element_dragger_js(
                "tr",
                drop_handler="cmk.valuespecs.listof_drop_handler",
                handler_args={"cur_index": index, "varprefix": varprefix},
            )
        self._del_button(varprefix, index)
        html.close_td()
        html.open_td(class_="vlof_content")
        if self._first_element_vs is not None and index in {
            "1",
            f"{self._magic}_first_elem",
        }:
            self._first_element_vs.render_input(varprefix + "_" + index, value)
        else:
            self._valuespec.render_input(varprefix + "_" + index, value)
        html.close_td()

    def _del_button(self, vp: str, nr: str) -> None:
        js = f"cmk.valuespecs.listof_delete({json.dumps(vp)}, {json.dumps(nr)})"
        html.icon_button("#", self._del_label, "close", onclick=js, class_=["delete_button"])

    def canonical_value(self) -> ListOfModel[T]:
        return []

    def value_to_html(self, value: ListOfModel[T]) -> ValueSpecText:
        if self._totext:
            if "%d" in self._totext:
                return self._totext % len(value)
            return self._totext
        if not value:
            return self._text_if_empty

        return HTMLWriter.render_table(
            HTML.empty().join(
                HTMLWriter.render_tr(HTMLWriter.render_td(self._valuespec.value_to_html(v)))
                for v in value
            )
        )

    def get_indexes(self, varprefix: str) -> Mapping[int, int]:
        count = request.get_integer_input_mandatory(varprefix + "_count", 0)
        n = 1
        indexes = {}
        while n <= count:
            indexof = request.var(varprefix + "_indexof_%d" % n)
            # for deleted entries, we have removed the whole row, therefore indexof is None
            if indexof:
                indexes[int(indexof)] = n
            n += 1
        return indexes

    def from_html_vars(self, varprefix: str) -> ListOfModel[T]:
        indexes = self.get_indexes(varprefix)
        value = []
        k = sorted(indexes.keys())
        for i in k:
            val = self._valuespec.from_html_vars(varprefix + "_%d" % indexes[i])
            value.append(val)
        return value

    def validate_datatype(self, value: ListOfModel[T], varprefix: str) -> None:
        if not isinstance(value, list):
            raise MKUserError(varprefix, _("The type must be list, but is %s") % type_name(value))
        for n, v in enumerate(value):
            self._valuespec.validate_datatype(v, varprefix + "_%d" % (n + 1))

    def _validate_value(self, value: ListOfModel[T], varprefix: str) -> None:
        if not self._allow_empty and len(value) == 0:
            raise MKUserError(varprefix, self._empty_text)
        for n, v in enumerate(value):
            self._valuespec.validate_value(v, varprefix + "_%d" % (n + 1))

    def has_show_more(self) -> bool:
        return self._valuespec.has_show_more()

    def mask(self, value: ListOfModel[T]) -> ListOfModel[T]:
        return [self._valuespec.mask(e) for e in value]

    def value_to_json(self, value: ListOfModel[T]) -> JSONValue:
        return [self._valuespec.value_to_json(e) for e in value]

    def value_from_json(self, json_value: JSONValue) -> ListOfModel[T]:
        return [self._valuespec.value_from_json(e) for e in json_value]

    def transform_value(self, value: ListOfModel[T]) -> ListOfModel[T]:
        return [self._valuespec.transform_value(v) for v in value]


ListOfMultipleChoices = Sequence[tuple[str, ValueSpec]]


class ListOfMultipleChoiceGroup(NamedTuple):
    title: str
    choices: ListOfMultipleChoices


GroupedListOfMultipleChoices = Sequence[ListOfMultipleChoiceGroup]
ListOfMultipleModel = Mapping[str, Any]


class ListOfMultiple(ValueSpec[ListOfMultipleModel]):
    """A generic valuespec where the user can choose from a list of sub-valuespecs.
    Each sub-valuespec can be added only once
    """

    def __init__(  # pylint: disable=redefined-builtin
        self,
        choices: GroupedListOfMultipleChoices | ListOfMultipleChoices,
        choice_page_name: str,
        page_request_vars: Mapping[str, Any] | None = None,
        size: int | None = None,
        add_label: str | None = None,
        del_label: str | None = None,
        delete_style: str = "default",
        title: str | None = None,
        help: ValueSpecHelp | None = None,
        default_value: ValueSpecDefault[Mapping[str, Any]] = DEF_VALUE,
        validate: ValueSpecValidateFunc[Mapping[str, Any]] | None = None,
        allow_empty: bool = True,
    ):
        super().__init__(title=title, help=help, default_value=default_value, validate=validate)
        # Normalize all to grouped choice structure
        ungrouped_group = ListOfMultipleChoiceGroup(
            title="",
            choices=[c for c in choices if not isinstance(c, ListOfMultipleChoiceGroup)],
        )
        grouped: GroupedListOfMultipleChoices = [ungrouped_group] + [
            e for e in choices if isinstance(e, ListOfMultipleChoiceGroup)
        ]

        self._grouped_choices = grouped
        self._choice_dict = {choice[0]: choice[1] for group in grouped for choice in group.choices}
        self._choice_page_name = choice_page_name
        self._page_request_vars = page_request_vars or {}
        self._size = size
        self._add_label = add_label if add_label is not None else _("Add element")
        self._del_label = del_label if del_label is not None else _("Delete this entry")
        self._delete_style = delete_style  # or "filter"
        self._allow_empty = allow_empty

    def allow_empty(self) -> bool:
        return self._allow_empty

    def del_button(self, varprefix: str, ident: str) -> None:
        js = f"cmk.valuespecs.listofmultiple_del({json.dumps(varprefix)}, {json.dumps(ident)})"
        html.icon_button("#", self._del_label, "close", onclick=js, class_=["delete_button"])

    def render_input(self, varprefix: str, value: ListOfMultipleModel) -> None:
        # Beware: the 'value' is only the default value in case the form
        # has not yet been filled in. In the complain phase we must
        # ignore 'value' but reuse the input from the HTML variables -
        # even if they are not syntactically correct. Calling from_html_vars
        # here is *not* an option since this might not work in case of
        # a wrong user input.

        # Special styling for filters
        extra_css = ["filter"] if self._delete_style == "filter" else []

        # In the 'complain' phase, where the user already saved the
        # form but the validation failed, we must not display the
        # original 'value' but take the value from the HTML variables.
        if request.var("%s_active" % varprefix):
            value = self.from_html_vars(varprefix)

        sorted_idents: list[str] = []
        for group in self._grouped_choices:
            for ident, _vs in group.choices:
                if ident in value and ident in self._choice_dict:
                    sorted_idents.append(ident)

        # Save all selected items
        html.hidden_field(
            "%s_active" % varprefix,
            ";".join(sorted_idents),
            id_="%s_active" % varprefix,
            add_var=True,
        )

        # Actual table of currently existing entries
        html.open_table(id_="%s_table" % varprefix, class_=["valuespec_listof"] + extra_css)
        html.open_tbody()

        for ident in sorted_idents:
            self.show_choice_row(varprefix, ident, value)

        html.close_tbody()
        html.close_table()

        self._show_add_elements(varprefix)

    def _show_add_elements(self, varprefix: str) -> None:
        choices: GroupedChoices = [ChoiceGroup(title="", choices=[("", "")])]
        for group in self._grouped_choices:
            choices.append(
                ChoiceGroup(
                    title=group.title,
                    choices=[(ident, vs.title() or "") for ident, vs in group.choices],
                )
            )

        html.dropdown(
            varprefix + "_choice",
            choices,
            style="width: %dex" % self._size if self._size is not None else None,
            class_=["vlof_filter"] if self._delete_style == "filter" else [],
        )
        html.javascript("cmk.valuespecs.listofmultiple_init(%s);" % json.dumps(varprefix))
        html.jsbutton(
            varprefix + "_add",
            self._add_label,
            "cmk.valuespecs.listofmultiple_add(%s, %s, %s)"
            % (
                json.dumps(varprefix),  #
                json.dumps(self._choice_page_name),
                json.dumps(self._page_request_vars),
            ),
        )

    def show_choice_row(self, varprefix: str, ident: str, value: ListOfMultipleModel) -> None:
        prefix = varprefix + "_" + ident
        html.open_tr(id_="%s_row" % prefix)
        self._show_del_button(varprefix, ident)
        self._show_content(varprefix, ident, value)
        html.close_tr()

    def _show_content(self, varprefix: str, ident: str, value: ListOfMultipleModel) -> None:
        prefix = varprefix + "_" + ident
        html.open_td(class_=["vlof_content"])
        vs = self._choice_dict[ident]
        vs.render_input(prefix, value.get(ident, vs.default_value()))
        html.close_td()

    def _show_del_button(self, varprefix: str, ident: str) -> None:
        html.open_td(class_=["vlof_buttons"])
        self.del_button(varprefix, ident)
        html.close_td()

    def canonical_value(self) -> ListOfMultipleModel:
        return {}

    def mask(self, value: ListOfMultipleModel) -> ListOfMultipleModel:
        return {ident: self._choice_dict[ident].mask(val) for ident, val in value.items()}

    def value_to_html(self, value: ListOfMultipleModel) -> ValueSpecText:
        table_content = HTML.empty()
        for ident, val in value.items():
            vs = self._choice_dict[ident]
            table_content += HTMLWriter.render_tr(
                HTMLWriter.render_td(vs.title()) + HTMLWriter.render_td(vs.value_to_html(val))
            )
        return HTMLWriter.render_table(table_content)

    def value_to_json(self, value: ListOfMultipleModel) -> JSONValue:
        return {ident: self._choice_dict[ident].value_to_json(val) for ident, val in value.items()}

    def value_from_json(self, json_value: JSONValue) -> ListOfMultipleModel:
        return {
            ident: self._choice_dict[ident].value_from_json(val)
            for ident, val in json_value.items()
        }

    def from_html_vars(self, varprefix: str) -> ListOfMultipleModel:
        value: dict[str, Any] = {}
        active = request.get_str_input_mandatory("%s_active" % varprefix, "").strip()
        if not active:
            return value

        for ident in active.split(";"):
            vs = self._choice_dict[ident]
            value[ident] = vs.from_html_vars(varprefix + "_" + ident)
        return value

    def validate_datatype(self, value: ListOfMultipleModel, varprefix: str) -> None:
        if not isinstance(value, dict):
            raise MKUserError(varprefix, _("The type must be dict, but is %s") % type_name(value))
        for ident, val in value.items():
            self._choice_dict[ident].validate_datatype(val, varprefix + "_" + ident)

    def _validate_value(self, value: ListOfMultipleModel, varprefix: str) -> None:
        if not self._allow_empty and not value:
            raise MKUserError(varprefix, _("You must specify at least one element."))
        for ident, val in value.items():
            self._choice_dict[ident].validate_value(val, varprefix + "_" + ident)


class Float(ValueSpec[float]):
    """Same as Integer, but for floating point values"""

    def __init__(  # pylint: disable=redefined-builtin
        self,
        decimal_separator: str = ".",
        allow_int: bool = False,
        # Integer
        size: int | None = None,
        minvalue: float | None = None,
        maxvalue: float | None = None,
        label: str | None = None,
        unit: str = "",
        display_format: str = "%r",
        align: Literal["left", "right"] = "left",
        # ValueSpec
        title: str | None = None,
        help: ValueSpecHelp | None = None,
        default_value: ValueSpecDefault[float] = DEF_VALUE,
        validate: ValueSpecValidateFunc[float] | None = None,
    ):
        super().__init__(
            title=title,
            label=label,
            help=help,
            default_value=default_value,
            validate=validate,
        )
        self._bounds = Bounds[float](minvalue, maxvalue)
        self._renderer = NumericRenderer(
            size=size,
            maxvalue=maxvalue,
            label=label,
            unit=unit,
            align=align,
        )
        self._display_format = display_format
        self._decimal_separator = decimal_separator
        self._allow_int = allow_int

    def canonical_value(self) -> float:
        return self._bounds.lower(0.0)

    def render_input(self, varprefix: str, value: float) -> None:
        self._renderer.render_input(varprefix, self._render_value(value))

    def _render_value(self, value: float) -> str:
        return self._display_format % utils.savefloat(value)

    def from_html_vars(self, varprefix: str) -> float:
        return request.get_float_input_mandatory(varprefix)

    def mask(self, value: float) -> float:
        return value

    def value_to_html(self, value: float) -> ValueSpecText:
        txt = self._renderer.format_text(self._render_value(value))
        return txt.replace(".", self._decimal_separator)

    def value_to_json(self, value: float) -> JSONValue:
        return value

    def value_from_json(self, json_value: JSONValue) -> float:
        return json_value

    def validate_datatype(self, value: float, varprefix: str) -> None:
        if isinstance(value, float):
            return
        if isinstance(value, numbers.Integral) and self._allow_int:
            return
        raise MKUserError(
            varprefix,
            _("The value %r has type %s, but must be of type float%s")
            % (value, type_name(value), _(" or int") if self._allow_int else ""),
        )

    def _validate_value(self, value: float, varprefix: str) -> None:
        self._bounds.validate_value(value, varprefix)


class Percentage(Float):
    def __init__(  # pylint: disable=redefined-builtin
        self,
        # Float
        decimal_separator: str = ".",
        allow_int: bool = False,
        # Integer
        size: int | None = None,
        minvalue: None | int | float = 0.0,
        maxvalue: None | int | float = 101.0,
        label: str | None = None,
        unit: str = "%",
        display_format: str = "%r",
        align: Literal["left", "right"] = "left",
        # ValueSpec
        title: str | None = None,
        help: ValueSpecHelp | None = None,
        default_value: ValueSpecDefault[float] = DEF_VALUE,
        validate: ValueSpecValidateFunc[float] | None = None,
    ):
        super().__init__(
            decimal_separator=decimal_separator,
            allow_int=allow_int,
            size=size,
            minvalue=minvalue,
            maxvalue=maxvalue,
            label=label,
            unit=unit,
            display_format=display_format,
            align=align,
            title=title,
            help=help,
            default_value=default_value,
            validate=validate,
        )

    def value_to_html(self, value: float) -> ValueSpecText:
        return (self._display_format + "%%") % value

    def validate_datatype(self, value: float, varprefix: str) -> None:
        if self._allow_int:
            if not isinstance(value, (int, float)):
                raise MKUserError(
                    varprefix,
                    _("The value %r has type %s, but must be either float or int")
                    % (value, type_name(value)),
                )
        else:
            super().validate_datatype(value, varprefix)


class Checkbox(ValueSpec[bool]):
    def __init__(  # pylint: disable=redefined-builtin
        self,
        label: str | None = None,
        true_label: str | None = None,
        false_label: str | None = None,
        onclick: str | None = None,
        # ValueSpec
        title: str | None = None,
        help: ValueSpecHelp | None = None,
        default_value: ValueSpecDefault[bool] = DEF_VALUE,
        validate: ValueSpecValidateFunc[bool] | None = None,
    ):
        super().__init__(
            title=title,
            label=label,
            help=help,
            default_value=default_value,
            validate=validate,
        )
        self._label = label
        self._true_label = true_label if true_label is not None else _("on")
        self._false_label = false_label if false_label is not None else _("off")
        self._onclick = onclick

    def canonical_value(self) -> bool:
        return False

    def render_input(self, varprefix: str, value: bool) -> None:
        html.checkbox(varprefix, value, label=self._label, onclick=self._onclick)

    def mask(self, value: bool) -> bool:
        return value

    def value_to_html(self, value: bool) -> ValueSpecText:
        return self._true_label if value else self._false_label

    def value_to_json(self, value: bool) -> JSONValue:
        return value

    def value_from_json(self, json_value: JSONValue) -> bool:
        return json_value

    def from_html_vars(self, varprefix: str) -> bool:
        return bool(request.var(varprefix))

    def validate_datatype(self, value: bool, varprefix: str) -> None:
        if not isinstance(value, bool):
            raise MKUserError(
                varprefix,
                _("The value %r has type %s, but must be of type bool") % (value, type_name(value)),
            )


DropdownChoiceEntry = tuple[T, str]
DropdownChoiceEntries = Sequence[DropdownChoiceEntry]
DropdownChoices = Promise[DropdownChoiceEntries]
DropdownInvalidChoice = Literal[None, "complain", "replace"]


class DropdownChoice(ValueSpec[T | None]):
    """A type-safe dropdown choice

    Parameters:
    help_separator: if you set this to a character, e.g. "-", then
    value_to_html will omit texts from the character up to the end of
    a choices name.
    choices may also be a function that returns - when called
    without arguments - such a tuple list. That way the choices
    can by dynamically computed"""

    # TODO: Cleanup redefined builtin sorted
    def __init__(  # pylint: disable=redefined-builtin
        self,
        # DropdownChoice
        choices: DropdownChoices,
        sorted: bool = False,
        label: str | None = None,
        help_separator: str | None = None,
        prefix_values: bool = False,
        empty_text: str | None = None,
        invalid_choice: DropdownInvalidChoice = "complain",
        invalid_choice_title: str | None = None,
        invalid_choice_error: str | None = None,
        no_preselect_title: str | None = None,
        on_change: str | None = None,
        read_only: bool = False,
        encode_value: bool = True,
        html_attrs: HTMLTagAttributes | None = None,
        deprecated_choices: Sequence[Any] = (),
        # ValueSpec
        title: str | None = None,
        help: ValueSpecHelp | None = None,
        default_value: ValueSpecDefault[T] = DEF_VALUE,
        validate: ValueSpecValidateFunc[T | None] | None = None,
        default: ValueSpecDefault[T] | None = None,  # CMK-12228
    ):
        super().__init__(
            title=title,
            label=label,
            help=help,
            default_value=default or default_value,
            validate=validate,
        )
        self._choices = choices
        self._help_separator = help_separator
        self._label = label
        self._prefix_values = prefix_values
        self._sorted = sorted
        self._empty_text = (
            empty_text
            if empty_text is not None
            else _("There are no elements defined for this selection yet.")
        )
        self._invalid_choice = invalid_choice
        self._invalid_choice_title = (
            invalid_choice_title
            if invalid_choice_title is not None
            else _("Element %r does not exist anymore")
        )
        self._invalid_choice_error = (
            invalid_choice_error
            if invalid_choice_error is not None
            else _("The selected element %r is not longer available. Please select something else.")
        )
        self._no_preselect_title = no_preselect_title
        self._on_change = on_change
        self._read_only = read_only
        self._encode_value = encode_value
        self._deprecated_choices = deprecated_choices
        self._html_attrs: HTMLTagAttributes = {} if html_attrs is None else html_attrs

    def allow_empty(self) -> bool:
        return self._read_only or self._no_preselect_title is None

    def choices(self) -> DropdownChoiceEntries:
        result = self._choices() if callable(self._choices) else self._choices
        pre = [] if self._no_preselect_title is None else [(None, self._no_preselect_title)]
        return pre + list(result)

    def canonical_value(self) -> T | None:
        choices = self.choices()
        if len(choices) > 0:
            return choices[0][0]
        return None

    def render_input(self, varprefix: str, value: T | None) -> None:
        if self._label:
            html.span(self._label, class_="vs_floating_text")

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
        if (
            self._invalid_choice == "complain"
            and value is not None
            and self._value_is_invalid(value)
        ):
            defval = value
            options.append(
                (
                    defval,
                    self._get_invalid_choice_text(self._invalid_choice_title, value),
                )
            )

        if value is None and not options:
            html.write_text_permissive(self._empty_text)
            return

        if len(options) == 0:
            html.write_text_permissive(self._empty_text)
            return

        html.dropdown(
            varprefix,
            self._options_for_html(options),
            deflt=self._option_for_html(defval),
            locked_choice=None,
            onchange=self._on_change,
            ordered=self._sorted,
            label=None,
            class_=[],
            size=1,
            multiple=False,
            read_only=self._read_only,
            **self._html_attrs,
        )

    def validate_datatype(self, value: T | None, varprefix: str) -> None:
        if (
            any(isinstance(value, type(choice[0])) for choice in self.choices())
            or value in self._deprecated_choices
        ):
            return
        raise MKUserError(
            varprefix,
            _("The value %r has type %s, but does not match any of the available choice types.")
            % (value, type_name(value)),
        )

    def _get_invalid_choice_text(self, tmpl: str, value: object) -> str:
        return tmpl % (value,) if "%s" in tmpl or "%r" in tmpl else tmpl

    def mask(self, value: T | None) -> T | None:
        return value

    def value_to_html(self, value: T | None) -> ValueSpecText:
        for val, title in self.choices():
            if value == val:
                if self._help_separator:
                    return title.split(self._help_separator, 1)[0].strip()
                return title
        return self._get_invalid_choice_text(self._invalid_choice_title, value)

    def value_to_json(self, value: T | None) -> JSONValue:
        return value

    def value_from_json(self, json_value: JSONValue) -> T | None:
        return json_value

    def from_html_vars(self, varprefix: str) -> T | None:
        choices = self.choices()

        for val, _title in choices:
            if self._is_selected_option_from_html(varprefix, val):
                return val

        if self._invalid_choice == "replace":
            return self.default_value()  # garbled URL or len(choices) == 0
        if not choices:
            raise MKUserError(varprefix, self._empty_text)
        raise MKUserError(
            varprefix,
            self._get_invalid_choice_text(self._invalid_choice_error, request.var(varprefix)),
        )

    def _is_selected_option_from_html(self, varprefix: str, val: T) -> bool:
        selected_value = request.var(varprefix)
        return selected_value == self._option_for_html(val)

    def _option_for_html(self, value: T | None) -> ChoiceId:
        if self._encode_value:
            return self.option_id(value)
        if value is not None and not isinstance(value, str):
            raise TypeError(
                f"Can not create option for html of value {value} type {type(value)}, "
                "expected str. Use encode_value=True"
            )
        return value

    def _options_for_html(self, orig_options: DropdownChoiceEntries) -> Choices:
        return [(self._option_for_html(val), title) for val, title in orig_options]

    @staticmethod
    def option_id(val: object) -> str:
        return "%s" % hashlib.sha256(repr(val).encode()).hexdigest()

    def _validate_value(self, value: T | None, varprefix: str) -> None:
        if self._no_preselect_title is not None and value is None:
            raise MKUserError(varprefix, _("Please make a selection"))

        if self._invalid_choice == "complain" and self._value_is_invalid(value):
            if value is not None:
                raise MKUserError(
                    varprefix,
                    self._get_invalid_choice_text(self._invalid_choice_error, value),
                )
            raise MKUserError(varprefix, self._empty_text)

    def _value_is_invalid(self, value: T | None) -> bool:
        return all(value != val for val, _title in self.choices())


class AjaxDropdownChoice(DropdownChoice[str]):
    # This valuespec is a coodinate effort between the python
    # renderer. A JS component for the ajax query and the AJAX
    # python endpoint. You're responsible of putting them together.
    # for new autocompleters.
    ident = ""
    # TODO: completely remove ident from this class! should only be defined in autocompleter!

    def __init__(  # pylint: disable=redefined-builtin
        self,
        regex: None | str | Pattern[str] = None,
        regex_error: str | None = None,
        # TODO: remove this one, replace with autocompleter!
        strict: Literal["True", "False"] = "False",
        # TODO: rename to autocompleter_config!
        autocompleter: AutocompleterConfig | None = None,
        cssclass: str | None = None,
        # DropdownChoice
        label: str | None = None,
        html_attrs: HTMLTagAttributes | None = None,
        on_change: str | None = None,
        # From ValueSpec
        title: str | None = None,
        help: ValueSpecHelp | None = None,
        default_value: ValueSpecDefault[str] = DEF_VALUE,
        validate: ValueSpecValidateFunc[str | None] | None = None,
    ):
        super().__init__(
            label=label,
            choices=[],
            encode_value=False,  # because JS picks & passes the values on same page
            on_change=on_change,
            title=title,
            help=help,
            default_value=default_value,
            validate=validate,
            html_attrs=html_attrs,
        )

        if autocompleter is None:
            # TODO: remove this!
            self._autocompleter = AutocompleterConfig(
                ident=self.ident,
                strict=(strict == "True"),
            )
        else:
            self._autocompleter = autocompleter

        if isinstance(regex, str):
            self._regex: Pattern[str] | None = re.compile(regex)
        else:
            self._regex = regex
        self._regex_error = (
            regex_error
            if regex_error is not None
            else _("Your input does not match the required format.")
        )
        self._cssclass = cssclass

    def from_html_vars(self, varprefix: str) -> str:
        return request.get_str_input_mandatory(varprefix, "")

    def validate_datatype(self, value: str | None, varprefix: str) -> None:
        if not isinstance(value, str):
            raise MKUserError(
                varprefix,
                _("The value must be of type str, but it has type %s") % type_name(value),
            )

    def _validate_value(self, value: str | None, varprefix: str) -> None:
        if value and self._regex and not self._regex.match(value):
            raise MKUserError(varprefix, self._regex_error)

    def value_to_html(self, value: str | None) -> ValueSpecText:
        return super().value_to_html(value) if self.choices() else str(value)

    def render_input(self, varprefix: str, value: str | None) -> None:
        if self._label:
            html.write_text_permissive(self._label)

        clean_choices = [(value, value)] if value else self.choices()

        html.dropdown(
            varprefix,
            self._options_for_html(clean_choices),
            deflt=self._option_for_html(value),
            locked_choice=None,
            onchange=self._on_change,
            ordered=self._sorted,
            label=None,
            class_=["ajax-vals", self._cssclass if self._cssclass else ""],
            data_autocompleter=json.dumps(self._autocompleter.config),
            size=1,
            multiple=False,
            read_only=self._read_only,
            # kwargs following
            style="width: 250px;",
            **self._html_attrs,
        )


# TODO: check where this class is used with strict=False.
# Create a separate class (MonitoredHostnameFreeInput?) for this usecase,
# otherwise use a normal AjaxDropdownChoice with the correct ident.
# grep for 'should be Valuespec.str.' to find typeignores that can be replaced
# after fixins that.
class MonitoredHostname(AjaxDropdownChoice):
    """Hostname input with dropdown completion

    Renders an input field for entering a host name while providing an auto completion dropdown field.
    Fetching the choices from the current live config via livestatus"""

    ident = "monitored_hostname"

    def __init__(  # pylint: disable=redefined-builtin
        self,
        strict: Literal["True", "False"] = "False",
        # DropdownChoice
        autocompleter: AutocompleterConfig | None = None,
        label: str | None = None,
        html_attrs: HTMLTagAttributes | None = None,
        # From ValueSpec
        title: str | None = None,
        help: ValueSpecHelp | None = None,
        default_value: ValueSpecDefault[str] = DEF_VALUE,
        validate: ValueSpecValidateFunc[str | None] | None = None,
    ):
        super().__init__(
            strict=strict,
            autocompleter=autocompleter,
            label=label,
            html_attrs=html_attrs,
            title=title,
            help=help,
            default_value=default_value,
            validate=_validate_hostname if validate is None else validate,
        )

    def value_to_html(self, value: str | None) -> ValueSpecText:
        if value is None:
            return ""
        return value


class MonitoredServiceDescription(AjaxDropdownChoice):
    """Unfiltered Service Descriptions for input with dropdown completion

    Renders an input field for entering a service name while providing an auto completion dropdown field.
    Fetching the choices from the current live config via livestatus"""

    ident = "monitored_service_description"


class DropdownChoiceWithHostAndServiceHints(AjaxDropdownChoice):
    def __init__(  # pylint: disable=redefined-builtin
        self,
        css_spec: Sequence[str],
        hint_label: str,
        # AjaxDropdownChoice
        regex: None | str | Pattern[str] = None,
        regex_error: str | None = None,
        # DropdownChoice
        label: str | None = None,
        html_attrs: HTMLTagAttributes | None = None,
        autocompleter: AutocompleterConfig | None = None,
        # From ValueSpec
        title: str | None = None,
        help: ValueSpecHelp | None = None,
        default_value: ValueSpecDefault[str] = DEF_VALUE,
        validate: ValueSpecValidateFunc[str | None] | None = None,
    ):
        if autocompleter is None:
            autocompleter = AutocompleterConfig(
                ident=self.ident,
                strict=True,
                dynamic_params_callback_name="host_and_service_hinted_autocompleter",
            )
        super().__init__(
            regex=regex,
            regex_error=regex_error,
            label=label,
            html_attrs=html_attrs,
            autocompleter=autocompleter,
            title=title,
            help=help,
            default_value=default_value,
            validate=validate,
        )
        self._css_spec = css_spec
        self._hint_label = hint_label

    def _choices_from_value(self, value: str | None) -> Choices:
        raise NotImplementedError()

    def render_input(self, varprefix: str, value: str | None) -> None:
        if self._label:
            html.span(self._label, class_="vs_floating_text")

        html.dropdown(
            varprefix,
            self._options_for_html(self._choices_from_value(value)),
            deflt=self._option_for_html(value),
            class_=list(self._css_spec),  # TODO: Fix dropdown's signature!
            style="width: 250px;",
            data_autocompleter=json.dumps(self._autocompleter.config),
            read_only=self._read_only,
        )

        vs_host = MonitoredHostname(
            label=_("Filter %s selection by host name: ") % self._hint_label,
            strict="True",
        )
        html.br()
        vs_host.render_input(varprefix + "_hostname_hint", "")

        vs_service = MonitoredServiceDescription(
            autocompleter=ContextAutocompleterConfig(
                ident=MonitoredServiceDescription.ident,
                show_independent_of_context=True,
                strict=True,
                dynamic_params_callback_name="host_hinted_autocompleter",
            ),
            label=_("Filter %s selection by service: ") % self._hint_label,
        )
        html.br()
        vs_service.render_input(varprefix + "_service_hint", "")


MonitoringStateValue = Literal[0, 1, 2, 3]


# TODO: Rename to ServiceState() or something like this
def MonitoringState(  # pylint: disable=redefined-builtin
    # DropdownChoice
    sorted: bool = False,
    label: str | None = None,
    help_separator: str | None = None,
    prefix_values: bool = False,
    empty_text: str | None = None,
    invalid_choice: DropdownInvalidChoice = "complain",
    invalid_choice_title: str | None = None,
    invalid_choice_error: str | None = None,
    no_preselect_title: str | None = None,
    on_change: str | None = None,
    read_only: bool = False,
    encode_value: bool = True,
    html_attrs: HTMLTagAttributes | None = None,
    # ValueSpec
    title: str | None = None,
    help: ValueSpecHelp | None = None,
    default_value: ValueSpecDefault[int] = 0,  # NOTE: Different!
    validate: ValueSpecValidateFunc[int | None] | None = None,
    deprecated_choices: Sequence[int] = (),
) -> DropdownChoice[int]:
    """Special convenience variant for monitoring states"""
    return DropdownChoice[int](
        choices=[
            (0, _("OK")),
            (1, _("WARN")),
            (2, _("CRIT")),
            (3, _("UNKNOWN")),
        ],
        sorted=sorted,
        label=label,
        help_separator=help_separator,
        prefix_values=prefix_values,
        empty_text=empty_text,
        invalid_choice=invalid_choice,
        invalid_choice_title=invalid_choice_title,
        invalid_choice_error=invalid_choice_error,
        no_preselect_title=no_preselect_title,
        on_change=on_change,
        read_only=read_only,
        encode_value=encode_value,
        html_attrs=html_attrs,
        title=title,
        help=help,
        default_value=default_value,
        validate=validate,
        deprecated_choices=deprecated_choices,
    )


HostStateValue = Literal[0, 1, 2]


class HostState(DropdownChoice):
    def __init__(  # pylint: disable=redefined-builtin
        self,
        # DropdownChoice
        sorted: bool = False,
        label: str | None = None,
        help_separator: str | None = None,
        prefix_values: bool = False,
        empty_text: str | None = None,
        invalid_choice: DropdownInvalidChoice = "complain",
        invalid_choice_title: str | None = None,
        invalid_choice_error: str | None = None,
        no_preselect_title: str | None = None,
        on_change: str | None = None,
        read_only: bool = False,
        encode_value: bool = True,
        html_attrs: HTMLTagAttributes | None = None,
        # ValueSpec
        title: str | None = None,
        help: ValueSpecHelp | None = None,
        default_value: ValueSpecDefault[int] = 0,  # NOTE: Different!
        validate: ValueSpecValidateFunc[int | None] | None = None,
        deprecated_choices: Sequence[int] = (),
    ):
        super().__init__(
            choices=[
                (0, _("UP")),
                (1, _("DOWN")),
                (2, _("UNREACHABLE")),
            ],
            sorted=sorted,
            label=label,
            help_separator=help_separator,
            prefix_values=prefix_values,
            empty_text=empty_text,
            invalid_choice=invalid_choice,
            invalid_choice_title=invalid_choice_title,
            invalid_choice_error=invalid_choice_error,
            no_preselect_title=no_preselect_title,
            on_change=on_change,
            read_only=read_only,
            encode_value=encode_value,
            html_attrs=html_attrs,
            title=title,
            help=help,
            default_value=default_value,
            validate=validate,
            deprecated_choices=deprecated_choices,
        )


CascadingDropdownChoiceIdent = None | str | bool | int
CascadingDropdownChoiceValue = (
    CascadingDropdownChoiceIdent | tuple[CascadingDropdownChoiceIdent, Any]
)
CascadingDropdownCleanChoice = tuple[CascadingDropdownChoiceIdent, str, None | ValueSpec]
CascadingDropdownShortChoice = tuple[CascadingDropdownChoiceIdent, str]
CascadingDropdownChoice = CascadingDropdownShortChoice | CascadingDropdownCleanChoice
CascadingDropdownChoices = Promise[Sequence[CascadingDropdownChoice]]


class CascadingDropdownChoiceWithoutValue(NamedTuple):
    ident: CascadingDropdownChoiceIdent
    title: str
    index_: int


class CascadingDropdownChoiceWithValue(NamedTuple):
    ident: CascadingDropdownChoiceIdent
    title: str
    vs: ValueSpec
    value: CascadingDropdownChoiceValue  # this is bound to vs
    index_: int


def _normalize_choices(
    choices: Sequence[CascadingDropdownChoice],
) -> Sequence[CascadingDropdownCleanChoice]:
    return [(c[0], c[1], _sub_valuespec(c)) for c in choices]


def _sub_valuespec(choice: CascadingDropdownChoice) -> ValueSpec | None:
    if len(choice) == 2:
        return None
    if len(choice) == 3:
        # NOTE: mypy is too dumb to figure out tuple lengths, so we use the funny "+ 0" below. Fragile...
        vs = choice[2 + 0]
        if vs is None or isinstance(vs, ValueSpec):
            return vs
    raise Exception(f"invalid CascadingDropdownChoice {choice!r}")


class CascadingDropdown(ValueSpec[CascadingDropdownChoiceValue]):
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
        choices: CascadingDropdownChoices,
        label: str | None = None,
        separator: str = ", ",
        sorted: bool = True,
        orientation: Literal["vertical", "horizontal"] = "vertical",
        # https://github.com/python/cpython/issues/90015
        render: "CascadingDropdown.Render | None" = None,
        no_elements_text: str | None = None,
        no_preselect_title: str | None = None,
        render_sub_vs_page_name: str | None = None,
        render_sub_vs_request_vars: dict | None = None,
        # ValueSpec
        title: str | None = None,
        help: ValueSpecHelp | None = None,
        default_value: ValueSpecDefault[CascadingDropdownChoiceValue] = DEF_VALUE,
        validate: ValueSpecValidateFunc[CascadingDropdownChoiceValue] | None = None,
        show_title_of_choices: bool = False,
    ):
        super().__init__(
            title=title,
            label=label,
            help=help,
            default_value=default_value,
            validate=validate,
        )

        if callable(choices):
            self._choices = lambda: _normalize_choices(choices())
        else:
            normalized = _normalize_choices(choices)
            self._choices = lambda: normalized

        self._label = label
        self._separator = separator
        self._sorted = sorted
        self._orientation = orientation  # or horizontal
        self._render = render if render is not None else CascadingDropdown.Render.normal

        self._no_elements_text = (
            no_elements_text
            if no_elements_text is not None
            else _("There are no elements defined for this selection")
        )

        self._no_preselect_title = no_preselect_title
        self._preselected = (
            []
            if self._no_preselect_title is None
            else _normalize_choices([(None, self._no_preselect_title)])
        )

        # When given, this ajax page is called to render the input fields of a cascaded valuespec
        # once the user selected this choice in case it was initially hidden.
        self._render_sub_vs_page_name = render_sub_vs_page_name
        self._render_sub_vs_request_vars = render_sub_vs_request_vars or {}
        self._show_title_of_choices = show_title_of_choices

    def allow_empty(self) -> bool:
        return self._no_preselect_title is None

    def choices(self) -> Sequence[CascadingDropdownCleanChoice]:
        return list(itertools.chain(self._preselected, self._choices()))

    def canonical_value(self) -> CascadingDropdownChoiceValue:
        return self._result_from_fallback_choice("canonical_value")

    def default_value(self) -> CascadingDropdownChoiceValue:
        if isinstance(self._default_value, Sentinel):
            return self._result_from_fallback_choice("default_value")
        return super().default_value()

    def _result_from_fallback_choice(
        self,
        value: Literal["default_value", "canonical_value"],
    ) -> CascadingDropdownChoiceValue:
        result = self._fallback_choice()
        if isinstance(result, tuple):
            if value == "default_value":
                return result[0], result[1].default_value()
            return result[0], result[1].canonical_value()
        return result

    def _fallback_choice(
        self,
    ) -> CascadingDropdownChoiceValue:
        choices = self.choices()
        if not choices:
            return None

        value, _, vs = choices[0]
        if vs is None:
            return value

        return value, vs

    def render_input(  # pylint: disable=too-many-branches
        self,
        varprefix: str,
        value: CascadingDropdownChoiceValue,
    ) -> None:
        def_val = "0"
        options: Choices = []
        choices = self.choices()
        if not choices:
            html.write_text_permissive(self._no_elements_text)
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
        onchange = "cmk.valuespecs.cascading_change(this, '%s', %d);" % (
            varprefix,
            len(choices),
        )
        if self._label:
            html.span(self._label, class_="vs_floating_text")
        html.dropdown(vp, options, deflt=def_val, onchange=onchange, ordered=self._sorted)

        # make sure, that the visibility is done correctly, in both
        # cases:
        # 1. Form painted for the first time (no submission yet, vp missing in URL)
        # 2. Form already submitted -> honor URL variable vp for visibility
        cur_val = request.var(vp)

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

            elif nr == int(def_val):
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

    def show_sub_valuespec(self, varprefix: str, vs: ValueSpec, value: Any) -> None:
        html.help(vs.help())
        if self._show_title_of_choices and (title_of_choice := vs.title()):
            html.p(title_of_choice)
        vs.render_input(varprefix, value)

    def _show_sub_valuespec_container(
        self, varprefix: str, choice_id: CascadingDropdownChoiceIdent, value: Any
    ) -> None:
        html.span("", id_="%s_sub" % varprefix)

        request_vars = {
            "varprefix": varprefix,
            "choice_id": repr(choice_id),
            "encoded_value": repr(value),
        }
        request_vars.update(self._render_sub_vs_request_vars)

        html.javascript(
            "cmk.valuespecs.add_cascading_sub_valuespec_parameters(%s, %s);"
            % (
                json.dumps(varprefix),
                json.dumps(
                    {
                        "page_name": self._render_sub_vs_page_name,
                        "request_vars": request_vars,
                    }
                ),
            )
        )

    def _choice_from_value_raise(self, message: str, varprefix: str | None) -> Exception:
        if varprefix is not None:
            return MKUserError(varprefix, message)
        return ValueError(message)

    def _choice_from_value(
        self,
        value: CascadingDropdownChoiceValue,
        varprefix: str | None = None,
    ) -> CascadingDropdownChoiceWithoutValue | CascadingDropdownChoiceWithValue:
        if isinstance(value, tuple):
            if len(value) != 2:
                raise self._choice_from_value_raise(
                    _("If value is a tuple it has to have length of two."), varprefix
                )
            ident, value = value
        else:
            ident, value = (value, None)

        try:
            index, result = next(
                (index, elem) for index, elem in enumerate(self.choices()) if elem[0] == ident
            )
        except StopIteration:
            raise self._choice_from_value_raise(
                _("Could not find an entry matching %r in choices") % (ident,),
                varprefix,
            )
        ident, title, vs = result
        if vs is not None:
            return CascadingDropdownChoiceWithValue(ident, title, vs, value, index)
        return CascadingDropdownChoiceWithoutValue(ident, title, index)

    def value_to_html(self, value: CascadingDropdownChoiceValue) -> ValueSpecText:
        choice = self._choice_from_value(value)
        if isinstance(choice, CascadingDropdownChoiceWithoutValue):
            return choice.title

        rendered_value = choice.vs.value_to_html(choice.value)
        if not rendered_value:
            return choice.title

        if self._render == CascadingDropdown.Render.foldable:
            with (
                output_funnel.plugged(),
                foldable_container(
                    treename="foldable_cascading_dropdown",
                    id_=hashlib.sha256(repr(value).encode()).hexdigest(),
                    isopen=False,
                    title=choice.title,
                    indent=False,
                ),
            ):
                html.write_text_permissive(rendered_value)
            return HTML.without_escaping(output_funnel.drain())

        return (
            HTML.without_escaping(escaping.escape_text(choice.title))
            + HTML.without_escaping(escaping.escape_text(self._separator))
            + rendered_value
        )

    def value_to_json(self, value: CascadingDropdownChoiceValue) -> JSONValue:
        choice = self._choice_from_value(value)
        if isinstance(choice, CascadingDropdownChoiceWithoutValue):
            return choice.ident
        return [choice.ident, choice.vs.value_to_json(choice.value)]

    def value_from_json(self, json_value: JSONValue) -> CascadingDropdownChoiceValue:
        if isinstance(json_value, list):
            value: CascadingDropdownChoiceValue = (json_value[0], json_value[1])
            choice = self._choice_from_value(value)
            # we already know this will be with value, because we explicitly passed a value one line above
            if not isinstance(choice, CascadingDropdownChoiceWithValue):
                raise TypeError(choice)
            value = choice.vs.value_from_json(choice.value)
            return (choice.ident, value)
        # no value, just a ident:
        return json_value

    def mask(self, value: CascadingDropdownChoiceValue) -> CascadingDropdownChoiceValue:
        choice = self._choice_from_value(value)
        if isinstance(choice, CascadingDropdownChoiceWithoutValue):
            return choice.ident
        return choice.ident, choice.vs.mask(choice.value)

    def from_html_vars(self, varprefix: str) -> CascadingDropdownChoiceValue:
        choices = self.choices()

        # No choices and "no elements text" is shown: The html var is
        # not present and no choice can be made. So fallback to default
        # value and let the validation methods lead to an error message.
        if not choices:
            return self.default_value()

        sel = request.get_integer_input_mandatory(varprefix + "_sel", 0)
        value, _, vs = choices[sel]
        if vs is None:
            return value
        return value, vs.from_html_vars(varprefix + "_%d" % sel)

    def validate_datatype(self, value: CascadingDropdownChoiceValue, varprefix: str) -> None:
        choice = self._choice_from_value(value, varprefix)
        if isinstance(choice, CascadingDropdownChoiceWithoutValue):
            return
        choice.vs.validate_datatype(choice.value, varprefix + "_%d" % choice.index_)

    def _validate_value(self, value: CascadingDropdownChoiceValue, varprefix: str) -> None:
        if self._no_preselect_title is not None and value is None:
            raise MKUserError(varprefix + "_sel", _("Please make a selection"))

        choices = self.choices()
        for nr, (val, _title, vs) in enumerate(choices):
            if value == val or (isinstance(value, tuple) and value[0] == val):
                if vs:
                    if not isinstance(value, tuple):
                        raise TypeError(value)
                    vs.validate_value(value[1], varprefix + "_%d" % nr)
                return
        raise MKUserError(varprefix + "_sel", _("Value %r is not allowed here.") % (value,))

    def transform_value(self, value: CascadingDropdownChoiceValue) -> CascadingDropdownChoiceValue:
        choice = self._choice_from_value(value)
        if isinstance(choice, CascadingDropdownChoiceWithoutValue):
            return choice.ident
        return (choice.ident, choice.vs.transform_value(choice.value))

    def has_show_more(self) -> bool:
        return any(vs.has_show_more() for _name, _title, vs in self.choices() if vs is not None)


# TODO: Can we clean up the int type here?
ListChoiceChoiceIdent = str | int
ListChoiceChoice = tuple[ListChoiceChoiceIdent, str]
ListChoiceChoices = None | Promise[Sequence[ListChoiceChoice]] | Mapping[ListChoiceChoiceIdent, str]
ListChoiceModel = Sequence[ListChoiceChoiceIdent]


class ListChoice(ValueSpec[ListChoiceModel]):
    """A list of checkboxes representing a list of values"""

    @staticmethod
    def dict_choices(
        choices: Mapping[ListChoiceChoiceIdent, str],
    ) -> Sequence[tuple[str, str]]:
        return [
            (str(type_id), f"{type_id} - {type_name}")
            for (type_id, type_name) in sorted(choices.items())
        ]

    def __init__(  # pylint: disable=redefined-builtin
        self,
        # ListChoice
        # TODO: This None works together with get_elements which are implemented in the specific sub
        # classes. This should beter be cleaned up to work like other valuespecs, e.g.
        # CascadingDropdown where you can hand over a generator that creates choices dynamically.
        choices: ListChoiceChoices = None,
        columns: int = 1,
        allow_empty: bool = True,
        empty_text: str | None = None,
        render_function: Callable[[ListChoiceChoiceIdent, str], str] | None = None,
        toggle_all: bool = False,
        # TODO: Rename to "orientation" to be in line with other valuespecs
        render_orientation: Literal["horizontal", "vertical"] = "horizontal",
        no_elements_text: str | None = None,
        # ValueSpec
        title: str | None = None,
        help: ValueSpecHelp | None = None,
        default_value: ValueSpecDefault[ListChoiceModel] = DEF_VALUE,
        validate: ValueSpecValidateFunc[ListChoiceModel] | None = None,
    ):
        super().__init__(title=title, help=help, default_value=default_value, validate=validate)
        self._choices = choices
        self._columns = columns
        self._allow_empty = allow_empty
        self._empty_text = empty_text if empty_text is not None else _("(nothing selected)")
        self._loaded_at: int | None = None
        self._render_function = (
            render_function if render_function is not None else (lambda id, val: val)
        )
        self._toggle_all = toggle_all
        self._render_orientation = render_orientation
        self._no_elements_text = (
            no_elements_text
            if no_elements_text is not None
            else _("There are no elements defined for this selection")
        )
        self._elements: Sequence[ListChoiceChoice] = []

    def allow_empty(self) -> bool:
        return self._allow_empty

    # In case of overloaded functions with dynamic elements
    def load_elements(self) -> None:
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

    def get_elements(self) -> Sequence[ListChoiceChoice]:
        raise NotImplementedError()

    def canonical_value(self) -> ListChoiceModel:
        return []

    def _draw_listchoice(self, varprefix: str, value: ListChoiceModel) -> None:
        if self._toggle_all:
            html.a(
                _("Check / Uncheck all"),
                href="javascript:cmk.valuespecs.list_choice_toggle_all('%s')" % varprefix,
            )
        html.open_table(id_="%s_tbl" % varprefix, class_=["listchoice"])
        for nr, (key, title) in enumerate(self._elements):
            if nr % self._columns == 0:
                if nr > 0:
                    html.close_tr()
                html.open_tr()
            html.open_td()
            html.checkbox("%s_%d" % (varprefix, nr), key in value, label=title)
            html.close_td()
        html.close_tr()
        html.close_table()

    def render_input(self, varprefix: str, value: ListChoiceModel) -> None:
        self.load_elements()
        if not self._elements:
            html.write_text_permissive(self._no_elements_text)
            return

        self._draw_listchoice(varprefix, value)

        # Make sure that at least one variable with the prefix is present
        html.hidden_field(varprefix, "1", add_var=True)

    def mask(self, value: ListChoiceModel) -> ListChoiceModel:
        return value

    def value_to_html(self, value: ListChoiceModel) -> ValueSpecText:
        if not value:
            return self._empty_text

        self.load_elements()
        d = dict(self._elements)
        texts = [self._render_function(v, d.get(v, str(v))) for v in value]
        if self._render_orientation == "horizontal":
            return ", ".join(texts)

        return HTMLWriter.render_table(
            HTMLWriter.render_tr(HTMLWriter.render_td(HTMLWriter.render_br().join(texts)))
        )

    def from_html_vars(self, varprefix: str) -> ListChoiceModel:
        self.load_elements()
        return [
            key
            for nr, (key, _title) in enumerate(self._elements)
            if html.get_checkbox("%s_%d" % (varprefix, nr))
        ]  #

    def value_to_json(self, value: ListChoiceModel) -> JSONValue:
        return value

    def value_from_json(self, json_value: JSONValue) -> ListChoiceModel:
        return json_value

    def validate_datatype(self, value: ListChoiceModel, varprefix: str) -> None:
        if not isinstance(value, list):
            raise MKUserError(
                varprefix, _("The datatype must be list, but is %s") % type_name(value)
            )

    def _validate_value(self, value: ListChoiceModel, varprefix: str) -> None:
        if not self._allow_empty and not value:
            raise MKUserError(varprefix, _("You have to select at least one element."))
        self.load_elements()
        for v in value:
            if self._value_is_invalid(v):
                raise MKUserError(varprefix, _("%s is not an allowed value") % v)

    def _value_is_invalid(self, value: ListChoiceChoiceIdent) -> bool:
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
        autoheight: bool = False,
        custom_order: bool = False,
        instant_add: bool = False,
        enlarge_active: bool = False,
        rows: int | None = None,
        size: int | None = None,
        # ListChoice
        choices: ListChoiceChoices = None,
        columns: int = 1,
        allow_empty: bool = True,
        empty_text: str | None = None,
        render_function: Callable[[ListChoiceChoiceIdent, str], str] | None = None,
        toggle_all: bool = False,
        # TODO: Rename to "orientation" to be in line with other valuespecs
        render_orientation: Literal["horizontal", "vertical"] = "horizontal",
        no_elements_text: str | None = None,
        # ValueSpec
        title: str | None = None,
        help: ValueSpecHelp | None = None,
        default_value: ValueSpecDefault[ListChoiceModel] = DEF_VALUE,
        validate: ValueSpecValidateFunc[ListChoiceModel] | None = None,
        locked_choices: Sequence[str] | None = None,
        locked_choices_text_singular: ChoiceText | None = None,
        locked_choices_text_plural: ChoiceText | None = None,
    ):
        super().__init__(
            choices=choices,
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
            validate=validate,
        )
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
        self._locked_choices: Sequence[str] = [] if locked_choices is None else locked_choices
        self._locked_choices_text_singular = (
            locked_choices_text_singular
            if locked_choices_text_singular is not None
            else _("%%d locked element")
        )
        self._locked_choices_text_plural = (
            locked_choices_text_plural
            if locked_choices_text_plural is not None
            else _("%%d locked elements")
        )

    def render_input(  # pylint: disable=too-many-branches
        self,
        varprefix: str,
        value: ListChoiceModel,
    ) -> None:
        self.load_elements()
        if not self._elements:
            html.write_text_permissive(_("There are no elements for selection."))
            return

        # Use values from HTTP request in complain mode (value is empty or None)
        if not value:
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

        select_func = "cmk.valuespecs.duallist_switch('unselected', '%s', %d);" % (
            varprefix,
            1 if self._custom_order else 0,
        )
        unselect_func = "cmk.valuespecs.duallist_switch('selected', '%s', %d);" % (
            varprefix,
            1 if self._custom_order else 0,
        )

        html.open_table(
            class_=["vs_duallist"],
            style="width: %dpx;" % (self._size * 6.4) if self._size else None,
        )

        html.open_tr()
        html.open_td(class_="head")
        html.write_text_permissive(_("Available"))
        if not self._instant_add:
            html.a(">", href="javascript:%s;" % select_func, class_=["control", "add"])
        html.close_td()

        html.open_td(class_="head")
        html.write_text_permissive(_("Selected"))
        if not self._instant_add:
            html.a("<", href="javascript:%s;" % unselect_func, class_=["control", "del"])
        html.close_td()
        html.close_tr()

        html.open_tr()
        for suffix, choices, select_func in [
            ("unselected", unselected, select_func),
            ("selected", selected, unselect_func),
        ]:
            onchange_func = select_func if self._instant_add else ""
            if self._enlarge_active:
                onchange_func = f"cmk.valuespecs.duallist_enlarge({json.dumps(suffix)}, {json.dumps(varprefix)});"

            html.open_td()
            html.dropdown(
                f"{varprefix}_{suffix}",
                [(str(k), v) for k, v in choices],
                deflt="",
                ordered=self._custom_order,
                multiple=True,
                style=("height:auto" if self._autoheight else "height: %dpx" % (self._rows * 16)),
                ondblclick=select_func if not self._instant_add else "",
                onchange=onchange_func,
                locked_choice=(self._locked_choice_text(value) if suffix == "selected" else None),
            )

            html.close_td()
        html.close_tr()

        html.close_table()
        html.hidden_field(
            varprefix,
            "|".join([str(k) for k, v in selected]),
            id_=varprefix,
            add_var=True,
        )

    def _locked_choice_text(self, value: ListChoiceModel) -> ChoiceText | None:
        num_locked_choices = sum(1 for choice_id in value if choice_id in self._locked_choices)
        return (
            self._locked_choices_text_singular % num_locked_choices
            if num_locked_choices == 1
            else (
                self._locked_choices_text_plural % num_locked_choices
                if num_locked_choices > 1
                else None
            )
        )

    def _value_is_invalid(self, value: ListChoiceChoiceIdent) -> bool:
        all_elements = [k for k, v in self._elements]
        all_elements.extend(self._locked_choices)
        return all(value != val for val in all_elements)

    def from_html_vars(self, varprefix: str) -> ListChoiceModel:
        self.load_elements()
        value: list = []
        selection_str = request.var(varprefix, "")
        if selection_str is None:
            return value
        selected = selection_str.split("|")
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

        for locked_choice in self._locked_choices:
            value.append(locked_choice)

        return value


class OptionalDropdownChoice(DropdownChoice[T]):
    """A type-safe dropdown choice with one extra field that
    opens a further value spec for entering an alternative
    Value."""

    def __init__(  # pylint: disable=redefined-builtin
        self,
        explicit: ValueSpec,
        choices: DropdownChoices,
        otherlabel: str | None = None,
        # DropdownChoice
        sorted: bool = False,
        label: str | None = None,
        help_separator: str | None = None,
        prefix_values: bool = False,
        empty_text: str | None = None,
        invalid_choice: DropdownInvalidChoice = "complain",
        invalid_choice_title: str | None = None,
        invalid_choice_error: str | None = None,
        no_preselect_title: str | None = None,
        on_change: str | None = None,
        read_only: bool = False,
        encode_value: bool = True,
        # ValueSpec
        title: str | None = None,
        help: ValueSpecHelp | None = None,
        default_value: ValueSpecDefault[T] = DEF_VALUE,
        validate: ValueSpecValidateFunc[T | None] | None = None,
    ):
        super().__init__(
            choices=choices,
            sorted=sorted,
            label=label,
            help_separator=help_separator,
            prefix_values=prefix_values,
            empty_text=empty_text,
            invalid_choice=invalid_choice,
            invalid_choice_title=invalid_choice_title,
            invalid_choice_error=invalid_choice_error,
            no_preselect_title=no_preselect_title,
            on_change=on_change,
            read_only=read_only,
            encode_value=encode_value,
            title=title,
            help=help,
            default_value=default_value,
            validate=validate,
        )

        self._explicit = explicit
        self._otherlabel = otherlabel if otherlabel is not None else _("Other")

    def canonical_value(self) -> Any:
        return self._explicit.canonical_value()

    def value_is_explicit(self, value):
        return value not in [c[0] for c in self.choices()]

    def render_input(self, varprefix: str, value: Any) -> None:
        defval = "other"
        options: list[tuple[str | None, str]] = []
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
            onchange="cmk.valuespecs.toggle_dropdown(this, '%s_ex');" % varprefix,
        )
        if request.has_var(varprefix):
            div_is_open = request.var(varprefix) == "other"
        else:
            div_is_open = self.value_is_explicit(value)

        html.open_span(
            id_="%s_ex" % varprefix,
            style=["white-space: nowrap;"] + ([] if div_is_open else ["display:none;"]),
        )
        html.nbsp()

        if defval == "other":
            input_value = value
        else:
            input_value = self._explicit.default_value()
        html.help(self._explicit.help())
        self._explicit.render_input(varprefix + "_ex", input_value)
        html.close_span()

    def value_to_html(self, value: Any) -> ValueSpecText:
        for val, title in self.choices():
            if val == value:
                return title
        return self._explicit.value_to_html(value)

    def from_html_vars(self, varprefix: str) -> Any:
        choices = self.choices()
        sel = request.var(varprefix)
        if sel == "other":
            return self._explicit.from_html_vars(varprefix + "_ex")

        for n, (val, _title) in enumerate(choices):
            if sel == str(n):
                return val
        return choices[0][0]  # can only happen if user garbled URL

    def _validate_value(self, value: Any, varprefix: str) -> None:
        if self.value_is_explicit(value):
            self._explicit.validate_value(value, varprefix)

    def validate_datatype(self, value: Any, varprefix: str) -> None:
        for val, _title in self.choices():
            if val == value:
                return
        self._explicit.validate_datatype(value, varprefix + "_ex")


def _round_date(t: float) -> int:
    return int(int(t) / seconds_per_day) * seconds_per_day


def _today() -> int:
    return _round_date(time.time())


# Shadowing help/sorted/... with kwargs is a baaad idea. :-/
_sorted = sorted


def Weekday(  # pylint: disable=redefined-builtin
    # DropdownChoice
    sorted: bool = False,
    label: str | None = None,
    help_separator: str | None = None,
    prefix_values: bool = False,
    empty_text: str | None = None,
    invalid_choice: DropdownInvalidChoice = "complain",
    invalid_choice_title: str | None = None,
    invalid_choice_error: str | None = None,
    no_preselect_title: str | None = None,
    on_change: str | None = None,
    read_only: bool = False,
    encode_value: bool = True,
    html_attrs: HTMLTagAttributes | None = None,
    # ValueSpec
    title: str | None = None,
    help: ValueSpecHelp | None = None,
    default_value: ValueSpecDefault[str] = DEF_VALUE,
    validate: ValueSpecValidateFunc[str | None] | None = None,
    deprecated_choices: Sequence[str] = (),
) -> DropdownChoice:
    return DropdownChoice(
        choices=_sorted(dateutils.weekdays().items()),
        sorted=sorted,
        label=label,
        help_separator=help_separator,
        prefix_values=prefix_values,
        empty_text=empty_text,
        invalid_choice=invalid_choice,
        invalid_choice_title=invalid_choice_title,
        invalid_choice_error=invalid_choice_error,
        no_preselect_title=no_preselect_title,
        on_change=on_change,
        read_only=read_only,
        encode_value=encode_value,
        html_attrs=html_attrs,
        title=title,
        help=help,
        default_value=default_value,
        validate=validate,
        deprecated_choices=deprecated_choices,
    )


class RelativeDate(OptionalDropdownChoice[int]):
    """Input of date with optimization for nearby dates in the future

    Useful for example for alarms. The date is represented by a UNIX timestamp
    where the seconds are silently ignored."""

    def __init__(  # pylint: disable=redefined-builtin
        self,
        default_days: int = 0,
        # DropdownChoice
        sorted: bool = False,
        label: str | None = None,
        help_separator: str | None = None,
        prefix_values: bool = False,
        empty_text: str | None = None,
        invalid_choice: DropdownInvalidChoice = "complain",
        invalid_choice_title: str | None = None,
        invalid_choice_error: str | None = None,
        no_preselect_title: str | None = None,
        on_change: str | None = None,
        read_only: bool = False,
        encode_value: bool = True,
        # ValueSpec
        title: str | None = None,
        help: ValueSpecHelp | None = None,
        validate: ValueSpecValidateFunc[int | None] | None = None,
    ) -> None:
        choices = [
            (0, _("today")),
            (1, _("tomorrow")),
        ]
        weekday = time.localtime(_today()).tm_wday
        for w in range(2, 7):
            wd = (weekday + w) % 7
            choices.append((w, dateutils.weekday_name(wd)))
        for w in range(0, 7):
            wd = (weekday + w) % 7
            if w < 2:
                title = _(" next week")
            else:
                title = _(" in %d days") % (w + 7)
            choices.append((w + 7, dateutils.weekday_name(wd) + title))

        super().__init__(
            explicit=Integer(),
            choices=choices,
            otherlabel=_("in ... days"),
            sorted=sorted,
            label=label,
            help_separator=help_separator,
            prefix_values=prefix_values,
            empty_text=empty_text,
            invalid_choice=invalid_choice,
            invalid_choice_title=invalid_choice_title,
            invalid_choice_error=invalid_choice_error,
            no_preselect_title=no_preselect_title,
            on_change=on_change,
            read_only=read_only,
            encode_value=encode_value,
            title=title,
            help=help,
            default_value=default_days * seconds_per_day + _today(),
            validate=validate,
        )

    def canonical_value(self) -> int | None:
        return self.default_value()

    def render_input(self, varprefix: str, value: int | None) -> None:
        if not isinstance(value, (int, float)):
            raise TypeError(value)
        reldays = int((_round_date(value) - _today()) / seconds_per_day)  # fixed: true-division
        super().render_input(varprefix, reldays)

    def value_to_html(self, value: int | None) -> ValueSpecText:
        if not isinstance(value, (int, float)):
            raise TypeError(value)
        reldays = int((_round_date(value) - _today()) / seconds_per_day)  # fixed: true-division
        if reldays == -1:
            return _("yesterday")
        if reldays == -2:
            return _("two days ago")
        if reldays < 0:
            return _("%d days ago") % -reldays
        choices = self.choices()  # TODO: Is this correct when no_preselect_title is not None?
        if reldays < len(choices):
            return choices[reldays][1]
        return _("in %d days") % reldays

    def from_html_vars(self, varprefix: str) -> int:
        reldays = super().from_html_vars(varprefix)
        return _today() + reldays * seconds_per_day

    def validate_datatype(self, value: int | None, varprefix: str) -> None:
        if not isinstance(value, (int, float)):
            raise MKUserError(varprefix, _("Date must be a number value"))


class AbsoluteDate(ValueSpec[None | float]):
    """A ValueSpec for editing a date

    The date is represented as a UNIX timestamp x where x % seconds_per_day is
    zero (or will be ignored if non-zero), as long as include_time is not set
    to True"""

    def __init__(  # pylint: disable=redefined-builtin
        self,
        show_titles: bool = True,
        label: str | None = None,
        include_time: bool = False,
        format: str | None = None,
        allow_empty: bool = False,
        none_means_empty: bool = False,
        submit_form_name: str | None = None,
        # ValueSpec
        title: str | None = None,
        help: ValueSpecHelp | None = None,
        default_value: ValueSpecDefault[float | None] = DEF_VALUE,
        validate: ValueSpecValidateFunc[float | None] | None = None,
    ):
        super().__init__(
            title=title,
            label=label,
            help=help,
            default_value=default_value,
            validate=validate,
        )
        self._show_titles = show_titles
        self._label = label
        self._include_time = include_time
        self._format = ("%F %T" if self._include_time else "%F") if format is None else format
        self._allow_empty = allow_empty
        # The default is that "None" means show current date/time in the input fields. This option
        # changes the input fields to be empty by default and makes the value able to be None when
        # no time is set. FIXME: Shouldn't this be the default?
        self._none_means_empty = none_means_empty
        self._submit_form_name = submit_form_name

    def allow_empty(self) -> bool:
        return self._allow_empty

    def default_value(self) -> float | None:
        # TODO: Remove the copy-n-paste with ValueSpec.
        if callable(self._default_value):
            try:
                value = self._default_value()
            except Exception:
                value = DEF_VALUE
        else:
            value = self._default_value
        if isinstance(value, Sentinel):
            value = None
        if value is not None:
            return value
        if self._allow_empty:
            return None
        if self._include_time:
            return time.time()
        return _today()

    def canonical_value(self) -> float | None:
        return self.default_value()  # TODO: Hmmm...

    def split_date(
        self, value: float | None
    ) -> tuple[int | None, int | None, int | None, int | None, int | None, int | None]:
        if self._none_means_empty and value is None:
            return None, None, None, None, None, None
        lt = time.localtime(value)
        return lt.tm_year, lt.tm_mon, lt.tm_mday, lt.tm_hour, lt.tm_min, lt.tm_sec

    def render_input(  # pylint: disable=too-many-branches
        self,
        varprefix: str,
        value: float | None,
    ) -> None:
        if self._label:
            html.span(self._label, class_="vs_floating_text")

        year, month, day, hour, mmin, sec = self.split_date(value)
        values: list[tuple[str, int | None, int] | None] = [
            ("_year", year, 4),
            ("_month", month, 2),
            ("_day", day, 2),
        ]
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
                titles += ["", _("Hour"), _("Minute"), _("Sec.")]

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
                        default_value=str(val[1]) if val[1] is not None else "",
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
                    html.write_text_permissive(" ")
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

    def set_focus(self, varprefix: str) -> None:
        html.set_focus(varprefix + "_year")

    def mask(self, value: float | None) -> float | None:
        return value

    def value_to_html(self, value: float | None) -> ValueSpecText:
        return time.strftime(self._format, time.localtime(value))

    def value_to_json(self, value: float | None) -> JSONValue:
        return value

    def value_from_json(self, json_value: JSONValue) -> float | None:
        return json_value

    # TODO: allow_empty is a *very* bad idea typing-wise! We are poisoned by Optional... :-P
    def from_html_vars(self, varprefix: str) -> float | None:
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
                part_str = request.var(varname, "")
                part = int(part_str)
            except ValueError:
                if self._allow_empty:
                    return None
                raise MKUserError(varname, _("Please enter a valid number"))
            if part < mmin or part > mmax:
                raise MKUserError(
                    varname,
                    _("The value for %s must be between %d and %d") % (title, mmin, mmax),
                )
            parts.append(part)

        # Construct broken time from input fields. Assume no-dst
        parts += [0] * (3 if self._include_time else 6)
        # Convert to epoch
        epoch = time.mktime(
            (
                parts[0],  # tm_year
                parts[1],  # tm_mon
                parts[2],  # tm_mday
                parts[3],  # tm_hour
                parts[4],  # tm_min
                parts[5],  # tm_sec
                parts[6],  # tm_wday
                parts[7],  # tm_yday
                parts[8],  # tm_isdst
            )
        )
        # Convert back to localtime in order to know DST setting
        localtime = time.localtime(epoch)
        # Enter DST setting of that time
        parts[-1] = localtime.tm_isdst
        # Convert to epoch again
        return time.mktime(
            (
                parts[0],  # tm_year
                parts[1],  # tm_mon
                parts[2],  # tm_mday
                parts[3],  # tm_hour
                parts[4],  # tm_min
                parts[5],  # tm_sec
                parts[6],  # tm_wday
                parts[7],  # tm_yday
                parts[8],  # tm_isdst
            )
        )

    def validate_datatype(self, value: Any, varprefix: str) -> None:
        if value is None and self._allow_empty:
            return
        if not isinstance(value, (int, float)):
            raise MKUserError(
                varprefix,
                _("The type of the timestamp must be int or float, but is %s") % type_name(value),
            )

    def _validate_value(self, value: float | None, varprefix: str) -> None:
        if (not self._allow_empty and value is None) or (
            value is not None and (value < 0 or int(value) > (2**31 - 1))
        ):
            raise MKUserError(varprefix, _("%s is not a valid Unix timestamp") % value)


TimeofdayValue = tuple[int, int] | None


class Timeofday(ValueSpec[TimeofdayValue]):
    """Valuespec for entering times like 00:35 or 16:17

    Currently no seconds are supported. But this could easily be added.  The
    value itself is stored as a pair of integers, a.g.  (0, 35) or (16, 17). If
    the user does not enter a time the vs will return None.
    """

    def __init__(  # pylint: disable=redefined-builtin
        self,
        allow_24_00: bool = False,
        allow_empty: bool = True,
        placeholder_value: TimeofdayValue = None,
        # ValueSpec
        title: str | None = None,
        help: ValueSpecHelp | None = None,
        default_value: ValueSpecDefault[TimeofdayValue] = DEF_VALUE,
        validate: ValueSpecValidateFunc[TimeofdayValue] | None = None,
    ):
        super().__init__(title=title, help=help, default_value=default_value, validate=validate)
        self._allow_24_00 = allow_24_00
        self._allow_empty = allow_empty
        self._placeholder = ("%02d:%02d" % placeholder_value) if placeholder_value else None

    def allow_empty(self) -> bool:
        return self._allow_empty

    def canonical_value(self) -> TimeofdayValue:
        if self._allow_empty:
            return None
        return (0, 0)

    def render_input(self, varprefix: str, value: TimeofdayValue) -> None:
        text = ("%02d:%02d" % value) if value else ""
        html.text_input(varprefix, text, size=5, placeholder=self._placeholder)

    def mask(self, value: TimeofdayValue) -> TimeofdayValue:
        return value

    def value_to_html(self, value: TimeofdayValue) -> ValueSpecText:
        if value is None:
            return ""
        return "%02d:%02d" % value

    def from_html_vars(self, varprefix: str) -> TimeofdayValue:
        # Fully specified
        text = request.get_str_input_mandatory(varprefix, "").strip()
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
                _("Invalid time format '<tt>%s</tt>', please use <tt>24:00</tt> format.") % text,
            )

    def validate_datatype(self, value: TimeofdayValue, varprefix: str) -> None:
        if self._allow_empty and value is None:
            return

        if not isinstance(value, tuple):
            raise MKUserError(
                varprefix,
                _("The datatype must be tuple, but ist %s") % type_name(value),
            )

        if len(value) != 2:
            raise MKUserError(
                varprefix,
                _("The tuple must contain two elements, but you have %d") % len(value),
            )

        for x in value:
            if not isinstance(x, int):
                raise MKUserError(
                    varprefix,
                    _("All elements of the tuple must be of type int, you have %s") % type_name(x),
                )

    def _validate_value(self, value: TimeofdayValue, varprefix: str) -> None:
        if not self._allow_empty and value is None:
            raise MKUserError(varprefix, _("Please enter a time."))

        if value is None:
            return

        if self._allow_24_00:
            max_value = (24, 0)
        else:
            max_value = (23, 59)

        if value > max_value:
            raise MKUserError(
                varprefix, _("The time must not be greater than %02d:%02d.") % max_value
            )
        if value[0] < 0 or value[1] < 0 or value[0] > 24 or value[1] > 59:
            raise MKUserError(varprefix, _("Hours/Minutes out of range"))

    def value_to_json(self, value: TimeofdayValue) -> JSONValue:
        return None if value is None else [value[0], value[1]]

    def value_from_json(self, json_value: JSONValue) -> tuple[Any, Any]:
        return (json_value[0], json_value[1])


TimeofdayRangeValue = None | tuple[tuple[int, int], tuple[int, int]]


class TimeofdayRange(ValueSpec[TimeofdayRangeValue]):
    """Range like 00:15 - 18:30"""

    def __init__(  # pylint: disable=redefined-builtin
        self,
        allow_empty: bool = True,
        # ValueSpec
        title: str | None = None,
        help: ValueSpecHelp | None = None,
        default_value: ValueSpecDefault[TimeofdayRangeValue] = DEF_VALUE,
        validate: ValueSpecValidateFunc[TimeofdayRangeValue] | None = None,
    ):
        super().__init__(title=title, help=help, default_value=default_value, validate=validate)
        self._allow_empty = allow_empty
        self._bounds = (
            Timeofday(allow_empty=self._allow_empty, allow_24_00=True, placeholder_value=(0, 0)),
            Timeofday(allow_empty=self._allow_empty, allow_24_00=True, placeholder_value=(24, 0)),
        )

    def allow_empty(self) -> bool:
        return self._allow_empty

    def canonical_value(self) -> TimeofdayRangeValue:
        if self._allow_empty:
            return None
        return (0, 0), (24, 0)

    def render_input(self, varprefix: str, value: TimeofdayRangeValue) -> None:
        self._bounds[0].render_input(varprefix + "_from", value[0] if value is not None else None)
        html.nbsp()
        html.write_text_permissive("-")
        html.nbsp()
        self._bounds[1].render_input(varprefix + "_until", value[1] if value is not None else None)

    def mask(self, value: TimeofdayRangeValue) -> TimeofdayRangeValue:
        return value

    def value_to_html(self, value: TimeofdayRangeValue) -> ValueSpecText:
        if value is None:
            return ""

        return (
            self._bounds[0].value_to_html(value[0]) + "-" + self._bounds[1].value_to_html(value[1])
        )

    def from_html_vars(self, varprefix: str) -> TimeofdayRangeValue:
        from_value = self._bounds[0].from_html_vars(varprefix + "_from")
        until_value = self._bounds[1].from_html_vars(varprefix + "_until")
        if (from_value is None) != (until_value is None):
            raise MKUserError(
                varprefix + "_from",
                _("Please leave either both from and until empty or enter two times."),
            )
        if from_value is None:
            return None
        if until_value is None:
            return None
        return (from_value, until_value)

    def validate_datatype(self, value: TimeofdayRangeValue, varprefix: str) -> None:
        if self._allow_empty and value is None:
            return

        if not isinstance(value, tuple):
            raise MKUserError(
                varprefix,
                _("The datatype must be tuple, but ist %s") % type_name(value),
            )

        if len(value) != 2:
            raise MKUserError(
                varprefix,
                _("The tuple must contain two elements, but you have %d") % len(value),
            )

        self._bounds[0].validate_datatype(value[0], varprefix + "_from")
        self._bounds[1].validate_datatype(value[1], varprefix + "_until")

    def _validate_value(self, value: TimeofdayRangeValue, varprefix: str) -> None:
        if value is None:
            if self._allow_empty:
                return
            raise MKUserError(varprefix + "_from", _("Please enter a valid time of day range"))

        self._bounds[0].validate_value(value[0], varprefix + "_from")
        self._bounds[1].validate_value(value[1], varprefix + "_until")
        if value[0] > value[1]:
            raise MKUserError(
                varprefix + "_until",
                _("The <i>from</i> time must not be later then the <i>until</i> time."),
            )

    def value_to_json(self, value: TimeofdayRangeValue) -> JSONValue:
        if value is None:
            return None
        return [
            self._bounds[0].value_to_json(value[0]),
            self._bounds[1].value_to_json(value[1]),
        ]

    def value_from_json(self, json_value: JSONValue) -> TimeofdayRangeValue:
        if json_value is None:
            return None
        return (
            self._bounds[0].value_from_json(json_value[0]),
            self._bounds[1].value_from_json(json_value[1]),
        )


class TimeHelper:
    @staticmethod
    def round(timestamp, unit):
        lt = datetime.datetime.fromtimestamp(timestamp, tzlocal()).replace(minute=0, second=0)
        if unit != "h":
            lt = lt.replace(hour=0)

        if unit == "w":
            lt -= datetime.timedelta(days=lt.weekday())
        elif unit == "m":
            lt = lt.replace(day=1)
        elif unit == "y":
            lt = lt.replace(month=1, day=1)
        elif unit not in {"d", "h"}:
            raise MKGeneralException("invalid time unit %s" % unit)

        return lt.timestamp()

    @staticmethod
    def add(timestamp, count, unit):
        lt = datetime.datetime.fromtimestamp(timestamp, tzlocal())
        if unit == "h":
            lt += relativedelta(hours=count)
        elif unit == "d":
            lt += relativedelta(days=count)
        elif unit == "w":
            lt += relativedelta(days=7 * count)
        elif unit == "m":
            lt += relativedelta(months=count)
        elif unit == "y":
            lt += relativedelta(years=count)
        else:
            raise MKGeneralException("invalid time unit %s" % unit)

        return lt.timestamp()


TimerangeValue = None | int | str | tuple[str, Any]  # TODO: Be more specific


class ComputedTimerange(NamedTuple):
    range: tuple[int, int]
    title: str


class Timerange(CascadingDropdown):
    def __init__(  # pylint: disable=redefined-builtin
        self,
        include_time: bool = False,
        choices: CascadingDropdownChoices | None = None,
        # CascadingDropdown
        # TODO: Make this more specific
        label: str | None = None,
        separator: str = ", ",
        sorted: bool = False,
        orientation: Literal["vertical", "horizontal"] = "vertical",
        render: CascadingDropdown.Render | None = None,
        no_elements_text: str | None = None,
        no_preselect_title: str | None = None,
        render_sub_vs_page_name: str | None = None,
        render_sub_vs_request_vars: dict | None = None,
        # ValueSpec
        title: str | None = None,
        help: ValueSpecHelp | None = None,
        default_value: ValueSpecDefault[CascadingDropdownChoiceValue] = DEF_VALUE,
        validate: ValueSpecValidateFunc[CascadingDropdownChoiceValue] | None = None,
    ):
        super().__init__(
            choices=self._prepare_choices,
            label=label,
            separator=separator,
            sorted=sorted,
            orientation=orientation,
            render=render,
            no_elements_text=no_elements_text,
            no_preselect_title=no_preselect_title,
            render_sub_vs_page_name=render_sub_vs_page_name,
            render_sub_vs_request_vars=render_sub_vs_request_vars,
            title=title,
            help=help,
            default_value=default_value,
            validate=validate,
        )
        self._title = title if title is not None else _("Time range")
        self._include_time = include_time
        self._fixed_choices = choices

    def _prepare_choices(self) -> Sequence[CascadingDropdownChoice]:
        # TODO: We have dispatching code like this all over place...
        if self._fixed_choices is None:
            choices: list[CascadingDropdownChoice] = []
        elif isinstance(self._fixed_choices, list):
            choices = list(self._fixed_choices)
        elif callable(self._fixed_choices):
            choices = list(self._fixed_choices())
        else:
            raise ValueError("invalid type for choices")

        choices.extend(self._get_graph_timeranges())
        choices.extend(
            [
                ("d0", _("Today")),
                ("d1", _("Yesterday")),
                ("d7", _("7 days back (this day last week)")),
                ("d8", _("8 days back")),
                ("w0", _("This week")),
                ("w1", _("Last week")),
                ("w2", _("2 weeks back")),
                ("m0", _("This month")),
                ("m1", _("Last month")),
                ("y0", _("This year")),
                ("y1", _("Last year")),
                ("age", _("The last..."), Age()),
                (
                    "date",
                    _("Date range"),
                    Tuple(
                        orientation="horizontal",
                        title_br=False,
                        elements=[
                            AbsoluteDate(title=_("From:")),
                            AbsoluteDate(title=_("To:")),
                        ],
                    ),
                ),
            ]
        )

        if self._include_time:
            choices += [
                (
                    "time",
                    _("Date & time range"),
                    Tuple(
                        orientation="vertical",
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
                        ],
                    ),
                )
            ]
        return choices

    def _get_graph_timeranges(self) -> Sequence[CascadingDropdownCleanChoice]:
        try:
            return _normalize_choices(
                [
                    (timerange_attrs["duration"], timerange_attrs["title"])
                    for timerange_attrs in active_config.graph_timeranges
                ]
            )

        except AttributeError:  # only available in cee
            return _normalize_choices(
                [
                    ("4h", _("The last 4 hours")),
                    ("25h", _("The last 25 hours")),
                    ("8d", _("The last 8 days")),
                    ("35d", _("The last 35 days")),
                    ("400d", _("The last 400 days")),
                ]
            )

    def value_to_html(self, value: CascadingDropdownChoiceValue) -> ValueSpecText:
        for ident, title, _vs in self._get_graph_timeranges():
            if value == ident:
                return title
            # Cleanup on Werk 4477, treat old(pre 2.0) casted defaults earlier
            if isinstance(value, tuple) and value == ("age", ident):
                return title

        return super().value_to_html(value)

    def value_to_json(self, value: CascadingDropdownChoiceValue) -> JSONValue:
        if isinstance(value, int):  # Handle default graph_timeranges
            return super().value_to_json(("age", value))
        return super().value_to_json(value)

    def value_from_json(self, json_value: JSONValue) -> CascadingDropdownChoiceValue:
        value = super().value_from_json(json_value)
        # Handle default graph_timeranges
        for ident, _title, _vs in self._get_graph_timeranges():
            if value == ("age", ident):
                return ident
        return value

    @staticmethod
    def compute_range(  # pylint: disable=too-many-branches
        rangespec: TimerangeValue,
    ) -> ComputedTimerange:
        def _date_span(from_time: float, until_time: float) -> str:
            start = AbsoluteDate().value_to_html(from_time)
            end = AbsoluteDate().value_to_html(until_time - 1)
            if start == end:
                return str(start)
            return str(start) + " \u2014 " + str(end)

        def _month_edge_days(now: float, day_id: str) -> ComputedTimerange:
            # base time is current time rounded down to month
            from_time = TimeHelper.round(now, "m")
            if day_id in ["f1", "fwd1"]:  # first (work) day of last month
                from_time = TimeHelper.add(from_time, -1, "m")
            if day_id in ["l1", "lwd1"]:  # last (work) day of last month
                from_time = TimeHelper.add(from_time, -1, "d")
            if day_id == "lwd0":  # last work day of this month
                from_time = TimeHelper.add(from_time, 1, "m")
                from_time = TimeHelper.add(from_time, -1, "d")

            if (
                "wd" in day_id
                and (weekday_number := datetime.datetime.fromtimestamp(from_time).weekday()) > 4
            ):
                # find first/last work day. we're ignoring holidays here
                if day_id.startswith("fwd"):
                    from_time = TimeHelper.add(from_time, 7 - weekday_number, "d")
                elif day_id.startswith("lwd"):
                    from_time = TimeHelper.add(from_time, 4 - weekday_number, "d")

            end_time = TimeHelper.add(from_time, 1, "d")

            return ComputedTimerange(
                (int(from_time), int(end_time)),
                time.strftime("%d/%m/%Y", time.localtime(from_time)),
            )

        def _fixed_dates(
            rangespec: tuple[str, tuple[float, float]],
        ) -> ComputedTimerange:
            from_time, until_time = rangespec[1]
            if from_time > until_time:
                raise MKUserError(
                    "avo_rangespec_9_0_year",
                    _("The end date must be after the start date"),
                )
            if rangespec[0] == "date":
                # This includes the end day
                until_time = TimeHelper.add(until_time, 1, "d")
            return ComputedTimerange(
                (int(from_time), int(until_time)), _date_span(from_time, until_time)
            )

        if rangespec is None:
            rangespec = "4h"
        elif isinstance(rangespec, int):
            rangespec = ("age", rangespec)

        elif isinstance(rangespec, tuple) and rangespec[0] == "pnp_view":
            # Compatibility with previous versions
            rangespec = {
                1: "4h",
                2: "25h",
                3: "8d",
                4: "35d",
                5: "400d",
            }.get(rangespec[1], "4h")

        now = time.time()

        if isinstance(rangespec, tuple):
            if rangespec[0] == "age":
                title = _("The last ") + str(Age().value_to_html(rangespec[1]))
                return ComputedTimerange((int(now - rangespec[1]), int(now)), title)
            if isinstance(rangespec, tuple) and rangespec[0] == "next":
                title = _("The next ") + str(Age().value_to_html(rangespec[1]))
                return ComputedTimerange((int(now), int(now + rangespec[1])), title)
            if isinstance(rangespec, tuple) and rangespec[0] == "until":
                return ComputedTimerange(
                    (int(now), int(rangespec[1])),
                    str(AbsoluteDate().value_to_html(rangespec[1])),
                )
            if isinstance(rangespec, tuple) and rangespec[0] in ["date", "time"]:
                return _fixed_dates(rangespec)

            raise NotImplementedError()

        if not isinstance(rangespec, str):
            raise TypeError(rangespec)

        if rangespec[0].isdigit():  # 4h, 400d
            count = int(rangespec[:-1])
            from_time = TimeHelper.add(now, count * -1, rangespec[-1])
            unit_name = {"d": "days", "h": "hours"}[rangespec[-1]]
            title = _("Last %d %s") % (count, unit_name)
            return ComputedTimerange((int(from_time), int(now)), title)

        if rangespec in ["f0", "f1", "l1", "fwd0", "lwd0", "fwd1", "lwd1"]:
            return _month_edge_days(now, rangespec)

        # base time is current time rounded down to the nearest unit (day, week, ...)
        from_time = TimeHelper.round(now, rangespec[0])
        year, month = time.localtime(now)[:2]
        # derive titles from unit ()
        titles = {
            "d": (_("Today"), _("Yesterday")),
            "w": (_("This week"), _("Last week")),
            "y": (str(year), None),
            "m": ("%s %d" % (dateutils.month_name(month - 1), year), None),
        }[rangespec[0]]

        if rangespec[1] == "0":
            return ComputedTimerange((int(from_time), int(now)), titles[0])

        # last (previous)
        span = int(rangespec[1:])
        prev_time = TimeHelper.add(from_time, -1 * span, rangespec[0])
        # day and week spans for historic data
        if rangespec[0] in ["d", "w"]:
            end_time = TimeHelper.add(prev_time, 1, rangespec[0])
            if not isinstance(titles[1], str):
                raise TypeError(titles[1])
            title = _date_span(prev_time, end_time) if span > 1 else titles[1]
            return ComputedTimerange((int(prev_time), int(end_time)), title)

        # This only works for Months, but those are the only defaults in Forecast Graphs
        # Language localization to system language not CMK GUI language
        if prev_time > from_time:
            from_time, prev_time = prev_time, from_time
        prev_time_str: str = time.strftime("%B %Y", time.localtime(prev_time))
        end_time_str = time.strftime("%B %Y", time.localtime(from_time - 1))
        if prev_time_str != end_time_str:
            prev_time_str += " \u2014 " + end_time_str
        if rangespec[0] == "y":
            prev_time_str = time.strftime("%Y", time.localtime(prev_time))

        return ComputedTimerange((int(prev_time), int(from_time)), titles[1] or prev_time_str)


def DateFormat(  # pylint: disable=redefined-builtin
    # DropdownChoice
    sorted: bool = False,
    label: str | None = None,
    help_separator: str | None = None,
    prefix_values: bool = False,
    empty_text: str | None = None,
    invalid_choice: DropdownInvalidChoice = "complain",
    invalid_choice_title: str | None = None,
    invalid_choice_error: str | None = None,
    no_preselect_title: str | None = None,
    on_change: str | None = None,
    read_only: bool = False,
    encode_value: bool = False,  # NOTE: Different!
    html_attrs: HTMLTagAttributes | None = None,
    # ValueSpec
    title: str | None = None,
    help: ValueSpecHelp | None = None,
    default_value: ValueSpecDefault[str] = "%Y-%m-%d",  # NOTE: Different!
    validate: ValueSpecValidateFunc[str | None] | None = None,
    deprecated_choices: Sequence[str] = (),
) -> DropdownChoice:
    """A selection of various date formats"""
    return DropdownChoice[str](
        choices=[
            ("%Y-%m-%d", "1970-12-18"),
            ("%d.%m.%Y", "18.12.1970"),
            ("%m/%d/%Y", "12/18/1970"),
            ("%d.%m.", "18.12."),
            ("%m/%d", "12/18"),
        ],
        sorted=sorted,
        label=label,
        help_separator=help_separator,
        prefix_values=prefix_values,
        empty_text=empty_text,
        invalid_choice=invalid_choice,
        invalid_choice_title=invalid_choice_title,
        invalid_choice_error=invalid_choice_error,
        no_preselect_title=no_preselect_title,
        on_change=on_change,
        read_only=read_only,
        encode_value=encode_value,
        html_attrs=html_attrs,
        title=_("Date format") if title is None else title,
        help=help,
        default_value=default_value,
        validate=validate,
        deprecated_choices=deprecated_choices,
    )


def TimeFormat(  # pylint: disable=redefined-builtin
    # DropdownChoice
    sorted: bool = False,
    label: str | None = None,
    help_separator: str | None = None,
    prefix_values: bool = False,
    empty_text: str | None = None,
    invalid_choice: DropdownInvalidChoice = "complain",
    invalid_choice_title: str | None = None,
    invalid_choice_error: str | None = None,
    no_preselect_title: str | None = None,
    on_change: str | None = None,
    read_only: bool = False,
    encode_value: bool = True,
    html_attrs: HTMLTagAttributes | None = None,
    # ValueSpec
    title: str | None = None,
    help: ValueSpecHelp | None = None,
    default_value: ValueSpecDefault[str] = "%H:%M:%S",  # NOTE: Different!
    validate: ValueSpecValidateFunc[str | None] | None = None,
    deprecated_choices: Sequence[str] = (),
) -> DropdownChoice:
    return DropdownChoice(
        choices=[
            ("%H:%M:%S", "18:27:36"),
            ("%l:%M:%S %p", "12:27:36 PM"),
            ("%H:%M", "18:27"),
            ("%l:%M %p", "6:27 PM"),
            ("%H", "18"),
            ("%l %p", "6 PM"),
        ],
        sorted=sorted,
        label=label,
        help_separator=help_separator,
        prefix_values=prefix_values,
        empty_text=empty_text,
        invalid_choice=invalid_choice,
        invalid_choice_title=invalid_choice_title,
        invalid_choice_error=invalid_choice_error,
        no_preselect_title=no_preselect_title,
        on_change=on_change,
        read_only=read_only,
        encode_value=encode_value,
        html_attrs=html_attrs,
        title=_("Time format") if title is None else title,
        help=help,
        default_value=default_value,
        validate=validate,
        deprecated_choices=deprecated_choices,
    )


class Optional(ValueSpec[None | T]):
    """Make a configuration value optional, i.e. it may be None.

    The user has a checkbox for activating the option. Example:
    debug_log: it is either None or set to a filename."""

    def __init__(  # pylint: disable=redefined-builtin
        self,
        valuespec: ValueSpec[T],
        label: str | None = None,
        negate: bool = False,
        none_label: str | None = None,
        sameline: bool = False,
        indent: bool = True,
        # ValueSpec
        title: str | None = None,
        help: ValueSpecHelp | None = None,
        default_value: ValueSpecDefault[T | None] = DEF_VALUE,
        validate: ValueSpecValidateFunc[T | None] | None = None,
    ):
        super().__init__(
            title=title,
            label=label,
            help=help,
            default_value=default_value,
            validate=validate,
        )
        self._valuespec = valuespec
        self._label = label
        self._negate = negate
        self._none_label = none_label if none_label is not None else _("(unset)")
        self._sameline = sameline
        self._indent = indent

    def canonical_value(self) -> T | None:
        return None

    def render_input(self, varprefix: str, value: T | None) -> None:
        div_id = "option_" + varprefix
        checked = html.get_checkbox(varprefix + "_use")
        if checked is None:
            if self._negate:
                checked = value is None
            else:
                checked = value is not None

        html.open_span()
        html.checkbox(
            "%s_use" % varprefix,
            checked,
            label=self._get_label(),
            onclick=f"cmk.valuespecs.toggle_option(this, {json.dumps(div_id)}, {1 if self._negate else 0!r})",
        )
        if self._sameline:
            html.nbsp()
        else:
            html.br()
        html.close_span()

        if self._indent:
            indent = 40
        else:
            indent = 0

        html.open_span(
            id_=div_id,
            style=["margin-left: %dpx;" % indent]
            + (["display:none;"] if checked == self._negate else []),
        )
        if value is None:
            value = self._valuespec.default_value()
        if self._valuespec.title():
            the_title = self._valuespec.title()
            html.write_text_permissive(("???" if the_title is None else the_title) + " ")
        self._valuespec.render_input(varprefix + "_value", value)
        html.close_span()

    def _get_label(self) -> str:
        if self._label is not None:
            return self._label
        t = self.title()
        if t:
            return t
        if self._negate:
            return _(" Ignore this option")
        return _(" Activate this option")

    def value_to_html(self, value: T | None) -> ValueSpecText:
        if value is None:
            return self._none_label
        return self._valuespec.value_to_html(value)

    def from_html_vars(self, varprefix: str) -> T | None:
        checkbox_checked = html.get_checkbox(varprefix + "_use") is True  # not None or False
        if checkbox_checked != self._negate:
            return self._valuespec.from_html_vars(varprefix + "_value")
        return None

    def validate_datatype(self, value: T | None, varprefix: str) -> None:
        if value is not None:
            self._valuespec.validate_datatype(value, varprefix + "_value")

    def _validate_value(self, value: T | None, varprefix: str) -> None:
        if value is not None:
            self._valuespec.validate_value(value, varprefix + "_value")

    def mask(self, value: T | None) -> T | None:
        return value if value is None else self._valuespec.mask(value)

    def transform_value(self, value: T | None) -> T | None:
        return value if value is None else self._valuespec.transform_value(value)

    def has_show_more(self) -> bool:
        return self._valuespec.has_show_more()

    def value_to_json(self, value: T | None) -> JSONValue:
        if value is None:
            return None
        return self._valuespec.value_to_json(value)

    def value_from_json(self, json_value: JSONValue) -> T | None:
        if json_value is None:
            return None
        return self._valuespec.value_from_json(json_value)


AlternativeModel = Any


class Alternative(ValueSpec[AlternativeModel]):
    """Handle case when there are several possible allowed formats
    for the value (e.g. strings, 4-tuple or 6-tuple like in SNMP-Communities)
    The different alternatives must have different data types that can
    be distinguished with validate_datatype."""

    def __init__(  # pylint: disable=redefined-builtin
        self,
        elements: Sequence[ValueSpec[AlternativeModel]],
        match: Callable[[AlternativeModel], int] | None = None,
        show_alternative_title: bool = False,
        on_change: str | None = None,
        orientation: Literal["horizontal", "vertical"] = "vertical",
        # ValueSpec
        title: str | None = None,
        help: ValueSpecHelp | None = None,
        default_value: ValueSpecDefault[AlternativeModel] = DEF_VALUE,
        validate: ValueSpecValidateFunc[AlternativeModel] | None = None,
        style: str | None = None,  # CMK-12228
    ):
        super().__init__(title=title, help=help, default_value=default_value, validate=validate)
        self._elements = elements
        self._match = match  # custom match function, returns index in elements
        self._show_alternative_title = show_alternative_title
        self._on_change = on_change
        self._orientation = orientation  # or horizontal

    # Return the alternative (i.e. valuespec)
    # that matches the datatype of a given value. We assume
    # that always one matches. No error handling here.
    # This may also tranform the input value in case it gets
    # "decorated" in the from_html_vars function
    def _matching_alternative(self, value: AlternativeModel) -> ValueSpec[AlternativeModel] | None:
        if self._match:
            return self._elements[self._match(value)]

        for vs in self._elements:
            try:
                vs.validate_datatype(value, "")
                return vs
            except Exception:
                pass

        return None

    def render_input(self, varprefix: str, value: AlternativeModel) -> None:
        mvs = self._matching_alternative(value)
        options: list[tuple[str | None, str]] = []
        sel_option = request.var(varprefix + "_use")
        for nr, vs in enumerate(self._elements):
            if not sel_option and vs == mvs:
                sel_option = str(nr)
            the_title = vs.title()
            options.append((str(nr), "???" if the_title is None else the_title))
        onchange = "cmk.valuespecs.cascading_change(this, '%s', %d);" % (
            varprefix,
            len(options),
        )
        if self._on_change:
            onchange += self._on_change
        if self._orientation == "horizontal":
            html.open_table(class_="alternative")
            html.open_tr()
            html.open_td()
        html.dropdown(
            varprefix + "_use",
            options,
            deflt=("???" if sel_option is None else sel_option),
            onchange=onchange,
        )
        if self._orientation == "vertical":
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
            html.open_span(id_=f"{varprefix}_{nr}_sub", style="display:%s" % disp)
            html.help(vs.help())
            vs.render_input(varprefix + "_%d" % nr, cur_val)
            html.close_span()

        if self._orientation == "horizontal":
            html.close_td()
            html.close_tr()
            html.close_table()

    def set_focus(self, varprefix: str) -> None:
        # TODO: Set focus to currently active option
        pass

    def canonical_value(self) -> AlternativeModel:
        return self._elements[0].canonical_value()

    def default_value(self) -> AlternativeModel:
        if callable(self._default_value):
            try:
                value = self._default_value()
            except Exception:
                value = DEF_VALUE
        else:
            value = self._default_value

        if isinstance(value, Sentinel):
            return self._elements[0].default_value()
        return value

    def mask(self, value: AlternativeModel) -> AlternativeModel:
        vs = self._matching_alternative(value)
        if vs is None:
            raise ValueError(_("Invalid value: %s") % (value,))
        return vs.mask(value)

    def value_to_html(self, value: AlternativeModel) -> ValueSpecText:
        vs = self._matching_alternative(value)
        if vs:
            output = HTML.empty()
            if self._show_alternative_title and (title := vs.title()):
                output = HTML.with_escaping(title) + HTMLWriter.render_br()
            return output + vs.value_to_html(value)
        return _("invalid:") + " " + str(value)

    def value_to_json(self, value: AlternativeModel) -> JSONValue:
        vs = self._matching_alternative(value)
        if vs is None:
            raise ValueError(_("Invalid value: %s") % (value,))
        return vs.value_to_json(value)

    def value_from_json(self, json_value: JSONValue) -> AlternativeModel:
        # FIXME: This is wrong! value_to_json transforms tuples to lists. json_value could
        # contain a list that should be a tuple at ANY level. So we would need to run
        # self.matching_value(json_value) with every permutation from list to tuple
        # inside json_value here. An example ruleset is "ESX Multipath Count".
        return json_value

    def from_html_vars(self, varprefix: str) -> AlternativeModel:
        nr = request.get_integer_input_mandatory(varprefix + "_use")
        vs = self._elements[nr]
        return vs.from_html_vars(varprefix + "_%d" % nr)

    def validate_datatype(self, value: AlternativeModel, varprefix: str) -> None:
        for vs in self._elements:
            try:
                vs.validate_datatype(value, "")
                return
            except Exception:
                pass
        raise MKUserError(
            varprefix,
            _("The data type of the value does not match any of the allowed alternatives."),
        )

    def _validate_value(self, value: AlternativeModel, varprefix: str) -> None:
        vs = self._matching_alternative(value)
        for nr, v in enumerate(self._elements):
            if vs == v:
                vs.validate_value(value, varprefix + "_%d" % nr)
                return
        raise MKUserError(
            varprefix,
            _("The data type of the value does not match any of the allowed alternatives."),
        )

    def transform_value(self, value: AlternativeModel) -> AlternativeModel:
        vs = self._matching_alternative(value)
        if not vs:
            raise MKUserError(
                None,
                _("Found no matching alternative."),
            )
        return vs.transform_value(value)


TT = TypeVar("TT", bound=tuple[Any, ...])


class Tuple(ValueSpec[TT]):
    # TODO: wait for TypeVarTuple mypy support:
    # https://github.com/python/mypy/issues/12840
    """Edit a n-tuple (with fixed size) of values"""

    def __init__(  # pylint: disable=redefined-builtin
        self,
        elements: Sequence[ValueSpec],
        show_titles: bool = True,
        orientation: str = "vertical",
        separator: str = " ",
        title_br: bool = True,
        # ValueSpec
        title: str | None = None,
        help: ValueSpecHelp | None = None,
        validate: ValueSpecValidateFunc[TT] | None = None,
    ):
        super().__init__(title=title, help=help, default_value=DEF_VALUE, validate=validate)
        self._elements = elements
        self._show_titles = show_titles
        self._orientation = orientation  # also: horizontal, float
        self._separator = separator  # in case of float
        self._title_br = title_br

    def allow_empty(self) -> bool:
        return all(vs.allow_empty() for vs in self._elements)

    def canonical_value(self) -> TT:
        return tuple(x.canonical_value() for x in self._elements)  # type: ignore[return-value]

    def default_value(self) -> TT:
        return tuple(x.default_value() for x in self._elements)  # type: ignore[return-value]

    def render_input(self, varprefix: str, value: Any) -> None:  # pylint: disable=too-many-branches
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
                html.write_text_permissive(self._separator)

            title = ""
            if self._show_titles:
                elem_title = element.title()
                if elem_title:
                    title = elem_title[0].upper() + elem_title[1:]
                if self._orientation == "vertical":
                    html.open_td(class_="tuple_left")
                    if title:
                        html.span(title, class_="vs_floating_text")

                    html.close_td()
                elif self._orientation == "horizontal":
                    html.open_td(class_="tuple_td")
                    if title:
                        html.span(title, class_=["title"])

                    if self._title_br and title:
                        html.br()
                    else:
                        html.write_text_permissive(" ")
                else:
                    html.write_text_permissive(" ")

            elif self._orientation == "horizontal":
                html.open_td(class_="tuple_td")

            if self._orientation == "vertical":
                html.open_td(class_="tuple_right" + (" has_title" if title else ""))

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

    def set_focus(self, varprefix: str) -> None:
        self._elements[0].set_focus(varprefix + "_0")

    def _iter_value(self, value: TT) -> Iterable[tuple[int, ValueSpec, Any]]:
        for idx, element in enumerate(self._elements):
            yield idx, element, value[idx]

    def mask(self, value: TT) -> TT:
        return tuple(el.mask(val) for _, el, val in self._iter_value(value))  # type: ignore[return-value]

    def value_to_html(self, value: TT) -> ValueSpecText:
        return HTML.without_escaping(", ").join(
            el.value_to_html(val) for _, el, val in self._iter_value(value)
        )

    def value_to_json(self, value: TT) -> JSONValue:
        return [el.value_to_json(val) for _, el, val in self._iter_value(value)]

    def value_from_json(self, json_value: JSONValue) -> TT:
        return tuple(el.value_from_json(val) for _, el, val in self._iter_value(json_value))  # type: ignore[return-value]

    def from_html_vars(self, varprefix: str) -> TT:
        return tuple(e.from_html_vars(f"{varprefix}_{idx}") for idx, e in enumerate(self._elements))  # type: ignore[return-value]

    def _validate_value(self, value: TT, varprefix: str) -> None:
        for idx, el, val in self._iter_value(value):
            el.validate_value(val, f"{varprefix}_{idx}")

    def validate_datatype(self, value: TT, varprefix: str) -> None:
        if not isinstance(value, tuple):
            raise MKUserError(
                varprefix,
                _("The datatype must be a tuple, but is %s") % type_name(value),
            )
        if len(value) != len(self._elements):
            raise MKUserError(
                varprefix,
                _("The number of elements in the tuple must be exactly %d.") % len(self._elements),
            )

        for idx, el, val in self._iter_value(value):
            el.validate_datatype(val, f"{varprefix}_{idx}")

    def transform_value(self, value: TT) -> TT:
        if not isinstance(value, tuple):
            raise TypeError(f"Tuple.transform_value() got a non-tuple: {value!r}")
        return tuple(vs.transform_value(value[index]) for index, vs in enumerate(self._elements))  # type: ignore[return-value]


DictionaryEntry = tuple[str, ValueSpec]
DictionaryElements = Iterable[DictionaryEntry]
DictionaryElementsRaw = Promise[DictionaryElements]
DictionaryModel = dict[str, Any]


class Dictionary(ValueSpec[DictionaryModel]):
    # TODO: Cleanup ancient "migrate"
    def __init__(  # pylint: disable=redefined-builtin
        self,
        elements: DictionaryElementsRaw,
        empty_text: str | None = None,
        default_text: str | None = None,
        optional_keys: bool | Iterable[str] = True,
        required_keys: Sequence[str] | None = None,
        show_more_keys: Sequence[str] | None = None,
        ignored_keys: Sequence[str] | None = None,
        default_keys: Sequence[str] | None = None,
        hidden_keys: Sequence[str] | None = None,
        columns: Literal[1, 2] = 1,
        render: Literal["normal", "form", "form_part"] = "normal",
        form_narrow: bool = False,
        form_isopen: bool = True,
        headers: None
        | (Sequence[tuple[str, Sequence[str]] | tuple[str, str, Sequence[str]]]) = None,
        migrate: Callable[[tuple], dict] | None = None,
        indent: bool = True,
        horizontal: bool = False,
        # ValueSpec
        title: str | None = None,
        help: ValueSpecHelp | None = None,
        validate: ValueSpecValidateFunc[DictionaryModel] | None = None,
    ):
        super().__init__(title=title, help=help, default_value=DEF_VALUE, validate=validate)
        if callable(elements):
            self._elements = elements
        else:
            const_elements = list(elements)
            self._elements = lambda: const_elements
        self._empty_text = empty_text if empty_text is not None else _("(no parameters)")

        # Optionally a text can be specified to be shown by value_to_html()
        # when the value equal the default value of the value spec. Normally
        # the default values are shown.
        self._default_text = default_text
        self._required_keys = required_keys or []
        self._show_more_keys = show_more_keys or []
        self._ignored_keys = ignored_keys or []
        self._default_keys = default_keys or []  # keys present in default value
        self._hidden_keys = hidden_keys or []

        if isinstance(optional_keys, bool):
            self._optional_keys = optional_keys
        elif opt_keys := set(optional_keys):
            self._optional_keys = True
            if self._required_keys:
                raise TypeError("optional_keys and required_keys can not be set at the same time.")
            self._required_keys = [e[0] for e in self._get_elements() if e[0] not in opt_keys]
        else:
            self._optional_keys = False

        if self._optional_keys is False and self._required_keys:
            raise TypeError(
                "optional_keys = False enforces all keys to be required, so required_keys has no effect."
            )

        self._columns = columns
        self._render = render
        self._form_narrow = form_narrow  # used if render == "form"
        self._form_isopen = form_isopen  # used if render == "form"
        self._headers = headers
        self._migrate = migrate  # value migration from old tuple version
        self._indent = indent
        self._horizontal = horizontal

    def migrate(self, value: Any) -> DictionaryModel:
        return self._migrate(value) if self._migrate else value

    def _get_elements(self) -> DictionaryElements:
        yield from self._elements()

    # TODO: Optional has to be cleaned up to make the type signature compatible with the base class
    def render_input_as_form(self, varprefix: str, value: DictionaryModel | None) -> None:
        self._render_input(varprefix, value, "form")

    # TODO: Optional has to be cleaned up to make the type signature compatible with the base class
    def render_input(self, varprefix: str, value: DictionaryModel | None) -> None:
        self._render_input(varprefix, value, self._render)

    # TODO: Optional has to be cleaned up to make the type signature compatible with the base class
    def _render_input(self, varprefix: str, value: DictionaryModel | None, render: str) -> None:
        value = self.migrate(value)
        if not isinstance(value, MutableMapping):
            value = {}  # makes code simpler in complain phase

        elements = list(self._get_elements())
        if len(elements) == 0:
            html.write_text_permissive(self._empty_text)
            return

        if render == "form":
            self._render_input_form(varprefix, elements, value)
        elif render == "form_part":
            self._render_input_form(varprefix, elements, value, as_part=True)
        else:
            self._render_input_normal(varprefix, elements, value, two_columns=self._columns == 2)

    def _render_input_normal_row(
        self,
        varprefix: str,
        value: DictionaryModel,
        two_columns: bool,
        nr: int,
        param: str,
        vs: ValueSpec,
    ) -> None:
        if not self._horizontal or self._horizontal and nr == 0:
            html.open_tr(class_="show_more_mode" if param in self._show_more_keys else None)

        self._render_td(
            varprefix,
            value,
            two_columns,
            param,
            vs,
        )
        if not self._horizontal:
            html.close_tr()

    def _render_td(
        self,
        varprefix: str,
        value: DictionaryModel,
        two_columns: bool,
        param: str,
        vs: ValueSpec,
    ) -> None:
        html.open_td(class_=["dictleft"] + (["horizontal"] if self._horizontal else []))

        div_id = varprefix + "_d_" + param
        vp = varprefix + "_p_" + param
        colon_printed = False
        label = vs.title()
        is_required_plain_checkbox = False
        if self._optional_keys and param not in self._required_keys:
            checkbox_varname = vp + "_USE"
            visible = html.get_checkbox(checkbox_varname)
            if visible is None:
                visible = param in value
            if two_columns:
                label = f"{label}:"
                colon_printed = True
            html.checkbox(
                checkbox_varname,
                visible,
                label=label,
                onclick="cmk.valuespecs.toggle_option(this, %s)" % json.dumps(div_id),
            )
        else:
            visible = True
            if label:
                html.write_text_permissive(" ")
                html.write_text_permissive(label)
            # two_columns are used for space efficiency in very few places like e.g. filters
            # where it is clear from the context if values are required or not. Therefore, we
            # dont add a required label in this case.
            if not two_columns and not vs.allow_empty():
                html.span(_(" (required)"), class_="required")

            is_required_plain_checkbox = isinstance(vs, Checkbox) and not label

        # If the vs is an instance of Checkbox, is required and does not have a title, we skip
        # this horizontal and vertical spacing. This makes the Checkbox vs rendering align with
        # the rendering of checkboxes for optional dict elements
        if not is_required_plain_checkbox:
            if two_columns:
                if label and not colon_printed:
                    html.write_text_permissive(":")
                html.help(vs.help())
                html.close_td()
                html.open_td(class_="dictright")
            elif label:
                html.br()

            html.open_div(
                id_=div_id,
                class_=["dictelement"] + (["indent"] if self._indent and not two_columns else []),
                style="display:none;" if not visible else None,
            )

        if not two_columns or is_required_plain_checkbox:
            html.help(vs.help())
        # Remember: in complain mode we do not render 'value' (the default value),
        # but re-display the values from the HTML variables. We must not use 'value'
        # in that case.
        the_value = value.get(param, vs.default_value()) if isinstance(value, dict) else None
        vs.render_input(vp, the_value)
        if not is_required_plain_checkbox:
            html.close_div()

        html.close_td()

    def _render_input_normal(
        self,
        varprefix: str,
        elements: DictionaryElements,
        value: DictionaryModel,
        two_columns: bool,
    ) -> None:
        html.open_table(class_=["dictionary"] + (["horizontal"] if self._horizontal else []))
        for nr, (param, vs) in enumerate(elements):
            if param in self._hidden_keys:
                continue
            self._render_input_normal_row(varprefix, value, two_columns, nr, param, vs)
        if self._horizontal:
            html.close_tr()
        html.close_table()

    def _render_input_form(
        self,
        varprefix: str,
        elements: DictionaryElements,
        value: DictionaryModel,
        as_part: bool = False,
    ) -> None:
        headers = self._headers or [(self.title() or _("Properties"), [])]
        for header, css, section_elements in map(self._normalize_header, headers):
            if not as_part:
                forms.header(
                    header,
                    isopen=self._form_isopen,
                    narrow=self._form_narrow,
                    show_more_toggle=self._section_has_show_more(section_elements),
                    show_more_mode=user.show_mode != "default_show_less",
                    help_text=self.help(),
                )
            self.render_input_form_header(
                varprefix, elements, value, header, section_elements, css=css
            )
        if not as_part:
            forms.end()

    @staticmethod
    def _normalize_header(
        header: tuple[str, Sequence[str]] | tuple[str, str, Sequence[str]],
    ) -> tuple[str, str | None, Sequence[str]]:
        if isinstance(header, tuple):
            if len(header) == 2:
                return header[0], None, header[1]
            if len(header) == 3:
                return header[0], header[1], header[2]
            raise ValueError("invalid header tuple length")
        raise ValueError("invalid header type")

    def _section_has_show_more(self, section_elements: Sequence[str]) -> bool:
        """Valuespec Dictionary has option "show_more_keys" but can be buried under
        multiple different valuespecs"""
        # visuals deliver no section_elements
        if not section_elements:
            return self.has_show_more()

        return any(
            param in self._show_more_keys or vs.has_show_more()
            for param, vs in self._get_elements()
            if param in section_elements
        )

    def render_input_form_header(
        self,
        varprefix: str,
        elements: DictionaryElements,
        value: DictionaryModel,
        title: str,
        section_elements: Sequence[str],
        css: str | None,
    ) -> None:
        for param, vs in elements:
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
                    onclick="cmk.valuespecs.toggle_option(this, %s)" % json.dumps(div_id),
                )
                forms.section(
                    vs.title(),
                    checkbox=checkbox_code,
                    css=css,
                    is_show_more=param in self._show_more_keys,
                )
            else:
                visible = True
                forms.section(
                    vs.title(),
                    css=css,
                    is_show_more=param in self._show_more_keys,
                    is_required=not vs.allow_empty(),
                )

            html.open_div(id_=div_id, style="display:none;" if not visible else None)
            html.help(vs.help())
            vs.render_input(vp, value.get(param, vs.default_value()))
            html.close_div()

    def set_focus(self, varprefix: str) -> None:
        first_element = next(iter(self._get_elements()), None)
        if first_element:
            first_element[1].set_focus(varprefix + "_p_" + first_element[0])

    def canonical_value(self) -> DictionaryModel:
        return {
            name: vs.canonical_value()
            for (name, vs) in self._get_elements()
            if name in self._required_keys or not self._optional_keys
        }

    def default_value(self) -> DictionaryModel:
        return {
            name: vs.default_value()
            for name, vs in self._get_elements()
            if name in self._required_keys or not self._optional_keys or name in self._default_keys
        }

    def mask(self, value: DictionaryModel) -> DictionaryModel:
        return {
            param: vs.mask(value[param]) for param, vs in self._get_elements() if param in value
        }

    def value_to_html(self, value: DictionaryModel) -> ValueSpecText:
        value = self.migrate(value)
        if not value:
            return self._empty_text

        if self._default_text and value == self.default_value():
            return self._default_text

        elem = self._get_elements()
        return self._value_to_html_multiline(elem, value)

    def _value_to_html_multiline(self, elem: DictionaryElements, value: DictionaryModel) -> HTML:
        s = HTML.empty()
        for param, vs in elem:
            if param in value:
                if vs.title():
                    title = "%s:&nbsp;" % vs.title()
                elif vs.label():
                    title = "%s:&nbsp;" % vs.label()
                else:
                    title = "&nbsp;"
                s += HTMLWriter.render_tr(
                    HTMLWriter.render_td(title, class_="title")
                    + HTMLWriter.render_td(vs.value_to_html(value[param]))
                )
        return HTMLWriter.render_table(s)

    def value_to_json(self, value: DictionaryModel) -> JSONValue:
        return {
            param: vs.value_to_json(value[param])
            for param, vs in self._get_elements()
            if param in value
        }

    def value_from_json(self, json_value: JSONValue) -> DictionaryModel:
        return {
            param: vs.value_from_json(json_value[param])
            for param, vs in self._get_elements()
            if param in json_value
        }

    def from_html_vars(self, varprefix: str) -> DictionaryModel:
        return {
            param: vs.from_html_vars(f"{varprefix}_p_{param}")
            for param, vs in self._get_elements()
            if (
                not self._optional_keys
                or param in self._required_keys
                or html.get_checkbox(f"{varprefix}_p_{param}_USE")
            )
        }

    def validate_datatype(self, value: DictionaryModel, varprefix: str) -> None:
        value = self.migrate(value)

        if not isinstance(value, dict):
            raise MKUserError(
                varprefix,
                _("The type must be a dictionary, but it is a %s") % type_name(value),
            )

        for param, vs in self._get_elements():
            if param in value:
                try:
                    vs.validate_datatype(value[param], f"{varprefix}_p_{param}")
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
                    _("Undefined key '%s' in the dictionary. Allowed are %s.")
                    % (param, ", ".join(allowed_keys)),
                )

    def _validate_value(self, value: DictionaryModel, varprefix: str) -> None:
        value = self.migrate(value)

        for param, vs in self._get_elements():
            if param in value:
                vs.validate_value(value[param], f"{varprefix}_p_{param}")
            elif not self._optional_keys or param in self._required_keys:
                raise MKUserError(varprefix, _("The entry %s is missing") % vs.title())

    def transform_value(self, value: DictionaryModel) -> DictionaryModel:
        if not isinstance(value, dict):
            raise TypeError(f"Dictionary.transform_value() got a non-dict: {value!r}")
        value = self.migrate(value)
        return {
            **{
                param: vs.transform_value(value[param])
                for param, vs in self._get_elements()
                if param in value
            },
            **{param: value[param] for param in self._ignored_keys if param in value},  #
        }

    def has_show_more(self) -> bool:
        return bool(self._show_more_keys) or any(
            vs.has_show_more() for _param, vs in self._get_elements()
        )


# TODO: Cleanup this and all call sites. Replace it with some kind of DropdownChoice
# based valuespec
class ElementSelection(ValueSpec[None | str]):
    """Base class for selection of a Nagios element out of a given list that must be loaded from a file.

    Example: GroupSelection. Child class must define
    a function get_elements() that returns a dictionary
    from element keys to element titles."""

    def __init__(  # pylint: disable=redefined-builtin
        self,
        label: str | None = None,
        empty_text: str | None = None,
        # ValueSpec
        title: str | None = None,
        help: ValueSpecHelp | None = None,
        default_value: ValueSpecDefault[str] = DEF_VALUE,
        validate: ValueSpecValidateFunc[str | None] | None = None,
    ):
        super().__init__(
            title=title,
            label=label,
            help=help,
            default_value=default_value,
            validate=validate,
        )
        self._loaded_at: int | None = None
        self._label = label
        self._empty_text = (
            empty_text
            if empty_text is not None
            else _("There are no elements defined for this selection yet.")
        )

    def load_elements(self) -> None:
        if self._loaded_at != id(html):
            self._elements = self.get_elements()
            self._loaded_at = id(html)  # unique for each query!

    @abc.abstractmethod
    def get_elements(self) -> Mapping[str, str]:
        raise NotImplementedError()

    def canonical_value(self) -> str | None:
        self.load_elements()
        if self._elements:
            return list(self._elements.keys())[0]
        return None

    def render_input(self, varprefix: str, value: str | None) -> None:
        self.load_elements()
        if len(self._elements) == 0:
            html.write_text_permissive(self._empty_text)
        else:
            if self._label:
                html.span(self._label, class_="vs_floating_text")
            html.dropdown(varprefix, self._elements.items(), deflt=value, ordered=True)

    def mask(self, value: str | None) -> str | None:
        return value

    def value_to_json(self, value: str | None) -> JSONValue:
        return value

    def value_from_json(self, json_value: JSONValue) -> str | None:
        return json_value

    def from_html_vars(self, varprefix: str) -> str | None:
        return request.var(varprefix)

    def _validate_value(self, value: str | None, varprefix: str) -> None:
        self.load_elements()
        if len(self._elements) == 0:
            raise MKUserError(varprefix, _("You cannot save this rule.") + " " + self._empty_text)
        if value not in self._elements:
            raise MKUserError(
                varprefix,
                _("%s is not an existing element in this selection.") % (value,),
            )

    def validate_datatype(self, value: str | None, varprefix: str) -> None:
        self.load_elements()
        # When no elements exists the default value is None and e.g. in wato.mode_edit_rule()
        # handed over to validate_datatype() before rendering the input form. Disable the
        # validation in this case to prevent validation errors. A helpful message is shown
        # during render_input()
        if len(self._elements) == 0 and value is None:
            return

        if not isinstance(value, str):
            raise MKUserError(
                varprefix,
                _("The datatype must be str (string), but is %s") % type_name(value),
            )


class AutoTimestamp(FixedValue[float]):
    def canonical_value(self) -> float:
        return time.time()

    def from_html_vars(self, varprefix: str) -> float:
        return time.time()

    def value_to_html(self, value: float) -> ValueSpecText:
        return time.strftime("%F %T", time.localtime(value))

    def validate_datatype(self, value: float, varprefix: str) -> None:
        if not isinstance(value, (int, float)):
            raise MKUserError(varprefix, _("Invalid datatype of timestamp: must be int or float."))


class Foldable(ValueSpec[T]):
    """Fully transparant VS encapsulating a vs in a foldable container"""

    def __init__(  # pylint: disable=redefined-builtin
        self,
        valuespec: ValueSpec[T],
        title_function: Callable[[Any], str] | None = None,
        # ValueSpec
        title: str | None = None,
        help: ValueSpecHelp | None = None,
        default_value: ValueSpecDefault[T] = DEF_VALUE,
        validate: ValueSpecValidateFunc[T] | None = None,
    ) -> None:
        super().__init__(title=title, help=help, default_value=default_value, validate=validate)
        self._valuespec = valuespec
        self._title_function = title_function

    def render_input(self, varprefix: str, value: T) -> None:
        with foldable_container(
            treename="valuespec_foldable",
            id_=varprefix,
            isopen=False,
            title=self._get_title(varprefix, value),
            indent=False,
        ):
            html.help(self._valuespec.help())
            html.open_div(class_="valuespec_foldable_content")
            self._valuespec.render_input(varprefix, value)
            html.close_div()

    def _get_title(self, varprefix: str, value: T) -> str:
        if self._title_function:
            title_value = value
            if html.form_submitted():
                try:
                    title_value = self._valuespec.from_html_vars(varprefix)
                except Exception:
                    pass
            return self._title_function(title_value)

        if title := self._valuespec.title():
            return title
        return _("(no title)")

    def set_focus(self, varprefix: str) -> None:
        self._valuespec.set_focus(varprefix)

    def canonical_value(self) -> T:
        return self._valuespec.canonical_value()

    def default_value(self) -> T:
        return self._valuespec.default_value()

    def mask(self, value: T) -> T:
        return self._valuespec.mask(value)

    def value_to_html(self, value: T) -> ValueSpecText:
        return self._valuespec.value_to_html(value)

    def from_html_vars(self, varprefix: str) -> T:
        return self._valuespec.from_html_vars(varprefix)

    def value_to_json(self, value: T) -> JSONValue:
        return self._valuespec.value_to_json(value)

    def value_from_json(self, json_value: JSONValue) -> T:
        return self._valuespec.value_from_json(json_value)

    def validate_datatype(self, value: Any, varprefix: str) -> None:
        self._valuespec.validate_datatype(value, varprefix)

    def _validate_value(self, value: T, varprefix: str) -> None:
        self._valuespec.validate_value(value, varprefix)

    def transform_value(self, value: T) -> T:
        return self._valuespec.transform_value(value)

    def has_show_more(self) -> bool:
        return self._valuespec.has_show_more()


class Transform(ValueSpec[T]):
    """Transforms the value from one representation to another while being
    completely transparent to the user

    The transformation is implemented by two functions: to_valuespec and from_valuespec:

    to_valuespec: Converts a value from any "outer world" representation (e.g. as
                  it was read from a .mk file) to the form that is processable by
                  the encapsulated ValueSpec (e.g. for rendering).

    from_valuespec: Converts a value created by the encapsulated ValueSpec back to
                    the outer representation.

    Use cases:
    * When the value of the valuespec is used by some external tool, and that
      tool expects a different value format: You already know that a vs.Age will
      be consumed by a tool that expects minutes instead of Seconds. Then you
      can use a Transform to transparently transform this value so it can be
      consumed without additional calculations.
    * When you can not decide if you already transformed the value or not:
      Imagine a vs.Integer that contained minutes, but was then replaced by a
      vs.Age (for better UI) which stores the duration in seconds:
      We only got an integer value and can not know if it's seconds or minutes.
      So we make sure it is saved as minutes on the disc, and transform it back
      and forth each time we load or save the value.
    """

    def __init__(  # pylint: disable=redefined-builtin
        self,
        valuespec: ValueSpec[T],
        *,
        # we would like to remove forth and back and make to_valuespec and from_valuespec mandatory,
        # however, this change is too incompatible (cf. CMK-12242)
        to_valuespec: Callable[[Any], T] | None = None,
        from_valuespec: Callable[[T], Any] | None = None,
        forth: Callable[[Any], T] | None = None,
        back: Callable[[T], Any] | None = None,
        title: str | None = None,
        help: ValueSpecHelp | None = None,
        default_value: ValueSpecDefault[Any] = DEF_VALUE,
        validate: ValueSpecValidateFunc[Any] | None = None,
    ):
        super().__init__(title=title, help=help, default_value=default_value, validate=validate)
        self._valuespec: Final = valuespec
        self.to_valuespec: Final = to_valuespec or forth or (lambda v: v)
        self.from_valuespec: Final = from_valuespec or back or (lambda v: v)

    def allow_empty(self) -> bool:
        return self._valuespec.allow_empty()

    def title(self) -> str | None:
        if self._title:
            return self._title
        return self._valuespec.title()

    def help(self) -> str | HTML | None:
        transform_help = super().help()
        if transform_help:
            return transform_help
        return self._valuespec.help()

    def render_input(self, varprefix: str, value: Any) -> None:
        self._valuespec.render_input(varprefix, self.to_valuespec(value))

    def set_focus(self, varprefix: str) -> None:
        self._valuespec.set_focus(varprefix)

    def canonical_value(self) -> Any:
        return self.from_valuespec(self._valuespec.canonical_value())

    def default_value(self) -> Any:
        return self.from_valuespec(self._valuespec.default_value())

    def mask(self, value: Any) -> Any:
        return self.from_valuespec(self._valuespec.mask(self.to_valuespec(value)))

    def value_to_html(self, value: Any) -> ValueSpecText:
        return self._valuespec.value_to_html(self.to_valuespec(value))

    def from_html_vars(self, varprefix: str) -> Any:
        return self.from_valuespec(self._valuespec.from_html_vars(varprefix))

    def validate_datatype(self, value: Any, varprefix: str) -> None:
        self._valuespec.validate_datatype(self.to_valuespec(value), varprefix)

    def _validate_value(self, value: Any, varprefix: str) -> None:
        self._valuespec.validate_value(self.to_valuespec(value), varprefix)

    def transform_value(self, value: Any) -> Any:
        return self.from_valuespec(self._valuespec.transform_value(self.to_valuespec(value)))

    def has_show_more(self) -> bool:
        return self._valuespec.has_show_more()

    def value_to_json(self, value: Any) -> JSONValue:
        return self._valuespec.value_to_json(self.to_valuespec(value))

    def value_from_json(self, json_value: JSONValue) -> Any:
        return self.from_valuespec(self._valuespec.value_from_json(json_value))


class Migrate(Transform[T]):
    """Migrates a value from a legacy format to the current format while
    being completely transparent to the user

    migrate: Converts a value from a legacy format (e.g. as it was read from a
             .mk file) to the format that is processable by the encapsulated
             ValueSpec (e.g. for rendering).
    """

    def __init__(  # pylint: disable=redefined-builtin
        self,
        valuespec: ValueSpec[T],
        *,
        migrate: Callable[[Any], T],
        title: str | None = None,
        help: ValueSpecHelp | None = None,
        default_value: ValueSpecDefault[T] = DEF_VALUE,
        validate: ValueSpecValidateFunc[T] | None = None,
    ):
        super().__init__(
            valuespec=valuespec,
            to_valuespec=migrate,
            from_valuespec=lambda v: v,
            title=title,
            help=help,
            default_value=default_value,
            validate=validate,
        )


class MigrateNotUpdated(Migrate[T]):
    """Marks places which are not covered by update_config, ie. places which cannot
    be cleaned up after a new major release.
    """


class Transparent(Transform[T]):
    """Transparenly changes the title or the help of a wrapped ValueSpec"""

    def __init__(  # pylint: disable=redefined-builtin
        self,
        valuespec: ValueSpec[T],
        *,
        title: str | None = None,
        help: ValueSpecHelp | None = None,
        default_value: ValueSpecDefault[T] = DEF_VALUE,
        validate: ValueSpecValidateFunc[T] | None = None,
    ):
        super().__init__(
            valuespec=valuespec,
            to_valuespec=lambda v: v,
            from_valuespec=lambda v: v,
            title=title,
            help=help,
            default_value=default_value,
            validate=validate,
        )


class LDAPDistinguishedName(TextInput):
    def __init__(  # pylint: disable=redefined-builtin
        self,
        enforce_suffix: str | None = None,
        # TextInput
        label: str | None = None,
        size: int | Literal["max"] = 25,
        try_max_width: bool = False,
        cssclass: str = "text",
        strip: bool = True,
        allow_empty: bool = True,
        empty_text: str = "",
        read_only: bool = False,
        forbidden_chars: str = "",
        regex: None | str | Pattern[str] = None,
        regex_error: str | None = None,
        minlen: int | None = None,
        maxlen: int | None = None,
        oninput: str | None = None,
        autocomplete: str | None = None,
        placeholder: str | None = None,
        # ValueSpec
        title: str | None = None,
        help: ValueSpecHelp | None = None,
        default_value: ValueSpecDefault[str] = DEF_VALUE,
        validate: ValueSpecValidateFunc[str] | None = None,
    ) -> None:
        super().__init__(
            label=label,
            size=size,
            try_max_width=try_max_width,
            cssclass=cssclass,
            strip=strip,
            allow_empty=allow_empty,
            empty_text=empty_text,
            read_only=read_only,
            forbidden_chars=forbidden_chars,
            regex=regex,
            regex_error=regex_error,
            minlen=minlen,
            maxlen=maxlen,
            oninput=oninput,
            autocomplete=autocomplete,
            placeholder=placeholder,
            title=title,
            help=help,
            default_value=default_value,
            validate=validate,
        )
        self.enforce_suffix = enforce_suffix

    def _validate_value(self, value: str, varprefix: str) -> None:
        super()._validate_value(value, varprefix)

        # Check whether or not the given DN is below a base DN
        if (
            self.enforce_suffix
            and value
            and not value.lower().endswith(self.enforce_suffix.lower())
        ):
            raise MKUserError(varprefix, _('Does not ends with "%s".') % self.enforce_suffix)


class Password(TextInput):
    """Text input for passwords

    About the Encrypter:

    A basic concept of valuespecs is that they transport ALL data back and forth between different
    states. This has also the consequence that also secrets, like passwords, must be transported to
    the client, which should remain better only on the server.

    To deal with this in a reasonably secure way, we encrypt passwords for transport from backend =>
    HTML => backend.

    If it turns out that the approach is not sufficient, then we will have to soften this principle
    of valuespecs and somehow leave the passwords on the server.

    The encrypted values are only used for transactions and not persisted. This means you can change
    the algorithm at any time.
    """

    def __init__(  # pylint: disable=redefined-builtin
        self,
        is_stored_plain: bool = True,
        encrypt_value: bool = True,
        password_meter: bool = False,
        # TextInput
        label: str | None = None,
        size: int | Literal["max"] = 25,
        try_max_width: bool = False,
        cssclass: str = "text",
        strip: bool = True,
        allow_empty: bool = True,
        empty_text: str = "",
        read_only: bool = False,
        forbidden_chars: str = "",
        regex: None | str | Pattern[str] = None,
        regex_error: str | None = None,
        minlen: int | None = None,
        maxlen: int | None = None,
        oninput: str | None = None,
        autocomplete: str | None = "new-password",  # NOTE: Different!
        placeholder: str | None = None,
        # ValueSpec
        title: str | None = None,
        help: ValueSpecText | None = None,  # NOTE: Different!
        default_value: ValueSpecDefault[str] = DEF_VALUE,
        validate: ValueSpecValidateFunc[str] | None = None,
    ) -> None:
        """Password ValueSpec

        Args:
            password_meter (bool): Should the password meter be displayed? (Default: False)
        """
        self._is_stored_plain = is_stored_plain
        self._encrypt_value = encrypt_value
        self.password_meter = password_meter
        if self._is_stored_plain:
            plain_help = _(
                "The password entered here is stored in clear text within "
                "the monitoring site. This is necessary because the "
                "monitoring process must have access to the unencrypted "
                "password in order to provide it for authentication with "
                "remote systems."
            )
            help = plain_help if help is None else (help + "<br><br>" + plain_help)

        super().__init__(
            label=label,
            size=size,
            try_max_width=try_max_width,
            cssclass=cssclass,
            strip=strip,
            allow_empty=allow_empty,
            empty_text=empty_text,
            read_only=read_only,
            forbidden_chars=forbidden_chars,
            regex=regex,
            regex_error=regex_error,
            minlen=minlen,
            maxlen=maxlen,
            oninput=oninput,
            autocomplete=autocomplete,
            placeholder=placeholder,
            title=title,
            help=help,
            default_value=default_value,
            validate=validate,
        )

    def render_input(self, varprefix: str, value: str | None) -> None:
        if value is None:
            value = ""

        if self._label:
            html.span(self._label, class_="vs_floating_text")

        if self._encrypt_value:
            html.hidden_field(
                varprefix + "_orig",
                value=(base64.b64encode(Encrypter.encrypt(value)).decode("ascii") if value else ""),
            )
            default_value = ""
        else:
            default_value = value

        html.password_input(
            varprefix,
            default_value=default_value,
            size=self._size,
            autocomplete=self._autocomplete,
            placeholder="******" if value else "",
        )
        if self.password_meter:
            html.password_meter()

    def password_plaintext_warning(self) -> None:
        if self._is_stored_plain:
            html.span(
                _(
                    "<br>Please note that Checkmk needs this password in clear"
                    "<br>text during normal operation and thus stores it unencrypted"
                    "<br>on the Checkmk server."
                )
            )

    def mask(self, value: str | None) -> str:
        # Note: This intentionally returns the same output if value is None,
        #       in order to not reveal any information about the (empty) password.
        return "******"

    def value_to_html(self, value: str | None) -> ValueSpecText:
        if value is None:
            return _("none")
        return "******"

    def from_html_vars(self, varprefix: str) -> str:
        value = super().from_html_vars(varprefix)
        if value or not self._encrypt_value:
            return value  # New password entered or unencrypted password

        # Gather the value produced by render_input() and use it.
        value = request.get_str_input_mandatory(varprefix + "_orig", "")
        if not value:
            return value

        return Encrypter.decrypt(base64.b64decode(value.encode("ascii")))


class PasswordSpec(Password):
    def __init__(  # pylint: disable=redefined-builtin
        self,
        pwlen: int = 8,
        # Password
        is_stored_plain: bool = True,
        # TextInput
        label: str | None = None,
        size: int | Literal["max"] = 25,
        try_max_width: bool = False,
        cssclass: str = "text",
        strip: bool = True,
        allow_empty: bool = True,
        empty_text: str = "",
        read_only: bool = False,
        forbidden_chars: str = "",
        regex: None | str | Pattern[str] = None,
        regex_error: str | None = None,
        minlen: int | None = None,
        maxlen: int | None = None,
        oninput: str | None = None,
        autocomplete: str | None = "new-password",  # NOTE: Different!
        placeholder: str | None = None,
        # ValueSpec
        title: str | None = None,
        help: ValueSpecText | None = None,  # NOTE: Different!
        default_value: ValueSpecDefault[str] = DEF_VALUE,
        validate: ValueSpecValidateFunc[str] | None = None,
    ) -> None:
        self._pwlen = pwlen
        super().__init__(
            is_stored_plain=is_stored_plain,
            encrypt_value=False,
            label=label,
            size=size,
            try_max_width=try_max_width,
            cssclass=cssclass,
            strip=strip,
            allow_empty=allow_empty,
            empty_text=empty_text,
            read_only=read_only,
            forbidden_chars=forbidden_chars,
            regex=regex,
            regex_error=regex_error,
            minlen=minlen,
            maxlen=maxlen,
            oninput=oninput,
            autocomplete=autocomplete,
            placeholder=placeholder,
            title=title,
            help=help,
            default_value=default_value,
            validate=validate,
        )

    def render_input(self, varprefix: str, value: str | None) -> None:
        super().render_input(varprefix, value)
        if not value:
            html.icon_button(
                "#",
                _("Randomize password"),
                "random",
                onclick=f"cmk.valuespecs.passwordspec_randomize(this, {self._pwlen});",
            )
        html.icon_button(
            "#",
            _("Show/hide password"),
            "showhide",
            onclick="cmk.valuespecs.toggle_hidden(this);",
        )

        self.password_plaintext_warning()


# TODO: This is totally broken, it should probably be just UploadedFile
FileUploadModel = bytes | UploadedFile | None


class FileUpload(ValueSpec[FileUploadModel]):
    def __init__(  # pylint: disable=redefined-builtin
        self,
        allow_empty: bool = False,
        allowed_extensions: Iterable[str] | None = None,
        mime_types: Iterable[str] | None = None,
        allow_empty_content: bool = True,
        # ValueSpec
        title: str | None = None,
        help: ValueSpecHelp | None = None,
        default_value: ValueSpecDefault[FileUploadModel] = DEF_VALUE,
        validate: ValueSpecValidateFunc[FileUploadModel] | None = None,
    ) -> None:
        super().__init__(title=title, help=help, default_value=default_value, validate=validate)
        self._allow_empty = allow_empty
        self._allowed_extensions = allowed_extensions
        self._allow_empty_content = allow_empty_content
        self._allowed_mime_types = mime_types

    def allow_empty(self) -> bool:
        return self._allow_empty

    def canonical_value(self) -> FileUploadModel:
        return None if self._allow_empty else b""

    def _validate_value(self, value: FileUploadModel, varprefix: str) -> None:
        if not value:
            raise MKUserError(varprefix, _("Please select a file."))
        if not isinstance(value, tuple):  # Hmmm...
            raise TypeError(value)

        file_name, mime, content = value

        if not self._allow_empty and (content == b"" or file_name == ""):
            raise MKUserError(varprefix, _("Please select a file."))

        if not self._allow_empty_content and not content:
            raise MKUserError(
                varprefix,
                _("The selected file is empty. Please select a non-empty file."),
            )
        if self._allowed_extensions is not None and not any(
            file_name.endswith(extension) for extension in self._allowed_extensions
        ):
            raise MKUserError(
                varprefix,
                _("Invalid file type expected %s received '%s'")
                % (
                    ", ".join(extension for extension in self._allowed_extensions),
                    Path(file_name).suffix,
                ),
            )

        if self._allowed_mime_types is not None and mime not in self._allowed_mime_types:
            raise MKUserError(varprefix, _("Invalid file type."))

    def render_input(self, varprefix: str, value: FileUploadModel) -> None:
        html.upload_file(varprefix)

    def mask(self, value: FileUploadModel) -> FileUploadModel:
        return value

    def from_html_vars(self, varprefix: str) -> FileUploadModel:
        return request.uploaded_file(varprefix)

    def value_to_json(self, value: FileUploadModel) -> JSONValue:
        return value

    def value_from_json(self, json_value: JSONValue) -> FileUploadModel:
        return json_value

    def value_to_html(self, value: FileUploadModel) -> ValueSpecText:
        match value:
            case (str(file_name), str(_), bytes(_)):
                return _("Chosen file: %s") % file_name
            case other:
                raise TypeError(other)


class ImageUpload(FileUpload):
    def __init__(  # pylint: disable=redefined-builtin
        self,
        max_size: tuple[int, int] | None = None,
        show_current_image: bool = False,
        # FileUpload
        allow_empty: bool = False,
        allowed_extensions: Iterable[str] | None = None,
        allow_empty_content: bool = True,
        mime_types: Iterable[str] | None = None,
        # ValueSpec
        title: str | None = None,
        help: ValueSpecHelp | None = None,
        default_value: ValueSpecDefault[FileUploadModel] = DEF_VALUE,
        validate: ValueSpecValidateFunc[FileUploadModel] | None = None,
    ) -> None:
        if allowed_extensions is None:
            allowed_extensions = [".png"]
        self._max_size: Final = max_size
        self._show_current_image: Final = show_current_image
        super().__init__(
            allow_empty=allow_empty,
            allowed_extensions=allowed_extensions,
            allow_empty_content=allow_empty_content,
            title=title,
            help=help,
            default_value=default_value,
            validate=validate,
            mime_types=mime_types,
        )

    def render_input(self, varprefix: str, value: FileUploadModel) -> None:
        if isinstance(value, str):
            # since latin_1 only uses one byte, we can use it for str->byte conversion
            value = value.encode("latin_1")
        if self._show_current_image and value:
            if not isinstance(value, bytes):  # Hmmm...
                raise TypeError(value)
            html.open_table()
            html.open_tr()
            html.td(_("Current image:"))
            html.td(
                HTMLWriter.render_img("data:image/png;base64,%s" % base64.b64encode(value).decode())
            )
            html.close_tr()
            html.open_tr()
            html.td(_("Upload new:"))
            html.open_td()
            super().render_input(varprefix, value)
            html.close_td()
            html.close_tr()
            html.close_table()
        else:
            super().render_input(varprefix, value)

    def _validate_value(self, value: FileUploadModel, varprefix: str) -> None:
        super()._validate_value(value, varprefix)
        if not value:
            raise MKUserError(varprefix, _("Please choose a PNG image."))
        if not isinstance(value, tuple):  # Hmmm...
            raise TypeError(value)

        content = value[2]

        try:
            image = CMKImage(content, ImageType.PNG)
        except (ValueError, OSError) as exception:
            raise MKUserError(varprefix, _("Please choose a valid PNG image.")) from exception

        if self._max_size:
            w, h = image.image_size()
            max_w, max_h = self._max_size
            if w > max_w or h > max_h:
                raise MKUserError(varprefix, _("Maximum image size: %dx%dpx") % (max_w, max_h))


class UploadOrPasteTextFile(Alternative):
    def __init__(  # pylint: disable=redefined-builtin
        self,
        file_title: str | None = None,
        allow_empty: bool = False,
        # Alternative
        elements: Iterable[ValueSpec] = (),
        # NOTE: Match defaut is different!
        match: Callable[[Any], int] | None = lambda val: (0 if isinstance(val, tuple) else 1),
        show_alternative_title: bool = False,
        on_change: str | None = None,
        orientation: Literal["horizontal", "vertical"] = "vertical",
        allowed_extensions: Iterable[str] | None = None,
        mime_types: Iterable[str] | None = None,
        # ValueSpec
        title: str | None = None,
        help: ValueSpecHelp | None = None,
        default_value: ValueSpecDefault[Any] = DEF_VALUE,
        validate: ValueSpecValidateFunc[Any] | None = None,
    ):
        f_title = _("File") if file_title is None else file_title
        additional_elements: list[ValueSpec] = [
            FileUpload(
                title=_("Upload %s") % f_title,
                allow_empty=allow_empty,
                allowed_extensions=allowed_extensions,
                mime_types=mime_types,
            ),
            TextAreaUnicode(
                title=_("Content of %s") % f_title,
                allow_empty=allow_empty,
                cols=80,
                rows="auto",
            ),
        ]
        super().__init__(
            elements=list(elements) + additional_elements,
            match=match,
            show_alternative_title=show_alternative_title,
            on_change=on_change,
            orientation=orientation,
            title=title,
            help=help,
            default_value=default_value,
            validate=validate,
        )

    def from_html_vars(self, varprefix: str) -> str:
        value: Final[UploadedFile] = super().from_html_vars(varprefix)
        # We validate the value here, because we want to validate the user input,
        # that will be lost after the following transformation to str.
        # After that, the validate_value() function will always validate the
        # TextAreaUnicode case when called.
        super()._validate_value(value, varprefix)
        if isinstance(value, tuple):
            try:
                # We are only interested in the file content here. Get it from FileUpload value.
                return value[-1].decode("utf-8")
            except UnicodeDecodeError as exc:
                raise MKUserError(varprefix, _("Please choose a file to upload.")) from exc
        return value


class TextOrRegExp(Alternative):
    def __init__(  # pylint: disable=redefined-builtin
        self,
        text_valuespec: ValueSpec | None = None,
        allow_empty: bool = True,
        # Alternative
        show_alternative_title: bool = False,
        on_change: str | None = None,
        # ValueSpec
        title: str | None = None,
        help: ValueSpecHelp | None = None,
        default_value: ValueSpecDefault[Any] = DEF_VALUE,
        validate: ValueSpecValidateFunc[Any] | None = None,
    ):
        vs_text = (
            TextInput(
                title=_("Explicit match"),
                size=49,
                allow_empty=allow_empty,
            )
            if text_valuespec is None
            else text_valuespec
        )
        vs_regex = RegExp(
            mode=RegExp.prefix,
            title=_("Regular expression match"),
            size=49,
            allow_empty=allow_empty,
        )
        super().__init__(
            elements=[
                vs_text,
                Transform(
                    valuespec=vs_regex,
                    to_valuespec=lambda v: (None if v is None else v[1:]),  # strip off "~"
                    from_valuespec=lambda v: "~" + v,  # add "~"
                ),
            ],
            # Use RegExp field when value is prefixed with "~"
            match=lambda v: 1 if v and v[0] == "~" else 0,
            show_alternative_title=show_alternative_title,
            on_change=on_change,
            orientation="horizontal",
            title=title,
            help=help,
            default_value=default_value,
            validate=validate,
        )


TextOrRegExpUnicode = TextOrRegExp  # alias added in 2.1.0 for compatibility


LabelsModel = Mapping[str, str]


class Labels(ValueSpec[LabelsModel]):
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
        world: "Labels.World",
        # https://github.com/python/cpython/issues/90015
        label_source: "Labels.Source | None" = None,
        max_labels: int | None = None,
        # ValueSpec
        title: str | None = None,
        help: ValueSpecHelp | None = None,
        default_value: ValueSpecDefault[LabelsModel] = DEF_VALUE,
        validate: ValueSpecValidateFunc[LabelsModel] | None = None,
    ):
        super().__init__(title=title, help=help, default_value=default_value, validate=validate)
        self._world = world
        # Set this source to mark the labels that have no explicit label source set
        self._label_source = label_source
        # Set to positive integer to limit the number of labels to add to this field
        self._max_labels = max_labels

    def help(self) -> str | HTML | None:
        h = super().help()
        return escaping.escape_to_html_permissive(
            ("" if h is None else str(h)) + label_help_text(), escape_links=False
        )

    def canonical_value(self) -> LabelsModel:
        return {}

    def from_html_vars(self, varprefix: str) -> LabelsModel:
        value = request.get_str_input_mandatory(varprefix, "[]")
        return self._from_html_vars(value, varprefix)

    def _from_html_vars(self, value: str, varprefix: str) -> LabelsModel:
        try:
            return {label.id: label.value for label in parse_labels_value(value)}
        except ValueError as e:
            raise MKUserError(varprefix, "%s" % e)

    def _validate_value(self, value: LabelsModel, varprefix: str) -> None:
        if not isinstance(value, dict):
            raise MKUserError(
                varprefix,
                _("The value is not of type dict."),
            )
        for k, v in value.items():
            if not isinstance(k, str):
                raise MKUserError(
                    varprefix,
                    _("The label ID %r is of type %s, but should be %s") % (k, type(k), str),
                )
            if not isinstance(v, str):
                raise MKUserError(
                    varprefix,
                    _("The label value %r is of type %s, but should be %s") % (k, type(v), str),
                )

    def mask(self, value: LabelsModel) -> LabelsModel:
        return value

    def value_to_html(self, value: LabelsModel) -> ValueSpecText:
        label_sources: LabelSources = (
            {k: self._label_source.value for k in value} if self._label_source else {}
        )
        return render_labels(
            value,
            "host",
            with_links=False,
            label_sources=label_sources,
            request=request,
        )

    def render_input(self, varprefix: str, value: LabelsModel) -> None:
        html.help(self.help())
        label_type = "host_label" if "host_label" in varprefix else "service_label"
        html.text_input(
            varprefix,
            default_value=encode_labels_for_http(value.items()),
            cssclass="labels" + " " + label_type,
            placeholder=_("Add some label"),
            data_attrs={
                "data-world": self._world.value,
                "data-max-labels": (None if self._max_labels is None else str(self._max_labels)),
            },
        )

    def value_to_json(self, value: LabelsModel) -> JSONValue:
        return value

    def value_from_json(self, json_value: JSONValue) -> LabelsModel:
        return json_value

    @classmethod
    def get_labels(cls, world: "Labels.World", search_label: str) -> Sequence[tuple[str, str]]:
        if world is cls.World.CONFIG:
            return get_labels_from_config(LabelType.ALL, search_label)

        if world is cls.World.CORE:
            return get_labels_from_core(LabelType.ALL, search_label)

        raise NotImplementedError()


AndOrNotDropdownValue = tuple[AndOrNotLiteral, T | None]
ListOfAndOrNotDropdownValue = Sequence[AndOrNotDropdownValue]


class AndOrNotDropdown(DropdownChoice):
    def __init__(  # pylint: disable=redefined-builtin
        self,
        valuespec: ValueSpec,
        choices: DropdownChoices | None = None,
        vs_label: str | None = None,
    ):
        super().__init__(
            choices=choices or [],
            encode_value=False,
        )

        self._valuespec = valuespec
        self._default_value: AndOrNotDropdownValue = ("and", valuespec.default_value())
        self._vs_label = vs_label

    def _varprefixes(self, varprefix: str) -> tuple[str, str]:
        return (varprefix + "_bool", varprefix + "_vs")

    def render_input(self, varprefix: str, value: AndOrNotDropdownValue | None) -> None:
        varprefix_bool, varprefix_vs = self._varprefixes(varprefix)
        value = value if value else self._default_value

        html.open_div(class_=["bool"])
        if self._vs_label and not self._choices:
            html.span(self._vs_label, class_=["vs_label"])
            html.hidden_field(varprefix_bool, value[0] if value else None)
        else:
            super().render_input(varprefix_bool, value[0] if value else None)
        html.div("", class_=["line"])
        html.close_div()

        self._valuespec.render_input(varprefix_vs, value[1])

    def from_html_vars(self, varprefix: str) -> AndOrNotDropdownValue | None:
        varprefix_bool, varprefix_vs = self._varprefixes(varprefix)
        bool_val: AndOrNotLiteral = super().from_html_vars(varprefix_bool)  # type: ignore[assignment]
        vs_val = self._valuespec.from_html_vars(varprefix_vs)
        return (bool_val, vs_val)

    def validate_datatype(self, value: AndOrNotDropdownValue | None, varprefix: str) -> None:
        if value is None:
            return

        varprefix_bool, varprefix_vs = self._varprefixes(varprefix)
        # Validate datatype of AndOrNotLiteral: value[0]
        super().validate_datatype(value[0], varprefix_bool)

        # Validate datatype of valuespec: value[1]
        vs_validate_datatype = getattr(self._valuespec, "validate_datatype", None)
        if callable(vs_validate_datatype):
            vs_validate_datatype(value[1], varprefix_vs)

    def _validate_value(self, value: AndOrNotDropdownValue | None, varprefix: str) -> None:
        if value is None:
            return

        varprefix_bool, varprefix_vs = self._varprefixes(varprefix)
        # Validate value of AndOrNotLiteral: value[0]
        super()._validate_value(value[0], varprefix_bool)

        # Validate value of valuespec: value[1]
        vs_validate_value = getattr(self._valuespec, "_validate_value", None)
        if callable(vs_validate_value):
            vs_validate_value(value[1], varprefix_vs)


class _SingleLabel(AjaxDropdownChoice):
    ident: str = "label"

    def __init__(  # pylint: disable=redefined-builtin
        self,
        world: Labels.World,
        label_source: Labels.Source | None = None,
        strict: Literal["True", "False"] = "False",
        # DropdownChoice
        on_change: str | None = None,
    ):
        super().__init__(
            regex=cmk.utils.regex.regex(LABEL_REGEX),
            regex_error=_(
                'Labels need to be in the format "[KEY]:[VALUE]". For example "os:windows".'
            ),
            autocompleter=AutocompleterConfig(
                ident=self.ident,
                dynamic_params_callback_name="label_autocompleter",
            ),
            strict=strict,
            html_attrs={"data-world": world.value},
            on_change=(on_change if on_change else "cmk.valuespecs.single_label_on_change(this)"),
            cssclass=self.ident,
            default_value="",
        )


class LabelGroup(ListOf):
    _ident: str = "label_group"
    _choices: DropdownChoices = [("and", "and"), ("or", "or"), ("not", "not")]
    _first_element_choices: DropdownChoices = [("and", "is"), ("not", "is not")]
    _first_element_label: str | None = None
    _sub_vs: ValueSpec = _SingleLabel(world=Labels.World.CORE)
    _magic: str = "@:@"  # Used by ListOf class to count through entries

    def __init__(  # pylint: disable=redefined-builtin
        self,
        show_empty_group_by_default: bool = True,
        # ListOf
        add_label: str | None = None,
        # ValueSpec
        title: str | None = None,
        help: ValueSpecHelp | None = None,
    ) -> None:
        super().__init__(
            valuespec=AndOrNotDropdown(
                valuespec=self._sub_vs,
                choices=self._choices,
            ),
            first_element_vs=AndOrNotDropdown(
                valuespec=self._sub_vs,
                choices=self._first_element_choices,
                vs_label=self._first_element_label,
            ),
            magic=self._magic,
            add_label=add_label if add_label is not None else _("Add to query"),
            del_label=self.del_label,
            add_icon="plus",
            ignore_complain=True,
            movable=False,
            default_value=[("and", self._sub_vs.default_value())],
            title=title,
            help=help,
        )
        self._show_empty_group_by_default = show_empty_group_by_default

    @property
    def del_label(self) -> str:
        return _("Remove this label")

    def render_input(
        self,
        varprefix: str,
        value: ListOfAndOrNotDropdownValue,
    ) -> None:
        html.open_div(class_=self._ident)
        super().render_input(varprefix, value)
        html.close_div()

    def _del_button(self, vp: str, nr: str) -> None:
        choices_or_label: DropdownChoices | str = (
            self._first_element_choices or self._first_element_label or self._choices
        )
        js = (
            f"cmk.valuespecs.label_group_delete({json.dumps(vp)}, {json.dumps(nr)},"
            f"{json.dumps(choices_or_label)}, {json.dumps(self._show_empty_group_by_default)});"
        )
        html.icon_button("#", self._del_label, "close", onclick=js, class_=["delete_button"])

    def title(self) -> str | None:
        if self._title:
            return self._title
        return self._valuespec.title()


class LabelGroups(LabelGroup):
    _ident: str = "label_groups"
    _choices: DropdownChoices = [("and", "and"), ("or", "or"), ("not", "not")]
    _first_element_choices: DropdownChoices = []
    _first_element_label: str | None = "Label"
    _sub_vs: ValueSpec = LabelGroup()
    _magic: str = "@!@"  # Used by ListOf class to count through entries

    def __init__(  # pylint: disable=redefined-builtin
        self,
        show_empty_group_by_default: bool = True,
        # ListOf
        add_label: str | None = None,
        # ValueSpec
        title: str | None = None,
        help: ValueSpecHelp | None = None,
    ) -> None:
        super().__init__(
            show_empty_group_by_default,
            add_label,
            title,
            help,
        )
        self._default_value: ListOfAndOrNotDropdownValue = (
            [("and", [("and", "")])] if show_empty_group_by_default else []
        )

    @property
    def del_label(self) -> str:
        return _("Remove this label group")

    def render_input(self, varprefix: str, value: ListOfAndOrNotDropdownValue) -> None:
        if request.has_var(varprefix + "_count"):
            value = self.from_html_vars(varprefix)
        value = self._add_empty_row_to_groups(value)
        super().render_input(varprefix, value)
        html.final_javascript(f"cmk.forms.remove_label_filter_hidden_fields('{varprefix}');")

    def _add_empty_row_to_groups(
        self, value: ListOfAndOrNotDropdownValue
    ) -> ListOfAndOrNotDropdownValue:
        if not value:
            return self._default_value

        for _group_operator, label_group in value:
            if label_group and label_group[-1] != ("and", ""):
                label_group.append(("and", ""))
        return value

    def from_html_vars(self, varprefix: str) -> ListOfAndOrNotDropdownValue:
        return parse_label_groups_from_http_vars(varprefix, dict(request.itervars(varprefix)))


# https://github.com/python/mypy/issues/12368
IconSelectorModel = None | Icon


class IconSelector(ValueSpec[IconSelectorModel]):
    def __init__(  # pylint: disable=redefined-builtin
        self,
        allow_empty: bool = True,
        empty_img: str = "empty",
        show_builtin_icons: bool = True,
        with_emblem: bool = True,
        # ValueSpec
        title: str | None = None,
        help: ValueSpecHelp | None = None,
        default_value: ValueSpecDefault[IconSelectorModel] = DEF_VALUE,
        validate: ValueSpecValidateFunc[IconSelectorModel] | None = None,
    ):
        super().__init__(title=title, help=help, default_value=default_value, validate=validate)
        self._allow_empty = allow_empty
        self._empty_img = empty_img
        self._show_builtin_icons = show_builtin_icons
        self._with_emblem = with_emblem
        self._exclude = [
            "trans",
            "empty",
        ]

    def allow_empty(self) -> bool:
        return self._allow_empty

    @classmethod
    def categories(cls) -> Iterable[tuple[str, str]]:
        return active_config.wato_icon_categories

    @classmethod
    def category_alias(cls, category_name: str) -> str:
        return dict(cls.categories()).get(category_name, category_name)

    # All icons within the images/icons directory have the ident of a category
    # witten in the PNG meta data. For the default images we have done this scripted.
    # During upload of user specific icons, the meta data is added to the images.
    def available_icons(self, only_local: bool = False) -> Mapping[str, str]:
        icons: dict[str, str] = {}
        icons.update(self._available_builtin_icons("icon_", only_local))
        icons.update(self._available_user_icons(only_local))
        return icons

    def available_emblems(self, only_local: bool = False) -> Mapping[str, str]:
        return self._available_builtin_icons("emblem_", only_local)

    def _available_builtin_icons(self, prefix: str, only_local: bool = False) -> Mapping[str, str]:
        if not self._show_builtin_icons:
            return {}

        icons = {}
        for theme_id in theme.icon_themes():
            dirs = [Path(cmk.utils.paths.local_web_dir) / "htdocs/themes" / theme_id / "images"]
            if not only_local:
                dirs.append(Path(cmk.utils.paths.web_dir) / "htdocs/themes" / theme_id / "images")

            for file_stem, category in self._get_icons_from_directories(
                dirs, default_category="builtin"
            ).items():
                if file_stem.startswith(prefix):
                    icons[file_stem[len(prefix) :]] = category
        return icons

    def _available_user_icons(self, only_local: bool = False) -> Mapping[str, str]:
        dirs = [Path(cmk.utils.paths.local_web_dir) / "htdocs/images/icons"]
        if not only_local:
            dirs.append(Path(cmk.utils.paths.web_dir) / "htdocs/images/icons")

        return self._get_icons_from_directories(dirs, default_category="misc")

    def _get_icons_from_directories(
        self, dirs: Iterable[Path], default_category: str
    ) -> Mapping[str, str]:
        icons: dict[str, str] = {}
        for directory in dirs:
            try:
                files = [f for f in directory.iterdir() if f.is_file()]
            except OSError:
                continue

            for file_ in files:
                if file_.suffix == ".png":
                    try:
                        category = self._extract_category_from_png(file_, default_category)
                    except OSError as e:
                        if "%s" % e == "cannot identify image file":
                            continue  # silently skip invalid files
                        raise
                elif file_.suffix == ".svg":
                    # users are not able to add SVGs and our builtin SVGs don't have a category
                    category = default_category
                else:
                    continue

                icons[file_.stem] = category

        for exclude in self._exclude:
            icons.pop(exclude, None)

        return icons

    def _extract_category_from_png(self, file_path: Path, default: str) -> str:
        # extract the category from the meta data
        image = CMKImage.from_path(file_path, ImageType.PNG)
        category = image.get_comment()
        valid_categories = {k for k, _v in self.categories()}
        if category not in valid_categories:
            return default
        return category

    def _available_icons_by_category(
        self, icons: Mapping[str, str]
    ) -> Sequence[tuple[str, str, Sequence[str]]]:
        by_cat: dict[str, list[str]] = {}
        for icon_name, category_name in icons.items():
            by_cat.setdefault(category_name, [])
            by_cat[category_name].append(icon_name)

        categories = list(self.categories())
        if self._show_builtin_icons:
            categories.append(("builtin", _("Built-in")))

        icon_categories = []
        for category_name, category_alias in categories:
            if category_name in by_cat:
                icon_categories.append((category_name, category_alias, by_cat[category_name]))
        return icon_categories

    def _render_icon(self, icon: str, onclick: str = "", title: str = "", id_: str = "") -> HTML:
        if not icon:
            icon = self._empty_img

        if id_.endswith("_emblem_img"):
            icon_tag = html.render_emblem(icon, title=title, id_=id_)
            html.write_text_permissive(" + ")
        else:
            icon_tag = html.render_icon(icon, title=title, id_=id_)

        if onclick:
            icon_tag = HTMLWriter.render_a(icon_tag, href="javascript:void(0)", onclick=onclick)

        return icon_tag

    def _transform_icon_str(self, value: IconSelectorModel) -> _Icon:
        if isinstance(value, dict):
            return value
        return {"icon": "empty" if value is None else value, "emblem": None}

    def render_input(self, varprefix: str, value: IconSelectorModel) -> None:
        icon_dict = self._transform_icon_str(value)

        self._render_input(varprefix, icon_dict["icon"])
        if self._with_emblem:
            self._render_input(varprefix + "_emblem", icon_dict["emblem"])

    def _render_input(self, varprefix: str, value: str | None) -> None:
        # Handle complain phase with validation errors correctly and get the value
        # from the HTML vars
        if value is None:
            value = request.var(varprefix + "_value")

        if not value:
            value = self._empty_img

        html.hidden_field(varprefix + "_value", value or "", varprefix + "_value", add_var=True)

        if value:
            is_emblem = varprefix.endswith("emblem")
            selection_text = _("Choose another %s") % ("Emblem" if is_emblem else "Icon")
            content = self._render_icon(value, "", selection_text, id_=varprefix + "_img")
        else:
            content = HTML.with_escaping(_("Select an Icon"))

        html.popup_trigger(
            content,
            varprefix + "_icon_selector",
            MethodAjax(
                endpoint="icon_selector",
                url_vars=[
                    ("value", value),
                    ("varprefix", varprefix),
                    ("allow_empty", "1" if self._allow_empty else "0"),
                    ("show_builtin_icons", "1" if self._show_builtin_icons else "0"),
                    ("back", makeuri(request, [])),
                ],
            ),
            resizable=True,
        )

    def render_popup_input(self, varprefix: str, value: str | None) -> None:
        html.open_div(class_="icons", id_="%s_icons" % varprefix)

        is_emblem = varprefix.endswith("_emblem")
        icons_name_and_cat = self.available_emblems() if is_emblem else self.available_icons()
        available_icons = self._available_icons_by_category(icons_name_and_cat)
        default_category = available_icons[0][0]
        active_category = (
            default_category if value is None else icons_name_and_cat.get(value, default_category)
        )

        # Render tab navigation
        html.open_ul()
        for category_name, category_alias, _icons in available_icons:
            html.open_li(class_="active" if active_category == category_name else None)
            html.a(
                category_alias,
                href=f"javascript:cmk.valuespecs.iconselector_toggle({json.dumps(varprefix)}, {json.dumps(category_name)})",
                id_=f"{varprefix}_{category_name}_nav",
                class_="%s_nav" % varprefix,
            )
            html.close_li()
        html.close_ul()

        # Now render the icons grouped by category
        empty = ["empty"] if self._allow_empty or is_emblem else []
        for category_name, category_alias, icons in available_icons:
            html.open_div(
                id_=f"{varprefix}_{category_name}_container",
                class_=["icon_container", "%s_container" % varprefix],
                style="display:none;" if active_category != category_name else None,
            )

            for icon in empty + sorted(icons):
                html.open_a(
                    href=None,
                    class_="icon",
                    onclick=f"cmk.valuespecs.iconselector_select(event, {json.dumps(varprefix)}, {json.dumps(icon)})",
                    title=icon,
                )

                icon_path = (
                    theme.detect_icon_path(icon, prefix="emblem_")
                    if is_emblem and icon != "empty"
                    else icon
                )
                html.write_html(
                    self._render_icon(icon_path, id_=varprefix + "_i_" + icon, title=icon)
                )

                html.span(icon)

                html.close_a()

            html.close_div()

        html.open_div(class_="buttons")

        html.jsbutton(
            "_toggle_names",
            _("Toggle names"),
            onclick="cmk.valuespecs.iconselector_toggle_names(event, %s)" % json.dumps(varprefix),
        )

        if user.may("wato.icons"):
            back_param = (
                "&back=" + urlencode(request.get_url_input("back"))
                if request.has_var("back")
                else ""
            )
            html.buttonlink("wato.py?mode=icons" + back_param, _("Manage"))

        html.close_div()

        html.close_div()

    def canonical_value(self) -> IconSelectorModel:
        return None

    def from_html_vars(self, varprefix: str) -> IconSelectorModel:
        icon = self._from_html_vars(varprefix)
        if not self._with_emblem:
            return icon

        emblem = self._from_html_vars(varprefix + "_emblem")
        if not emblem:
            return icon

        return {"icon": "empty" if icon is None else icon, "emblem": emblem}

    def _from_html_vars(self, varprefix: str) -> str | None:
        icon = request.var(varprefix + "_value")
        if icon == "empty":
            return None
        return icon

    def mask(self, value: IconSelectorModel) -> IconSelectorModel:
        return value

    def value_to_html(self, value: IconSelectorModel) -> ValueSpecText:
        return self._render_icon(self._transform_icon_str(value)["icon"])

    def value_to_json(self, value: Any) -> JSONValue:
        return value

    def value_from_json(self, json_value: JSONValue) -> IconSelectorModel:
        return json_value

    def validate_datatype(self, value: IconSelectorModel, varprefix: str) -> None:
        if value is not None and self._with_emblem and not isinstance(value, (str, dict)):
            raise MKUserError(varprefix, "The type is %s, but should be str or dict" % type(value))
        if value is not None and not self._with_emblem and not isinstance(value, str):
            raise MKUserError(varprefix, "The type is %s, but should be str or dict" % type(value))

        icon_dict = self._transform_icon_str(value)
        if not (icon_dict["icon"] is None or isinstance(icon_dict["icon"], str)):
            raise MKUserError(
                varprefix,
                _("The icon type is %s, but should be str") % type(icon_dict["icon"]),
            )
        if not (icon_dict["emblem"] is None or isinstance(icon_dict["emblem"], str)):
            raise MKUserError(
                varprefix,
                _("The emblem type is %s, but should be str") % type(icon_dict["emblem"]),
            )

    def _validate_value(self, value: IconSelectorModel, varprefix: str) -> None:
        icon_dict = self._transform_icon_str(value)

        if not self._allow_empty and (not icon_dict["icon"] or icon_dict["icon"] == "empty"):
            raise MKUserError(varprefix, _("You need to select an icon."))

        if icon_dict["icon"] and icon_dict["icon"] not in self.available_icons():
            raise MKUserError(varprefix, _("The selected icon does not exist."))

        if icon_dict["emblem"] and icon_dict["emblem"] not in self.available_emblems():
            raise MKUserError(varprefix, _("The selected emblem does not exist."))


def ListOfTimeRanges(  # pylint: disable=redefined-builtin
    # ListOf
    totext: str | None = None,
    text_if_empty: str | None = None,
    allow_empty: bool = True,
    empty_text: str | None = None,
    sort_by: int | None = None,
    # ValueSpec
    title: str | None = None,
    help: ValueSpecHelp | None = None,
    default_value: ValueSpecDefault[ListOfModel[TimeofdayRangeValue]] = DEF_VALUE,
    validate: ValueSpecValidateFunc[ListOfModel[TimeofdayRangeValue]] | None = None,
) -> ListOf:
    return ListOf(
        valuespec=TimeofdayRange(allow_empty=True),
        magic="#!#",
        add_label=_("Add time range"),
        del_label=_("Delete time range"),
        movable=False,
        style=ListOf.Style.FLOATING,
        totext=totext,
        text_if_empty=text_if_empty,
        allow_empty=allow_empty,
        empty_text=empty_text,
        sort_by=sort_by,
        title=title,
        help=help,
        default_value=default_value,
        validate=validate,
    )


def Fontsize(  # pylint: disable=redefined-builtin
    # Float
    decimal_separator: str = ".",
    allow_int: bool = False,
    # Integer
    minvalue: float | None = None,
    maxvalue: float | None = None,
    label: str | None = None,
    display_format: str = "%.2f",
    align: Literal["left", "right"] = "left",
    # ValueSpec
    title: str | None = None,
    help: ValueSpecHelp | None = None,
    default_value: ValueSpecDefault[float] = 10,  # NOTE: Different!
    validate: ValueSpecValidateFunc[float] | None = None,
) -> Float:
    return Float(
        decimal_separator=decimal_separator,
        allow_int=allow_int,
        size=5,
        minvalue=minvalue,
        maxvalue=maxvalue,
        label=label,
        unit=_("pt"),
        display_format=display_format,
        align=align,
        title=_("Font size") if title is None else title,
        help=help,
        default_value=default_value,
        validate=validate,
    )


class Color(ValueSpec[None | str]):
    def __init__(  # pylint: disable=redefined-builtin
        self,
        on_change: str | None = None,
        allow_empty: bool = True,
        # ValueSpec
        title: str | None = None,
        help: ValueSpecHelp | None = None,
        default_value: ValueSpecDefault[str | None] = DEF_VALUE,
        validate: ValueSpecValidateFunc[str | None] | None = None,
    ):
        # TODO: Should this actually subclass TextInput?
        # kwargs["regex"] = "#[0-9]{3,6}"
        # kwargs["regex_error"] = _("The color needs to be given in hex format.")
        super().__init__(title=title, help=help, default_value=default_value, validate=validate)
        self._on_change = on_change
        self._allow_empty = allow_empty

    def allow_empty(self) -> bool:
        return self._allow_empty

    def render_input(self, varprefix: str, value: str | None) -> None:
        if not value:
            value = "#FFFFFF"

        # Holds the actual value for form submission
        html.hidden_field(varprefix + "_value", value or "", varprefix + "_value", add_var=True)

        indicator = HTMLWriter.render_div(
            "",
            id_="%s_preview" % varprefix,
            class_="cp-preview",
            style="background-color:%s" % value,
        )

        html.popup_trigger(
            indicator,
            varprefix + "_popup",
            MethodColorpicker(varprefix, value),
            cssclass=["colorpicker"],
            onclose=self._on_change,
        )

    def mask(self, value: str | None) -> str | None:
        return value

    def canonical_value(self) -> str | None:
        return None

    def from_html_vars(self, varprefix: str) -> str | None:
        color = request.var(varprefix + "_value")
        if color == "":
            return None
        return color

    def value_to_html(self, value: str | None) -> ValueSpecText:
        return "" if value is None else value

    def value_to_json(self, value: str | None) -> JSONValue:
        return value

    def value_from_json(self, json_value: JSONValue) -> str | None:
        return json_value

    def validate_datatype(self, value: str | None, varprefix: str) -> None:
        if value is not None and not isinstance(value, str):
            raise MKUserError(varprefix, _("The type is %s, but should be str") % type(value))

    def _validate_value(self, value: str | None, varprefix: str) -> None:
        if not self._allow_empty and not value:
            raise MKUserError(varprefix, _("You need to select a color."))


def ColorWithThemeOrMetricDefault(
    title: str,
    default_value: ValueSpecDefault[str],
) -> Alternative:
    return Alternative(
        title=title,
        elements=[
            FixedValue(
                value="default",
                title=_("Default color"),
                totext=_("Use the default color of the theme or the metric."),
            ),
            Color(title=_("Use the following color")),
        ],
        default_value=default_value,
    )


def ColorWithThemeAndMetricDefault(
    title: str,
    default_value: ValueSpecDefault[str],
) -> Alternative:
    return Alternative(
        title=title,
        elements=[
            FixedValue(
                value="default_theme",
                title=_("Default theme color"),
                totext=_("Use the default color of the theme."),
            ),
            FixedValue(
                value="default_metric",
                title=_("Default metric color"),
                totext=_("Use the default color of the metric."),
            ),
            Color(title=_("Use the following color")),
        ],
        default_value=default_value,
    )


type SSHPrivateKey = str
type SSHPublicKey = str
type SSHKeyPairValue = tuple[SSHPrivateKey, SSHPublicKey]


class SSHKeyPair(ValueSpec[None | SSHKeyPairValue]):
    """
    An SSH key pair consisting of (private key, public key)

    The None variant indicates that there is no keypair yet, and one will be generated
    when the form is saved.
    """

    def render_input(self, varprefix: str, value: SSHKeyPairValue | None) -> None:
        if value:
            html.write_text_permissive(_("Fingerprint: %s") % self.value_to_html(value))
            html.hidden_field(varprefix, self._encode_key_for_url(value), add_var=True)
        else:
            html.write_text_permissive(_("Key pair will be generated when you save."))

    def canonical_value(self) -> SSHKeyPairValue | None:
        return None

    def mask(self, value: SSHKeyPairValue | None) -> SSHKeyPairValue | None:
        return ("******", value[1]) if value is not None else None

    def value_to_html(self, value: SSHKeyPairValue | None) -> ValueSpecText:
        if value is None:
            return ""
        return self._get_key_fingerprint(value)

    def value_to_json(self, value: SSHKeyPairValue | None) -> JSONValue:
        if value is None:
            return []
        return [value[0], value[1]]

    def value_from_json(self, json_value: JSONValue) -> SSHKeyPairValue | None:
        if json_value == []:
            return None
        return (json_value[0], json_value[1])

    def from_html_vars(self, varprefix: str) -> SSHKeyPairValue:
        if request.has_var(varprefix):
            return self._decode_key_from_url(request.get_ascii_input_mandatory(varprefix))
        return self._generate_ssh_key()

    @staticmethod
    def _encode_key_for_url(value: SSHKeyPairValue) -> str:
        return (
            f"{base64.b64encode(Encrypter.encrypt(value[0])).decode('ascii')}|"
            f"{base64.b64encode(value[1].encode('ascii')).decode('ascii')}"
        )

    @staticmethod
    def _decode_key_from_url(text: str) -> SSHKeyPairValue:
        parts = text.split("|")
        if len(parts) != 2:
            raise ValueError("Invalid value: %r" % text)
        return (
            Encrypter.decrypt(base64.b64decode(parts[0].encode("ascii"))),
            base64.b64decode(parts[1]).decode("ascii"),
        )

    @staticmethod
    def _generate_ssh_key() -> SSHKeyPairValue:
        # TODO: This method is the only reason we have to offer rsa_dump_legacy_pkcs1. Can we use
        # dump_pem instead? The only difference is "-----BEGIN RSA PRIVATE KEY-----" (pkcs1) vs
        # "-----BEGIN PRIVATE KEY-----".
        key = keys.PrivateKey.generate_rsa(4096)
        private_key = key.rsa_dump_legacy_pkcs1().str
        public_key = key.public_key.dump_openssh()
        return (private_key, public_key)

    @classmethod
    def _get_key_fingerprint(cls, value: SSHKeyPairValue) -> str:
        _private_key, public_key = value
        key = base64.b64decode(public_key.strip().split()[1].encode("ascii"))
        fp_plain = hashlib.md5(key, usedforsecurity=False).hexdigest()
        return ":".join(a + b for a, b in zip(fp_plain[::2], fp_plain[1::2]))


def SchedulePeriod(  # pylint: disable=redefined-builtin
    from_end: bool = True,
    # CascadingDropdown
    label: str | None = None,
    separator: str = ", ",
    sorted: bool = True,
    render: CascadingDropdown.Render | None = None,
    no_elements_text: str | None = None,
    no_preselect_title: str | None = None,
    render_sub_vs_page_name: str | None = None,
    render_sub_vs_request_vars: dict | None = None,
    # ValueSpec
    help: ValueSpecHelp | None = None,
    default_value: ValueSpecDefault[CascadingDropdownChoiceValue] = DEF_VALUE,
    validate: ValueSpecValidateFunc[CascadingDropdownChoiceValue] | None = None,
) -> CascadingDropdown:
    if from_end:
        from_end_choice: list[CascadingDropdownChoice] = [
            (
                "month_end",
                _("At the end of every month on day"),
                Integer(minvalue=1, maxvalue=28, unit=_("from the end")),
            ),
        ]
    else:
        from_end_choice = []

    dwm: list[CascadingDropdownChoice] = [
        ("day", _("Every day"), None),
        ("week", _("Every week on..."), Weekday(title=_("Day of the week"))),
        (
            "month_begin",
            _("At the beginning of every month on day"),
            Integer(minvalue=1, maxvalue=28),
        ),
    ]
    return CascadingDropdown(
        choices=dwm + from_end_choice,
        label=label,
        separator=separator,
        sorted=sorted,
        orientation="horizontal",
        render=render,
        no_elements_text=no_elements_text,
        no_preselect_title=no_preselect_title,
        render_sub_vs_page_name=render_sub_vs_page_name,
        render_sub_vs_request_vars=render_sub_vs_request_vars,
        title=_("Period"),
        help=help,
        default_value=default_value,
        validate=validate,
    )


_CAInputModel = None | tuple[str, int, bytes]


class _CAInput(ValueSpec[_CAInputModel]):
    """Allows users to fetch CAs interactively so that they don't have to upload files or
    paste text manually."""

    def __init__(self) -> None:
        super().__init__(title=_("Fetch certificate from server"))
        self.address = HostAddress()
        self.port = NetworkPort(title=None)

    def render_input(self, varprefix: str, value: _CAInputModel) -> None:
        address, port, content = value or ("", 443, b"")

        self.address.render_input(varprefix + "_address", address)
        self.port.render_input(varprefix + "_port", port)
        html.icon_button(
            url=None,
            title=_("Fetch certificate from server"),
            icon="host",
            onclick="cmk.valuespecs.fetch_ca_from_server(%s)" % json.dumps(varprefix),
        )
        html.div(None, id_=varprefix + "_status")
        html.text_area(varprefix, content.decode("ascii"), cols=80, readonly="")

    def canonical_value(self) -> _CAInputModel:
        return None

    def mask(self, value: _CAInputModel) -> _CAInputModel:
        return value

    def value_to_json(self, value: _CAInputModel) -> JSONValue:
        return None if value is None else [value[0], value[1], value[2].decode("ascii")]

    def value_from_json(self, json_value: JSONValue) -> _CAInputModel:
        return (
            None
            if json_value is None
            else (json_value[0], json_value[1], json_value[2].encode("ascii"))
        )

    def from_html_vars(self, varprefix: str) -> _CAInputModel:
        address = self.address.from_html_vars(varprefix + "_address")
        port = self.port.from_html_vars(varprefix + "_port")
        content = request.get_binary_input_mandatory(varprefix)
        return (address, port, content)


def CertificateWithPrivateKey(  # pylint: disable=redefined-builtin
    *,
    title: str | None = None,
    help: ValueSpecHelp | None = None,
) -> Tuple:
    """A single certificate with a matching private key."""

    def _validate_private_key(value: str, varprefix: str) -> None:
        if value.startswith("-----BEGIN ENCRYPTED PRIVATE KEY"):
            raise MKUserError(varprefix, _("Encrypted private keys are not supported"))

        try:
            keys.PrivateKey.load_pem(keys.PlaintextPrivateKeyPEM(value))
        except Exception:
            raise MKUserError(varprefix, _("Invalid private key"))

    def _validate_certificate(value: str, varprefix: str) -> None:
        try:
            certificate.Certificate.load_pem(certificate.CertificatePEM(value))
        except Exception:
            raise MKUserError(varprefix, _("Invalid certificate"))

    return Tuple(
        elements=[
            TextAreaUnicode(
                allow_empty=False,
                title="Private key",
                validate=_validate_private_key,
            ),
            TextAreaUnicode(
                allow_empty=False,
                title="Certificate",
                validate=_validate_certificate,
            ),
        ],
        title=title,
        help=help,
    )


class _CAorCAChain(UploadOrPasteTextFile):
    def __init__(  # pylint: disable=redefined-builtin
        self,
        # UploadOrPasteTextFile
        file_title: str | None = None,
        allow_empty: bool = False,
        # Alternative
        show_alternative_title: bool = False,
        on_change: str | None = None,
        orientation: Literal["horizontal", "vertical"] = "vertical",
        # ValueSpec
        title: str | None = None,
        help: ValueSpecHelp | None = None,
        default_value: ValueSpecDefault[Any] = DEF_VALUE,
        validate: ValueSpecValidateFunc[Any] | None = None,
    ):
        super().__init__(
            file_title=_("CRT/PEM File") if file_title is None else file_title,
            allow_empty=allow_empty,
            elements=[_CAInput()],
            mime_types=[
                "application/x-x509-user-cert",
                "application/x-x509-ca-cert",
                "application/pkix-cert",
            ],
            allowed_extensions=[".pem", ".crt"],
            match=lambda val: (
                2 if not isinstance(val, tuple) else (0 if isinstance(val[1], int) else 1)
            ),
            show_alternative_title=show_alternative_title,
            on_change=on_change,
            orientation=orientation,
            title=(
                _("Certificate Chain (Root / Intermediate Certificate)") if title is None else title
            ),
            help=help,
            default_value=default_value,
            validate=validate,
        )

    @staticmethod
    def _analyse_cert(cert: certificate.Certificate) -> dict[str, str]:
        """
        Inspect the certificate and place selected info in a dict.
        """

        return {
            "issuer": cert.issuer.rfc4514_string(),
            "subject": cert.subject.rfc4514_string(),
            "creation": cert.not_valid_before.date().isoformat(),
            "expiration": cert.not_valid_after.date().isoformat(),
            "fingerprint": cert.fingerprint(HashAlgorithm.Sha256).hex(sep=":").upper(),
        }

    def _validate_value(self, value: Any, varprefix: str) -> None:
        # value is really str | bytes, but UploadOrPasteTextFile doesn't know this
        try:
            # make sure the PEM can be loaded
            certificate.Certificate.load_pem(certificate.CertificatePEM(value))
        except Exception as e:
            raise MKUserError(varprefix, _("Invalid certificate file: %s") % e)

    def value_to_html(self, value: Any) -> ValueSpecText:
        # value is really str | bytes, but UploadOrPasteTextFile doesn't know this
        cert_info = self._analyse_cert(
            certificate.Certificate.load_pem(certificate.CertificatePEM(value))
        )
        show_info = {k: HTML.with_escaping(cert_info[k]) for k in ("issuer", "subject")}
        show_info["fingerprint"] = HTMLWriter.render_span(
            cert_info["fingerprint"][:41], title=cert_info["fingerprint"]
        )
        show_info["validity"] = HTML.without_escaping(
            _("Not Before: %s - Not After: %s")
            % (
                cert_info["creation"],
                cert_info["expiration"],
            )
        )
        rows = []
        for what, title in [
            ("issuer", _("Issuer")),
            ("subject", _("Subject")),
            ("validity", _("Validity")),
            ("fingerprint", _("Fingerprint")),
        ]:
            rows.append(
                HTMLWriter.render_tr(
                    HTMLWriter.render_td("%s:" % title) + HTMLWriter.render_td(show_info[what])
                )
            )
        return HTMLWriter.render_table(HTML.empty().join(rows))


def ListOfCAs(  # pylint: disable=redefined-builtin
    # ListOf
    magic: str = "@!@",
    add_label: str | None = None,
    del_label: str | None = None,
    style: ListOf.Style | None = None,
    totext: str | None = None,
    text_if_empty: str | None = None,
    allow_empty: bool = False,  # NOTE: Different!
    empty_text: str | None = None,
    sort_by: int | None = None,
    # ValueSpec
    title: str | None = None,
    help: ValueSpecHelp | None = None,
    default_value: ValueSpecDefault[ListOfModel[T]] = DEF_VALUE,
    validate: ValueSpecValidateFunc[ListOfModel[T]] | None = None,
) -> ListOf:
    return ListOf(
        valuespec=_CAorCAChain(),
        magic=magic,
        add_label=(_("Add new CA certificate or chain") if add_label is None else add_label),
        del_label=del_label,
        movable=False,
        style=style,
        totext=totext,
        text_if_empty=text_if_empty,
        allow_empty=allow_empty,
        empty_text=(
            _("You need to enter at least one CA. Otherwise no SSL connection can be made.")
            if empty_text is None
            else empty_text
        ),
        sort_by=sort_by,
        title=_("CAs to accept") if title is None else title,
        help=(
            _(
                "Only accepting HTTPS connections with a server which certificate "
                "is signed with one of the CAs that are listed here. That way it is guaranteed "
                "that it is communicating only with the authentic server. "
                "If you use self signed certificates for you server then enter that certificate "
                "here."
            )
            if help is None
            else help
        ),
        default_value=default_value,
        validate=validate,
    )


# TODO: Change to factory
class SetupSiteChoice(DropdownChoice):
    """Select configured sites in distributed setups

    This valuespec explicitly only cares about sites known to Setup. Pure status sites are excluded
    from this list.
    """

    def __init__(  # pylint: disable=redefined-builtin
        self,
        # DropdownChoice
        sorted: bool = False,
        label: str | None = None,
        help_separator: str | None = None,
        prefix_values: bool = False,
        empty_text: str | None = None,
        invalid_choice: DropdownInvalidChoice = "complain",
        invalid_choice_error: str | None = None,
        no_preselect_title: str | None = None,
        on_change: str | None = None,
        read_only: bool = False,
        encode_value: bool = True,
        html_attrs: HTMLTagAttributes | None = None,
        # ValueSpec
        title: str | None = None,
        help: ValueSpecHelp | None = None,
        default_value: ValueSpecDefault[SiteId] = DEF_VALUE,
        validate: ValueSpecValidateFunc[SiteId | None] | None = None,
        deprecated_choices: Sequence[SiteId] = (),
    ):
        super().__init__(
            choices=user_sites.get_activation_site_choices,
            sorted=sorted,
            label=label,
            help_separator=help_separator,
            prefix_values=prefix_values,
            empty_text=empty_text,
            invalid_choice=invalid_choice,
            invalid_choice_title=_("Unknown site (%s)"),
            invalid_choice_error=(
                _("The configured site is not known to this site.")
                if invalid_choice_error is None
                else invalid_choice_error
            ),
            no_preselect_title=no_preselect_title,
            on_change=on_change,
            read_only=read_only,
            encode_value=encode_value,
            html_attrs=html_attrs,
            title=_("Site") if title is None else title,
            help=help,
            default_value=(
                self._site_default_value if isinstance(default_value, Sentinel) else default_value
            ),
            validate=validate,
            deprecated_choices=deprecated_choices,
        )

    def _site_default_value(self):
        if site_config.is_wato_slave_site():
            # Placeholder for "central site". This is only relevant when using Setup on a remote site
            # and a host / folder has no site set.
            return ""

        default_value = user_sites.site_attribute_default_value()
        if default_value:
            return default_value
        return self.canonical_value()


def MonitoringSiteChoice() -> DropdownChoice:
    """Select a single site that is known as status remote site"""
    return DropdownChoice(
        title=_("Site"),
        choices=user_sites.get_configured_site_choices(),
    )


def LogLevelChoice(  # pylint: disable=redefined-builtin
    with_verbose: bool = True,
    # DropdownChoice
    sorted: bool = False,
    label: str | None = None,
    help_separator: str | None = None,
    prefix_values: bool = False,
    empty_text: str | None = None,
    invalid_choice: DropdownInvalidChoice = "complain",
    invalid_choice_title: str | None = None,
    invalid_choice_error: str | None = None,
    no_preselect_title: str | None = None,
    on_change: str | None = None,
    read_only: bool = False,
    encode_value: bool = True,
    html_attrs: HTMLTagAttributes | None = None,
    # ValueSpec
    title: str | None = None,
    help: ValueSpecHelp | None = None,
    default_value: ValueSpecDefault[int] = DEF_VALUE,
    validate: ValueSpecValidateFunc[int | None] | None = None,
    deprecated_choices: Sequence[int] = (),
) -> DropdownChoice:
    return DropdownChoice(
        choices=(
            [
                (logging.CRITICAL, _("Critical")),
                (logging.ERROR, _("Error")),
                (logging.WARNING, _("Warning")),
                (logging.INFO, _("Informational")),
                (cmk.utils.log.VERBOSE, _("Verbose")),
                (logging.DEBUG, _("Debug")),
            ]
            if with_verbose
            else [
                (logging.CRITICAL, _("Critical")),
                (logging.ERROR, _("Error")),
                (logging.WARNING, _("Warning")),
                (logging.INFO, _("Informational")),
                (logging.DEBUG, _("Debug")),
            ]
        ),
        sorted=sorted,
        label=label,
        help_separator=help_separator,
        prefix_values=prefix_values,
        empty_text=empty_text,
        invalid_choice=invalid_choice,
        invalid_choice_title=invalid_choice_title,
        invalid_choice_error=invalid_choice_error,
        no_preselect_title=no_preselect_title,
        on_change=on_change,
        read_only=read_only,
        encode_value=encode_value,
        html_attrs=html_attrs,
        title=title,
        help=help,
        default_value=(logging.INFO if isinstance(default_value, Sentinel) else default_value),
        validate=validate,
        deprecated_choices=deprecated_choices,
    )


def rule_option_elements(disabling: bool = True) -> list[DictionaryEntry]:
    elements: list[DictionaryEntry] = [
        (
            "description",
            TextInput(
                title=_("Description"),
                autocomplete="one-time-code",
                help=_(
                    "This field is intended for a brief description of the rule's purpose. "
                    "This description will be visible on the overview page of this rule set."
                ),
                size=80,
            ),
        ),
        ("comment", RuleComment()),
        ("docu_url", DocumentationURL()),
    ]
    if disabling:
        elements += [
            (
                "disabled",
                Checkbox(
                    title=_("Rule activation"),
                    help=_(
                        "A deactivated rule is not effective. However, it remains "
                        "in place so that it can be reactivated later, for example."
                    ),
                    label=_("do not apply this rule"),
                ),
            ),
        ]
    return elements


class RuleComment(TextAreaUnicode):
    def __init__(self) -> None:
        super().__init__(
            title=_("Comment"),
            help=_(
                "This field is intended for additional information that may help other "
                "users (and your future self) to understand the rule's purpose and the "
                "configured attributes. This comment is only visible in this dialog."
            ),
            rows=4,
            cols=80,
        )

    def render_input(self, varprefix: str, value: str | None) -> None:
        html.open_div(style="white-space: nowrap;")

        super().render_input(varprefix, value)

        date_and_user = "{} {}: ".format(time.strftime("%F", time.localtime()), user.id)

        html.nbsp()
        html.icon_button(
            None,
            title=_("Prefix the comment with the current date and your user name."),
            icon="insertdate",
            onclick="cmk.valuespecs.rule_comment_prefix_date_and_user(this, '%s');" % date_and_user,
        )
        html.close_div()


def DocumentationURL() -> TextInput:
    def _validate_documentation_url(value: str, varprefix: str) -> None:
        if is_allowed_url(value, cross_domain=True, schemes=["http", "https"]):
            return
        raise MKUserError(
            varprefix,
            _("Not a valid URL (Only http and https URLs are allowed)."),
        )

    return TextInput(
        title=_("Documentation URL"),
        autocomplete="one-time-code",
        help=HTML.without_escaping(
            _(
                "In this field you can add a URL linking to a page with related, "
                "useful information. You can use:<br>"
                "<ul>"
                "<li>an absolute URL starting with the protocol (<tt>http(s)://</tt>)</li>"
                "<li>or a relative URL either starting with a slash (<tt>/something</tt> "
                "will be resolved to <tt>https://mycheckmkserver/something</tt>) or without "
                "a slash (<tt>somethingelse</tt> will be resolved to "
                "<tt>https://mycheckmkserver/mysite/check_mk/somethingelse</tt>)</li>"
                "</ul>"
                "The link will be displayed as an icon in the description on the "
                "overview page of the related rule set."
            )
            % html.render_icon("url")
        ),
        size=80,
        validate=_validate_documentation_url,
    )


def type_name(v):
    try:
        return type(v).__name__
    except Exception:
        return escaping.escape_attribute(str(type(v)))


class DatePicker(ValueSpec[str]):
    def __init__(  # pylint: disable=redefined-builtin
        self,
        title: str | None = None,
        label: str | None = None,
        help: ValueSpecHelp | None = None,
        default_value: ValueSpecDefault[str] = DEF_VALUE,
        validate: ValueSpecValidateFunc[str] | None = None,
        onchange: str | None = None,
    ):
        self._onchange = onchange
        self._label = label
        super().__init__(
            title=title,
            label=label,
            help=help,
            default_value=default_value,
            validate=validate,
        )

    def render_input(self, varprefix: str, value: str) -> None:
        if self._label:
            html.span(self._label, class_="vs_floating_text")
        html.date(
            var=varprefix,
            value=value,
            id_="date_" + varprefix,
            onchange=self._onchange,
        )

    def canonical_value(self) -> str:
        return ""

    def from_html_vars(self, varprefix: str) -> str:
        return request.get_str_input_mandatory(varprefix)

    def mask(self, value: str) -> str:
        return value

    def value_from_json(self, json_value: JSONValue) -> str:
        return json_value

    def value_to_json(self, value: T) -> JSONValue:
        return value

    def validate_value(self, value: str, varprefix: str) -> None:
        try:
            dateutil.parser.isoparse(value)
        except ValueError as e:
            raise MKUserError(varprefix, _("Invalid date format: %s") % e) from e


class TimePicker(ValueSpec[str]):
    def __init__(  # pylint: disable=redefined-builtin
        self,
        title: str | None = None,
        help: ValueSpecHelp | None = None,
        default_value: ValueSpecDefault[str] = DEF_VALUE,
        validate: ValueSpecValidateFunc[str] | None = None,
        onchange: str | None = None,
    ):
        self._onchange = onchange
        super().__init__(
            title=title,
            help=help,
            default_value=default_value,
            validate=validate,
        )

    def render_input(self, varprefix: str, value: str) -> None:
        html.time(
            var=varprefix,
            value=value,
            id_="time_" + varprefix,
            onchange=self._onchange,
        )

    def canonical_value(self) -> str:
        return ""

    def from_html_vars(self, varprefix: str) -> str:
        return request.get_str_input_mandatory(varprefix)

    def mask(self, value: str) -> str:
        return value

    def value_from_json(self, json_value: JSONValue) -> str:
        return json_value

    def value_to_json(self, value: T) -> JSONValue:
        return value

    def validate_value(self, value: str, varprefix: str) -> None:
        try:
            time.strptime(value, "%H:%M")
        except ValueError as e:
            raise MKUserError(varprefix, _("Invalid time format: %s") % e) from e
