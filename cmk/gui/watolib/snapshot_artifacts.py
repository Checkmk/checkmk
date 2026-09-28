#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Files the central site writes for its sites before an activation takes its snapshots

A writer runs while an activation starts, before the snapshots for the remote sites are
created. What it writes below a replicated path therefore reaches the remote sites with the
very activation it was made for, together with the configuration it was made from.
"""

from collections.abc import Callable
from dataclasses import dataclass
from typing import override

import cmk.ccc.plugin_registry
from cmk.gui.watolib.hosts_and_folders import FolderTree


@dataclass(frozen=True)
class SnapshotArtifact:
    ident: str
    # Writes the artifact from the folder tree of the activation. It runs on every activation,
    # so it should leave an unchanged file untouched. An exception aborts the activation.
    write: Callable[[FolderTree], None]


class SnapshotArtifactRegistry(cmk.ccc.plugin_registry.Registry[SnapshotArtifact]):
    @override
    def plugin_name(self, instance: SnapshotArtifact) -> str:
        return instance.ident


snapshot_artifact_registry = SnapshotArtifactRegistry()
