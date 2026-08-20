#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest

from cmk.repo_checks.deballast import (
    analyze_spec,
    candidate_modules_for_path,
    canonical_label,
    dep_is_used,
    DepInfo,
    human_report,
    imports_in_tree,
    is_namespace_shim,
    is_pytest_conftest,
    load_dep_info,
    load_target_spec,
    main,
    module_roots,
    ModuleRefs,
    parse_python_source,
    resolve_imports_root,
    sarif_report,
    shares_srcs_with_target,
    SrcFile,
    stale_keeps,
    TargetSpec,
)


def test_resolve_imports_root_dot() -> None:
    assert resolve_imports_root("cmk/gui/nagvis", ".") == "cmk/gui/nagvis"


def test_resolve_imports_root_up_levels() -> None:
    # The canonical `imports = ["../../.."]` pattern used by cmk-plugins.
    assert (
        resolve_imports_root("packages/cmk-plugins/cmk/plugins/lib", "../../..")
        == "packages/cmk-plugins"
    )


def test_resolve_imports_root_empty_package() -> None:
    assert resolve_imports_root("", ".") == ""


def test_resolve_imports_root_going_above_workspace_clamps() -> None:
    assert resolve_imports_root("a", "../../..") == ""


def test_candidate_modules_for_path_imports_dot() -> None:
    # `imports = ["."]`: module derived from the path below the package dir.
    # Workspace root is always also a candidate.
    modules = candidate_modules_for_path(
        "packages/cmk-ccc/cmk/ccc/store/__init__.py",
        module_roots("packages/cmk-ccc", ["."]),
    )
    assert "cmk.ccc.store" in modules
    assert "packages.cmk-ccc.cmk.ccc.store" in modules


def test_candidate_modules_for_path_imports_up_levels() -> None:
    # `imports = ["../../.."]` is the pattern that the naive path-only approach missed.
    modules = candidate_modules_for_path(
        "packages/cmk-plugins/cmk/plugins/lib/fan.py",
        module_roots("packages/cmk-plugins/cmk/plugins/lib", ["../../.."]),
    )
    assert "cmk.plugins.lib.fan" in modules
    # Workspace-root resolution always included too.
    assert "packages.cmk-plugins.cmk.plugins.lib.fan" in modules


def test_candidate_modules_for_path_imports_dot_workspace_fallback() -> None:
    # `agents/plugins/mk_podman.py` with imports=["."] → local root gives
    # `mk_podman`, but tests import it as `agents.plugins.mk_podman` via the
    # workspace root. Both must be candidates.
    modules = candidate_modules_for_path(
        "agents/plugins/mk_podman.py",
        module_roots("agents/plugins", ["."]),
    )
    assert "mk_podman" in modules
    assert "agents.plugins.mk_podman" in modules


def test_candidate_modules_for_path_no_imports_uses_workspace_root() -> None:
    # With no imports attribute, file path is the module path directly.
    modules = candidate_modules_for_path(
        "cmk/gui/nagvis/__init__.py",
        module_roots("cmk/gui/nagvis", []),
    )
    assert modules == {"cmk.gui.nagvis"}


def test_candidate_modules_for_path_init_drops_init_suffix() -> None:
    modules = candidate_modules_for_path(
        "pkg/foo/__init__.py",
        module_roots("pkg", ["."]),
    )
    assert "foo" in modules
    assert "foo.__init__" not in modules


def test_candidate_modules_for_path_non_py_file_returns_empty() -> None:
    assert candidate_modules_for_path("pkg/BUILD", module_roots("pkg", ["."])) == set()


def test_parse_python_source_valid_file(tmp_path: Path) -> None:
    src = tmp_path / "m.py"
    src.write_text("import os\n")
    tree = parse_python_source(src)
    assert tree is not None
    assert imports_in_tree(tree).referenced == {"os"}


def test_parse_python_source_syntax_error_returns_none(tmp_path: Path) -> None:
    src = tmp_path / "bad.py"
    src.write_text("def oops(:\n")
    assert parse_python_source(src) is None


def test_parse_python_source_missing_file_returns_none() -> None:
    assert parse_python_source(Path("/does/not/exist.py")) is None


