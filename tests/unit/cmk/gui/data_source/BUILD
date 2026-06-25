load("//bazel/rules:py_cmk_test.bzl", "py_cmk_test")

py_cmk_test(
    name = "data_source",
    srcs = glob(["**/*.py"]),
    args = [
        "tests/unit/cmk/gui/data_source",
    ],
    env = {"EDITION": "community"},
    use_project_pytest_config = True,
    deps = [
        "//cmk/gui/data_source",
        "//tests/testlib:rest_api_client",
        "//tests/unit:conftest",
        "//tests/unit/cmk/gui:conftest",
    ],
)
