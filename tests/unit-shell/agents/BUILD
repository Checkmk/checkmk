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
    name = "test_mk_tsm",
    src = "plugins/test_mk_tsm.sh",
    deps = ["//packages/cmk-plugins/cmk/plugins/tsm:agents_sh"],
)

shunit2_test(
    name = "test_mk_redis",
    src = "plugins/test_mk_redis.sh",
    env = {
        "UNIT_SH_AGENTS_DIR": "${UNIT_SH_REPO_PATH}/agents",
        "UNIT_SH_PLUGINS_DIR": "${UNIT_SH_REPO_PATH}/agents/plugins",
    },
    deps = ["//agents/plugins:agents_plugins_sh"],
)

# Lets shellcheck see these scripts. Nothing depends on this target.
sh_library(
    name = "shell_scripts",
    srcs = [
        "plugins/test_common_inventory_parts.sh",
        "plugins/test_common_plugin_parts.sh",
        "plugins/test_mk_oracle.sh",
        "plugins/test_mk_sap_hana.sh",
        "test_bourne_again_shell.sh",
        "test_bourne_shell.sh",
        "test_common_agent_parts.sh",
        "test_common_mk-job_parts.sh",
        "test_current_shell.sh",
        "test_korn_shell.sh",
        "test_korn_shell_93.sh",
        "test_manage_binaries.sh",
        "test_z_shell.sh",
    ],
)
