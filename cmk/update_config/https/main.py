#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import sys

from cmk.update_config.https.arguments import (
    Activate,
    Deactivate,
    Delete,
    Finalize,
    Migrate,
    parse_arguments,
)


def main() -> None:
    args = parse_arguments()
    sys.stdout.write("Importing...\n")
    from cmk.update_config.https import commands

    match args:
        case Migrate(write=write):
            commands.migrate_main(args, args, write)
        case Activate():
            commands.activate_main(args)
        case Deactivate():
            commands.deactivate_main(args)
        case Delete():
            commands.delete_main(args)
        case Finalize():
            commands.finalize_main(args)


if __name__ == "__main__":
    main()
