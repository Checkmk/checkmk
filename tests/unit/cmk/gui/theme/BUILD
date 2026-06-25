load("//bazel/rules:py_cmk_test.bzl", "py_cmk_test")

py_cmk_test(
    name = "theme",
    srcs = glob(["**/*.py"]),
    args = ["tests/unit/cmk/gui/theme"],
    use_project_pytest_config = True,
    deps = [
        "//cmk/gui:html_toolkit",
    ],
)
