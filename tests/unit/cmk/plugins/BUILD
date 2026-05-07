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
    name = "plugins",
    srcs = ["__test__.py"] + glob(["**/*.py"]),
    args = [
        "--config-file=$(location @//:pyproject.toml)",
        "--import-mode=importlib",
        "--random-order-bucket=global",
    ],
    data = ["@//:pyproject.toml"] + glob(
        include = [
            "**/_check_form_submit_response",
            "**/*.json",
            "**/*.yaml",
        ],
    ),
    env = {"EDITION": "community"},
    main = ":__test__.py",
    visibility = ["//visibility:private"],
    deps = [
        ":__test__",
        "//cmk/legacy_checks",
        "//cmk/plugins",
        "//packages/cmk-plugins:azure_deprecated",
        "//tests/testlib/common:repo",
        "//tests/testlib/unit",
        requirement("exchangelib"),
        requirement("feedparser"),
        requirement("polyfactory"),
        requirement("pysmb"),
        requirement("pytest"),
        requirement("pytest-mock"),
        requirement("pytest-asyncio"),
        requirement("pytest-random-order"),
        requirement("python-snap7"),
        requirement("requests"),
        requirement("responses"),
        requirement("time-machine"),
        requirement("vcrpy"),
    ],
)
