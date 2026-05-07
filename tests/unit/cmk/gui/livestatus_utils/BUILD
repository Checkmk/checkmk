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
    name = "livestatus_utils",
    srcs = ["__test__.py"] + glob(["**/*.py"]),
    args = [
        "--import-mode=importlib",
        "tests/unit/cmk/gui/livestatus_utils",
    ],
    env = {"EDITION": "community"},
    main = ":__test__.py",
    deps = [
        ":__test__",
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
