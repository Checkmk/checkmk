"""Rules wrapping patchelf."""

def _set_runpath_impl(ctx):
    """Patches ELF files with the given RUNPATH."""
    patchelf = ctx.executable._patchelf
    outputs = []
    for src in ctx.files.srcs:
        out = ctx.actions.declare_file(src.basename)
        ctx.actions.run(
            outputs = [out],
            inputs = [src],
            executable = patchelf,
            arguments = [
                "--set-rpath",
                ctx.attr.rpath,
                "--output",
                out.path,
                src.path,
            ],
            mnemonic = "SetRunpath",
            progress_message = "Patching %s with RUNPATH %s" % (src.basename, ctx.attr.rpath),
        )
        outputs.append(out)

    return [DefaultInfo(files = depset(outputs))]

set_runpath = rule(
    implementation = _set_runpath_impl,
    attrs = {
        "rpath": attr.string(
            default = "${ORIGIN}",
            doc = "RUNPATH to set. Defaults to ${ORIGIN}.",
        ),
        "srcs": attr.label_list(
            allow_files = True,
            doc = "ELF files to patch",
            mandatory = True,
        ),
        "_patchelf": attr.label(
            cfg = "exec",
            default = "@patchelf//:patchelf",
            executable = True,
        ),
    },
    doc = "Sets the RUNPATH of the given ELF files to the given RUNPATH",
)
