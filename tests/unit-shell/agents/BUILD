load("//bazel/rules:shunit2.bzl", "shunit2_test")

[
    shunit2_test(
        name = src.replace(".sh", ""),
        src = src,
        env = {
            "UNIT_SH_AGENTS_DIR": "${UNIT_SH_REPO_PATH}/agents",
            "UNIT_SH_PLUGINS_DIR": "${UNIT_SH_REPO_PATH}/agents/plugins",
        },
        deps = ["//agents:agents_sh"],
    )
    for src in glob(["test_*.sh"])
]

shunit2_test(
    name = "test_mk_redis",
    src = "plugins/test_mk_redis.sh",
    env = {
        "UNIT_SH_AGENTS_DIR": "${UNIT_SH_REPO_PATH}/agents",
        "UNIT_SH_PLUGINS_DIR": "${UNIT_SH_REPO_PATH}/agents/plugins",
    },
    deps = ["//agents/plugins:agents_plugins_sh"],
)
