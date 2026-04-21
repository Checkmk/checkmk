load("@aspect_rules_py//py:defs.bzl", "py_test")
load("@cmk_requirements//:requirements.bzl", "requirement")

py_test(
    name = "auth_token",
    srcs = glob(["**/*.py"]),
    args = ["tests/unit/cmk/gui/auth_token"],
    pytest_main = True,
    deps = [
        "//cmk/gui/token_auth",
        "//packages/cmk-ccc:user",
        requirement("pytest"),
        requirement("python-dateutil"),
    ],
)
