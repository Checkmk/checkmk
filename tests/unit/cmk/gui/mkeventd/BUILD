load("@aspect_rules_py//py:defs.bzl", "py_test")
load("@cmk_requirements//:requirements.bzl", "requirement")

py_test(
    name = "mkeventd",
    srcs = glob(["**/*.py"]),
    args = ["tests/unit/cmk/gui/mkeventd"],
    env = {"EDITION": "community"},
    pytest_main = True,
    deps = [
        "//cmk/gui:type_defs",
        "//cmk/gui/mkeventd",
        "//cmk/gui/search",
        "//cmk/gui/utils:roles",
        "//cmk/gui/views:icon",
        "//packages/cmk-ec",
        "//tests/unit:conftest",
        "//tests/unit/cmk/gui:conftest",
        requirement("pytest"),
        requirement("time-machine"),
    ],
)
