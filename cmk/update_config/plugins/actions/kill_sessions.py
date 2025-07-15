#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from datetime import datetime
from logging import Logger
from typing import override

from cmk.gui import userdb

from cmk.update_config.registry import update_action_registry, UpdateAction


class TerminateUserSessions(UpdateAction):
    """Terminate all existing user sessions

    Theoretically a user could have an active session with a fully filled form in one tab. Then the
    site is updated and started again within the session timeout of default 1h. Then the user could
    continue with the form. Since something could have changed in the background, we do not want the
    session to be alive after the update. So we terminate all sessions on update.
    """

    @override
    def __call__(self, logger: Logger) -> None:
        for user_id in userdb.load_users(lock=False):
            session_infos = userdb.session.active_sessions(
                userdb.session.load_session_infos(user_id, lock=True),
                datetime.now(),
            )
            for session_info in session_infos.values():
                session_info.logged_out = True
            userdb.session.save_session_infos(user_id, session_infos)


update_action_registry.register(
    TerminateUserSessions(
        name="terminate_user_sessions",
        title="Terminating all existing user sessions",
        sort_index=100,  # I am not aware of any constrains
    )
)
