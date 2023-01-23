#!/usr/bin/env python3
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

import re


class UserId(str):
    USER_ID_REGEX = re.compile(r"^[\w$][-@.\w$]*$", re.UNICODE)

    @classmethod
    def validate(cls, text: str) -> None:
        """Check if it is a valid UserId

        UserIds are used in a variety of contexts, including HTML, file paths and other external
        systems. Currently we have no means of ensuring proper output encoding wherever UserIds
        are used. Thus, we strictly limit the characters that can be used in a UserId.

        Examples:

            The empty UserId is allowed for historical reasons (see `UserId.builtin`).

                >>> UserId.validate("")

            ASCII letters, digits, and selected special characters are allowed.

                >>> UserId.validate("cmkadmin")
                >>> UserId.validate("$cmk_@dmün.1")

            Special characters other than '$_-@.' are not allowed (see `USER_ID_REGEX`).

                >>> UserId.validate("foo/../")
                Traceback (most recent call last):
                ...
                ValueError: Invalid username: 'foo/../'

                >>> UserId.validate("%2F")
                Traceback (most recent call last):
                ...
                ValueError: Invalid username: '%2F'

        """
        if text == "":
            # see UserId.builtin
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
