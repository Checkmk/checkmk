"""Transition rules

Adapted from
  * https://github.com/bazelbuild/rules_rust/tree/main/examples/musl_cross_compiling
  * https://github.com/ouillie/bazel-rust-musl

"""

def _transition_platform_impl(_, attr):
    settings = {"//command_line_option:platforms": str(attr.platform)}
    if attr.compilation_mode:
        settings["//command_line_option:compilation_mode"] = attr.compilation_mode
    return settings

_transition_platform = transition(
    implementation = _transition_platform_impl,
    inputs = [],
    outputs = [
        "//command_line_option:platforms",
        "//command_line_option:compilation_mode",
    ],
)

def _platform_transition_binary_impl(ctx):
    default_info = ctx.attr.binary[0][DefaultInfo]
    executable = ctx.executable.binary
    output = ctx.actions.declare_file("{}.{}".format(ctx.label.name, executable.extension).rstrip("."))

    ctx.actions.symlink(
        output = output,
        target_file = default_info.files_to_run.executable,
        is_executable = True,
    )

    files = depset([output])
    runfiles = ctx.runfiles([output, executable]).merge(default_info.default_runfiles)
    return [DefaultInfo(
        files = files,
        runfiles = runfiles,
        executable = output,
    )]

platform_transition_binary = rule(
    doc = """Transitions a target to the provided platform.

    Example:
      For musl, this allows us to change the toolchain from the default
      toolchain resolved for `cpu:x86_64, os:linux` to a different toolchain
      with other constraints such as `cpu:x86_64, os:linux, linker:musl`.

    See Also:
      https://bazel.build/rules/lib/builtins/transition.html

    """,
    implementation = _platform_transition_binary_impl,
    attrs = {
        "binary": attr.label(
            doc = "The target to transition",
            allow_single_file = True,
            cfg = _transition_platform,
            executable = True,
        ),
        "platform": attr.label(
            doc = "The platform to transition to.",
            mandatory = True,
        ),
        "compilation_mode": attr.string(
            doc = "Optional compilation mode (e.g., 'opt', 'dbg', 'fastbuild'). If not set, uses the default from command line.",
            default = "",
        ),
        "_allowlist_function_transition": attr.label(
            default = "@bazel_tools//tools/allowlists/function_transition_allowlist",
        ),
    },
    executable = True,
)
