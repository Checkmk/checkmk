load("@aspect_rules_py//py:defs.bzl", "py_library")
load("@cmk_requirements//:requirements.bzl", "requirement")

package(default_visibility = ["//tests:__subpackages__"])

# The fake Livestatus fleet on its own, so the suites that drive a real site can serve the same
# generated estate over TCP without pulling in the in-process GUI fixtures.
py_library(
    name = "livestatus_fake",
    testonly = True,
    srcs = [
        "__init__.py",
        "livestatus_fake.py",
        "remotes.py",
        "report.py",
        "scenarios.py",
    ],
    imports = ["../../.."],
    deps = [
        "//packages/cmk-ccc:site",
        "//packages/cmk-livestatus-client:livestatus-api",
        "//packages/cmk-livestatus-client:py_livestatus",
    ],
)

# The suite that drives a real site. It is run by pytest through `perftest.sh` rather than by
# Bazel, like every other scenario here; the target exists so it is linted and type-checked
# with the rest, and so the top-level conftest may reach its report.
py_library(
    name = "site_comparison",
    testonly = True,
    srcs = [
        "__init__.py",
        "test_monitoring_views.py",
    ],
    imports = ["../../.."],
    deps = [
        ":livestatus_fake",
        "//tests/performance:sysmon",
        "//tests/testlib",
        requirement("pytest_benchmark"),
        requirement("requests"),
    ],
)
