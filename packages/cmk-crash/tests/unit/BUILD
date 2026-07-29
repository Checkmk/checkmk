load("@cmk_requirements//:requirements.bzl", "requirement")
load("//bazel/rules:py_cmk_test.bzl", "py_cmk_test")

py_cmk_test(
    name = "unit",
    size = "small",
    srcs = glob(["**/*.py"]),
    deps = [
        "//packages/cmk-crash:crash",
        "//packages/cmk-crash:crash_reporting",
        "//packages/cmk-crash:plugins",
        "//packages/cmk-plugin-apis:diagnostics",
        requirement("requests"),
        requirement("responses"),
    ],
)
