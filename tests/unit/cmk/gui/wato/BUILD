load("@aspect_rules_py//py:defs.bzl", "py_test")
load("@cmk_requirements//:requirements.bzl", "requirement")

py_test(
    name = "wato",
    srcs = glob(["**/*.py"]),
    args = ["tests/unit/cmk/gui/wato"],
    env = {"EDITION": "community"},
    pytest_main = True,
    deps = [
        "//cmk/gui:breadcrumb",
        "//cmk/gui:config",
        "//cmk/gui:exceptions",
        "//cmk/gui:http",
        "//cmk/gui:i18n",
        "//cmk/gui:permissions",
        "//cmk/gui:role_types",
        "//cmk/gui/plugins/wato",
        "//cmk/gui/valuespec",
        "//cmk/gui/wato",
        "//cmk/gui/wato:base",
        "//cmk/gui/watolib",
        "//cmk/gui/watolib:config_infra",
        "//cmk/gui/watolib:registries",
        "//tests/unit:conftest",
        "//tests/unit/cmk/gui:conftest",
        requirement("beautifulsoup4"),
        requirement("flask"),
        requirement("pytest"),
        requirement("pytest-mock"),
    ],
)
