load("@aspect_rules_py//py:defs.bzl", "py_library")
load("@cmk_requirements//:requirements.bzl", "requirement")

package(default_visibility = ["//tests:__subpackages__"])

py_library(
    name = "performance",
    testonly = True,
    srcs = glob(
        ["**/*.py"],
        exclude = [
            "__init__.py",
            "sysmon.py",
        ],
    ),
    imports = ["../.."],
    deps = [
        ":sysmon",
        requirement("pytest"),
        requirement("psycopg"),
        requirement("jira"),
        requirement("matplotlib"),
        requirement("requests"),
        requirement("playwright"),
        requirement("pytest_benchmark"),
        requirement("cryptography"),
        "//tests/testlib",
        "//tests/testlib/common:repo",
        "//tests/testlib/common:utils",
    ],
)

py_library(
    name = "sysmon",
    testonly = True,
    srcs = [
        "__init__.py",
        "sysmon.py",
    ],
    imports = ["../.."],
    # Also used by performance suites living in their components, so their
    # resource tracking feeds the same reporting pipeline.
    visibility = ["//non-free/packages/cmk-metric-backend:__pkg__"],
    deps = [
        "//tests:pkg_marker",
        "//tests/testlib",
        requirement("psutil"),
    ],
)

# Registry of the Bazel-based performance suites: CI runs this suite via
# `bazel test` and perftest_upload.sh collects every listed test's results
# from bazel-testlogs, so a new component suite only needs an entry in this
# list instead of its own CI job.
test_suite(
    name = "bazel_performance",
    tags = ["manual"],
    tests = [
        "//non-free/packages/cmk-metric-backend:performance",
    ],
)

sh_library(
    name = "performance_sh",
    srcs = [
        "database/mk_client_cert.sh",
        "database/mk_server_cert.sh",
        "perftest.sh",
        "perftest_upload.sh",
    ],
)
