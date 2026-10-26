load("@cmk_requirements//:requirements.bzl", "requirement")
load("@rules_pkg//pkg:mappings.bzl", "pkg_files", "pkg_mkdirs", "strip_prefix")
load("@rules_python//python:defs.bzl", "py_library")
load("//bazel/rules:pkg.bzl", "pkg_tar")
load("//bazel/rules:xcomp/qemu_test.bzl", "qemu_test")

py_library(
    name = "wnx-agent-integration-python-tests",
    srcs = [
        "__init__.py",
        "conftest.py",
        "test_check_mk_cmd_line.py",
        "test_check_mk_run.py",
        "test_python_module.py",
        "utils.py",
    ],
    visibility = ["//visibility:public"],
    deps = [
        "//agents/wnx/tests/testlib:wnx-agent-python-testlib",
        requirement("pytest"),
        requirement("pyyaml"),
    ],
)

# The updater plugin test_python_module copies. The GPL-only repository
# has no non-free/, so there test_python_module skips itself.
filegroup(
    name = "cmk_update_agent",
    testonly = True,
    srcs = select({
        "@//:gpl+nonfree_repo": ["//non-free/packages/cmk-update-agent:cmk_update_agent.py"],
        "@//:gpl_repo": [],
    }),
)

pkg_files(
    name = "integration_qemu_repo",
    testonly = True,
    srcs = glob(
        ["*.py"],
        exclude = ["integration_qemu.py"],
    ) + [":cmk_update_agent"],
    prefix = "repo",
    strip_prefix = strip_prefix.from_root(),
)

pkg_files(
    name = "integration_qemu_test_root",
    srcs = [
        "//agents/modules/windows:python_3_cab",
        "//packages/cmk-agent-ctl:cmk-agent-ctl-windows",
    ],
    prefix = "base/test/root",
    renames = {"//agents/modules/windows:python_3_cab": "python-3.cab"},
)

# The suite checks the cab in the install dir and unpacks the root one.
pkg_files(
    name = "integration_qemu_install_modules",
    srcs = ["//agents/modules/windows:python_3_cab"],
    prefix = "base/test/data/install/modules",
    renames = {"//agents/modules/windows:python_3_cab": "python-3.cab"},
)

pkg_mkdirs(
    name = "integration_qemu_dirs",
    dirs = [
        "base/test/data/bin",
        "base/test/data/modules/python-3",
        "base/test/data/plugins",
    ],
)

# On top of the shared layout (//agents/wnx/tests/qemu:pytest_stage), as
# run_tests.ps1's Create_IntegrationTestDir:
#   repo\             + the suite and the non-free updater plugin it copies
#   base\test\root\   + cmk-agent-ctl.exe + python-3.cab
#   base\test\data\   user dir with the layout the suite expects
pkg_tar(
    name = "integration_qemu_stage",
    testonly = True,
    srcs = [
        ":integration_qemu_dirs",
        ":integration_qemu_install_modules",
        ":integration_qemu_repo",
        ":integration_qemu_test_root",
        "//agents/wnx/tests/qemu:pytest_stage",
    ],
    extension = "tar.gz",
)

qemu_test(
    name = "integration-qemu",
    src = "integration_qemu.py",
    args = ["$(rootpath //agents/wnx:cmk_version_flag)"],
    data = ["//agents/wnx:cmk_version_flag"],
    stage = ":integration_qemu_stage",
    deps = ["//agents/wnx/tests/qemu:wnx_pytest_suite"],
)
