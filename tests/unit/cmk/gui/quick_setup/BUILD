load("@cmk_requirements//:requirements.bzl", "requirement")
load("//bazel/rules:py_cmk_test.bzl", "py_cmk_test")

py_cmk_test(
    name = "quick_setup",
    srcs = glob(["**/*.py"]),
    args = [
        "tests/unit/cmk/gui/quick_setup",
    ],
    env = {"EDITION": "community"},
    use_project_pytest_config = True,
    deps = [
        "//cmk/gui/form_specs",
        "//cmk/gui/quick_setup",
        "//cmk/server_side_calls_backend",
        "//cmk/utils",
        "//packages/cmk-ccc:user",
        "//packages/cmk-ccc:version",
        "//packages/cmk-plugin-apis:password_store",
        "//packages/cmk-plugin-apis:rulesets",
        "//packages/cmk-plugin-apis:server_side_calls",
        "//tests/unit:conftest",
        "//tests/unit/cmk/gui:conftest",
        requirement("polyfactory"),
        requirement("pytest-mock"),
    ],
)
