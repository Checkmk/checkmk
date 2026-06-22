load("@rules_pkg//pkg:mappings.bzl", "pkg_attributes", "pkg_files")
load("@rules_pkg//pkg:tar.bzl", "pkg_tar")
load("//bazel/rules:patchelf.bzl", "set_runpath")

# Extract the man page from the foreign_cc install tree.
genrule(
    name = "patch_man_page",
    srcs = ["@patch//:gen_dir"],
    outs = ["patch.1"],
    cmd = "cp $(location @patch//:gen_dir)/share/man/man1/patch.1 $@",
    tags = ["manual"],
)

# rules_foreign_cc links through the C++ toolchain driver, so the binary
# picks up the toolchain's default `-lstdc++ -lm` and ends up with a
# DT_NEEDED on libstdc++.so.6 (and libm.so.6) even though patch is pure C.
# OMD ships libstdc++.so.6 in its lib dir, so point a RUNPATH at it
# ($ORIGIN/../lib, i.e. bin/../lib) the same way redis does.
set_runpath(
    name = "patch_runpath",
    srcs = ["@patch//:patch_bin"],
    rpaths = ["$ORIGIN/../lib"],
    tags = ["manual"],
)

pkg_files(
    name = "patch_bin_pkg",
    srcs = [":patch_runpath"],
    attributes = pkg_attributes(
        mode = "0755",
    ),
    prefix = "bin",
    tags = ["manual"],
)

pkg_files(
    name = "patch_man_pkg",
    srcs = [":patch_man_page"],
    prefix = "share/man/man1",
    tags = ["manual"],
)

pkg_tar(
    name = "patch",
    srcs = [
        ":patch_bin_pkg",
        ":patch_man_pkg",
    ],
    stamp = 1,
    tags = ["manual"],
    visibility = ["//omd:__pkg__"],
)
