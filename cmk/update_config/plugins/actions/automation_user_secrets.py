#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from logging import Logger
from pathlib import Path
from typing import assert_never, Literal

import cmk.utils.paths
from cmk.utils.crypto.password import Password, PasswordHash
from cmk.utils.crypto.password_hashing import hash_password, is_unsupported_legacy_hash, matches
from cmk.utils.store.htpasswd import Htpasswd

from cmk.gui.userdb import load_users

from cmk.update_config.registry import update_action_registry, UpdateAction
from cmk.update_config.update_state import UpdateActionState


class SynchronizeAutomationSecretAndHtpasswd(UpdateAction):
    def __call__(self, logger: Logger, update_action_state: UpdateActionState) -> None:
        """Set the Htpasswd has of an automation user to its secret

        When changing a automation secret in the UI we also change it in the htpasswd file.
        This value was previously never used since we currently still store the secret in plain
        text and that value was used for verification.

        Now we want to be able to disable automation users so we need to prepend the password hash
        with a `!`. To be consistent we now check both the htpasswd hash and the automation secret.
        In this step we set the hash to the secret that was used previously and log if the hash was
        outdated. So hopefully all users now keep them in sync (if they have custom scripts) until
        we can finally get rid of the plain text secret.
        """

        htpasswd = Htpasswd(Path(cmk.utils.paths.htpasswd_file))
        htpasswd_entries = htpasswd.load(allow_missing_file=True)

        for user_id, user_spec in load_users().items():
            if (automation_user_secret := user_spec.get("automation_secret")) is None:
                # not an automation user
                continue
            automation_user_password = Password(automation_user_secret)

            password_hash = htpasswd_entries.get(user_id)
            locked = False
            reason: Literal["legacy_hash", "nomatch", "nohash"] = "nohash"

            if password_hash is not None:
                if password_hash.startswith("!"):
                    locked = True
                    password_hash = PasswordHash(password_hash[1:])

                if locked:
                    logger.warning(
                        "Automation user %r is locked!",
                        user_id,
                    )
                if is_unsupported_legacy_hash(password_hash):
                    reason = "legacy_hash"
                elif matches(automation_user_password, password_hash):
                    continue
                else:
                    reason = "nomatch"

            htpasswd.save(
                user_id,
                (
                    PasswordHash("!" + hash_password(automation_user_password))
                    if locked
                    else hash_password(automation_user_password)
                ),
            )
            match reason:
                case "nomatch" | "nohash":
                    logger.warning(
                        "Automationuser's (%r) secret does not match the password hash in etc/htpasswd. Updating the hash.",
                        user_id,
                    )
                case "legacy_hash":
                    logger.warning(
                        "Automationuser's (%r) secret hash used an old format. Updating the hash.",
                        user_id,
                    )
                case _:
                    assert_never(reason)


update_action_registry.register(
    SynchronizeAutomationSecretAndHtpasswd(
        name="synchronize_automationuser_secrets",
        title="Synchronize automationuser secrets",
        sort_index=100,  # I am not aware of any constrains
    )
)
