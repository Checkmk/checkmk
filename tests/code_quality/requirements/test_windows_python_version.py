#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Cross-check the MODULE.bazel literals that must track PYTHON_VERSION_WINDOWS or,
for the Windows build nodes, PYTHON_VERSION.

MODULE.bazel files cannot load() //:package_versions.bzl, so a few literals are
spelled out there and must agree on the major.minor.  Drift also hard-fails at
analysis time, for PYTHON_VERSION only on Windows; these tests are the curated
diagnostic naming every literal.
"""

import re
from pathlib import Path

from tests.code_quality.bazel_utils import bazel_repo_root

_DIVERGENCE_CHECKLIST = (
    "See the 'Bumping the Python version' section of agents/modules/windows/README.md: "
    "changing PYTHON_VERSION_WINDOWS's major.minor requires updating "
    "both pip.parse(python_version = ...) in bazel/module/python_cab.MODULE.bazel and, in "
    "bazel/module/py.MODULE.bazel, its x86_64-pc-windows-msvc "
    "single_version_platform_override (not the one for the site's Python), the use_repo'd "
    "python_<X_Y>_x86_64-unknown-linux-gnu runtime repo, and -- only while the minor "
    "differs from the site toolchain's -- an extra python.toolchain(python_version) "
    "registration."
)


def _major_minor(text: str, pattern: str, where: Path) -> str:
    match = re.search(pattern, text)
    assert match, f"pattern {pattern!r} not found in {where}"
    return f"{match.group(1)}.{match.group(2)}"


def _windows_override_versions(py_module_text: str) -> set[str]:
    return {
        f"{major}.{minor}"
        for major, minor in re.findall(
            r'platform = "x86_64-pc-windows-msvc",\s*python_version = "(\d+)\.(\d+)',
            py_module_text,
        )
    }


def test_windows_python_version_module_literals() -> None:
    root = bazel_repo_root()
    package_versions = root / "package_versions.bzl"
    versions_text = package_versions.read_text()
    windows = _major_minor(
        versions_text, r'(?m)^PYTHON_VERSION_WINDOWS\s*=\s*"(\d+)\.(\d+)', package_versions
    )

    wnx_module = root / "bazel/module/python_cab.MODULE.bazel"
    # python-3.cab's closure and the test cab's (agents/wnx/tests' harness Python).
    for hub in ("windows_python_wheels", "windows_test_python_wheels"):
        hub_version = _major_minor(
            wnx_module.read_text(),
            rf'hub_name = "{hub}",\s*python_version = "(\d+)\.(\d+)"',
            wnx_module,
        )
        assert hub_version == windows, (
            f'pip.parse(hub_name = "{hub}") in {wnx_module.name} resolves for '
            f"Python {hub_version}, but PYTHON_VERSION_WINDOWS is on {windows}. "
            + _DIVERGENCE_CHECKLIST
        )

    py_module = root / "bazel/module/py.MODULE.bazel"
    py_module_text = py_module.read_text()
    override_versions = _windows_override_versions(py_module_text)
    assert windows in override_versions, (
        f"No x86_64-pc-windows-msvc single_version_platform_override in {py_module.name} "
        f"pins Python {windows} (PYTHON_VERSION_WINDOWS), only {sorted(override_versions)}. "
        + _DIVERGENCE_CHECKLIST
    )

    runtime_repo = f"python_{windows.replace('.', '_')}_x86_64-unknown-linux-gnu"
    assert re.search(rf'use_repo\(\s*python,\s*"{runtime_repo}"\s*\)', py_module_text), (
        f'use_repo(python, "{runtime_repo}") missing from {py_module.name}: '
        "//agents/modules/windows:windows_requirements resolves under this runtime "
        "(rules_uv py3_runtime). " + _DIVERGENCE_CHECKLIST
    )

    site = _major_minor(versions_text, r'(?m)^PYTHON_VERSION\s*=\s*"(\d+)\.(\d+)', package_versions)
    if site != windows:
        assert re.search(
            rf'python\.toolchain\([^)]*python_version = "{re.escape(windows)}"',
            py_module_text,
            re.DOTALL,
        ), (
            f"PYTHON_VERSION_WINDOWS ({windows}) diverges from PYTHON_VERSION ({site}), so "
            f"{py_module.name} must register the Windows minor with an extra "
            f'python.toolchain(python_version = "{windows}") -- and drop that registration '
            "again once the two re-converge (rules_python rejects duplicate registrations "
            "of the same version from one module). " + _DIVERGENCE_CHECKLIST
        )


def test_windows_build_nodes_have_a_toolchain_of_the_site_python() -> None:
    root = bazel_repo_root()
    package_versions = root / "package_versions.bzl"
    site = _major_minor(
        package_versions.read_text(), r'(?m)^PYTHON_VERSION\s*=\s*"(\d+)\.(\d+)', package_versions
    )
    py_module = root / "bazel/module/py.MODULE.bazel"

    override_versions = _windows_override_versions(py_module.read_text())

    assert site in override_versions, (
        f"No x86_64-pc-windows-msvc single_version_platform_override in {py_module.name} "
        f"pins the site's Python {site} (PYTHON_VERSION), only {sorted(override_versions)}. "
        "The Windows build nodes evaluate the pip extension, too, and its cmk_requirements "
        "hub needs a host interpreter of that version there."
    )
