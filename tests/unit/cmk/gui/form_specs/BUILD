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
    name = "form_specs",
    srcs = ["__test__.py"] + glob(["**/*.py"]),
    args = [
        "--config-file=$(location @//:pyproject.toml)",
        "tests/unit/cmk/gui/form_specs",
    ],
    data = ["@//:pyproject.toml"],
    env = {"EDITION": "community"},
    main = ":__test__.py",
    deps = [
        ":__test__",
        "//cmk/gui:core_toolkit",
        "//cmk/gui:session_context",
        "//cmk/gui/form_specs",
        "//cmk/gui/utils:encrypter",
        "//cmk/gui/utils:roles",
        "//packages/cmk-ccc:exceptions",
        "//packages/cmk-ccc:user",
        "//packages/cmk-plugin-apis:rulesets",
        "//packages/cmk-shared-typing:cmk_shared_typing_py",
        "//tests/unit:conftest",
        "//tests/unit/cmk/gui:conftest",
        requirement("pytest"),
        requirement("python-dateutil"),
        requirement("types-python-dateutil"),
        requirement("werkzeug"),
    ],
)
