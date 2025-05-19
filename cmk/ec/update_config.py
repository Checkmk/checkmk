#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Functions for the cmk-update-config to be used in cmk/update_config/plugins/actions/ec_history.py."""

import logging
import time
from datetime import timedelta
from pathlib import Path

from cmk.ccc.store import save_mk_file

from .history_file import parse_history_file_python
from .history_sqlite import SQLiteHistory
from .main import (
    create_history_raw,
    default_slave_status_master,
    load_configuration,
    StatusTableEvents,
    StatusTableHistory,
)
from .settings import create_paths, create_settings


def history_files_to_sqlite(omd_root: Path, logger: logging.Logger) -> None:
    """Read history files one by one in the folder and write their contents into sqlite database.

    Is run by the update_ec_history action of cmk-update-config.

    """
    tic = time.time()

    (omd_root / "var/mkeventd/active_config/conf.d").mkdir(parents=True, exist_ok=True)
    (omd_root / "etc/check_mk/mkeventd.d/conf.d").mkdir(parents=True, exist_ok=True)
    save_mk_file(
        omd_root / "var/mkeventd/active_config/conf.d/enable_sqlite.mk", "archive_mode='sqlite'"
    )
    save_mk_file(
        omd_root / "etc/check_mk/mkeventd.d/conf.d/enable_sqlite.mk", "archive_mode='sqlite'"
    )

    history_dir = create_paths(omd_root).history_dir.value
    settings = create_settings("1.2.3i45", omd_root, ["mkeventd"])
    config = load_configuration(settings, logger, default_slave_status_master())

    history_sqlite = create_history_raw(
        settings,
        config | {"archive_mode": "sqlite"},
        logger,
        StatusTableEvents.columns,
        StatusTableHistory.columns,
    )

    assert isinstance(history_sqlite, SQLiteHistory)

    logger.debug("Processing files in history_dir %s", history_dir)
    # reverse=False is explicit here to make sure that the newer files are processed last.
    # this is important because the sqlite history_line column is unique and we want to avoid
    # duplicate entries AND we want the newest entry to have a higher history_line number.
    for file in sorted(history_dir.glob("*.log"), reverse=False):
        for parsed_entries in parse_history_file_python(
            StatusTableHistory.columns,
            file,
            logger,
        ):
            history_sqlite.add_entries(parsed_entries)

        # processed files are not needed anymore
        file.rename(file.with_suffix(".bak"))
        logger.debug("Renamed file %s", file)
    logger.debug("Migrating history files to sqlite took: %s", timedelta(seconds=time.time() - tic))
