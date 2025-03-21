load("@bazel_skylib//rules:common_settings.bzl", "BuildSettingInfo")

def _file_from_flag_impl(ctx):
    content = "\n".join(ctx.attr.content)
    for string, label in ctx.attr.replace_labels.items():
        content = content.replace("{%s}" % string, label[BuildSettingInfo].value)

    ctx.actions.write(
        output = ctx.outputs.out,
        content = content,
    )

file_from_flag = rule(
    doc = """Writes content to file and replaces strings with labels
        whilst using the python format string syntax with curly brackets.

        Args:
            name: Name of the rule.
            out: Path of the output file, relative to this package.
            content: List of strings written line for line.
            replace_labels: dict of strings to replace and labels containing flags.
        """,
    implementation = _file_from_flag_impl,
    attrs = {
        "out": attr.output(mandatory = True),
        "content": attr.string_list(mandatory = False, allow_empty = True),
        "replace_labels": attr.string_keyed_label_dict(mandatory = True),
    },
)
