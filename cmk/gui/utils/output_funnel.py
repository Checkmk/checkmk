#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from contextlib import contextmanager
from typing import Iterator, Union, List
from six import ensure_binary

from cmk.gui.http import Response
from cmk.gui.i18n import _
from cmk.gui.exceptions import MKGeneralException
from cmk.gui.utils.html import HTML

# TODO: Almost HTMLContent, only None is missing, but that would be OK, too...
OutputFunnelInput = Union[int, "HTML", str]


class OutputFunnel:
    """
    Provides the write functionality. The method _lowlevel_write needs
    to be overwritten in the specific subclass!

     Usage of plugged context:
             with html.plugged():
                html.write("something")
                html_code = html.drain()
             print html_code
    """
    def __init__(self, response: Response) -> None:
        super(OutputFunnel, self).__init__()
        self._response = response
        self.plug_text: List[List[str]] = []

    def write(self, text: OutputFunnelInput) -> None:
        if not text:
            return

        if isinstance(text, HTML):
            text = "%s" % text
        elif isinstance(text, int):
            text = str(text)

        if not isinstance(text, str):
            raise MKGeneralException(
                _('Type Error: html.write accepts str and unicode input objects only!'))

        if self._is_plugged():
            self.plug_text[-1].append(text)
        else:
            self._lowlevel_write(ensure_binary(text))

    # Please note that this does not work with the plugs at the moment (The plugs store text)
    def write_binary(self, data: bytes) -> None:
        self._response.stream.write(data)

    def _lowlevel_write(self, text: bytes) -> None:
        self._response.stream.write(text)

    @contextmanager
    def plugged(self) -> Iterator[None]:
        self.plug_text.append([])
        try:
            yield
        finally:
            text = self.drain()
            self.plug_text.pop()
            self.write(text)

    def _is_plugged(self) -> bool:
        return bool(self.plug_text)

    def drain(self) -> str:
        """Get the sink content in order to do something with it."""
        if not self._is_plugged():  # TODO: Raise exception or even remove "if"?
            return ''

        text = "".join(self.plug_text.pop())
        self.plug_text.append([])
        return text
