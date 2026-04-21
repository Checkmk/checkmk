load("@aspect_rules_py//py:defs.bzl", "py_test")
load("@cmk_requirements//:requirements.bzl", "requirement")

py_test(
    name = "form_specs",
    srcs = glob(["**/*.py"]),
    args = ["tests/unit/cmk/gui/form_specs"],
    env = {"EDITION": "community"},
    pytest_main = True,
    deps = [
        "//cmk/gui:http",
        "//cmk/gui:session",
        "//cmk/gui/form_specs",
        "//cmk/gui/utils:encrypter",
        "//cmk/gui/utils:roles",
        "//packages/cmk-ccc:exceptions",
        "//packages/cmk-ccc:user",
        "//packages/cmk-plugin-apis:rulesets",
        "//packages/cmk-shared-typing:cmk_shared_typing_py",
        "//tests/unit:conftest",
        "//tests/unit/cmk/gui:conftest",
        requirement("pytest"),
        requirement("python-dateutil"),
        requirement("types-python-dateutil"),
        requirement("werkzeug"),
    ],
)
