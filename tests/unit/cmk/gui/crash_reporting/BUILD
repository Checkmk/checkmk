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
    name = "crash_reporting",
    srcs = ["__test__.py"] + glob(["**/*.py"]),
    args = ["tests/unit/cmk/gui/crash_reporting"],
    main = ":__test__.py",
    use_project_pytest_config = True,
    deps = [
        ":__test__",
        "//cmk/gui:core_toolkit",
        "//cmk/gui/crash_reporting",
        "//packages/cmk-ccc:crash-reporting",
        "//packages/cmk-livestatus-client:py_livestatus",
        requirement("polyfactory"),
        requirement("pytest"),
        requirement("werkzeug"),
    ],
)
