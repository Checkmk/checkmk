load("//bazel/rules:py_cmk_test.bzl", "py_cmk_test")

py_cmk_test(
    name = "painter",
    srcs = glob(["**/*.py"]),
    args = [
        "tests/unit/cmk/gui/painter",
    ],
    env = {"EDITION": "community"},
    use_project_pytest_config = True,
    deps = [
        "//cmk/gui:config",
        "//cmk/gui/painter:v0_base",
        "//cmk/gui/utils:html",
        "//cmk/gui/utils:roles",
        "//tests/unit:conftest",
        "//tests/unit/cmk/gui:conftest",
    ],
)
