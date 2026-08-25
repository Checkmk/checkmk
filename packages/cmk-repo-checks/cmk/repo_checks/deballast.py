#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""deballast - shed the dead weight from Bazel py_* dependency lists.

Report Bazel py_library/py_test deps that are not used by the target's own srcs.

This is the per-target checker behind the Bazel aspect in `deballast.bzl`
(same package). The aspect describes the analyzed target in a JSON spec file
(own srcs, `imports` attribute, package) and each declared py_* dep in a
small JSON file (the dep's direct srcs and `imports`). The checker parses the
target's own srcs with AST, collects every import, and flags deps whose
provided modules are never referenced - candidates for pruning.

This is a src-import-vs-declared-dep check with the following implemented:

- It only looks at a dep's DIRECT srcs, not its transitive closure.
- It does not check for MISSING deps.
- Module resolution uses each rule's `imports` attribute, mirroring Bazel's
  runtime rules.
- Relative imports (`from . import X`, `from .._utils import Y`) are resolved
  against the containing package of each src file.
- Every module path an import statement names is recorded, and a dep counts as
  used when it provides one of those paths, or provides a package one of them
  lives under (`import X.Y.Z` cannot resolve without loading `X.Y`). Both
  follow from the statement alone.
- Reachability beyond that is not inferred. Whether naming a package reaches a
  particular module inside it depends on what that package's `__init__.py`
  imports - a dep's file content, which the aspect does not ship. Deps
  reachable only that way, or only at runtime, are declared with
  `deballast-keep`. `//cmk/gui/plugins/views:views` is one: it ships a single
  empty `icons/utils.py`, so the only thing it contributes is the existence of
  the `cmk.gui.plugins.views[.icons]` import paths, which
  `cmk/gui/views/__init__.py` imports and fills by name injection for pre-2.1
  plug-ins.
- Namespace-shim deps (whose Python srcs are all `__init__.py` or generated
  `_namespace.py` files) are treated as implicitly used. They provide runtime
  package structure rather than anything AST-visible. (e.g.
  `//packages/cmk-ccc:_init`, `//cmk/gui/plugins/wato/check_parameters:stub`)
- pytest conftest deps (targets with at least one `conftest.py` src) are
  treated as implicitly used.
- Deps whose srcs are listed in the target's own srcs are treated as
  implicitly used.
- Deps without dep info (external targets such as pip requirements, non-py_*
  rules) are treated as implicitly used.
- A dep carrying a `deballast-keep=<label>` tag on the consuming target is
  exempted: it is imported for a side effect (e.g. runtime plugin discovery)
  by another target, not by name. The label accepts the same shorthands as
  `deps` (`//pkg` and `:name`); a keep naming no declared dep is reported as
  stale so exemptions cannot rot silently. Example:

      py_library(
          ...
          tags = ["deballast-keep=//cmk/base/modes:modes"],  # loaded via discover_modes()
      )
- Generated srcs of the analyzed target contribute no imports (they are not
  action inputs); targets whose srcs are all generated yield no findings.
- A `conftest.py` among the analyzed target's own srcs is parsed like any
  other src. It is only as a dep that a conftest is unanalyzable (nobody
  imports it by name); as an analysis root its own imports are the evidence,
  and skipping it would exempt most of the test tree.
- Namespace-shim targets are skipped as analysis roots, too: an umbrella
  target (srcs = `__init__.py`, deps = the subpackage targets) aggregates its
  deps on purpose.
- Targets with an own src that fails to parse (e.g. Python-2-only agent
  plugins) are skipped as analysis roots: with incomplete import evidence,
  any finding could be a false positive.

Usage (interactive, prints findings to the terminal):
    bazel lint //cmk/gui/wato:wato
    bazel lint //cmk/gui/...

Usage (CI / scripted, materializes the report files):
    bazel build --config=deballast //cmk/gui/...
    # quick check - human reports are empty when nothing is flagged:
    find bazel-bin -name "*.AspectRulesLintDeballast.out" -size +0c -exec cat {} +
    # machine reports are SARIF 2.1.0:
    find bazel-bin -name "*.AspectRulesLintDeballast.report" -size +0c \
        -exec jq -r '.runs[].results[].message.text' {} +

Output:
    A human-readable findings block in the file passed via --human (empty
    when nothing is flagged) and a SARIF 2.1.0 document in the file passed
    via --machine (empty results list when nothing is flagged), one result
    per finding (unused dep or stale deballast-keep tag), located at the
    target's BUILD file. With --human-exit-code/--machine-exit-code (only
    valid together) the result code (1 for findings, 0 otherwise) goes to
    those files and the process exits 0; without them the process itself
    exits 1 on findings (aspect_rules_lint fail-on-violation mode).
