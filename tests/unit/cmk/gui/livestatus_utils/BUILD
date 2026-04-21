load("@aspect_rules_py//py:defs.bzl", "py_test")
load("@cmk_requirements//:requirements.bzl", "requirement")

py_test(
    name = "livestatus_utils",
    srcs = glob(["**/*.py"]),
    args = ["tests/unit/cmk/gui/livestatus_utils"],
    env = {"EDITION": "community"},
    pytest_main = True,
    deps = [
        "//cmk/gui:config",
        "//cmk/gui:script_helpers",
        "//cmk/gui:session",
        "//cmk/gui:sites",
        "//cmk/gui/livestatus_utils/commands",
        "//packages/cmk-ccc:hostaddress",
        "//packages/cmk-ccc:site",
        "//packages/cmk-livestatus-client:livestatus-api",
        "//packages/cmk-livestatus-client:py_livestatus",
        "//tests/unit:conftest",
        "//tests/unit/cmk/gui:conftest",
        requirement("python-dateutil"),
        requirement("pytest"),
    ],
)
