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

from typing import List, Tuple, Optional, Union, Text  # pylint: disable=unused-import
import six

HTTPVariables = List[Tuple[str, Optional[Union[int, str, Text]]]]


# TODO: Change methods to simple helper functions. The URLEncoder class is not really needed
class URLEncoder(object):
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
