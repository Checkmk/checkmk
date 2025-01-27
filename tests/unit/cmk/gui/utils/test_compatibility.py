#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import pytest

from cmk.ccc.version import Edition

from cmk.utils.licensing.handler import LicenseState

from cmk.gui.utils.compatibility import (
    EditionsIncompatible,
    is_distributed_monitoring_compatible_for_licensing,
    is_distributed_setup_compatible_for_licensing,
    LicenseStateIncompatible,
    LicensingCompatibility,
    LicensingCompatible,
)


@pytest.mark.parametrize(
    "central_edition, central_license_state, remote_edition, remote_license_state, expected_compatibility",
    [
        pytest.param(
            Edition.CRE,
            LicenseState.LICENSED,
            Edition.CRE,
            LicenseState.LICENSED,
            LicensingCompatible(),
            id="CRE-CRE",
        ),
        pytest.param(
            Edition.CRE,
            LicenseState.LICENSED,
            Edition.CEE,
            LicenseState.LICENSED,
            LicensingCompatible(),
            id="CRE-CEE",
        ),
        pytest.param(
            Edition.CRE,
            LicenseState.LICENSED,
            Edition.CCE,
            LicenseState.LICENSED,
            LicensingCompatible(),
            id="CRE-CCE",
        ),
        pytest.param(
            Edition.CRE,
            LicenseState.LICENSED,
            Edition.CCE,
            LicenseState.FREE,
            LicenseStateIncompatible("Remote site in license state free is not allowed"),
            id="CRE-CCE-free",
        ),
        pytest.param(
            Edition.CRE,
            LicenseState.LICENSED,
            Edition.CME,
            LicenseState.LICENSED,
            EditionsIncompatible("Mix of CME and non-CME is not allowed."),
            id="CRE-CME",
        ),
        pytest.param(
            Edition.CEE,
            LicenseState.LICENSED,
            Edition.CRE,
            LicenseState.LICENSED,
            LicensingCompatible(),
            id="CEE-CRE",
        ),
        pytest.param(
            Edition.CEE,
            LicenseState.LICENSED,
            Edition.CEE,
            LicenseState.LICENSED,
            LicensingCompatible(),
            id="CEE-CEE",
        ),
        pytest.param(
            Edition.CEE,
            LicenseState.LICENSED,
            Edition.CCE,
            LicenseState.LICENSED,
            LicensingCompatible(),
            id="CEE-CCE",
        ),
        pytest.param(
            Edition.CEE,
            LicenseState.LICENSED,
            Edition.CCE,
            LicenseState.FREE,
            LicenseStateIncompatible("Remote site in license state free is not allowed"),
            id="CEE-CCE-free",
        ),
        pytest.param(
            Edition.CEE,
            LicenseState.LICENSED,
            Edition.CME,
            LicenseState.LICENSED,
            EditionsIncompatible("Mix of CME and non-CME is not allowed."),
            id="CEE-CME",
        ),
        pytest.param(
            Edition.CCE,
            LicenseState.TRIAL,
            Edition.CRE,
            LicenseState.LICENSED,
            EditionsIncompatible("Only CCE remote sites can be added to CCE central site"),
            id="CCE-trial-CRE",
        ),
        pytest.param(
            Edition.CCE,
            LicenseState.TRIAL,
            Edition.CEE,
            LicenseState.LICENSED,
            EditionsIncompatible("Only CCE remote sites can be added to CCE central site"),
            id="CCE-trial-CEE",
        ),
        pytest.param(
            Edition.CCE,
            LicenseState.TRIAL,
            Edition.CCE,
            LicenseState.LICENSED,
            LicensingCompatible(),
            id="CCE-trial-CCE",
        ),
        pytest.param(
            Edition.CCE,
            LicenseState.LICENSED,
            Edition.CCE,
            LicenseState.FREE,
            LicenseStateIncompatible("Remote site in license state free is not allowed"),
            id="CCE-CCE-free",
        ),
        pytest.param(
            Edition.CCE,
            LicenseState.TRIAL,
            Edition.CME,
            LicenseState.LICENSED,
            EditionsIncompatible("Only CCE remote sites can be added to CCE central site"),
            id="CCE-trial-CME",
        ),
        pytest.param(
            Edition.CCE,
            LicenseState.LICENSED,
            Edition.CRE,
            LicenseState.LICENSED,
            EditionsIncompatible("Only CCE remote sites can be added to CCE central site"),
            id="CCE-licensed-CRE",
        ),
        pytest.param(
            Edition.CCE,
            LicenseState.LICENSED,
            Edition.CEE,
            LicenseState.LICENSED,
            EditionsIncompatible("Only CCE remote sites can be added to CCE central site"),
            id="CCE-licensed-CEE",
        ),
        pytest.param(
            Edition.CCE,
            LicenseState.LICENSED,
            Edition.CCE,
            LicenseState.LICENSED,
            LicensingCompatible(),
            id="CCE-licensed-CCE",
        ),
        pytest.param(
            Edition.CCE,
            LicenseState.LICENSED,
            Edition.CME,
            LicenseState.LICENSED,
            EditionsIncompatible("Only CCE remote sites can be added to CCE central site"),
            id="CCE-licensed-CME",
        ),
        pytest.param(
            Edition.CCE,
            LicenseState.UNLICENSED,
            Edition.CRE,
            LicenseState.LICENSED,
            LicenseStateIncompatible(
                "Remote sites are not allowed when central site in license state unlicensed"
            ),
            id="CCE-unlicensed-CRE",
        ),
        pytest.param(
            Edition.CCE,
            LicenseState.UNLICENSED,
            Edition.CEE,
            LicenseState.LICENSED,
            LicenseStateIncompatible(
                "Remote sites are not allowed when central site in license state unlicensed"
            ),
            id="CCE-unlicensed-CEE",
        ),
        pytest.param(
            Edition.CCE,
            LicenseState.UNLICENSED,
            Edition.CCE,
            LicenseState.LICENSED,
            LicenseStateIncompatible(
                "Remote sites are not allowed when central site in license state unlicensed"
            ),
            id="CCE-unlicensed-CCE",
        ),
        pytest.param(
            Edition.CCE,
            LicenseState.UNLICENSED,
            Edition.CME,
            LicenseState.LICENSED,
            LicenseStateIncompatible(
                "Remote sites are not allowed when central site in license state unlicensed"
            ),
            id="CCE-unlicensed-CME",
        ),
        pytest.param(
            Edition.CCE,
            LicenseState.FREE,
            Edition.CRE,
            LicenseState.LICENSED,
            LicenseStateIncompatible(
                "Remote sites are not allowed when central site in license state free"
            ),
            id="CCE-free-CRE",
        ),
        pytest.param(
            Edition.CCE,
            LicenseState.FREE,
            Edition.CEE,
            LicenseState.LICENSED,
            LicenseStateIncompatible(
                "Remote sites are not allowed when central site in license state free"
            ),
            id="CCE-free-CEE",
        ),
        pytest.param(
            Edition.CCE,
            LicenseState.FREE,
            Edition.CCE,
            LicenseState.LICENSED,
            LicenseStateIncompatible(
                "Remote sites are not allowed when central site in license state free"
            ),
            id="CCE-free-CCE",
        ),
        pytest.param(
            Edition.CCE,
            LicenseState.FREE,
            Edition.CME,
            LicenseState.LICENSED,
            LicenseStateIncompatible(
                "Remote sites are not allowed when central site in license state free"
            ),
            id="CCE-free-CME",
        ),
        pytest.param(
            Edition.CME,
            LicenseState.LICENSED,
            Edition.CRE,
            LicenseState.LICENSED,
            EditionsIncompatible("Mix of CME and non-CME is not allowed."),
            id="CME-CRE",
        ),
        pytest.param(
            Edition.CME,
            LicenseState.LICENSED,
            Edition.CEE,
            LicenseState.LICENSED,
            EditionsIncompatible("Mix of CME and non-CME is not allowed."),
            id="CME-CEE",
        ),
        pytest.param(
            Edition.CME,
            LicenseState.LICENSED,
            Edition.CCE,
            LicenseState.LICENSED,
            EditionsIncompatible("Mix of CME and non-CME is not allowed."),
            id="CME-CCE",
        ),
        pytest.param(
            Edition.CME,
            LicenseState.LICENSED,
            Edition.CCE,
            LicenseState.FREE,
            LicenseStateIncompatible("Remote site in license state free is not allowed"),
            id="CME-CCE-free",
        ),
        pytest.param(
            Edition.CME,
            LicenseState.LICENSED,
            Edition.CME,
            LicenseState.LICENSED,
            LicensingCompatible(),
            id="CME-CME",
        ),
    ],
)
def test_license_compatibility_distributed_setup(
    central_edition: Edition,
    central_license_state: LicenseState,
    remote_edition: Edition,
    remote_license_state: LicenseState,
    expected_compatibility: LicensingCompatibility,
) -> None:
    actual_compatibility = is_distributed_setup_compatible_for_licensing(
        central_edition, central_license_state, remote_edition, remote_license_state
    )
    assert isinstance(actual_compatibility, type(expected_compatibility))
    if not isinstance(expected_compatibility, LicensingCompatible) and not isinstance(
        actual_compatibility, LicensingCompatible
    ):
        assert actual_compatibility._reason == expected_compatibility._reason


