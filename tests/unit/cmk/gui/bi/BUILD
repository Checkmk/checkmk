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
    name = "bi",
    srcs = ["__test__.py"] + glob(["**/*.py"]),
    args = [
        "--import-mode=importlib",
        "tests/unit/cmk/gui/bi",
    ],
    env = {"EDITION": "community"},
    main = ":__test__.py",
    deps = [
        ":__test__",
        "//cmk/bi",
        "//cmk/gui:core_toolkit",
        "//cmk/gui/bi",
        "//packages/cmk-ccc:hostaddress",
        "//tests/unit:conftest",
        "//tests/unit/cmk/gui:conftest",
        requirement("pytest"),
    ],
)
