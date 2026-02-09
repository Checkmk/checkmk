load("@cpp_libs_opt//:symlink_mappings.bzl", opt_mappings = "SYMLINK_MAPPINGS")
load("@cpp_libs_usr//:symlink_mappings.bzl", usr_mappings = "SYMLINK_MAPPINGS")
load("@rules_pkg//pkg:mappings.bzl", "pkg_files")
load("@rules_pkg//pkg:tar.bzl", "pkg_tar")
load("//bazel/rules:patchelf.bzl", "set_runpath")
load("//bazel/toolchains/cc/gcc/bootlin:symlink_mappings.bzl", bootlin_mappings = "SYMLINK_MAPPINGS")
load(":create_symlink_targets.bzl", "create_symlink_targets")

# Create pkg_mklink targets from symlink mappings
# This keeps packaging concerns separate from repository detection
_usr_symlink_targets = create_symlink_targets("usr", usr_mappings)

_opt_symlink_targets = create_symlink_targets("opt", opt_mappings)

_bootlin_symlink_targets = create_symlink_targets("bootlin", bootlin_mappings)

set_runpath(
    name = "set_runpath",
    srcs = select({
        "//bazel/platforms:is_hermetic": ["@gcc-linux-x86_64//:cpp_libs_elf"],
        "//conditions:default": ["//bazel/toolchains/cc/gcc/local:cpp_libs_elf"],
    }),
    tags = ["manual"],
)

# Collect all files for packaging
pkg_files(
    name = "patched_elf_files_pkg",
    srcs = [":set_runpath"] + select({
        "//bazel/platforms:is_hermetic": ["@gcc-linux-x86_64//:cpp_libs_files"],
        "//bazel/toolchains/cc/gcc/local:opt": ["@cpp_libs_opt//:cpp_libs_files"],
        "//conditions:default": ["@cpp_libs_usr//:cpp_libs_files"],
    }),
    prefix = "lib",
    tags = ["manual"],
)

# Package everything into tarball
# Note: For local toolchain, symlinks are created from repository mappings above
# For hermetic Bootlin toolchain, symlinks are defined in BUILD.bootlin.bazel
pkg_tar(
    name = "cpp-libs",
    srcs = [
        ":patched_elf_files_pkg",
    ] + select({
        # Bootlin symlinks (hermetic) - created from mappings above
        "//bazel/platforms:is_hermetic": _bootlin_symlink_targets,
        # Local symlinks - select between opt and usr based on gcc_path flag
        "//bazel/toolchains/cc/gcc/local:opt": _opt_symlink_targets,
        "//conditions:default": _usr_symlink_targets,
    }),
    stamp = 1,
    tags = ["manual"],
    visibility = ["//visibility:public"],
)
