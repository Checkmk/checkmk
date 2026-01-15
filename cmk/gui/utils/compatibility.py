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
    if edition_short == cmk_version.Edition.COMMUNITY.short:
        # No licensing in Checkmk Community, information not necessary
        return _("Version: %s, Edition: %s") % (
            version,
            edition_short.title() if edition_short else _("unknown"),
        )

    return _("Version: %s, Edition: %s, License state: %s") % (
        version,
        edition_short.title() if edition_short else _("unknown"),
        license_state.readable if license_state else _("unknown"),
    )


def is_distributed_setup_compatible_for_licensing(
    central_edition: cmk_version.Edition,
    central_license_state: LicenseState | None,
    remote_edition: cmk_version.Edition,
    remote_license_state: LicenseState | None,
) -> LicensingCompatibility:
    if central_edition is cmk_version.Edition.CLOUD or remote_edition is cmk_version.Edition.CLOUD:
        return EditionsIncompatible(_("Checkmk Cloud is not allowed in distributed monitoring."))

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

    if (central_edition is cmk_version.Edition.ULTIMATEMT) is not (
        remote_edition is cmk_version.Edition.ULTIMATEMT
    ):
        return EditionsIncompatible(
            _("Mix of Checkmk Ultimate and Checkmk Ultimate with multi-tenancy is not possible.")
        )
    return LicensingCompatible()


def is_distributed_monitoring_compatible_for_licensing(
    central_edition: cmk_version.Edition,
    central_license_state: LicenseState | None,
    remote_edition: cmk_version.Edition,
) -> LicensingCompatibility:
    if central_edition is cmk_version.Edition.CLOUD:
        return EditionsIncompatible(_("Checkmk Cloud is not allowed in distributed monitoring."))
    if not isinstance(
        compatibility := _common_is_compatible_for_licensing(
            central_edition,
            central_license_state,
            remote_edition,
        ),
        LicensingCompatible,
    ):
        return compatibility

    if (
        central_edition is cmk_version.Edition.ULTIMATEMT
        and remote_edition is cmk_version.Edition.ULTIMATE
    ):
        return EditionsIncompatible(
            _("Mix of Checkmk Ultimate and Checkmk Ultimate with multi-tenancy is not possible.")
        )
    return LicensingCompatible()


def _common_is_compatible_for_licensing(
    central_edition: cmk_version.Edition,
    central_license_state: LicenseState | None,
    remote_edition: cmk_version.Edition,
) -> LicensingCompatibility:
    if central_edition in [
        cmk_version.Edition.COMMUNITY,
        cmk_version.Edition.PRO,
    ] and remote_edition in [
        cmk_version.Edition.COMMUNITY,
        cmk_version.Edition.PRO,
        cmk_version.Edition.ULTIMATE,
    ]:
        return LicensingCompatible()

    if central_edition is cmk_version.Edition.ULTIMATE:
        if central_license_state in [LicenseState.UNLICENSED, LicenseState.FREE]:
            return LicenseStateIncompatible(
                _("Remote sites are not allowed when central site in license state %s")
                % central_license_state.readable
            )
        if remote_edition is not cmk_version.Edition.ULTIMATE:
            return EditionsIncompatible(
                _(
                    "Only Checkmk Ultimate remote sites can be added to a Checkmk Ultimate central site"
                )
            )
        return LicensingCompatible()

    if (
        central_edition is cmk_version.Edition.ULTIMATEMT
        and remote_edition is cmk_version.Edition.ULTIMATEMT
    ):
        return LicensingCompatible()

    return LicensingCompatible()
