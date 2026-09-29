"""Module extension declaring the static QEMU (third_party/qemu)."""

load("@bazel_tools//tools/build_defs/repo:http.bzl", "http_archive")
load("//:bazel_variables.bzl", "UPSTREAM_MIRROR_URL")
load("//third_party/qemu:version.bzl", "QEMU_ARCHIVE")

def _repos_impl(mctx):
    # A static QEMU with KVM, user networking and zstd. The recipe, source
    # pins and publishing job live in third_party/qemu/ and
    # buildscripts/scripts/build-qemu-from-source.groovy.
    http_archive(
        name = "qemu_linux_x86_64",
        build_file = "//third_party/qemu:BUILD.qemu.bazel",
        sha256 = QEMU_ARCHIVE.sha256,
        strip_prefix = QEMU_ARCHIVE.name,
        urls = [UPSTREAM_MIRROR_URL + QEMU_ARCHIVE.name + ".tar.xz"],
    )

    # Fully pinned by sha256: nothing for MODULE.bazel.lock to record, so a
    # re-pin does not touch it.
    return mctx.extension_metadata(reproducible = True)

repos = module_extension(
    implementation = _repos_impl,
)
