#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.update_config.https.arguments import (
    Activate,
    Deactivate,
    Delete,
    Finalize,
    Migrate,
    parse_arguments,
)
from cmk.update_config.https.commands import (
    activate_main,
    deactivate_main,
    delete_main,
    finalize_main,
    migrate_main,
)


def main() -> None:
    args = parse_arguments()
    match args:
        case Migrate(write=write):
            migrate_main(args, args, write)
        case Activate():
            activate_main(args)
        case Deactivate():
            deactivate_main(args)
        case Delete():
            delete_main(args)
        case Finalize():
            finalize_main(args)


if __name__ == "__main__":
    main()
