load("@aspect_bazel_lib//lib:copy_to_directory.bzl", "copy_to_directory")
load("@gcc_toolchain//:cpp_libs.bzl", "CPP_LIBS_ELF", "SYMLINK_MAPPINGS")
load("@rules_pkg//pkg:mappings.bzl", "pkg_files")
load("//bazel/rules:patchelf.bzl", "set_runpath")
load("//bazel/rules:pkg.bzl", "pkg_tar")
load("//bazel/rules:xcomp/cc.bzl", "cc_test")
load(":create_symlink_targets.bzl", "create_symlink_targets")

_symlink_targets = create_symlink_targets("gcc_toolchain", SYMLINK_MAPPINGS)

genrule(
    name = "strip",
    srcs = ["@gcc_toolchain//:cpp_libs_elf"],
    outs = ["stripped/" + lib for lib in CPP_LIBS_ELF],
    cmd = """
        for src in $(SRCS); do
            $(execpath @gcc_toolchain//:bin/x86_64-checkmk-linux-gnu-strip) \\
                --strip-unneeded --remove-section=.comment \\
                -o $(RULEDIR)/stripped/$$(basename $$src) $$src
        done
    """,
    tags = ["manual"],
    tools = ["@gcc_toolchain//:bin/x86_64-checkmk-linux-gnu-strip"],
)

set_runpath(
    name = "set_runpath",
    srcs = [":strip"],
    tags = ["manual"],
)

# The shipped libraries, for tests to load via LD_LIBRARY_PATH like the site does
copy_to_directory(
    name = "runtime",
    srcs = [":set_runpath"],
    replace_prefixes = {dict(SYMLINK_MAPPINGS)["libstdc++.so.6"]: "libstdc++.so.6"},
    root_paths = ["omd/packages/cpp-libs/set_runpath"],
    tags = ["manual"],
    visibility = ["//visibility:public"],
)

# Collect all files for packaging
pkg_files(
    name = "patched_elf_files_pkg",
    srcs = [":set_runpath"] + ["@gcc_toolchain//:cpp_libs_files"],
    prefix = "lib",
    tags = ["manual"],
)

# Package everything into tarball
pkg_tar(
    name = "cpp-libs",
    srcs = [
        ":patched_elf_files_pkg",
    ] + _symlink_targets,
    stamp = 1,
    tags = ["manual"],
    visibility = ["//visibility:public"],
)

cc_test(
    name = "test_tzdata",
    size = "small",
    srcs = ["test/test_tzdata.cc"],
    copts = ["-std=c++20"],
    features = ["static_libstdcpp"],
    platform = "//bazel/platforms:x86_64-linux-gcc-hermetic",
    tags = ["cpp"],
    deps = ["@gtest//:gtest_main"],
)