def test_imports_in_tree_absolute_import() -> None:
    assert imports_in_tree(ast.parse("import cmk.gui.foo")) == ModuleRefs(
        referenced=frozenset({"cmk.gui.foo"}),
        namespaces=frozenset({"cmk.gui.foo"}),
    )


def test_imports_in_tree_from_import_yields_module_and_attribute() -> None:
    # The imported name is a namespace; the module it came from is not - see
    # test_dep_is_used_from_import_parent_does_not_match_siblings.
    assert imports_in_tree(ast.parse("from cmk.gui import foo")) == ModuleRefs(
        referenced=frozenset({"cmk.gui", "cmk.gui.foo"}),
        namespaces=frozenset({"cmk.gui.foo"}),
    )


def test_imports_in_tree_star_import_makes_the_module_a_namespace() -> None:
    # There is no child name to record, and the statement binds whatever the
    # package re-exports - so the package itself has to license descendants.
    assert imports_in_tree(ast.parse("from cmk.gui import *")) == ModuleRefs(
        referenced=frozenset({"cmk.gui"}),
        namespaces=frozenset({"cmk.gui"}),
    )


def test_imports_in_tree_relative_import_resolved_against_containing_package() -> None:
    # `cmk/gui/htmllib/generator.py` (pkg = cmk.gui.htmllib) does
    # `from .tag_rendering import X` - resolves to `cmk.gui.htmllib.tag_rendering`.
    assert imports_in_tree(
        ast.parse("from .tag_rendering import X"), containing_packages=["cmk.gui.htmllib"]
    ) == ModuleRefs(
        referenced=frozenset({"cmk.gui.htmllib.tag_rendering", "cmk.gui.htmllib.tag_rendering.X"}),
        namespaces=frozenset({"cmk.gui.htmllib.tag_rendering.X"}),
    )


def test_imports_in_tree_dotdot_relative_import() -> None:
    # `from ..utils import X` at pkg `cmk.gui.htmllib` -> `cmk.gui.utils.X`.
    assert imports_in_tree(
        ast.parse("from ..utils import X"), containing_packages=["cmk.gui.htmllib"]
    ) == ModuleRefs(
        referenced=frozenset({"cmk.gui.utils", "cmk.gui.utils.X"}),
        namespaces=frozenset({"cmk.gui.utils.X"}),
    )


def test_imports_in_tree_relative_import_without_containing_package_is_dropped() -> None:
    assert imports_in_tree(ast.parse("from . import sibling")) == ModuleRefs.empty()


def test_imports_in_tree_mixed_imports() -> None:
    tree = ast.parse("import os\nfrom cmk.ccc.store import load\nimport cmk.gui.foo.bar as bar\n")
    assert imports_in_tree(tree) == ModuleRefs(
        referenced=frozenset({"os", "cmk.ccc.store", "cmk.ccc.store.load", "cmk.gui.foo.bar"}),
        namespaces=frozenset({"os", "cmk.ccc.store.load", "cmk.gui.foo.bar"}),
    )


def test_module_refs_or_merges_both_tiers() -> None:
    combined = imports_in_tree(ast.parse("from cmk.gui import foo")) | imports_in_tree(
        ast.parse("import cmk.ccc.debug")
    )
    assert combined == ModuleRefs(
        referenced=frozenset({"cmk.gui", "cmk.gui.foo", "cmk.ccc.debug"}),
        namespaces=frozenset({"cmk.gui.foo", "cmk.ccc.debug"}),
    )


def test_module_refs_empty_is_the_identity_of_or() -> None:
    refs = imports_in_tree(ast.parse("from cmk.gui import foo"))
    assert refs | ModuleRefs.empty() == refs


def test_dep_is_used_exact_module_match() -> None:
    assert dep_is_used({"cmk.ccc.debug"}, imports_in_tree(ast.parse("import cmk.ccc.debug")))


def test_dep_is_used_from_import_with_attribute() -> None:
    assert dep_is_used({"cmk.ccc.debug"}, imports_in_tree(ast.parse("from cmk.ccc import debug")))


