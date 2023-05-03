#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.utils import version as cmk_version
from cmk.utils.i18n import _
from cmk.utils.licensing.handler import LicenseState


class LicenseStateIncompatible:
    def __init__(self, reason: str) -> None:
        self._reason = reason

    def __str__(self) -> str:
        return self._reason


class EditionsIncompatible:
    def __init__(self, reason: str) -> None:
        self._reason = reason

    def __str__(self) -> str:
        return self._reason


class LicensingCompatible:
    ...


LicensingCompatibility = EditionsIncompatible | LicenseStateIncompatible | LicensingCompatible


def make_incompatible_info(
    central_version: str,
    central_edition_short: str,
    remote_version: str,
    remote_edition_short: str,
    remote_license_state: LicenseState | None,
    compatibility: (cmk_version.VersionsIncompatible | LicensingCompatibility),
) -> str:
    return _("The central (%s) and remote site (%s) are not compatible. Reason: %s") % (
        _make_central_site_version_info(central_version, central_edition_short),
        make_remote_site_version_info(remote_version, remote_edition_short, remote_license_state),
        compatibility,
    )


def _make_central_site_version_info(
    central_version: str,
    central_edition_short: str,
) -> str:
    return _("Version: %s, Edition: %s") % (central_version, central_edition_short)


def make_remote_site_version_info(
    remote_version: str,
    remote_edition_short: str,
    remote_license_state: LicenseState | None,
) -> str:
    return _("Version: %s, Edition: %s, License state: %s") % (
        remote_version,
        remote_edition_short,
        remote_license_state.readable if remote_license_state else _("unknown"),
    )


def is_distributed_setup_compatible_for_licensing(
    central_edition_short: str,
    remote_edition_short: str,
    remote_license_state: LicenseState | None,
) -> LicensingCompatibility:
    if (central_edition_short == "cme") is not (remote_edition_short == "cme"):
        return EditionsIncompatible("Mix of CME and non-CME is not supported.")

    if remote_license_state is LicenseState.FREE:
        return LicenseStateIncompatible(
            "Remote site in license state %s is not allowed" % remote_license_state.readable
        )

    return LicensingCompatible()
