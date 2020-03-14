#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from contextlib import contextmanager
from typing import Iterator, Union, List, Text  # pylint: disable=unused-import
import six

from cmk.gui.http import Response  # pylint: disable=unused-import
from cmk.gui.i18n import _
from cmk.gui.exceptions import MKGeneralException
from cmk.gui.utils.html import HTML

# TODO: Almost HTMLContent, only None is missing, but that would be OK, too...
OutputFunnelInput = Union[int, "HTML", str, Text]


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
        elif isinstance(text, int):
            text = str(text)

        if not isinstance(text, six.string_types):
            raise MKGeneralException(
                _('Type Error: html.write accepts str and unicode input objects only!'))

        if self._is_plugged():
            self.plug_text[-1].append(text)
        else:
            self._lowlevel_write(six.ensure_binary(text))

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
