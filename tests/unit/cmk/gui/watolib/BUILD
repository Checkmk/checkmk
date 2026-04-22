load("@aspect_rules_py//py:defs.bzl", "py_test")
load("@cmk_requirements//:requirements.bzl", "requirement")

py_test(
    name = "watolib",
    srcs = glob(["**/*.py"]),
    args = ["tests/unit/cmk/gui/watolib"],
    env = {"EDITION": "community"},
    pytest_main = True,
    deps = [
        "//cmk/gui:config",
        "//cmk/gui:ctx_stack",
        "//cmk/gui:exceptions",
        "//cmk/gui:http",
        "//cmk/gui:logged_in",
        "//cmk/gui:login",
        "//cmk/gui/background_job/job",
        "//cmk/gui/form_specs",
        "//cmk/gui/userdb",
        "//cmk/gui/watolib",
        "//cmk/gui/watolib:config_infra",
        "//cmk/gui/watolib:registries",
        "//omd/packages/omd:omdlib",
        "//tests/unit:conftest",
        "//tests/unit/cmk/gui:conftest",
        requirement("flask"),
        requirement("pytest"),
        requirement("pytest-mock"),
        requirement("responses"),
        requirement("time-machine"),
    ],
)
