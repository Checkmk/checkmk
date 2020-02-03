#!/usr/bin/env python
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

from contextlib import contextmanager
from typing import Iterator, Union, List, Text  # pylint: disable=unused-import
import six

from cmk.gui.http import Response  # pylint: disable=unused-import
from cmk.gui.i18n import _
from cmk.gui.exceptions import MKGeneralException
from cmk.gui.utils.html import HTML

OutputFunnelInput = Union[str, Text, "HTML"]


class OutputFunnel(object):
    """
    Provides the write functionality. The method _lowlevel_write needs
    to be overwritten in the specific subclass!

     Usage of plugged context:
             with html.plugged():
                html.write("something")
                html_code = html.drain()
             print html_code
    """
    def __init__(self, response):
        # type: (Response) -> None
        super(OutputFunnel, self).__init__()
        self._response = response
        self.plug_text = []  # type: List[List[Text]]

    def write(self, text):
        # type: (OutputFunnelInput) -> None
        if not text:
            return

        if isinstance(text, HTML):
            text = "%s" % text

        if not isinstance(text, six.string_types):
            raise MKGeneralException(
                _('Type Error: html.write accepts str and unicode input objects only!'))

        if self._is_plugged():
            self.plug_text[-1].append(text)
        else:
            # encode when really writing out the data. Not when writing plugged,
            # because the plugged code will be handled somehow by our code. We
            # only encode when leaving the pythonic world.
            if isinstance(text, six.text_type):
                text = text.encode("utf-8")
            self._lowlevel_write(text)

    def _lowlevel_write(self, text):
        # type: (bytes) -> None
        self._response.stream.write(text)

    @contextmanager
    def plugged(self):
        # type: () -> Iterator[None]
        self.plug_text.append([])
        try:
            yield
        finally:
            text = self.drain()
            self.plug_text.pop()
            self.write(text)

    def _is_plugged(self):
        # type: () -> bool
        return bool(self.plug_text)

    def drain(self):
        # type: () -> Text
        """Get the sink content in order to do something with it."""
        if not self._is_plugged():  # TODO: Raise exception or even remove "if"?
            return ''

        text = "".join(self.plug_text.pop())
        self.plug_text.append([])
        return text
