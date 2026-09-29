# Package for third_party/qemu: lets BUILD.qemu.bazel be referenced as
# @qemu_linux_x86_64's build_file and version.bzl be loaded.

sh_test(
    name = "version_test",
    size = "small",
    srcs = ["version_test.sh"],
    data = [
        "create-archive",
        "sources.txt",
        "version.bzl",
    ],
)
