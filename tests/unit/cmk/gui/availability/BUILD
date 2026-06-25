load("@cmk_requirements//:requirements.bzl", "requirement")
load("//bazel/rules:py_cmk_test.bzl", "py_cmk_test")

py_cmk_test(
    name = "availability",
    srcs = glob(["**/*.py"]),
    args = [
        "tests/unit/cmk/gui/availability",
    ],
    env = {"EDITION": "community"},
    use_project_pytest_config = True,
    deps = [
        "//cmk/gui/availability",
        "//tests/unit:conftest",
        "//tests/unit/cmk/gui:conftest",
        requirement("fido2"),
        requirement("marshmallow"),
        requirement("opentelemetry-sdk"),
        requirement("python-ldap"),
    ],
)
