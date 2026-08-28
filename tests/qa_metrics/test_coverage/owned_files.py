#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""List what a component owns: its Python sources, and the packages holding them.

* ``--paths-out``: the component's source paths, which restrict the coverage
  tracefile to the component and supply the denominator for files no test loaded
* ``--packages-out``: the Bazel packages holding those sources, over which the
  test selection finds every test that can cover the component

Packages rather than the source files themselves: a file no target lists in its
``srcs`` has no valid label and would fail the query, whereas ``//pkg:*`` always
resolves. The superset that selects is cheap, the repository splitting its
``BUILD`` files finely.
"""

import argparse
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from tests.qa_metrics.components import load_ownership, UnknownComponentError
from tests.qa_metrics.test_coverage._file_lists import source_paths, tracked_files


def main() -> None:
    args = _parse_args()

    ownership = load_ownership(_tracked_python_files(args.repo_root))
    try:
        owned = ownership.paths_owned_by(args.component)
    except UnknownComponentError as exc:
        raise SystemExit(str(exc)) from None
    measured = set(source_paths(args.source_labels, args.repo_root))
    present = [path for path in owned if path in measured]
    if not present:
        raise SystemExit(_nothing_to_measure(args.component, owned))

    args.paths_out.write_text("".join(f"{path}\n" for path in present))
    args.packages_out.write_text(_package_patterns(present, args.repo_root))
    print(f"{args.component}: owns {len(present)} source file(s)", file=sys.stderr)


def _nothing_to_measure(component: str, owned: Sequence[Path]) -> str:
    """Why a component has no denominator, told apart by what it does own.

    The two need different fixes: owning nothing is a gap in the ``OWNERS`` files,
    owning only test support means there is nothing a number could be *about*.
    """
    if not owned:
        return f"Component {component!r} owns no Python file, so there is nothing to measure."
    return (
        f"Component {component!r} owns {len(owned)} Python file(s), none of which the coverage "
        "run measures: each is either testonly to Bazel, untracked, or compiled by no py rule. "
        "There is nothing to measure."
    )


def _bazel_package(path: Path, repo_root: Path) -> str | None:
    """Label of the Bazel package containing ``path``, or ``None`` if it has none.

    Walks the finite ancestor chain rather than looping until ``Path(".")``, which
    an absolute ``path`` never reaches.
    """
    for directory in path.parents:
        if any((repo_root / directory / name).is_file() for name in ("BUILD", "BUILD.bazel")):
            return "//" if directory == Path(".") else f"//{directory}"
    return None


def _tracked_python_files(repo_root: Path) -> list[Path]:
    """Every tracked ``.py`` file, test support included.

    Owning tests is what tells a component owning nothing from one owning only
    tests; :func:`main` drops them again.
    """
    return [path for path in tracked_files(repo_root) if path.suffix == ".py"]


def _package_patterns(paths: Sequence[Path], repo_root: Path) -> str:
    """The ``//pkg:*`` patterns covering ``paths``, one per line.

    A path in no Bazel package is reported rather than dropped: no test can be
    selected for it, so it is a hole in the measurement.
    """
    package_per_path = {path: _bazel_package(path, repo_root) for path in paths}
    if unpackaged := sorted(path for path, pkg in package_per_path.items() if pkg is None):
        print(
            f"Warning: {len(unpackaged)} owned source file(s) belong to no Bazel package, so no "
            f"test can be selected for them. First {min(3, len(unpackaged))}: "
            f"{', '.join(str(path) for path in unpackaged[:3])}",
            file=sys.stderr,
        )
    packages = sorted({pkg for pkg in package_per_path.values() if pkg is not None})
    return "".join(f"{package}:*\n" for package in packages)


@dataclass(frozen=True, kw_only=True)
class _Args:
    component: str
    repo_root: Path
    source_labels: Path
    paths_out: Path
    packages_out: Path


def _parse_args() -> _Args:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--component", required=True, help="component id, as used in OWNERS files")
    parser.add_argument(
        "--repo-root",
        required=True,
        type=Path,
        help="Repository root the paths are relative to. Needed because the "
        "working directory is not the repo under `bazel run`.",
    )
    parser.add_argument(
        "--source-labels",
        required=True,
        type=Path,
        help="Bazel labels of the measured source files, one per line",
    )
    parser.add_argument(
        "--paths-out", required=True, type=Path, help="write the owned file paths here"
    )
    parser.add_argument(
        "--packages-out",
        required=True,
        type=Path,
        help="write the source files' Bazel package patterns here, one `//pkg:*` per line",
    )
    args = parser.parse_args()
    return _Args(
        component=args.component,
        repo_root=args.repo_root,
        source_labels=args.source_labels,
        paths_out=args.paths_out,
        packages_out=args.packages_out,
    )


if __name__ == "__main__":
    main()
