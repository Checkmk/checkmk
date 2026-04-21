load("@aspect_rules_py//py:defs.bzl", "py_test")
load("@cmk_requirements//:requirements.bzl", "requirement")

py_test(
    name = "quick_setup",
    srcs = glob(["**/*.py"]),
    args = ["tests/unit/cmk/gui/quick_setup"],
    env = {"EDITION": "community"},
    pytest_main = True,
    deps = [
        "//cmk/gui/form_specs",
        "//cmk/gui/quick_setup",
        "//cmk/plugins",
        "//cmk/server_side_calls_backend",
        "//cmk/utils",
        "//packages/cmk-ccc:user",
        "//packages/cmk-ccc:version",
        "//packages/cmk-plugin-apis:password_store",
        "//packages/cmk-plugin-apis:rulesets",
        "//packages/cmk-plugin-apis:server_side_calls",
        "//tests/unit:conftest",
        "//tests/unit/cmk/gui:conftest",
        requirement("polyfactory"),
        requirement("pytest"),
        requirement("pytest-mock"),
    ],
)
