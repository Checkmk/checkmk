#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from datetime import datetime

from cmk.ccc.user import UserId
from cmk.gui.config import active_config, Config
from cmk.gui.log import logger
from cmk.gui.type_defs import Users
from cmk.gui.userdb._connector import ConnectorType
from cmk.gui.utils.security_log_events import UserManagementEvent
from cmk.utils.security_event import log_security_event

from ._user_attribute import get_user_attributes
from .store import load_users, release_users_lock, save_users


def execute_ldap_quarantine_cleanup_job(config: Config) -> None:
    """Delete quarantined LDAP users whose retention period has elapsed.

    Runs as a GUI cron job; errors are logged to var/log/web.log. This is the
    safety net that still expires quarantined users even when their LDAP
    connection has been disabled or removed and regular synchronization no
    longer runs for it.
    """
    expire_quarantined_users(datetime.now(), config.ldap_quarantine_period)


def expire_quarantined_users(now: datetime, retention: int | None) -> None:
    if retention is None:
        # Quarantine disabled: vanished LDAP users are deleted immediately by the sync.
        return

    users = load_users(lock=True)
    expired = _expired_quarantined_users(users, int(now.timestamp()), retention)

    if not expired:
        release_users_lock()
        return

    for user_id in expired:
        quarantine = users[user_id].get("ldap_quarantine")
        del users[user_id]
        logger.info(
            "Deleting quarantined LDAP user after retention period: %(user_id)s",
            {"user_id": user_id},
        )
        log_security_event(
            UserManagementEvent(
                event="user deleted",
                affected_user=user_id,
                acting_user=None,
                connector=ConnectorType.LDAP,
                connection_id=quarantine["connection_id"] if quarantine else None,
            )
        )

    save_users(
        users,
        get_user_attributes(active_config.wato_user_attrs),
        active_config.user_connections,
        now=now,
        pprint_value=active_config.wato_pprint_config,
        call_users_saved_hook=True,
        changed_users=expired,
    )


def _expired_quarantined_users(users: Users, now: int, retention: int) -> list[UserId]:
    expired: list[UserId] = []
    for user_id, user in users.items():
        quarantine = user.get("ldap_quarantine")
        if quarantine is None:
            continue
        if now - quarantine["quarantined_on"] > retention:
            expired.append(user_id)
    return expired
