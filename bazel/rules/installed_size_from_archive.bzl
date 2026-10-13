"""Rule to compute the Debian Installed-Size (in KiB) of a tar archive.

rules_pkg leaves this to the caller on purpose, see
https://github.com/bazelbuild/rules_pkg/pull/1068 and
https://github.com/bazelbuild/rules_pkg/pull/1083 (`installed_size_file`).
Upstream plans to have the tar builder emit the size and checksums as side
outputs instead, see https://github.com/bazelbuild/rules_pkg/issues/1080 and
https://github.com/bazelbuild/rules_pkg/issues/1057. Once a rules_pkg release
provides that, drop this rule and deb_installed_size.py, and possibly
md5sums_from_archive.bzl too.
"""

def _installed_size_from_archive_impl(ctx):
    ctx.actions.run(
        mnemonic = "DebInstalledSize",
        executable = ctx.executable._tool,
        arguments = [
            "--archive",
            ctx.file.src.path,
            "--out",
            ctx.outputs.out.path,
        ],
        inputs = [ctx.file.src],
        outputs = [ctx.outputs.out],
    )

installed_size_from_archive = rule(
    implementation = _installed_size_from_archive_impl,
    doc = """Writes the Installed-Size of the files in `src` for pkg_deb's `installed_size_file`.

    `src` should be the uncompressed package data tar: only its headers are
    read, so nothing has to be decompressed.""",
    attrs = {
        "out": attr.output(mandatory = True),
        "src": attr.label(allow_single_file = True, mandatory = True),
        "_tool": attr.label(
            default = "//bazel/rules:deb_installed_size",
            executable = True,
            cfg = "exec",
        ),
    },
)
