#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import ast
import base64
import secrets
import uuid
from dataclasses import asdict, dataclass, field
from logging import Logger
from pathlib import Path
from typing import cast, override, TypedDict

from cmk.ccc.user import UserId
from cmk.gui.type_defs import AuthType, SessionInfo
from cmk.gui.userdb import store
from cmk.update_config.lib import ExpiryVersion
from cmk.update_config.plugins.pre_actions.utils import ConflictMode
from cmk.update_config.registry import pre_update_action_registry, PreUpdateAction
from cmk.utils.paths import profile_dir


class WebAuthnActionState(TypedDict):
    # duplicated here for savekeeping
    challenge: str
    user_verification: str


def _gen_encrypter_secret() -> str:
    # this is dupliated from crypto.secrets, but let's avoid reaching for more packages for this
    return base64.b64encode(secrets.token_bytes(32)).decode("ascii")


@dataclass
class OldSessionInfo:
    """2.4 SessionInfo structure before migration."""

    session_id: str
    started_at: int
    last_activity: int
    csrf_token: str = field(default_factory=lambda: str(uuid.uuid4()))
    flashes: list[tuple[str, str]] = field(default_factory=list)
    encrypter_secret: str = field(default_factory=_gen_encrypter_secret)
    two_factor_completed: bool = False
    two_factor_required: bool = False
    webauthn_action_state: WebAuthnActionState | None = None
    logged_out: bool = field(default=False)
    auth_type: AuthType | None = None


def parse_old_info(value: str) -> dict[str, OldSessionInfo]:
    # this used to be cmk.gui.userdb.store.convert_session_info
    if value == "":
        return {}

    if value.startswith("{"):
        return {k: OldSessionInfo(**v) for k, v in ast.literal_eval(value).items()}

    # Transform pre 2.0 values (for the last time hopefully)
    session_id, last_activity = value.split("|", 1)
    return {
        session_id: OldSessionInfo(
            session_id=session_id,
            # We don't have that information. The best guess is to use the last activitiy
            started_at=int(last_activity),
            last_activity=int(last_activity),
            flashes=[],
        ),
    }


def parse_new_info(value: str) -> dict[str, SessionInfo]:
    if value == "":
        return {}

    return {k: SessionInfo(**v) for k, v in ast.literal_eval(value).items()}


def convert(old: OldSessionInfo) -> SessionInfo:
    return SessionInfo(
        session_id=old.session_id,
        started_at=old.started_at,
        last_activity=old.last_activity,
        csrf_token=old.csrf_token,
        flashes=old.flashes,
        encrypter_secret=old.encrypter_secret,
        two_factor_required=old.two_factor_required,
        webauthn_action_state=None,  # sessions are terminated, no need to keep this state
        auth_type=cast(AuthType, old.auth_type),
        session_state="credentials_needed",  # new field
    )


class MigrateSessionInfoPre(PreUpdateAction):
    """
    session_info.mk has lost some fields and gained some fields. While sessions are terminated
    during updates, the session info itself cannot be deleted completely. So we migrate.
    """

    @staticmethod
    def _delete_broken_session_info(session_info_file: Path, logger: Logger) -> None:
        logger.warning(
            f"Failed to read session info in {session_info_file}. Removing old session info file."
        )
        session_info_file.unlink()

    def _is_already_migrated(self, username: UserId) -> bool:
        try:
            _ = store.load_custom_attr(user_id=username, key="session_info", parser=parse_new_info)
            return True
        except Exception:
            return False

    @override
    def __call__(self, logger: Logger, conflict_mode: ConflictMode) -> None:
        for profile in profile_dir.iterdir():
            if not profile.is_dir():
                continue

            session_info_file = profile / "session_info.mk"
            if not session_info_file.exists():
                continue

            username = UserId(profile.name)

            if self._is_already_migrated(username):
                continue

            try:
                old_data = store.load_custom_attr(
                    user_id=username, key="session_info", parser=parse_old_info
                )
            except Exception:
                self._delete_broken_session_info(session_info_file, logger)
                continue

            if old_data is None:
                self._delete_broken_session_info(session_info_file, logger)
                continue

            new_data = {k: asdict(convert(v)) for k, v in old_data.items()}
            store.save_custom_attr(userid=username, key="session_info", val=repr(new_data))


pre_update_action_registry.register(
    MigrateSessionInfoPre(
        name="migrate_session_info",
        title="Migrating all existing user sessions",
        sort_index=25,  # run before any userdata is loaded (DCD)
        expiry_version=ExpiryVersion.CMK_300,
    )
)
