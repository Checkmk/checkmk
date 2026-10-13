load("//bazel/rules:py_cmk_test.bzl", "py_cmk_test")

py_cmk_test(
    name = "agent_commands",
    size = "small",
    srcs = ["test_agent_commands.py"],
    use_project_pytest_config = True,
    visibility = ["//visibility:private"],
    deps = [
        "//cmk/gui:agent",
        "//packages/cmk-ccc:hostaddress",
        "//packages/cmk-shared-typing:cmk_shared_typing_py",
        "//tests/testlib/common",
    ],
)
