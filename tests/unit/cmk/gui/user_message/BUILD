load("@aspect_rules_py//py:defs.bzl", "py_test")
load("@cmk_requirements//:requirements.bzl", "requirement")

py_test(
    name = "user_message",
    srcs = glob(["**/*.py"]),
    args = ["tests/unit/cmk/gui/user_message"],
    env = {"EDITION": "community"},
    pytest_main = True,
    deps = [
        "//tests:rest_api_client",
        "//tests/unit:conftest",
        "//tests/unit/cmk/gui:conftest",
        requirement("pytest"),
    ],
)
