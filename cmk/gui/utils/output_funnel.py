#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from contextlib import contextmanager
from typing import Iterator, List

from cmk.gui.http import Response


class OutputFunnel:
    """Provides writing to the response object or a plugged response

    Manages a stack of response objects. Calls to write() will always
    write the given string to the topmost request object. It is used
    like this:

        # Write "xyz" to response which is sent to the client
        html.write_text("xyz")

        # Write "something" to a "plugged" response and print it to stdout
        with output_funnel.plugged() as plug:
           html.write_text("something")
           html_code = html.drain()
        print(html_code)
    """

    def __init__(self, response: Response) -> None:
        self._response_stack: List[Response] = [response]

    def write(self, data: bytes) -> None:
        self._response_stack[-1].stream.write(data)

    @contextmanager
    def plugged(self) -> Iterator[None]:
        self._response_stack.append(Response())
        try:
            yield
        finally:
            response = self._response_stack.pop()
            # Rest of popped response is written to now topmost request.
            # TODO: Investigate call sites whether or not this is a used feature
            self.write(response.get_data())

    def _is_plugged(self) -> bool:
        return len(self._response_stack) > 1

    def drain(self) -> str:
        """Return the content of the topmost response object"""
        if not self._is_plugged():
            return ""

        text = self._response_stack.pop().get_data(as_text=True)
        self._response_stack.append(Response())
        return text
