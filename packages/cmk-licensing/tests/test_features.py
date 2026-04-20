#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.ccc.version import Edition
from cmk.licensing.community_handler import CommunityLicensingHandler
from cmk.licensing.features import FeatureFlag, Features, licensed_features


def test_community() -> None:
    assert licensed_features(
        edition=Edition.COMMUNITY,
        licensing_handler=CommunityLicensingHandler(),
    ) == Features(
        bakery=FeatureFlag(enabled=False),
    )


def test_pro() -> None:
    assert licensed_features(
        edition=Edition.PRO,
        # The handler type is not relevant for the test currently
        licensing_handler=CommunityLicensingHandler(),
    ) == Features(
        bakery=FeatureFlag(enabled=True),
    )


def test_cloud() -> None:
    assert licensed_features(
        edition=Edition.CLOUD,
        # The handler type is not relevant for the test currently
        licensing_handler=CommunityLicensingHandler(),
    ) == Features(
        bakery=FeatureFlag(enabled=True),
    )


def test_ultimate() -> None:
    assert licensed_features(
        edition=Edition.ULTIMATE,
        # The handler type is not relevant for the test currently
        licensing_handler=CommunityLicensingHandler(),
    ) == Features(
        bakery=FeatureFlag(enabled=True),
    )


def test_ultimatemt() -> None:
    assert licensed_features(
        edition=Edition.ULTIMATEMT,
        # The handler type is not relevant for the test currently
        licensing_handler=CommunityLicensingHandler(),
    ) == Features(
        bakery=FeatureFlag(enabled=True),
    )
