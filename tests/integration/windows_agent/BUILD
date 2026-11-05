load("//bazel/rules:py_cmk_test.bzl", "py_cmk_test")

py_cmk_test(
    name = "windows_agent",
    srcs = glob(["*.py"]),
    args = ["tests/integration/windows_agent"],
    data = ["//agents/wnx:include/wnx/upgrade.h"],
    env = {"UPGRADE_H": "$(rootpath //agents/wnx:include/wnx/upgrade.h)"},
    deps = ["//packages/cmk-plugin-apis:bakery"],
)
