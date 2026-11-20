load("//bazel/rules:py_cmk_test.bzl", "py_cmk_test")

py_cmk_test(
    name = "client",
    size = "small",
    srcs = ["test_client.py"],
    tags = ["deballast-keep=//cmk/gui/png/renderer:process"],
    use_project_pytest_config = True,
    visibility = ["//visibility:private"],
    deps = [
        "//cmk/gui/png",
        "//cmk/gui/png/renderer:process",
        "//cmk/gui/utils",
        "//packages/cmk-graphing-engine",
    ],
)
