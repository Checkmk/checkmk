#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import assert_never

from omdlib.args_site_user import Backup, Copy, Move, parse_arguments, Restore
from omdlib.backup import main_site_backup
from omdlib.main import main_finalize_copy, main_finalize_move, main_finalize_restore
from omdlib.site_name import site_name_from_uid


def main() -> int:
    args = parse_arguments()
    assert args.site == site_name_from_uid()

    match args:
        case Restore():
            return main_finalize_restore(args)
        case Move():
            return main_finalize_move(args)
        case Copy():
            return main_finalize_copy(args)
        case Backup():
            return main_site_backup(args)
        case _args:
            assert_never(_args)


if __name__ == "__main__":
    main()