def test_dep_is_used_submodule_import_matches_parent_package_dep() -> None:
    assert dep_is_used({"cmk.gui.foo"}, imports_in_tree(ast.parse("import cmk.gui.foo.bar")))


def test_dep_is_used_prefix_must_be_proper() -> None:
    assert not dep_is_used({"cmk.gui.foo"}, imports_in_tree(ast.parse("import cmk.gui.foobar")))


def test_dep_is_used_dep_module_under_imported_namespace() -> None:
    # `//cmk/gui/plugins/views:views` has no __init__.py at its namespace root,
    # only `icons/utils.py` etc. Consumers `import cmk.gui.plugins.views`
    # (the implicit namespace); the dep's deeper module should still count.
    assert dep_is_used(
        {"cmk.gui.plugins.views.icons.utils"},
        imports_in_tree(ast.parse("import cmk.gui.plugins.views")),
    )


def test_dep_is_used_namespace_reached_via_from_import_name() -> None:
    # The name in `from X import Y` is the namespace, not X - so a dep whose
    # modules live under `cmk.gui.plugins.views` still counts here.
    assert dep_is_used(
        {"cmk.gui.plugins.views.icons.utils"},
        imports_in_tree(ast.parse("from cmk.gui.plugins import views")),
    )


def test_dep_is_used_star_import_reaches_a_module_below_the_package() -> None:
    # `from cmk.gui.plugins.legacy_bakery_rulesets import *` can bind anything
    # the package re-exports, so a dep providing a module below it is used.
    assert dep_is_used(
        {"cmk.gui.plugins.views.icons.utils"},
        imports_in_tree(ast.parse("from cmk.gui.plugins.views import *")),
    )


def test_dep_is_used_from_import_parent_does_not_match_siblings() -> None:
    # `from cmk import trace` names `cmk` only to reach `cmk.trace`. Matching
    # everything under `cmk.` would exempt every first-party dep of every target
    # using this import form.
    imports = imports_in_tree(ast.parse("from cmk import trace"))
    assert dep_is_used({"cmk.trace.export"}, imports)
    assert not dep_is_used({"cmk.utils.paths"}, imports)
    assert not dep_is_used({"cmk.base.configlib.loaded_config"}, imports)


def test_dep_is_used_no_overlap_returns_false() -> None:
    assert not dep_is_used({"unrelated.module"}, imports_in_tree(ast.parse("import cmk.gui.foo")))


def test_dep_is_used_empty_dep_modules_returns_false() -> None:
    assert not dep_is_used(set(), imports_in_tree(ast.parse("import cmk.gui.foo")))


def test_is_namespace_shim_pure_init_target() -> None:
    assert is_namespace_shim(["packages/cmk-ccc/cmk/ccc/__init__.py"])


def test_is_namespace_shim_bare_init_file() -> None:
    assert is_namespace_shim(["__init__.py"])


def test_is_namespace_shim_multiple_init_files() -> None:
    assert is_namespace_shim(
        [
            "pkg/a/__init__.py",
            "pkg/a/b/__init__.py",
        ]
    )


def test_is_namespace_shim_target_with_real_code_is_not_shim() -> None:
    assert not is_namespace_shim(
        [
            "packages/cmk-ccc/cmk/ccc/store/__init__.py",
            "packages/cmk-ccc/cmk/ccc/store/_file.py",
        ]
    )


def test_is_namespace_shim_empty_srcs_are_not_shim() -> None:
    assert not is_namespace_shim([])


def test_is_namespace_shim_non_init_single_file_is_not_shim() -> None:
    assert not is_namespace_shim(["pkg/foo.py"])


def test_is_namespace_shim_generated_namespace_stub() -> None:
    # write_file-generated `_namespace.py` stubs materialize an implicit
    # namespace package in the runfiles tree (check_parameters:stub pattern).
    assert is_namespace_shim(
        [
            "cmk/gui/plugins/wato/check_parameters/_namespace_stub/cmk/gui/plugins/wato/check_parameters/_namespace.py"
        ]
    )


