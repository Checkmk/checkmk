#!/usr/bin/env python3
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

import re


class UserId(str):
    USER_ID_REGEX = re.compile(r"^[\w_$][-\w.@_$]*$")

    @classmethod
    def validate(cls, text: str) -> None:
        """Check if it is a valid UserId
        We use the userid to create file paths, so we we need to be strict...
        >>> UserId.validate("cmkadmin")
        >>> UserId.validate("")
        >>> UserId.validate("foo/../")
        Traceback (most recent call last):
        ...
        ValueError: Invalid username: 'foo/../'
        """
        if text == "":
            # For legacy reasons (e.g. cmk.gui.visuals)
            return
        if not cls.USER_ID_REGEX.match(text):
            raise ValueError(f"Invalid username: {text!r}")

    @classmethod
    def builtin(cls) -> UserId:
        """A special UserId signifying something is owned or created not by a real user but shipped
        as a built in functionality.
        This is mostly used in cmk.gui.visuals.
        Note that, unfortunately, the UserId "" will sometimes also be constructed via regular
        initialization, so this method is not the only source for them.
        Moreover, be aware that it is very possible that some parts of the code use the UserId ""
        with a different meaning.
        """
        return UserId("")

    def __new__(cls, text: str) -> UserId:
        cls.validate(text)
        return super().__new__(cls, text)
