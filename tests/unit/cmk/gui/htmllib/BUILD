load("@aspect_rules_py//py:defs.bzl", "py_test")
load("@cmk_requirements//:requirements.bzl", "requirement")

py_test(
    name = "htmllib",
    srcs = glob(["**/*.py"]),
    args = ["tests/unit/cmk/gui/htmllib"],
    env = {"EDITION": "community"},
    pytest_main = True,
    deps = [
        "//cmk/gui:exceptions",
        "//cmk/gui:http",
        "//cmk/gui:logged_in",
        "//cmk/gui/htmllib:foldable_container",
        "//cmk/gui/htmllib:generator",
        "//cmk/gui/htmllib:html",
        "//cmk/gui/htmllib:tag_rendering",
        "//cmk/gui/htmllib:type_defs",
        "//cmk/gui/utils:html",
        "//cmk/gui/utils:output_funnel",
        "//cmk/gui/utils:urls",
        "//cmk/gui/utils:user_errors",
        "//tests/unit:conftest",
        "//tests/unit/cmk/gui:compare_html",
        "//tests/unit/cmk/gui:conftest",
        requirement("pytest"),
        requirement("pytest-mock"),
        requirement("werkzeug"),
    ],
)
