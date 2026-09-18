load("@cmk_requirements//:requirements.bzl", "requirement")
load("//bazel/rules:py_cmk_test.bzl", "py_cmk_test")

package(default_visibility = ["//tests:__subpackages__"])

py_cmk_test(
    name = "in_process",
    size = "large",
    srcs = [
        "__init__.py",
        "components.py",
        "conftest.py",
        "fleet.py",
        "test_in_process.py",
    ],
    args = [
        "tests/performance/monitoring_views/in_process",
        # The comparison table this suite prints at the end is the result; pytest-benchmark's
        # own per-round chatter only buries it.
        "--benchmark-quiet",
    ],
    env = {"EDITION": "community"},
    tags = [
        "exclusive",  # a timing measurement wants the machine to itself
        "external",  # never serve a cached result for a measurement
        "manual",  # run on request, not on every build
    ],
    use_project_pytest_config = True,
    # listed in the registry of Bazel-based performance suites
    visibility = ["//tests/performance:__pkg__"],
    deps = [
        "//cmk/gui:auth_core",
        "//cmk/gui:config",
        "//cmk/gui:core_toolkit",
        "//cmk/gui:html_toolkit",
        "//cmk/gui:page_toolkit",
        "//cmk/gui/data_source",
        "//cmk/gui/monitor/command",
        "//cmk/gui/monitor/hosts",
        "//cmk/gui/monitor/services",
        "//cmk/gui/openapi/api_endpoints",
        "//cmk/gui/openapi/framework",
        "//cmk/gui/sidebar",
        "//cmk/gui/userdb",
        "//cmk/gui/views",
        "//cmk/gui/visuals",
        "//cmk/gui/wato",
        "//cmk/gui/watolib",
        "//cmk/plugins",
        "//packages/cmk-ccc:user",
        "//packages/cmk-ccc:version",
        "//tests/performance/monitoring_views:livestatus_fake",
        "//tests/testlib:fake_site",
        "//tests/testlib/gui",
        requirement("flask"),
        requirement("pytest-mock"),
        requirement("pytest_benchmark"),
    ],
)
