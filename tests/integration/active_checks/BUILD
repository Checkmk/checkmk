load("//bazel/rules:py_cmk_test.bzl", "py_cmk_test")

py_cmk_test(
    name = "active_checks",
    size = "small",
    srcs = glob(["*.py"]),
    args = ["tests/integration/active_checks"],
    data = ["//active_checks:check_mkevents"],
    env = {"CHECK_MKEVENTS": "$(rootpath //active_checks:check_mkevents)"},
    deps = ["//packages/cmk-ec"],
)
