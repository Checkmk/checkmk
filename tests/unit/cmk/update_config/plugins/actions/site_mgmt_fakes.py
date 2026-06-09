#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Shared fakes for update-config actions that rewrite the sites config."""

from __future__ import annotations

from cmk.ccc.site import SiteId


class FakeSiteMgmt:
    """Minimal stand-in for the registered site-management object.

    Serves a mutable site map from ``load_sites`` and captures whatever
    ``save_sites`` is handed — ``saved is None`` means it was never called, which
    is how the migrations' no-op/idempotency cases are asserted.
    """

    def __init__(self, sites: dict[SiteId, dict[str, object]]) -> None:
        self._sites = sites
        self.saved: dict[SiteId, dict[str, object]] | None = None

    def load_sites(self) -> dict[SiteId, dict[str, object]]:
        return self._sites

    def save_sites(
        self,
        folder_tree: object,
        configured_sites: dict[SiteId, dict[str, object]],
        *,
        activate: bool,
        pprint_value: bool,
        liveproxyd_enabled: bool,
        use_git: bool,
        acting_user_id: object,
    ) -> None:
        assert activate is False  # migration must not auto-activate
        self.saved = configured_sites
