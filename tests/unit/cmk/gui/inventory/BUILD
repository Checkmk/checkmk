load("@aspect_rules_py//py:defs.bzl", "py_test")
load("@cmk_requirements//:requirements.bzl", "requirement")

py_test(
    name = "inventory",
    srcs = glob(["**/*.py"]),
    args = ["tests/unit/cmk/gui/inventory"],
    env = {"EDITION": "community"},
    pytest_main = True,
    deps = [
        "//cmk/gui:config",
        "//cmk/gui:http",
        "//cmk/gui:type_defs",
        "//cmk/gui/inventory",
        "//cmk/gui/watolib:groups_io",
        "//cmk/inventory",
        "//cmk/utils",
        "//packages/cmk-ccc:exceptions",
        "//packages/cmk-ccc:hostaddress",
        "//packages/cmk-ccc:store",
        "//packages/cmk-livestatus-client:livestatus-api",
        "//tests/unit:conftest",
        "//tests/unit/cmk/gui:conftest",
        requirement("pytest"),
    ],
)
