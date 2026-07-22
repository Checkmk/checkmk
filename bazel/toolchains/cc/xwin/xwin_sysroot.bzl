"""Repository rule providing the MSVC CRT + Windows SDK for cross compilation.

Downloads a pinned release of xwin (https://github.com/Jake-Shadle/xwin) and
runs `xwin splat`, which fetches the MSVC CRT and Windows SDK packages from
Microsoft's Visual Studio package feed and lays them out with case-corrected
symlinks so they work on a case-sensitive Linux filesystem.

`--accept-license` (below and in the archive recipe) accepts the Microsoft
Software License Terms for the Visual Studio build tools packages:
https://go.microsoft.com/fwlink/?LinkId=2086102
Because that acceptance must be a deliberate act by whoever fetches from
Microsoft, the xwin fallback only runs with XWIN_ACCEPT_LICENSE=1 in the
environment (see below).

Layout produced under @xwin_sysroot:
    crt/include/**         MSVC CRT headers (vcruntime.h, stdio.h, ...)
    crt/lib/x86_64/**      MSVC CRT link libs (libcmt, libucrt, oldnames, ...)
    sdk/include/**         Windows SDK headers (Windows.h, winsock2.h, ...)
    sdk/lib/um/x86_64/**   User-mode SDK import libs (kernel32, ws2_32, ...)
    sdk/lib/ucrt/x86_64/** Universal C Runtime link libs

A pre-splatted archive of the pinned sysroot is preferred from the internal
mirror: it goes through Bazel's downloader (repository cache, integrity
check) and avoids depending on Microsoft's CDN. When the mirror doesn't
serve it (yet), the rule falls back to running xwin, which fetches the SDK
packages itself, bypassing Bazel's downloader.

To (re)create and publish the mirror archive after bumping the pins in
bazel/module/xwin.MODULE.bazel:

    xwin --accept-license --temp --manifest-version <M> \\
        --crt-version <CRT> --sdk-version <SDK> splat --output sysroot
    find sysroot -type l -lname . -delete
    tar -C sysroot --sort=name --owner=0 --group=0 --numeric-owner \\
        --mtime='2026-01-01 00:00:00Z' -cf - crt sdk \\
        | xz -T0 -6 > xwin-sysroot-crt<CRT>-sdk<SDK>-x86_64.tar.xz

then upload it to the upstream-archives Nexus repository and update
sysroot_sha256 in bazel/module/xwin.MODULE.bazel.
"""

def _xwin_sysroot_impl(rctx):
    mirror = rctx.download_and_extract(
        url = rctx.attr.sysroot_url,
        sha256 = rctx.attr.sysroot_sha256,
        allow_fail = True,
    )
    if mirror.success:
        rctx.template("BUILD.bazel", rctx.attr._build_file, executable = False)
        return

    # The fallback downloads MSVC CRT + Windows SDK packages from Microsoft's
    # VS feed, whose use requires accepting the Microsoft Software License
    # Terms (link in the header). Repository rules cannot prompt, so require
    # the acceptance as an explicit env var — the usual approach for
    # license-gated Bazel repositories (the Android SDK rules work the same
    # way: licenses are pre-accepted out of band, never silently).
    # rctx.getenv registers the variable, so changing it triggers a re-fetch.
    if not rctx.getenv("XWIN_ACCEPT_LICENSE"):
        fail(
            "fetching the pre-splatted xwin sysroot from the internal " +
            "mirror failed ({}), ".format(rctx.attr.sysroot_url) +
            "and the xwin fallback downloads MSVC CRT + Windows SDK " +
            "packages from Microsoft's VS feed, which requires accepting " +
            "the Microsoft Software License Terms:\n" +
            "  https://go.microsoft.com/fwlink/?LinkId=2086102\n" +
            "Set XWIN_ACCEPT_LICENSE=1 to accept them and enable the " +
            "fallback.",
        )

    # print is deliberate: repository rules have no warning API and
    # rctx.report_progress() is transient (gone once the fetch finishes).
    # This is the one channel that leaves a trace in the log, and a CI run
    # falling back to Microsoft's CDN must leave one.
    # buildifier: disable=print
    print("WARNING: could not fetch the xwin sysroot from the internal mirror ({}) — missing, network error, or checksum mismatch; splatting via xwin from Microsoft's CDN instead".format(rctx.attr.sysroot_url))

    rctx.download_and_extract(
        url = rctx.attr.xwin_url,
        sha256 = rctx.attr.xwin_sha256,
        stripPrefix = rctx.attr.xwin_strip_prefix,
        output = "_xwin_tool",
    )

    rctx.report_progress("Downloading MSVC CRT + Windows SDK via xwin ...")
    result = rctx.execute(
        [
            "_xwin_tool/xwin",
            "--accept-license",
            "--temp",
            "--http-retry",
            "3",
            "--manifest-version",
            rctx.attr.vs_manifest_version,
            "--crt-version",
            rctx.attr.crt_version,
            "--sdk-version",
            rctx.attr.sdk_version,
            "splat",
            "--output",
            ".",
        ],
        timeout = 1800,
    )
    if result.return_code != 0:
        fail("xwin splat failed (exit {}):\n{}".format(result.return_code, result.stderr))

    # xwin adds self-referential SDK version symlinks (sdk/include/10.0.x -> .)
    # so version-qualified include paths resolve. Bazel's glob() follows
    # symlinked directories and fails on the cycle, and nothing in this
    # toolchain uses version-qualified paths, so drop them. The file-level
    # case-correcting symlinks (windows.h -> Windows.h, ...) stay.
    result = rctx.execute(["find", ".", "-type", "l", "-lname", ".", "-delete"])
    if result.return_code != 0:
        fail("pruning self-referential symlinks failed:\n{}".format(result.stderr))

    rctx.delete("_xwin_tool")
    rctx.template("BUILD.bazel", rctx.attr._build_file, executable = False)

xwin_sysroot = repository_rule(
    implementation = _xwin_sysroot_impl,
    attrs = {
        "crt_version": attr.string(
            mandatory = True,
            doc = "MSVC CRT version passed to `xwin`.",
        ),
        "sdk_version": attr.string(
            mandatory = True,
            doc = "Windows SDK version passed to `xwin`.",
        ),
        "sysroot_sha256": attr.string(
            mandatory = True,
            doc = "Expected SHA-256 of the pre-splatted sysroot archive.",
        ),
        "sysroot_url": attr.string(
            mandatory = True,
            doc = "URL of the pre-splatted sysroot archive on the internal mirror.",
        ),
        "vs_manifest_version": attr.string(
            mandatory = True,
            doc = "Visual Studio manifest (channel) version passed to `xwin`.",
        ),
        "xwin_sha256": attr.string(
            mandatory = True,
            doc = "Expected SHA-256 of the xwin tool release archive.",
        ),
        "xwin_strip_prefix": attr.string(
            mandatory = True,
            doc = "Directory prefix to strip from the extracted xwin tool archive.",
        ),
        "xwin_url": attr.string(
            mandatory = True,
            doc = "URL of the xwin tool release used by the fallback.",
        ),
        "_build_file": attr.label(
            default = Label("//bazel/toolchains/cc/xwin:BUILD.xwin_sysroot.bazel"),
            allow_single_file = True,
        ),
    },
    doc = "MSVC CRT + Windows SDK sysroot for cross compiling to windows-msvc.",
)
