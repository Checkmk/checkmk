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
    "central_edition, central_license_state, remote_edition, remote_license_state, is_replication_enabled, expected_compatibility",
    [
        pytest.param(
            Edition.COMMUNITY,
            LicenseState.LICENSED,
            Edition.COMMUNITY,
            LicenseState.LICENSED,
            True,
            LicensingCompatible(),
            id="community-community",
        ),
        pytest.param(
            Edition.COMMUNITY,
            LicenseState.LICENSED,
            Edition.PRO,
            LicenseState.LICENSED,
            True,
            LicensingCompatible(),
            id="community-pro",
        ),
        pytest.param(
            Edition.COMMUNITY,
            LicenseState.LICENSED,
            Edition.ULTIMATE,
            LicenseState.LICENSED,
            True,
            LicensingCompatible(),
            id="community-ultimate",
        ),
        pytest.param(
            Edition.COMMUNITY,
            LicenseState.LICENSED,
            Edition.ULTIMATE,
            LicenseState.FREE,
            True,
            LicenseStateIncompatible("Remote site in license state free is not allowed"),
            id="community-ultimate-free",
        ),
        pytest.param(
            Edition.COMMUNITY,
            LicenseState.LICENSED,
            Edition.ULTIMATEMT,
            LicenseState.LICENSED,
            True,
            EditionsIncompatible(
                "Mix of Checkmk Ultimate and Checkmk Ultimate with Multi-Tenancy is not possible."
            ),
            id="community-ultimatemt",
        ),
        pytest.param(
            Edition.PRO,
            LicenseState.LICENSED,
            Edition.COMMUNITY,
            LicenseState.LICENSED,
            True,
            LicensingCompatible(),
            id="pro-community",
        ),
        pytest.param(
            Edition.PRO,
            LicenseState.LICENSED,
            Edition.PRO,
            LicenseState.LICENSED,
            True,
            LicensingCompatible(),
            id="pro-pro",
        ),
        pytest.param(
            Edition.PRO,
            LicenseState.LICENSED,
            Edition.ULTIMATE,
            LicenseState.LICENSED,
            True,
            LicensingCompatible(),
            id="pro-ultimate",
        ),
        pytest.param(
            Edition.PRO,
            LicenseState.LICENSED,
            Edition.ULTIMATE,
            LicenseState.FREE,
            True,
            LicenseStateIncompatible("Remote site in license state free is not allowed"),
            id="pro-ultimate-free",
        ),
        pytest.param(
            Edition.PRO,
            LicenseState.LICENSED,
            Edition.ULTIMATEMT,
            LicenseState.LICENSED,
            True,
            EditionsIncompatible(
                "Mix of Checkmk Ultimate and Checkmk Ultimate with Multi-Tenancy is not possible."
            ),
            id="pro-ultimatemt",
        ),
        pytest.param(
            Edition.ULTIMATE,
            LicenseState.TRIAL,
            Edition.COMMUNITY,
            LicenseState.LICENSED,
            True,
            EditionsIncompatible(
                "A Checkmk Ultimate central site can only have remote sites with Checkmk Ultimate "
                "or Checkmk Pro/Community remote sites without configuration replication."
            ),
            id="ultimate-trial-community",
        ),
        pytest.param(
            Edition.ULTIMATE,
            LicenseState.TRIAL,
            Edition.PRO,
            LicenseState.LICENSED,
            True,
            EditionsIncompatible(
                "A Checkmk Ultimate central site can only have remote sites with Checkmk Ultimate "
                "or Checkmk Pro/Community remote sites without configuration replication."
            ),
            id="ultimate-trial-pro",
        ),
        pytest.param(
            Edition.ULTIMATE,
            LicenseState.TRIAL,
            Edition.ULTIMATE,
            LicenseState.LICENSED,
            True,
            LicensingCompatible(),
            id="ultimate-trial-ultimate",
        ),
        pytest.param(
            Edition.ULTIMATE,
            LicenseState.LICENSED,
            Edition.ULTIMATE,
            LicenseState.FREE,
            True,
            LicenseStateIncompatible("Remote site in license state free is not allowed"),
            id="ultimate-ultimate-free",
        ),
        pytest.param(
            Edition.ULTIMATE,
            LicenseState.TRIAL,
            Edition.ULTIMATEMT,
            LicenseState.LICENSED,
            True,
            EditionsIncompatible(
                "A Checkmk Ultimate central site can only have remote sites with Checkmk Ultimate "
                "or Checkmk Pro/Community remote sites without configuration replication."
            ),
            id="ultimate-trial-ultimatemt",
        ),
        pytest.param(
            Edition.ULTIMATE,
            LicenseState.LICENSED,
            Edition.COMMUNITY,
            LicenseState.LICENSED,
            True,
            EditionsIncompatible(
                "A Checkmk Ultimate central site can only have remote sites with Checkmk Ultimate "
                "or Checkmk Pro/Community remote sites without configuration replication."
            ),
            id="ultimate-licensed-community",
        ),
        pytest.param(
            Edition.ULTIMATE,
            LicenseState.LICENSED,
            Edition.PRO,
            LicenseState.LICENSED,
            True,
            EditionsIncompatible(
                "A Checkmk Ultimate central site can only have remote sites with Checkmk Ultimate "
                "or Checkmk Pro/Community remote sites without configuration replication."
            ),
            id="ultimate-licensed-pro",
        ),
        pytest.param(
            Edition.ULTIMATE,
            LicenseState.LICENSED,
            Edition.ULTIMATE,
            LicenseState.LICENSED,
            True,
            LicensingCompatible(),
            id="ultimate-licensed-ultimate",
        ),
        pytest.param(
            Edition.ULTIMATE,
            LicenseState.LICENSED,
            Edition.ULTIMATEMT,
            LicenseState.LICENSED,
            True,
            EditionsIncompatible(
                "A Checkmk Ultimate central site can only have remote sites with Checkmk Ultimate "
                "or Checkmk Pro/Community remote sites without configuration replication."
            ),
            id="ultimate-licensed-ultimatemt",
        ),
        pytest.param(
            Edition.ULTIMATE,
            LicenseState.UNLICENSED,
            Edition.COMMUNITY,
            LicenseState.LICENSED,
            True,
            LicenseStateIncompatible(
                "Remote sites are not allowed when central site in license state unlicensed"
            ),
            id="ultimate-unlicensed-community",
        ),
        pytest.param(
            Edition.ULTIMATE,
            LicenseState.UNLICENSED,
            Edition.PRO,
            LicenseState.LICENSED,
            True,
            LicenseStateIncompatible(
                "Remote sites are not allowed when central site in license state unlicensed"
            ),
            id="ultimate-unlicensed-pro",
        ),
        pytest.param(
            Edition.ULTIMATE,
            LicenseState.UNLICENSED,
            Edition.ULTIMATE,
            LicenseState.LICENSED,
            True,
            LicenseStateIncompatible(
                "Remote sites are not allowed when central site in license state unlicensed"
            ),
            id="ultimate-unlicensed-ultimate",
        ),
        pytest.param(
            Edition.ULTIMATE,
            LicenseState.UNLICENSED,
            Edition.ULTIMATEMT,
            LicenseState.LICENSED,
            True,
            LicenseStateIncompatible(
                "Remote sites are not allowed when central site in license state unlicensed"
            ),
            id="ultimate-unlicensed-ultimatemt",
        ),
        pytest.param(
            Edition.ULTIMATE,
            LicenseState.FREE,
            Edition.COMMUNITY,
            LicenseState.LICENSED,
            True,
            LicenseStateIncompatible(
                "Remote sites are not allowed when central site in license state free"
            ),
            id="ultimate-free-community",
        ),
        pytest.param(
            Edition.ULTIMATE,
            LicenseState.FREE,
            Edition.PRO,
            LicenseState.LICENSED,
            True,
            LicenseStateIncompatible(
                "Remote sites are not allowed when central site in license state free"
            ),
            id="ultimate-free-pro",
        ),
        pytest.param(
            Edition.ULTIMATE,
            LicenseState.FREE,
            Edition.ULTIMATE,
            LicenseState.LICENSED,
            True,
            LicenseStateIncompatible(
                "Remote sites are not allowed when central site in license state free"
            ),
            id="ultimate-free-ultimate",
        ),
        pytest.param(
            Edition.ULTIMATE,
            LicenseState.FREE,
            Edition.ULTIMATEMT,
            LicenseState.LICENSED,
            True,
            LicenseStateIncompatible(
                "Remote sites are not allowed when central site in license state free"
            ),
            id="ultimate-free-ultimatemt",
        ),
        pytest.param(
            Edition.ULTIMATEMT,
            LicenseState.LICENSED,
            Edition.COMMUNITY,
            LicenseState.LICENSED,
            True,
            EditionsIncompatible(
                "Mix of Checkmk Ultimate and Checkmk Ultimate with Multi-Tenancy is not possible."
            ),
            id="ultimatemt-community",
        ),
        pytest.param(
            Edition.ULTIMATEMT,
            LicenseState.LICENSED,
            Edition.PRO,
            LicenseState.LICENSED,
            True,
            EditionsIncompatible(
                "Mix of Checkmk Ultimate and Checkmk Ultimate with Multi-Tenancy is not possible."
            ),
            id="ultimatemt-pro",
        ),
        pytest.param(
            Edition.ULTIMATEMT,
            LicenseState.LICENSED,
            Edition.ULTIMATE,
            LicenseState.LICENSED,
            True,
            EditionsIncompatible(
                "Mix of Checkmk Ultimate and Checkmk Ultimate with Multi-Tenancy is not possible."
            ),
            id="ultimatemt-ultimate",
        ),
        pytest.param(
            Edition.ULTIMATEMT,
            LicenseState.LICENSED,
            Edition.ULTIMATE,
            LicenseState.FREE,
            True,
            LicenseStateIncompatible("Remote site in license state free is not allowed"),
            id="ultimatemt-ultimate-free",
        ),
        pytest.param(
            Edition.ULTIMATEMT,
            LicenseState.LICENSED,
            Edition.ULTIMATEMT,
            LicenseState.LICENSED,
            True,
            LicensingCompatible(),
            id="ultimatemt-ultimatemt",
        ),
        pytest.param(
            Edition.ULTIMATE,
            LicenseState.LICENSED,
            Edition.COMMUNITY,
            LicenseState.LICENSED,
            False,
            LicensingCompatible(),
            id="ultimate-community",
        ),
        pytest.param(
            Edition.ULTIMATE,
            LicenseState.LICENSED,
            Edition.PRO,
            LicenseState.LICENSED,
            False,
            LicensingCompatible(),
            id="ultimate-pro",
        ),
    ],
)
def test_license_compatibility_distributed_setup(
    central_edition: Edition,
    central_license_state: LicenseState,
    remote_edition: Edition,
    remote_license_state: LicenseState,
    is_replication_enabled: bool,
    expected_compatibility: LicensingCompatibility,
) -> None:
    actual_compatibility = is_distributed_setup_compatible_for_licensing(
        central_edition,
        central_license_state,
        remote_edition,
        remote_license_state,
        is_replication_enabled,
    )
    assert isinstance(actual_compatibility, type(expected_compatibility))
    if not isinstance(expected_compatibility, LicensingCompatible) and not isinstance(
        actual_compatibility, LicensingCompatible
    ):
        assert actual_compatibility._reason == expected_compatibility._reason


