#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Check_MK's library for code used by different components of Check_MK.

This library is currently handled as internal module of Check_MK and
does not offer stable APIs. The code may change at any time."""

__version__ = "1.7.0i1"

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
    # type: () -> str
    try:
        return os.environ["OMD_SITE"]
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
