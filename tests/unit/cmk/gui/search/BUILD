load("@aspect_rules_py//py:defs.bzl", "py_test")
load("@cmk_requirements//:requirements.bzl", "requirement")

py_test(
    name = "search",
    srcs = glob(["**/*.py"]),
    args = ["tests/unit/cmk/gui/search"],
    env = {"EDITION": "community"},
    pytest_main = True,
    deps = [
        "//cmk/gui:config",
        "//cmk/gui:http",
        "//cmk/gui:i18n",
        "//cmk/gui:logged_in",
        "//cmk/gui:session",
        "//cmk/gui:type_defs",
        "//cmk/gui/search",
        "//cmk/gui/utils:roles",
        "//cmk/gui/watolib:config_infra",
        "//tests/unit:conftest",
        "//tests/unit/cmk/gui:conftest",
        requirement("fakeredis"),
        requirement("polyfactory"),
        requirement("pytest"),
        requirement("pytest-mock"),
        requirement("redis"),
        requirement("werkzeug"),
    ],
)