@pytest.mark.parametrize(
    "central_edition, central_license_state, remote_edition, is_replication_enabled, expected_compatibility",
    [
        pytest.param(
            Edition.COMMUNITY,
            LicenseState.LICENSED,
            Edition.COMMUNITY,
            False,
            LicensingCompatible(),
            id="community-community",
        ),
        pytest.param(
            Edition.COMMUNITY,
            LicenseState.LICENSED,
            Edition.PRO,
            False,
            LicensingCompatible(),
            id="community-pro",
        ),
        pytest.param(
            Edition.COMMUNITY,
            LicenseState.LICENSED,
            Edition.ULTIMATE,
            False,
            LicensingCompatible(),
            id="community-ultimate",
        ),
        pytest.param(
            Edition.COMMUNITY,
            LicenseState.LICENSED,
            Edition.ULTIMATEMT,
            False,
            LicensingCompatible(),
            id="community-ultimatemt",
        ),
        pytest.param(
            Edition.PRO,
            LicenseState.LICENSED,
            Edition.COMMUNITY,
            False,
            LicensingCompatible(),
            id="pro-community",
        ),
        pytest.param(
            Edition.PRO,
            LicenseState.LICENSED,
            Edition.PRO,
            False,
            LicensingCompatible(),
            id="pro-pro",
        ),
        pytest.param(
            Edition.PRO,
            LicenseState.LICENSED,
            Edition.ULTIMATE,
            False,
            LicensingCompatible(),
            id="pro-ultimate",
        ),
        pytest.param(
            Edition.PRO,
            LicenseState.LICENSED,
            Edition.ULTIMATEMT,
            False,
            LicensingCompatible(),
            id="pro-ultimatemt",
        ),
        pytest.param(
            Edition.ULTIMATE,
            LicenseState.LICENSED,
            Edition.COMMUNITY,
            False,
            LicensingCompatible(),
            id="ultimate-community",
        ),
        pytest.param(
            Edition.ULTIMATE,
            LicenseState.LICENSED,
            Edition.PRO,
            False,
            LicensingCompatible(),
            id="ultimate-pro",
        ),
        pytest.param(
            Edition.ULTIMATE,
            LicenseState.TRIAL,
            Edition.COMMUNITY,
            True,
            EditionsIncompatible(
                "A Checkmk Ultimate central site can only have remote sites with Checkmk Ultimate "
                "or Checkmk Pro/Community remote sites without configuration replication."
            ),
            id="ultimate-trial-community",
        ),
        pytest.param(
            Edition.ULTIMATE,
            LicenseState.TRIAL,
            Edition.PRO,
            True,
            EditionsIncompatible(
                "A Checkmk Ultimate central site can only have remote sites with Checkmk Ultimate "
                "or Checkmk Pro/Community remote sites without configuration replication."
            ),
            id="ultimate-trial-pro",
        ),
        pytest.param(
            Edition.ULTIMATE,
            LicenseState.TRIAL,
            Edition.ULTIMATE,
            False,
            LicensingCompatible(),
            id="ultimate-trial-ultimate",
        ),
        pytest.param(
            Edition.ULTIMATE,
            LicenseState.TRIAL,
            Edition.ULTIMATEMT,
            False,
            EditionsIncompatible(
                "A Checkmk Ultimate central site can only have remote sites with Checkmk Ultimate "
                "or Checkmk Pro/Community remote sites without configuration replication."
            ),
            id="ultimate-trial-ultimatemt",
        ),
        pytest.param(
            Edition.ULTIMATE,
            LicenseState.LICENSED,
            Edition.COMMUNITY,
            True,
            EditionsIncompatible(
                "A Checkmk Ultimate central site can only have remote sites with Checkmk Ultimate "
                "or Checkmk Pro/Community remote sites without configuration replication."
            ),
            id="ultimate-licensed-community",
        ),
        pytest.param(
            Edition.ULTIMATE,
            LicenseState.LICENSED,
            Edition.PRO,
            True,
            EditionsIncompatible(
                "A Checkmk Ultimate central site can only have remote sites with Checkmk Ultimate "
                "or Checkmk Pro/Community remote sites without configuration replication."
            ),
            id="ultimate-licensed-pro",
        ),
        pytest.param(
            Edition.ULTIMATE,
            LicenseState.LICENSED,
            Edition.ULTIMATE,
            False,
            LicensingCompatible(),
            id="ultimate-licensed-ultimate",
        ),
        pytest.param(
            Edition.ULTIMATE,
            LicenseState.LICENSED,
            Edition.ULTIMATEMT,
            False,
            EditionsIncompatible(
                "A Checkmk Ultimate central site can only have remote sites with Checkmk Ultimate "
                "or Checkmk Pro/Community remote sites without configuration replication."
            ),
            id="ultimate-licensed-ultimatemt",
        ),
        pytest.param(
            Edition.ULTIMATE,
            LicenseState.UNLICENSED,
            Edition.COMMUNITY,
            False,
            LicenseStateIncompatible(
                "Remote sites are not allowed when central site in license state unlicensed"
            ),
            id="ultimate-unlicensed-community",
        ),
        pytest.param(
            Edition.ULTIMATE,
            LicenseState.UNLICENSED,
            Edition.PRO,
            False,
            LicenseStateIncompatible(
                "Remote sites are not allowed when central site in license state unlicensed"
            ),
            id="ultimate-unlicensed-pro",
        ),
        pytest.param(
            Edition.ULTIMATE,
            LicenseState.UNLICENSED,
            Edition.ULTIMATE,
            False,
            LicenseStateIncompatible(
                "Remote sites are not allowed when central site in license state unlicensed"
            ),
            id="ultimate-unlicensed-ultimate",
        ),
        pytest.param(
            Edition.ULTIMATE,
            LicenseState.UNLICENSED,
            Edition.ULTIMATEMT,
            False,
            LicenseStateIncompatible(
                "Remote sites are not allowed when central site in license state unlicensed"
            ),
            id="ultimate-unlicensed-ultimatemt",
        ),
        pytest.param(
            Edition.ULTIMATE,
            LicenseState.FREE,
            Edition.COMMUNITY,
            False,
            LicenseStateIncompatible(
                "Remote sites are not allowed when central site in license state free"
            ),
            id="ultimate-free-community",
        ),
        pytest.param(
            Edition.ULTIMATE,
            LicenseState.FREE,
            Edition.PRO,
            False,
            LicenseStateIncompatible(
                "Remote sites are not allowed when central site in license state free"
            ),
            id="ultimate-free-pro",
        ),
        pytest.param(
            Edition.ULTIMATE,
            LicenseState.FREE,
            Edition.ULTIMATE,
            False,
            LicenseStateIncompatible(
                "Remote sites are not allowed when central site in license state free"
            ),
            id="ultimate-free-ultimate",
        ),
        pytest.param(
            Edition.ULTIMATE,
            LicenseState.FREE,
            Edition.ULTIMATEMT,
            False,
            LicenseStateIncompatible(
                "Remote sites are not allowed when central site in license state free"
            ),
            id="ultimate-free-ultimatemt",
        ),
        pytest.param(
            Edition.ULTIMATEMT,
            LicenseState.LICENSED,
            Edition.COMMUNITY,
            False,
            LicensingCompatible(),
            id="ultimatemt-community",
        ),
        pytest.param(
            Edition.ULTIMATEMT,
            LicenseState.LICENSED,
            Edition.PRO,
            False,
            LicensingCompatible(),
            id="ultimatemt-pro",
        ),
        pytest.param(
            Edition.ULTIMATEMT,
            LicenseState.LICENSED,
            Edition.ULTIMATE,
            False,
            EditionsIncompatible(
                "Mix of Checkmk Ultimate and Checkmk Ultimate with Multi-Tenancy is not possible."
            ),
            id="ultimatemt-ultimate",
        ),
        pytest.param(
            Edition.ULTIMATEMT,
            LicenseState.LICENSED,
            Edition.ULTIMATEMT,
            False,
            LicensingCompatible(),
            id="ultimatemt-ultimatemt",
        ),
    ],
)
def test_license_compatibility_distributed_monitoring(
    central_edition: Edition,
    central_license_state: LicenseState,
    remote_edition: Edition,
    is_replication_enabled: bool,
    expected_compatibility: LicensingCompatibility,
) -> None:
    actual_compatibility = is_distributed_monitoring_compatible_for_licensing(
        central_edition,
        central_license_state,
        remote_edition,
        is_replication_enabled,
    )

    assert isinstance(actual_compatibility, type(expected_compatibility))
    if not isinstance(expected_compatibility, LicensingCompatible) and not isinstance(
        actual_compatibility, LicensingCompatible
    ):
        assert actual_compatibility._reason == expected_compatibility._reason
