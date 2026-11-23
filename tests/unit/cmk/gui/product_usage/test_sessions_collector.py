#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Contract test: the sessions collector reads the files in the format the GUI writes them"""

import cmk.product_usage.collectors.sessions as sessions_collector
from cmk.ccc.user import UserId
from cmk.gui.type_defs import SessionInfo
from cmk.gui.userdb.session import save_session_infos
from cmk.product_usage.schema import SessionStats
from cmk.utils import paths


def test_collector_reads_the_sessions_that_the_gui_writes_to_the_session_store(
    with_user: tuple[UserId, str],
) -> None:
    session_info = SessionInfo(
        session_id="sid-1", started_at=1767789000, last_activity=1767790000, auth_type="cookie"
    )
    save_session_infos(with_user[0], {session_info.session_id: session_info})

    stats = sessions_collector.collect(paths.var_dir, now=1767790000)

    assert stats == SessionStats(
        count=1, average_duration=1000.0, median_duration=1000.0, stddev_duration=0.0
    )
