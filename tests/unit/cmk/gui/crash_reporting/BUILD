load("@aspect_rules_py//py:defs.bzl", "py_pytest_main", "py_test")
load("@cmk_requirements//:requirements.bzl", "requirement")

py_pytest_main(
    name = "__test__",
    deps = [
        requirement("coverage"),
        requirement("pytest"),
    ],
)

py_test(
    name = "crash_reporting",
    srcs = ["__test__.py"] + glob(["**/*.py"]),
    args = ["tests/unit/cmk/gui/crash_reporting"],
    main = ":__test__.py",
    deps = [
        ":__test__",
        "//cmk/gui:exceptions",
        "//cmk/gui:http",
        "//cmk/gui/crash_reporting",
        "//packages/cmk-ccc:crash-reporting",
        "//packages/cmk-livestatus-client:py_livestatus",
        requirement("polyfactory"),
        requirement("pytest"),
        requirement("werkzeug"),
    ],
)
