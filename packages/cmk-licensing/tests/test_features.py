#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

import pytest

from cmk.ccc.version import Edition
from cmk.licensing.basics.features import FeatureFlag, Features, licensed_features


def test_community() -> None:
    assert licensed_features(Path(), Edition.COMMUNITY) == Features(
        bakery=FeatureFlag(enabled=False),
        extended_metric_backend=FeatureFlag(enabled=False),
    )


def test_pro() -> None:
    assert licensed_features(Path(), Edition.PRO) == Features(
        bakery=FeatureFlag(enabled=True),
        extended_metric_backend=FeatureFlag(enabled=False),
    )


@pytest.mark.parametrize(
    "edition",
    [e for e in Edition if e not in [Edition.COMMUNITY, Edition.PRO]],
)
def test_commercial(edition: Edition) -> None:
    assert licensed_features(Path(), edition) == Features(
        bakery=FeatureFlag(enabled=True),
        extended_metric_backend=FeatureFlag(enabled=True),
    )
