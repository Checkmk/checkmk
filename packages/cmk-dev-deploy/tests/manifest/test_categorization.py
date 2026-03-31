# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Unit tests for manifest-derived categorization rule computation."""

from __future__ import annotations

from typing import Any

import pytest

from cmk.dev_deploy.manifest.reader import _parse_categorization_rule, get_categorization_rules
from cmk.dev_deploy.types import CategorizationRule, ChangeCategory

# ---------------------------------------------------------------------------
# _parse_categorization_rule tests
# ---------------------------------------------------------------------------


class TestParseCategorizationRule:
    """Tests for the _parse_categorization_rule parser."""

    def test_parses_rule_with_extensions(self) -> None:
        raw = {"prefix": "packages/livestatus/", "extensions": [".cc", ".h"], "category": "cpp"}
        result = _parse_categorization_rule(raw)
        assert result is not None
        assert result.prefix == "packages/livestatus/"
        assert result.extensions == frozenset({".cc", ".h"})
        assert result.category == ChangeCategory.CPP

    def test_parses_rule_with_null_extensions(self) -> None:
        raw = {"prefix": "agents/", "extensions": None, "category": "config"}
        result = _parse_categorization_rule(raw)
        assert result is not None
        assert result.extensions is None
        assert result.category == ChangeCategory.CONFIG

    def test_returns_none_for_unknown_category(self) -> None:
        raw = {"prefix": "foo/", "extensions": None, "category": "unknown_future_cat"}
        result = _parse_categorization_rule(raw)
        assert result is None

    def test_frozen_dataclass(self) -> None:
        raw = {"prefix": "cmk/", "extensions": [".py"], "category": "python"}
        result = _parse_categorization_rule(raw)
        assert result is not None
        with pytest.raises(AttributeError):
            result.prefix = "other/"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# get_categorization_rules integration tests (require manifest file)
# ---------------------------------------------------------------------------


class TestGetCategorizationRulesFromManifest:
    """Tests for get_categorization_rules() via the manifest reader.

    Works against both the real manifest (local dev) and the seed manifest
    (CI).  Both have categorization_rules computed by the real pipeline.
    """

    def test_loads_rules(self) -> None:
        """get_categorization_rules returns non-empty tuple of CategorizationRule."""
        rules = get_categorization_rules()
        assert len(rules) > 0
        assert all(isinstance(r, CategorizationRule) for r in rules)

    def test_rules_are_longest_prefix_first(self) -> None:
        """Rules are ordered by descending prefix length."""
        rules = get_categorization_rules()
        prefixes = [r.prefix for r in rules]
        for i in range(len(prefixes) - 1):
            assert len(prefixes[i]) >= len(prefixes[i + 1]), (
                f"Rule {i} prefix {prefixes[i]!r} (len={len(prefixes[i])}) "
                f"is shorter than rule {i + 1} prefix {prefixes[i + 1]!r} "
                f"(len={len(prefixes[i + 1])})"
            )


# ---------------------------------------------------------------------------
# _extensions_to_category tests
# ---------------------------------------------------------------------------


class TestExtensionsToCategory:
    """Tests for _extensions_to_category priority logic."""

    def test_rust_extensions(self) -> None:
        from cmk.dev_deploy.manifest.update import _extensions_to_category

        assert _extensions_to_category(frozenset({".rs"})) == ChangeCategory.RUST

    def test_cpp_extensions(self) -> None:
        from cmk.dev_deploy.manifest.update import _extensions_to_category

        assert _extensions_to_category(frozenset({".cc", ".h"})) == ChangeCategory.CPP

    def test_cpp_with_proto(self) -> None:
        from cmk.dev_deploy.manifest.update import _extensions_to_category

        assert (
            _extensions_to_category(frozenset({".cc", ".h", ".hpp", ".proto"}))
            == ChangeCategory.CPP
        )

    def test_vue_extensions(self) -> None:
        from cmk.dev_deploy.manifest.update import _extensions_to_category

        assert _extensions_to_category(frozenset({".vue", ".ts", ".js"})) == ChangeCategory.VUE

    def test_frontend_extensions(self) -> None:
        from cmk.dev_deploy.manifest.update import _extensions_to_category

        assert (
            _extensions_to_category(frozenset({".js", ".ts", ".css", ".scss"}))
            == ChangeCategory.FRONTEND
        )

    def test_frontend_supervised_overrides(self) -> None:
        from cmk.dev_deploy.manifest.update import _extensions_to_category

        # Even with frontend-like extensions, frontend_supervised forces VUE
        result = _extensions_to_category(frozenset({".js", ".ts"}), frontend_supervised=True)
        assert result == ChangeCategory.VUE

    def test_unknown_extensions_returns_none(self) -> None:
        from cmk.dev_deploy.manifest.update import _extensions_to_category

        assert _extensions_to_category(frozenset({".toml", ".lock"})) is None

    def test_empty_extensions_returns_none(self) -> None:
        from cmk.dev_deploy.manifest.update import _extensions_to_category

        assert _extensions_to_category(frozenset()) is None


