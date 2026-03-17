# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Shared test fixtures and environment setup for cmk-dev-deploy tests.

Handles two Bazel sandbox issues:

1. Stubs out ``cmk.dev_deploy.privilege`` before any test module can trigger
   its import.  The privilege module depends on system packages (SSH, sudo)
   that are not available inside the Bazel test sandbox.

2. Seeds the manifest reader cache with a minimal valid manifest when the
   ``deploy_manifest.json`` file is absent (not included in the Bazel build
   graph).  Tests that need specific manifest data should still mock the
   individual ``get_*()`` functions.
"""

from __future__ import annotations

import sys
import types
from unittest.mock import MagicMock

# ---------------------------------------------------------------------------
# 1. Stub out cmk.dev_deploy.privilege
# ---------------------------------------------------------------------------

# Stub cmk.dev_deploy.site.overlay (depends on privilege, mount commands)
if "cmk.dev_deploy.site.overlay" not in sys.modules:
    _overlay_stub = types.ModuleType("cmk.dev_deploy.site.overlay")
    _overlay_stub.is_overlay_active = MagicMock(return_value=True)  # type: ignore[attr-defined]
    _overlay_stub.ensure_overlay = MagicMock()  # type: ignore[attr-defined]
    _overlay_stub.teardown_overlay = MagicMock()  # type: ignore[attr-defined]
    _overlay_stub.overlay_upper_size = MagicMock(return_value=None)  # type: ignore[attr-defined]
    sys.modules["cmk.dev_deploy.site.overlay"] = _overlay_stub

if "cmk.dev_deploy.site.privilege" not in sys.modules:
    import dataclasses
    from pathlib import Path

    @dataclasses.dataclass
    class _SSHStateStub:
        """Test stub for SSHState."""

        deploy_key_path: Path | None = None
        ssh_available: dict[str, bool] = dataclasses.field(default_factory=dict)

        def clear_ssh_cache(self) -> None:
            self.ssh_available.clear()

    _stub = types.ModuleType("cmk.dev_deploy.site.privilege")
    _stub.SSHState = _SSHStateStub  # type: ignore[attr-defined]
    _stub.run_as_site_user = MagicMock()  # type: ignore[attr-defined]
    _stub.get_real_user = MagicMock(return_value="testuser")  # type: ignore[attr-defined]
    _stub.run_as_root = MagicMock()  # type: ignore[attr-defined]
    _stub.ensure_sudo = MagicMock()  # type: ignore[attr-defined]
    _stub.try_setcap = MagicMock(return_value=True)  # type: ignore[attr-defined]
    _stub.inject_ssh_key = MagicMock(return_value=True)  # type: ignore[attr-defined]
    _stub.clear_ssh_cache = MagicMock()  # type: ignore[attr-defined]
    sys.modules["cmk.dev_deploy.site.privilege"] = _stub

# ---------------------------------------------------------------------------
# 2. Seed manifest reader cache when deploy_manifest.json is absent
# ---------------------------------------------------------------------------

from cmk.dev_deploy.manifest.reader import manifest_path

if not manifest_path().is_file():
    import cmk.dev_deploy.manifest.reader as _reader

    _SEED_MANIFEST: dict[str, object] = {
        "install_specs": [
            {
                "source_prefix": "packages/cmk-frontend-vue/",
                "package_target": "//packages/cmk-frontend-vue:vite",
                "output_basename": "dist",
                "site_dest": "share/check_mk/web/htdocs/vue",
                "mode": 0o644,
                "post_install": [],
                "editions": [],
                "needs_version_flag": False,
                "needs_faked_artifacts": False,
                "use_copytree": True,
                "frontend_supervised": True,
            },
        ],
        "config_specs": [],
        "wheel_specs": [],
        "service_specs": [],
        "deploy_deps": {},
    }

    # Seed the lru_cache by replacing _load_raw with one that returns
    # the seed data, then warm the cache.
    import functools

    @functools.lru_cache(maxsize=1)
    def _seeded_load_raw() -> dict[str, object]:
        return _SEED_MANIFEST

    _reader._load_raw = _seeded_load_raw  # noqa: SLF001
