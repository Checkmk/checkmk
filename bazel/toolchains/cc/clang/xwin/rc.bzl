# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Compile a Windows .rc resource script to a .res object with llvm-rc."""

load("@bazel_skylib//rules/directory:providers.bzl", "DirectoryInfo")

def _windows_rc_impl(ctx):
    out = ctx.actions.declare_file(ctx.label.name + ".res")

    args = ctx.actions.args()
    sysroot_inputs = []
    for dep in ctx.attr.sysroot_includes:
        directory = dep[DirectoryInfo]
        args.add("/I", directory.path)
        sysroot_inputs.append(directory.transitive_files)
    for include in ctx.attr.includes:
        if include == ".":
            args.add("/I", ctx.label.package)
        else:
            args.add("/I", ctx.label.package + "/" + include)
    args.add("/FO", out)
    args.add(ctx.file.src)

    clang = ctx.attr._clang[DefaultInfo].default_runfiles.files

    ctx.actions.run(
        executable = ctx.file._llvm_rc,
        arguments = [args],
        inputs = depset(
            direct = [ctx.file.src] + ctx.files.hdrs,
            transitive = sysroot_inputs,
        ),
        tools = depset([ctx.file._llvm_rc], transitive = [clang]),
        outputs = [out],
        mnemonic = "WindowsResource",
        progress_message = "Compiling Windows resource %{label}",
    )
    return [DefaultInfo(files = depset([out]))]

windows_rc = rule(
    implementation = _windows_rc_impl,
    doc = "Compile a .rc resource script to a .res with llvm-rc (cross from Linux).",
    attrs = {
        "hdrs": attr.label_list(
            allow_files = True,
            doc = "Headers and data files the .rc script includes.",
        ),
        "includes": attr.string_list(
            doc = "Package-relative /I directories for the .rc's own " +
                  "#includes, as in cc_library. Headers reachable through " +
                  "them are not discovered: each one the .rc pulls in must " +
                  "also be listed in hdrs, or llvm-rc fails to find it.",
        ),
        "src": attr.label(
            allow_single_file = [".rc"],
            mandatory = True,
            doc = "The .rc resource script to compile.",
        ),
        "sysroot_includes": attr.label_list(
            default = [
                "@xwin_sysroot//:crt_include",
                "@xwin_sysroot//:sdk_include_ucrt",
                "@xwin_sysroot//:sdk_include_um",
                "@xwin_sysroot//:sdk_include_shared",
            ],
            providers = [DirectoryInfo],
            doc = "Windows SDK / CRT include directories; defaults to the " +
                  "@xwin_sysroot set in the cc toolchain's search order.",
        ),
        "_clang": attr.label(
            default = "@llvm_toolchain//:compiler_builtins",
        ),
        "_llvm_rc": attr.label(
            allow_single_file = True,
            default = "@llvm_toolchain//:bin/llvm-rc",
        ),
    },
)
