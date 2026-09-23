"""Run a tool from the workspace root with the Bazel-managed Go SDK on PATH.

Some generators -- ocb, for one -- shell out to `go`.  Pointing them at the
registered rules_go SDK rather than whatever happens to be installed keeps the
result independent of the machine, and lets them write into the source tree,
which a build action cannot do.

    go_run(
        name = "regenerate",
        tool = ":some_generator",
        arguments = ["--out", "some/package"],
    )

    bazel run //some/package:regenerate
"""

load("@bazel_skylib//lib:shell.bzl", "shell")

_LAUNCHER = """\
#!/usr/bin/env bash
set -eu -o pipefail

# bazel run starts us in the runfiles tree; remember it before leaving.
runfiles="${{PWD}}"
export PATH="$(cd "$(dirname "${{runfiles}}/{go}")" && pwd):${{PATH}}"
# The SDK is complete, so never let the toolchain fetch another one.
export GOTOOLCHAIN=local

cd "${{BUILD_WORKSPACE_DIRECTORY:?must be run via bazel run}}"
"${{runfiles}}/{tool}" {arguments} "$@"
{moves}{removes}"""

def _go_run_impl(ctx):
    sdk = ctx.toolchains["@rules_go//go:toolchain"].sdk

    launcher = ctx.actions.declare_file(ctx.label.name + ".bash")
    ctx.actions.write(
        output = launcher,
        is_executable = True,
        content = _LAUNCHER.format(
            go = sdk.go.short_path,
            tool = ctx.executable.tool.short_path,
            arguments = " ".join([shell.quote(a) for a in ctx.attr.arguments]),
            removes = "".join([
                "rm -f %s\n" % shell.quote(f)
                for f in ctx.attr.remove
            ]),
            moves = "".join([
                "mv -f %s %s\n" % (shell.quote(src), shell.quote(dst))
                for src, dst in ctx.attr.move.items()
            ]),
        ),
    )

    runfiles = ctx.runfiles(
        files = ctx.files.data + [sdk.go],
        transitive_files = depset(
            transitive = [sdk.srcs, sdk.libs, sdk.headers, sdk.tools],
        ),
    ).merge(ctx.attr.tool[DefaultInfo].default_runfiles)

    return [DefaultInfo(executable = launcher, runfiles = runfiles)]

go_run = rule(
    implementation = _go_run_impl,
    executable = True,
    doc = "Run `tool` from the workspace root with the rules_go SDK on PATH.",
    attrs = {
        "arguments": attr.string_list(
            doc = "Arguments passed to the tool, before any given on the command line.",
        ),
        "data": attr.label_list(
            allow_files = True,
            doc = "Files the tool needs at runtime.",
        ),
        "move": attr.string_dict(
            doc = ("Files to move after the tool ran, as {from: to} relative to the " +
                   "workspace root.  Some generators insist on writing everything to " +
                   "one output directory even when the outputs belong in different " +
                   "places."),
        ),
        "remove": attr.string_list(
            doc = ("Files to delete after the tool ran, relative to the workspace " +
                   "root.  For outputs a generator insists on writing but we do not " +
                   "want to keep."),
        ),
        "tool": attr.label(
            cfg = "target",
            executable = True,
            mandatory = True,
            doc = "The executable to run.",
        ),
    },
    toolchains = ["@rules_go//go:toolchain"],
)