def test_is_namespace_shim_mixed_init_and_namespace_stub() -> None:
    assert is_namespace_shim(["pkg/__init__.py", "pkg/sub/_namespace.py"])


def test_is_pytest_conftest_pure_conftest_target() -> None:
    assert is_pytest_conftest(["tests/unit/cmk/gui/conftest.py"])


def test_is_pytest_conftest_empty_is_false() -> None:
    assert not is_pytest_conftest([])


def test_is_pytest_conftest_mixed_srcs_is_true() -> None:
    # Targets with conftest.py alongside helper modules still auto-load the
    # conftest via pytest; the whole target is load-bearing for its consumers.
    assert is_pytest_conftest(["tests/unit/cmk/gui/conftest.py", "tests/unit/cmk/gui/helpers.py"])


def test_is_pytest_conftest_no_conftest_src_is_false() -> None:
    assert not is_pytest_conftest(["tests/unit/cmk/gui/helpers.py"])


def test_shares_srcs_with_target_file_overlap_detected() -> None:
    assert shares_srcs_with_target(
        {"pkg/__test__.py", "pkg/tests/test_foo.py"},
        [],
        "//pkg:gen",
        ["pkg/__test__.py"],
    )


def test_shares_srcs_with_target_dep_label_in_srcs_attr_detected() -> None:
    # Target uses `srcs = [":__test__"]` (label ref to a py_pytest_main rule):
    # the dep's label itself appears in the target's srcs attribute.
    assert shares_srcs_with_target(
        {"pkg/tests/test_foo.py"},
        ["//pkg:__test__"],
        "//pkg:__test__",
        ["pkg/__test__.py"],
    )


def test_shares_srcs_with_target_no_overlap() -> None:
    assert not shares_srcs_with_target(
        {"pkg/a.py", "pkg/b.py"},
        [],
        "//pkg:c",
        ["pkg/c.py"],
    )


def test_shares_srcs_with_target_empty_dep_srcs() -> None:
    assert not shares_srcs_with_target({"pkg/a.py"}, [], "//pkg:dep", [])


def test_load_target_spec_round_trip(tmp_path: Path) -> None:
    spec_file = tmp_path / "spec.json"
    spec_file.write_text(
        json.dumps(
            {
                "label": "//pkg:app",
                "package": "pkg",
                "imports": ["."],
                "src_attr_labels": ["//pkg:app.py"],
                "srcs": [{"short_path": "pkg/app.py", "path": "pkg/app.py", "is_source": True}],
                "dep_attr_labels": ["//dep:lib"],
                "dep_json_paths": ["dep.json"],
                "keep_deps": ["//dep:kept"],
            }
        )
    )
    spec = load_target_spec(spec_file)
    assert spec.label == "//pkg:app"
    assert spec.package == "pkg"
    assert spec.imports == ["."]
    assert spec.src_attr_labels == ["//pkg:app.py"]
    assert spec.srcs == [SrcFile("pkg/app.py", "pkg/app.py", True)]
    assert spec.dep_attr_labels == ["//dep:lib"]
    assert spec.dep_json_paths == ["dep.json"]
    assert spec.keep_deps == ["//dep:kept"]


def test_load_dep_info_round_trip(tmp_path: Path) -> None:
    dep_file = tmp_path / "dep.json"
    dep_file.write_text(
        json.dumps(
            {
                "label": "//dep:lib",
                "package": "dep",
                "imports": ["."],
                "srcs": ["dep/lib.py"],
            }
        )
    )
    dep = load_dep_info(dep_file)
    assert dep == DepInfo("//dep:lib", "dep", ["."], ["dep/lib.py"])


def _dep_lib() -> DepInfo:
    return DepInfo(label="//dep:lib", package="dep", imports=["."], srcs=["dep/lib.py"])


def _app_spec(tmp_path: Path, app_src: str) -> TargetSpec:
    (tmp_path / "pkg").mkdir(exist_ok=True)
    app = tmp_path / "pkg" / "app.py"
    app.write_text(app_src)
    return TargetSpec(
        label="//pkg:app",
        package="pkg",
        imports=["."],
        src_attr_labels=["//pkg:app.py"],
        srcs=[SrcFile("pkg/app.py", str(app), True)],
        dep_attr_labels=[],
        dep_json_paths=[],
        keep_deps=[],
    )


