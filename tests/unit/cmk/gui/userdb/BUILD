load("@aspect_rules_py//py:defs.bzl", "py_test")
load("@cmk_requirements//:requirements.bzl", "requirement")

py_test(
    name = "userdb",
    srcs = glob(["**/*.py"]),
    args = ["tests/unit/cmk/gui/userdb"],
    env = {"EDITION": "community"},
    pytest_main = True,
    deps = [
        "//cmk/gui:config",
        "//cmk/gui:exceptions",
        "//cmk/gui:http",
        "//cmk/gui:role_types",
        "//cmk/gui:session",
        "//cmk/gui:type_defs",
        "//cmk/gui:user_connection_config_types",
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
