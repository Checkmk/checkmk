load("@aspect_rules_py//py:defs.bzl", "py_test")
load("@cmk_requirements//:requirements.bzl", "requirement")

py_test(
    name = "visuals",
    srcs = glob(["**/*.py"]),
    args = ["tests/unit/cmk/gui/visuals"],
    env = {"EDITION": "community"},
    pytest_main = True,
    deps = [
        "//cmk/gui:type_defs",
        "//cmk/gui/bi",
        "//cmk/gui/utils:output_funnel",
        "//cmk/gui/visuals",
        "//cmk/gui/wato",
        "//cmk/utils",
        "//packages/cmk-ccc:site",
        "//packages/cmk-livestatus-client:livestatus-api",
        "//tests/unit:conftest",
        "//tests/unit/cmk/gui:conftest",
        requirement("pytest"),
        requirement("pytest-mock"),
        requirement("time-machine"),
    ],
)
