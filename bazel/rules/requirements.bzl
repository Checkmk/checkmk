load("@rules_uv//uv:pip.bzl", "RequirementsInInfo")

def _impl(ctx):
    content = []
    runfiles = []

    # Calculate the relative path from the output file to the workspace root.
    # The output file is declared in the current package, so we need to go up
    # one directory level for each path component in the package path.
    # For example, if package is "omd/non-free/relay", we need "../../../"
    package_depth = len(ctx.label.package.split("/")) if ctx.label.package else 0
    workspace_root_prefix = "../" * package_depth

    for req in ctx.files.requirements:
        # Use workspace_root_prefix + short_path to make paths relative to
        # the output file's location, which allows them to work when pip/uv
        # resolves -r directives relative to the input file's directory
        content.append("-r %s%s" % (workspace_root_prefix, req.short_path))
        runfiles.append(req)
    for constraint in ctx.files.constraints:
        content.append("-c %s%s" % (workspace_root_prefix, constraint.short_path))
        runfiles.append(constraint)
    requirements_txt = ctx.actions.declare_file(ctx.attr.name + ".txt")
    ctx.actions.write(requirements_txt, content = "\n".join(content + [""]))
    return [
        DefaultInfo(
            files = depset([requirements_txt]),
            runfiles = ctx.runfiles(files = runfiles),
        ),
        RequirementsInInfo(srcs = ctx.attr.requirements + ctx.attr.constraints),
    ]

compile_requirements_in = rule(
    implementation = _impl,
    attrs = {
        "constraints": attr.label_list(
            mandatory = False,
            allow_files = True,
            doc = "List of constraints.txt files.",
        ),
        "requirements": attr.label_list(
            mandatory = True,
            allow_files = True,
            doc = "List of requirements files to compile.",
        ),
    },
)
