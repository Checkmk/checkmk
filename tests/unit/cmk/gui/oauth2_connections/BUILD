load("@aspect_rules_py//py:defs.bzl", "py_test")
load("@cmk_requirements//:requirements.bzl", "requirement")

py_test(
    name = "oauth2_connections",
    srcs = glob(["**/*.py"]),
    args = ["tests/unit/cmk/gui/oauth2_connections"],
    env = {"EDITION": "community"},
    pytest_main = True,
    deps = [
        "//cmk/gui:session",
        "//cmk/gui/form_specs",
        "//cmk/gui/oauth2_connections",
        "//cmk/gui/utils:roles",
        "//packages/cmk-ccc:user",
        "//packages/cmk-shared-typing:cmk_shared_typing_py",
        "//tests/unit:conftest",
        "//tests/unit/cmk/gui:conftest",
        requirement("pytest"),
    ],
)
