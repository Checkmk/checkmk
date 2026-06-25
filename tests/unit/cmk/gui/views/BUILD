load("@cmk_requirements//:requirements.bzl", "requirement")
load("//bazel/rules:py_cmk_test.bzl", "py_cmk_test")

py_cmk_test(
    name = "views",
    srcs = glob(["**/*.py"]),
    args = [
        "tests/unit/cmk/gui/views",
    ],
    env = {"EDITION": "community"},
    use_project_pytest_config = True,
    deps = [
        "//cmk/gui:auth_core",
        "//cmk/gui:config",
        "//cmk/gui:core_toolkit",
        "//cmk/gui:general_pages",
        "//cmk/gui:html_toolkit",
        "//cmk/gui:page_toolkit",
        "//cmk/gui:painter_options",
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
        requirement("pytest-mock"),
    ],
)
