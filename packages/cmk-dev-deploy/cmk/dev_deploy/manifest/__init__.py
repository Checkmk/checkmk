# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Manifest subpackage: manifest reading, registry, dependencies, and update logic.

Re-exports the public API from submodules so callers can import from
``cmk.dev_deploy.manifest`` or directly from the submodules.
"""

from cmk.dev_deploy.manifest.deps import expand_dependencies
from cmk.dev_deploy.manifest.reader import (
    get_config_specs,
    get_deploy_deps,
    get_frontend_supervised_prefixes,
    get_install_specs,
    get_service_specs,
    get_wheel_specs,
    hash_path,
    manifest_path,
)
from cmk.dev_deploy.manifest.registry import (
    uncovered_changed_files,
)
from cmk.dev_deploy.manifest.staleness import (
    ensure_manifest,
    is_manifest_stale,
    save_manifest_hashes,
)

__all__ = [
    "ensure_manifest",
    "expand_dependencies",
    "get_config_specs",
    "get_deploy_deps",
    "get_frontend_supervised_prefixes",
    "get_install_specs",
    "get_service_specs",
    "get_wheel_specs",
    "hash_path",
    "is_manifest_stale",
    "manifest_path",
    "save_manifest_hashes",
    "uncovered_changed_files",
]
