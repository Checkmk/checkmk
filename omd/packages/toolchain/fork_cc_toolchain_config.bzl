"""Fork unix_cc_toolchain_config and add static_link_cpp_runtimes feature."""

def _copy_file(repository_ctx, src, dst):
    repository_ctx.file(dst, repository_ctx.read(src))

def _fork_cc_toolchain_config_impl(repository_ctx):
    cc_toolchain_config_bzl = "unix_cc_toolchain_config.bzl"
    _copy_file(
        repository_ctx,
        # https://cs.opensource.google/bazel/bazel/+/master:tools/cpp/unix_cc_toolchain_config.bzl
        Label("@bazel_tools//tools/cpp:" + cc_toolchain_config_bzl),
        cc_toolchain_config_bzl,
    )

    # Patch adapted from https://github.com/bazelbuild/bazel/issues/14342#issuecomment-983956125
    repository_ctx.patch(Label(":add_static_link_cpp_runtimes_feature.patch"), strip = 3)
    repository_ctx.file("BUILD.bazel", 'exports_files(["' + cc_toolchain_config_bzl + '"])')

fork_cc_toolchain_config = repository_rule(
    implementation = _fork_cc_toolchain_config_impl,
)
