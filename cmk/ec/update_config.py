#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Functions for the cmk-update-config to be used in cmk/update_config/plugins/actions/ec_history.py"""

import logging
import time
from datetime import timedelta
from pathlib import Path

from cmk.utils.store import save_to_mk_file

import cmk.ec.export as ec

from .history_file import parse_history_file_python
from .history_sqlite import SQLiteHistory
from .main import create_history, make_config, StatusTableEvents, StatusTableHistory
from .settings import create_paths, create_settings


def history_files_to_sqlite(omd_root: Path, logger: logging.Logger) -> None:
    """Read history files one by one in the folder and write their contents into sqlite database.

    Is run by the update_ec_history action of cmk-update-config.

    """
    tic = time.time()

    save_to_mk_file(
        omd_root / "etc/check_mk/mkeventd.d/enable_sqlite.mk",
        "archive_mode",
        "sqlite",
    )

    history_dir = create_paths(omd_root).history_dir.value
    settings = create_settings("1.2.3i45", omd_root, ["mkeventd"])
    config = make_config(ec.default_config())
    logger = logging.getLogger("cmk.mkeventd")

    history_sqlite = create_history(
        settings,
        {**config, "archive_mode": "sqlite"},
        logger,
        StatusTableEvents.columns,
        StatusTableHistory.columns,
    )

    assert isinstance(history_sqlite, SQLiteHistory)

    logger.info("Processing files in history_dir %s", history_dir)
    for file in sorted(history_dir.glob("*.log"), reverse=True):
        for parsed_entries in parse_history_file_python(
            StatusTableHistory.columns,
            file,
            logger,
        ):
            history_sqlite._add_entry(parsed_entries)

        # processed files are not needed anymore
        logger.info("Renaming file %s", file)
        file.rename(file.with_suffix(".bak"))
    logger.info("history_files_to_sqlite took: %s", str(timedelta(seconds=time.time() - tic)))
