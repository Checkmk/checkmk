# Rules to fix binaries for deployment.
# For example setting the RPATH
load("@bazel_skylib//rules:common_settings.bzl", "BuildSettingInfo")

# Set RPATH for a whole directory with unknown file names
def _make_deployable_dir_impl(ctx):
    output_dir = ctx.actions.declare_directory(ctx.attr.input_dir)

    ctx.actions.run_shell(
        inputs = [ctx.file.src],
        outputs = [output_dir],
        command = """
            mkdir -p {output_path}
            cp -r -L {src_path}/{input_dir}/* {output_path}

            chmod u+w -R {output_path}

            file -L {output_path}/* \\
                | grep ELF | cut -d ':' -f1 \\
                | xargs patchelf --force-rpath --set-rpath "{rpath}"

        """.format(output_path = output_dir.path, src_path = ctx.file.src.path, input_dir = ctx.attr.input_dir, rpath = ctx.attr.rpath),
    )

    return [DefaultInfo(files = depset([output_dir]))]

make_deployable_dir = rule(
    implementation = _make_deployable_dir_impl,
    attrs = {
        "src": attr.label(allow_single_file = True, providers = ["files"], mandatory = True),  # gendir input
        "input_dir": attr.string(mandatory = True),
        "rpath": attr.string(mandatory = True),
    },
)

# Set RPATH for a whole directory with known file names
def _make_deployable_file_impl(ctx):
    out_file = ctx.actions.declare_file(ctx.attr.out)

    ctx.actions.run_shell(
        inputs = [ctx.file.src],
        outputs = [out_file],
        command = """
            if [ -d {input_path} ]; then
                INPUT_FILE_PATH="{input_path}/{filename}"
            else
                INPUT_FILE_PATH="{input_path}"
                # assert: filename must be suffix of input_path
            fi
            cp -r -L $INPUT_FILE_PATH {file_dir}
            chmod u+w -R {file_dir}
            file -L  {file_dir} \\
                | grep ELF | cut -d ':' -f1 \\
                | xargs patchelf --force-rpath --set-rpath "{rpath}"
        """.format(input_path = ctx.file.src.path, filename = ctx.attr.out, file_dir = out_file.path, rpath = ctx.attr.rpath),
    )

    return [DefaultInfo(files = depset([out_file]))]

make_deployable_file = rule(
    implementation = _make_deployable_file_impl,
    attrs = {
        "src": attr.label(allow_single_file = True, providers = ["files"], mandatory = True),  # gendir input
        "out": attr.string(mandatory = True),
        "rpath": attr.string(mandatory = True),
    },
)

def _string_replace_impl(ctx):
    output_dir = ctx.actions.declare_directory(ctx.label.name)
    value = ctx.attr.value
    for string, label in ctx.attr.replace_labels.items():
        value = value.replace("{%s}" % string, label[BuildSettingInfo].value)

    ctx.actions.run_shell(
        inputs = [ctx.file.src],
        outputs = [output_dir],
        command = """
        cp -a --dereference {src_path} {dst_path}
        find {dst_path} -type f {filepattern} -exec sed -i 's|{replace_pattern}|{value}|' {{}} \\;
        """.format(
            src_path = ctx.file.src.path,
            dst_path = output_dir.path,
            filepattern = "".join(["-iname %s " % pattern for pattern in ctx.attr.filepattern]),
            replace_pattern = ctx.attr.replace_pattern,
            value = value,
        ),
    )

    return [DefaultInfo(files = depset([output_dir]))]

string_replace = rule(
    implementation = _string_replace_impl,
    attrs = {
        "src": attr.label(allow_single_file = True, providers = ["files"], mandatory = True),
        "filepattern": attr.string_list(),
        "replace_pattern": attr.string(),
        "value": attr.string(),
        "replace_labels": attr.string_keyed_label_dict(mandatory = True),
    },
)
