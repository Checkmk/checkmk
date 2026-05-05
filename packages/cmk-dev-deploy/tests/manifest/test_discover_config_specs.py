# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Unit tests for _discover_config_specs grouping behavior."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from cmk.dev_deploy.manifest.update import (
    _discover_config_specs,
    PackagingTargetIndex,
)


def _discover(
    pkg_data: PackagingTargetIndex,
    *,
    overrides: dict[str, dict[str, Any]] | None = None,
    is_nonfree_checkout: bool = True,
) -> list[dict[str, Any]]:
    return _discover_config_specs(
        pkg_data,
        overrides or {},
        Path("/repo"),
        is_nonfree_checkout,
    )


class TestHomogeneousTarget:
    def test_single_root_yields_one_spec(self) -> None:
        pkg_data: PackagingTargetIndex = {
            "//bin:foo": [
                ("bin/a", "0755", "bin/a.py", True),
                ("bin/b", "0755", "bin/b.py", True),
            ]
        }
        specs = _discover(pkg_data)
        assert len(specs) == 1
        spec = specs[0]
        assert spec["name"] == "deploy_bin_foo"
        assert spec["source_prefix"] == "bin/"
        assert spec["site_dest"] == "bin/"
        assert [f["src"] for f in spec["files"]] == ["bin/a.py", "bin/b.py"]


class TestHeterogeneousTarget:
    """The //bin:bin_755 failure mode: srcs span multiple top-level directories."""

    def test_yields_one_spec_per_root(self) -> None:
        pkg_data: PackagingTargetIndex = {
            "//bin:bin_755": [
                ("bin/check_mk", "0755", "bin/check_mk.py", True),
                ("bin/mkbackup", "0755", "bin/mkbackup.py", True),
                ("bin/cmk-pwstore", "0755", "cmk/utils/password_store/cli.py", True),
            ]
        }
        specs = _discover(pkg_data)
        assert {s["name"] for s in specs} == {
            "deploy_bin_bin_755__bin",
            "deploy_bin_bin_755__cmk",
        }
        by_name = {s["name"]: s for s in specs}
        assert by_name["deploy_bin_bin_755__bin"]["source_prefix"] == "bin/"
        assert [f["src"] for f in by_name["deploy_bin_bin_755__bin"]["files"]] == [
            "bin/check_mk.py",
            "bin/mkbackup.py",
        ]
        assert [f["src"] for f in by_name["deploy_bin_bin_755__cmk"]["files"]] == [
            "cmk/utils/password_store/cli.py"
        ]

    def test_overrides_replicate_to_every_subspec(self) -> None:
        pkg_data: PackagingTargetIndex = {
            "//bin:bin_755": [
                ("bin/x", "0755", "bin/x.py", True),
                ("bin/y", "0755", "cmk/y.py", True),
            ]
        }
        specs = _discover(
            pkg_data,
            overrides={
                "//bin:bin_755": {
                    "delete_extra": True,
                    "includes": ["*.py"],
                    "services": ["apache:reload"],
                }
            },
        )
        assert len(specs) == 2
        for spec in specs:
            assert spec["delete_extra"] is True
            assert spec["includes"] == ["*.py"]
            assert spec["services"] == ["apache:reload"]


class TestGeneratedEntries:
    def test_pure_generated_target_is_skipped(self) -> None:
        pkg_data: PackagingTargetIndex = {
            "//some:compiled": [
                ("bin/binary", "0755", "some/binary", False),
            ]
        }
        assert _discover(pkg_data) == []

    def test_generated_entry_within_editable_group_is_kept(self) -> None:
        """bin_755-style: bin/check_mk.py editable + bin/mkevent generated together."""
        pkg_data: PackagingTargetIndex = {
            "//bin:t": [
                ("bin/check_mk", "0755", "bin/check_mk.py", True),
                ("bin/mkevent", "0755", "bin/mkevent", False),
            ]
        }
        specs = _discover(pkg_data)
        assert len(specs) == 1
        files = {f["src"]: f["generated"] for f in specs[0]["files"]}
        assert files == {"bin/check_mk.py": False, "bin/mkevent": True}

    def test_pure_generated_group_is_dropped_others_kept(self) -> None:
        pkg_data: PackagingTargetIndex = {
            "//bin:t": [
                ("bin/foo", "0755", "bin/foo.py", True),
                ("bin/bar", "0755", "bin/bar.py", True),
                ("share/x", "0644", "external_repo/x", False),
            ]
        }
        # external_repo/x is NOT under "external/" or "../" so it's not filtered as
        # external; it's just a generated file in its own group with no editable
        # source → group dropped.
        specs = _discover(pkg_data)
        assert [s["source_prefix"] for s in specs] == ["bin/"]


class TestExternalPaths:
    def test_external_prefix_filtered(self) -> None:
        pkg_data: PackagingTargetIndex = {
            "//some:t": [
                ("share/a", "0644", "external/repo/a", False),
                ("share/b", "0644", "../other_repo/b", False),
                ("share/c", "0644", "data/c", True),
            ]
        }
        specs = _discover(pkg_data)
        assert len(specs) == 1
        assert [f["src"] for f in specs[0]["files"]] == ["data/c"]

    def test_only_external_yields_no_specs(self) -> None:
        pkg_data: PackagingTargetIndex = {
            "//some:t": [
                ("share/a", "0644", "external/repo/a", False),
                ("share/b", "0644", "../other_repo/b", False),
            ]
        }
        assert _discover(pkg_data) == []


class TestNonFreeFilter:
    def test_target_label_skipped_in_gpl_checkout(self) -> None:
        pkg_data: PackagingTargetIndex = {
            "//non-free/packages/cmc:wheel": [
                ("share/foo", "0644", "non-free/packages/cmc/foo.py", True),
            ]
        }
        assert _discover(pkg_data, is_nonfree_checkout=False) == []

    def test_target_label_kept_in_nonfree_checkout(self) -> None:
        pkg_data: PackagingTargetIndex = {
            "//non-free/packages/cmc:wheel": [
                ("share/foo", "0644", "non-free/packages/cmc/foo.py", True),
            ]
        }
        specs = _discover(pkg_data, is_nonfree_checkout=True)
        assert len(specs) == 1

    def test_nonfree_group_dropped_in_gpl_checkout(self) -> None:
        """Target label is GPL-clean but a source group lands under non-free/."""
        pkg_data: PackagingTargetIndex = {
            "//some:t": [
                ("share/a", "0644", "agents/foo", True),
                ("share/b", "0644", "agents/bar", True),
                ("share/c", "0644", "non-free/packages/x.py", True),
            ]
        }
        specs = _discover(pkg_data, is_nonfree_checkout=False)
        assert len(specs) == 1
        assert specs[0]["source_prefix"] == "agents/"


class TestDeterminism:
    def test_same_input_yields_identical_output(self) -> None:
        pkg_data: PackagingTargetIndex = {
            "//bin:bin_755": [
                ("bin/a", "0755", "bin/a.py", True),
                ("bin/b", "0755", "cmk/b.py", True),
                ("bin/c", "0755", "bin/c.py", True),
            ]
        }
        first = _discover(pkg_data)
        second = _discover(pkg_data)
        assert first == second
        assert [s["name"] for s in first] == sorted(s["name"] for s in first)