def _test_spec(tmp_path: Path, conftest_src: str, test_src: str) -> TargetSpec:
    """A py_test target in the shape pytest targets have: conftest.py plus tests."""
    (tmp_path / "pkg").mkdir(exist_ok=True)
    conftest = tmp_path / "pkg" / "conftest.py"
    conftest.write_text(conftest_src)
    test = tmp_path / "pkg" / "test_app.py"
    test.write_text(test_src)
    return TargetSpec(
        label="//pkg:app_test",
        package="pkg",
        imports=["."],
        src_attr_labels=["//pkg:conftest.py", "//pkg:test_app.py"],
        srcs=[
            SrcFile("pkg/conftest.py", str(conftest), True),
            SrcFile("pkg/test_app.py", str(test), True),
        ],
        dep_attr_labels=[],
        dep_json_paths=[],
        keep_deps=[],
    )


def test_flags_a_dep_whose_modules_are_never_imported(tmp_path: Path) -> None:
    spec = _app_spec(tmp_path, "import os\n")
    assert analyze_spec(spec, [_dep_lib()]) == ["//dep:lib"]


def test_does_not_flag_a_dep_whose_module_is_imported(tmp_path: Path) -> None:
    spec = _app_spec(tmp_path, "import dep.lib\n")
    assert analyze_spec(spec, [_dep_lib()]) == []


def test_does_not_flag_a_dep_importable_only_under_the_consumer_root(tmp_path: Path) -> None:
    # `//bazel/rules:console_scripts_gen_test` shape: the dep declares no
    # `imports`, so under its own roots its src is `pkg.tool`. The consumer's
    # `imports = ["."]` puts `pkg` on PYTHONPATH, making `tool` the name the
    # consumer actually imports. That root counts for the dep's srcs too.
    dep = DepInfo(label="//pkg:tool", package="pkg", imports=[], srcs=["pkg/tool.py"])
    spec = _app_spec(tmp_path, "from tool import main\n")
    assert analyze_spec(spec, [dep]) == []


def test_flags_a_dep_the_consumer_root_does_not_reach_either(tmp_path: Path) -> None:
    dep = DepInfo(label="//pkg:tool", package="pkg", imports=[], srcs=["pkg/tool.py"])
    spec = _app_spec(tmp_path, "import os\n")
    assert analyze_spec(spec, [dep]) == ["//pkg:tool"]


def test_flags_a_dep_only_the_bare_parent_of_a_from_import_reaches(tmp_path: Path) -> None:
    # `from dep import other` names `dep` only to reach `dep.other`; it must not
    # keep `//dep:lib` (which provides `dep.lib`) alive.
    spec = _app_spec(tmp_path, "from dep import other\n")
    assert analyze_spec(spec, [_dep_lib()]) == ["//dep:lib"]


def test_does_not_flag_a_dep_reached_by_a_star_import_of_its_package(tmp_path: Path) -> None:
    nested = DepInfo(label="//dep:nested", package="dep", imports=["."], srcs=["dep/lib/impl.py"])
    spec = _app_spec(tmp_path, "from dep.lib import *\n")
    assert analyze_spec(spec, [nested]) == []


def test_does_not_flag_a_namespace_shim_dep(tmp_path: Path) -> None:
    # A dep whose srcs are all __init__.py only provides runtime package
    # scaffolding; it is never imported by name but must not be pruned.
    shim = DepInfo(label="//dep:shim", package="dep", imports=["."], srcs=["dep/__init__.py"])
    spec = _app_spec(tmp_path, "import os\n")
    assert analyze_spec(spec, [shim]) == []


def test_does_not_flag_a_conftest_dep(tmp_path: Path) -> None:
    conftest = DepInfo(
        label="//dep:conftest", package="dep", imports=["."], srcs=["dep/conftest.py"]
    )
    spec = _app_spec(tmp_path, "import os\n")
    assert analyze_spec(spec, [conftest]) == []