"""

import argparse
import ast
import json
import sys
from collections.abc import Iterable, Sequence
from pathlib import Path
from typing import NamedTuple


class SrcFile(NamedTuple):
    short_path: str
    path: str
    is_source: bool


class TargetSpec(NamedTuple):
    label: str
    package: str
    imports: list[str]
    src_attr_labels: list[str]
    srcs: list[SrcFile]
    dep_attr_labels: list[str]
    dep_json_paths: list[str]
    keep_deps: list[str]


class DepInfo(NamedTuple):
    label: str
    package: str
    imports: list[str]
    srcs: list[str]


def canonical_label(label: str, package: str) -> str:
    """Normalize a dep label to the canonical `//pkg:name` form.

    Accepts the shorthands Bazel accepts in `deps`: `//pkg/path` (implicit
    target name) and `:name` (same-package reference).
    """
    if label.startswith(":"):
        return f"//{package}{label}"
    if ":" not in label:
        return f"{label}:{label.rsplit('/', 1)[-1]}"
    return label


def load_target_spec(path: Path) -> TargetSpec:
    raw = json.loads(path.read_text())
    return TargetSpec(
        label=raw["label"],
        package=raw["package"],
        imports=list(raw["imports"]),
        src_attr_labels=list(raw["src_attr_labels"]),
        srcs=[SrcFile(s["short_path"], s["path"], s["is_source"]) for s in raw["srcs"]],
        dep_attr_labels=list(raw["dep_attr_labels"]),
        dep_json_paths=list(raw["dep_json_paths"]),
        keep_deps=[canonical_label(k, raw["package"]) for k in raw["keep_deps"]],
    )


def load_dep_info(path: Path) -> DepInfo:
    raw = json.loads(path.read_text())
    return DepInfo(
        label=raw["label"],
        package=raw["package"],
        imports=list(raw["imports"]),
        srcs=list(raw["srcs"]),
    )


def parse_python_source(path: Path) -> ast.Module | None:
    try:
        return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except OSError, SyntaxError, UnicodeDecodeError, ValueError:
        return None


def resolve_imports_root(package: str, imports_entry: str) -> str:
    """Resolve an `imports` attribute entry against its rule's BUILD package path.

    Returns the workspace-relative directory that Bazel places on PYTHONPATH.
    Examples:
        resolve_imports_root("packages/cmk-plugins/cmk/plugins/lib", "../../..")
            => "packages/cmk-plugins"
        resolve_imports_root("cmk/gui/nagvis", ".") => "cmk/gui/nagvis"
    """
    parts = [p for p in package.split("/") if p]
    for component in imports_entry.split("/"):
        if component in ("", "."):
            continue
        if component == "..":
            if parts:
                parts.pop()
        else:
            parts.append(component)
    return "/".join(parts)


def _module_under_root(file_path: str, module_root: str) -> str | None:
    """Python module name for a file under a given module root; None if outside."""
    if module_root:
        if not file_path.startswith(module_root + "/"):
            return None
        rel = file_path[len(module_root) + 1 :]
    else:
        rel = file_path
    parts = list(Path(rel).with_suffix("").parts)
    if parts and parts[-1] == "__init__":
        parts.pop()
    if not parts:
        return None
    return ".".join(parts)


def module_roots(package: str, imports: Iterable[str]) -> set[str]:
    """PYTHONPATH roots that a rule's srcs are reachable under.

    Each entry in the rule's `imports` attribute yields a module root. The
    workspace root is always included too - the `imports` attribute adds to
    PYTHONPATH but doesn't remove the workspace root, so downstream targets can
    import srcs via either path. Missing that root caused e.g.
    `//agents/plugins:agent-plugins-python` (with `imports=["."]`, so its files
    are `mk_podman` under its own root) to be flagged as unused by tests that
    import them as `agents.plugins.mk_podman`.
    """
    return {""}.union(resolve_imports_root(package, e) for e in imports)


def candidate_modules_for_path(short_path: str, roots: Iterable[str]) -> set[str]:
    """Candidate absolute module paths a src file is exposed as."""
    if not short_path.endswith(".py"):
        return set()
    return {mod for root in roots if (mod := _module_under_root(short_path, root))}


def modules_provided_by_dep(dep: DepInfo, consumer_roots: Iterable[str]) -> set[str]:
    """Absolute Python module paths provided by the dep's direct srcs.

    `consumer_roots` are the roots the *consuming* target puts on PYTHONPATH.
    They apply to the whole runfiles tree, so a dep's src is importable under
    them as well as under the dep's own roots. Ignoring them flagged
    `//bazel/rules:console_scripts_gen` as unused by
    `//bazel/rules:console_scripts_gen_test`, which declares `imports = ["."]`
    and does `from console_scripts_gen import ...` - a name that only exists
    under the consumer's root, not under the dep's.
    """
    roots = module_roots(dep.package, dep.imports) | set(consumer_roots)
    out: set[str] = set()
    for short_path in dep.srcs:
        out |= candidate_modules_for_path(short_path, roots)
    return out


def _basename(short_path: str) -> str:
    return short_path.rsplit("/", 1)[-1]


# `_namespace.py` is the repo's write_file convention for materializing an
# implicit namespace package in the runfiles tree (see e.g.
# cmk/gui/plugins/wato/check_parameters:stub).
_NAMESPACE_SCAFFOLDING_BASENAMES = frozenset({"__init__.py", "_namespace.py"})


def is_namespace_shim(src_paths: Sequence[str]) -> bool:
    if not src_paths:
        return False
    return all(_basename(p) in _NAMESPACE_SCAFFOLDING_BASENAMES for p in src_paths)


def is_pytest_conftest(src_paths: Sequence[str]) -> bool:
    """True if any of the rule's Python srcs is a `conftest.py`.

    conftest.py is auto-loaded by pytest via filesystem discovery; no test
    source imports it explicitly. Such targets are also commonly used as
    fixture hubs that transitively re-export test utilities. A conftest
    target that also ships helper modules (e.g. `conftest.py` +
    `mocks_and_helpers.py`) is still load-bearing via the conftest.py half,
    regardless of whether the helper is imported.
    """
    return any(_basename(p) == "conftest.py" for p in src_paths)


def shares_srcs_with_target(
    target_src_paths: set[str],
    target_src_attr_labels: Sequence[str],
    dep_label: str,
    dep_srcs: Iterable[str],
) -> bool:
    """True if the target's own srcs reference any of the dep's srcs.

    Two forms are accepted:
    - `dep_srcs` contains a file that also appears in the target's srcs
      (same file on both sides).
    - The target's `srcs` attribute lists `dep_label` itself (target uses the
      dep by label reference, e.g. `srcs = [":__test__"]` for a
      `py_pytest_main` output).
    """
    if dep_label in target_src_attr_labels:
        return True
    return any(s in target_src_paths for s in dep_srcs)


def imports_in_tree(tree: ast.Module, containing_packages: Iterable[str] = ()) -> frozenset[str]:
    """Return the module paths imported by a parsed Python module.

    `containing_packages` is the set of candidate packages the module belongs
    to (derived from its rule's imports attribute). Relative `from . import X`
    statements are resolved against each candidate — the union is returned.
    """
    refs: set[str] = set()
    pkgs = list(containing_packages)
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            refs.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            names = [alias.name for alias in node.names]
            if node.level == 0:
                if node.module:
                    refs |= _from_import_refs(node.module, names)
                continue
            # Relative: resolve against each candidate containing package.
            for pkg in pkgs:
                parts = pkg.split(".") if pkg else []
                up = node.level - 1
                if up > len(parts):
                    continue
                base = parts[: len(parts) - up]
                if node.module:
                    base.extend(node.module.split("."))
                if base:
                    refs |= _from_import_refs(".".join(base), names)
    return frozenset(refs)


def _from_import_refs(module: str, names: Iterable[str]) -> set[str]:
    """`from <module> import <names>`: the module itself and each named child.

    A `*` names no child - it binds whatever the package re-exports - so it
    contributes only `module`.
    """
    return {module} | {f"{module}.{name}" for name in names if name != "*"}


def _containing_packages_for_path(
    short_path: str, imports: Iterable[str], package: str
) -> set[str]:
    """Candidate containing-package paths for a src file (for relative-import resolution).

    For `foo/bar/__init__.py` candidate module `foo.bar`, the containing
    package IS `foo.bar`. For `foo/bar/baz.py` candidate module `foo.bar.baz`,
    the containing package is `foo.bar` (drop the last segment).
    """
    is_init = _basename(short_path) == "__init__.py"
    out: set[str] = set()
    for mod in candidate_modules_for_path(short_path, module_roots(package, imports)):
        if is_init:
            out.add(mod)
        else:
            parent = mod.rsplit(".", 1)[0] if "." in mod else ""
            if parent:
                out.add(parent)
    return out


def dep_is_used(dep_modules: set[str], target_imports: frozenset[str]) -> bool:
    """True if any module from the dep is reached by the target's imports.

    Two ways a dep module M can be reached, both implied by the import
    statement on its own:
    - Exact: M is imported verbatim.
    - Ancestor: something below M is imported, as `import X.Y.Z` does for a dep
      providing `X.Y` - Python cannot resolve `X.Y.Z` without loading `X.Y`.

    Naming a package does not reach the modules inside it; that depends on what
    the package's `__init__.py` imports, which is content of a dep and not
    available here. Deps used only that way carry a `deballast-keep` tag.
    """
    for mod in dep_modules:
        if mod in target_imports:
            return True
        if any(imp.startswith(mod + ".") for imp in target_imports):
            return True
    return False


def analyze_spec(spec: TargetSpec, deps: Sequence[DepInfo]) -> list[str]:
    """Return sorted list of pruneable dep labels for the target in `spec`."""
    own_paths = [s.short_path for s in spec.srcs]
    if is_namespace_shim(own_paths):
        # Umbrella targets (srcs = __init__.py, deps = the subpackages) exist
        # to hand consumers the whole package; their deps are intentional.
        return []
    target_imports: frozenset[str] = frozenset()
    parsed_any = False
    for src in spec.srcs:
        if not src.is_source or not src.short_path.endswith(".py"):
            # Generated srcs are not action inputs - they contribute no
            # imports, matching the predecessor which only saw checked-in
            # files.
            continue
        tree = parse_python_source(Path(src.path))
        if tree is None:
            # Unparseable own src (e.g. a Python-2-only agent plugin): the
            # import evidence is incomplete, so any finding could be a false
            # positive. Skip the whole target.
            return []
        parsed_any = True
        pkgs = _containing_packages_for_path(src.short_path, spec.imports, spec.package)
        target_imports |= imports_in_tree(tree, pkgs)
    if not parsed_any:
        # All srcs are generated (py_doc_test runners, py_pytest_main
        # outputs) - no AST evidence to work from.
        return []
    target_src_paths = set(own_paths)
    spec_roots = module_roots(spec.package, spec.imports)
    keep_deps = set(spec.keep_deps)
    pruneable: list[str] = []
    for dep in deps:
        if dep.label in keep_deps:
            continue  # explicitly exempted via deballast-keep tag
        if is_namespace_shim(dep.srcs):
            continue  # runtime package scaffolding; invisible to AST
        if is_pytest_conftest(dep.srcs):
            continue  # auto-discovered by pytest; never imported
        if shares_srcs_with_target(target_src_paths, spec.src_attr_labels, dep.label, dep.srcs):
            continue  # dep's srcs are used directly by target (e.g. py_pytest_main)
        modules = modules_provided_by_dep(dep, spec_roots)
        if not modules:
            continue  # dep provides no Python modules (e.g. data-only target)
        if not dep_is_used(modules, target_imports):
            pruneable.append(dep.label)
    return sorted(pruneable)


def stale_keeps(spec: TargetSpec) -> list[str]:
    """Keep entries naming no declared dep - typos or leftovers of removed deps.

    Without this, a `deballast-keep` tag that stops matching anything keeps
    silencing nothing and rots unnoticed.
    """
    return sorted(set(spec.keep_deps) - set(spec.dep_attr_labels))


def human_report(label: str, unused_deps: Sequence[str], stale_keep_tags: Sequence[str]) -> str:
    """Human-readable findings block; empty string when nothing is flagged."""
    lines = []
    if unused_deps:
        lines.append(f"{label} — {len(unused_deps)} suspected unused dep(s):")
        lines.extend(f"  - {dep}" for dep in unused_deps)
        lines.append(
            "Confirm with `bazel build`, `bazel lint`, and `bazel build --config=mypy` "
            'before removing; exempt runtime-loaded deps with tags = ["deballast-keep=<label>"].'
        )
    if stale_keep_tags:
        lines.append(f"{label} — {len(stale_keep_tags)} stale deballast-keep tag(s):")
        lines.extend(f"  - {kept} (names no declared dep)" for kept in stale_keep_tags)
    return "".join(f"{line}\n" for line in lines)


_SARIF_RULES = [
    {
        "id": "unused-dep",
        "shortDescription": {
            "text": "Declared dep provides no Python module imported by the target's own srcs"
        },
    },
    {
        "id": "stale-keep",
        "shortDescription": {"text": "deballast-keep tag names no declared dep"},
    },
]


def sarif_report(
    spec: TargetSpec, unused_deps: Sequence[str], stale_keep_tags: Sequence[str]
) -> str:
    """Findings as SARIF 2.1.0 JSON, located at the target's BUILD file.

    Matches the machine-report format of the other in-repo linters (astrein,
    python_extension_checker). The results list is empty when nothing is
    flagged.
    """

    def result(rule_id: str, message: str) -> dict[str, object]:
        return {
            "ruleId": rule_id,
            "level": "error",
            "message": {"text": message},
            "locations": [
                {
                    "physicalLocation": {
                        "artifactLocation": {
                            "uri": f"{spec.package}/BUILD",
                            "uriBaseId": "%SRCROOT%",
                        }
                    }
                }
            ],
        }

    results = [
        result("unused-dep", f"{spec.label}: suspected unused dep {dep}") for dep in unused_deps
    ] + [
        result("stale-keep", f"{spec.label}: deballast-keep tag {kept} names no declared dep")
        for kept in stale_keep_tags
    ]
    sarif = {
        "$schema": "https://raw.githubusercontent.com/oasis-tcs/sarif-spec/master/Schemata/sarif-schema-2.1.0.json",
        "version": "2.1.0",
        "runs": [
            {
                "tool": {
                    "driver": {
                        "name": "deballast",
                        "informationUri": "https://checkmk.com",
                        "rules": _SARIF_RULES,
                    }
                },
                "results": results,
            }
        ],
    }
    return json.dumps(sarif, indent=2)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0] if __doc__ else "")
    parser.add_argument("--spec", type=Path, required=True, help="Target spec JSON file")
    parser.add_argument("--human", type=Path, required=True, help="Human-readable report file")
    parser.add_argument("--machine", type=Path, required=True, help="Machine-readable report file")
    parser.add_argument(
        "--human-exit-code",
        type=Path,
        default=None,
        help="File to receive the result code; without it, exit 1 on findings",
    )
    parser.add_argument(
        "--machine-exit-code",
        type=Path,
        default=None,
        help="File to receive the result code; without it, exit 1 on findings",
    )
    args = parser.parse_args()
    if (args.human_exit_code is None) != (args.machine_exit_code is None):
        parser.error("--human-exit-code and --machine-exit-code must be given together")

    spec = load_target_spec(args.spec)
    deps = [load_dep_info(Path(p)) for p in spec.dep_json_paths]
    findings = analyze_spec(spec, deps)
    stale = stale_keeps(spec)

    args.human.write_text(human_report(spec.label, findings, stale))
    args.machine.write_text(sarif_report(spec, findings, stale))

    result = 1 if findings or stale else 0
    if args.human_exit_code is None:
        # aspect_rules_lint fail-on-violation mode: the action itself fails.
        if result:
            sys.stderr.write(human_report(spec.label, findings, stale))
        sys.exit(result)
    args.human_exit_code.write_text(f"{result}\n")
    args.machine_exit_code.write_text(f"{result}\n")
    sys.exit(0)


if __name__ == "__main__":
    main()
