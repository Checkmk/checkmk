#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.ccc import version as cmk_version
from cmk.ccc.i18n import _
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


class LicensingCompatible: ...


LicensingCompatibility = EditionsIncompatible | LicenseStateIncompatible | LicensingCompatible


def make_incompatible_info(
    central_version: str,
    central_edition_short: str,
    central_license_state: LicenseState | None,
    remote_version: str,
    remote_edition_short: str | None,
    remote_license_state: LicenseState | None,
    compatibility: cmk_version.VersionsIncompatible | LicensingCompatibility,
) -> str:
    return _("The central (%s) and remote site (%s) are not compatible. Reason: %s") % (
        make_site_version_info(central_version, central_edition_short, central_license_state),
        make_site_version_info(remote_version, remote_edition_short, remote_license_state),
        compatibility,
    )


def make_site_version_info(
    version: str,
    edition_short: str | None,
    license_state: LicenseState | None,
) -> str:
    if edition_short == cmk_version.Edition.CRE.short:
        # No licensing in CRE, information not necessary
        return _("Version: %s, Edition: %s") % (
            version,
            edition_short.upper() if edition_short else _("unknown"),
        )

    return _("Version: %s, Edition: %s, License state: %s") % (
        version,
        edition_short.upper() if edition_short else _("unknown"),
        license_state.readable if license_state else _("unknown"),
    )


def is_distributed_setup_compatible_for_licensing(
    central_edition: cmk_version.Edition,
    central_license_state: LicenseState | None,
    remote_edition: cmk_version.Edition,
    remote_license_state: LicenseState | None,
) -> LicensingCompatibility:
    if central_edition is cmk_version.Edition.CSE or remote_edition is cmk_version.Edition.CSE:
        return EditionsIncompatible(_("CSE is not allowed in distributed monitoring."))

    if remote_license_state is LicenseState.FREE:
        return LicenseStateIncompatible(
            "Remote site in license state %s is not allowed" % remote_license_state.readable
        )

    if not isinstance(
        compatibility := _common_is_compatible_for_licensing(
            central_edition,
            central_license_state,
            remote_edition,
        ),
        LicensingCompatible,
    ):
        return compatibility

    if (central_edition is cmk_version.Edition.CME) is not (
        remote_edition is cmk_version.Edition.CME
    ):
        return EditionsIncompatible(_("Mix of CME and non-CME is not allowed."))
    return LicensingCompatible()


def is_distributed_monitoring_compatible_for_licensing(
    central_edition: cmk_version.Edition,
    central_license_state: LicenseState | None,
    remote_edition: cmk_version.Edition,
) -> LicensingCompatibility:
    if central_edition is cmk_version.Edition.CSE:
        return EditionsIncompatible(_("CSE is not allowed in distributed monitoring."))
    if not isinstance(
        compatibility := _common_is_compatible_for_licensing(
            central_edition,
            central_license_state,
            remote_edition,
        ),
        LicensingCompatible,
    ):
        return compatibility

    if central_edition is cmk_version.Edition.CME and remote_edition is cmk_version.Edition.CCE:
        return EditionsIncompatible(_("Mix of CME and non-CME is not allowed."))
    return LicensingCompatible()


def _common_is_compatible_for_licensing(
    central_edition: cmk_version.Edition,
    central_license_state: LicenseState | None,
    remote_edition: cmk_version.Edition,
) -> LicensingCompatibility:
    if central_edition in [cmk_version.Edition.CRE, cmk_version.Edition.CEE] and remote_edition in [
        cmk_version.Edition.CRE,
        cmk_version.Edition.CEE,
        cmk_version.Edition.CCE,
    ]:
        return LicensingCompatible()

    if central_edition is cmk_version.Edition.CCE:
        if central_license_state in [LicenseState.UNLICENSED, LicenseState.FREE]:
            return LicenseStateIncompatible(
                _("Remote sites are not allowed when central site in license state %s")
                % central_license_state.readable
            )
        if remote_edition is not cmk_version.Edition.CCE:
            return EditionsIncompatible(_("Only CCE remote sites can be added to CCE central site"))
        return LicensingCompatible()

    if central_edition is cmk_version.Edition.CME and remote_edition is cmk_version.Edition.CME:
        return LicensingCompatible()

    return LicensingCompatible()
