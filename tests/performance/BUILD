load("@aspect_rules_py//py:defs.bzl", "py_library")
load("@cmk_requirements//:requirements.bzl", "requirement")

package(default_visibility = ["//tests:__subpackages__"])

# The `tests.performance` package itself, for every target below it to import through.
py_library(
    name = "pkg",
    testonly = True,
    srcs = ["__init__.py"],
    imports = ["../.."],
    visibility = ["//tests/performance:__subpackages__"],
    deps = ["//tests:pkg_marker"],
)

# The same for `tests.performance.component`, which holds only suites with targets of their own.
py_library(
    name = "component_pkg",
    testonly = True,
    srcs = ["component/__init__.py"],
    imports = ["../.."],
    visibility = ["//tests/performance/component:__subpackages__"],
    deps = [":pkg"],
)

py_library(
    name = "performance",
    testonly = True,
    # The site suite (`system/`) and the reporting carry no Bazel target of their own -
    # `perftest.sh` runs the site suite with pytest - so they are globbed in here to be linted
    # and type-checked with everything else. `testlib/` and the component suites are Bazel
    # packages of their own, which the glob does not reach into.
    srcs = glob(
        ["**/*.py"],
        exclude = [
            "__init__.py",
            "benchmark_json.py",
            "component/__init__.py",
            "sysmon.py",
        ],
    ),
    imports = ["../.."],
    deps = [
        ":pkg",
        ":sysmon",
        "//tests/performance/testlib:livestatus_fake",
        requirement("pytest"),
        requirement("psycopg"),
        requirement("jira"),
        requirement("matplotlib"),
        requirement("requests"),
        requirement("playwright"),
        requirement("pytest_benchmark"),
        requirement("cryptography"),
        "//tests/testlib/common",
        "//tests/testlib/system",
    ],
)

# What every performance suite needs to feed the reporting, wherever it lives: the resource
# tracking and the benchmark.json plugin. Suites in other packages use them too, which is why
# they stay at this level.
py_library(
    name = "sysmon",
    testonly = True,
    srcs = ["sysmon.py"],
    imports = ["../.."],
    visibility = [
        "//non-free/packages/cmk-data-backend:__pkg__",
        "//tests/performance:__subpackages__",
    ],
    deps = [
        ":pkg",
        "//tests/testlib/common",
        requirement("psutil"),
    ],
)

py_library(
    name = "benchmark_json",
    testonly = True,
    srcs = ["benchmark_json.py"],
    imports = ["../.."],
    # Loaded by the Bazel-based performance suites with `-p tests.performance.benchmark_json`.
    visibility = [
        "//non-free/packages/cmk-data-backend:__pkg__",
        "//tests/performance:__subpackages__",
    ],
    deps = [
        ":pkg",
        requirement("pytest"),
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
        "//non-free/packages/cmk-data-backend:performance",
        "//tests/performance/component/monitoring_views",
    ],
)

sh_library(
    name = "performance_sh",
    srcs = [
        "perftest.sh",
        "perftest_upload.sh",
        "reporting/database/mk_client_cert.sh",
        "reporting/database/mk_server_cert.sh",
    ],
)
