load("@aspect_rules_py//py:defs.bzl", "py_pytest_main")
load("@cmk_requirements//:requirements.bzl", "requirement")
load("//bazel/rules:py_cmk_test.bzl", "py_cmk_test")

py_pytest_main(
    name = "__test__",
    deps = [
        requirement("coverage"),
        requirement("pytest"),
    ],
)

py_cmk_test(
    name = "watolib",
    srcs = ["__test__.py"] + glob(["**/*.py"]),
    args = [
        "tests/unit/cmk/gui/watolib",
    ],
    env = {"EDITION": "community"},
    main = ":__test__.py",
    use_project_pytest_config = True,
    deps = [
        ":__test__",
        "//cmk/gui:auth",
        "//cmk/gui:config",
        "//cmk/gui:core_toolkit",
        "//cmk/gui/background_job/job",
        "//cmk/gui/background_job/process",
        "//cmk/gui/form_specs",
        "//cmk/gui/userdb",
        "//cmk/gui/watolib",
        "//cmk/gui/watolib:config_infra",
        "//cmk/gui/watolib:registries",
        "//cmk/utils:redis",
        "//omd/packages/omd:omdlib",
        "//tests/unit:conftest",
        "//tests/unit/cmk/gui:conftest",
        requirement("flask"),
        requirement("pytest-mock"),
        requirement("responses"),
        requirement("time-machine"),
    ],
)
