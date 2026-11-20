load("//bazel/rules:py_cmk_test.bzl", "py_cmk_test")

py_cmk_test(
    name = "png_rendering",
    size = "small",
    srcs = ["test_png_rendering.py"],
    tags = ["deballast-keep=//cmk/png_renderer:process"],
    use_project_pytest_config = True,
    visibility = ["//visibility:private"],
    deps = [
        "//cmk/gui/png",
        "//cmk/gui/utils",
        "//cmk/png_renderer:process",
        "//packages/cmk-graphing-engine",
    ],
)
