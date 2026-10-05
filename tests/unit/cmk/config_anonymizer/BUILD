load("@cmk_requirements//:requirements.bzl", "requirement")
load("//bazel/rules:py_cmk_test.bzl", "py_cmk_test")

py_cmk_test(
    name = "config_anonymizer",
    srcs = glob(["**/*.py"]),
    args = ["--random-order-bucket=global"],
    env = {"EDITION": "community"},
    use_project_pytest_config = True,
    visibility = ["//visibility:private"],
    deps = [
        "//cmk/config_anonymizer",
        "//packages/cmk-ccc:debug",
        "//packages/cmk-check-engine/cmk/checkengine/plugin_backend",
        "//packages/cmk-check-engine/cmk/checkengine/plugins",
        "//tests/testlib/unit",
        "//tests/unit:conftest",
        requirement("flask"),
        requirement("pytest-random-order"),
    ],
)
