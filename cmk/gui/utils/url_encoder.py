#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import List, Tuple, Optional, Union, Text  # pylint: disable=unused-import
import six

HTTPVariables = List[Tuple[str, Optional[Union[int, str, Text]]]]


# TODO: Change methods to simple helper functions. The URLEncoder class is not really needed
class URLEncoder(object):  # pylint: disable=useless-object-inheritance
    def urlencode_vars(self, vars_):
        # type: (HTTPVariables) -> str
        """Convert a mapping object or a sequence of two-element tuples to a “percent-encoded” string

        This function returns a str object, never unicode!
        Note: This should be changed once we change everything to
        unicode internally.
        """
        assert isinstance(vars_, list)
        pairs = []
        for varname, value in sorted(vars_):
            assert isinstance(varname, six.string_types)

            if isinstance(value, int):
                value = str(value)
            elif value is None:
                # TODO: This is not ideal and should better be cleaned up somehow. Shouldn't
                # variables with None values simply be skipped? We currently can not find the
                # call sites easily. This may be cleaned up once we establish typing. Until then
                # we need to be compatible with the previous behavior.
                value = ""

            value = six.ensure_str(value)
            #assert type(value) == str, "%s: %s" % (varname, value)
            pairs.append((varname, value))

        return six.moves.urllib.parse.urlencode(pairs)

    def urlencode(self, value):
        # type: (Optional[Union[str, Text]]) -> str
        """Replace special characters in string using the %xx escape.
        This function returns a str object in py2 and py3
        """
        if value is None:
            return ""

        value = six.ensure_str(value)
        assert isinstance(value, str)
        return six.moves.urllib.parse.quote_plus(value)
