load("@rules_uv//uv:pip.bzl", "RequirementsInInfo")

def _impl(ctx):
    content = []
    runfiles = []
    for req in ctx.files.requirements:
        content.append("-r %s" % req.short_path)
        runfiles.append(req)
    for constraint in ctx.files.constraints:
        content.append("-c %s" % constraint.short_path)
        runfiles.append(constraint)
    out = ctx.actions.declare_file(ctx.attr.name + "-requirements.in")
    ctx.actions.write(out, content = "\n".join(content + [""]))
    return [
        DefaultInfo(
            files = depset([out]),
            runfiles = ctx.runfiles(files = runfiles),
        ),
        RequirementsInInfo(srcs = ctx.attr.requirements + ctx.attr.constraints),
    ]

compile_requirements_in = rule(
    implementation = _impl,
    attrs = {
        "requirements": attr.label_list(
            mandatory = True,
            allow_files = True,
            doc = "List of requirements files to compile.",
        ),
        "constraints": attr.label_list(
            mandatory = False,
            allow_files = True,
            doc = "List of constraints.txt files.",
        ),
    },
)
