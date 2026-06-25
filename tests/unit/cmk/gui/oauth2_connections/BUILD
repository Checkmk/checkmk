load("//bazel/rules:py_cmk_test.bzl", "py_cmk_test")

py_cmk_test(
    name = "oauth2_connections",
    srcs = glob(["**/*.py"]),
    args = [
        "tests/unit/cmk/gui/oauth2_connections",
    ],
    env = {"EDITION": "community"},
    use_project_pytest_config = True,
    deps = [
        "//cmk/gui:session_context",
        "//cmk/gui/form_specs",
        "//cmk/gui/oauth2_connections",
        "//cmk/gui/utils:roles",
        "//packages/cmk-ccc:user",
        "//packages/cmk-shared-typing:cmk_shared_typing_py",
        "//tests/unit:conftest",
        "//tests/unit/cmk/gui:conftest",
    ],
)
