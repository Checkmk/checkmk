load("@cmk_requirements//:requirements.bzl", "requirement")
load("//bazel/rules:py_cmk_test.bzl", "py_cmk_test")

py_cmk_test(
    name = "form_specs",
    srcs = glob(["**/*.py"]),
    args = [
        "tests/unit/cmk/gui/form_specs",
    ],
    env = {"EDITION": "community"},
    use_project_pytest_config = True,
    deps = [
        "//cmk/gui:core_toolkit",
        "//cmk/gui:session_context",
        "//cmk/gui/form_specs",
        "//cmk/gui/utils:encrypter",
        "//cmk/gui/utils:roles",
        "//packages/cmk-ccc:exceptions",
        "//packages/cmk-ccc:user",
        "//packages/cmk-plugin-apis:rulesets",
        "//packages/cmk-shared-typing:cmk_shared_typing_py",
        "//tests/unit:conftest",
        "//tests/unit/cmk/gui:conftest",
        requirement("python-dateutil"),
        requirement("types-python-dateutil"),
        requirement("werkzeug"),
    ],
)
