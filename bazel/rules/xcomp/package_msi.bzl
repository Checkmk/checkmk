"""Rule linking an MSI with WiX under wine, on Linux.

The rule stages its inputs, sets up wine and leaves the WiX invocations and
any post-link patching to a per-package script. That script sources
xcomp/package_msi.sh, which consumes the arguments the rule passes:

    source "$1"
    shift
    package_msi_init "$@"
    set -- "${PACKAGE_MSI_ARGS[@]}"
"""

def _package_msi_impl(ctx):
    staged = []
    for src in ctx.files.srcs:
        if not src.is_source:
            # Generated files have no workspace path to be staged at.
            fail("srcs takes source files only, got %s; use stage_files" % src)
        staged.append((src, src.path))
    for target, dest in ctx.attr.stage_files.items():
        files = target.files.to_list()
        if len(files) != 1:
            fail("stage_files expects single files, %s has %d" % (target.label, len(files)))
        staged.append((files[0], dest))

    lib_dirs = []
    for lib in ctx.files._msi_libs:
        if ".so" in lib.basename and lib.dirname not in lib_dirs:
            lib_dirs.append(lib.dirname)

    args = ctx.actions.args()
    args.add(ctx.file._lib)
    args.add(ctx.file._candle)
    args.add(ctx.file._light)
    args.add(ctx.file._wine_mono)
    args.add(ctx.file._wine_bin)
    args.add(ctx.executable._msibuild)
    args.add_joined(lib_dirs, join_with = ":")
    args.add(ctx.outputs.out)
    args.add(ctx.file.version_file)
    args.add(ctx.label.package)
    args.add(len(staged))
    for file, dest in staged:
        args.add(file)
        args.add(dest)
    args.add_all([
        ctx.expand_location(arg, targets = ctx.attr.tools)
        for arg in ctx.attr.script_args
    ])

    ctx.actions.run(
        outputs = [ctx.outputs.out],
        inputs = depset(
            [file for file, _ in staged] +
            ctx.files._wix + ctx.files._wine + ctx.files._msi_libs + [
                ctx.file._lib,
                ctx.file._candle,
                ctx.file._light,
                ctx.file._wine_mono,
                ctx.file._wine_bin,
                ctx.file.version_file,
            ],
        ),
        tools = [ctx.attr._msibuild[DefaultInfo].files_to_run] + [
            tool[DefaultInfo].files_to_run
            for tool in ctx.attr.tools
        ],
        executable = ctx.executable.script,
        arguments = [args],
        mnemonic = "PackageMsi",
        progress_message = "Linking %{output} with WiX under wine",
        use_default_shell_env = True,
    )

package_msi = rule(
    doc = """Links an MSI with WiX under wine.

        Args:
            name: Name of the rule.
            out: Path of the output MSI, relative to this package.
            srcs: Source files, staged at their workspace paths: the WiX
                sources and every file they reference.
            stage_files: Generated single files, staged at the given
                workspace-relative paths (e.g. cross-built executables).
            version_file: Single-line file with the Checkmk version to
                stamp, read into CMK_VERSION.
            script: The package's script running WiX on the staged tree.
            script_args: Further arguments to the script, subject to
                $(location) expansion of tools.
            tools: Executables the script runs.
        """,
    implementation = _package_msi_impl,
    attrs = {
        "out": attr.output(mandatory = True),
        "script": attr.label(
            mandatory = True,
            executable = True,
            cfg = "exec",
            allow_single_file = True,
        ),
        "script_args": attr.string_list(),
        "srcs": attr.label_list(allow_files = True),
        "stage_files": attr.label_keyed_string_dict(allow_files = True),
        "tools": attr.label_list(cfg = "exec", allow_files = True),
        "version_file": attr.label(mandatory = True, allow_single_file = True),
        "_candle": attr.label(default = "@wix3//:candle", allow_single_file = True),
        "_lib": attr.label(
            default = "//bazel/rules:xcomp/package_msi.sh",
            allow_single_file = True,
        ),
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
            doc = "Applies the post-link patches; see patch_msi in package_msi.sh.",
        ),
        "_wine": attr.label(default = "@wine_linux_x86_64//:wine"),
        "_wine_bin": attr.label(default = "@wine_linux_x86_64//:wine_bin", allow_single_file = True),
        "_wine_mono": attr.label(default = "@wine_mono//file", allow_single_file = True),
        "_wix": attr.label(default = "@wix3//:binaries"),
    },
)
