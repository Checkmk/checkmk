"""Module extension declaring the binary tools of the Windows agent build."""

load("@bazel_tools//tools/build_defs/repo:http.bzl", "http_archive", "http_file")
load("//:bazel_variables.bzl", "CI_BINARY_ARTIFACTS_URL", "UPSTREAM_MIRROR_URL")

def _repos_impl(_mctx):
    # A portable Wine build (WoW64: 64-bit, no i386 multilib on the host).
    # The build recipe, source pin and publishing job live in
    # third_party/wine/ and buildscripts/scripts/build-wine-from-source.groovy.
    http_archive(
        name = "wine_linux_x86_64",
        build_file = "//third_party/wine:BUILD.wine.bazel",
        sha256 = "2894e6624bcf8714c5b4c303ca9f125e3ebdd5275e1d62308290aa4feb278e27",
        strip_prefix = "wine-11.0-amd64-wow64",
        urls = [
            CI_BINARY_ARTIFACTS_URL + "wine/wine/11.0/linux/amd64/wow64/wine-11.0-amd64-wow64.tar.xz",
        ],
    )
    http_file(
        name = "wine_mono",
        sha256 = "071f4b2887e1c97a11d791ff3d65be9429eed6dec4c2708888bfd546ba358e23",
        urls = [
            UPSTREAM_MIRROR_URL + "wine-mono-10.4.1-x86.msi",
            "https://dl.winehq.org/wine/wine-mono/10.4.1/wine-mono-10.4.1-x86.msi",
        ],
    )
    http_archive(
        name = "wix3",
        build_file = "//third_party/wine:BUILD.wix.bazel",
        sha256 = "6ac824e1642d6f7277d0ed7ea09411a508f6116ba6fae0aa5f2c7daa2ff43d31",
        urls = [
            UPSTREAM_MIRROR_URL + "wix314-binaries.zip",
            "https://github.com/wixtoolset/wix3/releases/download/wix3141rtm/wix314-binaries.zip",
        ],
    )

repos = module_extension(
    implementation = _repos_impl,
)