def test_does_not_flag_a_dep_whose_generated_src_the_target_lists(tmp_path: Path) -> None:
    # py_pytest_main pattern: the target lists the generated file the dep
    # produces (and references the dep by label in its srcs attribute), so the
    # dep is used even though no import references it.
    (tmp_path / "pkg").mkdir()
    app = tmp_path / "pkg" / "app.py"
    app.write_text("import os\n")
    spec = TargetSpec(
        label="//pkg:app",
        package="pkg",
        imports=["."],
        src_attr_labels=["//pkg:app.py", "//pkg:gen"],
        srcs=[
            SrcFile("pkg/app.py", str(app), True),
            SrcFile("pkg/__test__.py", "bazel-out/bin/pkg/__test__.py", False),
        ],
        dep_attr_labels=[],
        dep_json_paths=[],
        keep_deps=[],
    )
    gen = DepInfo(label="//pkg:gen", package="pkg", imports=["."], srcs=["pkg/__test__.py"])
    assert analyze_spec(spec, [gen]) == []


def test_does_not_flag_a_dep_a_conftest_src_imports(tmp_path: Path) -> None:
    # A conftest is unanalyzable as a dep, not as an analysis root: pytest
    # loads it by filename, but its own imports are evidence like any other.
    spec = _test_spec(tmp_path, conftest_src="import dep.lib\n", test_src="import os\n")
    assert analyze_spec(spec, [_dep_lib()]) == []


def test_flags_an_unused_dep_of_a_target_shipping_a_conftest(tmp_path: Path) -> None:
    spec = _test_spec(tmp_path, conftest_src="import os\n", test_src="import os\n")
    assert analyze_spec(spec, [_dep_lib()]) == ["//dep:lib"]


def test_reports_nothing_when_all_srcs_are_generated() -> None:
    # Generated srcs (py_doc_test / py_pytest_main output) are not action
    # inputs, leaving no AST evidence to reason about.
    spec = TargetSpec(
        label="//pkg:gen",
        package="pkg",
        imports=["."],
        src_attr_labels=["//pkg:gen_src"],
        srcs=[SrcFile("pkg/gen.py", "bazel-out/bin/pkg/gen.py", False)],
        dep_attr_labels=[],
        dep_json_paths=[],
        keep_deps=[],
    )
    assert analyze_spec(spec, [_dep_lib()]) == []


def test_does_not_flag_a_kept_dep(tmp_path: Path) -> None:
    # `tags = ["deballast-keep=//dep:lib"]` on the target exempts the dep.
    spec = _app_spec(tmp_path, "import os\n")._replace(keep_deps=["//dep:lib"])
    assert analyze_spec(spec, [_dep_lib()]) == []


def test_keep_only_exempts_the_named_dep(tmp_path: Path) -> None:
    other = DepInfo(label="//dep:other", package="dep", imports=["."], srcs=["dep/other.py"])
    spec = _app_spec(tmp_path, "import os\n")._replace(keep_deps=["//dep:lib"])
    assert analyze_spec(spec, [_dep_lib(), other]) == ["//dep:other"]


def test_canonical_label_passes_through_full_labels() -> None:
    assert canonical_label("//cmk/base/modes:modes", "pkg") == "//cmk/base/modes:modes"


def test_canonical_label_expands_implicit_target_name() -> None:
    assert canonical_label("//cmk/base/modes", "pkg") == "//cmk/base/modes:modes"


def test_canonical_label_resolves_same_package_reference() -> None:
    assert canonical_label(":helper", "cmk/gui") == "//cmk/gui:helper"


def test_keep_shorthand_label_exempts_the_dep(tmp_path: Path) -> None:
    # A keep written as `//dep` (implicit target name) exempts the dep whose
    # canonical label is `//dep:dep`, mirroring how Bazel reads `deps`.
    dep = DepInfo(label="//dep:dep", package="dep", imports=["."], srcs=["dep/lib.py"])
    spec = _app_spec(tmp_path, "import os\n")._replace(
        keep_deps=[canonical_label("//dep", "pkg")], dep_attr_labels=["//dep:dep"]
    )
    assert analyze_spec(spec, [dep]) == []


