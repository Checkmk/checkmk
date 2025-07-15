#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
import sqlite3
from pathlib import Path

from cmk.ec.settings import create_paths
from cmk.update_config.plugins.actions.ec_history import UpdateECHistory


def test_update_ec_history(tmp_path: Path) -> None:
    """update_ec_history should create a history.sqlite file.
    Rename all *.log files to *.bak. Create a history.sqlite file and a enable_sqlite.mk file.
    """

    values = """1666942211.07616	NEW			1002	1	999: # Network services, Internet style # # Updated from https://www.iana.org/assignments/service-names-port-numbers/service-names-port-numbers.xhtml . # # New ports will be added on request if they have been officially assigned # by IANA and used in the real-world or are needed by a debian package. # If you need a huge list of used numbers please install the nmap package. tcpmux 1/tcp # TCP port service multiplexer echo 7/tcp	1666942208.0	1666942208.0		0	heute		OMD	0	6	9	asdf	0	open						host	heute	0	
1666942292.2998602	DELETE	cmkadmin		5	1	4: # Network services, Internet style # # Updated from https://www.iana.org/assignments/service-names-port-numbers/service-names-port-numbers.xhtml . # # New ports will be added on request if they have been officially assigned # by IANA and used in the real-world or are needed by a debian package. # If you need a huge list of used numbers please install the nmap package. tcpmux 1/tcp # TCP port service multiplexer echo 7/tcp	1666942205.0	1666942205.0		0	heute		OMD	0	6	9	asdf	0	closed	cmkadmin					host	heute	0	
1666942292.2999856	DELETE	cmkadmin		6	1	5: # Network services, Internet style # # Updated from https://www.iana.org/assignments/service-names-port-numbers/service-names-port-numbers.xhtml . # # New ports will be added on request if they have been officially assigned # by IANA and used in the real-world or are needed by a debian package. # If you need a huge list of used numbers please install the nmap package. tcpmux 1/tcp # TCP port service multiplexer echo 7/tcp	1666942205.0	1666942205.0		0	heute		OMD	0	6	9	asdf	0	closed	cmkadmin					host	heute	0	
1666942292.3000507	DELETE	cmkadmin		7	1	6: # Network services, Internet style # # Updated from https://www.iana.org/assignments/service-names-port-numbers/service-names-port-numbers.xhtml . # # New ports will be added on request if they have been officially assigned # by IANA and used in the real-world or are needed by a debian package. # If you need a huge list of used numbers please install the nmap package. tcpmux 1/tcp # TCP port service multiplexer echo 7/tcp	1666942205.0	1666942205.0		0	heute		OMD	0	6	9	asdf	0	closed	cmkadmin					host	heute	0	
"""
    history_dir = create_paths(tmp_path).history_dir.value
    history_dir.mkdir(parents=True, exist_ok=True)
    history_file = history_dir / "history_test.log"
    history_file.write_text(values)

    UpdateECHistory.history_files_to_sqlite(tmp_path, logger=logging.getLogger("cmk.mkeventd"))

    assert history_file.with_suffix(".bak").exists()
    with sqlite3.connect(history_dir / "history.sqlite") as connection:
        cur = connection.cursor()
        cur.execute("SELECT COUNT(*) FROM history;")
        assert cur.fetchone()[0] == 4
