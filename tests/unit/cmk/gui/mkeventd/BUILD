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
    name = "mkeventd",
    srcs = ["__test__.py"] + glob(["**/*.py"]),
    args = [
        "tests/unit/cmk/gui/mkeventd",
    ],
    env = {"EDITION": "community"},
    main = ":__test__.py",
    use_project_pytest_config = True,
    deps = [
        ":__test__",
        "//cmk/gui:core_toolkit",
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
