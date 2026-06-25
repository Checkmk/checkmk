load("@aspect_rules_py//py:defs.bzl", "py_pytest_main")
load("@cmk_requirements//:requirements.bzl", "requirement")
load("//bazel/rules:py_cmk_test.bzl", "py_cmk_test")

py_pytest_main(
    name = "__test__",
    deps = [
        requirement("coverage"),
        requirement("pytest"),
    ],
)

py_cmk_test(
    name = "quick_setup",
    srcs = ["__test__.py"] + glob(["**/*.py"]),
    args = [
        "tests/unit/cmk/gui/quick_setup",
    ],
    env = {"EDITION": "community"},
    main = ":__test__.py",
    use_project_pytest_config = True,
    deps = [
        ":__test__",
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
