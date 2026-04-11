#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import assert_never

from cmk.ccc.version import Edition
from cmk.gui.utils import get_failed_plugins as get_failed_plugins

_registered_edition: Edition | None = None


def register(edition: Edition) -> None:
    global _registered_edition
    if _registered_edition is not None:
        if _registered_edition is not edition:
            raise RuntimeError(
                f"main_modules.register() called with {edition!r}, "
                f"but was already registered with {_registered_edition!r}"
            )
        return
    _registered_edition = edition

    match edition:
        case Edition.PRO:
            import cmk.gui.nonfree.pro.registration  # type: ignore[import-not-found, import-untyped, unused-ignore]

            cmk.gui.nonfree.pro.registration.register(edition)

        case Edition.ULTIMATEMT:
            import cmk.gui.nonfree.ultimatemt.registration  # type: ignore[import-not-found, import-untyped, unused-ignore]

            cmk.gui.nonfree.ultimatemt.registration.register(edition)

        case Edition.ULTIMATE:
            import cmk.gui.nonfree.ultimate.registration  # type: ignore[import-not-found, import-untyped, unused-ignore]

            cmk.gui.nonfree.ultimate.registration.register(edition)

        case Edition.CLOUD:
            import cmk.gui.nonfree.cloud.registration  # type: ignore[import-not-found, import-untyped, unused-ignore]

            cmk.gui.nonfree.cloud.registration.register(edition)

        case Edition.COMMUNITY:
            import cmk.gui.community_registration

            cmk.gui.community_registration.register(edition)

        case _ as unreachable:
            assert_never(unreachable)
