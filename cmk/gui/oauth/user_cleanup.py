#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""End the OAuth grants of deleted users."""

from collections.abc import Sequence

from cmk.ccc.user import UserId
from cmk.gui import hooks
from cmk.gui.log import logger
from cmk.gui.oauth.token.backend import StoreUnavailableError
from cmk.gui.oauth.token.token_store import get_token_store
from cmk.gui.userdb.store import load_users_uncached


def register() -> None:
    hooks.register_builtin("users-deleted", _revoke_grants_of_deleted_users)
    # A remote site gets its users with the config sync, which deletes no
    # user on its own, so compare the grants with the synced users.
    hooks.register_builtin("snapshot-pushed", _revoke_grants_of_users_not_synced)


def _revoke_grants_of_deleted_users(user_ids: Sequence[UserId]) -> None:
    try:
        with get_token_store() as store:
            revoked = store.revoke_grants_of_users(user_ids)
    except StoreUnavailableError:
        # Already logged. The users are deleted at this point, so raising
        # would report a failure for a change that was made.
        return

    if revoked:
        logger.info(
            "Revoked the OAuth grants of deleted users: %(users)s",
            {"users": ", ".join(sorted(user_ids))},
        )


def _revoke_grants_of_users_not_synced() -> None:
    # Uncached: the sync request may have loaded the users before the
    # snapshot replaced them.
    users = load_users_uncached()
    if not users:
        # An empty list means loading the users failed. Going on would end
        # every grant.
        logger.warning("Found no users, not revoking any OAuth grants")
        return

    try:
        with get_token_store() as store:
            revoked = store.revoke_grants_of_users_not_in(users)
    except StoreUnavailableError:
        # Already logged. The snapshot is applied at this point, so raising
        # would report a failure for a sync that was made.
        return

    if revoked:
        logger.info(
            "Revoked the OAuth grants of users removed by the config sync: %(users)s",
            {"users": ", ".join(sorted(revoked))},
        )
