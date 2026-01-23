load("@bazel_skylib//rules:common_settings.bzl", "BuildSettingInfo")

def _filename_from_flag_impl(ctx):
    replacements = {}
    for key, label in ctx.attr.replacements.items():
        replacements[key] = label[BuildSettingInfo].value

    filename = ctx.attr.file_name.format(**replacements)

    output_file = ctx.actions.declare_file(filename)
    ctx.actions.symlink(
        output = output_file,
        target_file = ctx.file.src,
    )

    return [DefaultInfo(files = depset([output_file]))]

filename_from_flag = rule(
    doc = """Copies a source file to an output file with a name based on build settings.

        The output filename can use placeholders (e.g., {version}, {edition}) which will
        be replaced with values from the corresponding build settings.

        Example:
            filename_from_flag(
                name = "versioned_file",
                src = "my_file.txt",
                file_name = "{version}-{edition}.txt",
                replacements = {
                    "version": "//:cmk_version",
                    "edition": "//:cmk_edition",
                },
            )

        Args:
            name: Name of the rule.
            src: Source file to copy.
            file_name: Output filename pattern. Use {key} placeholders for replacement.
            replacements: Dictionary mapping placeholder names to build setting labels.
        """,
    implementation = _filename_from_flag_impl,
    attrs = {
        "src": attr.label(allow_single_file = True, mandatory = True),
        "file_name": attr.string(mandatory = True),
        "replacements": attr.string_keyed_label_dict(mandatory = True),
    },
)
