def _replace_string_in_file_impl(ctx):
    if (ctx.attr.content) and not (ctx.file.src):
        template = ctx.actions.declare_file("template")
        content = "\n".join(ctx.attr.content)
        ctx.actions.write(
            output = template,
            content = content,
        )
    else:
        template = ctx.file.src

    replace_dict = ctx.attr.replace_dict

    ctx.actions.expand_template(
        template = template,
        output = ctx.outputs.out,
        substitutions = replace_dict,
    )

replace_string_in_file = rule(
    doc = """Writes content to file and replaces strings
        whilst using the python format string syntax with curly brackets.

        Args:
            name: Name of the rule.
            out: Path of the output file, relative to this package.
            content: List of strings written line by line.
            src: Source file to replace strings. Do not use with content
            replace_dict: dict in the form {old_sting: new_sting}
        """,
    implementation = _replace_string_in_file_impl,
    attrs = {
        "out": attr.output(mandatory = True),
        "content": attr.string_list(mandatory = False, allow_empty = True),
        "src": attr.label(mandatory = False, allow_single_file = True, providers = ["files"]),
        "replace_dict": attr.string_dict(mandatory = True),
    },
)
