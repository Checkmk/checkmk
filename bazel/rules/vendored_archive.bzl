"""Repository rule for archives vendored inside this repository.

The Windows agent's third-party dependencies are checked in as tarballs
under //third_party (the vcxproj build unpacks them into agents/wnx/extlibs
via `make install_extlibs`). This rule makes the same tarballs available as
external repositories for the Bazel build, with a build file supplied by
the caller — the Bazel analog of http_archive for in-tree archives.
"""

def _vendored_archive_impl(ctx):
    ctx.extract(
        archive = ctx.attr.src,
        stripPrefix = ctx.attr.strip_prefix,
    )
    ctx.file("BUILD.bazel", ctx.read(ctx.attr.build_file))

vendored_archive = repository_rule(
    implementation = _vendored_archive_impl,
    attrs = {
        "build_file": attr.label(
            allow_single_file = True,
            mandatory = True,
            doc = "File to use as the BUILD file for this repository.",
        ),
        "src": attr.label(
            allow_single_file = True,
            mandatory = True,
            doc = "In-repository archive to extract.",
        ),
        "strip_prefix": attr.string(
            doc = "Directory prefix to strip from the extracted files.",
        ),
    },
)
