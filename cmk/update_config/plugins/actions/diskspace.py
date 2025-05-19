#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pprint
from logging import Logger
from pathlib import Path
from typing import override

from pydantic import BaseModel

from cmk.ccc.store import save_text_to_file

from cmk.utils.paths import diskspace_config_dir, omd_root

from cmk.diskspace.config import Config
from cmk.update_config.registry import update_action_registry, UpdateAction


class _OldConfig(BaseModel, frozen=True):
    cleanup_abandoned_host_files: int | None = 2592000
    min_free_bytes: int | None = None
    max_file_age: int | None = None
    min_file_age: int | None = None


INVALID_CONFIG = object()


def _load_config(path: Path, logger: Logger) -> object:
    raw_config: dict[str, object] = {}
    try:
        exec(path.read_text(), raw_config, raw_config)  # nosec B102 # BNS:aee528
        old_config = _OldConfig.parse_obj(raw_config)
    except OSError:
        logger.debug("Could not find etc/diskspace.conf.")
        return None
    except Exception:
        logger.exception(
            "The content of etc/diskspace.conf seems to be invalid. The file is ignored, please check `Global settings > Site management > Automatic disk space cleanup`"
        )
        return INVALID_CONFIG
    return Config(
        max_file_age=old_config.max_file_age,
        cleanup_abandoned_host_files=old_config.cleanup_abandoned_host_files,
        min_free_bytes=None
        if old_config.min_free_bytes is None or old_config.min_file_age is None
        else (old_config.min_free_bytes, old_config.min_file_age),
    )


def migrate(old_config_file: Path, config_dir: Path, logger: Logger) -> None:
    logger.debug("Loading etc/diskspace.conf")
    config = _load_config(old_config_file, logger)
    if config is None:
        logger.debug("Nothing to be done.")
    elif isinstance(config, Config):
        output = f"""# Created during update by cmk-update-config

diskspace_cleanup = {pprint.pformat(config.model_dump(exclude_none=True))}
"""
        config_dir.mkdir(mode=0o770, exist_ok=True, parents=True)
        save_text_to_file(config_dir / "global.mk", output)
        old_config_file.unlink()
        logger.debug("Migrated etc/diskspace.conf to etc/check_mk/diskspace.d/wato/global.mk")
    else:
        assert config is INVALID_CONFIG
        logger.debug("Keeping factory default.")


class MigrateDiskSpaceConf(UpdateAction):
    @override
    def __call__(self, logger: Logger) -> None:
        migrate(omd_root / "etc/diskspace.conf", diskspace_config_dir, logger)


update_action_registry.register(
    MigrateDiskSpaceConf(
        name="migrate_diskspace_conf",
        title="Migrate etc/diskspace.conf",
        sort_index=155,  # Does not matter
    )
)
