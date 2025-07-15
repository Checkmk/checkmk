#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from logging import Logger
from typing import override

from cmk.ccc.store import DimSerializer, ObjectStore
from cmk.gui.message import all_messages_paths
from cmk.update_config.registry import update_action_registry, UpdateAction


class MigrateUserMessages(UpdateAction):
    @override
    def __call__(self, logger: Logger) -> None:
        for path in all_messages_paths():
            store = ObjectStore(path, serializer=DimSerializer())
            with store.locked():
                messages = store.read_obj(default=[])
                migrated = [self.migrate(m) for m in messages]
                if messages != migrated:
                    store.write_obj(migrated)

    @staticmethod
    def migrate(message: object) -> object:
        if not isinstance(message, dict) or isinstance(message["text"], dict):
            return message

        # pre 2.3 message format
        return dict(
            text=dict(content_type="text", content=message["text"]),
            dest=message["dest"],
            methods=message["methods"],
            valid_till=message.get("valid_till"),
            id=message["id"],
            time=message["time"],
            security=message.get("security", False),
            acknowledged=message.get("acknowledged", False),
        )


update_action_registry.register(
    MigrateUserMessages(
        name="migrate_user_messages",
        title="Migrate user messages",
        sort_index=100,  # don't care
    )
)
