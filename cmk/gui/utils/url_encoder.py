#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Optional
import urllib.parse

from six import ensure_str

from cmk.gui.type_defs import HTTPVariables


# TODO: Change methods to simple helper functions. The URLEncoder class is not really needed
class URLEncoder:
    @staticmethod
    def urlencode_vars(vars_: HTTPVariables) -> str:
        """Convert a mapping object or a sequence of two-element tuples to a “percent-encoded” string

        This function returns a str object, never unicode!
        Note: This should be changed once we change everything to
        unicode internally.
        """
        assert isinstance(vars_, list)
        pairs = []
        for varname, value in sorted(vars_):
            assert isinstance(varname, str)

            if isinstance(value, int):
                value = str(value)
            elif value is None:
                # TODO: This is not ideal and should better be cleaned up somehow. Shouldn't
                # variables with None values simply be skipped? We currently can not find the
                # call sites easily. This may be cleaned up once we establish typing. Until then
                # we need to be compatible with the previous behavior.
                value = ""

            value = ensure_str(value)
            #assert type(value) == str, "%s: %s" % (varname, value)
            pairs.append((varname, value))

        return urllib.parse.urlencode(pairs)

    @staticmethod
    def urlencode(value: Optional[str]) -> str:
        """Replace special characters in string using the %xx escape.
        This function returns a str object in py2 and py3
        """
        if value is None:
            return ""

        value = ensure_str(value)
        assert isinstance(value, str)
        return urllib.parse.quote_plus(value)
