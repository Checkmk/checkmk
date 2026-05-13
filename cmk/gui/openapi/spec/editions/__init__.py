#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Slim per-edition registration for the OpenAPI spec generator.

This is a separate registration path from :func:`cmk.gui.main_modules.register`,
which loads every GUI feature. For spec generation we populate only the registries the
spec generator reads - currently the three OpenAPI endpoint registries plus
``permission_registry`` and ``permission_section_registry``.

Each edition lives in its own subpackage and exposes a ``register_for_<edition>()``
function that calls only the feature-local openapi + permission registration entry
points.
"""

from typing import assert_never

from cmk.ccc.version import Edition


def register(edition: Edition) -> None:
    match edition:
        case Edition.COMMUNITY:
            from .community import (  # type: ignore[import-not-found, unused-ignore]
                register_for_community,
            )

            register_for_community()
        case Edition.PRO:
            from .nonfree.pro import (  # type: ignore[import-not-found, unused-ignore]
                register_for_pro,
            )

            register_for_pro()
        case Edition.ULTIMATE:
            from .nonfree.ultimate import (  # type: ignore[import-not-found, unused-ignore]
                register_for_ultimate,
            )

            register_for_ultimate()
        case Edition.CLOUD:
            from .nonfree.cloud import (  # type: ignore[import-not-found, unused-ignore]
                register_for_cloud,
            )

            register_for_cloud()
        case Edition.ULTIMATEMT:
            from .nonfree.ultimatemt import (  # type: ignore[import-not-found, unused-ignore]
                register_for_ultimatemt,
            )

            register_for_ultimatemt()
        case _ as unreachable:
            assert_never(unreachable)
