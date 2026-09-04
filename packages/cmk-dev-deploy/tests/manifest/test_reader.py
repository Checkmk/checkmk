# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Unit tests for the install spec parser of the manifest reader."""

from cmk.dev_deploy.manifest.reader import _parse_install_spec

_RAW_INSTALL_SPEC = {
    "source_prefix": "packages/cmk-frontend-vue",
    "package_target": "//packages/cmk-frontend-vue:frontend_vue_dist_pkg",
    "output_basename": "dist",
    "site_dest": "share/check_mk/web/htdocs/cmk-frontend-vue",
    "mode": 420,
    "post_install": [],
    "editions": [],
    "needs_version_flag": False,
    "use_copytree": True,
    "frontend_supervised": True,
}


class TestParseInstallSpec:
    def test_input_prefixes_are_parsed(self) -> None:
        raw = {**_RAW_INSTALL_SPEC, "input_prefixes": ["packages/cmk-ui-library/"]}
        assert _parse_install_spec(raw).input_prefixes == ("packages/cmk-ui-library/",)

    def test_input_prefixes_default_to_none_for_manifests_without_them(self) -> None:
        assert _parse_install_spec(_RAW_INSTALL_SPEC).input_prefixes == ()
