#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from logging import Logger

from cmk.ccc import tty
from cmk.ccc.version import Version


def format_warning(msg: str) -> str:
    return f"{tty.yellow} {msg}{tty.normal}"


def is_update_from_before_3_0(from_version: str | None, logger: Logger) -> bool:
    """Tell whether the site is updated from a Checkmk older than 3.0.

    Args:
        from_version: the value of ``OMD_FROM_VERSION``, which ``omd update`` passes to
            ``cmk-update-config``. It is ``None`` on a new site.
        logger: receives a warning if the version does not parse.

    Returns:
        True if the site comes from a Checkmk before 3.0.

    An absent or unparsable version counts as no such update. The actions that ask run
    once per site, so acting on an unknown version is the worse of the two mistakes.
    """
    if from_version is None:
        return False
    try:
        # OMD_FROM_VERSION carries the edition suffix, e.g. "2.5.0p17.ultimate"
        base = Version.from_str(from_version.rsplit(".", 1)[0]).base
    except ValueError:
        logger.warning(
            'Cannot parse OMD_FROM_VERSION "%(version)s", assuming an update within 3.0',
            {"version": from_version},
        )
        return False
    return base is not None and base.major < 3
