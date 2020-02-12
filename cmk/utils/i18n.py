#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Stub for future i18n code on cmk main module level"""

from typing import AnyStr, Text  # pylint:disable=unused-import

from cmk.utils.encoding import ensure_unicode


# TODO: Clean this up one day by using the way recommended by gettext.
# (See https://docs.python.org/2/library/gettext.html). For this we
# need the path to the locale files here.
# Fake i18n when not available
def _(string):
    # type: (AnyStr) -> Text
    return ensure_unicode(string)
