#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import argparse
import os
import sys
from pathlib import Path

from cmk.ccc.site import omd_site
from cmk.licensing.basics.paths import (
    get_instance_id_file_path,
    get_next_run_file_path,
)
from cmk.licensing.helper import (
    hash_site_id,
    init_logging,
    load_instance_id,
)
from cmk.licensing.usage import (
    create_sample,
    Now,
    try_update_license_usage,
)


def _parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawTextHelpFormatter,
        allow_abbrev=False,
    )
    parser.add_argument(
        "--force",
        action="store_true",
        default=False,
        help="Force a license usage update, ie. ignoring the next scheduled update.",
    )
    return parser.parse_args()


def _omd_root() -> Path:
    try:
        return Path(os.environ["OMD_ROOT"])
    except KeyError as exc:
        raise RuntimeError(
            "OMD_ROOT environment variable not set. Can only be executed in a Checkmk site."
        ) from exc


def main() -> int:
    args = _parse_arguments()
    omd_root = _omd_root()
    logger = init_logging(omd_root / "var" / "log")

    if args.force:
        get_next_run_file_path(omd_root).unlink(missing_ok=True)

    try:
        try_update_license_usage(
            Now.make(),
            load_instance_id(get_instance_id_file_path(omd_root)),
            hash_site_id(omd_site()),
            lambda now, instance_id, site_hash: create_sample(
                now, instance_id, site_hash, omd_root=omd_root, logger=logger
            ),
            omd_root=omd_root,
        )
        logger.info("Successfully updated the license usage")
        return 0
    except Exception:
        logger.exception("Error during license usage update")
        return 1


if __name__ == "__main__":
    sys.exit(main())
