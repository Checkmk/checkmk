load("@aspect_rules_py//py:defs.bzl", "py_pytest_main")
load("@cmk_requirements//:requirements.bzl", "requirement")
load("//bazel/rules:py_cmk_test.bzl", "py_cmk_test")

py_pytest_main(
    name = "__test__",
    deps = [
        requirement("coverage"),
        requirement("pytest"),
    ],
)

py_cmk_test(
    name = "livestatus_utils",
    srcs = ["__test__.py"] + glob(["**/*.py"]),
    args = [
        "tests/unit/cmk/gui/livestatus_utils",
    ],
    env = {"EDITION": "community"},
    main = ":__test__.py",
    use_project_pytest_config = True,
    deps = [
        ":__test__",
        "//cmk/gui:app",
        "//cmk/gui:config",
        "//cmk/gui:session_context",
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
