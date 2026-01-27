#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from omdlib.args_site_user import parse_arguments, Restore
from omdlib.main import main_finalize_restore
from omdlib.site_name import site_name_from_uid


def main() -> int:
    args = parse_arguments()
    assert args.site == site_name_from_uid()

    match args:
        case Restore():
            return main_finalize_restore(args)
        case _:
            raise NotImplementedError()


if __name__ == "__main__":
    main()
