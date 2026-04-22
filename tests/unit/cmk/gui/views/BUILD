load("@aspect_rules_py//py:defs.bzl", "py_test")
load("@cmk_requirements//:requirements.bzl", "requirement")

py_test(
    name = "views",
    srcs = glob(["**/*.py"]),
    args = ["tests/unit/cmk/gui/views"],
    env = {"EDITION": "community"},
    pytest_main = True,
    deps = [
        "//cmk/gui:config",
        "//cmk/gui:display_options",
        "//cmk/gui:exporter",
        "//cmk/gui:http",
        "//cmk/gui:logged_in",
        "//cmk/gui:num_split",
        "//cmk/gui:painter_options",
        "//cmk/gui:theme",
        "//cmk/gui:type_defs",
        "//cmk/gui/data_source",
        "//cmk/gui/inventory",
        "//cmk/gui/painter:v0_base",
        "//cmk/gui/plugins/views",
        "//cmk/gui/utils:html",
        "//cmk/gui/views",
        "//cmk/gui/visuals",
        "//tests/unit:conftest",
        "//tests/unit/cmk/gui:conftest",
        requirement("flask"),
        requirement("pytest"),
        requirement("pytest-mock"),
    ],
)
