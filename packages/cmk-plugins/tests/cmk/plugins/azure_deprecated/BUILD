load("@cmk_requirements//:requirements.bzl", "requirement")
load("//bazel/rules:py_cmk_test.bzl", "py_cmk_test")

py_cmk_test(
    name = "azure_deprecated-test",
    size = "small",
    srcs = glob(["**/*.py"]),
    deps = [
        "//packages/cmk-plugins/cmk/plugins/azure_deprecated",
        requirement("pytest-asyncio"),
        requirement("time-machine"),
    ],
)
