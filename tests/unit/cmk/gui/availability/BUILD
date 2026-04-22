load("@aspect_rules_py//py:defs.bzl", "py_test")
load("@cmk_requirements//:requirements.bzl", "requirement")

py_test(
    name = "availability",
    srcs = glob(["**/*.py"]),
    args = ["tests/unit/cmk/gui/availability"],
    env = {"EDITION": "community"},
    pytest_main = True,
    deps = [
        "//cmk/gui/availability",
        "//tests/unit:conftest",
        "//tests/unit/cmk/gui:conftest",
        requirement("fido2"),
        requirement("marshmallow"),
        requirement("opentelemetry-sdk"),
        requirement("pytest"),
        requirement("python-ldap"),
    ],
)
