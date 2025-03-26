#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import re
from typing import Self


class UserId(str):
    """
    A Checkmk user ID

    UserIds must comply to a restricted set of allowed characters (see UserId.validate_userid).

    UserIds must either be compatible with all protocols and components we interface with, or we
    must ensure proper encoding whenever UserIds leave Checkmk.
    The following *not exhaustive* list provides a starting point for the interfaces we need to
    keep in mind:

        * HTML rendering in numerous instances in the GUI
        * URLs and links
            * usually these go through `makeuri_contextless()` or `urlencode()` at the call site
        * GUI messages (user to user) (`cmk.gui.message`)
        * the value of the auth cookie
        * the RestAPI
            * responses
            * bearer token (not base64 encoded!)
        * various error messages (displayed in the GUI)

        * file paths like `var/check_mk/web/<UserId>`
            * sometimes those check for `/` and `..` but currently there's no mechanism make sure
        * Visuals like Graphs and Reports that serialize UserIds into .mk files
        * persisted UserSpecs and Sessions (.mk files)
        * cmk.gui.userdb and htpasswd (LDAP is only ingress of users)
        * various logs, including Audit Log

        * Micro Core
        * Nagios core
        * livestatus queries and commands
            * livestatus.py (the validation regex is currently duplicated here!)
            * cmk.gui.livestatus_utils (acknowledgements, comments, downtimes, ...)
        * event console for contacts, notifications, possibly more
        * agent registration and background jobs

        * ntop connector
        * Grafana connector
        * X509 certificates and the `Key` object (`cmk.gui.key_mgmt`)
    """

    # Note: livestatus.py duplicates the regex to validate incoming UserIds!
    USER_ID_REGEX = re.compile(r"^[\w$][-@.+\w$]*$", re.UNICODE)

    def __new__(cls, text: str) -> Self:
        """Construct a new UserId object

        UserIds are used in a variety of contexts, including HTML, file paths and other external
        systems. Currently we have no means of ensuring proper output encoding wherever UserIds
        are used. Thus, we strictly limit the characters that can be used in a UserId.

        See class docstring for an incomplete list of places where UserIds are processed.

        Raises:
            - ValueError: whenever the given text contains special characters.

        Examples:
            The empty UserId is allowed for historical reasons (see `UserId.builtin`).

                >>> UserId("")
                ''

            ASCII letters, digits, and selected special characters are allowed.

                >>> UserId("cmkadmin")
                'cmkadmin'

                >>> UserId("$cmk_@dmün.1")
                '$cmk_@dmün.1'

            Anything considered a letter in Unicode and the dollar sign is allowed.

                >>> UserId("$cmkädmin")
                '$cmkädmin'

                >>> UserId("ↄ𝒽ѥ𝕔𖹬-艋く")
                'ↄ𝒽ѥ𝕔𖹬-艋く'

            Emails are allowed

                >>> UserId("cmkadmin@hi.com")
                'cmkadmin@hi.com'

                >>> UserId("cmkadmin+test@hi.com")
                'cmkadmin+test@hi.com'

            Special characters other than '$_-@.' are not allowed (see `USER_ID_REGEX`).

                >>> UserId("foo/../")
                Traceback (most recent call last):
                ...
                ValueError: invalid username: 'foo/../'

                >>> UserId("%2F")
                Traceback (most recent call last):
                ...
                ValueError: invalid username: '%2F'

            Some special characters are not allowed at the start.

                >>> UserId(".")
                Traceback (most recent call last):
                ...
                ValueError: invalid username: '.'

                >>> UserId("@example.com")
                Traceback (most recent call last):
                ...
                ValueError: invalid username: '@example.com'

            UserIds must not be longer than 255 bytes.

                >>> UserId("𐌈")
                '𐌈'

                >>> UserId(64*"𐌈")
                Traceback (most recent call last):
                ...
                ValueError: username too long: '𐌈𐌈𐌈𐌈𐌈𐌈𐌈𐌈𐌈𐌈𐌈𐌈𐌈𐌈𐌈𐌈…'
        """
        # Ext4 and other file systems allow filenames of up to 255 bytes.
        if len(bytes(text, encoding="utf-8")) > 255:
            raise ValueError(f"username too long: {text[:16] + '…'!r}")
        # For the empty case, see UserId.builtin().
        if text and not cls.USER_ID_REGEX.match(text):
            raise ValueError(f"invalid username: {text!r}")
        return super().__new__(cls, text)

    @classmethod
    def parse(cls, x: object) -> Self:
        if isinstance(x, cls):
            return x
        if isinstance(x, str):
            return cls(x)
        raise ValueError(f"invalid username: {x!r}")

    @classmethod
    def builtin(cls) -> Self:
        """A special UserId signifying something is owned or created not by a real user but shipped
        as a built in functionality.
        This is mostly used in cmk.gui.visuals.
        Note that, unfortunately, the UserId "" will sometimes also be constructed via regular
        initialization, so this method is not the only source for them.
        Moreover, be aware that it is very possible that some parts of the code use the UserId ""
        with a different meaning.
        """
        return cls("")
