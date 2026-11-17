load("@aspect_rules_py//py:defs.bzl", "py_library")

package(default_visibility = ["//tests:__subpackages__"])

# Helpers for the suites in tests/performance. What suites in other packages need as well
# (sysmon, benchmark_json) lives one level up.

# The fake Livestatus fleet, shared by the monitoring-view comparison on a real site and its
# in-process twin, so the same generated estate serves both and neither depends on the other.
py_library(
    name = "livestatus_fake",
    testonly = True,
    srcs = [
        "__init__.py",
        "monitoring_views/__init__.py",
        "monitoring_views/livestatus_fake.py",
        "monitoring_views/remotes.py",
        "monitoring_views/report.py",
        "monitoring_views/scenarios.py",
    ],
    imports = ["../../.."],
    deps = [
        "//packages/cmk-ccc:site",
        "//packages/cmk-livestatus-client:livestatus-api",
        "//packages/cmk-livestatus-client:py_livestatus",
        "//tests/performance:pkg",
    ],
)
