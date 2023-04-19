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

from collections.abc import Mapping, MutableMapping
from pathlib import Path

from pydantic import BaseModel, PrivateAttr

from cmk.utils.paths import default_config_dir
from cmk.utils.store import load_object_from_file, save_object_to_file
from cmk.utils.version import is_cma

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
        return cls.construct(
            **load_object_from_file(
                path,
                default={"targets": {}},
            )
        )


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
        path_site: Path = Path(default_config_dir) / "backup.mk",
        path_cma_system: Path = Path("/etc/cma/backup.conf"),
    ) -> Config:
        return cls(
            site=SiteConfig.load(path_site),
            cma_system=CMASystemConfig.load(path_cma_system)
            if is_cma()
            else CMASystemConfig(targets={}),
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
