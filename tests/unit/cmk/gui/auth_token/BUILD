load("@cmk_requirements//:requirements.bzl", "requirement")
load("//bazel/rules:py_cmk_test.bzl", "py_cmk_test")

py_cmk_test(
    name = "auth_token",
    srcs = glob(["**/*.py"]),
    args = ["tests/unit/cmk/gui/auth_token"],
    use_project_pytest_config = True,
    deps = [
        "//cmk/gui/token_auth",
        "//packages/cmk-ccc:user",
        requirement("python-dateutil"),
    ],
)
