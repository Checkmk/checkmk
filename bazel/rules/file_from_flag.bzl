load("@bazel_skylib//rules:common_settings.bzl", "BuildSettingInfo")

def _file_from_flag_impl(ctx):
    if (ctx.attr.content) and not (ctx.file.src):
        template = ctx.actions.declare_file("template")
        content = "\n".join(ctx.attr.content)
        ctx.actions.write(
            output = template,
            content = content,
        )
    else:
        template = ctx.file.src

    replace_dict = {}
    for string, label in ctx.attr.replace_labels.items():
        replace_dict.update({"{%s}" % string: label[BuildSettingInfo].value})

    ctx.actions.expand_template(
        template = template,
        output = ctx.outputs.out,
        substitutions = replace_dict,
    )

file_from_flag = rule(
    doc = """Writes content to file and replaces strings with labels
        whilst using the python format string syntax with curly brackets.

        Args:
            name: Name of the rule.
            out: Path of the output file, relative to this package.
            content: List of strings written line for line.
            src: Source file to replace strings. Do not use with content
            replace_labels: dict of strings to replace and labels containing flags.
        """,
    implementation = _file_from_flag_impl,
    attrs = {
        "out": attr.output(mandatory = True),
        "content": attr.string_list(mandatory = False, allow_empty = True),
        "src": attr.label(mandatory = False, allow_single_file = True, providers = ["files"]),
        "replace_labels": attr.string_keyed_label_dict(mandatory = True),
    },
)
