"""Generic platform-transitioning wrapper for an already-defined target."""

load(":private/xcomp/transition.bzl", "transition_platform", _HOST_PLATFORM = "HOST_PLATFORM")

def _platform_transitioned_target_impl(ctx):
    info = ctx.attr.target[DefaultInfo]
    original = info.files_to_run.executable

    # A rule declared executable=True must create its own executable file;
    # forwarding the dependency's executable directly is rejected by Bazel.
    # Keep the original basename so downstream packaging doesn't ship the
    # wrapper's own target name instead of the wrapped binary's name.
    executable = ctx.actions.declare_file(original.basename)
    ctx.actions.symlink(output = executable, target_file = original, is_executable = True)
    return [DefaultInfo(
        executable = executable,
        files = depset([executable]),
        runfiles = info.default_runfiles,
    )]

platform_transitioned_target = rule(
    implementation = _platform_transitioned_target_impl,
    cfg = transition_platform,
    executable = True,
    attrs = {
        "platform": attr.label(default = _HOST_PLATFORM),
        "target": attr.label(),
    },
)
