#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Care for the licensing state of a Checkmk installation"""

import enum
import time
from datetime import timedelta

import livestatus

from cmk.utils.i18n import _
from cmk.utils.version import is_raw_edition


class LicenseState(enum.Enum):
    """All possible license states of the Checkmk site"""

    TRIAL = enum.auto()
    FREE = enum.auto()
    LICENSED = enum.auto()


def license_status_message() -> str:
    if is_raw_edition():
        return ""

    if is_licensed():
        return _("Licensed")

    passed_time = _get_age_trial()
    # Hardcoded 30 days of trial. For dynamic trial time change the 30 days
    remaining_time = timedelta(seconds=30 * 24 * 60 * 60 - passed_time)

    if is_expired_trial() or remaining_time.days < 0:
        return _("Trial expired")

    if remaining_time.days > 1:
        return _("Trial expires in %s days") % remaining_time.days

    return _("Trial expires today (%s)") % time.strftime(
        str(_("%H:%M")), time.localtime(time.time() + remaining_time.seconds)
    )


def is_licensed() -> bool:
    return get_license_status() is LicenseState.LICENSED


def is_expired_trial() -> bool:
    return get_license_status() is LicenseState.FREE


def get_license_status() -> LicenseState:
    if is_raw_edition():
        return (
            LicenseState.LICENSED
        )  # There is no license management for the CRE -> Always licensed
    # TODO: Implement detection of "licensed" case here
    return _get_expired_status()


def _query(query: str) -> livestatus.LivestatusResponse:
    return livestatus.LocalConnection().query(query)


def _get_expired_status() -> LicenseState:
    try:
        response = _query("GET status\nColumns: is_trial_expired\n")
        return LicenseState.FREE if response[0][0] == 1 else LicenseState.TRIAL
    except (livestatus.MKLivestatusNotFoundError, livestatus.MKLivestatusSocketError):
        # NOTE: If livestatus is absent we assume that trial is expired. Livestatus may be absent
        # only when the cmc missing and this case for free version means just
        # expiration(impossibility to check)
        return LicenseState.FREE


def _get_timestamp_trial() -> int:
    try:
        response = _query("GET status\nColumns: state_file_created\n")
        return int(response[0][0])
    except (livestatus.MKLivestatusNotFoundError, livestatus.MKLivestatusSocketError):
        # NOTE: If livestatus is absent we assume that trial is expired. Livestatus may be absent
        # only when the cmc missing and this case for free version means just
        # expiration(impossibility to check)
        return 0


def _get_age_trial() -> int:
    return int(time.time()) - _get_timestamp_trial()
