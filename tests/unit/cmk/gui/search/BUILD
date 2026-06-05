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
    name = "search",
    srcs = ["__test__.py"] + glob(["**/*.py"]),
    args = [
        "--config-file=$(location @//:pyproject.toml)",
        "--import-mode=importlib",
        "tests/unit/cmk/gui/search",
    ],
    data = ["@//:pyproject.toml"],
    env = {"EDITION": "community"},
    main = ":__test__.py",
    deps = [
        ":__test__",
        "//cmk/gui:config",
        "//cmk/gui:core_toolkit",
        "//cmk/gui:session_context",
        "//cmk/gui/background_job/process",
        "//cmk/gui/search",
        "//cmk/gui/utils:roles",
        "//tests/unit:conftest",
        "//tests/unit/cmk/gui:conftest",
        requirement("fakeredis"),
        requirement("polyfactory"),
        requirement("pytest-mock"),
        requirement("redis"),
        requirement("werkzeug"),
    ],
)
