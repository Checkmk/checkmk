load("@aspect_rules_py//py:defs.bzl", "py_library", "py_pytest_main", "py_test")
load("@cmk_requirements//:requirements.bzl", "requirement")

py_library(
    name = "conftest",
    testonly = True,
    srcs = ["conftest.py"],
    visibility = [":__subpackages__"],
    deps = [
        "//cmk/plugins",
        "//tests/testlib/unit",
        requirement("flask"),
        requirement("pytest"),
        requirement("pytest-mock"),
    ],
)

py_pytest_main(
    name = "__test__",
    deps = [
        requirement("pytest"),
    ],
)

py_test(
    name = "update_config",
    srcs = ["__test__.py"] + glob(
        include = ["**/*.py"],
        exclude = ["**/conftest.py"],
    ),
    args = [
        "--config-file=$(location @//:pyproject.toml)",
        "--import-mode=importlib",
        "--random-order-bucket=global",
    ],
    data = ["@//:pyproject.toml"],
    env = {"EDITION": "community"},
    main = ":__test__.py",
    visibility = ["//visibility:private"],
    deps = [
        ":__test__",
        ":conftest",
        "//cmk/gui/plugins/wato/check_parameters",
        "//cmk/update_config",
        "//cmk/utils:werks",
        "//tests/unit:conftest",
        requirement("flask"),
        requirement("pytest"),
        requirement("pytest-asyncio"),
        requirement("pytest-random-order"),
        requirement("pytest-mock"),
    ],
)
