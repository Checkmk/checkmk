load(":register_shell_toolchain.bzl", "shell_commands")

shell_commands(name = "shell_cmd")

toolchain(
    name = "shell_toolchain",
    toolchain_type = "@rules_foreign_cc//foreign_cc/private/framework:shell_toolchain",
    toolchain = ":shell_cmd",
)
