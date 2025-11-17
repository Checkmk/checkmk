def _snmp_compile_mibs_impl(ctx):
    output_dir = ctx.actions.declare_directory("share")
    args = [output_dir.path + "/snmp/compiled_mibs"]

    for src_file in ctx.files.mibs:
        args.append(src_file.path)

    ctx.actions.run(
        executable = ctx.executable.compiler,
        inputs = ctx.files.mibs,
        outputs = [output_dir],
        arguments = args,
        progress_message = "Processing MIBs",
    )

    return [DefaultInfo(files = depset([output_dir]))]

snmp_compile_mibs = rule(
    implementation = _snmp_compile_mibs_impl,
    attrs = {
        "mibs": attr.label_list(
            mandatory = True,
            allow_files = True,
            doc = "The list of MIB files to compile.",
        ),
        "compiler": attr.label(
            executable = True,
            mandatory = True,
            cfg = "exec",
        ),
    },
    provides = [DefaultInfo],
)
