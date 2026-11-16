load("//bazel/rules:py_cmk_test.bzl", "py_cmk_test")

py_cmk_test(
    name = "docker",
    size = "small",
    srcs = glob(["**/*.py"]),
    args = ["tests/integration/docker"],
    tags = [
        "deballast-keep=//packages/cmk-plugins/cmk/plugins/docker",  # agent sections are found at runtime by discover_all_plugins
    ],
    deps = [
        "//agents/plugins:agent-plugins-python",
        "//packages/cmk-plugin-apis:agent_based",
        "//packages/cmk-plugin-apis:discover_plugins",
        "//packages/cmk-plugins/cmk/plugins/docker",
    ],
)
