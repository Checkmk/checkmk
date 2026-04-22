load("@aspect_rules_py//py:defs.bzl", "py_test")
load("@cmk_requirements//:requirements.bzl", "requirement")

py_test(
    name = "dashboard",
    srcs = glob(["**/*.py"]),
    args = ["tests/unit/cmk/gui/dashboard"],
    env = {"EDITION": "community"},
    pytest_main = True,
    deps = [
        "//cmk/gui:config",
        "//cmk/gui:exceptions",
        "//cmk/gui:type_defs",
        "//cmk/gui:unit_formatter",
        "//cmk/gui/dashboard",
        "//cmk/gui/graphing",
        "//cmk/gui/openapi/framework",
        "//cmk/gui/token_auth",
        "//cmk/gui/utils:temperate_unit",
        "//cmk/gui/views:icon",
        "//tests/unit:conftest",
        "//tests/unit/cmk/gui:conftest",
        requirement("pytest"),
        requirement("pytest-mock"),
    ],
)
