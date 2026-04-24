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
    )


@pytest.mark.parametrize(
    "edition",
    [e for e in Edition if e is not Edition.COMMUNITY],
)
def test_commercial(edition: Edition) -> None:
    # NOTE: this will go away soon
    assert licensed_features(Path(), edition) == Features(
        bakery=FeatureFlag(enabled=True),
    )
