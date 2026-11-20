load("@cmk_requirements//:requirements.bzl", "requirement")
load("//bazel/rules:py_cmk_test.bzl", "py_cmk_test")

py_cmk_test(
    name = "png_renderer",
    size = "small",
    srcs = glob(["**/*.py"]),
    use_project_pytest_config = True,
    visibility = ["//visibility:private"],
    deps = [
        "//cmk/png_renderer:process",
        requirement("matplotlib"),
        requirement("numpy"),
    ],
)
