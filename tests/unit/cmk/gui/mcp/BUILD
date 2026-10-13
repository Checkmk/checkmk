load("//bazel/rules:py_cmk_test.bzl", "py_cmk_test")

py_cmk_test(
    name = "mcp_tests",
    srcs = glob(["**/*.py"]),
    args = ["tests/unit/cmk/gui/mcp"],
    env = {"EDITION": "community"},
    use_project_pytest_config = True,
    deps = [
        "//cmk/gui:auth_core",
        "//cmk/gui/openapi/framework",
        "//cmk/gui/openapi/restful_objects",
        "//packages/cmk-web/cmk/web/utils",
        "//tests/unit:conftest",
        "//tests/unit/cmk/gui:conftest",
        "//tests/unit/cmk/gui:init_py",
    ],
)
