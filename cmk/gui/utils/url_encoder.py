#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Optional, Union
from urllib.parse import quote_plus

from six import ensure_str

from cmk.gui.type_defs import HTTPVariables


def _quote_pair(varname: str, value: Union[None, int, str]):
    assert isinstance(varname, str)
    if isinstance(value, int):
        return "%s=%s" % (quote_plus(varname), quote_plus(str(value)))
    if value is None:
        # TODO: This is not ideal and should better be cleaned up somehow. Shouldn't
        # variables with None values simply be skipped? We currently can not find the
        # call sites easily. This may be cleaned up once we establish typing. Until then
        # we need to be compatible with the previous behavior.
        return "%s=" % quote_plus(varname)
    return "%s=%s" % (quote_plus(varname), quote_plus(value))


# TODO: Change methods to simple helper functions. The URLEncoder class is not really needed
class URLEncoder:
    @staticmethod
    def urlencode_vars(vars_: HTTPVariables) -> str:
        """Convert a mapping object or a sequence of two-element tuples to a “percent-encoded” string

        This function returns a str object, never unicode!
        Note: This should be changed once we change everything to
        unicode internally.
        """
        return '&'.join([_quote_pair(var, val) for var, val in sorted(vars_)])

    @staticmethod
    def urlencode(value: Optional[str]) -> str:
        """Replace special characters in string using the %xx escape.
        This function returns a str object in py2 and py3
        """
        if value is None:
            return ""

        value = ensure_str(value)
        assert isinstance(value, str)
        return quote_plus(value)
