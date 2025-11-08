#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import assert_never

import cmk.ccc.version as cmk_version
from cmk.ccc.version import Edition
from cmk.gui.utils import get_failed_plugins as get_failed_plugins
from cmk.utils import paths

match edition := cmk_version.edition(paths.omd_root):
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
