load("@aspect_rules_py//py:defs.bzl", "py_library")

py_library(
    name = "openapi_test",
    testonly = True,
    srcs = glob(["**/*.py"]),
    imports = ["../../.."],
    visibility = ["//tests/openapi:__subpackages__"],
    deps = [
        "//packages/cmk-plugin-apis:graphing",
        "//packages/cmk-plugin-apis:rulesets",
    ],
)
