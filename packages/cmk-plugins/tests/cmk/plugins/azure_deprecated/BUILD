load("@cmk_requirements//:requirements.bzl", "requirement")
load("//bazel/rules:py_cmk_test.bzl", "py_cmk_test")

py_cmk_test(
    name = "azure_deprecated-test",
    size = "small",
    srcs = glob(["**/*.py"]),
    deps = [
        "//packages/cmk-plugins/cmk/plugins/azure_deprecated",
        requirement("msal"),
        requirement("pydantic"),
        requirement("pytest-asyncio"),
        requirement("requests"),
        requirement("time-machine"),
    ],
)