@pytest.mark.parametrize(
    "central_edition, central_license_state, remote_edition, expected_compatibility",
    [
        pytest.param(
            Edition.CRE, LicenseState.LICENSED, Edition.CRE, LicensingCompatible(), id="CRE-CRE"
        ),
        pytest.param(
            Edition.CRE, LicenseState.LICENSED, Edition.CEE, LicensingCompatible(), id="CRE-CEE"
        ),
        pytest.param(
            Edition.CRE, LicenseState.LICENSED, Edition.CCE, LicensingCompatible(), id="CRE-CCE"
        ),
        pytest.param(
            Edition.CRE,
            LicenseState.LICENSED,
            Edition.CME,
            LicensingCompatible(),
            id="CRE-CME",
        ),
        pytest.param(
            Edition.CEE, LicenseState.LICENSED, Edition.CRE, LicensingCompatible(), id="CEE-CRE"
        ),
        pytest.param(
            Edition.CEE, LicenseState.LICENSED, Edition.CEE, LicensingCompatible(), id="CEE-CEE"
        ),
        pytest.param(
            Edition.CEE, LicenseState.LICENSED, Edition.CCE, LicensingCompatible(), id="CEE-CCE"
        ),
        pytest.param(
            Edition.CEE,
            LicenseState.LICENSED,
            Edition.CME,
            LicensingCompatible(),
            id="CEE-CME",
        ),
        pytest.param(
            Edition.CCE,
            LicenseState.TRIAL,
            Edition.CRE,
            EditionsIncompatible("Only CCE remote sites can be added to CCE central site"),
            id="CCE-trial-CRE",
        ),
        pytest.param(
            Edition.CCE,
            LicenseState.TRIAL,
            Edition.CEE,
            EditionsIncompatible("Only CCE remote sites can be added to CCE central site"),
            id="CCE-trial-CEE",
        ),
        pytest.param(
            Edition.CCE,
            LicenseState.TRIAL,
            Edition.CCE,
            LicensingCompatible(),
            id="CCE-trial-CCE",
        ),
        pytest.param(
            Edition.CCE,
            LicenseState.TRIAL,
            Edition.CME,
            EditionsIncompatible("Only CCE remote sites can be added to CCE central site"),
            id="CCE-trial-CME",
        ),
        pytest.param(
            Edition.CCE,
            LicenseState.LICENSED,
            Edition.CRE,
            EditionsIncompatible("Only CCE remote sites can be added to CCE central site"),
            id="CCE-licensed-CRE",
        ),
        pytest.param(
            Edition.CCE,
            LicenseState.LICENSED,
            Edition.CEE,
            EditionsIncompatible("Only CCE remote sites can be added to CCE central site"),
            id="CCE-licensed-CEE",
        ),
        pytest.param(
            Edition.CCE,
            LicenseState.LICENSED,
            Edition.CCE,
            LicensingCompatible(),
            id="CCE-licensed-CCE",
        ),
        pytest.param(
            Edition.CCE,
            LicenseState.LICENSED,
            Edition.CME,
            EditionsIncompatible("Only CCE remote sites can be added to CCE central site"),
            id="CCE-licensed-CME",
        ),
        pytest.param(
            Edition.CCE,
            LicenseState.UNLICENSED,
            Edition.CRE,
            LicenseStateIncompatible(
                "Remote sites are not allowed when central site in license state unlicensed"
            ),
            id="CCE-unlicensed-CRE",
        ),
        pytest.param(
            Edition.CCE,
            LicenseState.UNLICENSED,
            Edition.CEE,
            LicenseStateIncompatible(
                "Remote sites are not allowed when central site in license state unlicensed"
            ),
            id="CCE-unlicensed-CEE",
        ),
        pytest.param(
            Edition.CCE,
            LicenseState.UNLICENSED,
            Edition.CCE,
            LicenseStateIncompatible(
                "Remote sites are not allowed when central site in license state unlicensed"
            ),
            id="CCE-unlicensed-CCE",
        ),
        pytest.param(
            Edition.CCE,
            LicenseState.UNLICENSED,
            Edition.CME,
            LicenseStateIncompatible(
                "Remote sites are not allowed when central site in license state unlicensed"
            ),
            id="CCE-unlicensed-CME",
        ),
        pytest.param(
            Edition.CCE,
            LicenseState.FREE,
            Edition.CRE,
            LicenseStateIncompatible(
                "Remote sites are not allowed when central site in license state free"
            ),
            id="CCE-free-CRE",
        ),
        pytest.param(
            Edition.CCE,
            LicenseState.FREE,
            Edition.CEE,
            LicenseStateIncompatible(
                "Remote sites are not allowed when central site in license state free"
            ),
            id="CCE-free-CEE",
        ),
        pytest.param(
            Edition.CCE,
            LicenseState.FREE,
            Edition.CCE,
            LicenseStateIncompatible(
                "Remote sites are not allowed when central site in license state free"
            ),
            id="CCE-free-CCE",
        ),
        pytest.param(
            Edition.CCE,
            LicenseState.FREE,
            Edition.CME,
            LicenseStateIncompatible(
                "Remote sites are not allowed when central site in license state free"
            ),
            id="CCE-free-CME",
        ),
        pytest.param(
            Edition.CME,
            LicenseState.LICENSED,
            Edition.CRE,
            LicensingCompatible(),
            id="CME-CRE",
        ),
        pytest.param(
            Edition.CME,
            LicenseState.LICENSED,
            Edition.CEE,
            LicensingCompatible(),
            id="CME-CEE",
        ),
        pytest.param(
            Edition.CME,
            LicenseState.LICENSED,
            Edition.CCE,
            EditionsIncompatible("Mix of CME and non-CME is not allowed."),
            id="CME-CCE",
        ),
        pytest.param(
            Edition.CME,
            LicenseState.LICENSED,
            Edition.CME,
            LicensingCompatible(),
            id="CME-CME",
        ),
    ],
)
def test_license_compatibility_distributed_monitoring(
    central_edition: Edition,
    central_license_state: LicenseState,
    remote_edition: Edition,
    expected_compatibility: LicensingCompatibility,
) -> None:
    actual_compatibility = is_distributed_monitoring_compatible_for_licensing(
        central_edition,
        central_license_state,
        remote_edition,
    )

    assert isinstance(actual_compatibility, type(expected_compatibility))
    if not isinstance(expected_compatibility, LicensingCompatible) and not isinstance(
        actual_compatibility, LicensingCompatible
    ):
        assert actual_compatibility._reason == expected_compatibility._reason
