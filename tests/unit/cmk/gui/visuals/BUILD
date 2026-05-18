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
    name = "visuals",
    srcs = ["__test__.py"] + glob(["**/*.py"]),
    args = [
        "--import-mode=importlib",
        "tests/unit/cmk/gui/visuals",
    ],
    env = {"EDITION": "community"},
    main = ":__test__.py",
    deps = [
        ":__test__",
        "//cmk/gui:core_toolkit",
        "//cmk/gui/bi",
        "//cmk/gui/utils:output_funnel",
        "//cmk/gui/visuals",
        "//cmk/gui/wato",
        "//cmk/utils",
        "//packages/cmk-ccc:site",
        "//packages/cmk-livestatus-client:livestatus-api",
        "//tests/unit:conftest",
        "//tests/unit/cmk/gui:conftest",
        requirement("pytest-mock"),
        requirement("time-machine"),
    ],
)