# ---------------------------------------------------------------------------
# _compute_categorization_rules unit tests (mock manifest data)
# ---------------------------------------------------------------------------


def _make_manifest(
    *,
    install_specs: list[dict[str, Any]] | None = None,
    wheel_specs: list[dict[str, Any]] | None = None,
    config_specs: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Build a minimal manifest_data dict for testing."""
    return {
        "install_specs": install_specs or [],
        "wheel_specs": wheel_specs or [],
        "config_specs": config_specs or [],
        "service_specs": [],
    }


def _load_toml_supplementary() -> tuple[CategorizationRule, ...]:
    """Load supplementary rules from the real deploy_specs.toml."""
    from cmk.dev_deploy.manifest.update import _load_supplementary_rules, specs_path

    return _load_supplementary_rules(specs_path())


class TestComputeCategorizationRules:
    """Tests for _compute_categorization_rules logic.

    These import the function directly and test with synthetic manifest data.
    The install_spec_extensions dict simulates what _query_install_spec_extensions
    would return from the Bazel build graph.
    """

    def test_install_spec_rust(self) -> None:
        """Rust install spec produces RUST rule with extensions from Bazel."""
        from cmk.dev_deploy.manifest.update import _compute_categorization_rules

        manifest = _make_manifest(
            install_specs=[
                {"source_prefix": "packages/check-cert", "frontend_supervised": False},
            ]
        )
        extensions = {"packages/check-cert": frozenset({".rs"})}
        rules = _compute_categorization_rules(manifest, extensions)
        assert any(
            r["prefix"] == "packages/check-cert/"
            and r["category"] == "rust"
            and ".rs" in r["extensions"]
            for r in rules
        )

    def test_install_spec_cpp_with_proto(self) -> None:
        """CMC install spec includes .proto because Bazel reports it in srcs."""
        from cmk.dev_deploy.manifest.update import _compute_categorization_rules

        manifest = _make_manifest(
            install_specs=[
                {"source_prefix": "non-free/packages/cmc", "frontend_supervised": False},
            ]
        )
        extensions = {"non-free/packages/cmc": frozenset({".cc", ".h", ".hpp", ".proto"})}
        rules = _compute_categorization_rules(manifest, extensions)
        cmc_rules = [r for r in rules if r["prefix"] == "non-free/packages/cmc/"]
        assert len(cmc_rules) == 1
        assert ".proto" in cmc_rules[0]["extensions"]
        assert ".cc" in cmc_rules[0]["extensions"]

    def test_install_spec_unixcat(self) -> None:
        """unixcat extensions come from Bazel, not a hardcoded override."""
        from cmk.dev_deploy.manifest.update import _compute_categorization_rules

        manifest = _make_manifest(
            install_specs=[
                {"source_prefix": "packages/unixcat", "frontend_supervised": False},
            ]
        )
        # Bazel reports only .cc and .h for unixcat (no .hpp)
        extensions = {"packages/unixcat": frozenset({".cc", ".h"})}
        rules = _compute_categorization_rules(manifest, extensions)
        unixcat_rules = [r for r in rules if r["prefix"] == "packages/unixcat/"]
        assert len(unixcat_rules) == 1
        assert set(unixcat_rules[0]["extensions"]) == {".cc", ".h"}

    def test_install_spec_frontend_supervised_overrides_to_vue(self) -> None:
        """frontend_supervised=True forces VUE category regardless of extensions."""
        from cmk.dev_deploy.manifest.update import _compute_categorization_rules

        manifest = _make_manifest(
            install_specs=[
                {"source_prefix": "packages/cmk-frontend-vue", "frontend_supervised": True},
            ]
        )
        extensions = {"packages/cmk-frontend-vue": frozenset({".vue", ".ts", ".tsx", ".js"})}
        rules = _compute_categorization_rules(manifest, extensions)
        vue_rules = [r for r in rules if r["prefix"] == "packages/cmk-frontend-vue/"]
        assert len(vue_rules) == 1
        assert vue_rules[0]["category"] == "vue"

    def test_install_spec_frontend_ts_included(self) -> None:
        """cmk-frontend gets .ts in extensions from Bazel (the motivating bug)."""
        from cmk.dev_deploy.manifest.update import _compute_categorization_rules

        manifest = _make_manifest(
            install_specs=[
                {"source_prefix": "packages/cmk-frontend", "frontend_supervised": False},
            ]
        )
        extensions = {"packages/cmk-frontend": frozenset({".js", ".ts", ".css", ".scss"})}
        rules = _compute_categorization_rules(manifest, extensions)
        fe_rules = [r for r in rules if r["prefix"] == "packages/cmk-frontend/"]
        assert len(fe_rules) == 1
        assert ".ts" in fe_rules[0]["extensions"]
        assert fe_rules[0]["category"] == "frontend"

    def test_install_spec_no_extensions_skipped(self) -> None:
        """Install spec with no Bazel extensions is skipped gracefully."""
        from cmk.dev_deploy.manifest.update import _compute_categorization_rules

        manifest = _make_manifest(
            install_specs=[
                {"source_prefix": "packages/unknown-pkg", "frontend_supervised": False},
            ]
        )
        # No extensions found for this package
        rules = _compute_categorization_rules(manifest, {})
        assert not any(r["prefix"] == "packages/unknown-pkg/" for r in rules)

    def test_wheel_spec_python(self) -> None:
        """Wheel spec produces PYTHON rule with .py extension."""
        from cmk.dev_deploy.manifest.update import _compute_categorization_rules

        manifest = _make_manifest(
            wheel_specs=[
                {"source_prefix": "packages/cmk-ccc"},
            ]
        )
        rules = _compute_categorization_rules(manifest, {})
        assert any(
            r["prefix"] == "packages/cmk-ccc/"
            and r["category"] == "python"
            and r["extensions"] == [".py"]
            for r in rules
        )

    def test_cmk_shared_typing_dual_rules(self) -> None:
        """cmk-shared-typing produces both PYTHON (.py) and VUE (.ts) rules."""
        from cmk.dev_deploy.manifest.update import _compute_categorization_rules

        manifest = _make_manifest(
            wheel_specs=[
                {"source_prefix": "packages/cmk-shared-typing"},
            ]
        )
        rules = _compute_categorization_rules(manifest, {})
        st_rules = [r for r in rules if r["prefix"] == "packages/cmk-shared-typing/"]
        categories = {r["category"] for r in st_rules}
        assert "python" in categories
        assert "vue" in categories

    def test_config_spec_locale_is_data(self) -> None:
        """Config spec with locale_compile method produces DATA category."""
        from cmk.dev_deploy.manifest.update import _compute_categorization_rules

        manifest = _make_manifest(
            config_specs=[
                {"source_prefix": "locale/", "method": "locale_compile"},
            ]
        )
        rules = _compute_categorization_rules(manifest, {})
        assert any(
            r["prefix"] == "locale/" and r["category"] == "data" and r["extensions"] is None
            for r in rules
        )

    def test_config_spec_copy_dir_is_config(self) -> None:
        """Config spec with copy_dir method produces CONFIG category."""
        from cmk.dev_deploy.manifest.update import _compute_categorization_rules

        manifest = _make_manifest(
            config_specs=[
                {"source_prefix": "agents/", "method": "copy_dir"},
            ]
        )
        rules = _compute_categorization_rules(manifest, {})
        assert any(r["prefix"] == "agents/" and r["category"] == "config" for r in rules)

    def test_supplementary_rules_included(self) -> None:
        """Supplementary rules from TOML for packages without specs are included."""
        from cmk.dev_deploy.manifest.update import _compute_categorization_rules

        manifest = _make_manifest()
        rules = _compute_categorization_rules(manifest, {}, _load_toml_supplementary())
        prefixes = {r["prefix"] for r in rules}
        assert "packages/cmk-agent-ctl/" in prefixes
        assert "packages/mk-sql/" in prefixes
        assert "notifications/" in prefixes
        assert "doc/" in prefixes
        assert "packages/" in prefixes
        assert "non-free/packages/" in prefixes

    def test_supplementary_catch_all_notifications_is_config(self) -> None:
        """notifications/ catch-all maps to CONFIG with no extension filter."""
        from cmk.dev_deploy.manifest.update import _compute_categorization_rules

        manifest = _make_manifest()
        rules = _compute_categorization_rules(manifest, {}, _load_toml_supplementary())
        notif_rules = [r for r in rules if r["prefix"] == "notifications/"]
        assert len(notif_rules) == 1
        assert notif_rules[0]["category"] == "config"
        assert notif_rules[0]["extensions"] is None

    def test_supplementary_catch_all_doc_is_data(self) -> None:
        """doc/ catch-all maps to DATA with no extension filter."""
        from cmk.dev_deploy.manifest.update import _compute_categorization_rules

        manifest = _make_manifest()
        rules = _compute_categorization_rules(manifest, {}, _load_toml_supplementary())
        doc_rules = [r for r in rules if r["prefix"] == "doc/"]
        assert len(doc_rules) == 1
        assert doc_rules[0]["category"] == "data"
        assert doc_rules[0]["extensions"] is None

    def test_supplementary_catch_all_packages_is_python(self) -> None:
        """packages/ catch-all maps to PYTHON with .py extension filter."""
        from cmk.dev_deploy.manifest.update import _compute_categorization_rules

        manifest = _make_manifest()
        rules = _compute_categorization_rules(manifest, {}, _load_toml_supplementary())
        pkg_rules = [r for r in rules if r["prefix"] == "packages/"]
        assert len(pkg_rules) == 1
        assert pkg_rules[0]["category"] == "python"
        assert pkg_rules[0]["extensions"] == [".py"]

    def test_catch_all_packages_sorts_after_specific(self) -> None:
        """Catch-all packages/ sorts after specific package prefixes."""
        from cmk.dev_deploy.manifest.update import _compute_categorization_rules

        manifest = _make_manifest(
            wheel_specs=[
                {"source_prefix": "packages/cmk-ccc"},
            ]
        )
        rules = _compute_categorization_rules(manifest, {}, _load_toml_supplementary())
        prefixes = [r["prefix"] for r in rules]
        specific_idx = prefixes.index("packages/cmk-ccc/")
        catchall_idx = prefixes.index("packages/")
        assert specific_idx < catchall_idx

    def test_duplicate_source_prefix_deduplication(self) -> None:
        """Multiple install specs with same source_prefix produce only one rule."""
        from cmk.dev_deploy.manifest.update import _compute_categorization_rules

        manifest = _make_manifest(
            install_specs=[
                {"source_prefix": "non-free/packages/cmc", "frontend_supervised": False},
                {"source_prefix": "non-free/packages/cmc", "frontend_supervised": False},
                {"source_prefix": "non-free/packages/cmc", "frontend_supervised": False},
            ]
        )
        extensions = {"non-free/packages/cmc": frozenset({".cc", ".h", ".hpp", ".proto"})}
        rules = _compute_categorization_rules(manifest, extensions)
        cmc_rules = [r for r in rules if r["prefix"] == "non-free/packages/cmc/"]
        assert len(cmc_rules) == 1

    def test_ordering_longest_prefix_first(self) -> None:
        """Rules are ordered by descending prefix length."""
        from cmk.dev_deploy.manifest.update import _compute_categorization_rules

        manifest = _make_manifest(
            install_specs=[
                {"source_prefix": "packages/cmk-frontend-vue", "frontend_supervised": True},
                {"source_prefix": "packages/cmk-frontend", "frontend_supervised": False},
            ],
            wheel_specs=[
                {"source_prefix": "packages/cmk-ccc"},
            ],
        )
        extensions = {
            "packages/cmk-frontend-vue": frozenset({".vue", ".ts", ".tsx", ".js"}),
            "packages/cmk-frontend": frozenset({".js", ".ts", ".css", ".scss"}),
        }
        rules = _compute_categorization_rules(manifest, extensions)
        prefixes = [r["prefix"] for r in rules]
        vue_idx = prefixes.index("packages/cmk-frontend-vue/")
        fe_idx = prefixes.index("packages/cmk-frontend/")
        ccc_idx = prefixes.index("packages/cmk-ccc/")
        assert vue_idx < fe_idx < ccc_idx

    def test_extensions_are_sorted_in_output(self) -> None:
        """Extension lists in output dicts are alphabetically sorted."""
        from cmk.dev_deploy.manifest.update import _compute_categorization_rules

        manifest = _make_manifest(
            install_specs=[
                {"source_prefix": "packages/cmk-frontend-vue", "frontend_supervised": True},
            ]
        )
        extensions = {"packages/cmk-frontend-vue": frozenset({".vue", ".ts", ".tsx", ".js"})}
        rules = _compute_categorization_rules(manifest, extensions)
        vue_rules = [r for r in rules if r["prefix"] == "packages/cmk-frontend-vue/"]
        assert vue_rules[0]["extensions"] == sorted(vue_rules[0]["extensions"])

    def test_same_prefix_different_extensions_coexist(self) -> None:
        """Rules with same prefix but different extensions are both emitted."""
        from cmk.dev_deploy.manifest.update import _compute_categorization_rules

        manifest = _make_manifest(
            wheel_specs=[
                {"source_prefix": "packages/cmk-shared-typing"},
            ]
        )
        rules = _compute_categorization_rules(manifest, {})
        st_rules = [r for r in rules if r["prefix"] == "packages/cmk-shared-typing/"]
        assert len(st_rules) == 2
        ext_sets = [frozenset(r["extensions"]) for r in st_rules]
        assert frozenset({".py"}) in ext_sets
        assert frozenset({".ts"}) in ext_sets
