load("@cmk_requirements//:requirements.bzl", "requirement")
load("@rules_pkg//pkg:mappings.bzl", "pkg_files", "pkg_mkdirs", "strip_prefix")
load("@rules_python//python:defs.bzl", "py_library")
load("//bazel/rules:crlf_files.bzl", "crlf_files")
load("//bazel/rules:pkg.bzl", "pkg_tar")
load("//bazel/rules:xcomp/qemu_test.bzl", "qemu_test")

py_library(
    name = "wnx-agent-regression-python-tests",
    testonly = True,
    srcs = [
        "__init__.py",
        "_test_section_logfiles.py",
        "conftest.py",
        "it_utils.py",
        "local.py",
        "test_agent_start_parameters.py",
        "test_section_check_mk.py",
        "test_section_df.py",
        "test_section_dotnet_clrmemory.py",
        "test_section_eventlog.py",
        "test_section_fileinfo.py",
        "test_section_mem.py",
        "test_section_mrpe.py",
        "test_section_plugin_group.py",
        "test_section_plugin_group_windows_if.py",
        "test_section_ps.py",
        "test_section_services.py",
        "test_section_spool.py",
        "test_section_systemtime.py",
        "test_section_uptime.py",
        "test_section_winperf.py",
        "test_section_wmi_cpuload.py",
        "test_section_wmi_webservices.py",
    ],
    visibility = ["//visibility:public"],
    deps = [
        "//agents/wnx/tests/testlib:wnx-agent-python-testlib",
        requirement("pytest"),
        requirement("pyyaml"),
    ],
)

pkg_files(
    name = "regression_qemu_suite",
    srcs = glob(
        ["*.py"],
        exclude = ["regression_qemu.py"],
    ),
    prefix = "repo",
    strip_prefix = strip_prefix.from_root(),
)

# Fixtures the suite finds next to itself, in ..\files\regression (prebuilt
# monty.exe/dummy.exe + scripts), with CRLF line ends like the autocrlf
# checkout of the Windows build nodes.
crlf_files(
    name = "regression_qemu_crlf",
    srcs = ["//agents/wnx:pytest_test_files"],
    suffixes = [
        ".bat",
        ".cmd",
        ".ps1",
        ".vbs",
    ],
)

pkg_files(
    name = "regression_qemu_fixtures",
    srcs = [":regression_qemu_crlf"],
    prefix = "repo",
    strip_prefix = strip_prefix.from_pkg("regression_qemu_crlf"),
)

pkg_mkdirs(
    name = "regression_qemu_dirs",
    dirs = [
        "base/test/data",
        "repo/artefacts",
    ],
)

# On top of the shared layout (//agents/wnx/tests/qemu:pytest_stage), as
# run_tests.ps1's Create_RegressionTestDir:
#   repo\             + the suite, its fixtures and the dirs local.py checks
#   base\test\data\   user dir (populated by the suite itself)
pkg_tar(
    name = "regression_qemu_stage",
    testonly = True,
    srcs = [
        ":regression_qemu_dirs",
        ":regression_qemu_fixtures",
        ":regression_qemu_suite",
        "//agents/wnx/tests/qemu:pytest_stage",
    ],
    extension = "tar.gz",
)

qemu_test(
    name = "regression-qemu",
    src = "regression_qemu.py",
    stage = ":regression_qemu_stage",
    deps = ["//agents/wnx/tests/qemu:wnx_pytest_suite"],
)
