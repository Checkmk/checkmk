load("@aspect_rules_py//py:defs.bzl", "py_test")
load("@cmk_requirements//:requirements.bzl", "requirement")

py_test(
    name = "ldap",
    srcs = glob(["**/*.py"]),
    args = ["tests/unit/cmk/gui/ldap"],
    env = {"EDITION": "community"},
    pytest_main = True,
    deps = [
        "//cmk/gui:config",
        "//cmk/gui:logged_in",
        "//cmk/gui:type_defs",
        "//cmk/gui:user_connection_config_types",
        "//cmk/gui/ldap_integration",
        "//cmk/gui/userdb",
        "//cmk/gui/utils:security_log_events",
        "//cmk/gui/watolib",
        "//packages/cmk-ccc:user",
        "//packages/cmk-crypto",
        "//tests/unit:conftest",
        "//tests/unit/cmk/gui:conftest",
        requirement("pytest"),
        requirement("pytest-mock"),
        requirement("python-ldap"),
    ],
)