def test_stale_keeps_reports_keep_naming_no_declared_dep(tmp_path: Path) -> None:
    spec = _app_spec(tmp_path, "import os\n")._replace(
        keep_deps=["//dep:gone"], dep_attr_labels=["//dep:lib"]
    )
    assert stale_keeps(spec) == ["//dep:gone"]


def test_stale_keeps_empty_when_keep_matches_a_declared_dep(tmp_path: Path) -> None:
    spec = _app_spec(tmp_path, "import os\n")._replace(
        keep_deps=["//dep:lib"], dep_attr_labels=["//dep:lib"]
    )
    assert stale_keeps(spec) == []


def _write_spec_with_unused_dep(tmp_path: Path) -> Path:
    (tmp_path / "pkg").mkdir()
    app = tmp_path / "pkg" / "app.py"
    app.write_text("import os\n")
    dep_file = tmp_path / "dep.json"
    dep_file.write_text(
        json.dumps(
            {"label": "//dep:lib", "package": "dep", "imports": ["."], "srcs": ["dep/lib.py"]}
        )
    )
    spec_file = tmp_path / "spec.json"
    spec_file.write_text(
        json.dumps(
            {
                "label": "//pkg:app",
                "package": "pkg",
                "imports": ["."],
                "src_attr_labels": ["//pkg:app.py"],
                "srcs": [{"short_path": "pkg/app.py", "path": str(app), "is_source": True}],
                "dep_attr_labels": ["//dep:lib"],
                "dep_json_paths": [str(dep_file)],
                "keep_deps": [],
            }
        )
    )
    return spec_file


