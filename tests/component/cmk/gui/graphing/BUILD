load("//bazel/rules:py_cmk_test.bzl", "py_cmk_test")

py_cmk_test(
    name = "png_rendering",
    size = "small",
    srcs = ["test_png_rendering.py"],
    use_project_pytest_config = True,
    visibility = ["//visibility:private"],
    deps = [
        "//cmk/gui/graphing",
        "//cmk/gui/utils",
        "//packages/cmk-graphing-engine",
    ],
)
