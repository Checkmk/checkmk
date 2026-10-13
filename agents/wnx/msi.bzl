"""Rule building the Windows agent MSI on Linux."""

def _wnx_msi_impl(ctx):
    args = ctx.actions.args()
    args.add(ctx.outputs.out)
    args.add(ctx.file._candle)
    args.add(ctx.file._light)
    args.add(ctx.file.service_exe)
    args.add(ctx.file.agent_ctl_exe)
    args.add(ctx.file._wine_mono)
    args.add(ctx.file._wine_bin)
    args.add(ctx.file.version_file)
    args.add(ctx.executable._msibuild)

    lib_dirs = []
    for lib in ctx.files._msi_libs:
        if ".so" in lib.basename and lib.dirname not in lib_dirs:
            lib_dirs.append(lib.dirname)
    args.add_all(lib_dirs)

    ctx.actions.run(
        outputs = [ctx.outputs.out],
        inputs = depset(
            ctx.files.srcs + ctx.files._wix + ctx.files._wine + ctx.files._msi_libs + [
                ctx.file._candle,
                ctx.file._light,
                ctx.file.service_exe,
                ctx.file.agent_ctl_exe,
                ctx.file._wine_mono,
                ctx.file._wine_bin,
                ctx.file.version_file,
            ],
        ),
        tools = [ctx.executable._msibuild],
        executable = ctx.executable._script,
        arguments = [args],
        mnemonic = "WnxMsi",
        progress_message = "Linking %{output} with WiX under wine",
        use_default_shell_env = True,
    )

wnx_msi = rule(
    doc = """Builds the Windows agent MSI with WiX under wine.

        Args:
            name: Name of the rule.
            out: Path of the output MSI, relative to this package.
            srcs: The workspace-layout inputs Product.wxs references
                (wxs/wxi sources, install resources, agent plugins).
            service_exe: The cross-built check_mk_service.exe.
            agent_ctl_exe: The cross-built cmk-agent-ctl.exe.
            version_file: Single-line file with the Checkmk version to
                stamp.
        """,
    implementation = _wnx_msi_impl,
    attrs = {
        "agent_ctl_exe": attr.label(mandatory = True, allow_single_file = True),
        "out": attr.output(mandatory = True),
        "service_exe": attr.label(mandatory = True, allow_single_file = True),
        "srcs": attr.label_list(mandatory = True, allow_files = True),
        "version_file": attr.label(mandatory = True, allow_single_file = True),
        "_candle": attr.label(default = "@wix3//:candle", allow_single_file = True),
        "_light": attr.label(default = "@wix3//:light", allow_single_file = True),
        "_msi_libs": attr.label_list(
            default = [
                "@msitools//:lib",
                # SONAME-named libmsi.so.0, sibling of :lib's libmsi.so.0.0.0.
                "@msitools//:libmsi_so_symlink_fs",
                "@libgsf",
            ],
            cfg = "exec",
            doc = "msibuild's non-system runtime libraries (libmsi, libgsf);" +
                  " their directories become msibuild's LD_LIBRARY_PATH.",
        ),
        "_msibuild": attr.label(
            default = "@msitools//:msibuild",
            executable = True,
            cfg = "exec",
            doc = "Applies the post-link patches; see build_msi.sh.",
        ),
        "_script": attr.label(
            default = "//agents/wnx:install/build_msi.sh",
            executable = True,
            cfg = "exec",
            allow_single_file = True,
        ),
        "_wine": attr.label(default = "@wine_linux_x86_64//:wine"),
        "_wine_bin": attr.label(default = "@wine_linux_x86_64//:wine_bin", allow_single_file = True),
        "_wine_mono": attr.label(default = "@wine_mono//file", allow_single_file = True),
        "_wix": attr.label(default = "@wix3//:binaries"),
    },
)
