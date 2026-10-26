load("@aspect_rules_py//py:defs.bzl", "py_library")
load("@rules_pkg//pkg:mappings.bzl", "pkg_filegroup", "pkg_files", "strip_prefix")
load("//bazel/rules:crlf_files.bzl", "crlf_files")

# Shared by the *-qemu runners of the pytest suites (qemu_test deps).
py_library(
    name = "wnx_pytest_suite",
    srcs = ["wnx_pytest_suite.py"],
    imports = ["."],
    visibility = ["//agents/wnx/tests:__subpackages__"],
    deps = ["//bazel/tools/windows_vm:tier"],
)

# cmd.exe needs CRLF line ends, which a Linux checkout lacks.
crlf_files(
    name = "pytest_stage_script",
    srcs = ["run-pytest-suite.cmd"],
    suffixes = [".cmd"],
)

pkg_files(
    name = "pytest_stage_root",
    testonly = True,
    srcs = [
        ":pytest_stage_script",
        "//agents/modules/windows:python_test_cab",
    ],
    renames = {"//agents/modules/windows:python_test_cab": "python-test.cab"},
)

pkg_files(
    name = "pytest_stage_test_root",
    testonly = True,
    srcs = [
        "//agents/wnx:check_mk_service-windows",
        "//agents/wnx:install/resources/check_mk.yml",
    ],
    prefix = "base/test/root",
    renames = {"//agents/wnx:check_mk_service-windows": "check_mk_agent.exe"},
)

pkg_files(
    name = "pytest_stage_test_root_plugins",
    srcs = ["//agents/windows/plugins:top_level_plugins"],
    prefix = "base/test/root/plugins",
)

pkg_files(
    name = "pytest_stage_testlib",
    srcs = ["//agents/wnx/tests/testlib:srcs"],
    prefix = "repo",
    strip_prefix = strip_prefix.from_root(),
)

# The part of run_tests.ps1's Create_*TestDir layout both pytest suites
# expect, for their *-qemu stages:
#   repo\             testlib, at its checkout-relative path
#   base\test\root\   check_mk_agent.exe + check_mk.yml + plugins (flat)
#   python-test.cab   the test Python, unpacked by run-pytest-suite.cmd
pkg_filegroup(
    name = "pytest_stage",
    testonly = True,
    srcs = [
        ":pytest_stage_root",
        ":pytest_stage_test_root",
        ":pytest_stage_test_root_plugins",
        ":pytest_stage_testlib",
    ],
    visibility = ["//agents/wnx/tests:__subpackages__"],
)
