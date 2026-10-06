load("@cmk_requirements//:requirements.bzl", "requirement")
load("//bazel/rules:py_cmk_test.bzl", "py_cmk_test")

py_cmk_test(
    name = "gui",
    size = "small",
    srcs = glob(["**/*.py"]),
    use_project_pytest_config = True,
    visibility = ["//visibility:private"],
    deps = [
        "//tests/testlib/unit",
        requirement("flask"),
    ],
)
