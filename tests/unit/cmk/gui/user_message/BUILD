load("//bazel/rules:py_cmk_test.bzl", "py_cmk_test")

py_cmk_test(
    name = "user_message",
    srcs = glob(["**/*.py"]),
    args = [
        "tests/unit/cmk/gui/user_message",
    ],
    env = {"EDITION": "community"},
    use_project_pytest_config = True,
    deps = [
        "//tests/testlib:rest_api_client",
        "//tests/unit:conftest",
        "//tests/unit/cmk/gui:conftest",
    ],
)
