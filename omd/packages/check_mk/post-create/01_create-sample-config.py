#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Initialize the Checkmk default configuration in case it is necessary."""

# pylint: disable=cmk-module-layer-violation

import argparse
import sys

from cmk.utils import log

from cmk.gui import main_modules
from cmk.gui.session import SuperUserContext
from cmk.gui.utils.script_helpers import gui_context
from cmk.gui.watolib.sample_config import init_wato_datastructures


def parse_arguments(args: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        help="Verbose mode (use multiple times for more output)",
    )

    return p.parse_args(args)


def main(args: list[str]) -> int:
    arguments = parse_arguments(args)
    log.setup_console_logging()
    log.logger.setLevel(log.verbosity_to_log_level(arguments.verbose))

    main_modules.load_plugins()
    with gui_context(), SuperUserContext():
        init_wato_datastructures()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
