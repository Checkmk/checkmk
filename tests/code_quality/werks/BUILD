load("@aspect_rules_py//py:defs.bzl", "py_test")
load("@cmk_requirements//:requirements.bzl", "requirement")

py_test(
    name = "validation",
    srcs = glob(["**/*.py"]),
    data = [
        "//:defines.make",
        "//:werks_group",
    ],
    pytest_main = True,
    deps = [
        requirement("pytest"),
        "//packages/cmk-werks",
        "//tests/code_quality:bazel_utils",
    ],
)
