#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disallow-any-generics
# mypy: disallow-any-decorated
# mypy: disallow-any-unimported
# mypy: disallow-subclassing-any
import os
import sys
import traceback
from pathlib import Path

from omdlib.utils import get_site_distributed_setup, SiteDistributedSetup

from cmk.utils.paths import diskspace_config_dir

# TODO: The diskspace tool depends on `check_mk` as a cli tool. Therefore, having the
# "site context" as a dependency is probably appropriate. It could be moved to `cmk/diskspace`,
# but that is also suboptimal, since the tool depends on `omdlib`.
# pylint: disable=cmk-module-layer-violation
from cmk.diskspace.abandoned import do_cleanup_abandoned_host_files
from cmk.diskspace.config import read_config
from cmk.diskspace.file import cleanup_aged, cleanup_oldest_files, load_plugins
from cmk.diskspace.free_space import fmt_bytes, get_free_space
from cmk.diskspace.logging import error, print_config, setup_logging, verbose


def main() -> None:
    omd_root = Path(os.environ["OMD_ROOT"])
    setup_logging("-v" in sys.argv)
    config = read_config(diskspace_config_dir)
    print_config(config)
    infos = load_plugins(omd_root, omd_root / "share/diskspace", omd_root / "local/share/diskspace")

    if config.cleanup_abandoned_host_files:
        do_cleanup_abandoned_host_files(
            omd_root,
            get_site_distributed_setup() == SiteDistributedSetup.DISTRIBUTED_REMOTE,
            config.cleanup_abandoned_host_files,
        )

    # get used disk space of the sites volume
    bytes_free = get_free_space(omd_root)
    verbose(f"Free space: {fmt_bytes(bytes_free)}")

    cleanup_aged(omd_root, config.max_file_age, infos)
    cleanup_oldest_files(omd_root, "-f" in sys.argv, config.min_free_bytes, infos)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        error(f"Unexpected exception: {traceback.format_exc()}")
        sys.exit(1)
