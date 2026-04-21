load("@aspect_rules_py//py:defs.bzl", "py_test")
load("@cmk_requirements//:requirements.bzl", "requirement")

py_test(
    name = "graphing",
    srcs = glob(["**/*.py"]),
    args = ["tests/unit/cmk/gui/graphing"],
    env = {"EDITION": "community"},
    pytest_main = True,
    deps = [
        "//cmk/gui:type_defs",
        "//cmk/gui:unit_formatter",
        "//cmk/gui/graphing",
        "//cmk/gui/utils:roles",
        "//cmk/gui/utils:temperate_unit",
        "//cmk/utils",
        "//packages/cmk-livestatus-client:livestatus-api",
        "//tests/unit:conftest",
        "//tests/unit/cmk/gui:conftest",
        requirement("pytest"),
        requirement("time-machine"),
    ],
)
