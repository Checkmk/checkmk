load("@aspect_rules_py//py:defs.bzl", "py_test")
load("@cmk_requirements//:requirements.bzl", "requirement")

py_test(
    name = "sidebar",
    srcs = glob(["**/*.py"]),
    args = ["tests/unit/cmk/gui/sidebar"],
    env = {"EDITION": "community"},
    pytest_main = True,
    deps = [
        "//cmk/gui:config",
        "//cmk/gui:exceptions",
        "//cmk/gui:http",
        "//cmk/gui:logged_in",
        "//cmk/gui:pages",
        "//cmk/gui/search",
        "//cmk/gui/sidebar",
        "//cmk/gui/utils:labels",
        "//cmk/gui/utils:roles",
        "//tests/unit:conftest",
        "//tests/unit/cmk/gui:conftest",
        requirement("pytest"),
        requirement("pytest-mock"),
        requirement("werkzeug"),
    ],
)
