#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
from pathlib import Path
from typing import Final

from cmk.cli.internal import Context as CLIContext
from cmk.cli.internal import GlobalOptions as CLIGlobalOptions

OMD_ROOT: Final = Path("/omd/sites/mysite")


def context(*, debug: bool = False) -> CLIContext:
    return CLIContext(
        omd_root=OMD_ROOT,
        global_options=CLIGlobalOptions(debug=debug),
        logger=logging.getLogger(__name__),
    )
