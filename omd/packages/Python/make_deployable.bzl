def _make_deployable_impl(ctx):
    # Define the output directory where the tar file will be unpacked
    output_dir = ctx.actions.declare_directory(ctx.attr.input_dir)

    ctx.actions.run_shell(
        inputs = [ctx.file.src],
        outputs = [output_dir],
        command = """
            mkdir -p %s
            cp -r -L %s/%s/* %s
     
            chmod u+w -R %s
     
            file -L %s/* \\
                | grep ELF | cut -d ':' -f1 \\
                | xargs patchelf --force-rpath --set-rpath "%s"

        """ % (output_dir.path, ctx.file.src.path, ctx.attr.input_dir, output_dir.path, output_dir.path, output_dir.path, ctx.attr.rpath),
    )

    # Return the directory as the output
    return [DefaultInfo(files = depset([output_dir]))]

# Rule definition
make_deployable = rule(
    implementation = _make_deployable_impl,
    attrs = {
        "src": attr.label(allow_single_file = True, providers = ["files"], mandatory = True),  # gendir input
        "input_dir": attr.string(mandatory = True),
        "rpath": attr.string(mandatory = True),
    },
)
