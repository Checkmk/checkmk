load("@cpp_libs_opt//:symlink_mappings.bzl", opt_mappings = "SYMLINK_MAPPINGS")
load("@cpp_libs_usr//:symlink_mappings.bzl", usr_mappings = "SYMLINK_MAPPINGS")
load("@rules_pkg//pkg:mappings.bzl", "pkg_files")
load("@rules_pkg//pkg:tar.bzl", "pkg_tar")
load("//bazel/rules:patchelf.bzl", "set_runpath")
load(":create_symlink_targets.bzl", "create_symlink_targets")

# Create pkg_mklink targets from symlink mappings
# This keeps packaging concerns separate from repository detection
_usr_symlink_targets = create_symlink_targets("usr", usr_mappings)

_opt_symlink_targets = create_symlink_targets("opt", opt_mappings)

set_runpath(
    name = "set_runpath",
    srcs = ["//bazel/toolchains/cc/gcc/local:cpp_libs_elf"],
    tags = ["manual"],
)

# Collect all files for packaging
pkg_files(
    name = "patched_elf_files_pkg",
    srcs = [":set_runpath"] + select({
        "//bazel/toolchains/cc/gcc/local:opt": ["@cpp_libs_opt//:cpp_libs_files"],
        "//conditions:default": ["@cpp_libs_usr//:cpp_libs_files"],
    }),
    prefix = "lib",
    tags = ["manual"],
)

# Package everything into tarball
# Symlinks are created from repository mappings above, selected between
# opt and usr based on the gcc_path flag.
pkg_tar(
    name = "cpp-libs",
    srcs = [
        ":patched_elf_files_pkg",
    ] + select({
        "//bazel/toolchains/cc/gcc/local:opt": _opt_symlink_targets,
        "//conditions:default": _usr_symlink_targets,
    }),
    stamp = 1,
    tags = ["manual"],
    visibility = ["//visibility:public"],
)
