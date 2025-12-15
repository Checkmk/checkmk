def _git_hash_file_impl(ctx):
    ctx.actions.run_shell(
        inputs = [ctx.version_file, ctx.info_file],
        outputs = [ctx.outputs.out],
        command = """
set -e
awk '/^STABLE_GIT_COMMIT /{{print $2}}' "{infile}" > "{outfile}"
""".format(
            infile = ctx.info_file.path,
            outfile = ctx.outputs.out.path,
        ),
    )

git_hash_file = rule(
    doc = """
        Write git hash to hash file
        """,
    implementation = _git_hash_file_impl,
    attrs = {
        "out": attr.output(mandatory = True),
    },
)
