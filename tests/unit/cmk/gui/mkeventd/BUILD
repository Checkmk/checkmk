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
    name = "mkeventd",
    srcs = ["__test__.py"] + glob(["**/*.py"]),
    args = [
        "--config-file=$(location @//:pyproject.toml)",
        "tests/unit/cmk/gui/mkeventd",
    ],
    data = ["@//:pyproject.toml"],
    env = {"EDITION": "community"},
    main = ":__test__.py",
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
