#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from pathlib import Path

from cmk.fetchers import AdHocSecrets
from cmk.password_store.v1_unstable import Secret


def test_ad_hoc_secrets_serialization() -> None:
    secrets = AdHocSecrets(
        path=Path("/what/a/beautiful/day"), secrets={"my_secret": Secret("I always loved you")}
    )

    assert secrets == AdHocSecrets.deserialize(secrets.serialize())
