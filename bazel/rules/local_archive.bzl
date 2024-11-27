# https://www.stevenengelhardt.com/2023/03/01/practical-bazel-local_archive-workspace-rule/

def _impl(repository_ctx):
    repository_ctx.extract(
        archive = repository_ctx.attr.src,
        stripPrefix = repository_ctx.attr.strip_prefix,
    )
    repository_ctx.file(
        "BUILD.bazel",
        repository_ctx.read(repository_ctx.attr.build_file),
    )

local_archive = repository_rule(
    implementation = _impl,
    attrs = {
        "src": attr.label(mandatory = True, allow_single_file = True),
        "build_file": attr.label(mandatory = True, allow_single_file = True),
        "sha256": attr.string(),
        "strip_prefix": attr.string(),
    },
)
