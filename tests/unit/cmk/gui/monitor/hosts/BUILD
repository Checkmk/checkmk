load("@cmk_requirements//:requirements.bzl", "requirement")
load("//bazel/rules:py_cmk_test.bzl", "py_cmk_test")

py_cmk_test(
    name = "hosts",
    srcs = glob(["**/*.py"]),
    use_project_pytest_config = True,
    deps = [
        "//cmk/gui/monitor/hosts",
        requirement("polyfactory"),
    ],
)
