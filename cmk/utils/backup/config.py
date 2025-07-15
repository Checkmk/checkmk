#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""
BEWARE: Even though we are using pydantic, *no* validation is happening (see BaseModel.construct).
In the current state, we cannot validate because we have no good way to handle validation erros. In
the GUI, we must render, even if there are invalid configurations. The same holds on the command
line: mkbackup should not completely stop working due to eg. one invalid target configuration.
"""

from __future__ import annotations

import ast
from collections.abc import Mapping, MutableMapping
from os import getuid
from pathlib import Path
from stat import S_IMODE, S_IWOTH
from typing import Any

from pydantic import BaseModel, PrivateAttr

from cmk.ccc.exceptions import MKGeneralException
from cmk.ccc.i18n import _
from cmk.ccc.store import load_object_from_file, save_object_to_file
from cmk.ccc.version import is_cma

from cmk.utils.paths import default_config_dir

from .job import JobConfig
from .targets import TargetId
from .targets.config import TargetConfig


class SiteConfig(BaseModel, frozen=True):
    targets: MutableMapping[TargetId, TargetConfig]
    jobs: MutableMapping[str, JobConfig]

    @classmethod
    def load(cls, path: Path) -> SiteConfig:
        return cls.construct(
            **load_object_from_file(
                path,
                default={
                    "targets": {},
                    "jobs": {},
                },
            )
        )

    def save(self, path: Path) -> None:
        save_object_to_file(path, dict(self))


class CMASystemConfig(BaseModel, frozen=True):
    targets: Mapping[TargetId, TargetConfig]

    @classmethod
    def load(cls, path: Path) -> CMASystemConfig:
        data: dict[str, Any] = {"targets": {}}
        # The default CMESystemConfig file (/etc/cma/backup.conf) has special permissions
        # The file is group-owned by omd. To fix this in the appliance will
        # take more time, considering the compatibility with older versions
        # So we check for owner and world and don't care for group...
        try:
            if path.exists():
                if path.resolve() == Path("/etc/cma/backup.conf"):
                    stat = path.stat()
                    world_writable = S_IMODE(stat.st_mode) & S_IWOTH != 0
                    if stat.st_uid not in [0, getuid()] or world_writable:
                        raise MKGeneralException(
                            _("/etc/cma/backup.conf has wrong permissions. Refusing to read file")
                        )
                data = ast.literal_eval(path.read_text())
        except (ValueError, SyntaxError, OSError, PermissionError, UnicodeDecodeError):
            # Note: MKGeneralException is explicitly not caught
            pass

        return cls.model_construct(**data)


class Config(BaseModel, frozen=True):
    site: SiteConfig
    cma_system: CMASystemConfig
    _path_site: Path = PrivateAttr()

    def __init__(
        self,
        *,
        site: SiteConfig,
        cma_system: CMASystemConfig,
        path_site: Path,
    ) -> None:
        super().__init__(
            site=site,
            cma_system=cma_system,
        )
        self._path_site = path_site

    @classmethod
    def load(
        cls,
        *,
        path_site: Path = default_config_dir / "backup.mk",
        path_cma_system: Path = Path("/etc/cma/backup.conf"),
    ) -> Config:
        return cls(
            site=SiteConfig.load(path_site),
            cma_system=(
                CMASystemConfig.load(path_cma_system) if is_cma() else CMASystemConfig(targets={})
            ),
            path_site=path_site,
        )

    def save(self) -> None:
        self.site.save(self._path_site)

    @property
    def all_targets(self) -> dict[TargetId, TargetConfig]:
        return {
            **self.cma_system.targets,
            **self.site.targets,
        }
