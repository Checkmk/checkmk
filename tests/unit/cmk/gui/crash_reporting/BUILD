load("@aspect_rules_py//py:defs.bzl", "py_test")
load("@cmk_requirements//:requirements.bzl", "requirement")

py_test(
    name = "crash_reporting",
    srcs = glob(["**/*.py"]),
    args = ["tests/unit/cmk/gui/crash_reporting"],
    pytest_main = True,
    deps = [
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