def test_main_with_exit_code_files_writes_reports_and_exits_zero(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    spec_file = _write_spec_with_unused_dep(tmp_path)
    human = tmp_path / "human.out"
    machine = tmp_path / "machine.report"
    human_ec = tmp_path / "human.exit_code"
    machine_ec = tmp_path / "machine.exit_code"
    monkeypatch.setattr(
        "sys.argv",
        [
            "deballast",
            "--spec",
            str(spec_file),
            "--human",
            str(human),
            "--machine",
            str(machine),
            "--human-exit-code",
            str(human_ec),
            "--machine-exit-code",
            str(machine_ec),
        ],
    )
    with pytest.raises(SystemExit) as excinfo:
        main()
    assert excinfo.value.code == 0
    sarif = json.loads(machine.read_text())
    assert [r["ruleId"] for r in sarif["runs"][0]["results"]] == ["unused-dep"]
    assert (
        sarif["runs"][0]["results"][0]["message"]["text"]
        == "//pkg:app: suspected unused dep //dep:lib"
    )
    assert (
        sarif["runs"][0]["results"][0]["locations"][0]["physicalLocation"]["artifactLocation"][
            "uri"
        ]
        == "pkg/BUILD"
    )
    assert "//pkg:app — 1 suspected unused dep(s):" in human.read_text()
    assert "  - //dep:lib" in human.read_text()
    assert human_ec.read_text() == "1\n"
    assert machine_ec.read_text() == "1\n"


def test_main_without_exit_code_files_exits_one_on_findings(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # aspect_rules_lint fail-on-violation mode: the process exit code carries
    # the result, failing the action.
    spec_file = _write_spec_with_unused_dep(tmp_path)
    human = tmp_path / "human.out"
    machine = tmp_path / "machine.report"
    monkeypatch.setattr(
        "sys.argv",
        ["deballast", "--spec", str(spec_file), "--human", str(human), "--machine", str(machine)],
    )
    with pytest.raises(SystemExit) as excinfo:
        main()
    assert excinfo.value.code == 1
    sarif = json.loads(machine.read_text())
    assert [r["ruleId"] for r in sarif["runs"][0]["results"]] == ["unused-dep"]


def test_main_rejects_a_single_exit_code_flag(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    spec_file = _write_spec_with_unused_dep(tmp_path)
    monkeypatch.setattr(
        "sys.argv",
        [
            "deballast",
            "--spec",
            str(spec_file),
            "--human",
            str(tmp_path / "h"),
            "--machine",
            str(tmp_path / "m"),
            "--human-exit-code",
            str(tmp_path / "h.ec"),
        ],
    )
    with pytest.raises(SystemExit) as excinfo:
        main()
    assert excinfo.value.code == 2
    assert "must be given together" in capsys.readouterr().err


def test_main_reports_stale_keep_tags(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    (tmp_path / "pkg").mkdir()
    app = tmp_path / "pkg" / "app.py"
    app.write_text("import os\n")
    spec_file = tmp_path / "spec.json"
    spec_file.write_text(
        json.dumps(
            {
                "label": "//pkg:app",
                "package": "pkg",
                "imports": ["."],
                "src_attr_labels": ["//pkg:app.py"],
                "srcs": [{"short_path": "pkg/app.py", "path": str(app), "is_source": True}],
                "dep_attr_labels": [],
                "dep_json_paths": [],
                "keep_deps": ["//dep:gone"],
            }
        )
    )
    human = tmp_path / "human.out"
    machine = tmp_path / "machine.report"
    monkeypatch.setattr(
        "sys.argv",
        ["deballast", "--spec", str(spec_file), "--human", str(human), "--machine", str(machine)],
    )
    with pytest.raises(SystemExit) as excinfo:
        main()
    assert excinfo.value.code == 1
    sarif = json.loads(machine.read_text())
    assert [r["ruleId"] for r in sarif["runs"][0]["results"]] == ["stale-keep"]
    assert (
        sarif["runs"][0]["results"][0]["message"]["text"]
        == "//pkg:app: deballast-keep tag //dep:gone names no declared dep"
    )
    assert "stale deballast-keep tag(s)" in human.read_text()


def test_human_report_empty_without_findings() -> None:
    assert human_report("//pkg:app", [], []) == ""


def test_sarif_report_empty_results_without_findings(tmp_path: Path) -> None:
    spec = _app_spec(tmp_path, "import os\n")
    sarif = json.loads(sarif_report(spec, [], []))
    assert sarif["version"] == "2.1.0"
    assert sarif["runs"][0]["results"] == []


def test_flags_deps_of_a_target_whose_srcs_import_nothing(tmp_path: Path) -> None:
    # A parsed src without imports is still evidence: none of the declared
    # deps can be used by it.
    spec = _app_spec(tmp_path, "ANSWER = 42\n")
    assert analyze_spec(spec, [_dep_lib()]) == ["//dep:lib"]


def test_reports_nothing_when_an_own_src_fails_to_parse(tmp_path: Path) -> None:
    # Python-2-only srcs (agent plugins) leave the import evidence incomplete;
    # flagging anything would risk false positives.
    spec = _app_spec(tmp_path, "print 'python 2'\n")
    assert analyze_spec(spec, [_dep_lib()]) == []


def test_relative_import_marks_sibling_dep_as_used(tmp_path: Path) -> None:
    # `from . import helper` in pkg/app.py resolves against the containing
    # package derived from the rule's imports attribute and matches a dep
    # providing pkg/helper.py, while an unrelated dep is still flagged.
    spec = _app_spec(tmp_path, "from . import helper\n")
    sibling = DepInfo(label="//pkg:helper", package="pkg", imports=["."], srcs=["pkg/helper.py"])
    assert analyze_spec(spec, [sibling, _dep_lib()]) == ["//dep:lib"]


def test_reports_nothing_for_an_umbrella_target(tmp_path: Path) -> None:
    # srcs = __init__.py, deps = the subpackages: the target exists to hand
    # consumers the whole package, so its deps are intentional.
    (tmp_path / "pkg").mkdir()
    init = tmp_path / "pkg" / "__init__.py"
    init.write_text("")
    spec = TargetSpec(
        label="//pkg:pkg",
        package="pkg",
        imports=["."],
        src_attr_labels=["//pkg:__init__.py"],
        srcs=[SrcFile("pkg/__init__.py", str(init), True)],
        dep_attr_labels=["//dep:lib"],
        dep_json_paths=[],
        keep_deps=[],
    )
    assert analyze_spec(spec, [_dep_lib()]) == []
