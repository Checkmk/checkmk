#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable
from typing import assert_never

from cmk.ccc.version import Edition

from .base_app import CheckmkBaseApp


def make_app(edition: Edition) -> CheckmkBaseApp:
    make_app: Callable[[], CheckmkBaseApp]
    match edition:
        case Edition.PRO:
            from cmk.base.nonfree.pro.app import (  # type: ignore[import-not-found, import-untyped, unused-ignore]
                make_app,
            )
        case Edition.ULTIMATEMT:
            from cmk.base.nonfree.ultimatemt.app import (  # type: ignore[import-not-found, import-untyped, unused-ignore]
                make_app,
            )
        case Edition.ULTIMATE:
            from cmk.base.nonfree.ultimate.app import (  # type: ignore[import-not-found, import-untyped, unused-ignore]
                make_app,
            )
        case Edition.CLOUD:
            from cmk.base.nonfree.cloud.app import (  # type: ignore[import-not-found, import-untyped, unused-ignore]
                make_app,
            )

        case Edition.COMMUNITY:
            from cmk.base.community_app import make_app

        case _ as unreachable:
            assert_never(unreachable)

    return make_app()
