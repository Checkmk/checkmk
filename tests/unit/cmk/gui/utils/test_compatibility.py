#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import pytest

from cmk.ccc.version import Edition
from cmk.gui.utils.compatibility import (
    EditionsIncompatible,
    is_distributed_monitoring_compatible_for_licensing,
    is_distributed_setup_compatible_for_licensing,
    LicenseStateIncompatible,
    LicensingCompatibility,
    LicensingCompatible,
)
from cmk.utils.licensing.handler import LicenseState


@pytest.mark.parametrize(
    "central_edition, central_license_state, remote_edition, remote_license_state, expected_compatibility",
    [
        pytest.param(
            Edition.COMMUNITY,
            LicenseState.LICENSED,
            Edition.COMMUNITY,
            LicenseState.LICENSED,
            LicensingCompatible(),
            id="CRE-CRE",
        ),
        pytest.param(
            Edition.COMMUNITY,
            LicenseState.LICENSED,
            Edition.PRO,
            LicenseState.LICENSED,
            LicensingCompatible(),
            id="CRE-CEE",
        ),
        pytest.param(
            Edition.COMMUNITY,
            LicenseState.LICENSED,
            Edition.ULTIMATE,
            LicenseState.LICENSED,
            LicensingCompatible(),
            id="CRE-CCE",
        ),
        pytest.param(
            Edition.COMMUNITY,
            LicenseState.LICENSED,
            Edition.ULTIMATE,
            LicenseState.FREE,
            LicenseStateIncompatible("Remote site in license state free is not allowed"),
            id="CRE-CCE-free",
        ),
        pytest.param(
            Edition.COMMUNITY,
            LicenseState.LICENSED,
            Edition.ULTIMATEMT,
            LicenseState.LICENSED,
            EditionsIncompatible("Mix of CME and non-CME is not allowed."),
            id="CRE-CME",
        ),
        pytest.param(
            Edition.PRO,
            LicenseState.LICENSED,
            Edition.COMMUNITY,
            LicenseState.LICENSED,
            LicensingCompatible(),
            id="CEE-CRE",
        ),
        pytest.param(
            Edition.PRO,
            LicenseState.LICENSED,
            Edition.PRO,
            LicenseState.LICENSED,
            LicensingCompatible(),
            id="CEE-CEE",
        ),
        pytest.param(
            Edition.PRO,
            LicenseState.LICENSED,
            Edition.ULTIMATE,
            LicenseState.LICENSED,
            LicensingCompatible(),
            id="CEE-CCE",
        ),
        pytest.param(
            Edition.PRO,
            LicenseState.LICENSED,
            Edition.ULTIMATE,
            LicenseState.FREE,
            LicenseStateIncompatible("Remote site in license state free is not allowed"),
            id="CEE-CCE-free",
        ),
        pytest.param(
            Edition.PRO,
            LicenseState.LICENSED,
            Edition.ULTIMATEMT,
            LicenseState.LICENSED,
            EditionsIncompatible("Mix of CME and non-CME is not allowed."),
            id="CEE-CME",
        ),
        pytest.param(
            Edition.ULTIMATE,
            LicenseState.TRIAL,
            Edition.COMMUNITY,
            LicenseState.LICENSED,
            EditionsIncompatible("Only CCE remote sites can be added to CCE central site"),
            id="CCE-trial-CRE",
        ),
        pytest.param(
            Edition.ULTIMATE,
            LicenseState.TRIAL,
            Edition.PRO,
            LicenseState.LICENSED,
            EditionsIncompatible("Only CCE remote sites can be added to CCE central site"),
            id="CCE-trial-CEE",
        ),
        pytest.param(
            Edition.ULTIMATE,
            LicenseState.TRIAL,
            Edition.ULTIMATE,
            LicenseState.LICENSED,
            LicensingCompatible(),
            id="CCE-trial-CCE",
        ),
        pytest.param(
            Edition.ULTIMATE,
            LicenseState.LICENSED,
            Edition.ULTIMATE,
            LicenseState.FREE,
            LicenseStateIncompatible("Remote site in license state free is not allowed"),
            id="CCE-CCE-free",
        ),
        pytest.param(
            Edition.ULTIMATE,
            LicenseState.TRIAL,
            Edition.ULTIMATEMT,
            LicenseState.LICENSED,
            EditionsIncompatible("Only CCE remote sites can be added to CCE central site"),
            id="CCE-trial-CME",
        ),
        pytest.param(
            Edition.ULTIMATE,
            LicenseState.LICENSED,
            Edition.COMMUNITY,
            LicenseState.LICENSED,
            EditionsIncompatible("Only CCE remote sites can be added to CCE central site"),
            id="CCE-licensed-CRE",
        ),
        pytest.param(
            Edition.ULTIMATE,
            LicenseState.LICENSED,
            Edition.PRO,
            LicenseState.LICENSED,
            EditionsIncompatible("Only CCE remote sites can be added to CCE central site"),
            id="CCE-licensed-CEE",
        ),
        pytest.param(
            Edition.ULTIMATE,
            LicenseState.LICENSED,
            Edition.ULTIMATE,
            LicenseState.LICENSED,
            LicensingCompatible(),
            id="CCE-licensed-CCE",
        ),
        pytest.param(
            Edition.ULTIMATE,
            LicenseState.LICENSED,
            Edition.ULTIMATEMT,
            LicenseState.LICENSED,
            EditionsIncompatible("Only CCE remote sites can be added to CCE central site"),
            id="CCE-licensed-CME",
        ),
        pytest.param(
            Edition.ULTIMATE,
            LicenseState.UNLICENSED,
            Edition.COMMUNITY,
            LicenseState.LICENSED,
            LicenseStateIncompatible(
                "Remote sites are not allowed when central site in license state unlicensed"
            ),
            id="CCE-unlicensed-CRE",
        ),
        pytest.param(
            Edition.ULTIMATE,
            LicenseState.UNLICENSED,
            Edition.PRO,
            LicenseState.LICENSED,
            LicenseStateIncompatible(
                "Remote sites are not allowed when central site in license state unlicensed"
            ),
            id="CCE-unlicensed-CEE",
        ),
        pytest.param(
            Edition.ULTIMATE,
            LicenseState.UNLICENSED,
            Edition.ULTIMATE,
            LicenseState.LICENSED,
            LicenseStateIncompatible(
                "Remote sites are not allowed when central site in license state unlicensed"
            ),
            id="CCE-unlicensed-CCE",
        ),
        pytest.param(
            Edition.ULTIMATE,
            LicenseState.UNLICENSED,
            Edition.ULTIMATEMT,
            LicenseState.LICENSED,
            LicenseStateIncompatible(
                "Remote sites are not allowed when central site in license state unlicensed"
            ),
            id="CCE-unlicensed-CME",
        ),
        pytest.param(
            Edition.ULTIMATE,
            LicenseState.FREE,
            Edition.COMMUNITY,
            LicenseState.LICENSED,
            LicenseStateIncompatible(
                "Remote sites are not allowed when central site in license state free"
            ),
            id="CCE-free-CRE",
        ),
        pytest.param(
            Edition.ULTIMATE,
            LicenseState.FREE,
            Edition.PRO,
            LicenseState.LICENSED,
            LicenseStateIncompatible(
                "Remote sites are not allowed when central site in license state free"
            ),
            id="CCE-free-CEE",
        ),
        pytest.param(
            Edition.ULTIMATE,
            LicenseState.FREE,
            Edition.ULTIMATE,
            LicenseState.LICENSED,
            LicenseStateIncompatible(
                "Remote sites are not allowed when central site in license state free"
            ),
            id="CCE-free-CCE",
        ),
        pytest.param(
            Edition.ULTIMATE,
            LicenseState.FREE,
            Edition.ULTIMATEMT,
            LicenseState.LICENSED,
            LicenseStateIncompatible(
                "Remote sites are not allowed when central site in license state free"
            ),
            id="CCE-free-CME",
        ),
        pytest.param(
            Edition.ULTIMATEMT,
            LicenseState.LICENSED,
            Edition.COMMUNITY,
            LicenseState.LICENSED,
            EditionsIncompatible("Mix of CME and non-CME is not allowed."),
            id="CME-CRE",
        ),
        pytest.param(
            Edition.ULTIMATEMT,
            LicenseState.LICENSED,
            Edition.PRO,
            LicenseState.LICENSED,
            EditionsIncompatible("Mix of CME and non-CME is not allowed."),
            id="CME-CEE",
        ),
        pytest.param(
            Edition.ULTIMATEMT,
            LicenseState.LICENSED,
            Edition.ULTIMATE,
            LicenseState.LICENSED,
            EditionsIncompatible("Mix of CME and non-CME is not allowed."),
            id="CME-CCE",
        ),
        pytest.param(
            Edition.ULTIMATEMT,
            LicenseState.LICENSED,
            Edition.ULTIMATE,
            LicenseState.FREE,
            LicenseStateIncompatible("Remote site in license state free is not allowed"),
            id="CME-CCE-free",
        ),
        pytest.param(
            Edition.ULTIMATEMT,
            LicenseState.LICENSED,
            Edition.ULTIMATEMT,
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
            Edition.COMMUNITY,
            LicenseState.LICENSED,
            Edition.COMMUNITY,
            LicensingCompatible(),
            id="CRE-CRE",
        ),
        pytest.param(
            Edition.COMMUNITY,
            LicenseState.LICENSED,
            Edition.PRO,
            LicensingCompatible(),
            id="CRE-CEE",
        ),
        pytest.param(
            Edition.COMMUNITY,
            LicenseState.LICENSED,
            Edition.ULTIMATE,
            LicensingCompatible(),
            id="CRE-CCE",
        ),
        pytest.param(
            Edition.COMMUNITY,
            LicenseState.LICENSED,
            Edition.ULTIMATEMT,
            LicensingCompatible(),
            id="CRE-CME",
        ),
        pytest.param(
            Edition.PRO,
            LicenseState.LICENSED,
            Edition.COMMUNITY,
            LicensingCompatible(),
            id="CEE-CRE",
        ),
        pytest.param(
            Edition.PRO, LicenseState.LICENSED, Edition.PRO, LicensingCompatible(), id="CEE-CEE"
        ),
        pytest.param(
            Edition.PRO,
            LicenseState.LICENSED,
            Edition.ULTIMATE,
            LicensingCompatible(),
            id="CEE-CCE",
        ),
        pytest.param(
            Edition.PRO,
            LicenseState.LICENSED,
            Edition.ULTIMATEMT,
            LicensingCompatible(),
            id="CEE-CME",
        ),
        pytest.param(
            Edition.ULTIMATE,
            LicenseState.TRIAL,
            Edition.COMMUNITY,
            EditionsIncompatible("Only CCE remote sites can be added to CCE central site"),
            id="CCE-trial-CRE",
        ),
        pytest.param(
            Edition.ULTIMATE,
            LicenseState.TRIAL,
            Edition.PRO,
            EditionsIncompatible("Only CCE remote sites can be added to CCE central site"),
            id="CCE-trial-CEE",
        ),
        pytest.param(
            Edition.ULTIMATE,
            LicenseState.TRIAL,
            Edition.ULTIMATE,
            LicensingCompatible(),
            id="CCE-trial-CCE",
        ),
        pytest.param(
            Edition.ULTIMATE,
            LicenseState.TRIAL,
            Edition.ULTIMATEMT,
            EditionsIncompatible("Only CCE remote sites can be added to CCE central site"),
            id="CCE-trial-CME",
        ),
        pytest.param(
            Edition.ULTIMATE,
            LicenseState.LICENSED,
            Edition.COMMUNITY,
            EditionsIncompatible("Only CCE remote sites can be added to CCE central site"),
            id="CCE-licensed-CRE",
        ),
        pytest.param(
            Edition.ULTIMATE,
            LicenseState.LICENSED,
            Edition.PRO,
            EditionsIncompatible("Only CCE remote sites can be added to CCE central site"),
            id="CCE-licensed-CEE",
        ),
        pytest.param(
            Edition.ULTIMATE,
            LicenseState.LICENSED,
            Edition.ULTIMATE,
            LicensingCompatible(),
            id="CCE-licensed-CCE",
        ),
        pytest.param(
            Edition.ULTIMATE,
            LicenseState.LICENSED,
            Edition.ULTIMATEMT,
            EditionsIncompatible("Only CCE remote sites can be added to CCE central site"),
            id="CCE-licensed-CME",
        ),
        pytest.param(
            Edition.ULTIMATE,
            LicenseState.UNLICENSED,
            Edition.COMMUNITY,
            LicenseStateIncompatible(
                "Remote sites are not allowed when central site in license state unlicensed"
            ),
            id="CCE-unlicensed-CRE",
        ),
        pytest.param(
            Edition.ULTIMATE,
            LicenseState.UNLICENSED,
            Edition.PRO,
            LicenseStateIncompatible(
                "Remote sites are not allowed when central site in license state unlicensed"
            ),
            id="CCE-unlicensed-CEE",
        ),
        pytest.param(
            Edition.ULTIMATE,
            LicenseState.UNLICENSED,
            Edition.ULTIMATE,
            LicenseStateIncompatible(
                "Remote sites are not allowed when central site in license state unlicensed"
            ),
            id="CCE-unlicensed-CCE",
        ),
        pytest.param(
            Edition.ULTIMATE,
            LicenseState.UNLICENSED,
            Edition.ULTIMATEMT,
            LicenseStateIncompatible(
                "Remote sites are not allowed when central site in license state unlicensed"
            ),
            id="CCE-unlicensed-CME",
        ),
        pytest.param(
            Edition.ULTIMATE,
            LicenseState.FREE,
            Edition.COMMUNITY,
            LicenseStateIncompatible(
                "Remote sites are not allowed when central site in license state free"
            ),
            id="CCE-free-CRE",
        ),
        pytest.param(
            Edition.ULTIMATE,
            LicenseState.FREE,
            Edition.PRO,
            LicenseStateIncompatible(
                "Remote sites are not allowed when central site in license state free"
            ),
            id="CCE-free-CEE",
        ),
        pytest.param(
            Edition.ULTIMATE,
            LicenseState.FREE,
            Edition.ULTIMATE,
            LicenseStateIncompatible(
                "Remote sites are not allowed when central site in license state free"
            ),
            id="CCE-free-CCE",
        ),
        pytest.param(
            Edition.ULTIMATE,
            LicenseState.FREE,
            Edition.ULTIMATEMT,
            LicenseStateIncompatible(
                "Remote sites are not allowed when central site in license state free"
            ),
            id="CCE-free-CME",
        ),
        pytest.param(
            Edition.ULTIMATEMT,
            LicenseState.LICENSED,
            Edition.COMMUNITY,
            LicensingCompatible(),
            id="CME-CRE",
        ),
        pytest.param(
            Edition.ULTIMATEMT,
            LicenseState.LICENSED,
            Edition.PRO,
            LicensingCompatible(),
            id="CME-CEE",
        ),
        pytest.param(
            Edition.ULTIMATEMT,
            LicenseState.LICENSED,
            Edition.ULTIMATE,
            EditionsIncompatible("Mix of CME and non-CME is not allowed."),
            id="CME-CCE",
        ),
        pytest.param(
            Edition.ULTIMATEMT,
            LicenseState.LICENSED,
            Edition.ULTIMATEMT,
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
