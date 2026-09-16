load("@cmk_requirements//:requirements.bzl", "requirement")
load("//bazel/rules:py_cmk_test.bzl", "py_cmk_test")

py_cmk_test(
    name = "cli",
    size = "small",
    srcs = glob(["**/*.py"]),
    args = ["--random-order-bucket=global"],
    env = {"EDITION": "community"},
    tags = [
        # discover_modes() imports these at runtime; without them it silently
        # finds fewer commands and the parametrized tests shrink unnoticed.
        "deballast-keep=//cmk/base:app",  # the commands of the transitional module list
        "deballast-keep=//cmk/plugins:plugins",  # the cmk/plugins/<family>/cli/ plug-ins
    ],
    use_project_pytest_config = True,
    visibility = ["//visibility:private"],
    deps = [
        "//cmk/base:app",
        "//cmk/cli/engine",
        "//cmk/plugins",
        "//packages/cmk-plugin-apis:cli",
        "//tests/unit:conftest",
        requirement("pytest-random-order"),
    ],
)
