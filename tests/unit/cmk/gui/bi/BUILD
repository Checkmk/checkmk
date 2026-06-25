load("//bazel/rules:py_cmk_test.bzl", "py_cmk_test")

py_cmk_test(
    name = "bi",
    srcs = glob(["**/*.py"]),
    args = [
        "tests/unit/cmk/gui/bi",
    ],
    env = {"EDITION": "community"},
    use_project_pytest_config = True,
    deps = [
        "//cmk/bi",
        "//cmk/gui:core_toolkit",
        "//cmk/gui/bi",
        "//packages/cmk-ccc:hostaddress",
        "//tests/unit:conftest",
        "//tests/unit/cmk/gui:conftest",
    ],
)
