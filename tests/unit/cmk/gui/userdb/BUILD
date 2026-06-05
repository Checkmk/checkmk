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
    name = "userdb",
    srcs = ["__test__.py"] + glob(["**/*.py"]),
    args = [
        "--config-file=$(location @//:pyproject.toml)",
        "--import-mode=importlib",
        "tests/unit/cmk/gui/userdb",
    ],
    data = ["@//:pyproject.toml"],
    env = {"EDITION": "community"},
    main = ":__test__.py",
    deps = [
        ":__test__",
        "//cmk/gui:auth",
        "//cmk/gui:config",
        "//cmk/gui:core_toolkit",
        "//cmk/gui/ldap_integration",
        "//cmk/gui/userdb",
        "//cmk/gui/utils:htpasswd",
        "//cmk/gui/utils:roles",
        "//cmk/gui/valuespec",
        "//cmk/utils",
        "//packages/cmk-ccc:user",
        "//packages/cmk-ccc:version",
        "//packages/cmk-crypto",
        "//tests/unit:conftest",
        "//tests/unit/cmk/gui:conftest",
        requirement("pytest"),
    ],
)
