#!/usr/bin/python
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
"""Check_MK's library for code used by different components of Check_MK.

This library is currently handled as internal module of Check_MK and
does not offer stable APIs. The code may change at any time."""

__version__ = u"1.7.0i1"

import os
import sys
from typing import Text  # pylint: disable=unused-import
import six

import cmk.utils.paths
from cmk.utils.encoding import ensure_unicode
from cmk.utils.exceptions import MKGeneralException
from cmk.utils.i18n import _

# Explicitly check for Python 3 (which is understood by mypy)
if sys.version_info[0] >= 3:
    from pathlib import Path  # pylint: disable=import-error
else:
    from pathlib2 import Path


def omd_version():
    # type: () -> Text
    version_link = Path(cmk.utils.paths.omd_root).joinpath("version")
    return ensure_unicode(version_link.resolve().name)  # pylint: disable=no-member


def omd_site():
    # type: () -> Text
    try:
        return ensure_unicode(os.environ["OMD_SITE"])
    except KeyError:
        raise MKGeneralException(
            _("OMD_SITE environment variable not set. You can "
              "only execute this in an OMD site."))


def edition_short():
    # type: () -> Text
    """Can currently either return \"cre\" or \"cee\"."""
    parts = omd_version().split(".")
    if parts[-1] == "demo":
        return six.text_type(parts[-2])

    return six.text_type(parts[-1])


def is_enterprise_edition():
    # type: () -> bool
    return edition_short() == "cee"


def is_raw_edition():
    # type: () -> bool
    return edition_short() == "cre"


def is_managed_edition():
    # type: () -> bool
    return edition_short() == "cme"


def is_demo():
    # type: () -> bool
    parts = omd_version().split(".")
    return parts[-1] == "demo"
