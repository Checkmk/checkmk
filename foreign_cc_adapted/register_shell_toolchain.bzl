load("//foreign_cc_adapted/private/framework/toolchains:linux_commands.bzl", "commands")

def _shell_commands_impl(repository_ctx):
    """The implementation of `shell_commands`"""
    exec_compatible_with = [
        "@platforms//os:linux",
    ]
    file = ":linux_commands.bzl"
    return platform_common.ToolchainInfo(
		    commands = commands
    )

shell_commands = rule(
    doc = "Rule to rule our own shell commands",
    implementation = _shell_commands_impl
)
