#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import sys

from cmk.update_config.https.arguments import (
    Activate,
    Args,
    Deactivate,
    Delete,
    Finalize,
    Migrate,
    parse_arguments,
)


def _preamble(args: Args) -> None:
    if isinstance(args, Finalize):
        continue_ = input(
            "This action will delete existing v1 rules and remove any references from the newly created v2 rules. After that, no action (e.g., activating or deleting) can be taken on the v2 rules by the script. It cannot be undone. Proceed by typing 'Yes': "
        )
        if continue_.strip().lower() != "yes":
            sys.stdout.write("Aborted.\n")
            sys.exit(0)
    if isinstance(args, Migrate) and not args.write:
        sys.stdout.write("Starting dry run.\n")


def main() -> None:
    args = parse_arguments()
    _preamble(args)
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
